#include <stdint.h>
#include <stdlib.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdatomic.h>
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

#ifdef __GNUC__
#define likely(x)   __builtin_expect(!!(x), 1)
#define unlikely(x) __builtin_expect(!!(x), 0)
#else
#define likely(x)   (x)
#define unlikely(x) (x)
#endif

#define max(a, b) ((a) > (b) ? (a) : (b))
#define min(a, b) ((a) < (b) ? (a) : (b))

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
    bool lut_optimize; // 是否启用LUT优化。这能够大幅提升性能，但需要一丢丢内存。
}
*/

SHARED atomic_size_t* atomic_init_size_t(atomic_size_t* p, size_t v){
    atomic_init(p, v);
    return p;
}

typedef enum {
    SCALE_NEAREST = 0,
    SCALE_BILINEAR = 1,
    SCALE_BICUBIC = 2,
    SCALE_LANCZOS = 3,
}scale_mode;

typedef struct {
    float sx, sy;
    scale_mode mode;
    int core_left; // 卷积核左边界，通常是负数。仅对于使用自定义卷积缩放的算法有效。
    int core_right; // 卷积核右边界，通常是正数。仅对于使用自定义卷积缩放的算法有效。
    int core_top; // 卷积核上边界，通常是负数。仅对于使用自定义卷积缩放的算法有效。
    int core_bottom; // 卷积核下边界，通常是正数。仅对于使用自定义卷积缩放的算法有效。
    bool lut_optimize;
    float *lut_x_buffer;
    float *lut_y_buffer;
    atomic_size_t* thread_lock;
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
            
            // 计算平均值并四舍五入
            float result = w00 * p00 + w01 * p01 + w10 * p10 + w11 * p11;
            out_buf[p * 4 + c] = round5(result);
        }
    }
    return 0;
}

typedef float (*weight_func)(float dis, int left, int right);

static inline float cubic_weight(float dis, int left, int right) {
    dis = fabsf(dis);
    float a = -0.75f;
    if(unlikely(dis == 0.0f)){
        return 1.0f;
    }
    if(dis < 1.0f){
        // (a+2)x^3 - (a+3)x^2 + 1
        return (a + 2.0f) * dis * dis * dis - (a + 3.0f) * dis * dis + 1.0f;
    }
    if(dis < 2.0f){
        // ax^3 - 5ax^2 + 8ax - 4a
        return a * dis * dis * dis - 5.0f * a * dis * dis + 8.0f * a * dis - 4.0f * a;
    }
    return 0.0f;
}
static inline float sinc(float x) {
    x = M_PI * x;
    /*
    if (x < 1e-6f) {
        return 1.0f;
    } else {
        return sinf(x) / x;
    }
    */
   return sinf(x) / x;
}
static inline float lanczos_weight(float dis, int left, int right) {
    // 动态计算a的值
    int a = max(-left, right);
    // 套函数
    if(unlikely(fabsf(dis) >= a)){
        return 0.0f;
    }else{
        float ret = sinc(dis) * sinc(dis / a);
        if(isinf(ret) || isnan(ret)){
            return 1.0f;
        }
        return ret;
    }
}

// 自定义卷积核以及范围的卷积缩放。无LUT优化。
int main_generic_custom_scale_nolut(args_t *args, float scale_x, float scale_y,
                       size_t in_w, size_t in_h,
                       size_t out_w, size_t out_h,
                       uint8_t* in_buf, uint8_t* out_buf,
                       size_t start_p, size_t end_p,
                       int core_left, int core_right, int core_top, int core_bottom,
                       weight_func core) {
    for(size_t p = start_p; p < end_p; p++) {
        size_t x = p % out_w;
        size_t y = p / out_w;

        // 计算浮点源坐标
        float src_x_float = x / scale_x;
        float src_y_float = y / scale_y;
        
        // 获取基准整数坐标
        int base_x = floorf(src_x_float);
        int base_y = floorf(src_y_float);
        
        // 计算相对于基准坐标的小数偏移量
        float frac_x = src_x_float - base_x;
        float frac_y = src_y_float - base_y;
        
        for(int c = 0; c < 4; c++) {
            float sum = 0.0f;
            float weight_sum = 0.0f;
            for(int dx = core_left; dx <= core_right; dx++) {
                int sample_x = base_x + dx;
                sample_x = clip(sample_x, 0, in_w - 1);
                
                // 相对于核中心的一维水平距离
                float dis_x = dx - frac_x;
                
                for(int dy = core_left; dy <= core_right; dy++) {
                    int sample_y = base_y + dy;
                    sample_y = clip(sample_y, 0, in_h - 1);
                    
                    // 相对于核中心的一维垂直距离
                    float dis_y = dy - frac_y;

                    float weight = core(dis_x, core_left, core_right) * 
                                  core(dis_y, core_left, core_right);

                    uint8_t pixel = in_buf[(sample_y * in_w + sample_x) * 4 + c];
                    sum += weight * pixel;
                    weight_sum += weight;
                }
            }

            float result = sum / weight_sum;
            result = clip(result, 0.0f, 255.0f);
            out_buf[p * 4 + c] = round5(result);
        }
    }
    return 0;
}

// 通用自定义插值缩放函数（带LUT优化，时间复杂度从O(n^2)降至O(n)）
int main_generic_custom_scale_lut(args_t *args, float scale_x, float scale_y,
                       size_t in_w, size_t in_h,
                       size_t out_w, size_t out_h,
                       uint8_t* in_buf, uint8_t* out_buf,
                       size_t threads, size_t idx,
                       int core_left, int core_right, int core_top, int core_bottom,
                       weight_func core,
                       atomic_size_t* weight_lut_nonfill_threads) 
                     {
    // 计算当前线程处理的lut的x y坐标范围
    const size_t lut_x_opstart = out_w * idx / threads;
    const size_t lut_x_opend = out_w * (idx + 1) / threads;
    const size_t lut_y_opstart = out_h * idx / threads;
    const size_t lut_y_opend = out_h * (idx + 1) / threads;
    // 计算卷积图片时像素的x y坐标范围
    const size_t pixels = out_w * out_h;
    const size_t start_p = pixels * idx / threads;
    const size_t end_p = pixels * (idx + 1) / threads;
    // 计算核长宽
    const int core_width = core_right - core_left + 1;
    const int core_height = core_bottom - core_top + 1;

    // 计算x部分
    for(size_t x = lut_x_opstart; x < lut_x_opend; x++) {
        // 计算浮点源坐标
        float src_x_float = x / scale_x;
        // 获取基准整数坐标
        int base_x = floorf(src_x_float);
        // 计算相对于基准坐标的小数偏移量
        float frac_x = src_x_float - base_x;
        // 开始
        for(int dx = core_left, di = 0; dx <= core_right; dx++, di++) {
            // 采样点
            int sample_x = base_x + dx;
            // 边界限制(等效于边缘扩展)
            sample_x = clip(sample_x, 0, in_w - 1);
            // 相对于核中心的一维水平距离
            float dis_x = dx - frac_x;
            // 计算权重
            float weight = core(dis_x, core_left, core_right);
            // 存入LUT
            args->lut_x_buffer[x * core_width + di] = weight;
        }
    }
    // 计算y部分
    for(size_t y = lut_y_opstart; y < lut_y_opend; y++) {
        // 计算浮点源坐标
        float src_y_float = y / scale_y;
        // 获取基准整数坐标
        int base_y = floorf(src_y_float);
        // 计算相对于基准坐标的小数偏移量
        float frac_y = src_y_float - base_y;
        // 开始
        for(int dy = core_top, di = 0; dy <= core_bottom; dy++, di++) {
            // 采样点
            int sample_y = base_y + dy;
            // 边界限制(等效于边缘扩展)
            sample_y = clip(sample_y, 0, in_h - 1);
            // 相对于核中心的一维垂直距离
            float dis_y = dy - frac_y;
            // 计算权重
            float weight = core(dis_y, core_top, core_bottom);
            // 存入LUT
            args->lut_y_buffer[y * core_height + di] = weight;
        }
    }
    // 减原子变量
    atomic_fetch_sub_explicit(weight_lut_nonfill_threads, 1, memory_order_release);
    // 等待所有线程完成
    while(atomic_load_explicit(weight_lut_nonfill_threads, memory_order_acquire) != 0){
        // 忙等待
        #ifdef __x86_64__
            __builtin_ia32_pause();  // x86 PAUSE指令，降低功耗
        #elif defined(__aarch64__)
            __asm__ __volatile__("yield" ::: "memory");  // ARM YIELD
        #endif
    }
    
    // 开始卷积，使用预计算好的LUT
    // 遍历输出像素
    for(size_t p = start_p; p < end_p; p++) {
        size_t x = p % out_w;
        size_t y = p / out_w;

        // 计算浮点源坐标
        float src_x_float = x / scale_x;
        float src_y_float = y / scale_y;
        
        // 获取基准整数坐标
        int base_x = floorf(src_x_float);
        int base_y = floorf(src_y_float);

        // 开始
        for(int c = 0; c < 4; c++) {
            // 开始卷积
            float sum = 0.0f;
            float weight_sum = 0.0f;
            for(int dx = core_left, dxi = 0; dx <= core_right; dx++, dxi++) {
                // 采样点
                int sample_x = base_x + dx;
                // 边界限制(等效于边缘扩展)
                sample_x = clip(sample_x, 0, in_w - 1);

                for(int dy = core_top, dyi = 0; dy <= core_bottom; dy++, dyi++) {
                    // 采样点
                    int sample_y = base_y + dy;
                    // 边界限制(等效于边缘扩展)
                    sample_y = clip(sample_y, 0, in_h - 1);

                    // 计算权重
                    float weight = args->lut_x_buffer[x * core_width + dxi] * args->lut_y_buffer[y * core_height + dyi];

                    // 获取像素并加权求和
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

// 通用自定义插值缩放函数
int main_generic_custom_scale(args_t *args, float scale_x, float scale_y,
                       size_t in_w, size_t in_h,
                       size_t out_w, size_t out_h,
                       uint8_t* in_buf, uint8_t* out_buf,
                       size_t threads, size_t idx,
                       int core_left, int core_right, int core_top, int core_bottom,
                       weight_func core) {
    if(args->lut_optimize){

        return main_generic_custom_scale_lut(args, scale_x, scale_y, in_w, in_h, out_w, out_h, in_buf, out_buf, threads, idx, core_left, core_right, core_top, core_bottom, core, args->thread_lock);
    }
    else{
        const size_t pixels = out_w * out_h;
        const size_t start_p = pixels * idx / threads;
        const size_t end_p = pixels * (idx + 1) / threads;
        return main_generic_custom_scale_nolut(args, scale_x, scale_y, in_w, in_h, out_w, out_h, in_buf, out_buf, start_p, end_p, core_left, core_right, core_top, core_bottom, core);
    }
}

static int main_enum(args_t *args, float scale_x, float scale_y, size_t in_w, size_t in_h, size_t out_w, size_t out_h, uint8_t* in_buf, uint8_t* out_buf, size_t threads, size_t idx){
    const size_t pixels = out_w * out_h;
    const size_t start_p = pixels * idx / threads;
    const size_t end_p = pixels * (idx + 1) / threads;

    switch(args->mode){
        case SCALE_NEAREST:
            main_nearest(scale_x, scale_y, in_w, in_h, out_w, out_h, in_buf, out_buf, start_p, end_p);
            break;
        case SCALE_BILINEAR:
            main_bilinear(scale_x, scale_y, in_w, in_h, out_w, out_h, in_buf, out_buf, start_p, end_p);
            break;
        case SCALE_BICUBIC:
            main_generic_custom_scale(args, scale_x, scale_y, 
                in_w, in_h, out_w, out_h, 
                in_buf, out_buf, 
                threads, idx,
                args->core_left, args->core_right, args->core_top, args->core_bottom,

                cubic_weight);
            break;
        case SCALE_LANCZOS:
            main_generic_custom_scale(args, scale_x, scale_y, 
                in_w, in_h, out_w, out_h, 
                in_buf, out_buf, 
                threads, idx,
                args->core_left, args->core_right, args->core_top, args->core_bottom,
                lanczos_weight);
        default:
            return -1;
    }
    return 0;
}

SHARED int f1(size_t threads, size_t idx, args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]){
    const size_t out_w = round5(in_shape[1] * args->sx);
    const size_t out_h = round5(in_shape[0] * args->sy);

    const size_t pixels = out_w * out_h;
    const size_t start_p = pixels * idx / threads;
    const size_t end_p = pixels * (idx + 1) / threads;

    main_enum(args, args->sx, args->sy, in_shape[1], in_shape[0], out_w, out_h, in_buf, out_buf, threads, idx);


    return 0;
}

SHARED int f0(args_t* args, uint8_t *in_buf, uint8_t *out_buf, size_t in_shape[2]){
    // 单线程缩放
    const size_t out_w = round5(in_shape[1] * args->sx);
    const size_t out_h = round5(in_shape[0] * args->sy);

    main_enum(args, args->sx, args->sy, in_shape[1], in_shape[0], out_w, out_h, in_buf, out_buf, 1, 0);

    return 0;
}