import os

# 遍历当前目录及其子目录中的所有文件
for root, dirs, files in os.walk('.'):
    for file in files:
        if file == '.hash':
            os.remove(os.path.join(root, file))