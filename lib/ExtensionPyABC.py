"""
扩展中ext.py的规范
"""

from types import ModuleType

from typing import Optional, TypeAlias

from numpy import uint8
from numpy.typing import NDArray
from ctypes import CDLL, _Pointer, byref, c_void_p
# import _ctypes

from PySide6.QtWidgets import QWidget, QTextEdit

class OutPreviewTextEdit(QTextEdit):
    """用于显示输出预览的QTextEdit。仅在输出扩展中可用。"""
    def getEquivalentWidth(self) -> int:
        """获取等效单行显示宽度"""
        ...

_CArgObject: TypeAlias = type(byref(c_void_p(0))) # type: ignore

# _CArgObject: TypeAlias = _ctypes._CArgObject

CPointerArgType: TypeAlias = _CArgObject | _Pointer

class abcExt(ModuleType):
    #@staticmethod
    class UI():
        """UI的抽象类"""
        def __init__(self):
            """类初始化代码。用处不大"""
            ...
        def ui_init(self, widget: QWidget, ext: CDLL, save: dict | None):
            """UI初始化时的加载代码。每个独立的扩展控制台都会创建一个独立的类。
            widget: 供自身使用的QWidget。
            ext: 自己的动态链接库扩展。
            save: 之前存档的内容。若没有，则为None。
            """
            ...
        def __del__(self):
            """UI销毁时要执行的代码"""
            ...
        def ui_save(self) -> dict | None:
            """保存当前UI的设置。返回一个字典或None。当窗口或标签页关闭时，在开启存档后会调用此函数。"""
            ...
        def img2arr_UpdateTiptext(self, text: str) -> None:
            """不需要扩展提供此函数。img2arr开头的所有函数都不需要扩展提供，而作为扩展的一个辅助功能。所有img2arr开头的函数在__init__后才会存在。
            更新提示文本。在折叠时显示粗略参数时十分重要。
            text: 要显示的文本。
            该函数是线程安全的。
            仅在预处理扩展中可用。
            """
            ...
        def img2arr_notify_update(self) -> None:
            """通知img2arr更新预处理。在输出扩展中为空函数。
            """
            ...
        def update(self, arr: NDArray[uint8], threads: int) -> tuple[CPointerArgType, int]:
            """当img2arr需要刷新计算时调用。可能在别的线程中调用，因此请使用线程安全的方法在此函数修改UI。
            应返回一个元组，第一个元素为传参的指针，第二个元素为传参的长度
            threads: 此次的线程数。1表示单线程，0表示使用了OpenCL，其余表示多线程的线程数。
            """
            ...
        def update_end(self, arg: CPointerArgType, arglen: int) -> None:
            """当自身更新结束时调用。
            arg: 上一次update传参的指针。
            arglen: 上一次update传参的长度。
            """
            ...
        preview_textedit: OutPreviewTextEdit | None = None
        """
        预览的文本框。仅在输出扩展中可用，其它扩展中会为None。
        """
        def update_preview(self, arr: NDArray[uint8]) -> bool | None:
            """当img2arr需要更新预览时调用。仅在输出扩展中可用。
            若未定义此函数，或函数返回False, 则隐藏预览，否则显示预览。
            """
            ...