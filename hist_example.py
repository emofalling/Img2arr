from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCharts import QChart, QChartView, QBarSet, QBarSeries, QBarCategoryAxis, QValueAxis
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtCore import Qt, QMargins, QPointF

def create_borderless_histogram():
    app = QApplication([])
    
    # 创建主窗口
    window = QMainWindow()
    window.setWindowTitle("无边缘直方图")
    
    # 准备直方图数据
    data = [15, 20, 30, 35, 25, 20, 15, 10, 5, 10, 20, 30]
    bins = ['0-50', '51-100', '101-150', '151-200', '201-250', '251-300', 
           '301-350', '351-400', '401-450', '451-500', '501-550', '551-600']
    
    # 创建条形数据集
    bar_set = QBarSet("像素数量")
    for value in data:
        bar_set.append(value)
    
    # 关键设置1：移除条形的边框
    bar_set.setPen(QPen(Qt.NoPen))  # 无边框
    
    # 关键设置2：设置纯色填充，无效果
    bar_set.setColor(QColor(100, 100, 100))  # 简单的灰色
    bar_set.setBorderColor(QColor(0, 0, 0, 0))  # 透明边框颜色
    
    # 创建条形系列
    series = QBarSeries()
    series.append(bar_set)
    series.setBarWidth(1.0)
    
    # 创建图表
    chart = QChart()
    chart.addSeries(series)
    chart.setTitle("图像像素值分布直方图")
    
    # 关键设置3：使用最简洁的主题
    chart.setTheme(QChart.ChartThemeLight)  # 简洁主题
    
    # 关键设置4：完全移除图表边距和背景效果
    chart.setBackgroundRoundness(0)
    chart.setMargins(QMargins(0, 0, 0, 0))
    chart.setBackgroundVisible(False)  # 移除背景
    
    # 设置X轴
    axisX = QBarCategoryAxis()
    axisX.append(bins)
    axisX.setTitleText("像素值范围")
    chart.addAxis(axisX, Qt.AlignBottom)
    series.attachAxis(axisX)
    
    # 关键设置5：移除X轴的线条
    axisX.setLineVisible(False)
    axisX.setGridLineVisible(False)
    
    # 设置Y轴
    axisY = QValueAxis()
    axisY.setRange(0, max(data) * 1.1)
    axisY.setTitleText("像素数量")
    chart.addAxis(axisY, Qt.AlignLeft)
    series.attachAxis(axisY)
    
    # 移除图例
    chart.legend().setVisible(False)
    
    # 创建图表视图
    chart_view = QChartView(chart)
    chart_view.setRenderHint(QPainter.Antialiasing)
    
    # 关键设置6：设置视图背景为白色
    chart_view.setStyleSheet("background-color: white; border: none;")
    
    window.setCentralWidget(chart_view)
    window.resize(800, 600)
    window.show()
    
    app.exec()

create_borderless_histogram()