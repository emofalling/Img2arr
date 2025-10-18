from __future__ import annotations

import sys

from PySide6.QtCore import QPointF, Qt

from PySide6.QtGui import QColor, QPainter, QPalette

from PySide6.QtWidgets import (QApplication, QMainWindow, QSizePolicy,

                               QWidget)

from PySide6.QtCharts import (QAreaSeries, QBarSet, QChart, QChartView,

                              QLineSeries, QPieSeries, QScatterSeries,

                              QSplineSeries, QStackedBarSeries)

from hist_example import Ui_ThemeWidgetForm as ui    

from random import random, uniform

#示例主窗口

class ThemeWidget(QWidget):

    def __init__(self, parent):

        QWidget.__init__(self, parent)

        self.charts = []   #定义本示例要用的图表:共下面6种类型

        self.ui = ui()    #为ui设置器设计的窗体实例化一对象，要调用此模块中的控件对象或继续初始化窗体布局

       

        self.ui.setupUi(self)        #初始化主窗口自身界面（使用设计器编制的窗口themewidget.ui编绎成窗口模块文件ui_themewidget.py.在终端命令行中输入：  PySide6-uic 'themewidget.ui'  -o 'ui_themewidget.py' ）

        self.populate_themebox()     #初始化显示颜色组合框

        self.populate_animationbox() #初始化动画选项组合框

        self.populate_legendbox()    #初始化图标位置组合框

       

        # 面积区域图表显示视图

        chart_view = QChartView(self.create_areachart())

        self.ui.gridLayout.addWidget(chart_view, 1, 0)   #继续完成UI设计器中没有完成的界面初始化工作:网格布局依次加入6个view

        self.charts.append(chart_view)

        #饼状图显示视图

        chart_view = QChartView(self.create_pie_chart())

        chart_view.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        self.ui.gridLayout.addWidget(chart_view, 1, 1)

        self.charts.append(chart_view)

        #折线图显示视图

        chart_view = QChartView(self.create_line_chart())

        self.ui.gridLayout.addWidget(chart_view, 1, 2)

        self.charts.append(chart_view)

        #直方图显示视图

        chart_view = QChartView(self.create_bar_chart())

        self.ui.gridLayout.addWidget(chart_view, 2, 0)

        self.charts.append(chart_view)

        #样条直线图显示视图

        chart_view = QChartView(self.create_spline_chart())

        self.ui.gridLayout.addWidget(chart_view, 2, 1)

        self.charts.append(chart_view)

        #离散点图显示视图

        chart_view = QChartView(self.create_scatterchart())

        self.ui.gridLayout.addWidget(chart_view, 2, 2)

        self.charts.append(chart_view)

        #设置默认支持抗锯齿

        self.ui.antialiasCheckBox.setChecked(True)

        #设置默认显示颜色

        pal = qApp.palette()

        pal.setColor(QPalette.Window, QColor(0xf0f0f0))

        pal.setColor(QPalette.WindowText, QColor(0x404044))

        qApp.setPalette(pal)

        self.update_ui()   #刷新一次显示

   

    #初始化颜色类型选项组合框

    def populate_themebox(self):

        theme = self.ui.themeComboBox

        theme.addItem("亮白", QChart.ChartThemeLight)

        theme.addItem("天蓝色", QChart.ChartThemeBlueCerulean)

        theme.addItem("暗色调", QChart.ChartThemeDark)

        theme.addItem("棕沙色", QChart.ChartThemeBrownSand)

        theme.addItem("蓝NCS", QChart.ChartThemeBlueNcs)

        theme.addItem("高对比", QChart.ChartThemeHighContrast)

        theme.addItem("蓝Icy", QChart.ChartThemeBlueIcy)

        theme.addItem("Qt", QChart.ChartThemeQt)

    #初始化动画类型选项组合框

    def populate_animationbox(self):

        animated = self.ui.animatedComboBox

        animated.addItem("无动画", QChart.NoAnimation)

        animated.addItem("沿网格轴动画", QChart.GridAxisAnimations)

        animated.addItem("连续动画", QChart.SeriesAnimations)

        animated.addItem("所有动画", QChart.AllAnimations)

    #初始化图例显示位置选项组合框

    def populate_legendbox(self):

        legend = self.ui.legendComboBox

        legend.addItem("无图例", 0)

        legend.addItem("图例在上", Qt.AlignTop)

        legend.addItem("图例在下", Qt.AlignBottom)

        legend.addItem("图例在左", Qt.AlignLeft)

        legend.addItem("图例在右", Qt.AlignRight)

    #1.创建面积区域类型图表

    def create_areachart(self):

        chart = QChart()

        chart.setTitle("面积区域图")

        #下面定义面积区域的三条线上的点坐标示例数据

        lstDatas1=[[0.0,1.1],[2.0,1.5],[3.0,1.8],[4.0,2.1],[5.0,2.6],[6.0,2.9]]

        lstDatas2=[[0.0,3.1],[2.0,3.5],[3.0,3.5],[4.0,4.1],[5.0,4.6],[6.0,4.9]]

        lstDatas3=[[0.0,6.1],[2.0,6.5],[3.0,6.8],[4.0,8.5],[5.0,8.9],[6.0,9.3]]

        lstDatas=[]

        lstDatas.append(lstDatas1)

        lstDatas.append(lstDatas2)

        lstDatas.append(lstDatas3)

        count=len(lstDatas1)

        #底层线位置

        lower_series = None

        name = "A"    #设置图标名前缀

        id=0

        for oneDatas in lstDatas:

            upper_series = QLineSeries(chart)        #上层线位置

            for onePoint in oneDatas:

                x=onePoint[0]

                y=onePoint[1]

                upper_series.append(QPointF(x,y))

            id+=1

            area = QAreaSeries(upper_series, lower_series)  

            area.setName(f"{name}{id}")

            chart.addSeries(area)

            lower_series = upper_series                           #下一个区的的上层线变成下一个区域的底层线

       

        chart.createDefaultAxes()

        axis_x = chart.axes(Qt.Orientation.Horizontal)[0]

        axis_x.setRange(0, count-1)    #设置X轴标区间

        axis_y = chart.axes(Qt.Vertical)[0]

        axis_y.setRange(0,10)          #设置X轴标区间

        #增加轴标在轴线外侧

        axis_y.setLabelFormat("%.1f  ")

        return chart

   

    #2.创建饼状图图表

    def create_pie_chart(self):

        chart = QChart()

        chart.setTitle("饼状图")

        series = QPieSeries(chart)

        #下面饼状图中各区域的示例值

        lstDatas=[1.0,2.0,3.0,4.0,5.0,6.0,7.0]

        count=len(lstDatas)

        id=0

        for oneBarValue in  lstDatas:

            barStr=f'饼:{id+1}'

            slc=series.append(barStr,oneBarValue)

            if(id==4):   #如当前为id=4号的饼数据时，将此饼状区域（序号4+1）单独提出来分离开显示

                slc.setLabelVisible()

                slc.setExploded()

                slc.setExplodeDistanceFactor(0.5)

            id+=1

        series.setPieSize(0.5)    #设置饼显示尺寸相对视中的占比

        chart.addSeries(series)

        return chart

   

     #3.创建折线图图表

    def create_line_chart(self):

        chart = QChart()

        chart.setTitle("线性图")

        #下面定义三组每条折线上的点坐标示例数据

        lstDatas1=[[0.0,1.1],[2.0,1.5],[3.0,1.8],[4.0,2.1],[5.0,2.6],[6.0,2.9]]

        lstDatas2=[[0.0,3.1],[2.0,3.5],[3.0,3.5],[4.0,4.1],[5.0,4.6],[8.0,4.9]]

        lstDatas3=[[0.0,6.1],[2.0,6.5],[3.0,6.8],[4.0,8.5],[5.0,8.9],[10.0,9.3]]

        lstDatas=[]

        lstDatas.append(lstDatas1)

        lstDatas.append(lstDatas2)

        lstDatas.append(lstDatas3)

        name = "C"   #设置图标名前缀

        id=0

        for oneDatas in lstDatas:

            series = QLineSeries(chart)

            for onePoint in oneDatas:

                series.append(QPointF(onePoint[0],onePoint[1]))            #得到数据中的点值要转换为QPointF

            series.setName(f"{name}{id}")                                  #为每条线(共3条)设置图标名称

            chart.addSeries(series)

            id+=1

        chart.createDefaultAxes()

        axis_x = chart.axes(Qt.Orientation.Horizontal)[0]

        axis_x.setRange(0, 10)                 #设置X轴标区间

        axis_y = chart.axes(Qt.Vertical)[0]

        axis_y.setRange(0, 10)                 #设置y轴标区间

        #增加轴标在轴线外侧

        axis_y.setLabelFormat("%.1f  ")

        return chart

   

    #4.创建直方图类型图表

    def create_bar_chart(self):

        chart = QChart()

        chart.setTitle("直方图")

        #下面定义三组数据在每个矩形上的高度示例数据

        lstDatas1=[1.0,2.0,3.0,4.0,5.0,6.0,7.0]

        lstDatas2=[1.0,3.0,5.0,7.0,2.0,4.0,6.0]

        lstDatas3=[7.0,6.0,5.0,4.0,3.0,3.0,1.0]

        lstDatas=[]

        lstDatas.append(lstDatas1)

        lstDatas.append(lstDatas2)

        lstDatas.append(lstDatas3)

        series = QStackedBarSeries(chart)

        id=0

        for oneDatas in lstDatas:                   #得到3组数据中的每一组数据

            barset = QBarSet(f"D{id}")              #为每组数据设置对象及对应图标名

            for oneRectY in oneDatas:               #得到每组数据中的Y值

                barset.append(oneRectY)

            series.append(barset)                   #共创建7项直方图(X向)，每组直方图有3个矩形区,如X轴第1列矩形的高分别为：lstDatas1[0],中间为lstDatas2[0],上部矩形为lstDatas3[0]

            id+=1

        chart.addSeries(series)

        chart.createDefaultAxes()

        axis_y = chart.axes(Qt.Vertical)[0]

        axis_y.setRange(0, 30)                  #设置Y轴网格最大高度，不用此句时，为三组数据最大值合

        axis_y.setLabelFormat("%.2f  ")         #Y轴标显示格式

        return chart

   

    #5.创建样条曲线类型图表

    def create_spline_chart(self):

        chart = QChart()

        chart.setTitle("样条曲线图")

        name = "E"    #设置图标名前缀

        #下面定义三组每条样条曲线上的点坐标示例数据

        lstDatas1=[[0.0,1.1],[2.0,1.5],[3.0,1.8],[4.0,2.1],[5.0,2.6],[6.0,2.9]]

        lstDatas2=[[0.0,3.1],[2.0,3.5],[3.0,3.5],[4.0,4.1],[5.0,4.6],[8.0,4.9]]

        lstDatas3=[[0.0,6.1],[2.0,6.5],[3.0,6.8],[4.0,8.5],[5.0,8.9],[10.0,9.3]]

        lstDatas=[]

        lstDatas.append(lstDatas1)

        lstDatas.append(lstDatas2)

        lstDatas.append(lstDatas3)

        id=0

        for oneDatas in lstDatas:

            series = QSplineSeries(chart)

            for onePoint in oneDatas:

                series.append(QPointF(onePoint[0],onePoint[1]))            #得到数据中的点值要转换为QPointF

            series.setName(f"{name}{id}")                                  #为每条线(共3条)设置图标名称

            chart.addSeries(series)

            id+=1

        chart.createDefaultAxes()

        axis_x = chart.axes(Qt.Orientation.Horizontal)[0]

        axis_x.setRange(0,10)                    #设置X轴标区间

        axis_y = chart.axes(Qt.Vertical)[0]

        axis_y.setRange(0, 10)                   #设置X轴标区间

        axis_y.setLabelFormat("%.1f  ")

        return chart

   

    #6.创建离散点类型图表

    def create_scatterchart(self):

        chart = QChart()

        chart.setTitle("离散点图")

        name = "F"

        #下面定义三组离散点坐标示例数据:共21个点

        lstDatas1=[[0.2,1.1],[2.0,1.5],[3.0,1.8],[4.0,2.1],[5.0,2.6],[6.0,2.9]]

        lstDatas2=[[0.4,3.1],[2.0,3.5],[3.0,3.5],[4.0,4.1],[5.0,4.6],[8.0,4.9]]

        lstDatas3=[[0.5,6.1],[2.0,6.5],[3.0,6.8],[4.0,8.5],[5.0,8.9],[9.8,9.3]]

        lstDatas=[]

        lstDatas.append(lstDatas1)

        lstDatas.append(lstDatas2)

        lstDatas.append(lstDatas3)

        id=0

        for oneDatas in lstDatas:

            series = QScatterSeries(chart)

            for onePoint in oneDatas:

                series.append(QPointF(onePoint[0],onePoint[1]))            #得到数据中的点值要转换为QPointF

            series.setName(f"{name}{id}")                                  #为每条线(共3条)设置图标名称

            chart.addSeries(series)

            id+=1

        chart.createDefaultAxes()

        axis_x = chart.axes(Qt.Orientation.Horizontal)[0]

        axis_x.setRange(0,10)          #设置X轴标区间(最大值为数据中的X最大值)

        axis_y = chart.axes(Qt.Vertical)[0]

        axis_y.setRange(0, 10)         #设置y轴标区间 (最大值为数据中的y最大值)

        axis_y.setLabelFormat("%.1f  ")

        return chart

   

    #按当前的设置选项更新显示视图:组合框选项发生变化时均会自动调用此函数,本例无需定义对应的信号槽函数?

    def update_ui(self):

        def set_colors(window_color, text_color):

            pal = self.window().palette()

            pal.setColor(QPalette.Window, window_color)

            pal.setColor(QPalette.WindowText, text_color)

            self.window().setPalette(pal)

        idx = self.ui.themeComboBox.currentIndex()

        theme = self.ui.themeComboBox.itemData(idx)

        if len(self.charts):

            chart_theme = self.charts[0].chart().theme()

            if chart_theme != theme:

                for chart_view in self.charts:

                    chart_view.chart().setTheme(theme)

                #根据选择的类型更新颜色面板

                if theme == QChart.ChartThemeLight:

                    set_colors(QColor(0xf0f0f0), QColor(0x404044))

                elif theme == QChart.ChartThemeDark:

                    set_colors(QColor(0x121218), QColor(0xd6d6d6))

                elif theme == QChart.ChartThemeBlueCerulean:

                    set_colors(QColor(0x40434a), QColor(0xd6d6d6))

                elif theme == QChart.ChartThemeBrownSand:

                    set_colors(QColor(0x9e8965), QColor(0x404044))

                elif theme == QChart.ChartThemeBlueNcs:

                    set_colors(QColor(0x018bba), QColor(0x404044))

                elif theme == QChart.ChartThemeHighContrast:

                    set_colors(QColor(0xffab03), QColor(0x181818))

                elif theme == QChart.ChartThemeBlueIcy:

                    set_colors(QColor(0xcee7f0), QColor(0x404044))

                else:

                    set_colors(QColor(0xf0f0f0), QColor(0x404044))

        # 更新抗锯齿显示

        checked = self.ui.antialiasCheckBox.isChecked()

        for chart in self.charts:

            chart.setRenderHint(QPainter.RenderHint.Antialiasing, checked)

        #更新动画显示

        idx = self.ui.animatedComboBox.currentIndex()

        options = self.ui.animatedComboBox.itemData(idx)

        if len(self.charts):

            animation_options = self.charts[0].chart().animationOptions()

            if animation_options != options:

                for chart_view in self.charts:

                    chart_view.chart().setAnimationOptions(options)

        # 更新图例显示位置

        idx = self.ui.legendComboBox.currentIndex()

        alignment = self.ui.legendComboBox.itemData(idx)

        if not alignment:

            for chart_view in self.charts:

                chart_view.chart().legend().hide()

        else:

            for chart_view in self.charts:

                alignment_name = Qt.AlignTop

                if alignment == 32:

                    alignment_name = Qt.AlignTop

                elif alignment == 64:

                    alignment_name = Qt.AlignBottom

                elif alignment == 1:

                    alignment_name = Qt.AlignLeft

                elif alignment == 2:

                    alignment_name = Qt.AlignRight

                chart_view.chart().legend().setAlignment(alignment_name)

                chart_view.chart().legend().show()

#程序入口

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = QMainWindow()

    widget = ThemeWidget(None)

    window.setCentralWidget(widget)

    available_geometry = window.screen().availableGeometry()

    size = available_geometry.height() * 1.0

    window.setFixedSize(size, size *0.85)

    window.show()

    window.setWindowTitle('PySide6.QtCharts的6种方式显示图表')

   

    sys.exit(app.exec())