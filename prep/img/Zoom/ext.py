import json
from numpy import uint8
from numpy.typing import NDArray
from ctypes import CDLL, c_void_p, c_uint8, c_int, POINTER
import struct
import time
import weakref

from PySide6.QtWidgets import QWidget, QLabel, QSlider, QVBoxLayout, QHBoxLayout, QComboBox

from PySide6.QtCore import Qt, QTimer

from PySide6.QtGui import QPalette, QColor, QFontMetrics


class absMain(object):
    """Main的抽象类"""
    def __init__(self):
        """初始化代码。用处不大"""
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


class main(absMain):
    def __init__(self):
        pass
    """用于绘制自己的UI空间。需要PySide6。若没有此函数，则表示没有UI。不需要构造函数和析构函数。"""
    def ui_init(self, widget: QWidget, ext: CDLL, save: dict | None):
        self_ref = weakref.ref(self)
        self.ext = ext
        # 创建布局
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        # 提示文本
        xtext = QLabel("X轴缩放因子：")
        layout.addWidget(xtext)
        # 横向布局
        xlayout = QHBoxLayout()
        xlayout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(xlayout)
        # 文本：显示当前值，右对齐
        xtext = QLabel("100%")
        xtext.setAlignment(Qt.AlignmentFlag.AlignRight)
        xlayout.addWidget(xtext)
        # 文本宽度固定4个字符
        xtext.setFixedWidth(QFontMetrics(xtext.font()).horizontalAdvance("1000%"))
        # 创建滑动条(0~1000, 占满宽度)
        self.xscale = QSlider(Qt.Orientation.Horizontal)
        xlayout.addWidget(self.xscale)
        self.xscale.setRange(0, 1000)
        self.xscale.setValue(100)
        self.xscale.setTickInterval(20)
        self.xscale.setPageStep(20)
        # 设置刻度位置，在下方
        self.xscale.setTickPosition(QSlider.TickPosition.TicksBelow)
        # 同理，y缩放因子
        ytext = QLabel("Y轴缩放因子：")
        layout.addWidget(ytext)
        ylayout = QHBoxLayout()
        ylayout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(ylayout)
        ytext = QLabel("100%")
        ytext.setAlignment(Qt.AlignmentFlag.AlignRight)
        ylayout.addWidget(ytext)
        ytext.setFixedWidth(QFontMetrics(ytext.font()).horizontalAdvance("1000%"))
        self.yscale = QSlider(Qt.Orientation.Horizontal)
        ylayout.addWidget(self.yscale)
        self.yscale.setRange(0, 1000)
        self.yscale.setValue(100)
        self.yscale.setTickInterval(20)
        self.yscale.setPageStep(20)
        self.yscale.setTickPosition(QSlider.TickPosition.TicksBelow)

        # 滑杆回调
        def Change(_):
            self = self_ref()
            if self is None: return
            xtext.setText(f"{self.xscale.value()}%")
            ytext.setText(f"{self.yscale.value()}%")
            # 请求更新
            self.img2arr_notify_update()
        
        self.xscale.valueChanged.connect(Change)
        self.yscale.valueChanged.connect(Change)

        # 下拉列表
        method_layout = QHBoxLayout()
        method_layout.setContentsMargins(0, 0, 0, 0)
        # 全部靠左
        method_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(method_layout)
        method_text = QLabel("插值方法：")
        method_layout.addWidget(method_text)
        method_text.setToolTip("越上面的，性能越高，质量越低\n越下面的，性能越低，质量越高")
        self.method = QComboBox()
        method_layout.addWidget(self.method)
        self.method.addItems([
            "最近邻插值",
            "双线性插值",
            "双三次插值",
            "Lanczos插值"
        ])
        self.method.setCurrentIndex(1) # 默认双线性插值
        # 更新事件
        self.method.currentIndexChanged.connect(lambda _: self.img2arr_notify_update())
        
        # 更新提示文本
        self.UpdateTiptext()
        

    # 更新提示文本
    def UpdateTiptext(self):
        self.img2arr_UpdateTiptext("text")
    def Update(self):
        self.UpdateTiptext()
        self.img2arr_notify_update()
    def update(self, threads):
        # 构造参数
        # [pack]struct{
        #     float sx; // x方向缩放比例
        #     float sy; // y方向缩放比例
        #     int enum{
        #         NEAREST = 0, // 最近邻插值
        #         BILINEAR = 1, // 双线性插值
        #         BICUBIC = 2, // 双三次插值
        #         LANCZOS = 3, // Lanczos插值
        #     };
        # }
        arg = struct.pack("ffi", self.xscale.value() / 100, self.yscale.value() / 100, self.method.currentIndex())
        return (arg, len(arg))


        

    def __del__(self):
        print("缩放 释放")
    def ui_save(self) -> dict:
        pass
