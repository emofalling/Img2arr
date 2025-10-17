#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <math.h>
#include <float.h>

#if defined(_WIN32) || defined(_WIN64)
#define SHARED __declspec(dllexport)
#else
#define SHARED __attribute__((visibility("default")))
#endif

#ifndef M_PI
#warning "Not found M_PI in math.h, using 3.141592653589793238462643"
#define M_PI 3.141592653589793238462643
#endif

SHARED const char img2arr_ext_sign[] = "img2arr.prep.img.Zoom";

enum{
    ATTR_NONE = 0, // 不指定任何属性。
    ATTR_REUSE = 1, // 能够复用输入缓冲区。若指定定了该参数，in_buf和out_buf可能指向同一块内存。
    ATTR_READONLY = 2, // 只读取，不输出(REUSE的进阶)。若指定了该参数，out_buf一定为NULL。
};

/*
[pack]struct{
    float sx; // x方向缩放比例
    float sy; // y方向缩放比例
    int enum{
        NEAREST = 0, // 最近邻插值
        BILINEAR = 1, // 双线性插值
        BICUBIC = 2, // 双三次插值
        LANCZOS = 3, // Lanczos插值
    };
}
*/

typedef enum {
    SCALE_NEAREST = 0,
    SCALE_BILINEAR = 1,
    SCALE_BICUBIC = 2,
    SCALE_LANCZOS = 3,
}scale_mode;

typedef struct {
    float sx, sy;
    scale_mode mode;
}__attribute__((packed)) args_t;

#define round5(x) ((x) + 0.5f)
#define clip(x, min, max) ((x) < (min) ? (min) : ((x) > (max) ? (max) : (x)))

SHARED int io_GetOutInfo(args_t* args, size_t in_shape[2], size_t out_shape[2], int* attr){
    out_shape[0] = round5(in_shape[0] * args->sy); // h
    out_shape[1] = round5(in_shape[1] * args->sx); // w
    // attr默认为none
    return 0;
}

int main_nearest(float scale_x, float scale_y, 
                       size_t in_w, size_t in_h, 
                       size_t out_w, size_t out_h, 
                       uint8_t* in_buf, uint8_t* out_buf, 
                       size_t start_p, size_t end_p) {
    // 参数说明：scale_x = in_w / out_w, scale_y = in_h / out_h
    
    for(size_t p = start_p; p < end_p; p++) {
        size_t x = p % out_w;
        size_t y = p / out_w;
        
        // 计算源坐标（四舍五入）并限制边界
        size_t in_x = round5(x / scale_x);
        size_t in_y = round5(y / scale_y);
        // in_x = (in_x < in_w) ? in_x : (in_w - 1);
        // in_y = (in_y < in_h) ? in_y : (in_h - 1);
        in_x = clip(in_x, 0, in_w - 1);
        in_y = clip(in_y, 0, in_h - 1);
        
        out_buf[p * 4 + 0] = in_buf[(in_y * in_w + in_x) * 4 + 0];
        out_buf[p * 4 + 1] = in_buf[(in_y * in_w + in_x) * 4 + 1];
        out_buf[p * 4 + 2] = in_buf[(in_y * in_w + in_x) * 4 + 2];
        out_buf[p * 4 + 3] = in_buf[(in_y * in_w + in_x) * 4 + 3];
    }
    return 0;
}

int main_bilinear(float scale_x, float scale_y,
                       size_t in_w, size_t in_h, 
                       size_t out_w, size_t out_h, 
                       uint8_t* in_buf, uint8_t* out_buf, 
                       size_t start_p, size_t end_p) {
    for(size_t p = start_p; p < end_p; p++) {
        size_t x = p % out_w;
        size_t y = p / out_w;

        // 计算源坐标（浮点数）
        float src_x = x / scale_x;
        float src_y = y / scale_y;
        
        // 获取四个相邻像素的坐标
        int x0 = (int)floorf(src_x);
        int y0 = (int)floorf(src_y);
        int x1 = x0 + 1;
        int y1 = y0 + 1;
        
        // 边界检查
        x0 = clip(x0, 0, in_w - 1);
        y0 = clip(y0, 0, in_h - 1);
        x1 = clip(x1, 0, in_w - 1);
        y1 = clip(y1, 0, in_h - 1);
        
        // 计算权重
        float dx = src_x - x0;
        float dy = src_y - y0;
        float w00 = (1 - dx) * (1 - dy);
        float w01 = (1 - dx) * dy;
        float w10 = dx * (1 - dy);
        float w11 = dx * dy;
        
        // 对每个通道进行双线性插值
        for(int c = 0; c < 4; c++) {
            // 获取四个相邻像素的值
            uint8_t p00 = in_buf[(y0 * in_w + x0) * 4 + c];
            uint8_t p01 = in_buf[(y1 * in_w + x0) * 4 + c];
            uint8_t p10 = in_buf[(y0 * in_w + x1) * 4 + c];
            uint8_t p11 = in_buf[(y1 * in_w + x1) * 4 + c];
            
            // 计算插值结果并四舍五入
            float result = w00 * p00 + w01 * p01 + w10 * p10 + w11 * p11;
            out_buf[p * 4 + c] = round5(result);
        }
    }
    return 0;
}

typedef float (*weight_func)(float);


int main_generel_convolution_scale(float scale_x, float scale_y,
                       size_t in_w, size_t in_h, 
                       size_t out_w, size_t out_h, 
                       uint8_t* in_buf, uint8_t* out_buf, 
                       size_t start_p, size_t end_p, weight_func core) {
    
    for(size_t p = start_p; p < end_p; p++) {
        size_t x = p % out_w;
        size_t y = p / out_w;

        // 计算浮点源坐标
        float src_x_float = x / scale_x;
        float src_y_float = y / scale_y;
        
        // 获取基准整数坐标
        int base_x = floorf(src_x_float);
        int base_y = floorf(src_y_float);
        
        for(int c = 0; c < 4; c++) {
            float sum = 0.0f;
            float weight_sum = 0.0f;
            // 遍历周围[-1~2][-1~2]共16个像素
            for(int i = -1; i <= 2; i++) {
                for(int j = -1; j <= 2; j++) {
                    int sample_x = base_x + i;
                    int sample_y = base_y + j;
                    
                    // 边界检查
                    sample_x = clip(sample_x, 0, in_w - 1);
                    sample_y = clip(sample_y, 0, in_h - 1);
                    
                    // 计算实际距离（关键修正！）
                    float dx = src_x_float - sample_x;
                    float dy = src_y_float - sample_y;
                    
                    // 使用实际距离计算权重
                    float weight = core(dx) * core(dy);
                    
                    uint8_t pixel = in_buf[(sample_y * in_w + sample_x) * 4 + c];
                    sum += weight * pixel;
                    weight_sum += weight;
                }
            }
            
            // 归一化并限制范围
            float result = sum / weight_sum;
            result = clip(result, 0.0f, 255.0f);
            out_buf[p * 4 + c] = round5(result);

        }
    }
    return 0;
}

// 双三次插值核函数（Catmull-Rom 样条）
static float cubic_weight(float x) {
    x = fabsf(x);
    if (x < 1.0f) {
        return 1.5f * x * x * x - 2.5f * x * x + 1.0f;
    } else if (x < 2.0f) {
        return -0.5f * x * x * x + 2.5f * x * x - 4.0f * x + 2.0f;
    } else {
        return 0.0f;
    }
}

// Lanzcos插值核函数(a = 3)
static float lanzcos_weight(float x) {
    x = fabsf(x);
    float a = 3.0f;
    if(x < 1e-6f){
        return 1.0f;
    }else if(x < a){        
        float pi_x = M_PI * x;
        float pi_x_a = M_PI * x / a;
        return (sinf(pi_x) * sinf(pi_x_a)) / (pi_x * pi_x_a) * a;
    }else{
        return 0.0f;
    }

}

static int main_enum(scale_mode mode, float scale_x, float scale_y, size_t in_w, size_t in_h, size_t out_x, size_t out_y, uint8_t* in_buf, uint8_t* out_buf, size_t start_p, size_t end_p){
    switch(mode){
        case SCALE_NEAREST:
            main_nearest(scale_x, scale_y, in_w, in_h, out_x, out_y, in_buf, out_buf, start_p, end_p);
            break;
        case SCALE_BILINEAR:
            main_bilinear(scale_x, scale_y, in_w, in_h, out_x, out_y, in_buf, out_buf, start_p, end_p);
            break;
        case SCALE_BICUBIC:
            main_generel_convolution_scale(scale_x, scale_y, in_w, in_h, out_x, out_y, in_buf, out_buf, start_p, end_p, cubic_weight);
            break;
        case SCALE_LANCZOS:
            main_generel_convolution_scale(scale_x, scale_y, in_w, in_h, out_x, out_y, in_buf, out_buf, start_p, end_p, lanzcos_weight);
        default:
            return -1;
    }
    return 0;
}

SHARED int f1(size_t threads, size_t idx, args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]){
    const size_t out_x = round5(in_shape[1] * args->sx);
    const size_t out_y = round5(in_shape[0] * args->sy);

    const size_t pixels = 1 * out_x * out_y;
    const size_t start_p = pixels * idx / threads;
    const size_t end_p = pixels * (idx + 1) / threads;

    main_enum(args->mode, args->sx, args->sy, in_shape[1], in_shape[0], out_x, out_y, in_buf, out_buf, start_p, end_p);


    return 0;
}

SHARED int f0(args_t* args, uint8_t *in_buf, uint8_t *out_buf, size_t in_shape[2]){
    // 单线程缩放
    const size_t out_x = round5(in_shape[1] * args->sx);
    const size_t out_y = round5(in_shape[0] * args->sy);

    main_enum(args->mode, args->sx, args->sy, in_shape[1], in_shape[0], out_x, out_y, in_buf, out_buf, 0, out_x * out_y);

    return 0;
}