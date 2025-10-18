#pragma once

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

typedef struct {
    // 0:+, 1:-
    bool op;
    uint8_t val;
    bool opR;
    bool opG;
    bool opB;
    bool opA;
}__attribute__((packed)) args_t;

typedef int (*f0_func_t)(args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]);
typedef int (*f1_func_t)(size_t threads, size_t idx, args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]);

int f0_avx512(args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]);
int f0_avx2(args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]);
int f0_sse2(args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]);
int f1_avx512(size_t threads, size_t idx, args_t * args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]);
int f1_avx2(size_t threads, size_t idx, args_t * args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]);
int f1_sse2(size_t threads, size_t idx, args_t * args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]);


// 非扩展指令集实现的饱和加法
#define SaturationAdd(x, val) ((x) < (255 - val)) ? ((x) + val) : 255
// 非扩展指令集实现的饱和减法
#define SaturationSub(x, val) ((x) > val) ? ((x) - val) : 0

