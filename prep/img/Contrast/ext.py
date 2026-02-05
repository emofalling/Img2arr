import json
from numpy import uint8
from numpy.typing import NDArray
from ctypes import CDLL, c_bool, c_uint8, c_uint16, c_int, POINTER, Structure, sizeof, byref
import struct
import time
import weakref

from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QCheckBox, QSlider, QVBoxLayout, QHBoxLayout, QSizePolicy

from PySide6.QtCore import Qt, QTimer

from PySide6.QtGui import QPalette, QColor, QFontMetrics

from lib.ExtensionPyABC import abcExt


class UI(abcExt.UI):
    """主类"""
    def __init__(self):
        """初始化代码。用处不大"""
        ...
    """用于绘制自己的UI空间。需要PySide6。若没有此函数，则表示没有UI。不需要构造函数和析构函数。"""
    def ui_init(self, widget: QWidget, ext: CDLL, save: dict | None):
        self_ref = weakref.ref(self)
        self.ext = ext
        # 创建布局
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        # 提示文本
        dtext = QLabel("对比度：")
        layout.addWidget(dtext)
        # 横向布局
        layout_contrast = QHBoxLayout()
        layout_contrast.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(layout_contrast)
        # 文本：显示当前值，右对齐
        ctext = QLabel("0%")
        ctext.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout_contrast.addWidget(ctext)
        # 文本宽度固定4个字符
        ctext.setFixedWidth(QFontMetrics(ctext.font()).horizontalAdvance("4000%"))
        # 创建滑动条(0~400)，占满宽度
        self.contrast = QSlider(Qt.Orientation.Horizontal)
        layout_contrast.addWidget(self.contrast)
        self.contrast.setRange(0, 1000)
        self.contrast.setValue(100)
        self.contrast.setTickInterval(20)
        self.contrast.setPageStep(20)
        # 设置刻度位置，在下方
        self.contrast.setTickPosition(QSlider.TickPosition.TicksBelow)
        # 基准色标题
        layout_gray_title = QHBoxLayout()
        layout_gray_title.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(layout_gray_title)
        gtext = QLabel("基准色：")
        layout_gray_title.addWidget(gtext)
        gtext.setToolTip("对比度的参考颜色。\n当对比度<100%时，图像会靠近此颜色；\n当对比度>100%时，图像会远离此颜色。\n大部分图像处理工具的基准色都是中性灰(128, 128, 128)，即此扩展的默认基准色。")
        # 恢复默认
        layout_gray_title.addStretch()
        gray_setdefault_button = QPushButton("恢复默认")
        gray_setdefault_button.setToolTip("将基准色设为默认值：\n(128, 128, 128)。")
        layout_gray_title.addWidget(gray_setdefault_button)
        def set_default():
            self = self_ref()
            if self is None: return
            self.set_gray_color((128, 128, 128, 255))
        gray_setdefault_button.clicked.connect(set_default)
        # 横向布局
        layout_gray = QHBoxLayout()
        layout_gray.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(layout_gray)
        # 回调
        def contrast_changed(value):
            self = self_ref()
            if self is None: return
            # 刷新文本
            ctext.setText(str(value) + "%")
            # 更新
            self.Update()
        self.contrast.valueChanged.connect(contrast_changed)
        # 颜色框
        self.gray_color: tuple[int, int, int] = (128, 128, 128)
        self.gray_widget = QWidget()
        layout_gray.addWidget(self.gray_widget)
        # 设置高度占满，宽度固定50px
        # self.gray_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.gray_widget.setFixedWidth(50)
        self.gray_widget.setFixedHeight(50)
        self.set_gray_color((*self.gray_color, 255), False)

        
        # 设置颜色
        def click_gray_widget(e):
            self = self_ref()
            if self is None: return
            color_rgba = (*self.gray_color, 255)
            self.ext_ColorDialogGetColor(widget, color_rgba, currentColorChanged=self.set_gray_color)
        
        self.gray_widget.mousePressEvent = click_gray_widget


        self.useint = QCheckBox("高精度")
        layout.addWidget(self.useint)
        self.useint.stateChanged.connect(self.Update)
        # 添加悬浮提示
        self.useint.setToolTip("保证画面的质量（尤其是极端情况）。\n打开此模式后，使用FP32进行处理，处理速度会稍微降低。")

        
        # 更新提示文本
        self.UpdateTiptext()
        

    # 更新颜色
    def set_gray_color(self, color: tuple[int, int, int, int] | None, _is_non_initial=True):
        if color is None: return
        r, g, b, a = color
        self.gray_color = (r, g, b)
        self.gray_widget.setStyleSheet(f"background-color: rgb({r}, {g}, {b});")
        if _is_non_initial: self.Update()
    # 更新提示文本
    def UpdateTiptext(self):
        text = f"对比度: {self.contrast.value()}%, 基准色: ({self.gray_color[0]}, {self.gray_color[1]}, {self.gray_color[2]})"
        if self.useint.isChecked():
            text += ", 整数"
        self.img2arr_UpdateTiptext(text)
    def Update(self):
        self.UpdateTiptext()
        self.img2arr_notify_update()
    """
    typedef struct {
        bool useint;
        uint16_t contrast;
        uint8_t centr;    //基准色R
        uint8_t centg;    //基准色G
        uint8_t centb;    //基准色B
    }__attribute__((packed)) args_t;
    """
    class arg_t(Structure):
        _fields_ = (
            ("useint", c_bool),
            ("contrast", c_uint16),
            ("centr", c_uint8),
            ("centg", c_uint8),
            ("centb", c_uint8)
        )
        _pack_ = 1

    def update(self, arr, threads):
        arg = self.arg_t()
        arg.useint = self.useint.isChecked()
        arg.contrast = self.contrast.value()
        arg.centr = self.gray_color[0]
        arg.centg = self.gray_color[1]
        arg.centb = self.gray_color[2]
        return byref(arg), sizeof(arg)


        

    def __del__(self):
        print("对比度 释放")
    def ui_save(self):
        pass
