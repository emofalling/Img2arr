// #include <required_standard_headers.h>
#include <stdint.h>
#include <stddef.h>

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

// 签名: 验证扩展是否加载正确
// Sign: Verify that the extension is loaded correctly
SHARED const char img2arr_ext_sign[] = "img2arr.code.img.Single";

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
 * @return 错误码，0表示成功，非0表示失败。若函数无返回，则默认返回0。
 * Error code, 0 means success, non-0 means failure. If the function has no return, it defaults to return 0.
 * @note 没有此函数并不会导致扩展加载失败，只是无法自定义初始化。
 * @note No such function will not cause the extension to fail to load, but it cannot be customized to initialize.
 */
SHARED int init(void){
    return 0;
}

// ext.py传入的参数解析结构体。可以作为处理结果输出。
// The parameter parsing structure passed in by ext.py. It can be used as the output of the processing result.
typedef struct {
    unsigned int offset;
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
SHARED int io_GetOutInfo(args_t* args, size_t in_shape[2], size_t out_shape[1], int* attr){
    // 指定输出的尺寸及其属性
    // Specify the size and attributes of the output
    const size_t height = in_shape[0];
    const size_t width = in_shape[1];
    out_shape[0] = height * width;
    return 0;
    // Other Implement here. If no return, equal to return 0.
}

/**
 * @brief 获取预览图像输出信息。在调用`f0p`或`f1p`之前会被调用以确认输出缓冲区大小及其属性。仅在编码阶段扩展中有效。
 * Get output data information. It will be called before calling `f0` or `f1` to confirm the size and attributes of the output buffer. Only valid in the encoding stage extension.
 * @param args[in/out] 参数解析结构体。
 * Parameter parsing structure.
 * @param in_shape[in] 输入缓冲区形状。关于具体内容，参考下面的注释说明。
 * Input buffer shape. For specific content, refer to the comment description below.
 * @param out_shape[out] 输出缓冲区形状。关于具体内容，参考下面的注释说明。
 * Output buffer shape. For specific content, refer to the comment description below.
 * @return 错误码，0表示成功，非0表示失败。若函数无返回，则返回随机值，容易导致错误。
 * Error code, 0 means success, non-0 means failure. If the function has no return, it returns a random value, which is easy to cause errors.
 */
SHARED int io_GetViewOutInfo(args_t* args, size_t in_shape[2], size_t out_shape[2]){
    // 指定输出的尺寸及其属性
    // Specify the size and attributes of the output
    out_shape[0] = in_shape[0];
    out_shape[1] = in_shape[1];
    // Other Implement here. If no return, equal to return 0.
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
 * @return 错误码，0表示成功，非0表示失败。若函数无返回，则默认返回0。
 * Error code, 0 means success, non-0 means failure. If the function has no return, it defaults to return 0.
 */
SHARED int f0(args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]){
    unsigned int offset = args->offset;
    for(size_t i = 0, o = 0; i < in_shape[0] * in_shape[1]; i+=4, o+=1){
        out_buf[o] = in_buf[i + offset];
    }
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
 * @return 错误码，0表示成功，非0表示失败。若函数无返回，则默认返回0。
 * Error code, 0 means success, non-0 means failure. If the function has no return, it defaults to return 0.
 */
SHARED int f1(size_t threads, size_t idx, args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]){
    // 计算该线程处理的像素点范围。如果需要特殊需求，请自行修改。
    // Calculate the pixel range processed by this thread. If you need special requirements, please modify it yourself.
    unsigned int offset = args->offset;
    const size_t size = in_shape[0] * in_shape[1];
    const size_t start = size * idx / threads;
    const size_t end = size * (idx + 1) / threads;
    for(size_t i = start * 4, o = start * 1; i < end * 4; i+=4, o+=1){
        out_buf[o] = in_buf[i + offset];
    }

}

/**
 * @brief 预览图像函数：单线程实现。仅在编码阶段扩展中有效。
 * Single-threaded implementation.
 * @param args[in/out] 参数解析结构体。
 * Parameter parsing structure.
 * @param in_buf[in] 输入缓冲区，格式为`[*in_shape, 4]`。
 * Input buffer, format is `[*in_shape, 4]`.
 * @param out_buf[out] 输出缓冲区。大小由`io_GetViewOutInfo`指定。
 * Output buffer. The size is specified by `io_GetViewOutInfo`.
 * @param in_shape[in] 输入缓冲区形状。关于具体内容，参考下面的注释说明。
 * Input buffer shape. For specific content, refer to the comment description below.
 * @return 错误码，0表示成功，非0表示失败。若函数无返回，则默认返回0。
 * Error code, 0 means success, non-0 means failure. If the function has no return, it defaults to return 0.
 */
SHARED int f0p(args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]){
    unsigned int offset = args->offset;
    for(size_t i = 0; i < in_shape[0] * in_shape[1]; i+=4){
        out_buf[i] = out_buf[i+1] = out_buf[i+2] = in_buf[i + offset];
        out_buf[i+3] = 255;
    }
}

/**
 * @brief 预览图像函数：多线程实现。仅在编码阶段扩展中有效。
 * Multi-threaded implementation.
 * @param threads[in] 任务数。
 * Number of tasks.
 * @param idx[in] 任务索引。
 * Task index.
 * @param args[in/out] 参数解析结构体。
 * Parameter parsing structure.
 * @param in_buf[in] 输入缓冲区，格式为`[*in_shape, 4]`。
 * Input buffer, format is `[*in_shape, 4]`.
 * @param out_buf[out] 输出缓冲区。大小由`io_GetViewOutInfo`指定。
 * Output buffer. The size is specified by `io_GetViewOutInfo`.
 * @param in_shape[in] 输入缓冲区形状。关于具体内容，参考下面的注释说明。
 * Input buffer shape. For specific content, refer to the comment description below.
 * @return 错误码，0表示成功，非0表示失败。若函数无返回，则默认返回0。
 * Error code, 0 means success, non-0 means failure. If the function has no return, it defaults to return 0.
 */
SHARED int f1p(size_t threads, size_t idx, args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[2]){
    // 计算该线程处理的像素点范围。如果需要特殊需求，请自行修改。
    // Calculate the pixel range processed by this thread. If you need special requirements, please modify it yourself.
    const size_t size = in_shape[0] * in_shape[1];
    const size_t start_i = (size * idx / threads) * 4;
    const size_t end_i = (size * (idx + 1) / threads) * 4;
    unsigned int offset = args->offset;
    for(size_t i = start_i; i < end_i; i+=4){
        out_buf[i] = out_buf[i+1] = out_buf[i+2] = in_buf[i + offset];
        out_buf[i+3] = 255;
    }
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
*/