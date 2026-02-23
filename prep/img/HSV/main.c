// #include <required_standard_headers.h>
#include <stdint.h>
#include <stdlib.h>
#include <stddef.h>
#include <math.h>
#include <stdatomic.h>
#include <assert.h>

// #include <required_project_headers.h>

// #include <required_custom_headers.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// SHARED: 表示这个函数是导出函数
// SHARED: This function is exported
#if defined(_WIN32) || defined(_WIN64)
#define SHARED __declspec(dllexport)
#define SUPPORT_DLLENTRY
#else
#define SHARED __attribute__((visibility("default")))
#endif

#ifdef __GNUC__
#define likely(x)   __builtin_expect(!!(x), 1)
#define unlikely(x) __builtin_expect(!!(x), 0)
#else
#define likely(x)   (x)
#define unlikely(x) (x)
#endif

// 签名: 验证扩展是否加载正确
// Sign: Verify that the extension is loaded correctly
SHARED const char img2arr_ext_sign[] = "img2arr.prep.img.HSV";

// 扩展属性enum。用于为管线进行特化提示，以进行优化。仅预处理阶段使用。
// Extension attribute enum. Used to specialize the pipeline for optimization. Only used in the preprocessing stage.
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
 * @brief 初始化函数。当扩展被加载时，会被调用一次，在重新加载前不会再次调用。
 * This function is called once when the extension is loaded, and it will not be called again before reloading.
 * @return 错误码，0表示成功，非0表示失败。若函数无返回，则可能返回随机值
 * Error code, 0 means success, non-0 means failure. If the function has no return, it may return a random value.
 * @note 没有此函数并不会导致扩展加载失败，只是无法自定义初始化。
 * @note No such function will not cause the extension to fail to load, but it cannot be customized to initialize.
 */
SHARED int init(void){
    // Implement here.
    return 0;
}

SHARED atomic_size_t* atomic_init_size_t(atomic_size_t* p, size_t v){
    atomic_init(p, v);
    return p;
}

#define MAX3(a, b, c) ((a) > (b) ? ((a) > (c) ? (a) : (c)) : ((b) > (c) ? (b) : (c)))
#define MIN3(a, b, c) ((a) < (b) ? ((a) < (c) ? (a) : (c)) : ((b) < (c) ? (b) : (c)))
inline const int max_arr(const int arr[], int n){
    int max = arr[0];
    for(int i = 1; i < n; ++i)
        if(arr[i] > max) max = arr[i];
    return max;
}
#define clip(x, min, max) ((x) < (min) ? (min) : ((x) > (max) ? (max) : (x)))
typedef struct{
    uint8_t result;
    uint8_t i;
}maxmin_flag_u8_res_t;

// 求三数最大值，并返回最大值的索引。若最大的数中存在相等的情况，则返回第一个出现的。
inline maxmin_flag_u8_res_t u8_max3_with_flag(uint8_t a, uint8_t b, uint8_t c){
    if(a >= b && a >= c) return (maxmin_flag_u8_res_t){a, 0};
    else if(b >= c) return (maxmin_flag_u8_res_t){b, 1};
    else return (maxmin_flag_u8_res_t){c, 2};
}

// 求一个角度的平均值。将它分解为sin和cos分量，并使用向量加法进行平均。
inline float angle_average(float a, float b, float weight_a, float weight_b){
    float x = cosf(a) * weight_a + cosf(b) * weight_b;
    float y = sinf(a) * weight_a + sinf(b) * weight_b;
    if(x == 0 && y == 0) return NAN; // 无意义
    return atan2f(y, x);
}

// 角度归一化。result in [0, 1), a real in [0, 1).
inline float angle_normalize(float a){
    return a - floorf(a);
}

inline void swapf(float* a, float* b){
    float temp = *a;
    *a = *b;
    *b = temp;
}

inline void swaparr2f(float arr[], int i, int j, float with1[], float with2[]){
    float temp = arr[i];
    arr[i] = arr[j];
    arr[j] = temp;

    if(with1 != NULL){
        temp = with1[i];
        with1[i] = with1[j];
        with1[j] = temp;
    }
    if(with2 != NULL){
        temp = with2[i];
        with2[i] = with2[j];
        with2[j] = temp;
    }
}

// 计算两个色调的差值。由于色调是一个圆环，所以需要特殊处理。result [0, 0.5] map to [0, 1]。
inline float hue_diff(float h1, float h2){
    float d = fabsf(h1 - h2);
    return fminf(d, 1.0f - d);
}

// 快速选择算法 - 返回第k小的元素，并部分排序数组。*with用于指定与之同时排序的数组。
static float quickselectf(float arr[], int left, int right, int k, float with1[], float with2[]) {
    if (left == right) return arr[left];
    
    // 使用中位数法选择pivot
    int mid = left + (right - left) / 2;
    
    // 对左、中、右三个元素排序
    if (arr[right] < arr[left]) swaparr2f(arr, left, right, with1, with2);
    if (arr[mid] < arr[left]) swaparr2f(arr, left, mid, with1, with2);
    if (arr[right] < arr[mid]) swaparr2f(arr, mid, right, with1, with2);
    
    float pivot = arr[mid];
    swaparr2f(arr, mid, right - 1, with1, with2);
    
    int i = left, j = right - 1;
    while (i < j) {
        while (arr[++i] < pivot);
        while (j > left && arr[--j] > pivot);
        if (i < j) swaparr2f(arr, i, j, with1, with2);
    }
    
    if (i < right - 1) swaparr2f(arr, i, right - 1, with1, with2);
    
    if (i == k) return arr[i];
    else if (i > k) return quickselectf(arr, left, i - 1, k, with1, with2);
    else return quickselectf(arr, i + 1, right, k, with1, with2);
}

// 取数组中位数。会对原数组进行部分排序。with用于指定与之同时排序的数组。
static float medianf(float arr[], int n, float with1[], float with2[]){
    if (n & 1) {
        return quickselectf(arr, 0, n - 1, n / 2, with1, with2);
    } else {
        // 偶数个元素时，返回中间两个数的平均值
        float m1 = quickselectf(arr, 0, n - 1, n / 2 - 1, with1, with2);
        float m2 = quickselectf(arr, n / 2, n - 1, n / 2, with1, with2);
        return (m1 + m2) * 0.5f;
    }
}

// ext.py传入的参数解析结构体。可以作为处理结果输出。
// The parameter parsing structure passed in by ext.py. It can be used as the output of the processing result.
typedef struct {
    float H_change; // 色调偏移量。建议范围是[-0.5, 0.5]对应[-180°, +180°]。运算后处理为模360°的值。
    float S_change; // 饱和度偏移量。建议范围是[-1.0, 1.0]对应[-100%, +100%]。钳位至[0, 1]区间内。
    int16_t V_change; // 明亮度偏移量。建议范围是[-255, 255]。钳位至[-255, 255]区间内。
    enum{ // 对于中性色，H未定义。本枚举定义了如何设定中性色的H值。
        EXCEPT_SET_H = 0, // 将H设定为特定值
        EXCEPT_IGNORE_S_H, // 忽略上述对S和H的偏移。
    }exception_process;
    /*
    对于中性色的异常处理方案：
    是否使用基于物理模型的智能算法设定中性色像素的H值。
    true:使用该方案，并且exception_process作为该方案无效时的备选方案。
    false:则直接应用exception_process。
    */
    bool smart_fillH;
    float EXCEPT_SET_H_value; // 当exception_process为EXCEPT_SET_H时，设定H的特定值。建议范围是[0, 1]对应[0, 360°]。

    float *h_buffer; // 用于预存储H通道的值来加速智能填充的速度。若为NULL则不使用。仅当使用了smart_fillH时有效。需要分配(width * height * sizeof(float))大小的内存。初始值应为NaN。
    atomic_size_t *h_buffer_sync; //用于同步所有线程完成h_buffer的写入。其初始值应为线程数

    bool pre_write_h; //仅当使用了smart_fillH且启用缓存时有效。当某个线程完成了对色相的解算，是否将其结果提前写入到 h_buffer中。能够加速智能填充的速度，同时使结果更为平滑。
    unsigned int step; // 仅当使用了smart_fillH有效。指定步长。
    bool scan_8_ways; // 仅当使用了smart_fillH有效。是否启用8方向(左上、上、右上、左、右、左下、下、右下)扫描。若位false，将只扫描4个方向(上、下、左、右)
    size_t sample_times; // 每个扫描点至多采样多少个数据点。
    float mad_k; // MAD去噪时的k值
    float S_thr; //[色彩修复]调整中性色的明度判定阈值。若S_thr<0，则无效，严格判定中性色；否则，当颜色的S < S_thr时，就会判定为中性色，可以结合smart_fillH来完成色彩修复。
    bool ignore_npixels; // 仅当使用了smart_fillH有效。是否在预计算阶段将透明像素视为中性色并填充。若为false，则忽略透明通道。

}__attribute__((packed)) args_t;

/**
 * @brief 获取输出数据信息。在调用`f0`或`f1`之前会被调用以确认输出缓冲区大小及其属性.
 * Get output data information. It will be called before calling `f0` or `f1` to confirm the size and attributes of the output buffer.
 * @param args[in/out] 参数解析结构体。
 * Parameter parsing structure.
 * @param in_shape[in] 输入缓冲区形状。关于具体内容，参考下面的注释说明。
 * Input buffer shape. For specific content, refer to the comment description below.
 * @param out_shape[out] 输出缓冲区形状。关于具体内容，参考下面的注释说明。
 * Output buffer shape. For specific content, refer to the comment description below.
 * @param attr[out] 扩展属性，应是`ExtAttr`中的某个值。当扩展是预处理扩展是时，它用于为管线进行特化提示，以进行优化，其余类型则无效。若不赋值，则默认为`ATTR_NONE`。
 * Extension attribute, should be a value in `ExtAttr`. When the extension is a preprocessing extension, it is used to specialize the pipeline for optimization, otherwise it is invalid. If not assigned, the default is `ATTR_NONE`.
 * @return 错误码，0表示成功，非0表示失败。若函数无返回，则返回随机值，容易导致错误。
 * Error code, 0 means success, non-0 means failure. If the function has no return, it returns a random value, which is easy to cause errors.
 */
SHARED int io_GetOutInfo(args_t* args, size_t in_shape[2], size_t out_shape[2], int* attr){
    // 指定输出的尺寸及其属性
    // Specify the size and attributes of the output
    const size_t height = in_shape[0];
    const size_t width = in_shape[1];
    out_shape[0] = height;
    out_shape[1] = width;
    *attr = ATTR_REUSE;
    // Other Implement here.
    return 0;
}

typedef struct HSV{
    float h; // 色调。值域是[0.0, 1.0)。对于中性色，该值为NaN。
    float s; // 饱和度。值域是[0.0, 1.0]。对于中性色，该值为0。
    uint8_t v; // 明亮度。值域是[0, 255]。
}color_hsv_t;

typedef struct RGB{
    uint8_t r;
    uint8_t g;
    uint8_t b;
}color_rgb_t;

#define HSV_V(r, g, b) (MAX3((r), (g), (b)))

inline color_hsv_t rgb2hsv(uint8_t r, uint8_t g, uint8_t b){
    color_hsv_t out = {NAN, 0.0f, 0};
    maxmin_flag_u8_res_t max_res = u8_max3_with_flag(r,g,b);
    out.v = max_res.result;
    if(r == g && r == b){ // Neutral Color
        return out; // H=NaN, S=0
    }
    float v_sub_min = out.v - MIN3(r,g,b); // v - Min, [0.0, 255.0]
    out.s = v_sub_min / out.v; // S, [0.0, 255.0] / [0.0, 255.0] = [0.0, 1.0]
    switch(max_res.i){
        case 0: // R is max.
            out.h = (g - b) / v_sub_min;
            break;
        case 1: // G is max.
            out.h = 2.0f + (b - r) / v_sub_min;
            break;
        case 2: // B is max.
            out.h = 4.0f + (r - g) / v_sub_min;
            break;
        default: // Error.
            break;
    } //out.h base in [0.0, 6.0]
    out.h = angle_normalize(out.h / 6.0f);
    return out;
}

// 带阈值的RGB转HSV。若thr=NaN，则严格比对中性色(等价于直接调用rgb2hsv)。否则，当饱和度[0.0, 1.0]小于thr时，返回的H值被设置为NaN以还原为中性色。
inline color_hsv_t rgb2hsv_withthr(uint8_t r, uint8_t g, uint8_t b, float thr){
    color_hsv_t out = rgb2hsv(r,g,b);
    if(!isnan(thr) && (out.s < thr)){
        out.h = NAN;
    }
    return out;
}

// 要求h的值域为[0.0, 1.0)。
inline color_rgb_t hsv2rgb(color_hsv_t hsv){
    if(isnan(hsv.h)){ // Neural Color
        return (color_rgb_t){hsv.v, hsv.v, hsv.v};
    }
    hsv.h *= 6.0f; // h base in [0.0, 6.0]
    int i = floorf(hsv.h);
    float f = hsv.h - i;
    float p_f = hsv.v * (1.0f - hsv.s); // [0.0, 255.0]
    float q_f = hsv.v * (1.0f - f * hsv.s); // [0.0, 255.0]
    float t_f = hsv.v * (1.0f - (1.0f - f) * hsv.s); // [0.0, 255.0]
    uint8_t v = hsv.v;
    uint8_t p = roundf(p_f);
    uint8_t q = roundf(q_f);
    uint8_t t = roundf(t_f);
    switch(i){
        case 0: // v, t, p
        case 6: //=0, 小概率情况
            return (color_rgb_t){v, t, p};
        case 1: // q, v, p
            return (color_rgb_t){q, v, p};
        case 2: // p, v, t
            return (color_rgb_t){p, v, t};
        case 3: // p, q, v
            return (color_rgb_t){p, q, v};
        case 4: // t, p, v
            return (color_rgb_t){t, p, v}; 
        case 5: // v, p, q
            return (color_rgb_t){v, p, q};
        default: // Error
            return (color_rgb_t){0, 0, 0};
    }
    // returned.
}

// 平方距离
inline float distancesqrtf(float x0, float y0, float x1, float y1){
    const float dx = x1 - x0;
    const float dy = y1 - y0;
    return dx*dx + dy*dy;
}

// 距离
inline float distancef(float x0, float y0, float x1, float y1){
    return sqrtf(distancesqrtf(x0, y0, x1, y1));
}

// 倒数平方距离
inline float rdistancesqrtf(float x0, float y0, float x1, float y1){
    return 1.0f / distancesqrtf(x0, y0, x1, y1);
}

// 倒数距离函数
inline float rdistancef(float x0, float y0, float x1, float y1){
    return 1.0f / distancef(x0, y0, x1, y1);
}

#include <stdio.h>

/**
 * @brief 主函数：多线程实现。
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
 * @param in_shape[in] 输入缓冲区形状。关于具体内容，参考下面的注释说明。
 * Input buffer shape. For specific content, refer to the comment description below.
 * @return 错误码，0表示成功，非0表示失败。若函数无返回，则可能返回随机值
 * Error code, 0 means success, non-0 means failure. If the function has no return, it may return a random value.
 */
SHARED int f1(size_t threads, size_t idx, args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[3]){
    // 计算该线程处理的像素点范围。如果需要特殊需求，请自行修改。
    // Calculate the pixel range processed by this thread. If you need special requirements, please modify it yourself.
    const size_t size = in_shape[0] * in_shape[1];
    const size_t start = (size * idx / threads);
    const size_t end = (size * (idx + 1) / threads);

    const size_t width = in_shape[1];
    const size_t height = in_shape[0];

    const float H_change = args->H_change;
    const float S_change = args->S_change;
    const int16_t V_change = args->V_change;

    const int exception_process = args->exception_process;
    const bool smart_fillH = args->smart_fillH;
    const float EXCEPT_SET_H_value = args->EXCEPT_SET_H_value;
    float *const h_buffer = args->h_buffer;
    const bool pre_write_h = args->pre_write_h;

    const unsigned int step = args->step;
    const bool ways_8 = args->scan_8_ways;
    const size_t sample_times = args->sample_times;
    const float mad_k = args->mad_k;
    const float S_thr = args->S_thr;

    bool ignore_npixels = args->ignore_npixels;

    // 是否使用临时缓冲区。
    bool use_tmp = smart_fillH && h_buffer != NULL;

    // 中性色判断阈值。NaN表示严格中性色。
    float thr = NAN;
    if(S_thr >= 0.0f) thr = S_thr;

    if(use_tmp){
        // 处理自身的像素点范围，并填充到`h_buffer`中。
        for(size_t p = start * 4, i = start; /* p < end * 4, */i < end; p+=4, i++){
            uint8_t r = in_buf[p], g = in_buf[p+1], b = in_buf[p+2], a = in_buf[p+3];
            color_hsv_t hsv = rgb2hsv_withthr(r,g,b, thr);
            if(ignore_npixels && a == 0) hsv.h = NAN;
            h_buffer[i] = hsv.h;
        }
        // printf("sub atomic_add: %d\n", idx);
        // 减原子变量
        atomic_fetch_sub_explicit(args->h_buffer_sync, 1, memory_order_release);
        // 等待所有线程完成
        while(atomic_load_explicit(args->h_buffer_sync, memory_order_acquire) != 0){
            // 忙等待
            #ifdef __x86_64__
                __builtin_ia32_pause();  // x86 PAUSE指令，降低功耗
            #elif defined(__aarch64__)
                __asm__ __volatile__("yield" ::: "memory");  // ARM YIELD
            #endif
        }
    }

    for(size_t p = start * 4, i = start; /* p < end * 4, */i < end; p+=4, i++){
        uint8_t r = in_buf[p], g = in_buf[p+1], b = in_buf[p+2], a = in_buf[p+3];
        color_hsv_t hsv;

        hsv = rgb2hsv_withthr(r,g,b, thr);

        // 运行智能扫描算法
        if(smart_fillH && S_change > 0.0f && isnan(hsv.h)){

            // 获取当前像素的坐标
            int x = i % width;
            int y = i / width;

            // 扫描的8个像素点的坐标。
            typedef struct{
                int x, y; // x, y坐标。当采样完毕时，它作为最后一次采样的点。
                int first_x, first_y; // 第一次采样时的x, y坐标。
                unsigned int sample_len; // 已经采样的次数。
            }scp_info_t;
            typedef struct{
                int x, y;
            }pos_t;
            scp_info_t trace_info[8] = {
                // L R T B
                {x-1, y, 0, 0, 0}, {x+1, y, 0, 0, 0},
                {x, y-1, 0, 0, 0}, {x, y+1, 0, 0, 0},
                // LT RT LB RB
                {x-1, y-1, 0, 0, 0}, {x+1, y-1, 0, 0, 0},
                {x-1, y+1, 0, 0, 0}, {x+1, y+1, 0, 0, 0}
            };
            // 8个扫描点每次采样的H值。
            float traces_Hs[8][sample_times];
            // 8个扫描点每次采样时与原点的距离的的倒数。
            float traces_rdis[8][sample_times];
            // 色相差缓存数组
            float huediff_tmp[sample_times];
            for(int i=0; i<8; i++){
                for(int j=0; j<sample_times; j++){
                    traces_Hs[i][j] = NAN;
                    traces_rdis[i][j] = NAN;
                }
            }
            float middis_huediff[sample_times], huediff_copy[sample_times]; // MAD去噪的缓存数组
            // 8个扫描点的最终的H值。
            float traces_Hs_finally[8] = {
                NAN, NAN,
                NAN, NAN,
                NAN, NAN,
                NAN, NAN
            };
            // 8个扫描点是否坐标越界
            bool trace_is_out_of_bound[8] = {false};
            // 有多少个点已经越界。
            unsigned int out_of_bound_count = 0;
            // 有多少个点的H值已经足够多了。
            unsigned int nnan_h_full_count = 0;

            const unsigned int total_points = ways_8 ? 8 : 4;

            while(true){
                for(int i=0; i<total_points; i++){
                    // 检查坐标是否越界。快速排除掉上一次已经越界的点。
                    if(!trace_is_out_of_bound[i] &&
                      (trace_info[i].x <  0     || trace_info[i].y <  0
                    || trace_info[i].x >= width || trace_info[i].y >= height)
                    ){
                        trace_is_out_of_bound[i] = true;
                        out_of_bound_count++;
                    }
                    // 若未越界，如果找到的次数不够，搜索当前的。
                    if(!trace_is_out_of_bound[i]){
                        if(trace_info[i].sample_len /* < */ != sample_times){
                            size_t p = (trace_info[i].y * width + trace_info[i].x);
                            float h;
                            if(use_tmp){
                                h = h_buffer[p];
                            }else{
                                size_t p4 = p*4;
                                uint8_t r = in_buf[p4], g = in_buf[p4+1], b = in_buf[p4+2];
                                color_hsv_t hsv_tmp = rgb2hsv_withthr(r,g,b, thr);
                                h = hsv_tmp.h;
                                if(ignore_npixels && a == 0) h = NAN;
                            }
                            // 注意：h有可能是NAN。
                            if(!isnan(h)){
                                traces_Hs[i][trace_info[i].sample_len] = h; 
                                traces_rdis[i][trace_info[i].sample_len] = rdistancef(x,y, trace_info[i].x, trace_info[i].y);
                                if(trace_info[i].sample_len == 0) {
                                    trace_info[i].first_x = trace_info[i].x;
                                    trace_info[i].first_y = trace_info[i].y;
                                }
                                trace_info[i].sample_len++;
                            }

                            if(trace_info[i].sample_len == sample_times) nnan_h_full_count++;
                            
                        }
                    }
                }

                // 检查退出条件
                // 若所有点都停止则退出
                if(out_of_bound_count + nnan_h_full_count == total_points) break;

                // 更新下一个要扫描的坐标。注意：不要移动已经采集足够数据的点，或者已经越界的点(用于提升性能)。
                if(trace_info[0].sample_len!=sample_times && !trace_is_out_of_bound[0]) trace_info[0].x -= step;
                if(trace_info[1].sample_len!=sample_times && !trace_is_out_of_bound[1]) trace_info[1].x += step;
                if(trace_info[2].sample_len!=sample_times && !trace_is_out_of_bound[2]) trace_info[2].y -= step;
                if(trace_info[3].sample_len!=sample_times && !trace_is_out_of_bound[3]) trace_info[3].y += step;
                if(ways_8){
                if(trace_info[4].sample_len!=sample_times && !trace_is_out_of_bound[4]) trace_info[4].x -= step, trace_info[4].y -= step;
                if(trace_info[5].sample_len!=sample_times && !trace_is_out_of_bound[5]) trace_info[5].x += step, trace_info[5].y -= step;
                if(trace_info[6].sample_len!=sample_times && !trace_is_out_of_bound[6]) trace_info[6].x -= step, trace_info[6].y += step;
                if(trace_info[7].sample_len!=sample_times && !trace_is_out_of_bound[7]) trace_info[7].x += step, trace_info[7].y += step;
                }
            }
            for(int i=0; i<8; ++i){
                // 计算第一个采样点与最后一个采样点的中点
                // trace_info[i].x = trace_info[i].first_x;
                // trace_info[i].y = trace_info[i].first_y;
                // 计算自身最终的H值
                unsigned int sample_len = trace_info[i].sample_len;
                if(sample_len > 0){
                    trace_info[i].x = (trace_info[i].first_x + trace_info[i].x) / 2U;
                    trace_info[i].y = (trace_info[i].first_y + trace_info[i].y) / 2U;
                }
                if(sample_len >= 3){ // 有效数据，MAD去噪后求平均值
                    // 计算每个颜色与0°的色相差
                    for(int j=0; j<sample_len; ++j){
                        huediff_tmp[j] = hue_diff(traces_Hs[i][j], 0.0f);
                    }
                    float mid = medianf(huediff_tmp, sample_len, traces_rdis[i], traces_Hs[i]);
                    // 此时traces_Hs[i]和traces_rdis[i]顺序已经发生变化。但相对顺序不变。
                    // middis_huediff: 存储每个色差与中点的差值。顺序应与huediff_tmp和traces_Hs[i]保持一致。
                    // huediff_copy: 复制huediff_tmp
                    for(int j=0; j<sample_len; ++j){
                        middis_huediff[j] = fabsf(huediff_tmp[j] - mid);
                        huediff_copy[j] = huediff_tmp[j];
                    }
                    float mad = medianf(middis_huediff, sample_len, NULL, NULL); // MAD去噪后的标准差。
                    float threshold = mad_k * mad;
                    // 此时middis_huediff顺序已经发生变化，但是huediff_copy与huediff_tmp不变，与traces_Hs[i]保持一致。
                    // 同时使用huediff_copy存储没有被mad筛出去的值。
                    size_t H_count = 0;
                    for(int j=0; j<sample_len; ++j){
                        if(huediff_copy[j] <= threshold){
                            huediff_copy[H_count++] = traces_Hs[i][j];
                        }
                    }
                    // 此时huediff_copy的前H_count个值又变为原始的色相值，不是色相差了
                    // 计算角度平均数，见上文。
                    float *arr = huediff_copy;
                    int arrlen = H_count;
                    if(arrlen == 0){
                        arr = traces_Hs[i];
                        arrlen = sample_len;
                    }
                    /*
                    float H_sum = 0;
                    float H_div = 0.0f;
                    for(int j=0; j<arrlen; ++j){
                        H_sum += arr[j] * traces_rdis[i][j];
                        H_div += traces_rdis[i][j];
                    }
                    traces_Hs_finally[i] = H_sum / H_div;
                    */
                    float H_sin_sum = 0.0f, H_cos_sum = 0.0f;
                    float weight_sum = 0.0f;
                    for(int j=0; j<arrlen; ++j){ 
                        // 分解向量
                        float angle = arr[j] * 2.0f * M_PI; // 将[0, 1)映射到[0, 2π)
                        float weight = traces_rdis[i][j];
                        H_sin_sum += sin(angle) * weight;
                        H_cos_sum += cos(angle) * weight;
                        weight_sum += weight;
                    }
                    if(H_sin_sum == 0.0f && H_cos_sum == 0.0f){
                        traces_Hs_finally[i] = NAN; // 无法确定方向，保持为NAN。
                    }else{
                        traces_Hs_finally[i] = atan2f(H_sin_sum / weight_sum, H_cos_sum / weight_sum) / (2.0f * M_PI);
                    }
                }
                else if(sample_len == 2){ // 只有两个有效数据，计算平均数
                    // traces_Hs_finally[i] = (traces_Hs[i][0]+traces_Hs[i][1]) * 0.5f;
                    traces_Hs_finally[i] = angle_average(traces_Hs[i][0] * 2 * M_PI, traces_Hs[i][1] * 2 * M_PI, traces_rdis[i][0], traces_rdis[i][1]) / (2.0f * M_PI);
                }
                else if(sample_len == 1){ // 只有一个有效数据，直接使用这个值。
                    traces_Hs_finally[i] = traces_Hs[i][0];
                }
                else continue; // 没有找到任何有效的H值。依然保持为NAN。
            }
            // 加权求和。取距离的倒数
            // if(dis_max > 0.0f){
                /*
                float H_sum = 0.0f;
                float H_divider = 0.0f;
                for(int i=0; i<total_points; ++i){
                    if(!isnan(traces_Hs_finally[i])){
                        float dis = rdistancef(x, y, trace_info[i].x, trace_info[i].y);
                        assert(!isnan(dis));
                        float weight = 1.0f / dis;
                        // H_sum += traces_Hs_finally[i] * weight;
                        // H_divider += weight;
                        H_sum += traces_Hs_finally[i];
                        H_divider += 1;
                    }
                }

                hsv.h = H_sum / H_divider;
                */

            float H_sin_sum = 0.0f, H_cos_sum = 0.0f;
            float weight_sum = 0.0f;
            for(int i=0; i<total_points; ++i){
                if(!isnan(traces_Hs_finally[i])){
                    // 分解向量
                    float angle = traces_Hs_finally[i] * 2.0f * M_PI;
                    float weight = rdistancef(x, y, trace_info[i].x, trace_info[i].y);
                    H_sin_sum += sin(angle) * weight;
                    H_cos_sum += cos(angle) * weight;
                    weight_sum += weight;
                }
                if(H_sin_sum == 0.0f && H_cos_sum == 0.0f){
                    hsv.h = NAN; // 无法确定方向，保持为NAN。
                }else{
                    hsv.h = atan2f(H_sin_sum / weight_sum, H_cos_sum / weight_sum) / (2.0f * M_PI);
                }
            }

            // } 

            // 写回缓冲区以供其他线程使用。
            if(use_tmp && pre_write_h){
                h_buffer[i] = hsv.h;
            }
            // 若没有扫描到，则会自然的跳到备选方案
        }

        if(isnan(hsv.h)){ // Neutral Color
            // 进行异常处理
            switch(exception_process){
                case EXCEPT_SET_H:
                    hsv.h = EXCEPT_SET_H_value;
                    break;
                case EXCEPT_IGNORE_S_H:
                    break;
                default:
                    break;
            }
        }

        if(!isnan(hsv.h)){
        hsv.h = angle_normalize(hsv.h + H_change);
        hsv.s = clip(hsv.s + S_change, 0.0f, 1.0f);
        }
        hsv.v = clip((int16_t)hsv.v + V_change, 0, 255);

        color_rgb_t rgb = hsv2rgb(hsv);
        out_buf[p]   = rgb.r;
        out_buf[p+1] = rgb.g;
        out_buf[p+2] = rgb.b;
        out_buf[p+3] = a;
    }
    return 0;
}

/**
 * @brief 主函数：单线程实现。
 * Single-threaded implementation.
 * @param args[in/out] 参数解析结构体。
 * Parameter parsing structure.
 * @param in_buf[in] 输入缓冲区，格式为`[*in_shape, 4]`。
 * Input buffer, format is `[*in_shape, 4]`.
 * @param out_buf[out] 输出缓冲区。大小由`io_GetOutInfo`指定。
 * Output buffer. The size is specified by `io_GetOutInfo`.
 * @param in_shape[in] 输入缓冲区形状。关于具体内容，参考下面的注释说明。
 * Input buffer shape. For specific content, refer to the comment description below.
 * @return 错误码，0表示成功，非0表示失败。若函数无返回，则可能返回随机值
 * Error code, 0 means success, non-0 means failure. If the function has no return, it may return a random value.
 */
SHARED int f0(args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[3]){
    // Implement here.
    f1(1, 0, args, in_buf, out_buf, in_shape);
    return 0;
}


/*
缓冲区形状说明：
    缓冲区分为图像缓冲区、数据缓冲区，未来可能会进一步增加。
    对于图像缓冲区，其shape为`[height, width]`，一个像素是RGBA8888，
    此时：`shape[0]`表示图像的高度，`shape[1]`表示图像的宽度。
    对于数据缓冲区，其shape为`[length]`，一个元素是uint8_t，
    此时：`shape[0]`表示数据的长度。

预处理扩展中：
    io_GetOutInfo: in_shape[height, width] -> out_shape[height, width]
    f0: in_buffer[height, width, 4] -> out_buffer[out_shape[0], out_shape[1], 4]
    f1同理。
编码扩展中：
    io_GetOutInfo: in_shape[height, width] -> out_shape[length]
    io_GetViewOutInfo: in_shape[height, width] -> out_shape_v[height, width]
    f0: in_buffer[height, width, 4] -> out_buffer[out_shape[0]]
    f0p: in_buffer[height, width, 4] -> out_buffer[out_shape_v[0], out_shape_v[1], 4]
    f1同理。
输出扩展中：
    io_GetOutInfo: in_shape[length] -> out_shape[length]
    f0: in_buffer[length] -> out_buffer[out_shape[0]]
    f1同理。
*/