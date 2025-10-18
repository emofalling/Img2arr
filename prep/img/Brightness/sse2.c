#include <emmintrin.h> // SSE2+

#include "main.h"

int f1_sse2(size_t threads, size_t idx, args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]) {

    bool op = args->op;
    uint8_t val = args->val;
    bool opR = args->opR;
    bool opG = args->opG;
    bool opB = args->opB;
    bool opA = args->opA;

    const size_t pixels = in_shape[0] * in_shape[1];
    const size_t start = (pixels * idx / threads) * 4;
    const size_t end = (pixels * (idx + 1) / threads) * 4;

    // 创建常量向量
    const __m128i val_vec = _mm_set1_epi8(val);
    
    // 创建通道掩码 (RGBA 顺序)
    const uint8_t mask_r = opR ? 0xFF : 0x00;
    const uint8_t mask_g = opG ? 0xFF : 0x00;
    const uint8_t mask_b = opB ? 0xFF : 0x00;
    const uint8_t mask_a = opA ? 0xFF : 0x00;
    
    // SSE2 没有 blendv_epi8，使用位运算模拟混合操作
    const __m128i channel_mask = _mm_setr_epi8(
        mask_r, mask_g, mask_b, mask_a,  // 像素0
        mask_r, mask_g, mask_b, mask_a,  // 像素1
        mask_r, mask_g, mask_b, mask_a,  // 像素2
        mask_r, mask_g, mask_b, mask_a   // 像素3
    );

    size_t p = start;
    
    if (op) {  // 饱和减法
        // SSE2 主循环：每次处理 16 字节 (4个像素)
        for (; p + 16 <= end; p += 16) {
            __m128i input = _mm_loadu_si128((__m128i*)(in_buf + p));
            
            // 执行饱和减法
            __m128i saturated_result = _mm_subs_epu8(input, val_vec);
            
            // SSE2 没有 blendv，使用位运算实现混合：
            // result = (input & ~mask) | (saturated_result & mask)
            __m128i result = _mm_or_si128(
                _mm_andnot_si128(channel_mask, input),
                _mm_and_si128(channel_mask, saturated_result)
            );
            
            _mm_storeu_si128((__m128i*)(out_buf + p), result);
        }
        
        // 处理剩余不足16字节的部分（使用标量处理）
        for (; p < end; p += 4) {
            out_buf[p + 0] = opR ? SaturationSub(in_buf[p + 0], val) : in_buf[p + 0];
            out_buf[p + 1] = opG ? SaturationSub(in_buf[p + 1], val) : in_buf[p + 1];
            out_buf[p + 2] = opB ? SaturationSub(in_buf[p + 2], val) : in_buf[p + 2];
            out_buf[p + 3] = opA ? SaturationSub(in_buf[p + 3], val) : in_buf[p + 3];
        }
    } else {  // 饱和加法
        // SSE2 主循环：每次处理 16 字节 (4个像素)
        for (; p + 16 <= end; p += 16) {
            __m128i input = _mm_loadu_si128((__m128i*)(in_buf + p));
            
            // 执行饱和加法
            __m128i saturated_result = _mm_adds_epu8(input, val_vec);
            
            // 使用位运算实现混合
            __m128i result = _mm_or_si128(
                _mm_andnot_si128(channel_mask, input),
                _mm_and_si128(channel_mask, saturated_result)
            );
            
            _mm_storeu_si128((__m128i*)(out_buf + p), result);
        }
        
        // 处理剩余不足16字节的部分
        for (; p < end; p += 4) {
            out_buf[p + 0] = opR ? SaturationAdd(in_buf[p + 0], val) : in_buf[p + 0];
            out_buf[p + 1] = opG ? SaturationAdd(in_buf[p + 1], val) : in_buf[p + 1];
            out_buf[p + 2] = opB ? SaturationAdd(in_buf[p + 2], val) : in_buf[p + 2];
            out_buf[p + 3] = opA ? SaturationAdd(in_buf[p + 3], val) : in_buf[p + 3];
        }
    }
    

    return 0;
}


int f0_sse2(args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]){
    return f1_sse2(1, 0, args, in_buf, out_buf, in_shape);
}