#include <immintrin.h> // AVX512

#include "main.h"

int f1_avx512(size_t threads, size_t idx, args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]) {

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
    const __m512i val_vec = _mm512_set1_epi8(val);
    
    // 创建通道掩码 (RGBA 顺序)
    // 为每个通道创建单独的掩码，然后组合
    const uint8_t mask_r = opR ? 0xFF : 0x00;
    const uint8_t mask_g = opG ? 0xFF : 0x00;
    const uint8_t mask_b = opB ? 0xFF : 0x00;
    const uint8_t mask_a = opA ? 0xFF : 0x00;
    
    // 创建 64 位的掩码（每个字节对应一个掩码位）
    // 模式：[R, G, B, A] 重复 16 次（对应 16 个像素）
    __mmask64 channel_mask = 0;
    for (int i = 0; i < 16; i++) {
        channel_mask |= ((__mmask64)mask_r << (i * 4 + 0));
        channel_mask |= ((__mmask64)mask_g << (i * 4 + 1));
        channel_mask |= ((__mmask64)mask_b << (i * 4 + 2));
        channel_mask |= ((__mmask64)mask_a << (i * 4 + 3));
    }

    size_t p = start;
    
    if (op) {  // 饱和减法
        // AVX512 主循环：每次处理 64 字节 (16个像素)
        for (; p + 64 <= end; p += 64) {
            __m512i input = _mm512_loadu_si512((__m512i*)(in_buf + p));
            
            // 执行饱和减法
            __m512i saturated_result = _mm512_subs_epu8(input, val_vec);
            
            // 根据通道掩码混合结果
            __m512i result = _mm512_mask_blend_epi8(channel_mask, input, saturated_result);
            
            _mm512_storeu_si512((__m512i*)(out_buf + p), result);
        }
        
        // 处理剩余不足64字节的部分（使用 AVX2 处理）
        for (; p + 32 <= end; p += 32) {
            __m256i input = _mm256_loadu_si256((__m256i*)(in_buf + p));
            __m256i val_vec256 = _mm256_set1_epi8(val);
            
            // 创建 AVX2 版本的掩码
            const __m256i channel_mask256 = _mm256_setr_epi8(
                mask_r, mask_g, mask_b, mask_a,
                mask_r, mask_g, mask_b, mask_a,
                mask_r, mask_g, mask_b, mask_a,
                mask_r, mask_g, mask_b, mask_a,
                mask_r, mask_g, mask_b, mask_a,
                mask_r, mask_g, mask_b, mask_a,
                mask_r, mask_g, mask_b, mask_a,
                mask_r, mask_g, mask_b, mask_a
            );
            
            // 执行饱和减法
            __m256i saturated_result = _mm256_subs_epu8(input, val_vec256);
            
            // 混合结果
            __m256i result = _mm256_blendv_epi8(input, saturated_result, channel_mask256);
            
            _mm256_storeu_si256((__m256i*)(out_buf + p), result);
        }
        
        // 处理剩余不足32字节的部分（使用标量处理）
        for (; p < end; p += 4) {
            out_buf[p + 0] = opR ? SaturationSub(in_buf[p + 0], val) : in_buf[p + 0];
            out_buf[p + 1] = opG ? SaturationSub(in_buf[p + 1], val) : in_buf[p + 1];
            out_buf[p + 2] = opB ? SaturationSub(in_buf[p + 2], val) : in_buf[p + 2];
            out_buf[p + 3] = opA ? SaturationSub(in_buf[p + 3], val) : in_buf[p + 3];
        }
    } else {  // 饱和加法
        // AVX512 主循环：每次处理 64 字节 (16个像素)
        for (; p + 64 <= end; p += 64) {
            __m512i input = _mm512_loadu_si512((__m512i*)(in_buf + p));
            
            // 执行饱和加法
            __m512i saturated_result = _mm512_adds_epu8(input, val_vec);
            
            // 根据通道掩码混合结果
            __m512i result = _mm512_mask_blend_epi8(channel_mask, input, saturated_result);
            
            _mm512_storeu_si512((__m512i*)(out_buf + p), result);
        }
        
        // 处理剩余不足64字节的部分（使用 AVX2 处理）
        for (; p + 32 <= end; p += 32) {
            __m256i input = _mm256_loadu_si256((__m256i*)(in_buf + p));
            __m256i val_vec256 = _mm256_set1_epi8(val);
            
            // 创建 AVX2 版本的掩码
            const __m256i channel_mask256 = _mm256_setr_epi8(
                mask_r, mask_g, mask_b, mask_a,
                mask_r, mask_g, mask_b, mask_a,
                mask_r, mask_g, mask_b, mask_a,
                mask_r, mask_g, mask_b, mask_a,
                mask_r, mask_g, mask_b, mask_a,
                mask_r, mask_g, mask_b, mask_a,
                mask_r, mask_g, mask_b, mask_a,
                mask_r, mask_g, mask_b, mask_a
            );
            
            // 执行饱和加法
            __m256i saturated_result = _mm256_adds_epu8(input, val_vec256);
            
            // 混合结果
            __m256i result = _mm256_blendv_epi8(input, saturated_result, channel_mask256);
            
            _mm256_storeu_si256((__m256i*)(out_buf + p), result);
        }
        
        // 处理剩余不足32字节的部分
        for (; p < end; p += 4) {
            out_buf[p + 0] = opR ? SaturationAdd(in_buf[p + 0], val) : in_buf[p + 0];
            out_buf[p + 1] = opG ? SaturationAdd(in_buf[p + 1], val) : in_buf[p + 1];
            out_buf[p + 2] = opB ? SaturationAdd(in_buf[p + 2], val) : in_buf[p + 2];
            out_buf[p + 3] = opA ? SaturationAdd(in_buf[p + 3], val) : in_buf[p + 3];
        }
    }
    
    return 0;
}

int f0_avx512(args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]){
    return f1_avx512(1, 0, args, in_buf, out_buf, in_shape);
}