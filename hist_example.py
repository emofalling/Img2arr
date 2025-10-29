from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QAreaSeries, QValueAxis
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, QPointF

def create_seamless_area_histogram():
    app = QApplication([])
    
    window = QMainWindow()
    window.setWindowTitle("无间隙像素直方图")
    
    # 模拟像素数据（256个值）
    data = [0] * 256
    for i in range(50, 150):
        data[i] = int(30 * (1 - abs(i-100)/50))
    for i in range(180, 220):
        data[i] = int(20 * (1 - abs(i-200)/20))
    
    # 创建上边界线（直方图顶部）
    upper_series = QLineSeries()
    # 创建下边界线（y=0）
    lower_series = QLineSeries()
    
    # 创建完全连续的直方图
    for i in range(len(data)):
        # 每个像素值对应一个点，形成连续区域
        upper_series.append(QPointF(i, data[i]))
        lower_series.append(QPointF(i, 0))
    
    # 为了闭合区域，添加最后一个点
    upper_series.append(QPointF(len(data)-1, 0))
    
    # 创建区域系列（这会填充整个区域，没有间隙）
    area_series = QAreaSeries(upper_series, lower_series)
    area_series.setColor(QColor(100, 100, 100))
    area_series.setBorderColor(QColor(100, 100, 100))
    
    chart = QChart()
    chart.addSeries(area_series)
    chart.setTitle("图像像素值分布直方图")
    
    # 设置坐标轴
    axisX = QValueAxis()
    axisX.setRange(0, 255)
    axisX.setTitleText("像素值")
    axisX.setGridLineVisible(False)
    axisX.setLineVisible(False)
    chart.addAxis(axisX, Qt.AlignBottom)
    area_series.attachAxis(axisX)
    
    axisY = QValueAxis()
    axisY.setRange(0, max(data) * 1.1)
    axisY.setTitleText("像素数量")
    axisY.setGridLineVisible(False)
    axisY.setLineVisible(False)
    chart.addAxis(axisY, Qt.AlignLeft)
    area_series.attachAxis(axisY)
    
    chart.legend().setVisible(False)
    chart.setBackgroundVisible(False)
    
    chart_view = QChartView(chart)
    chart_view.setRenderHint(QPainter.Antialiasing)
    chart_view.setStyleSheet("background-color: white; border: none;")
    
    window.setCentralWidget(chart_view)
    window.resize(800, 400)
    window.show()
    
    app.exec()

create_seamless_area_histogram()