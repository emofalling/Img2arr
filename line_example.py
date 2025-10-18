from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtCore import Qt, QPointF, QMargins

def create_line_based_histogram():
    app = QApplication([])
    
    window = QMainWindow()
    window.setWindowTitle("线条模拟直方图")
    
    # 准备数据
    data = [15, 20, 30, 35, 25, 20, 15, 10, 5, 10, 20, 30]
    
    # 创建线条系列
    series = QLineSeries()
    series.setName("像素数量")
    
    # 关键：使用阶梯线模拟直方图柱子
    for i, value in enumerate(data):
        # 每个柱子的左边缘从0开始上升到值
        series.append(i, 0)
        series.append(i, value)
        # 每个柱子的右边缘保持在值位置
        series.append(i + 1, value)
        series.append(i + 1, 0)
    
    # 设置线条样式 - 较粗的线条来模拟柱子
    pen = QPen(QColor(100, 100, 100))
    # pen.setWidth(100)  # 设置线条宽度来模拟柱子宽度
    pen.setCapStyle(Qt.FlatCap)  # 平头端点，避免圆角
    series.setPen(pen)
    
    # 创建图表
    chart = QChart()
    chart.addSeries(series)
    chart.setTitle("图像像素值分布直方图")
    chart.setAnimationOptions(QChart.NoAnimation)
    
    # 设置X轴
    axisX = QValueAxis()
    axisX.setRange(0, len(data))
    axisX.setTitleText("像素值范围")
    axisX.setTickCount(len(data) + 1)
    axisX.setLabelFormat("%d")
    chart.addAxis(axisX, Qt.AlignBottom)
    series.attachAxis(axisX)
    
    # 设置Y轴
    axisY = QValueAxis()
    axisY.setRange(0, max(data) * 1.1)
    axisY.setTitleText("像素数量")
    chart.addAxis(axisY, Qt.AlignLeft)
    series.attachAxis(axisY)
    
    # 优化图表显示
    chart.legend().setVisible(False)
    chart.setMargins(QMargins(0, 0, 0, 0))
    
    chart_view = QChartView(chart)
    chart_view.setRenderHint(QPainter.Antialiasing)
    
    window.setCentralWidget(chart_view)
    window.resize(800, 600)
    window.show()
    
    app.exec()

create_line_based_histogram()