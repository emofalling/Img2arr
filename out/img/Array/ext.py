from numpy import uint8
from numpy.typing import NDArray
from ctypes import CDLL, c_void_p, c_size_t, c_char_p, POINTER, Structure, cast, byref, sizeof
import string
import weakref

from PySide6.QtWidgets import QWidget, QLabel, QCheckBox, QSlider, QVBoxLayout, QHBoxLayout, QLineEdit, QLayout, QTextEdit

from PySide6.QtCore import Qt, QTimer, QObject, Signal

from PySide6.QtGui import QPalette, QColor, QFontMetrics, QIntValidator

from lib.ExtensionPyABC import abcExt

import logging, os.path

logger = logging.getLogger(os.path.basename(os.path.dirname(__file__)))

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

class SignalStr(QObject):
    signal = Signal(str)
    
class UI(abcExt.UI):
    def __init__(self):
        self.update_preview_text_signal = SignalStr()
        self.update_preview_text_signal.signal.connect(self.UpdatePreviewText)
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

    def UpdatePreviewText(self, text: str):
        if self.preview_textedit is None: 
            logger.error("preview_textedit 竟然神奇的是 None")
            return
        self.preview_textedit.setText(text)

    def update_preview(self, arr: NDArray[uint8]):
        # 如果没有self.preview_textedit，则直接退出
        if not isinstance(self.preview_textedit, QTextEdit): return False
        arr_prefix = self.arr_prefix
        arr_suffix = self.arr_suffix
        num_prefix = self.num_prefix
        num_suffix = self.num_suffix
        num_split = self.num_split
        lut = self.LUT
        # 计算等效最大宽度
        max_width = self.preview_textedit.getEquivalentWidth()
        # 获取fontMetrics
        fm = self.preview_textedit.fontMetrics()
        # 数组前缀与后缀字符宽度
        arr_prefix_width = fm.horizontalAdvance(arr_prefix)
        arr_suffix_width = fm.horizontalAdvance(arr_suffix)
        # 数字前缀与后缀字符宽度
        num_prefix_width = fm.horizontalAdvance(num_prefix)
        num_suffix_width = fm.horizontalAdvance(num_suffix)
        # 数字分隔符字符宽度
        num_split_width = fm.horizontalAdvance(num_split)

        # 获取一个非结尾数字的字面表示及宽度的函数
        def get_num(num: int) -> tuple[str, int]:
            num_s = lut[num]
            num_str = num_prefix + num_s + num_suffix + num_split
            num_width = num_prefix_width + fm.horizontalAdvance(num_s) + num_suffix_width + num_split_width
            return (num_str, num_width)

        # 第一个数字的字面表示及宽度
        if len(arr) > 0:
            num_first_str, num_first_width = get_num(arr[0])
        else:
            num_first_str = ""
            num_first_width = 0

        # 最后一个数字的字面表示及宽度
        if len(arr) > 1:
            num_last_str = num_prefix + lut[arr[-1]] + num_suffix
            num_last_width = num_prefix_width + fm.horizontalAdvance(num_last_str) + num_suffix_width
        else:
            num_last_str = ""
            num_last_width = 0

        # 初始累计宽度。至少包含前后两个数字
        total_width = arr_prefix_width + num_first_width \
                      + num_last_width + arr_suffix_width
        # str = total_str_0 + total_str_1
        total_str_0 = self.arr_prefix + num_first_str
        total_str_1 = num_last_str + self.arr_suffix

        elp = ELLIPSIS + self.num_split # ...,
        elp_width = fm.horizontalAdvance(ELLIPSIS + elp) # ...,

        if len(arr) > 2:
            for i in range(1, len(arr) - 2):
                num_str, num_width = get_num(arr[i])
                # 如果加上当前数字后，剩余宽度小于省略号宽度，则添加省略号之后退出
                if total_width + num_width > max_width:
                    total_str_0 += elp
                  # total_width += elp_width
                    break
                # 否则，添加当前数字
                total_width += num_width
                total_str_0 += num_str
        # 更新文本
        # self.preview_textedit.setText(total_str_0 + total_str_1)
        self.update_preview_text_signal.signal.emit(total_str_0 + total_str_1)
        return True


