#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
#include <stdatomic.h>

#if defined(_WIN32) || defined(_WIN64)
#define SHARED __declspec(dllexport)
#else
#define SHARED __attribute__((visibility("default")))
#endif

#ifndef likely
#ifdef __GNUC__
#define likely(x)   __builtin_expect(!!(x), 1)
#define unlikely(x) __builtin_expect(!!(x), 0)
#else
#define likely(x)   (x)
#define unlikely(x) (x)
#endif
#endif

SHARED const char img2arr_ext_sign[] = "img2arr.prep.img.Histogram";

enum{
    ATTR_NONE = 0, // 不指定任何属性。会为该函数分配独立的输出缓冲区。
    ATTR_REUSE = 1, // 能够复用输入缓冲区。若指定定了该参数，in_buf和out_buf可能指向同一块内存。
    ATTR_READONLY = 2, // 只读取，不输出(REUSE的进阶)。若指定了该参数，out_buf一定为NULL。
};

SHARED int io_GetOutInfo(void* args, size_t in_t, size_t in_h, size_t in_w, size_t* out_t, size_t* out_h, size_t* out_w, int* attr){
    *out_t = in_t;
    *out_w = in_w;
    *out_h = in_h;
    *attr = ATTR_READONLY;
    return 0;
}

// 图像图表
typedef struct{
    uint64_t *R; // 直方图求和结果：R
    uint64_t *G; // 直方图求和结果：G
    uint64_t *B; // 直方图求和结果：B
    uint64_t *A; // 直方图求和结果：A
}__attribute__((packed)) args_f0_t;

typedef struct{
    uint64_t *R; // 每个任务的直方图求和结果：R， 256为一间隔
    uint64_t *G; // 每个任务的直方图求和结果：G， 256为一间隔
    uint64_t *B; // 每个任务的直方图求和结果：B， 256为一间隔
    uint64_t *A; // 每个任务的直方图求和结果：A， 256为一间隔
}__attribute__((packed)) args_f1_t;

// 单线程处理函数。对于img2arr.*.img.*（图像处理扩展类）来说，in_t始终为1，in_h和in_w分别对应图像的高度和宽度。
// 当in_reuse=True时，out_buf有时指向in_buf（但不总是），可以更好的利用处理器优化。
SHARED int f0(args_f0_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_t, size_t in_h, size_t in_w){
    // args: uint8_t v[2], v[0]: +(0)/-(1), v[1]: value
    size_t size = in_t * in_h * in_w;
    uint64_t R[256] = {0}, 
             G[256] = {0}, 
             B[256] = {0}, 
             A[256] = {0};
    for(size_t i = 0; i < size * 4; i += 4){
        uint8_t a = in_buf[i + 3];
        if(likely(a)){
            R[in_buf[i + 0]]++;
            G[in_buf[i + 1]]++;
            B[in_buf[i + 2]]++;
        }
        A[a]++;
    }
    // 复制到args
    // for(size_t i = 0; i < 256; i++){
    //     args->R[i] = R[i];
    //     args->G[i] = G[i];
    //     args->B[i] = B[i];
    //     args->A[i] = A[i];
    // }
    memcpy(args->R, R, sizeof(R));
    memcpy(args->G, G, sizeof(G));
    memcpy(args->B, B, sizeof(B));
    memcpy(args->A, A, sizeof(A));
    return 0;
}

// #include <stdio.h> // 仅调试用

SHARED int f1(size_t threads, size_t idx, args_f1_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_t, size_t in_h, size_t in_w){
    size_t size = in_t * in_h * in_w;
    size_t start_i = (size * idx / threads) * 4;
    size_t end_i = (size * (idx + 1) / threads) * 4;
    uint64_t R[256] = {0}, 
             G[256] = {0}, 
             B[256] = {0}, 
             A[256] = {0};
    for(size_t i = start_i; i < end_i; i += 4){
        uint8_t a = in_buf[i + 3];
        if(likely(a)){
            R[in_buf[i + 0]]++;
            G[in_buf[i + 1]]++;
            B[in_buf[i + 2]]++;
        }
        A[a]++;
    }
    // 复制到args
    // for(size_t i = 0; i < 256; i++){
    //     args->R[256 * idx + i] = R[i];
    //     args->G[256 * idx + i] = G[i];
    //     args->B[256 * idx + i] = B[i];
    //     args->A[256 * idx + i] = A[i];
    // }
    memcpy(args->R + 256 * idx, R, sizeof(R));
    memcpy(args->G + 256 * idx, G, sizeof(G));
    memcpy(args->B + 256 * idx, B, sizeof(B));
    memcpy(args->A + 256 * idx, A, sizeof(A));
    return 0;
}