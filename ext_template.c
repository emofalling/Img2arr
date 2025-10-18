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
SHARED const char img2arr_ext_sign[] = "img2arr.<stage>.<type>.<name>";

// 扩展属性enum。用于为管线进行特化提示，以进行优化。
// Extension attribute enum. Used to specialize the pipeline for optimization.
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
    // Implement here. If no return, equal to return 0.
}

// ext.py传入的参数解析结构体。可以作为处理结果输出。
// The parameter parsing structure passed in by ext.py. It can be used as the output of the processing result.
typedef struct {
    // 这里填写参数列表
    // Fill in the output parameter list here
}__attribute__((packed)) args_t;

/**
 * @brief 获取输出数据信息。在调用`f0`或`f1`之前会被调用以确认输出缓冲区大小及其属性.
 * Get output data information. It will be called before calling `f0` or `f1` to confirm the size and attributes of the output buffer.
 * @param args[in/out] 参数解析结构体。
 * Parameter parsing structure.
 * @param in_shape[in] 输入缓冲区形状。对于`img`类扩展，其值为[height, width].
 * For `img` class extensions, its value is [height, width].
 * @param out_shape[out] 输出缓冲区形状。对于`img`类扩展，其值为[height, width].
 * For `img` class extensions, its value is [height, width].
 * @param attr[out] 扩展属性，应是`ExtAttr`中的某个值。用于为管线进行特化提示，以进行优化。若不赋值，则默认为`ATTR_NONE`。
 * Extension attribute, should be a value in `ExtAttr`. Used to specialize the pipeline for optimization. If not assigned, the default is `ATTR_NONE`.
 * @return 错误码，0表示成功，非0表示失败。若函数无返回，则返回随机值，容易导致错误。
 * Error code, 0 means success, non-0 means failure. If the function has no return, it returns a random value, which is easy to cause errors.
 */
SHARED int io_GetOutInfo(args_t* args, size_t in_shape[ ], size_t out_shape[ ], int* attr){
    // 指定输出的尺寸及其属性
    // Specify the size and attributes of the output
    // const size_t height = in_shape[0];
    // const size_t width = in_shape[1];
    // out_shape[0] = height;
    // out_shape[1] = width;
    // *attr = ATTR_NONE;
    // Other Implement here. If no return, equal to return 0.
}

/**
 * @brief 单线程实现。
 * Single-threaded implementation.
 * @param args[in/out] 参数解析结构体。
 * Parameter parsing structure.
 * @param in_buf[in] 输入缓冲区，格式为`[*in_shape, 4]`。
 * Input buffer, format is `[*in_shape, 4]`.
 * @param out_buf[out] 输出缓冲区。大小由`io_GetOutInfo`指定。
 * Output buffer. The size is specified by `io_GetOutInfo`.
 * @param in_shape[in] 输入缓冲区形状。对于`img`类扩展，其值为[height, width].
 * For `img` class extensions, its value is [height, width].
 * @return 错误码，0表示成功，非0表示失败。若函数无返回，则默认返回0。
 * Error code, 0 means success, non-0 means failure. If the function has no return, it defaults to return 0.
 */
SHARED int f0(args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[ ]){
    // Implement here. If no return, equal to return 0.
}

/**
 * @brief 多线程实现。
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
 * @param in_shape[in] 输入缓冲区形状。对于`img`类扩展，其值为[height, width].
 * For `img` class extensions, its value is [height, width].
 * @return 错误码，0表示成功，非0表示失败。若函数无返回，则默认返回0。
 * Error code, 0 means success, non-0 means failure. If the function has no return, it defaults to return 0.
 */
SHARED int f1(size_t threads, size_t idx, args_t* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[ ]){
    // 计算该线程处理的像素点范围。如果需要特殊需求，请自行修改。
    // Calculate the pixel range processed by this thread. If you need special requirements, please modify it yourself.
    const size_t size = in_shape[0] * in_shape[1];
    const size_t start_i = (size * idx / threads) * 4;
    const size_t end_i = (size * (idx + 1) / threads) * 4;
    // Implement here. If no return, equal to return 0.
}