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

#define cdecl extern "C"

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
// 其他：返回114514表示功能未实现

cdecl SHARED int SingleCore(char* caller, void* func, void* args, int *ret,
    uint8_t* in_buffer, uint8_t* out_buffer, 
    size_t in_shape[])
{
    SingleCoreFunc func_ = (SingleCoreFunc)func;
    *ret = func_(args, in_buffer, out_buffer, in_shape);
    return 0;
}

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

// 多线程部分大更新：自然任务管理，使用线程池，大幅提高速度和均衡性

std::atomic<bool> ThreadPool_Running{true};
std::mutex TaskMutex;
std::queue<mtTask> TaskQueue;
std::counting_semaphore TaskQueueSemaphore(0); //计数信号量
std::condition_variable TaskQueueCV;

std::vector<std::thread> ThreadPool;

static void ThreadPoolFunc(){
    while(ThreadPool_Running){
        // 若TaskQueue为空，则等待
        std::unique_lock<std::mutex> lock(TaskMutex);
        TaskQueueCV.wait(lock, []{return !TaskQueue.empty() || !ThreadPool_Running;});
        if(!ThreadPool_Running){
            // 该休息了
            // 自动解锁
            return;
        }
        // 取出任务
        mtTask task = TaskQueue.front();
        TaskQueue.pop();
        // 解锁
        lock.unlock();
        // 执行任务
        int ret = task.func(task.threads, task.idx, task.args, task.in_buffer, task.out_buffer, task.in_shape);
        // 将返回值存入ret
        task.ret[task.idx] = ret;
        // 任务完成
        TaskQueueSemaphore.release();
    }
}

// 初始化/重新初始化线程池
cdecl SHARED size_t InitThreadPool(size_t threadnum){
    // 若还在运行，结束线程
    if(ThreadPool_Running){
        ThreadPool_Running = false;
        TaskQueueCV.notify_all();
        for(auto& thread : ThreadPool){
            thread.join();
        }
        ThreadPool.clear();
    }
    // 清空任务队列和信号量
    while(TaskQueueSemaphore.try_acquire()) {
        // 清空所有pending的信号量计数
    }
    while(!TaskQueue.empty()){
        TaskQueue.pop();
    }
    ThreadPool_Running = true;
    // 创建线程
    size_t real_threadnum = 0; // 实际创建的线程数
    ThreadPool.reserve(threadnum);
    for(size_t i = 0; i < threadnum; i++){
        try{
            ThreadPool.emplace_back(std::thread(ThreadPoolFunc));
            real_threadnum++;
        }catch(std::system_error &e){
            fprintf(stderr, "PlProcCore::InitThreadPool Error: Failed to create thread %zu: %s\n", i, e.what());
        }
    }
    return real_threadnum;
}

// 旧实现，现已启用
cdecl SHARED int MultiCore_old(char* caller, size_t threadnum, void* func, void* args, int *ret,
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

cdecl SHARED int MultiCore(char* caller, void* func, void* args, int *ret,
    uint8_t* in_buffer, uint8_t* out_buffer,
    size_t in_shape[])
{
    // 添加至队列
    size_t threads = ThreadPool.size();
    if (threads == 0){
        fprintf(stderr, "PlProcCore Error: On caller %s, No thread pool initialized. Please call InitThreadPool() first.\n", caller);
        return -114514;
    }
    for(size_t i = 0; i < threads; i++){
        TaskQueue.push({
            .threads = threads,
            .idx = i,
            .func = (MultiCoreFunc)func,
            .args = args,
            .in_shape = in_shape,
            .in_buffer = in_buffer,
            .out_buffer = out_buffer,
            .ret = ret
        });
        // printf("Run %s in thread %zu, total %zu\n", caller, i, threads);
    }
    // 唤醒并等待全部任务完成
    TaskQueueCV.notify_all();
    for(size_t i = 0; i < threads; i++){
        TaskQueueSemaphore.acquire();
    }
    return 0;
}

// 退出前的清理函数
cdecl SHARED void Exit(){
    ThreadPool_Running = false;
    TaskQueueCV.notify_all();
    for(auto& thread : ThreadPool){
        thread.join();
    }
    ThreadPool.clear();
}

// 判断是否有CUDA支持
