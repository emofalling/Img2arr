# Img2arr后端。不建议直接运行。

"""
命名规则：
    动态链接库：{主名}_{系统}_{架构}_{扩展指令集列表,用_分隔}.{扩展名}
主名 扩展名：
    一般功能：      main dll/so/dylib
    OpenCL SPIR-V：opencl spv
    控制台插件：    ext    py
例如：
    main_linux_x86_64_avx2.so ：一般核心功能(单核/多核)，平台Linux x86_64架构，需平台有AVX2指令集
    opencl.spv：OpenCL并行计算，OpenCL SPIR-V
    ext.py：控制台插件

注意：
    amd64和x86_64是同一种架构，但windows上多显示为amd64, linux上多显示为x86_64, 程序能够处理
    对于OpenCL/控制台插件等系统无关程序，可以不填系统/架构/扩展指令集列表
    控制台插件中(class)Main的init函数(不是__init__!)会在扩展被选中时自动调用，需返回QFrame(否则认为没有参数)。
        它是与主程序串行的，因此非常不建议在其中进行耗时操作。
        系统能够对它进行报错捕获（因此报错了不会污染主程序），而主程序能够将错误信息保存为日志文件并作为弹窗显示。注意：如果返回了SystemExit，则程序会弹窗申请用户是否需要退出标签页。
    控制台插件中(class)Main的exit函数(不是__del__!)会在扩展被取消选中时自动调用，不会捕获返回值（但同样会捕获异常）。
"""
import numpy
from numpy.typing import NDArray

from collections import namedtuple

from itertools import islice

import logging

from PIL import Image # 以后会转而使用动态链接库而非PIL

import ctypes

import sys, os
from types import ModuleType
import typing
from typing import Callable, Any, NewType, Sequence, Optional

import importlib.util
import platform
import json

import traceback

from lib.datatypes import JsonDataType

from lib import ExtensionPyABC, SpecialArch

logger = logging.getLogger(os.path.basename(__file__))

NULL = 0

NULLPTR = ctypes.cast(NULL, ctypes.c_void_p)



self_dir = os.path.dirname(__file__)

# os.chdir(self_dir)

LIB_PATH = os.path.join(self_dir, "lib")

# 如果py > 3.8, 设置self.dir为dll导入的默认路径
if sys.version_info >= (3, 8) and hasattr(os, "add_dll_directory"):
    os.add_dll_directory(self_dir)

ext_index_name_map = {
    0: "open",
    1: "prep",
    2: "code" ,
    3: "out",
}

# 获取CPU系统（小写）
system = platform.system().lower()
if system == "windows": soext = "dll"
elif system == "linux": soext = "so"
elif system == "darwin": soext = "dylib"
else: raise ImportError("Unsupported system: " + system)
# 获取CPU架构（小写）
arch = platform.machine()
arch = SpecialArch.GetNormalArchName(arch)

PlProcCoreName = f"PlProcCore_{system}_{arch}.{soext}"

PlProcCore = ctypes.CDLL(os.path.join(LIB_PATH, PlProcCoreName), use_errno=True, winmode=0)
"""
int SingleCore(char* caller, void* func, void* args, int *ret,
    uint8_t* in_buffer, uint8_t* out_buffer, 
    size_t in_shape[])
"""
PlProcCore.SingleCore.argtypes = [
    ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_size_t)
]
PlProcCore.SingleCore.restype = ctypes.c_int
"""
该函数已弃用
int MultiCore_old(char* caller, size_t threadnum, void* func, void* args, int *ret,
    uint8_t* in_buffer, uint8_t* out_buffer,
    size_t in_shape[])
"""
PlProcCore.MultiCore_old.argtypes = [
    ctypes.c_char_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_size_t)
]
PlProcCore.MultiCore.restype = ctypes.c_int
"""
size_t InitThreadPool(size_t threadnum)
"""
PlProcCore.InitThreadPool.argtypes = [ctypes.c_size_t]
PlProcCore.InitThreadPool.restype = ctypes.c_size_t
"""
int MultiCore(char* caller, void* func, void* args, int *ret,
    uint8_t* in_buffer, uint8_t* out_buffer,
    size_t in_shape[])
"""
PlProcCore.MultiCore.argtypes = [
    ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_size_t)
]
PlProcCore.MultiCore.restype = ctypes.c_int
"""
void Exit()
"""
PlProcCore.Exit.argtypes = []
PlProcCore.Exit.restype = None

def CDLLreadsig(ext: ctypes.CDLL) -> str: # 读取动态链接库签名
    return ctypes.string_at(ext.img2arr_ext_sign).decode('utf-8', 'ignore')

def load_module_from_path(file_path, module_name) -> ExtensionPyABC.abcExt:
    """从文件路径导入模块"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        raise ImportError(f"Unable to create spec from path: {file_path}")
    
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    
    try:
        if spec.loader is None:
            raise ImportError(f"Unable to load module {module_name} from {file_path}: no loader")
        spec.loader.exec_module(module)
    except Exception as e:
        del sys.modules[module_name]
        raise ImportError(f"Loading module {module_name} from {file_path} failed: {e}")
    
    return typing.cast(ExtensionPyABC.abcExt, module)

EXT_TYPE_OPEN = 0
EXT_TYPE_PREP = 1
EXT_TYPE_CODE = 2
EXT_TYPE_OUT = 3

EXT_TYPE_NUMS = 4

EXT_OP_INFO = 0
EXT_OP_CDLL = 1
EXT_OP_EXT = 2
EXT_OP_OPENCL = 3
EXT_OP_CUDA = 4

EXT_PATH_SINGLECORE = 0
EXT_PATH_MULTICORE = 1
EXT_PATH_OPENCL = 2
EXT_PATH_CUDA = 3

ExtMain = tuple[dict[str, str], ctypes.CDLL, ExtensionPyABC.abcExt | None, Any | None, None]

ExtItem = dict[str, 
            dict[str, 
                 ExtMain
            ]
        ]

ExtList = tuple[ExtItem, ExtItem, ExtItem, ExtItem]

def load_exts(loadf: Callable[[str], None], errf: Callable[[str, Exception], None], 
              reload_var: ExtList | None = None, reload_feautures: Sequence[int] = (0, 1, 2, 3)) -> ExtList:
    """加载所有扩展"""
    
    target_json    = "info.json"
    target_extfile = f"main_{system}_{arch}.{soext}" # 扩展一定要有链接库
    target_ctlext  = "ext.py"
    target_opencl  = "opencl.spv"

    new = False
    if reload_var is None:
        reload_var = ({}, {}, {}, {})
        new = True
    else: # 检查传入函数是否为tuple[dict, dict, dict, dict]
        assert len(reload_var) == EXT_TYPE_NUMS
        for i in range(EXT_TYPE_NUMS):
            assert isinstance(reload_var[i], dict)
    for funci, funcname in ext_index_name_map.items(): # 遍历最外层：处理阶段
        for ctype in os.listdir(os.path.join(self_dir, funcname)): # 遍历第二层：处理的数据类型
            ctype_fullpath = os.path.join(self_dir, funcname, ctype)
            ctype_fullpath_exist = os.path.isdir(ctype_fullpath)
            if not ctype_fullpath_exist:
                continue
            if (ctype not in reload_var[funci]) and not new:
                continue
            if new: # 走到这，说明不仅是new，而且reload_var[funci]也不存在
                reload_var[funci][ctype] = {}
            for extname in os.listdir(ctype_fullpath):
                ext_fullpath = os.path.join(ctype_fullpath, extname)
                ext_fullpath_exist = os.path.isdir(ext_fullpath)
                # if ext_fullpath_exist and (extname in reload_var[funci][ctype] or new):
                if not ext_fullpath_exist:
                    continue
                if (extname not in reload_var[funci][ctype]) and not new:
                    continue


                # if new: # 如果是new的，需要初始化为一个足够长的列表
                    # reload_var[funci][ctype][extname] = ({}, None, None, None, None)
                # reload_var_current = reload_var[funci][ctype][extname]
                reload_var_new = [{}, None, None, None, None]
                regname = f"img2arr.{funcname}.{ctype}.{extname}"
                loadf(regname)
                regname_prefix = f"img2arr.{funcname}.{ctype}."
                
                logger.info(f"加载扩展 {regname}")

                # JSON
                if True:
                    failed = False
                    path = os.path.join(ext_fullpath, target_json)
                    if os.path.isfile(path):
                        try:
                            with open(path, "r", encoding="utf-8") as f:
                                ext = json.load(f)
                        except Exception as e:
                            errf(path, e)
                            failed = True
                        else:
                            reload_var_new[EXT_OP_INFO] = ext
                    else:
                        failed = True
                    if failed:
                        # 创建一个空字典
                        reload_var_new[EXT_OP_INFO] = {}
                    # 如果EXP_OP_INFO.name为空，则将文件夹名作为name
                    if reload_var_new[EXT_OP_INFO].get("name", None) is None:
                        reload_var_new[EXT_OP_INFO]["name"] = extname
                    logger.debug(f"扩展 {regname} 的名称为: {reload_var_new[EXT_OP_INFO]["name"]}")
                    

                if EXT_OP_CDLL in reload_feautures:
                    # 动态链接库
                    path = os.path.join(ext_fullpath, target_extfile)
                    if not os.path.isfile(path):
                        # 删除
                        del reload_var[funci][ctype][extname]
                        continue
                    try:
                        ext = _load_exts_cdll(path, regname_prefix, is_code_stage=(funci==EXT_TYPE_CODE))
                    except Exception as e:
                        errf(path, e)
                        logger.warning(f"加载扩展 {regname} 失败: \n{traceback.format_exc()}")
                        continue
                    reload_var_new[EXT_OP_CDLL] = ext

                if EXT_OP_EXT in reload_feautures:
                    # 扩展模块
                    path = os.path.join(ext_fullpath, target_ctlext)
                    if os.path.isfile(path):
                        try:
                            ext = _load_exts_ctlext(path, reload_var_new[EXT_OP_CDLL])
                        except Exception as e:
                            errf(path, e)
                            continue
                        reload_var_new[EXT_OP_EXT] = ext

                if EXT_OP_OPENCL in reload_feautures:
                    # opencl
                    path = os.path.join(ext_fullpath, target_opencl)
                    if os.path.isfile(path):
                        ...
                
                # 赋值回去
                reload_var[funci][ctype][extname] = typing.cast(ExtMain, reload_var_new)

                                    

    return reload_var

def _load_exts_cdll(file: str, regname_prefix: str, is_code_stage: bool = False) -> ctypes.CDLL:
    """load_exts子函数：加载CDLL"""
    # 先加载
    cdll = ctypes.CDLL(file, use_errno=True, winmode=0)
    # 校验签名
    if not hasattr(cdll, "img2arr_ext_sign"):
        raise AttributeError(f"Cannot found variable \"char img2arr_ext_sign[]\"")
    sgn = CDLLreadsig(cdll)
    # 验证前缀
    if not sgn.startswith(regname_prefix):
        raise ValueError(f"Invalid signature: {sgn}. Expected prefix: {regname_prefix}* .")
    # 检查基本函数是否存在
    # int io_GetOutInfo(void* args, size_t in_shape[], size_t out_shape[], int* attr)
    if not hasattr(cdll, "io_GetOutInfo"):
        raise AttributeError(f"Cannot found function \"int io_GetOutInfo(void* args, size_t in_t, size_t in_h, size_t in_w, size_t* out_t, size_t* out_h, size_t* out_w, int* attr)\"")
    cdll.io_GetOutInfo.restype = ctypes.c_int
    cdll.io_GetOutInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_int)]

    # 对于code阶段，还需要io_GetViewOutInfo
    # int io_GetViewOutInfo(void* args, size_t in_shape[ ], size_t out_shape[ ])
    if is_code_stage:
        if not hasattr(cdll, "io_GetViewOutInfo"):
            raise AttributeError(f"Cannot found function \"int io_GetViewOutInfo(void* args, size_t in_shape[ ], size_t out_shape[ ])\"")
        cdll.io_GetViewOutInfo.restype = ctypes.c_int
        cdll.io_GetViewOutInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]

    # 单核和多核至少有一个可用
    # 单核：int f0(void* args, uint8_t* int_buf, uint8_t* out_buf, size_t in_shape[])
    # 多核：int f1(size_t threads, size_t idx, void* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[])
    if not hasattr(cdll, "f0") and not hasattr(cdll, "f1"):
        raise AttributeError("Cannot found function "
                        "\"int f0(void* args, uint8_t* int_buf, uint8_t* out_buf, size_t in_shape[])\""
                        "or"
                        "\"int f1(size_t threads, size_t idx, void* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[])\""
        )
    if hasattr(cdll, "f0"):
        cdll.f0.restype = ctypes.c_int
        cdll.f0.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_size_t)]
    if hasattr(cdll, "f1"):
        cdll.f1.restype = ctypes.c_int
        cdll.f1.argtypes = [ctypes.c_size_t, ctypes.c_size_t, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_size_t)]
    # 对于code阶段，还需要f0p和f1p，其参数定义与f0和f1相同
    if is_code_stage:
        if not hasattr(cdll, "f0p") and not hasattr(cdll, "f1p"):
            raise AttributeError("Cannot found function "
                            "\"int f0p(void* args, uint8_t* int_buf, uint8_t* out_buf, size_t in_shape[])\""
                            "or"
                            "\"int f1p(size_t threads, size_t idx, void* args, uint8_t* in_buf, uint8_t* out_buf, size_t in_shape[])\""
            )
        if hasattr(cdll, "f0p"):
            cdll.f0p.restype = ctypes.c_int
            cdll.f0p.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_size_t)]
        if hasattr(cdll, "f1p"):
            cdll.f1p.restype = ctypes.c_int
            cdll.f1p.argtypes = [ctypes.c_size_t, ctypes.c_size_t, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_size_t)]
    if hasattr(cdll, "init"):
        # 初始化函数，启动时调用
        # int init(void)
        cdll.init.restype = ctypes.c_int
        cdll.init.argtypes = []
        # logger.debug("init()")
        ret = cdll.init()
        if ret != 0:
            raise RuntimeError(f"init() return {ret}")
    return cdll

def _load_exts_ctlext(file: str, cdll: ctypes.CDLL) -> ModuleType:
    """load_exts子函数：加载ctlext"""
    lib = load_module_from_path(file, "pyext")

    return lib



import time


threads = 0

def SetParallelThreads(thrs: int) -> int:
    global threads
    if thrs == 0:
        thrs_ = os.cpu_count()
        if thrs_ is None:
            thrs = 1
        else:
            thrs = thrs_
    threads = PlProcCore.InitThreadPool(thrs)
    return threads


IMG_SHAPE_T = 0
IMG_SHAPE_H = 1
IMG_SHAPE_W = 2
IMG_SHAPE_C = 3

class PRE_ATTRS:
    """预处理属性enum"""
    ATTR_REUSE = 1
    """能够复用输入缓冲区。若指定定了该参数，in_buf和out_buf可能指向同一块内存。"""
    ATTR_READONLY = 2
    """只读取，不输出(REUSE的进阶)。若指定了该参数，out_buf一定为NULL。"""

class PRE_PIPE_MODES:
    """预处理链模式enum"""
    PIPE_MODE_DEFAULT = 0 
    """平衡性能和内存使用"""
    PIPE_MODE_SPEED = 1
    """优先性能。这会独立创建每个预处理单元的输出"""
    PIPE_MODE_MEMORY = 2
    """优先内存使用。完全动态的创建和销毁输出，会产生内存创建和销毁的开销"""

class PIPENodeResult:
    """返回值"""
    def __init__(self):
        pass
    proc_mode: int
    """处理模式.EXT_PATH_*。对于多线程，包含所有线程的返回值。对于单线程，类型为int"""
    results: NDArray[numpy.intc] | int
    """总返回值"""
    ret: int

class MidBuffer:
    def __init__(self, arr: NDArray):
        self.arr = arr
        self.arrptr: ctypes._Pointer[ctypes.c_uint8]
        self.readers: list[int] = []
        self.writers: list[int] = []
        self.update_ptr()
    def update_ptr(self):
        self.arrptr = self.arr.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    def resize(self, shape: Sequence[int], refcheck=False):
        self.arr.resize(shape, refcheck=refcheck)
        self.update_ptr()

def call_processor(name: str, dll: ctypes.CDLL, args: ExtensionPyABC.CPointerArgType, in_buf: MidBuffer, out_buf: MidBuffer | None, is_code_view: bool = False):
    """调用处理"""
    # 获取指针
    inbuf_ptr = in_buf.arrptr
    if out_buf is None:
        outbuf_ptr = ctypes.cast(0, ctypes.POINTER(ctypes.c_uint8))
    else: 
        outbuf_ptr = out_buf.arrptr
    # 获取输入的shape
    # 修复：正确处理一维和多维数组的形状
    if len(in_buf.arr.shape) == 1:
        # 一维数组：形状就是数组长度
        in_shape = in_buf.arr.shape
    else:
        # 多维数组：去掉最后一个维度（通常是通道维度）
        in_shape = in_buf.arr.shape[:-1]
        in_shape_ct = (ctypes.c_size_t * len(in_shape))(*in_shape)
    in_shape_ct = (ctypes.c_size_t * len(in_shape))(*in_shape)
    result = PIPENodeResult()
    if not is_code_view:
        f1_name = "f1"
        f1_func = dll.f1 if hasattr(dll, "f1") else None
        f0_name = "f0"
        f0_func = dll.f0 if hasattr(dll, "f0") else None
    else:
        f1_name = "f1p"
        f1_func = dll.f1p if hasattr(dll, "f1p") else None
        f0_name = "f0p"
        f0_func = dll.f0p if hasattr(dll, "f0p") else None
    # 如果有多核，优先使用多核
    if hasattr(dll, f1_name):
        # 准备返回值列表，默认值全是0
        ret_list = numpy.zeros(threads, dtype=numpy.intc)
        # 多核
        ret = PlProcCore.MultiCore(bytes(name, "utf-8"), f1_func, args, ret_list.ctypes.data_as(ctypes.POINTER(ctypes.c_int)), 
                                   inbuf_ptr, outbuf_ptr, in_shape_ct)
        result.proc_mode = EXT_PATH_MULTICORE
        result.results = ret_list
        result.ret = ret
    # 否则，尝试单核
    elif hasattr(dll, f0_name):
        logger.debug("Single Core")
        ret_main = ctypes.c_int(0)
        ret = PlProcCore.SingleCore(bytes(name, "utf-8"), f0_func, args, ctypes.byref(ret_main), 
                                    inbuf_ptr, outbuf_ptr, in_shape_ct)
        result.proc_mode = EXT_PATH_SINGLECORE
        result.results = ret_main.value
        result.ret = ret
    # 如果都没有，抛出异常
    else:
        raise AttributeError("Cannot found process function(f1 or f0) in ext")
    return result

class Img2arrPIPE:
    def __init__(self, imgf: str, extdc: ExtList):
        # 原图
        self.img = numpy.array(Image.open(imgf).convert("RGBA"), dtype=numpy.uint8)
        # reshape
        # self.img.shape = (self.img.shape[0], self.img.shape[1], self.img.shape[2])
        self.extdc = extdc
        # 原图与预处理间的中间缓冲区
        self.img_pre_buf: list[MidBuffer] = []
        # 预处理后的图片，copy原图
        self.pre = self.img.copy()
        # 编码后预览图片
        self.code_view = numpy.zeros_like(self.img)
        # 编码输出
        self.code_out = numpy.empty((0,), dtype=numpy.uint8)
        # 输出
        self.out = numpy.empty((0,), dtype=numpy.uint8)

    def Pre(self, i: int, empty: bool = False):
        """预处理。返回一个一次性迭代器  
        i: 预处理链索引。i=0，从头开始（但仍会保存用过且必要的缓冲区）；i!=0时，会启用增量刷新  
        empty: 处理链是否为空。若为空，则不进行任何操作，并且将img复制到pre。  
        如果处理链为空，但empty=False，则不会把img复制到pre，画面不符合预期
        """
        it = Pre_iter(self.extdc, self.img, self.img_pre_buf, self.pre, i)
        if empty:
            # 检查pre尺寸是否需要更新
            if self.pre.shape != self.img.shape:
                self.pre.resize(self.img.shape, refcheck=False)
                it.pre_resized = True
            else:
                it.pre_resized = False
            numpy.copyto(self.pre, self.img, casting="no")
        return it
    def CodeView(self, name: str, args: ExtensionPyABC.CPointerArgType, argslen: int, in_arr: Optional[NDArray[numpy.uint8]] = None) -> tuple[PIPENodeResult, bool]:
        """编码预览图刷新。返回处理结果和code_view尺寸是否更新的标志。若未指定in_arr，则使用pre"""
        assert name != "", "编码器名称不能为空"
        view_updated = False
        if in_arr is None:
            in_arr = self.pre
        # 获取对应名称编码器的动态链接库
        dll = self.extdc[EXT_TYPE_CODE]["img"][name][EXT_OP_CDLL]
        # 调用io_GetViewOutInfo获取输出尺寸
        out_shape_ct = (ctypes.c_size_t * 2)()
        in_shape = in_arr.shape[:-1]
        in_shape_ct = (ctypes.c_size_t * len(in_shape))(*in_shape)
        ret = dll.io_GetViewOutInfo(args, in_shape_ct, out_shape_ct)
        if ret != 0: 
            raise RuntimeError(f"io_GetViewOutInfo返回错误码{ret}")
        out_shape = (out_shape_ct[0], out_shape_ct[1], 4)
        # 是否需要resize code_view
        if self.code_view.shape != out_shape:
            self.code_view.resize(out_shape, refcheck=False)
            view_updated = True
        # 调用编码器
        result = call_processor(name, dll, args, MidBuffer(in_arr), MidBuffer(self.code_view), is_code_view=True)
        # 返回结果
        return result, view_updated
    def Code(self, name: str, args: ExtensionPyABC.CPointerArgType, argslen: int) -> PIPENodeResult:
        """编码。返回处理结果"""
        assert name != "", "编码器名称不能为空"
        # 获取对应名称编码器的动态链接库
        dll = self.extdc[EXT_TYPE_CODE]["img"][name][EXT_OP_CDLL]
        # 调用io_GetOutInfo获取输出尺寸
        out_shape_ct = (ctypes.c_size_t * 1)()
        in_shape = self.pre.shape
        in_shape_ct = (ctypes.c_size_t * len(in_shape))(*in_shape)
        attr = ctypes.c_int(0)
        ret = dll.io_GetOutInfo(args, in_shape_ct, out_shape_ct, ctypes.byref(attr))
        if ret != 0:
            raise RuntimeError(f"io_GetOutInfo返回错误码{ret}")
        # resize到输出尺寸（如果需要的话）
        out_size = out_shape_ct[0]
        if self.code_out.shape[0] != out_size:
            self.code_out.resize((out_size,), refcheck=False)
        # 调用编码器
        result = call_processor(name, dll, args, MidBuffer(self.pre), MidBuffer(self.code_out))
        # 返回结果
        return result
    def Out(self, name: str, args: ExtensionPyABC.CPointerArgType, argslen: int) -> PIPENodeResult:
        """输出。返回处理结果"""
        assert name != "", "输出器名称不能为空"
        # 获取对应名称输出器的动态链接库
        dll = self.extdc[EXT_TYPE_OUT]["img"][name][EXT_OP_CDLL]
        # 调用io_GetOutInfo获取输出尺寸
        out_shape_ct = (ctypes.c_size_t * 1)()
        in_shape = self.code_out.shape
        in_shape_ct = (ctypes.c_size_t * len(in_shape))(*in_shape)
        attr = ctypes.c_int(0)
        ret = dll.io_GetOutInfo(args, in_shape_ct, out_shape_ct, ctypes.byref(attr))
        if ret != 0:
            raise RuntimeError(f"io_GetOutInfo返回错误码{ret}")
        # resize到输出尺寸（如果需要的话）
        out_size = out_shape_ct[0]
        logger.debug(f"此次输出数据量: {out_size}")
        if self.out.shape[0] != out_size:
            self.out.resize((out_size,), refcheck=False)
        # 调用输出器
        result = call_processor(name, dll, args, MidBuffer(self.code_out), MidBuffer(self.out))
        # 返回结果
        return result
    def resetPrePIPE(self):
        """重置预处理链"""
        self.img_pre_buf.clear()
    def __del__(self):
        logger.info("管线被删除")

        
class Pre_iter:
    def __init__(self, extdc: ExtList, img: NDArray[numpy.uint8], img_pre_buf: list[MidBuffer], pre: NDArray[numpy.uint8], i: int):
        # print("----")
        self.extdc = extdc
        self.img = MidBuffer(img)
        self.pre = MidBuffer(pre)

        self.img_pre_buf = img_pre_buf
        self.i = self.get_avaliable_index(i)
        """
        索引。它在启动时，其值为保持管线顺利更新所需的尽可能大的索引。
        """
        self.cur_buf_index = self.init_current_buf(self.i) # 当前中间缓冲区索引
        # print("Init buf index:", self.cur_buf_index)
        self.pre_resized: Optional[bool] = None 
        """pre的尺寸是否发生了更新。  
        None: 还没跑到最后一步  
        True: 更新了。需要UI端进行一定处理以适应新的尺寸  
        False: 没有更新。UI端可以继续使用原来的尺寸
        """
        # 清理[i, ...]区间的缓冲区读写者
        # 打破复用依赖，确保平衡和性能模式之间切换顺畅
        for buf in islice(self.img_pre_buf, self.i, None):
            buf.readers.clear()
            buf.writers.clear()
        self.mode: int = PRE_PIPE_MODES.PIPE_MODE_DEFAULT
    def __iter__(self):
        return self
    def set_index(self, i: int):
        """设置当前索引"""
        self.i = i
    def reset_buf_index(self):
        """重置中间缓冲区索引"""
        self.cur_buf_index = -1
    def init_current_buf(self, i):
        """根据i设置当前中间缓冲区。启动时调用一次。"""
        # 如果i==0，直接返回-1
        if i == 0: return -1
        for idx, buf in enumerate(self.img_pre_buf):
            if i in buf.readers:
                # print("Found buf", idx)
                return idx
        
        # 没有找到，返回-1
        return -1

    def current_buf(self) -> MidBuffer:
        """获取当前中间缓冲区"""
        if self.cur_buf_index == -1:
            raise AttributeError("缓冲区索引错误！")
            # print("self.cur_buf_index == -1, use self.img")
            # return self.img
        else:
            return self.img_pre_buf[self.cur_buf_index]
    def add_buf_reader(self, i: int):
        """添加缓冲区读者"""
        # print(f"Add reader array {i} to buf {self.cur_buf_index}")
        rlist = self.img_pre_buf[self.cur_buf_index].readers
        if i not in rlist:
            rlist.append(i)
    def add_buf_writer(self, i: int):
        """添加缓冲区写者"""
        # print(f"Add writer array {i} to buf {self.cur_buf_index}")
        wlist = self.img_pre_buf[self.cur_buf_index].writers
        if i not in wlist:
            wlist.append(i)
    
    def next_buf(self, shape: tuple):
        """获取下一个中间缓冲区，并标记"""
        shape_ = (*shape, 4)
        self.cur_buf_index += 1
        if self.cur_buf_index >= len(self.img_pre_buf):
            self.img_pre_buf.append(MidBuffer(numpy.empty(shape_, dtype=numpy.uint8)))
        buf = self.img_pre_buf[self.cur_buf_index]
        arr = buf.arr
        # 如果shape对不上，则resize
        if arr.shape != shape_:
            buf.resize(shape_, refcheck=False)
        # print("Create new buf at", self.cur_buf_index)
        return buf
    def clear_buf(self):
        """移除之后的缓冲区"""
        del self.img_pre_buf[self.cur_buf_index+1:]

    def get_avaliable_index(self, i: int):
        """当需要增量刷新时，刷新的最低索引。启动时调用一次。"""
        # print("Writers:", self.img_pre_buf_writers, "i:", i)
        # 如果缓冲区为空，返回0
        if len(self.img_pre_buf) == 0:
            return 0
        # 查找users包含i的缓冲区。从后往前找，不然会因为使用了较前的缓冲区而导致多更新了几步，从而性能下降
        # for buf in reversed(self.img_pre_buf):
        for idx, buf in reversed(list(enumerate(self.img_pre_buf))):
            logging.debug(f"idx: {idx}, readers: {buf.readers}, writers: {buf.writers}")
            if i in buf.writers:
                return buf.writers[0]
        # 没有，则i是最后一项（不涉及到任何的中间缓冲区更改）
        return i

    def next(self, name: str, args: ExtensionPyABC.CPointerArgType, argsize: int, is_head: bool = False, is_tail: bool = False):
        """迭代一次  
        name: 要操作的预处理名称*  
        args: 参数  
        argsize: 参数大小  
        is_head: 是否是第一个预处理。相对于整个预处理链，而不是当前的起始点（考虑到增量刷新）。即，i==0时，is_head为True  
        is_tail: 是否是最后一个预处理  
        *：有一个特殊的虚扩展""(空字符串)，它固有属性为ATTR_REUSE，且只负责将输入复制到输出（如果数组指针不同）。利用它能快速的实现扩展的禁用。
        """

        # 分配头缓冲区（很重要，后面要进行大小判断）
        # 如果是head，in_buf一定是img
        if is_head:
            in_buf = self.img
            in_buf_name = "img" # 调试用，跟踪管线路径
        else:
            in_buf = self.current_buf()
            in_buf_name = str(self.cur_buf_index)
            self.add_buf_reader(self.i)
        # 加载扩展
        if name != "":
            ext = self.extdc[EXT_TYPE_PREP]["img"][name]
            dll = ext[EXT_OP_CDLL]

            # 获取信息
            # int io_GetOutInfo(void* args, size_t in_t, size_t in_h, size_t in_w, size_t* out_t, size_t* out_h, size_t* out_w, int* attr)
            if not hasattr(dll, "io_GetOutInfo"):
                raise AttributeError("Cannot found function \"int io_GetOutInfo(void* args, size_t in_t, size_t in_h, size_t in_w, size_t* out_t, size_t* out_h, size_t* out_w, int* attr)\" in ext")
            out_shape_ct = (ctypes.c_size_t * 2)() # 未来会更改shape数
            out_attr = ctypes.c_int(0)

            # 获取输入的shape
            in_shape = in_buf.arr.shape[:-1]
            in_shape_ct = (ctypes.c_size_t * len(in_shape))(*in_shape)

            ret = dll.io_GetOutInfo(args, in_shape_ct,
                                    out_shape_ct, ctypes.byref(out_attr))
            if ret != 0:
                raise AttributeError(f"Cannot get out info from ext, returned {ret}")
            out_shape = tuple(out_shape_ct)
            out_attr = out_attr.value
            # 对于只读扩展，设置输出shape为输入shape
            if out_attr == PRE_ATTRS.ATTR_READONLY:
                out_shape = in_shape
        elif name == "":
            # 特殊扩展：REUSE，输入复制到输出
            out_shape = in_buf.arr.shape[:-1]
            in_shape = out_shape
            out_attr = PRE_ATTRS.ATTR_REUSE
            dll = None

        else:
            raise AttributeError("name类型错误！")
        
        # 对于具有head的只读扩展，输入数组需要特殊处理
        if is_head and out_attr == PRE_ATTRS.ATTR_READONLY:
            # 申请一个buf，并将self.img复制过去
            in_buf = self.next_buf(in_shape)
            in_buf_name = str(self.cur_buf_index)
            numpy.copyto(in_buf.arr, self.img.arr, "no")
            self.add_buf_writer(self.i)
            self.add_buf_reader(self.i)

        # 如果是tail，out_buf一定是pre，并清理缓冲区
        if is_tail:
            # print("Tail")
            out_buf = self.pre
            out_buf_name = "pre" # 调试用，跟踪管线路径
            out_buf_shape_with_c = (*out_shape, 4)
            # 检查尺寸是否匹配
            if out_buf.arr.shape != out_buf_shape_with_c:
                # 调整大小
                self.pre.resize(out_buf_shape_with_c, refcheck=False)
                self.pre_resized = True
            else:
                self.pre_resized = False
            # 如果最后一项恰是只读扩展，则手动将current_buf复制到pre，且没有out_buf
            if out_attr == PRE_ATTRS.ATTR_READONLY:
                out_buf = None
                numpy.copyto(self.pre.arr, self.current_buf().arr, "no")
        else:
            # print(f"Attr for {name}: {out_attr}")
            if out_attr == PRE_ATTRS.ATTR_REUSE and not is_head:
                # 输入可复用，在默认模式下直接使用输入缓冲区
                if self.mode == PRE_PIPE_MODES.PIPE_MODE_SPEED: 
                    out_buf = self.next_buf(out_shape)
                    out_buf_name = str(self.cur_buf_index)
                else:
                    out_buf = in_buf
                    out_buf_name = in_buf_name
            elif out_attr == PRE_ATTRS.ATTR_READONLY:
                # 只读，仅使用输入缓冲区
                out_buf = None
                out_buf_name = "NULL"
            else:
                out_buf = self.next_buf(out_shape)
                out_buf_name = str(self.cur_buf_index)
            if out_buf is not None:
                # 有输出缓冲区，添加写指针
                self.add_buf_writer(self.i)
        
        logger.debug(f"Call pre index {self.i}, {in_buf_name} -> {out_buf_name}")
            

        # 调用预处理
        if name != "": # 默认逻辑
            if dll is not None:
                ret = call_processor(name, dll, args, in_buf, out_buf)
            else:
                logger.error("预处理时，name不为空，但dll为None")
        else: # 空扩展，直接复制
            if out_buf is not None:
                if in_buf.arrptr != out_buf.arrptr: # 开始复制
                    numpy.copyto(out_buf.arr, in_buf.arr, "no")
                else: # 不用复制
                    pass
            else:
                logger.error("空扩展，但out_buf为None")
            ret = None

        self.i += 1

        return None, None # TODO: 处理返回值问题

    def __del__(self):
        """清理"""
        self.clear_buf()
        
def Close():
    """退出清理"""
    PlProcCore.Exit()