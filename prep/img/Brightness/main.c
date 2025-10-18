#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>


#include "main.h"

// ====================
// WARNING: Use AVX-512 must be compiled with -DSUPPORT_AVX512
// ====================

// SHARED: 表示这个函数是导出函数
// SHARED: This function is exported
#if defined(_WIN32) || defined(_WIN64)
#define SHARED __declspec(dllexport)
#else
#define SHARED __attribute__((visibility("default")))
#endif

// 签名: 验证扩展是否加载正确
// Sign: Verify that the extension is loaded correctly
SHARED const char img2arr_ext_sign[] = "img2arr.prep.img.Brightness";

// ext.py传入的参数解析结构体。可以作为处理结果输出。
// The parameter parsing structure passed in by ext.py. It can be used as the output of the processing result.

static int f0_default(args_t * args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]);
static int f1_default(size_t threads, size_t idx, args_t * args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]);
f0_func_t f0_func = f0_default; // 扩展函数指针。默认值为f0（最原始的实现）。
f1_func_t f1_func = f1_default; // 扩展函数指针。默认值为f1（最原始的实现）。

#include <stdio.h>

/**
 * @brief 初始化函数。当扩展被加载时，会被调用一次，在重新加载前不会再次调用。
 * This function is called once when the extension is loaded, and it will not be called again before reloading.
 * @return 错误码，0表示成功，非0表示失败。若函数无返回，则默认返回0。
 * Error code, 0 means success, non-0 means failure. If the function has no return, it defaults to return 0.
 */
SHARED int init(void){
    __builtin_cpu_init(); // 初始化CPU检测
    // 优先使用AVX-2指令集
    if(__builtin_cpu_supports("avx2")){// 使用AVX-2实现
        f0_func = f0_avx2;
        f1_func = f1_avx2;
        printf("Using AVX2\n");
    }
    else if(__builtin_cpu_supports("sse2")){// 使用SSE2实现
        f0_func = f0_sse2;
        f1_func = f1_sse2;
    }
    // 否则，使用原始实现
    return 0;
}

// 扩展属性enum。用于为管线进行特化提示，以进行优化。
// Extension attribute enum. Used to specialize the pipeline for optimization.
enum ExtAttr{
    /*
        没有任何额外属性，这会确保函数接收到的输入缓冲区和输出缓冲区始终不同。
        No additional attributes, this ensures that the input and output buffers received by the function are always different.
    */
    ATTR_NONE = 0,
    /*
        可以重用输入缓冲区，函数接收到的输入缓冲区和输出缓冲区有可能相同。
        The input buffer can be reused, and the input and output buffers received by the function may be the same.
    */
    ATTR_REUSE = 1,
    /*
        只读扩展。保证函数的输出缓冲区是NULL。
        Read-only extension. Ensure that the output buffer of the function is NULL.
    */
    ATTR_READONLY = 2

};


/**
 * @brief 获取输出数据信息。在调用`f0`或`f1`之前会被调用以确认输出缓冲区大小及其属性.
 * Get output data information. It will be called before calling `f0` or `f1` to confirm the size and attributes of the output buffer.
 * @param args[in/out] 参数解析结构体。
 * Parameter parsing structure.
 * @param in_shape[in] 输入缓冲区形状。对于`img`类扩展，其值为[height, width].
 * For `img` class extensions, its value is [height, width].
 * @param out_shape[out] 输出缓冲区形状。对于`img`类扩展，其值为[height, width].
 * For `img` class extensions, its value is [height, width].
 * @param attr[out] 扩展属性，应是`ExtAttr`中的某个值。用于为管线进行特化提示，以进行优化。若不赋值，则默认为`ATTR_NONE`。
 * Extension attribute, should be a value in `ExtAttr`. Used to specialize the pipeline for optimization. If not assigned, the default is `ATTR_NONE`.
 * @return 错误码，0表示成功，非0表示失败。若函数无返回，则默认返回0。
 * Error code, 0 means success, non-0 means failure. If the function has no return, it defaults to return 0.
 */
SHARED int io_GetOutInfo(void* args, size_t in_shape[2], size_t out_shape[2], int* attr){
    out_shape[0] = in_shape[0]; // h
    out_shape[1] = in_shape[1]; // w
    *attr = ATTR_REUSE;
    return 0;
}

/**
 * @brief 单线程实现。
 * Single-threaded implementation.
 * @param args[in/out] 参数解析结构体。
 * Parameter parsing structure.
 * @param in_buf[in] 输入缓冲区，格式为`[*in_shape, 4]`。
 * Input buffer, format is `[*in_shape, 4]`.
 * @param out_buf[out] 输出缓冲区。大小由`io_GetOutInfo`指定。
 * Output buffer. The size is specified by `io_GetOutInfo`.
 * @param in_shape[in] 输入缓冲区形状。对于`img`类扩展，其值为[height, width].
 * For `img` class extensions, its value is [height, width].
 * @return 错误码，0表示成功，非0表示失败。若函数无返回，则默认返回0。
 * Error code, 0 means success, non-0 means failure. If the function has no return, it defaults to return 0.
 */
SHARED int f0(args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]){
    return f0_func(args, in_buf, out_buf, in_shape);
}

static int f0_default(args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]){
    bool op = args->op;
    uint8_t val = args->val;
    bool opR = args->opR;
    bool opG = args->opG;
    bool opB = args->opB;
    bool opA = args->opA;

    const size_t total_size = in_shape[0] * in_shape[1] * 4;
    if(op){  // -
        for(size_t p = 0; p < total_size; p+=4){
            /* (x > val) ? (x - val) : 0 */
            out_buf[p + 0] = opR ? SaturationSub(in_buf[p + 0], val) : in_buf[p + 0];
            out_buf[p + 1] = opG ? SaturationSub(in_buf[p + 1], val) : in_buf[p + 1];
            out_buf[p + 2] = opB ? SaturationSub(in_buf[p + 2], val) : in_buf[p + 2];
            out_buf[p + 3] = opA ? SaturationSub(in_buf[p + 3], val) : in_buf[p + 3];
        }
    }else{  // +
        for(size_t p = 0; p < total_size; p+=4){
            /* (x < max_val) ? (x + val) : 255 */
            out_buf[p + 0] = opR ? SaturationAdd(in_buf[p + 0], val) : in_buf[p + 0];
            out_buf[p + 1] = opG ? SaturationAdd(in_buf[p + 1], val) : in_buf[p + 1];
            out_buf[p + 2] = opB ? SaturationAdd(in_buf[p + 2], val) : in_buf[p + 2];
            out_buf[p + 3] = opA ? SaturationAdd(in_buf[p + 3], val) : in_buf[p + 3];
        }
    }
}

/**
 * @brief 多线程实现。
 * Multi-threaded implementation.
 * @param threads[in] 任务数。
 * Number of tasks.
 * @param idx[in] 任务索引。
 * Task index.
 * @param args[in/out] 参数解析结构体。
 * Parameter parsing structure.
 * @param in_buf[in] 输入缓冲区，格式为`[*in_shape, 4]`。
 * Input buffer, format is `[*in_shape, 4]`.
 * @param out_buf[out] 输出缓冲区。大小由`io_GetOutInfo`指定。
 * Output buffer. The size is specified by `io_GetOutInfo`.
 * @param in_shape[in] 输入缓冲区形状。对于`img`类扩展，其值为[height, width].
 * For `img` class extensions, its value is [height, width].
 * @return 错误码，0表示成功，非0表示失败。若函数无返回，则默认返回0。
 * Error code, 0 means success, non-0 means failure. If the function has no return, it defaults to return 0.
 */
SHARED int f1(size_t threads, size_t idx, args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]){
    return f1_func(threads, idx, args, in_buf, out_buf, in_shape);
}

static int f1_default(size_t threads, size_t idx, args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]){
    bool op = args->op;
    uint8_t val = args->val;
    bool opR = args->opR;
    bool opG = args->opG;
    bool opB = args->opB;
    bool opA = args->opA;

    const size_t pixels = in_shape[0] * in_shape[1];
    // 计算自己要处理的索引范围
    const size_t start = (pixels * idx / threads) * 4;
    const size_t end = (pixels * (idx + 1) / threads) * 4;

    // 开算
    
    if(op){  // -
        for(size_t p = start; p < end; p+=4){
            /* (x > val) ? (x - val) : 0 */
            out_buf[p + 0] = opR ? SaturationSub(in_buf[p + 0], val) : in_buf[p + 0];
            out_buf[p + 1] = opG ? SaturationSub(in_buf[p + 1], val) : in_buf[p + 1];
            out_buf[p + 2] = opB ? SaturationSub(in_buf[p + 2], val) : in_buf[p + 2];
            out_buf[p + 3] = opA ? SaturationSub(in_buf[p + 3], val) : in_buf[p + 3];
        }
    }else{  // +
        for(size_t p = start; p < end; p+=4){
            /* (x < max_val) ? (x + val) : 255 */
            out_buf[p + 0] = opR ? SaturationAdd(in_buf[p + 0], val) : in_buf[p + 0];
            out_buf[p + 1] = opG ? SaturationAdd(in_buf[p + 1], val) : in_buf[p + 1];
            out_buf[p + 2] = opB ? SaturationAdd(in_buf[p + 2], val) : in_buf[p + 2];
            out_buf[p + 3] = opA ? SaturationAdd(in_buf[p + 3], val) : in_buf[p + 3];
        }
    }


    return 0;
}

