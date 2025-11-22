from numpy import uint8
from numpy.typing import NDArray
from ctypes import CDLL, c_void_p, c_uint8, c_int, POINTER
import time
import weakref

from PySide6.QtWidgets import QWidget, QLabel, QCheckBox, QSlider, QVBoxLayout, QHBoxLayout

from PySide6.QtCore import Qt, QTimer, QObject

from PySide6.QtGui import QPalette, QColor, QFontMetrics


from lib.ExtensionPyABC import abcExt

class UI(abcExt.UI):
    """主类"""
    def __init__(self):
        """初始化代码。用处不大"""
        
        print("亮度 初始化")
    """用于绘制自己的UI空间。需要PySide6。若没有此函数，则表示没有UI。不需要构造函数和析构函数。"""
    def ui_init(self, widget: QWidget, ext: CDLL, save: dict | None):
        self_ref = weakref.ref(self)
        self.ext = ext
        # 创建布局
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        # 提示文本
        dtext = QLabel("亮度：")
        layout.addWidget(dtext)
        # 横向布局
        layout_slider = QHBoxLayout()
        layout_slider.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(layout_slider)
        # 文本：显示当前值，右对齐
        text = QLabel("0")
        text.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout_slider.addWidget(text)
        # 文本宽度固定4个字符
        text.setFixedWidth(QFontMetrics(text.font()).horizontalAdvance("-255"))
        # 创建滑动条(-255~255)，占满宽度
        self.slider = QSlider(Qt.Orientation.Horizontal)
        layout_slider.addWidget(self.slider)
        self.slider.setRange(-255, 255)
        self.slider.setValue(0)
        # 刻度，15一格，0为起点
        self.slider.setTickInterval(15)
        # 设置PgUp/PgDn为15
        self.slider.setPageStep(15)
        # 设置刻度位置，在下方
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)

        # 回调
        def slider_changed(value):
            self = self_ref()
            if self is None: return
            # 刷新文本
            text.setText(str(value))
            # 更新
            self.Update()
        self.slider.valueChanged.connect(slider_changed)
        # 提示文本
        dtext = QLabel("生效通道：")
        layout.addWidget(dtext)
        # 横向布局
        layout_chan = QHBoxLayout()
        layout_chan.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(layout_chan)
        # 4个多选框
        chanword = ["R", "G", "B", "A"]
        chancolor = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (127, 127, 127)]
        self.checkboxs: list[QCheckBox] = []
        def checkbox_changed():
            self = self_ref()
            if self is None: return
            # 更新
            self.Update()
        for word, color in zip(chanword, chancolor):
            # 创建多选框
            checkbox = QCheckBox(word)
            # 设置前景色
            palette = checkbox.palette()
            palette.setColor(QPalette.ColorRole.WindowText, QColor(*color))
            checkbox.setPalette(palette)
            # 添加到布局
            layout_chan.addWidget(checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
            # 勾选RGB
            if word in "RGB":
                checkbox.setChecked(True)
            # 回调
            checkbox.stateChanged.connect(checkbox_changed)

            self.checkboxs.append(checkbox)

        # 更新提示文本
        self.UpdateTiptext()

    # 更新提示文本
    def UpdateTiptext(self):
        text = f"亮度: {self.slider.value()}, 通道: "
        ctext = ""
        for checkbox in self.checkboxs:
            if checkbox.isChecked():
                ctext += checkbox.text()
        if ctext == "":
            text += "无"
        else:
            text += ctext
        self.img2arr_UpdateTiptext(text)
    # 更新
    def Update(self):
        self.UpdateTiptext()
        self.img2arr_notify_update()
    def update(self, arr, threads):
        # 参数：uint8_t[op, absval, opr, opg, opb, opa]
        # op: 0为加，1为减
        # absval: 绝对值
        # opr, opg, opb, opa: 通道值
        # 0为不操作，1为操作
        arg = (c_uint8 * 6)()
        # 先判断符号
        if self.slider.value() >= 0:
            arg[0] = 0
        else:
            arg[0] = 1
        # 绝对值
        arg[1] = abs(self.slider.value())
        # 每个通道的开关
        for i, checkbox in enumerate(self.checkboxs, start=2):
            arg[i] = checkbox.isChecked()
        # 更新
        return (arg, 6)

    def __del__(self):
        print("亮度 释放")
    def ui_save(self) -> dict | None:
        return {
            "slider": self.slider.value(),
            "channels": [checkbox.isChecked() for checkbox in self.checkboxs]
        }
