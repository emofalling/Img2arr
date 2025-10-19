# 考虑到Intel处理器在长时间使用AVX512后极易发热降频，考虑到兼容性，默认不启用AVX512
$EnableAVX512 = $true
# 第一个传入参数是输出文件名
$OutputFileName = $args[0]

# AVX512 编译标志，根据 EnableAVX512 变量决定
$AVX512Flags = @()
if ($EnableAVX512) {
    $AVX512Flags = @("-mavx512f", "-mavx512bw")
    Write-Host "AVX512 已启用" -ForegroundColor Green
} else {
    Write-Host "AVX512 已禁用" -ForegroundColor Yellow
}

# AVX2 编译（始终启用）
Write-Host "编译 AVX2 模块..." -ForegroundColor Green
gcc avx2.c -fPIC -c -o avx2.obj "-mavx2" -O3
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# SSE2 编译（始终启用）
Write-Host "编译 SSE2 模块..." -ForegroundColor Green
gcc sse2.c -fPIC -c -o sse2.obj "-msse2" -O3
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# AVX512 编译（条件性启用）
if ($EnableAVX512) {
    Write-Host "编译 AVX512 模块..." -ForegroundColor Green
    gcc avx512.c -fPIC -c -o avx512.obj $AVX512Flags -O3
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

# 主程序链接
$LinkObjects = @("avx2.obj", "sse2.obj")
$DefineFlags = @()

if ($EnableAVX512) {
    $LinkObjects += "avx512.obj"
    $DefineFlags += "-DEXT_ENABLE_AVX512"
    Write-Host "链接时将启用 AVX512 支持" -ForegroundColor Green
}

Write-Host "链接主程序..." -ForegroundColor Green
gcc main.c $LinkObjects -shared -fPIC -O3 -o $OutputFileName $DefineFlags
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "编译完成: $OutputFileName" -ForegroundColor Green