#!/bin/bash

# 考虑到Intel处理器在长时间使用AVX512后极易发热降频，考虑到兼容性，默认不启用AVX512
EnableAVX512=true

if [ "$EnableAVX512" = true ]; then
    gcc avx512.c -fPIC -c -o avx512.o -mavx512f -mavx512bw -O3
    gcc avx2.c -fPIC -c -o avx2.o -mavx2 -O3
    gcc sse2.c -fPIC -c -o sse2.o -msse2 -O3
    gcc main.c avx512.o avx2.o sse2.o -shared -fPIC -O3 -o main_linux_x86_64.so -DEXT_ENABLE_AVX512
fi

# 清理中间文件
rm -f ./avx512.o ./avx2.o ./sse2.o