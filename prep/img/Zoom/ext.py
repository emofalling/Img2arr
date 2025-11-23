import json
from numpy import uint8, nan
from numpy.typing import NDArray
from ctypes import CDLL, c_float, c_bool, c_int, c_size_t, Structure, sizeof, byref, POINTER
import struct
import time
import weakref

from PySide6.QtWidgets import QWidget, QLabel, QSlider, QVBoxLayout, QHBoxLayout, QComboBox, QCheckBox, QSpinBox

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
        # SHARED (atomic_)size_t* create_atomic_size_t(size_t v)
        self.ext.create_atomic_size_t.argtypes = [c_size_t]
        self.ext.create_atomic_size_t.restype = POINTER(c_size_t)
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
        self.method.setCurrentIndex(2) # 默认双三次插值
        # 更新事件
        self.method.currentIndexChanged.connect(lambda _: self.img2arr_notify_update())

        # LUT优化多选框
        self.lut_optimize = QCheckBox("LUT优化")
        self.lut_optimize.setChecked(True)
        self.lut_optimize.setToolTip("以空间换时间，能大幅提升处理性能\n不过嘛...需要占用一丢丢内存")
        layout.addWidget(self.lut_optimize)
        self.lut_optimize.stateChanged.connect(lambda _: self.img2arr_notify_update())
        
        # 更新提示文本
        self.UpdateTiptext()
        

    # 更新提示文本
    def UpdateTiptext(self):
        self.img2arr_UpdateTiptext("text")
    def Update(self):
        self.UpdateTiptext()
        self.img2arr_notify_update()
    
    class args_t(Structure):
        # [pack]struct{
        #     float sx; // x方向缩放比例
        #     float sy; // y方向缩放比例
        #     int enum{
        #         NEAREST = 0, // 最近邻插值
        #         BILINEAR = 1, // 双线性插值
        #         BICUBIC = 2, // 双三次插值
        #         LANCZOS = 3, // Lanczos插值
        #     }method;
        # bool lut_optimize; // 是否启用LUT优化。这能够大幅提升性能，但需要一丢丢内存。
        # float *lut_x_buffer; // x轴LUT内存。其大小为：图像宽*(右卷积核索引 - 左卷积核索引 + 1)。
        # float *lut_y_buffer; // y轴LUT内存。其大小为：图像高*(上卷积核索引 - 下卷积核索引 + 1)。
        # (atomic_)size_t* thread_lock; // 线程锁。
        # }
        _fields_ = [
            ("sx", c_float),
            ("sy", c_float),
            ("method", c_int),
            ("lut_optimize", c_bool),
            ("lut_x_buffer", POINTER(c_float)),
            ("lut_y_buffer", POINTER(c_float)),
            ("thread_lock", POINTER(c_size_t))
        ]
        _pack_ = 1
    def update(self, arr, threads):
        # arr shape: (H, W, C)
        core_left, core_right = -2, 2
        core_top, core_bottom = -2, 2
        out_w = self.spin_outx.value()
        out_h = self.spin_outy.value()
        # 初始化原子变量锁
        atm = self.ext.create_atomic_size_t(threads)

        # 不能直接lut_x_buffer lut_y_buffer！不然这些最终会因局部变量会被销毁。
        if self.lut_optimize.isChecked():
            lut_x_buffer = (c_float * (out_w * (core_right - core_left + 1)))(nan)
            lut_y_buffer = (c_float * (out_h * (core_bottom - core_top + 1)))(nan)
        else:
            lut_x_buffer = None
            lut_y_buffer = None
        args = self.args_t(
            out_w / arr.shape[1],
            out_h / arr.shape[0],
            self.method.currentIndex(),
            self.lut_optimize.isChecked(),
            lut_x_buffer,
            lut_y_buffer,
            atm
        )
        

        return (byref(args), sizeof(args))


        

    def __del__(self):
        print("缩放 释放")
    def ui_save(self):
        pass
