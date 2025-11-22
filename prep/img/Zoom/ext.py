import json
from numpy import uint8
from numpy.typing import NDArray
from ctypes import CDLL, c_void_p, c_uint8, c_int, POINTER
import struct
import time
import weakref

from PySide6.QtWidgets import QWidget, QLabel, QSlider, QVBoxLayout, QHBoxLayout, QComboBox, QSpinBox

from PySide6.QtCore import Qt, QTimer

from PySide6.QtGui import QPalette, QColor, QFontMetrics


from lib.ExtensionPyABC import abcExt



class UI(abcExt.UI):
    def __init__(self):
        pass
    """用于绘制自己的UI空间。需要PySide6。若没有此函数，则表示没有UI。不需要构造函数和析构函数。"""
    def ui_init(self, widget: QWidget, ext: CDLL, save: dict | None):
        self_ref = weakref.ref(self)
        self.ext = ext
        # 创建布局
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # 输出宽度
        spin_outx_layout = QHBoxLayout()
        spin_outx_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(spin_outx_layout)
        spin_outx_text = QLabel("输出宽度：")
        spin_outx_layout.addWidget(spin_outx_text)
        self.spin_outx = QSpinBox()
        self.spin_outx.setFixedWidth(100)
        self.spin_outx.setRange(0, 2**31-1)
        self.spin_outx.setValue(1920)
        self.spin_outx.setSingleStep(1)
        spin_outx_layout.addWidget(self.spin_outx)
        spin_outx_layout.addStretch()

        # 输出高度
        spin_outy_layout = QHBoxLayout()
        spin_outy_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(spin_outy_layout)
        spin_outy_text = QLabel("输出高度：")
        spin_outy_layout.addWidget(spin_outy_text)
        self.spin_outy = QSpinBox()
        self.spin_outy.setFixedWidth(100)
        self.spin_outy.setRange(0, 2**31-1)
        self.spin_outy.setValue(1080)
        self.spin_outy.setSingleStep(1)
        spin_outy_layout.addWidget(self.spin_outy)
        spin_outy_layout.addStretch()

        # 绑定刷新事件
        self.spin_outx.valueChanged.connect(lambda _: self.img2arr_notify_update())
        self.spin_outy.valueChanged.connect(lambda _: self.img2arr_notify_update())

        # 下拉列表
        method_layout = QHBoxLayout()
        method_layout.setContentsMargins(0, 0, 0, 0)
        # 全部靠左
        method_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(method_layout)
        # 插值方法
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
    def update(self, arr, threads):
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
        # arr shape: (H, W, C)
        arg = struct.pack("ffi", self.spin_outx.value() / arr.shape[1], self.spin_outy.value() / arr.shape[0], self.method.currentIndex())
        return (arg, len(arg))


        

    def __del__(self):
        print("缩放 释放")
    def ui_save(self):
        pass
