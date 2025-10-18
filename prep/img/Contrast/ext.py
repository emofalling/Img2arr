import json
from numpy import uint8
from numpy.typing import NDArray
from ctypes import CDLL, c_void_p, c_uint8, c_int, POINTER
import struct
import time
import weakref

from PySide6.QtWidgets import QWidget, QLabel, QCheckBox, QSlider, QVBoxLayout, QHBoxLayout

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
        # 同理，中心灰度
        gtext = QLabel("中央灰度：")
        layout.addWidget(gtext)
        # 横向布局
        layout_gray = QHBoxLayout()
        layout_gray.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(layout_gray)
        # 文本：显示当前值，右对齐
        gtext = QLabel("128")
        gtext.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout_gray.addWidget(gtext)
        # 文本宽度固定4个字符
        gtext.setFixedWidth(QFontMetrics(gtext.font()).horizontalAdvance("-255"))
        # 创建滑动条(-255~255)，占满宽度
        self.gray = QSlider(Qt.Orientation.Horizontal)
        layout_gray.addWidget(self.gray)
        self.gray.setRange(0, 255)
        self.gray.setValue(128)
        self.gray.setTickInterval(15)
        self.gray.setPageStep(15)
        # 设置刻度位置，在下方
        self.gray.setTickPosition(QSlider.TickPosition.TicksBelow)
        # 回调
        def contrast_changed(value):
            self = self_ref()
            if self is None: return
            # 刷新文本
            ctext.setText(str(value) + "%")
            # 更新
            self.Update()
        def gray_changed(value):
            self = self_ref()
            if self is None: return
            # 刷新文本
            gtext.setText(str(value))
            # 更新
            self.Update()
        self.contrast.valueChanged.connect(contrast_changed)
        self.gray.valueChanged.connect(gray_changed)
        # 使用整数
        self.useint = QCheckBox("高精度")
        layout.addWidget(self.useint)
        self.useint.stateChanged.connect(self.Update)
        # 添加悬浮提示
        self.useint.setToolTip("保证画面的质量（尤其是极端情况），处理速度会显著降低。")

        
        # 更新提示文本
        self.UpdateTiptext()
        

    # 更新提示文本
    def UpdateTiptext(self):
        text = f"对比度: {self.contrast.value()}%, 中央灰度: {self.gray.value()}"
        if self.useint.isChecked():
            text += ", 整数"
        self.img2arr_UpdateTiptext(text)
    def Update(self):
        self.UpdateTiptext()
        self.img2arr_notify_update()
    def update(self, threads):
        # 构造参数
        #
        # [pack]struct{
        #     bool useint; //是否使用纯整数运算。如果是，性能将更高，但是画面精准度会下降。
        #     uint16_t contrast; //对比度，百分比表示。
        #     uint8_t centgray; //中心灰度
        # }
        arg = struct.pack(b"=BHB", not self.useint.isChecked(), self.contrast.value(), self.gray.value())
        # print("S:",arg.hex())
        # 更新
        return arg, len(arg)


        

    def __del__(self):
        print("对比度 释放")
    def ui_save(self) -> dict:
        pass
