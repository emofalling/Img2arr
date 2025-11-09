# 标准化架构名称

special_arch = {
    'amd64': 'x86_64',    # 64-bit AMD
    'x64': 'x86_64',  
    'x86_64h': 'x86_64',  # x86-64 with Haswell features (macOS)
    'i386': 'x86',        # 32-bit Pentium
    'i486': 'x86',        # 32-bit Pentium
    'i586': 'x86',        # 32-bit Pentium
    'i686': 'x86',        # 32-bit Pentium Pro

    'arm64': 'aarch64',   # 64-bit ARM
    'arm64e': 'aarch64',  # 64-bit ARM with Apple Silicon features (macOS)
    'armv6hl': 'arm',     # 32-bit ARMv6 with hardware floating point
    'armv6': 'arm',       # 32-bit ARMv6
    'armv7l': 'arm',      # 32-bit ARMv7 with hardware floating point
    'armv7': 'arm',       # 32-bit ARMv7
    'armv8': 'aarch64',   # 64-bit ARMv8
}

def GetNormalArchName(arch_name: str):
    arch_name = arch_name.lower()
    return special_arch.get(arch_name, arch_name).lower()