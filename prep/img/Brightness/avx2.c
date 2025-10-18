#include <immintrin.h> // AVX2

#include "main.h"

int f1_avx2(size_t threads, size_t idx, args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]) {

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
    const __m256i val_vec = _mm256_set1_epi8(val);
    
    // 创建通道掩码 (RGBA 顺序)
    const uint8_t mask_r = opR ? 0xFF : 0x00;
    const uint8_t mask_g = opG ? 0xFF : 0x00;
    const uint8_t mask_b = opB ? 0xFF : 0x00;
    const uint8_t mask_a = opA ? 0xFF : 0x00;
    
    // 创建掩码向量：每个32位像素的掩码模式 [A, B, G, R]
    const __m256i channel_mask = _mm256_setr_epi8(
        mask_r, mask_g, mask_b, mask_a,  // 像素0
        mask_r, mask_g, mask_b, mask_a,  // 像素1
        mask_r, mask_g, mask_b, mask_a,  // 像素2
        mask_r, mask_g, mask_b, mask_a,  // 像素3
        mask_r, mask_g, mask_b, mask_a,  // 像素4
        mask_r, mask_g, mask_b, mask_a,  // 像素5
        mask_r, mask_g, mask_b, mask_a,  // 像素6
        mask_r, mask_g, mask_b, mask_a   // 像素7
    );

    size_t p = start;
    
    if (op) {  // 饱和减法
        // AVX2 主循环：每次处理 32 字节 (8个像素)
        for (; p + 32 <= end; p += 32) {
            __m256i input = _mm256_loadu_si256((__m256i*)(in_buf + p));
            
            // 执行饱和减法
            __m256i saturated_result = _mm256_subs_epu8(input, val_vec);
            
            // 根据通道掩码混合结果：需要处理的通道用饱和结果，不需要的用原始输入
            __m256i result = _mm256_blendv_epi8(input, saturated_result, channel_mask);
            
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
        // AVX2 主循环：每次处理 32 字节 (8个像素)
        for (; p + 32 <= end; p += 32) {
            __m256i input = _mm256_loadu_si256((__m256i*)(in_buf + p));
            
            // 执行饱和加法
            __m256i saturated_result = _mm256_adds_epu8(input, val_vec);
            
            // 根据通道掩码混合结果
            __m256i result = _mm256_blendv_epi8(input, saturated_result, channel_mask);
            
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

int f0_avx2(args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]){
    return f1_avx2(1, 0, args, in_buf, out_buf, in_shape);
}