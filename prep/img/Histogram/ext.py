import json
import numpy as np
from numpy.typing import NDArray
from ctypes import CDLL, c_void_p, c_uint64, c_double, c_size_t, POINTER, addressof, _Pointer
import math
import weakref

from typing import Optional

from lib import ColorStandard

from PySide6.QtWidgets import QApplication, QWidget, QLabel, QCheckBox, QSlider, QVBoxLayout, QHBoxLayout, QSizePolicy, QRadioButton, QButtonGroup
# 直方图
from PySide6.QtCharts import QChart, QChartView, QAreaSeries, QLineSeries, QValueAxis

from PySide6.QtCore import Qt, QTimer, QObject, QPointF, Signal

from PySide6.QtGui import QPalette, QColor, QFontMetrics, QPen

import logging

logger = logging.getLogger(__name__)

from lib.ExtensionPyABC import abcExt

class HistChartSignal(QObject):
    """用于传递直方图数据的信号"""
    update = Signal(list, list, list, list, 
                    list, list, list, list)

class UI(abcExt.UI):
    """主类"""
    def __init__(self):
        """初始化代码。用处不大"""
        self.threads = 1
        self.r_arr: NDArray[np.float64] = np.array([])
        self.g_arr: NDArray[np.float64] = np.array([])
        self.b_arr: NDArray[np.float64] = np.array([])
        self.a_arr: NDArray[np.float64] = np.array([])
        print("亮度 初始化")
    """用于绘制自己的UI空间。需要PySide6。若没有此函数，则表示没有UI。不需要构造函数和析构函数。"""
    def ui_init(self, widget: QWidget, ext: CDLL, save: dict | None):
        self_ref = weakref.ref(self)
        self.ext = ext
        # 创建布局
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        # 单选框：选择通道
        channel_button_layout = QHBoxLayout()
        channel_button_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(channel_button_layout)
        self.channel_group = QButtonGroup(widget)
        self.channel_group.buttonClicked.connect(lambda: self.ui_update() if (self := self_ref()) else logger.error("self_ref()返回None"))
        self.radio_channel_red = QRadioButton("红色")
        self.radio_channel_green = QRadioButton("绿色")
        self.radio_channel_blue = QRadioButton("蓝色")
        self.radio_channel_alpha = QRadioButton("透明度")
        self.radio_channel_rgb = QRadioButton("RGB")

        self.channel_group.addButton(self.radio_channel_red)
        self.channel_group.addButton(self.radio_channel_green)
        self.channel_group.addButton(self.radio_channel_blue)
        self.channel_group.addButton(self.radio_channel_alpha)
        self.channel_group.addButton(self.radio_channel_rgb)
        # 默认选择RGB
        self.radio_channel_rgb.setChecked(True)
        channel_button_layout.addWidget(self.radio_channel_red, alignment=Qt.AlignmentFlag.AlignCenter)
        channel_button_layout.addWidget(self.radio_channel_green, alignment=Qt.AlignmentFlag.AlignCenter)
        channel_button_layout.addWidget(self.radio_channel_blue, alignment=Qt.AlignmentFlag.AlignCenter)
        channel_button_layout.addWidget(self.radio_channel_alpha, alignment=Qt.AlignmentFlag.AlignCenter)
        channel_button_layout.addWidget(self.radio_channel_rgb, alignment=Qt.AlignmentFlag.AlignCenter)



        # 图表
        self.hist_chart = QChart()
        self.hist_chart.legend().hide() # 隐藏图例标题
        self.hist_chart.setMinimumHeight(300)
        # 上下边界数据
        self.series_red   = QLineSeries()
        self.series_green = QLineSeries()
        self.series_blue  = QLineSeries()
        self.series_rg    = QLineSeries()
        self.series_gb    = QLineSeries()
        self.series_rb    = QLineSeries()
        self.series_rgb   = QLineSeries()
        self.series_alpha = QLineSeries()


        # 创建面积图系列，按正确的层叠顺序
        # 最底层：RGB交集（白色）
        self.area_rgb = QAreaSeries(self.series_rgb)
        self.area_alpha = QAreaSeries(self.series_alpha) # A
        # 中间层：两两交集
        self.area_rg = QAreaSeries(self.series_rg, self.series_rgb)    # RG在RGB之上
        self.area_gb = QAreaSeries(self.series_gb, self.series_rgb)    # GB在RGB之上  
        self.area_rb = QAreaSeries(self.series_rb, self.series_rgb)    # RB在RGB之上
        # 最下层：单通道
        self.area_red = QAreaSeries(self.series_red
                                    #, self.series_rg
                                    )   # R在RG之上
        self.area_green = QAreaSeries(self.series_green
                                    #, self.series_rg
                                    ) # G在RG之上
        self.area_blue = QAreaSeries(self.series_blue
                                    #, self.series_gb
                                    ) # B在GB之上

        # 创建XY轴
        self.axis_x = QValueAxis()
        self.axis_x.setRange(0, 255)
        # X轴每隔51个单位显示一个刻度，不显示值
        self.axis_x.setTickCount(6)
        self.axis_x.setLabelsVisible(False)
        # 次要刻度线：每17个单位显示一个
        # self.axis_x.setMinorTickCount(2)

        self.axis_y = QValueAxis()
        self.axis_y.setRange(0.0, 1.0)
        # Y轴不显示刻度
        self.axis_y.setGridLineVisible(False)
        self.axis_y.setLineVisible(False)
        self.axis_y.setLabelsVisible(False)
        # 将XY轴添加到图表
        self.hist_chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.hist_chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)
        # 设置样式
        rpen = QPen(QColor(255, 0, 0), 2)
        gpen = QPen(QColor(0, 255, 0), 2)
        bpen = QPen(QColor(0, 0, 255), 2)
        rgpen = QPen(QColor(255, 255, 0), 2)
        gbpen  = QPen(QColor(0, 255, 255), 2)
        rbpen  = QPen(QColor(255, 0, 255), 2)
        rgbpen = QPen(QColor(240, 240, 240), 2)
        apen = QPen(QColor(240, 240, 240), 2)
        # 设置线宽
        rpen.setWidth(1)
        gpen.setWidth(1)
        bpen.setWidth(1)
        rgpen.setWidth(1)
        gbpen.setWidth(1)
        rbpen.setWidth(1)
        rgbpen.setWidth(1)
        apen.setWidth(1)

        self.area_red.setPen(rpen)
        self.area_green.setPen(gpen)
        self.area_blue.setPen(bpen)
        self.area_rg.setPen(rgpen)
        self.area_gb.setPen(gbpen)
        self.area_rb.setPen(rbpen)
        self.area_rgb.setPen(rgbpen)
        self.area_alpha.setPen(apen)
        # 设置颜色和透明度
        # 单通道：纯色，半透明
        self.area_red.setColor(QColor(255, 0, 0))
        self.area_green.setColor(QColor(0, 255, 0))  
        self.area_blue.setColor(QColor(0, 0, 255))

        # 双通道交集：混合色，半透明
        self.area_rg.setColor(QColor(255, 255, 0))    # 红+绿=黄
        self.area_gb.setColor(QColor(0, 255, 255))    # 绿+蓝=青
        self.area_rb.setColor(QColor(255, 0, 255))    # 红+蓝=品红

        # 三通道交集：白色，不透明
        self.area_rgb.setColor(QColor(240, 240, 240))
    
        self.area_alpha.setColor(QColor(240, 240, 240))
        # 将面积图系列添加到图表
        self.hist_chart.addSeries(self.area_red)
        self.hist_chart.addSeries(self.area_green)
        self.hist_chart.addSeries(self.area_blue)
        self.hist_chart.addSeries(self.area_rg)
        self.hist_chart.addSeries(self.area_gb)
        self.hist_chart.addSeries(self.area_rb)
        self.hist_chart.addSeries(self.area_rgb)
        self.hist_chart.addSeries(self.area_alpha)
        # 绑定XY轴
        self.area_red.attachAxis(self.axis_x)
        self.area_red.attachAxis(self.axis_y)
        self.area_green.attachAxis(self.axis_x)
        self.area_green.attachAxis(self.axis_y)
        self.area_blue.attachAxis(self.axis_x)
        self.area_blue.attachAxis(self.axis_y)
        self.area_rg.attachAxis(self.axis_x)
        self.area_rg.attachAxis(self.axis_y)
        self.area_gb.attachAxis(self.axis_x)
        self.area_gb.attachAxis(self.axis_y)
        self.area_rb.attachAxis(self.axis_x)
        self.area_rb.attachAxis(self.axis_y)
        self.area_rgb.attachAxis(self.axis_x)
        self.area_rgb.attachAxis(self.axis_y)
        self.area_alpha.attachAxis(self.axis_x)
        self.area_alpha.attachAxis(self.axis_y)

        # 创建图表视图
        self.chart_view = QChartView(self.hist_chart)
        # 绑定到布局
        layout.addWidget(self.chart_view)
        # 最初每个图表都有空点
        for i in range(256):
            self.series_red.append(i, 0)
            self.series_green.append(i, 0)
            self.series_blue.append(i, 0)
            self.series_rg.append(i, 0)
            self.series_gb.append(i, 0)
            self.series_rb.append(i, 0)
            self.series_rgb.append(i, 0)
        # 创建信号
        self.signal = HistChartSignal()
        self.signal.update.connect(lambda r, g, b, a, rg, gb, rb, rgb: self.UpdateChart(r, g, b, a, rg, gb, rb, rgb) if (self := self_ref()) else logger.error("self_ref()返回None"))
        # 对数化多选框
        self.log_checkbox = QCheckBox("对数化")
        # self.log_checkbox.setChecked(True)
        self.log_checkbox.stateChanged.connect(lambda: self.ui_update() if (self := self_ref()) else logger.error("self_ref()返回None"))
        layout.addWidget(self.log_checkbox)

    # 更新提示文本
    def UpdateTiptext(self):
        text = f""
        self.img2arr_UpdateTiptext(text)
    # 更新
    def Update(self):
        self.UpdateTiptext()
        self.img2arr_notify_update()
    
    item_type = type((c_uint64 * 256)(0))

    def update(self, arr, threads):
      # [pack]struct{
      # [pack]struct{
      #     uint64_t [out]R[256]; // 直方图求和结果：R
      #     uint64_t [out]G[256]; // 直方图求和结果：G
      #     uint64_t [out]B[256]; // 直方图求和结果：B
      #     uint64_t [out]A[256]; // 直方图求和结果：A
      # }对于单线程
      # [pack]struct{
      #     uint64_t [out]R[256 * thread]; // 每个任务的直方图求和结果：R
      #     uint64_t [out]G[256 * thread]; // 每个任务的直方图求和结果：G
      #     uint64_t [out]B[256 * thread]; // 每个任务的直方图求和结果：B
      #     uint64_t [out]A[256 * thread]; // 每个任务的直方图求和结果：A
      # }对于多线程
        if threads > 1:# 多线程
            r = (c_uint64 * (256 * threads))(0)
            g = (c_uint64 * (256 * threads))(0)
            b = (c_uint64 * (256 * threads))(0)
            a = (c_uint64 * (256 * threads))(0)
            arg = (POINTER(c_uint64) * 4)(r, g, b, a)
                
        elif threads == 1: # 单线程
            r = (c_uint64 * 256)(0)
            g = (c_uint64 * 256)(0)
            b = (c_uint64 * 256)(0)
            a = (c_uint64 * 256)(0)
            arg = (POINTER(c_uint64) * 4)(r, g, b, a)

        else:# OpenCL
            raise Exception("OpenCL不支持")
        
        self.threads = threads

        return (arg, 8 * 4 * threads)

    def update_end(self, arg, arglen):

        if self.threads == 1:
            # 单线程情况
            r = np.frombuffer((c_uint64 * 256).from_address(addressof(arg[0].contents)), dtype=np.uint64)
            g = np.frombuffer((c_uint64 * 256).from_address(addressof(arg[1].contents)), dtype=np.uint64)
            b = np.frombuffer((c_uint64 * 256).from_address(addressof(arg[2].contents)), dtype=np.uint64)
            a = np.frombuffer((c_uint64 * 256).from_address(addressof(arg[3].contents)), dtype=np.uint64)

            r_result, g_result, b_result, a_result = r, g, b, a
        else:
            # 多线程情况
            threads = self.threads
            total_size = 256 * threads

            r_flat = np.frombuffer((c_uint64 * total_size).from_address(addressof(arg[0].contents)), dtype=np.uint64, count=total_size)
            g_flat = np.frombuffer((c_uint64 * total_size).from_address(addressof(arg[1].contents)), dtype=np.uint64, count=total_size)
            b_flat = np.frombuffer((c_uint64 * total_size).from_address(addressof(arg[2].contents)), dtype=np.uint64, count=total_size)
            a_flat = np.frombuffer((c_uint64 * total_size).from_address(addressof(arg[3].contents)), dtype=np.uint64, count=total_size)

            r_2d = r_flat.reshape(threads, 256)
            g_2d = g_flat.reshape(threads, 256)
            b_2d = b_flat.reshape(threads, 256)
            a_2d = a_flat.reshape(threads, 256)

            r_result = np.sum(r_2d, axis=0, dtype=np.uint64)
            g_result = np.sum(g_2d, axis=0, dtype=np.uint64)
            b_result = np.sum(b_2d, axis=0, dtype=np.uint64)
            a_result = np.sum(a_2d, axis=0, dtype=np.uint64)

        # 明确转换
        self.r_arr = np.array(r_result, dtype=np.float64)
        self.g_arr = np.array(g_result, dtype=np.float64)
        self.b_arr = np.array(b_result, dtype=np.float64)
        self.a_arr = np.array(a_result, dtype=np.float64)

        self.ui_update()

    def ui_update(self):

        r = self.r_arr.copy()
        g = self.g_arr.copy()
        b = self.b_arr.copy()
        a = self.a_arr.copy()

        log = self.log_checkbox.isChecked()

        if self.radio_channel_red.isChecked():
            check = "R"
        elif self.radio_channel_green.isChecked():
            check = "G"
        elif self.radio_channel_blue.isChecked():
            check = "B"
        elif self.radio_channel_alpha.isChecked():
            check = "A"
        elif self.radio_channel_rgb.isChecked():
            check = "RGB"
        else:
            raise Exception("未选择通道")

        # 如果勾选了对数化，则对数化
        if log:
            r = np.log1p(r)
            g = np.log1p(g)
            b = np.log1p(b)
            a = np.log1p(a)

        # 各通道归一化
        # 如果仅R, R归一化
        if check == "R":
            maxv = np.max(r)
            if maxv != 0.0:
                r /= maxv
            # else:
            #     r[:] = 0
        # 如果仅G, G归一化
        elif check == "G":
            maxv = np.max(g)
            if maxv != 0.0:
                g /= maxv
            # else:
            #     g[:] = 0
        # 如果仅B, B归一化
        elif check == "B":
            maxv = np.max(b)
            if maxv != 0.0:
                b /= maxv
            # else:
            #     b[:] = 0
        # 如果仅A, A归一化
        elif check == "A":
            maxv = np.max(a)
            if maxv != 0.0:
                a /= maxv
            # else:
            #     a[:] = 0
        # 如果RGB, RGB归一化
        elif check == "RGB":
            maxv = max(np.max(r), np.max(g), np.max(b))
            if maxv != 0.0:
                r /= maxv
                g /= maxv
                b /= maxv
                # a /= maxv
            # else:
            #     r[:] = 0
            #     g[:] = 0
            #     b[:] = 0
        else:
            raise Exception("未选择通道")

        # 对于RGB，准备rg, gb, rb, rgb
        if check == "RGB":
            rg, gb, rb = np.minimum(r, g), np.minimum(g, b), np.minimum(r, b)
            rgb = np.minimum(rg, b)
        else:
            rg, gb, rb, rgb = [], [], [], [] # 如果执行到这一行，说明之后的代码不会使用到这些变量

        # 生成点
        r_points, g_points, b_points, a_points = [], [], [], []
        rg_points, gb_points, rb_points, rgb_points = [], [], [], []
        if check in ("R", "RGB"):
            r_points = [QPointF(i, r[i]) for i in range(256)]
        if check in ("G", "RGB"):
            g_points = [QPointF(i, g[i]) for i in range(256)]
        if check in ("B", "RGB"):
            b_points = [QPointF(i, b[i]) for i in range(256)]
        if check == "A":
            a_points = [QPointF(i, a[i]) for i in range(256)]
        if check == "RGB":
            rg_points  = [QPointF(i, rg[i]) for i in range(256)]
            gb_points  = [QPointF(i, gb[i]) for i in range(256)]
            rb_points  = [QPointF(i, rb[i]) for i in range(256)]
            rgb_points = [QPointF(i, rgb[i]) for i in range(256)]


        # 更新
        self.signal.update.emit(r_points, g_points, b_points, a_points, rg_points, gb_points, rb_points, rgb_points)

    def UpdateChart(self, r: list[QPointF], g: list[QPointF], b: list[QPointF], a: list[QPointF],
                    rg: list[QPointF], gb: list[QPointF], rb: list[QPointF], rgb: list[QPointF]):
        # 更新图表
        # 暂停更新
        # 先暂停更新，然后更新数据，最后恢复更新
        self.chart_view.setUpdatesEnabled(False)
        # 先生成点
        # 更新点
        self.series_red.replace(r)
        self.series_green.replace(g)
        self.series_blue.replace(b)
        self.series_rg.replace(rg)
        self.series_gb.replace(gb)
        self.series_rb.replace(rb)
        self.series_rgb.replace(rgb)
        self.series_alpha.replace(a)

        self.chart_view.setUpdatesEnabled(True)

        

    def __del__(self):
        print("图片图表 释放")
    def ui_save(self):
        # 实现时请务必更改函数名
        pass
