// 并行数据处理调度核心
// 暂时不处理跨平台编译问题（MSVC编译会失败）
#include <cstdio>
#include <thread>

#include <queue>
#include <condition_variable>
#include <semaphore>
#include <mutex>
#include <atomic>

#include <cstddef>
#include <cstdint>
#include <system_error>

#if defined(_WIN32) || defined(_WIN64)
#define SHARED __declspec(dllexport)
#else
#define SHARED __attribute__((visibility("default")))
#endif

#define externc extern "C"

volatile const char DEFINE[] = "This a custom library for parallel processing, use for img2arr project.";

using SingleCoreFunc = int(*)(void* args, uint8_t* int_buf, uint8_t* out_buf, size_t in_shape[]); 
using MultiCoreFunc = int(*)(size_t threads, size_t idx, void* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[]);

// 核心。返回值：
// 对于单核，返回值恒返回0，ret[0]被设为func的返回值值
// 对于多核，ret[i]被设为工作在第i个线程的func的返回值，但函数的返回值：
// - 0: 成功
// - -x: 有x个线程创建失败。注意：一个线程创建失败（不看函数返回值），其他线程可能仍会继续运行。
//       会将失败信息输出到终端（传递一个不定长字符串到Python是一个不简单的事）
// 对于其他，直接返回所需特定驱动程序的错误码
// 其他：返回0表示功能未实现

externc SHARED int SingleCore(char* caller, void* func, void* args, int *ret,
    uint8_t* in_buffer, uint8_t* out_buffer, 
    size_t in_shape[])
{
    SingleCoreFunc func_ = (SingleCoreFunc)func;
    *ret = func_(args, in_buffer, out_buffer, in_shape);
    return 0;
}

// 旧实现，现不推荐使用
externc SHARED int MultiCore_old(char* caller, size_t threadnum, void* func, void* args, int *ret,
    uint8_t* in_buffer, uint8_t* out_buffer,
    size_t in_shape[])
{
    
    MultiCoreFunc func_ = (MultiCoreFunc)func;
    std::thread* threads = new std::thread[threadnum];
    int _ret = 0;
    for(size_t i = 0; i < threadnum; i++){
        try{
            // printf("PlProcCore: On caller %s, Creating thread %d\n", caller, i);
            threads[i] = std::thread([ret, func_, threadnum, args, in_buffer, out_buffer, in_shape](size_t i){
                ret[i] = func_(threadnum, i, args, in_buffer, out_buffer, in_shape);
            }, i);
        }catch(std::system_error &e){
            fprintf(stderr, "PlProcCore Error: On caller %s, Failed to create thread %zu: %s\n", caller, i, e.what());
            _ret--;
        }
    }
    for(size_t i = 0; i < threadnum; i++){
        threads[i].join();
    }
    delete[] threads;
    return _ret;
}


// 多线程部分大更新：自然任务管理，使用线程池，大幅提高速度和均衡性

class ThreadPoolCtx{
// 创建参数结构体、队列和线程池函数
    struct mtTask{
        size_t threads;
        size_t idx;
        MultiCoreFunc func;
        void* args;
        size_t *in_shape;
        uint8_t* in_buffer;
        uint8_t* out_buffer;
        int* ret;
    };
private:
    std::vector<std::thread> ThreadPool;
    std::atomic<bool> ThreadPool_Running{true};
    std::mutex TaskMutex;
    std::queue<mtTask> TaskQueue;
    std::counting_semaphore<> TaskQueueSemaphore{0}; //计数信号量
    std::condition_variable TaskQueueCV;

    void ThreadPoolFunc(){
        while(this->ThreadPool_Running){
            // 若TaskQueue为空，则等待
            std::unique_lock<std::mutex> lock(this->TaskMutex);
            // 如果队列为空且线程池仍在运行，才等待
            if(this->TaskQueue.empty() && this->ThreadPool_Running){
                TaskQueueCV.wait(lock, [this]{
                    return !this->TaskQueue.empty() || !this->ThreadPool_Running;
                });
            }
            if(!this->ThreadPool_Running){
                // 该休息了
                // 自动解锁
                return;
            }
            // 取出任务
            mtTask task = this->TaskQueue.front();
            this->TaskQueue.pop();
            // 解锁
            lock.unlock();
            // 执行任务
            int ret = task.func(task.threads, task.idx, task.args, task.in_buffer, task.out_buffer, task.in_shape);
            // 将返回值存入ret
            task.ret[task.idx] = ret;
            // 任务完成
            this->TaskQueueSemaphore.release();
        }
    }
public:
    constexpr size_t get_threads(){
        return ThreadPool.size();
    }
    
    ThreadPoolCtx() = default;

    size_t InitThreadPool(size_t threadnum){
        // 若还在运行，结束线程
        if(this->ThreadPool_Running){
            this->ThreadPool_Running = false;
            this->TaskQueueCV.notify_all();
            for(auto& thread : this->ThreadPool){
                thread.join();
            }
            this->ThreadPool.clear();
        }
        // 清空任务队列和信号量
        while(this->TaskQueueSemaphore.try_acquire()) {
            // 清空所有pending的信号量计数
        }
        while(!this->TaskQueue.empty()){
            this->TaskQueue.pop();
        }
        this->ThreadPool_Running = true;
        // 创建线程
        size_t real_threadnum = 0; // 实际创建的线程数
        this->ThreadPool.reserve(threadnum);
        for(size_t i = 0; i < threadnum; i++){
            try{
                this->ThreadPool.emplace_back(std::thread([this]{
                    this->ThreadPoolFunc();
                }));
                real_threadnum++;
            }catch(std::system_error &e){
                fprintf(stderr, "ThreadPoolCtx::InitThreadPool Error: Failed to create thread %zu: %s\n", i, e.what());
            }
        }
        return real_threadnum;
    }
    // 当tasks=0时，表示tasks=threads
    int MultiCore(
        char* caller, void* func, void* args, int *ret,
        uint8_t* in_buffer, uint8_t* out_buffer,
        size_t in_shape[],
        size_t tasks
    )
    {   
        if(tasks == 0){
            tasks = this->ThreadPool.size();
        }
        // 添加至队列
        size_t threads = this->ThreadPool.size();
        if (threads == 0){
            fprintf(stderr, "ThreadPoolCtx Error: On caller %s, No thread pool initialized. Please call InitThreadPool() first.\n", caller);
            return -114514;
        }
        for(size_t i = 0; i < tasks; i++){
            TaskQueue.push({
                .threads = tasks,
                .idx = i,
                .func = (MultiCoreFunc)func,
                .args = args,
                .in_shape = in_shape,
                .in_buffer = in_buffer,
                .out_buffer = out_buffer,
                .ret = ret
            });
            // printf("Run %s in thread %zu, total %zu\n", caller, i, tasks);
        }
        // 唤醒并等待全部任务完成
        this->TaskQueueCV.notify_all();
        for(size_t i = 0; i < tasks; i++){
            this->TaskQueueSemaphore.acquire();
        }
        return 0;
    }

    ~ThreadPoolCtx(){
        this->ThreadPool_Running = false;
        this->TaskQueueCV.notify_all();
        for(auto& thread : this->ThreadPool){
            thread.join();
        }
        this->ThreadPool.clear();
    }
};

externc SHARED ThreadPoolCtx* NewThreadPoolCtx(){
    return new ThreadPoolCtx();
}

// 初始化/重新初始化线程池
externc SHARED size_t InitThreadPool(ThreadPoolCtx* ctx, size_t threadnum){
    return ctx->InitThreadPool(threadnum);
}

externc SHARED size_t ThreadPoolGetThreads(ThreadPoolCtx* ctx){
    return ctx->get_threads();
}

externc SHARED int MultiCore(ThreadPoolCtx* ctx,
    char* caller, void* func, void* args, int *ret,
    uint8_t* in_buffer, uint8_t* out_buffer,
    size_t in_shape[],
    size_t tasks
)
{
    ctx->MultiCore(caller, func, args, ret, in_buffer, out_buffer, in_shape, tasks);
    return 0;
}

externc SHARED void DeleteThreadPoolCtx(ThreadPoolCtx* ctx){
    delete ctx;
}