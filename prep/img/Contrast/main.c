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

SHARED int io_GetOutInfo(void* args, size_t in_shape[2], size_t out_shape[2], int* attr){
    out_shape[0] = in_shape[0]; // h
    out_shape[1] = in_shape[1]; // w
    *attr = ATTR_REUSE;
    return 0;
}

#define SaturationtoU8(x) ((x) > 255 ? 255 : ((x) < 0 ? 0 : (x)))

// new_value = (old_value - UGRAY) * contrast_factor + UGRAY


#define ROUND_DIV(a, b) (((a) + (b) / 2) / (b))

typedef struct {
    bool useint;
    uint16_t contrast;
    uint8_t centr;    //基准色R
    uint8_t centg;    //基准色G
    uint8_t centb;    //基准色B
}__attribute__((packed)) args_t;



SHARED int f1(size_t threads, size_t idx, args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]){
    bool useint = args->useint;
    int contrast_int = args->contrast;
    int centr_int = args->centr;
    int centg_int = args->centg;
    int centb_int = args->centb;

    const size_t pixels = in_shape[0] * in_shape[1];
    const size_t start_i = (pixels * idx / threads) * 4;
    const size_t end_i = (pixels * (idx + 1) / threads) * 4;

    if(useint){
        for(size_t p = start_i; p < end_i; p += 4){
            int r = in_buf[p + 0];
            int g = in_buf[p + 1];
            int b = in_buf[p + 2];
            r = /*ROUND_DIV(*/(r - centr_int) * contrast_int / 100/*)*/ + centr_int;
            g = /*ROUND_DIV(*/(g - centg_int) * contrast_int / 100/*)*/ + centg_int;
            b = /*ROUND_DIV(*/(b - centb_int) * contrast_int / 100/*)*/ + centb_int;
            out_buf[p + 0] = SaturationtoU8(r);
            out_buf[p + 1] = SaturationtoU8(g);
            out_buf[p + 2] = SaturationtoU8(b);
            out_buf[p + 3] = in_buf[p + 3];
        }
    }
    else{
        float contrast_float = (float)contrast_int / 100.0f;
        float centr_intf = (float)centr_int / 255.0f;
        float centg_intf = (float)centg_int / 255.0f;
        float centb_intf = (float)centb_int / 255.0f;
        for(size_t p = start_i; p < end_i; p += 4){
            float r = (float)in_buf[p + 0] / 255.0f;
            float g = (float)in_buf[p + 1] / 255.0f;
            float b = (float)in_buf[p + 2] / 255.0f;
            float out_r = (r - centr_intf) * contrast_float + centr_intf;
            float out_g  = (g - centg_intf) * contrast_float + centg_intf;
            float out_b  = (b - centb_intf) * contrast_float + centb_intf;
            out_buf[p + 0] = SaturationtoU8(roundf(out_r * 255.0f));
            out_buf[p + 1] = SaturationtoU8(roundf(out_g * 255.0f));
            out_buf[p + 2] = SaturationtoU8(roundf(out_b * 255.0f));
            out_buf[p + 3] = in_buf[p + 3];
        }
    }

    return 0;
}

SHARED int f0(args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]){
    
    return f1(1, 0, args, in_buf, out_buf, in_shape);
    
}