gcc avx2.c -fPIC -c -o avx2.o "-mavx2" -O3 &&
gcc sse2.c -fPIC -c -o sse2.o "-msse2" -O3 &&
gcc main.c sse2.o avx2.o -shared -fPIC -O3 -o main_windows_x86_64.dll
Remove-Item ./avx2.o
Remove-Item ./sse2.o