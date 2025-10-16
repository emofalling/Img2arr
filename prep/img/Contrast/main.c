#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <math.h>

#if defined(_WIN32) || defined(_WIN64)
#define SHARED __declspec(dllexport)
#else
#define SHARED __attribute__((visibility("default")))
#endif

SHARED const char img2arr_ext_sign[] = "img2arr.prep.img.Contrast";

enum{
    ATTR_NONE = 0, // 不指定任何属性。
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

#define SaturationtoU8(x) ((x) > 255 ? 255 : ((x) < 0 ? 0 : (x)))

// new_value = (old_value - UGRAY) * contrast_factor + UGRAY
/*
[pack]struct{
    bool useint; //是否使用纯整数运算。如果是，性能将更高，但是画面精准度会下降。
    uint16_t       contrast; //对比度。百分比，100=1
    uint8_t       centgray; //中心灰度
}
*/

typedef struct{
    bool useint;
    uint16_t contrast;
    uint8_t centgray;
}__attribute__((packed)) args_t;

static int main(bool useint, int contrast_int, int centgray_int, 
    size_t start_i, size_t end_i, 
    uint8_t* in_buf, uint8_t* out_buf, size_t in_t, size_t in_h, size_t in_w){

    if(useint){
        for(size_t p = start_i; p < end_i; p += 4){
            int r = in_buf[p + 0];
            int g = in_buf[p + 1];
            int b = in_buf[p + 2];
            r = (r - centgray_int) * contrast_int / 100 + centgray_int;
            g = (g - centgray_int) * contrast_int / 100 + centgray_int;
            b = (b - centgray_int) * contrast_int / 100 + centgray_int;
            out_buf[p + 0] = SaturationtoU8(r);
            out_buf[p + 1] = SaturationtoU8(g);
            out_buf[p + 2] = SaturationtoU8(b);
            out_buf[p + 3] = in_buf[p + 3];
        }
    }
    else{
        float contrast_float = (float)contrast_int / 100.0f;
        float centgray_float = (float)centgray_int / 255.0f;
        for(size_t p = start_i; p < end_i; p += 4){
            float r = (float)in_buf[p + 0] / 255.0f;
            float g = (float)in_buf[p + 1] / 255.0f;
            float b = (float)in_buf[p + 2] / 255.0f;
            float out_r = (r - centgray_float) * contrast_float + centgray_float;
            float out_g  = (g - centgray_float) * contrast_float + centgray_float;
            float out_b  = (b - centgray_float) * contrast_float + centgray_float;
            out_buf[p + 0] = SaturationtoU8(roundf(out_r * 255.0f));
            out_buf[p + 1] = SaturationtoU8(roundf(out_g * 255.0f));
            out_buf[p + 2] = SaturationtoU8(roundf(out_b * 255.0f));
            out_buf[p + 3] = in_buf[p + 3];
        }
    }
}

SHARED int f0(args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_t, size_t in_h, size_t in_w){
    
    bool useint = args->useint;
    int contrast_int = args->contrast;
    int centgray_int = args->centgray;
    
    const size_t pixels = in_t * in_h * in_w;

    return main(useint, contrast_int, centgray_int, 0, pixels * 4, in_buf, out_buf, in_t, in_h, in_w);
    
}

SHARED int f1(size_t threads, size_t idx, args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_t, size_t in_h, size_t in_w){
    bool useint = args->useint;
    int contrast_int = args->contrast;
    int centgray_int = args->centgray;

    const size_t pixels = in_t * in_h * in_w;
    const size_t start_i = (pixels * idx / threads) * 4;
    const size_t end_i = (pixels * (idx + 1) / threads) * 4;

    return main(useint, contrast_int, centgray_int, start_i, end_i, in_buf, out_buf, in_t, in_h, in_w);
}