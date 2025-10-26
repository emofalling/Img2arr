#include <cuda.h>
#include <cuda_runtime.h>

// compile: nvcc NVCUDAhome.cu -shared -o NVCUDAhome.dll -O3 -lcuda -lcudart (-Xcompiler "/source-charset:utf-8")(for Windows)

#if defined(_WIN32) || defined(_WIN64)
#define SHARED __declspec(dllexport)
#else
#define SHARED __attributes__((visibility("default")))
#endif

#include <stdbool.h>

typedef unsigned int uint;

#if defined(__cplusplus)
extern "C" {
#endif

inline SHARED CUresult api_cuInit(uint Flags){
    return cuInit(Flags);
}

inline SHARED CUresult api_cuDeviceGetCount(int *count){
    return cuDeviceGetCount(count);
}

inline SHARED CUresult api_cuDeviceGet(CUdevice *device, uint ordinal){
    return cuDeviceGet(device, ordinal);
}

inline SHARED CUresult api_cuDeviceGetName(char *name, int len, CUdevice dev){
    return cuDeviceGetName(name, len, dev);
}

inline SHARED CUresult api_cuDeviceGetAttribute(int *pi, CUdevice_attribute attrib, CUdevice dev){
    return cuDeviceGetAttribute(pi, attrib, dev);
}

// 初始化上下文
inline SHARED CUresult api_cuCtxCreate(CUcontext *pctx, uint flags, CUdevice dev){
    return cuCtxCreate(pctx, flags, dev);
}

// 销毁上下文
inline SHARED CUresult api_cuCtxDestroy(CUcontext ctx){
    return cuCtxDestroy(ctx);
}


/*
module: 模块句柄
image: 二进制文件数据（ptx cubin fatbin均可）
numOptions: 选项数量
*/
inline SHARED CUresult api_cuModuleLoadDataEx(CUmodule *module, const void *image, uint numOptions, CUjit_option *options, void **optionValues){
    return cuModuleLoadDataEx(module, image, numOptions, options, optionValues);
}

// 卸载模块
inline SHARED CUresult api_cuModuleUnload(CUmodule module){
    return cuModuleUnload(module);
}

// 取函数
inline SHARED CUresult api_cuModuleGetFunction(CUfunction *hfunc, CUmodule hmod, const char *name){
    return cuModuleGetFunction(hfunc, hmod, name);
}

// 分配内存
inline SHARED cudaError_t api_cudaMalloc(void **dptr, size_t size){
    return cudaMalloc(dptr, size);
}

// 分配内存（主机）。相比malloc，这个函数分配的内存是不分页的，能够有效地使用cudaMemcpyAsync复制
inline SHARED cudaError_t api_cudaMallocHost(void **ptr, size_t size){
    return cudaMallocHost(ptr, size);
}

// 清理内存
inline SHARED cudaError_t api_cudaFree(void *dptr){
    return cudaFree(dptr);
}

// 启动！
inline SHARED CUresult api_cuLaunchKernel(CUfunction f, uint gridDimX, uint gridDimY, uint gridDimZ, uint blockDimX, uint blockDimY, uint blockDimZ, uint sharedMemBytes, CUstream hStream, void **kernelParams, void **extra){
    return cuLaunchKernel(f, gridDimX, gridDimY, gridDimZ, blockDimX, blockDimY, blockDimZ, sharedMemBytes, hStream, kernelParams, extra);
}

// 等待整个上下文完成
inline SHARED CUresult api_cuCtxSynchronize(){
    return cuCtxSynchronize();
}

// 等待某个流完成
inline SHARED CUresult api_cuStreamSynchronize(CUstream stream){
    return cuStreamSynchronize(stream);
}

// 串行复制内存。kind指定了复制的方向
SHARED cudaError_t api_cudaMemcpy(void* dst, const void* src, size_t count, cudaMemcpyKind kind) {
    return cudaMemcpy(dst, src, count, kind);
}

// 异步复制内存。kind指定了复制的方向
SHARED cudaError_t api_cudaMemcpyAsync(void* dst, const void* src, size_t count, cudaMemcpyKind kind, cudaStream_t stream) {
    return cudaMemcpyAsync(dst, src, count, kind, stream);
}

// 创建流
SHARED cudaError_t api_cudaStreamCreate(cudaStream_t *pStream) {
    return cudaStreamCreate(pStream);
}

// 销毁流
SHARED cudaError_t api_cudaStreamDestroy(cudaStream_t stream) {
    return cudaStreamDestroy(stream);
}

SHARED const char* api_cudaGetErrorString(cudaError_t error) {
    return cudaGetErrorString(error);
}

#if defined(__cplusplus)
}
#endif