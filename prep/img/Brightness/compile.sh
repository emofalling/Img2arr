#!/bin/bash

# 考虑到Intel处理器在长时间使用AVX512后极易发热降频，考虑到兼容性，默认不启用AVX512
ENABLE_AVX512=true
# 第一个传入参数是输出文件名
OUTPUT_FILE_NAME=$1

# AVX512 编译标志，根据 ENABLE_AVX512 变量决定
if [ "$ENABLE_AVX512" = true ]; then
    AVX512_FLAGS="-mavx512f -mavx512bw"
    echo -e "\033[32mAVX512 已启用\033[0m"
else
    AVX512_FLAGS=""
    echo -e "\033[33mAVX512 已禁用\033[0m"
fi

# AVX2 编译（始终启用）
echo "编译 AVX2 模块..."
gcc avx2.c -fPIC -c -o avx2.o -mavx2 -O3
if [ $? -ne 0 ]; then
    echo -e "\033[31mAVX2 编译失败\033[0m"
    exit 1
fi

# SSE2 编译（始终启用）
echo "编译 SSE2 模块..."
gcc sse2.c -fPIC -c -o sse2.o -msse2 -O3
if [ $? -ne 0 ]; then
    echo -e "\033[31mSSE2 编译失败\033[0m"
    exit 1
fi

# AVX512 编译（条件性启用）
if [ "$ENABLE_AVX512" = true ]; then
    echo "编译 AVX512 模块..."
    gcc avx512.c -fPIC -c -o avx512.o $AVX512_FLAGS -O3
    if [ $? -ne 0 ]; then
        echo -e "\033[31mAVX512 编译失败\033[0m"
        exit 1
    fi
fi

# 主程序链接
LINK_OBJECTS="avx2.o sse2.o"
DEFINE_FLAGS=""

if [ "$ENABLE_AVX512" = true ]; then
    LINK_OBJECTS="$LINK_OBJECTS avx512.o"
    DEFINE_FLAGS="$DEFINE_FLAGS -DEXT_ENABLE_AVX512"
    echo -e "\033[32m链接时将启用 AVX512 支持\033[0m"
fi

echo "链接主程序..."
gcc main.c $LINK_OBJECTS -shared -fPIC -O3 -o $OUTPUT_FILE_NAME $DEFINE_FLAGS -static
if [ $? -ne 0 ]; then
    echo -e "\033[31m链接失败\033[0m"
    exit 1
fi

echo -e "\033[32m编译完成: $OUTPUT_FILE_NAME\033[0m"