# 考虑到Intel处理器在长时间使用AVX512后极易发热降频，考虑到兼容性，默认不启用AVX512
$EnableAVX512 = $true
gcc avx512.c -fPIC -c -o avx512.o "-mavx512f" "-mavx512bw" -O3 &&
gcc avx2.c -fPIC -c -o avx2.o "-mavx2" -O3 &&
gcc sse2.c -fPIC -c -o sse2.o "-msse2" -O3 &&
gcc main.c avx512.o avx2.o sse2.o -shared -fPIC -O3 -o main_windows_x86_64.dll -DEXT_ENABLE_AVX512
Remove-Item ./avx512.o
Remove-Item ./avx2.o
Remove-Item ./sse2.o