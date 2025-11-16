from numpy import uint8
from numpy.typing import NDArray
from ctypes import CDLL, c_int, c_void_p, c_size_t, c_char_p, POINTER, Structure, cast, byref, sizeof
import weakref

from PySide6.QtWidgets import QWidget, QLabel, QCheckBox, QSlider, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QSizePolicy

from PySide6.QtCore import Qt, QTimer, QObject, Signal

from PySide6.QtGui import QPalette, QColor, QFontMetrics, QIntValidator

from lib.ExtensionPyABC import abcExt

import logging, os.path

logger = logging.getLogger(os.path.basename(os.path.dirname(__file__)))

    
class UI(abcExt.UI):
    def __init__(self):
        pass
    def ui_init(self, widget: QWidget, ext: CDLL, save: dict | None):
        self_ref = weakref.ref(self)

        layout = QVBoxLayout(widget)
        layout.setSpacing(0)
        widget.setLayout(layout)

        list_layout = QHBoxLayout()
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)
        layout.addLayout(list_layout)

        list_layout.addWidget(QLabel("格式: "))

        self.list = QComboBox()
        self.list.currentIndexChanged.connect(lambda: self.img2arr_notify_update() if (self := self_ref()) else None)
        list_layout.addWidget(self.list)
        # 设置水平拉伸
        self.list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # 添加项
        self.list.addItems([
            "不要选这个",
            "RGB565",
            "RGB332"
        ])
        self.list.setCurrentIndex(1) # 默认RGB565

        # 底部弹簧
        layout.addStretch()

    
    def update(self, threads: int):
        fmt_enum = self.list.currentIndex()
        fmt_enum_ct = c_int(fmt_enum)
        return byref(fmt_enum_ct), sizeof(fmt_enum_ct)


