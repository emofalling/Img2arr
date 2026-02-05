from ctypes import CDLL, c_void_p, c_uint, POINTER
import time
import weakref

from lib.ExtensionPyABC import abcExt

from PySide6.QtWidgets import QWidget, QLabel, QCheckBox, QSlider, QVBoxLayout, QHBoxLayout, QButtonGroup, QRadioButton

from PySide6.QtCore import Qt, QTimer, QObject

from PySide6.QtGui import QPalette, QColor, QFontMetrics

class UI(abcExt.UI):
    """主类"""
    def __init__(self):
        """类初始化代码。用处不大"""
        ...
    """用于绘制自己的UI空间。需要PySide6。若没有此函数，则表示没有UI。不需要构造函数和析构函数。"""
    def ui_init(self, widget: QWidget, ext: CDLL, save: dict | None):
        self_ref = weakref.ref(self)

        self.layout = QVBoxLayout()
        widget.setLayout(self.layout)
        self.layout.addWidget(QLabel("选择通道："))

        self.button_layout = QHBoxLayout()
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addLayout(self.button_layout)

        self.channel_group = QButtonGroup()
        self.rbtn_r = QRadioButton("R")
        self.rbtn_r.setChecked(True)
        self.channel_group.addButton(self.rbtn_r, 0)
        self.button_layout.addWidget(self.rbtn_r, alignment=Qt.AlignmentFlag.AlignCenter)
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 0, 0))
        self.rbtn_r.setPalette(palette)

        self.rbtn_g = QRadioButton("G")
        self.channel_group.addButton(self.rbtn_g, 1)
        self.button_layout.addWidget(self.rbtn_g, alignment=Qt.AlignmentFlag.AlignCenter)
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 255, 0))
        self.rbtn_g.setPalette(palette)

        self.rbtn_b = QRadioButton("B")
        self.channel_group.addButton(self.rbtn_b, 2)
        self.button_layout.addWidget(self.rbtn_b, alignment=Qt.AlignmentFlag.AlignCenter)
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 255))
        self.rbtn_b.setPalette(palette)

        self.rbtn_a = QRadioButton("A")
        self.channel_group.addButton(self.rbtn_a, 3)
        self.button_layout.addWidget(self.rbtn_a, alignment=Qt.AlignmentFlag.AlignCenter)
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(127, 127, 127))
        self.rbtn_a.setPalette(palette)


        self.channel_group.buttonClicked.connect(lambda: self.img2arr_notify_update() if (self := self_ref()) else None)

        # 底部弹簧
        self.layout.addStretch()
    
    def update(self, arr, threads: int):
        channel = self.channel_group.checkedId()
        arg = (c_uint * 1)(channel)
        return (arg, 1)


    def __del__(self):
        print("Single UI 销毁")


        