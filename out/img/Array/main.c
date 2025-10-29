// #include <required_standard_headers.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>

// #include <required_project_headers.h>

// #include <required_custom_headers.h>

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
SHARED const char img2arr_ext_sign[] = "img2arr.out.img.Array";

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

//===========================================================
//六大参数：
// char **lut: lut表，用于快速映射到数字字符串。共256个数字字符串。
// arr_prefix: 数组前缀。
// num_prefix: 数字前缀。
// num_split: 数字分隔符。
// num_suffix: 数字后缀。
// arr_suffix: 数组后缀。
//===========================================================

// ext.py传入的参数解析结构体。可以作为处理结果输出。
// The parameter parsing structure passed in by ext.py. It can be used as the output of the processing result.
typedef struct {
    // 这里填写参数列表
    size_t num_str_len; // 数字字符串长度。要求lut表中的数字字符串也应符合它。
    char **lut;

    size_t arr_prefix_len;
    char *arr_prefix;

    size_t num_prefix_len;
    char *num_prefix;

    size_t num_split_len;
    char *num_split;

    size_t num_suffix_len;
    char *num_suffix;

    size_t arr_suffix_len;
    char *arr_suffix;
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
SHARED int io_GetOutInfo(args_t* args, size_t in_shape[1], size_t out_shape[1], int* attr){
    // 指定输出的尺寸及其属性
    out_shape[0] = \
        args->arr_prefix_len +  // 数组前缀
        (
            args->num_prefix_len +  // 数字前缀
            args->num_str_len +     // 数字字符串长度
            args->num_suffix_len    // 数字后缀
        ) * in_shape[0] +          // 乘以元素个数
        args->num_split_len * ((in_shape[0] > 0) ? (in_shape[0] - 1) : 0) +  // 安全的分隔符计算
        args->arr_suffix_len;      // 数组后缀
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
SHARED int f0(args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[1]){
    char *lut[256] = {}; // 内部LUT表
    // 初始化LUT表
    for(size_t i = 0; i < 256; i++){
        lut[i] = args->lut[i];
    }
    memcpy(out_buf, args->arr_prefix, args->arr_prefix_len);
    out_buf += args->arr_prefix_len;
    for(size_t i = 0; i < in_shape[0]; i++){
        memcpy(out_buf, args->num_prefix, args->num_prefix_len);
        out_buf += args->num_prefix_len;
        memcpy(out_buf, lut[in_buf[i]], args->num_str_len);
        out_buf += args->num_str_len;
        memcpy(out_buf, args->num_suffix, args->num_suffix_len);
        out_buf += args->num_suffix_len;
        if(likely(i != in_shape[0] - 1)){
            memcpy(out_buf, args->num_split, args->num_split_len);
            out_buf += args->num_split_len;
        }
    }
    memcpy(out_buf, args->arr_suffix, args->arr_suffix_len);
    return 0;
}

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
SHARED int f1(size_t threads, size_t idx, args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[]){ //尚未实现
    char *lut[256] = {}; // 内部LUT表
    // 初始化LUT表
    for(size_t i = 0; i < 256; i++){
        lut[i] = args->lut[i];
    }
    // 计算操作长度
    const size_t size = in_shape[0];
    const size_t start_i = (size * idx / threads);
    const size_t end_i = (size * (idx + 1) / threads);
    // 如果是第一个任务，就写开头
    if(unlikely(idx == 0)){
        memcpy(out_buf, args->arr_prefix, args->arr_prefix_len);
    }
    // 计算自己的起始索引
    out_buf += args->arr_prefix_len
            + (start_i * 
                (args->num_prefix_len + args->num_str_len + args->num_suffix_len + args->num_split_len));
    // 开写！
    for(size_t i = start_i; i < end_i; i++){
        memcpy(out_buf, args->num_prefix, args->num_prefix_len);
        out_buf += args->num_prefix_len;
        memcpy(out_buf, lut[in_buf[i]], args->num_str_len);
        out_buf += args->num_str_len;
        memcpy(out_buf, args->num_suffix, args->num_suffix_len);
        out_buf += args->num_suffix_len;
        if(likely(i != in_shape[0] - 1)){
            memcpy(out_buf, args->num_split, args->num_split_len);
            out_buf += args->num_split_len;
        }
    }
    // 如果是最后一个任务，就写结尾
    if(unlikely(idx == threads - 1)){
        memcpy(out_buf, args->arr_suffix, args->arr_suffix_len);
    }
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