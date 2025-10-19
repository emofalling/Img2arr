import os
import subprocess
import sys
import hashlib
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

def gethash(path: str) -> str:
    
    sha256 = hashlib.sha256()
    for root, dirs, files in os.walk(path):
        for file in files:
            if file == ".hash": continue
            with open(os.path.join(root, file), "rb") as f:
                sha256.update(f.read())
    return sha256.hexdigest()

# 比较文件夹下除/.hash外的所有文件SHA256与.hash的值是否不相同
def hashnok(path: str) -> bool:
    hashfile = os.path.join(path, ".hash")
    if not os.path.isfile(hashfile): return True

    with open(hashfile, "r") as f:
        hashstr = f.read().strip()

    hash = gethash(path)

    return hash != hashstr


# 生成文件夹下除/.hash外的所有文件的SHA256并写入.hash
def genhash(path: str):
    hash = gethash(path)
    with open(os.path.join(path, ".hash"), "w") as f:
        f.write(hash)

# 校验PlProcCore.cpp的SHA256，不匹配则编译

if hashnok("./lib"):

    print("正在编译：img2arr核心库::PlProcCore.cpp")

    subprocess.run([
        "g++",
        "PlProcCore.cpp",
        "-shared", "-fPIC",
        "-o", f"PlProcCore.{soext}",
        "-O3",
        "-std=c++23"
    ], cwd="./lib", check=True)

    genhash("./lib")
else:
    print("img2arr核心库::PlProcCore.cpp SHA256匹配，跳过编译")


ext_stage_list = ["open", "prep", "code", "out"]

for stage in ext_stage_list:
    print(f"编译阶段：{stage}")
    for preptype in os.listdir(stage):
        for preproc in os.listdir(os.path.join(stage, preptype)):
            path = os.path.join(stage, preptype, preproc)

            if not os.path.isdir(path): continue

            if hashnok(path):

                print("编译：", path)

                output = f"main_{system}_{arch}.{soext}"

                # 若path下有compile.sh且环境是Linux，则执行compile.sh，传入的第一个参数是输出文件名
                if os.path.isfile(os.path.join(path, "compile.sh")) and system == "linux":
                    subprocess.run([
                        "bash",
                        "compile.sh",
                        output
                    ], cwd=path, check=True)
                # 若path下有compile.bat/compile.ps1且环境是Windows，则执行compile.bat/compile.ps1，传入的第一个参数是输出文件名
                elif os.path.isfile(os.path.join(path, "compile.bat")) and system == "windows":
                    subprocess.run([
                        "cmd",
                        "/c",
                        "compile.bat",
                        output
                    ], cwd=path, check=True)
                elif os.path.isfile(os.path.join(path, "compile.ps1")) and system == "windows":
                    subprocess.run([
                        "powershell",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        "compile.ps1",
                        output
                    ], cwd=path, check=True)
                # 否则，直接编译
                else:
                
                    subprocess.run([
                        "gcc",
                        "main.c",
                        "-shared", "-fPIC",
                        "-o", output,
                        "-O3"
                    ], cwd=path, check=True)

                genhash(path)
            else:
                print("跳过编译：", path)


