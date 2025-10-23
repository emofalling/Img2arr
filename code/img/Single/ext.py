from ctypes import CDLL, c_void_p, c_uint, POINTER
import time
import weakref

from PySide6.QtWidgets import QWidget, QLabel, QCheckBox, QSlider, QVBoxLayout, QHBoxLayout, QButtonGroup, QRadioButton

from PySide6.QtCore import Qt, QTimer, QObject

from PySide6.QtGui import QPalette, QColor, QFontMetrics

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

class UI(abcUI):
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


        self.channel_group.buttonClicked.connect(lambda: self_ref().img2arr_notify_update())

        # 底部弹簧
        self.layout.addStretch()
    
    def update(self, threads: int) -> tuple[c_void_p, int]:
        channel = self.channel_group.checkedId()
        arg = (c_uint * 1)(channel)
        return (arg, 1)


    def __del__(self):
        print("Single UI 销毁")


        