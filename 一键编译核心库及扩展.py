import os
import subprocess
import sys
import platform
from typing import Optional, List

# 获取CPU系统（小写）
system = platform.system().lower()
if system == "windows": soext = "dll"
elif system == "linux": soext = "so"
elif system == "darwin": soext = "dylib"
# 获取CPU架构（小写）
arch = platform.machine().lower()
if arch == "amd64":
    arch = "x86_64"

print("正在编译：img2arr核心库::PlProcCore.cpp")

subprocess.run([
    "g++",
    "PlProcCore.cpp",
    "-shared", "-fPIC",
    "-o", f"PlProcCore.{soext}",
    "-O3",
    "-std=c++23"
], cwd="./lib", check=True)

print("正在编译：预处理扩展")

for preptype in os.listdir("prep"):
    for preproc in os.listdir(os.path.join("prep", preptype)):
        path = os.path.join("prep", preptype, preproc)

        print("编译：", path)

        subprocess.run([
            "gcc",
            "main.c",
            "-shared", "-fPIC",
            "-o", f"main_{system}_{arch}.{soext}",
            "-O3"
        ], cwd=path, check=True)


