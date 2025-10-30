from numpy import uint8
from numpy.typing import NDArray
from ctypes import CDLL, c_void_p, c_size_t, c_char_p, POINTER, Structure, cast, byref, sizeof
import string
import weakref

from PySide6.QtWidgets import QWidget, QLabel, QCheckBox, QSlider, QVBoxLayout, QHBoxLayout, QLineEdit, QLayout, QTextEdit

from PySide6.QtCore import Qt, QTimer, QObject

from PySide6.QtGui import QPalette, QColor, QFontMetrics, QIntValidator


class OutPreviewTextEdit(QTextEdit):
    """用于显示输出预览的QTextEdit。仅在输出扩展中可用。"""
    def maxRowsColumns(self) -> tuple[int, int]:
        """获取能显示的最大行数和列数。"""
        ...

class abcUI():
    """Main的抽象类"""
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
    def ui_save(self) -> dict:
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
        """通知img2arr更新预处理。
        """
        ...
    def update(self, threads: int) -> tuple[c_void_p, int]:
        """当img2arr需要刷新计算时调用。可能在别的线程中调用，因此请使用线程安全的方法在此函数修改UI。
        应返回一个元组，第一个元素为传参的指针，第二个元素为传参的长度
        threads: 此次的线程数。1表示单线程，0表示使用了OpenCL，其余表示多线程的线程数。
        """
        ...
    def update_end(self, arg: c_void_p, arglen: int) -> None:
        """当img2arr管线更新结束时调用。
        arg: 上一次update传参的指针。
        arglen: 上一次update传参的长度。
        """
        ...
    preview_textedit: OutPreviewTextEdit | None = ...
    """
    预览的文本框。仅在输出扩展中可用。
    """
    def update_preview(self, arr: NDArray[uint8]) -> bool | None:
        """当img2arr需要更新预览时调用。仅在输出扩展中可用。
        若未定义此函数，或函数返回False, 则隐藏预览，否则显示预览。
        """
        ...

BASE62 = string.digits + string.ascii_lowercase + string.ascii_uppercase

ELLIPSIS = "..."

def int2str(num: int, base: int = 62) -> str:
    if num == 0:
        return BASE62[0]
    res = ""
    while num:
        num, remainder = divmod(num, base)
        res = BASE62[remainder] + res
    return res
    
class UI(abcUI):
    """Main的默认实现"""
    def __init__(self):
        pass
    def ui_init(self, widget: QWidget, ext: CDLL, save: dict | None):
        self_ref = weakref.ref(self)
        self.ext = ext
        # 六大参数：
        # num_base: 进制数(用于生成LUT)
        # arr_prefix: 数组前缀。
        # num_prefix: 数字前缀。
        # num_split: 数字分隔符。
        # num_suffix: 数字后缀。
        # arr_suffix: 数组后缀。
        self.string_encoding = "utf-8"

        self.num_base = 16
        self.arr_prefix = "{"
        self.num_prefix = "0x"
        self.num_split = ", "
        self.num_suffix = ""
        self.arr_suffix = "}"

        self.initLUT()

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        widget.setLayout(layout)

        line1_layout = QHBoxLayout()
        line1_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(line1_layout)

        num_base_widget = QWidget()
        num_base_layout = QHBoxLayout()
        num_base_widget.setLayout(num_base_layout)
        num_base_layout.setContentsMargins(0, 0, 0, 0)
        line1_layout.addWidget(num_base_widget, alignment = Qt.AlignmentFlag.AlignCenter)

        num_base_layout.addWidget(QLabel("进制(2~62): "))
        self.num_base_edit = QLineEdit()
        self.num_base_edit.setMinimumWidth(25)
        self.num_base_edit.setValidator(QIntValidator(2, 62))
        self.num_base_edit.setText(str(self.num_base))
        num_base_layout.addWidget(self.num_base_edit)
        def _on_num_base_edit():
            self = self_ref()
            if self is None: return
            if self.num_base_edit.hasAcceptableInput():
                self.num_base = int(self.num_base_edit.text())
                self.initLUT()
                self.img2arr_notify_update()
        self.num_base_edit.textChanged.connect(_on_num_base_edit)

        arr_prefix_widget = QWidget()
        arr_prefix_layout = QHBoxLayout()
        arr_prefix_widget.setLayout(arr_prefix_layout)
        arr_prefix_layout.setContentsMargins(0, 0, 0, 0)
        line1_layout.addWidget(arr_prefix_widget, alignment = Qt.AlignmentFlag.AlignCenter)

        arr_prefix_layout.addWidget(QLabel("数组前缀: "))
        self.arr_prefix_edit = QLineEdit()
        self.arr_prefix_edit.setMinimumWidth(25)
        arr_prefix_layout.addWidget(self.arr_prefix_edit)
        self.arr_prefix_edit.setText(self.arr_prefix)
        def _on_arr_prefix_edit():
            self = self_ref()
            if self is None: return
            self.arr_prefix = self.arr_prefix_edit.text()
            self.img2arr_notify_update()
        self.arr_prefix_edit.textChanged.connect(_on_arr_prefix_edit)

        num_prefix_widget = QWidget()
        arr_suffix_layout = QHBoxLayout()
        num_prefix_widget.setLayout(arr_suffix_layout)
        arr_suffix_layout.setContentsMargins(0, 0, 0, 0)
        line1_layout.addWidget(num_prefix_widget, alignment = Qt.AlignmentFlag.AlignCenter)

        arr_suffix_layout.addWidget(QLabel("数组后缀: "))
        self.arr_suffix_edit = QLineEdit()
        self.arr_suffix_edit.setMinimumWidth(25)
        arr_suffix_layout.addWidget(self.arr_suffix_edit)
        self.arr_suffix_edit.setText(self.arr_suffix)
        def _on_arr_suffix_edit():
            self = self_ref()
            if self is None: return
            self.arr_suffix = self.arr_suffix_edit.text()
            self.img2arr_notify_update()
        self.arr_suffix_edit.textChanged.connect(_on_arr_suffix_edit)

        line2_layout = QHBoxLayout()
        line2_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(line2_layout)

        num_split_widget = QWidget()
        num_split_layout = QHBoxLayout()
        num_split_widget.setLayout(num_split_layout)
        num_split_layout.setContentsMargins(0, 0, 0, 0)
        line2_layout.addWidget(num_split_widget, alignment = Qt.AlignmentFlag.AlignCenter)

        num_split_layout.addWidget(QLabel("数字分隔符: "))
        self.num_split_edit = QLineEdit()
        self.num_split_edit.setMinimumWidth(25)
        num_split_layout.addWidget(self.num_split_edit)
        self.num_split_edit.setText(self.num_split)
        def _on_num_split_edit():
            self = self_ref()
            if self is None: return
            self.num_split = self.num_split_edit.text()
            self.img2arr_notify_update()
        self.num_split_edit.textChanged.connect(_on_num_split_edit)

        num_prefix_widget = QWidget()
        num_prefix_layout = QHBoxLayout()
        num_prefix_widget.setLayout(num_prefix_layout)
        num_prefix_layout.setContentsMargins(0, 0, 0, 0)
        line2_layout.addWidget(num_prefix_widget, alignment = Qt.AlignmentFlag.AlignCenter)

        num_prefix_layout.addWidget(QLabel("数字前缀: "))
        self.num_prefix_edit = QLineEdit()
        self.num_prefix_edit.setMinimumWidth(25)
        num_prefix_layout.addWidget(self.num_prefix_edit)
        self.num_prefix_edit.setText(self.num_prefix)
        def _on_num_prefix_edit():
            self = self_ref()
            if self is None: return
            self.num_prefix = self.num_prefix_edit.text()
            self.img2arr_notify_update()
        self.num_prefix_edit.textChanged.connect(_on_num_prefix_edit)
        
        num_suffix_widget = QWidget()
        num_suffix_layout = QHBoxLayout()
        num_suffix_widget.setLayout(num_suffix_layout)
        num_suffix_layout.setContentsMargins(0, 0, 0, 0)
        line2_layout.addWidget(num_suffix_widget, alignment = Qt.AlignmentFlag.AlignCenter)

        num_suffix_layout.addWidget(QLabel("数字后缀: "))
        self.num_suffix_edit = QLineEdit()
        self.num_suffix_edit.setMinimumWidth(25)
        num_suffix_layout.addWidget(self.num_suffix_edit)
        self.num_suffix_edit.setText(self.num_suffix)
        def _on_num_suffix_edit():
            self = self_ref()
            if self is None: return
            self.num_suffix = self.num_suffix_edit.text()
            self.img2arr_notify_update()
        self.num_suffix_edit.textChanged.connect(_on_num_suffix_edit)

        # 底部弹簧
        layout.addStretch(1)
    
    def initLUT(self):
        self.LUT: list[str] = []
        max_strnum_len = len(int2str(255, self.num_base))
        for i in range(256):
            self.LUT.append(int2str(i, self.num_base).zfill(max_strnum_len))
        # char *lut[]
        self.LUT_ctypes = (c_char_p * len(self.LUT))(*[s.encode('utf-8') for s in self.LUT])

    class args_t(Structure):
        # typedef struct {
        #     // 这里填写参数列表
        #     size_t num_str_len; // 数字字符串长度。要求lut表中的数字字符串也应符合它。
        #     char **lut;
        # 
        #     size_t arr_prefix_len;
        #     char *arr_prefix;
        # 
        #     size_t num_prefix_len;
        #     char *num_prefix;
        # 
        #     size_t num_split_len;
        #     char *num_split;
        # 
        #     size_t num_suffix_len;
        #     char *num_suffix;
        # 
        #     size_t arr_suffix_len;
        #     char *arr_suffix;
        # }__attribute__((packed)) args_t;
        _fields_ = [
            ("num_str_len", c_size_t),
            ("lut", POINTER(c_char_p)),
            ("arr_prefix_len", c_size_t),
            ("arr_prefix", c_char_p),
            ("num_prefix_len", c_size_t),
            ("num_prefix", c_char_p),
            ("num_split_len", c_size_t),
            ("num_split", c_char_p),
            ("num_suffix_len", c_size_t),
            ("num_suffix", c_char_p),
            ("arr_suffix_len", c_size_t),
            ("arr_suffix", c_char_p),
        ]
        _pack_ = 1
    
    def update(self, threads: int):
        args = self.args_t()

        args.num_str_len = len(self.LUT[0])
        args.lut = self.LUT_ctypes
        args.arr_prefix_len = len(self.arr_prefix)
        args.arr_prefix = self.arr_prefix.encode(self.string_encoding)
        args.num_prefix_len = len(self.num_prefix)
        args.num_prefix = self.num_prefix.encode(self.string_encoding)
        args.num_split_len = len(self.num_split)
        args.num_split = self.num_split.encode(self.string_encoding)
        args.num_suffix_len = len(self.num_suffix)
        args.num_suffix = self.num_suffix.encode(self.string_encoding)
        args.arr_suffix_len = len(self.arr_suffix)
        args.arr_suffix = self.arr_suffix.encode(self.string_encoding)

        return (byref(args), sizeof(args))

    def update_preview(self, arr: NDArray[uint8]):
        # 计算最大输出字符数
        rc = self.preview_textedit.maxRowsColumns()
        max_prelen = rc[0] * rc[1]

        # 计算一个单位数字(包含分割符)的字符数
        num_strlen = len(self.LUT[0]) + len(self.num_prefix) + len(self.num_suffix) + len(self.num_split)
        # 计算结尾数字(不包含分割符)的字符数
        endnum_strlen = len(self.LUT[0]) + len(self.num_prefix) + len(self.num_suffix)

        # 计算剩给数字部分的字符数
        max_numlen = max_prelen - len(self.arr_prefix) - len(self.arr_suffix)

        # 计算能否将所有的数字放下
        if len(arr) == 0:
            # 空数组情况
            self.preview_textedit.setText(self.arr_prefix + self.arr_suffix)
        elif (len(arr) - 1) * num_strlen + endnum_strlen <= max_numlen:
            # 直接输出所有数字
            result = self.arr_prefix
            for i, num in enumerate(arr):
                result += self.num_prefix + self.LUT[num] + self.num_suffix
                if i != len(arr) - 1:
                    result += self.num_split
            result += self.arr_suffix
            self.preview_textedit.setText(result)
        else:
            # 需要省略部分数字
            ELLIPSIS = "..."

            # 剩余空间减去省略号长度
            max_numlen -= len(ELLIPSIS)

            # 一定要包含首位数字和末位数字
            max_numlen = max_numlen - num_strlen - endnum_strlen

            if max_numlen < 0:
                # 连首尾数字都放不下，只显示省略号
                result = self.arr_prefix + ELLIPSIS + self.arr_suffix
                self.preview_textedit.setText(result)
                return

            # 剩余还能放多少个中间数字
            max_nums = max_numlen // num_strlen

            # 构建输出文本
            result = self.arr_prefix

            # 第一个数字
            result += self.num_prefix + self.LUT[arr[0]] + self.num_suffix + self.num_split

            # 省略号前的数字
            for i in range(1, 1 + max_nums):
                result += self.num_prefix + self.LUT[arr[i]] + self.num_suffix
                if i != len(arr) - 1:  # 不是最后一个数字
                    result += self.num_split

            # 省略号
            result += ELLIPSIS + self.num_split

            # 最后一个数字
            result += self.num_prefix + self.LUT[arr[-1]] + self.num_suffix

            result += self.arr_suffix
            self.preview_textedit.setText(result)
        
        # return False # 测试：隐藏预览框