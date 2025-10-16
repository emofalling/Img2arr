#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <math.h>

#if defined(_WIN32) || defined(_WIN64)
#define SHARED __declspec(dllexport)
#else
#define SHARED __attribute__((visibility("default")))
#endif

SHARED const char img2arr_ext_sign[] = "img2arr.prep.img.Brightness";

enum{
    ATTR_NONE = 0, // 不指定任何属性。会为该函数分配独立的输出缓冲区。
    ATTR_REUSE = 1, // 能够复用输入缓冲区。若指定定了该参数，in_buf和out_buf可能指向同一块内存。
    ATTR_READONLY = 2, // 只读取，不输出(REUSE的进阶)。若指定了该参数，out_buf一定为NULL。
};

SHARED int io_GetOutInfo(void* args, size_t in_t, size_t in_h, size_t in_w, size_t* out_t, size_t* out_h, size_t* out_w, int* attr){
    *out_t = in_t;
    *out_w = in_w;
    *out_h = in_h;
    *attr = ATTR_REUSE;
    return 0;
}

#define SaturationAdd(x, val) ((x) < (255 - val)) ? ((x) + val) : 255
#define SaturationSub(x, val) ((x) > val) ? ((x) - val) : 0

// 单线程处理函数。对于img2arr.*.img.*（图像处理扩展类）来说，in_t始终为1，in_h和in_w分别对应图像的高度和宽度。
// 当in_reuse=True时，out_buf有时指向in_buf（但不总是），可以更好的利用处理器优化。
SHARED int f0(void* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_t, size_t in_h, size_t in_w){
    // args: uint8_t v[2], v[0]: +(0)/-(1), v[1]: value
    uint8_t *v = (uint8_t*)args;
    bool op = v[0];
    uint8_t val = v[1];
    bool opR = v[2];
    bool opG = v[3];
    bool opB = v[4];
    bool opA = v[5];

    const size_t total_size = in_t * in_h * in_w * 4;
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
    return 0;
}

// #include <stdio.h> // 仅调试用

SHARED int f1(size_t threads, size_t idx, void* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_t, size_t in_h, size_t in_w){
    uint8_t *v = (uint8_t*)args;
    bool op = v[0];
    uint8_t val = v[1];
    bool opR = v[2];
    bool opG = v[3];
    bool opB = v[4];
    bool opA = v[5];

    const size_t pixels = /*in_t * */in_h * in_w;
    // 计算自己要处理的索引范围
    const size_t start = (pixels * idx / threads) * 4;
    const size_t end = (pixels * (idx + 1) / threads) * 4;
    // printf("idx: %zu, start: %zu, end: %zu\n", idx, start, end);
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
        uint8_t max_val = 255 - val;
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