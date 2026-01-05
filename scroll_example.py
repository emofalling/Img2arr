import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollBar, QFrame, QLabel, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QRect, QSize
from PySide6.QtGui import QPaintEvent, QPainter

class CustomScrollArea(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_scrollbars()
        
    def setup_ui(self):
        # 设置框架样式
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)
        self.setStyleSheet("CustomScrollArea { border: 1px solid #cccccc; background: white; }")
        
        # 主布局
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建内容区域和滚动条的容器
        self.content_container = QWidget()
        self.content_container_layout = QVBoxLayout(self.content_container)
        self.content_container_layout.setSpacing(0)
        self.content_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # 视口部件 - 实际显示内容的区域
        self.viewport = QFrame()
        self.viewport.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.viewport.setStyleSheet("background: transparent;")
        
        # 内容部件 - 承载实际内容的部件
        self.content_widget = None
        self.content_layout = QVBoxLayout(self.viewport)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        
        # 滚动条
        self.vertical_scrollbar = QScrollBar(Qt.Orientation.Vertical)
        self.horizontal_scrollbar = QScrollBar(Qt.Orientation.Horizontal)
        
        # 组装界面
        self.content_container_layout.addWidget(self.viewport)
        self.content_container_layout.addWidget(self.horizontal_scrollbar)
        
        self.main_layout.addWidget(self.content_container)
        self.main_layout.addWidget(self.vertical_scrollbar)
        
        # 滚动状态
        self.horizontal_scroll_value = 0
        self.vertical_scroll_value = 0
        
        # 内容尺寸
        self.content_width = 0
        self.content_height = 0
        
    def setup_scrollbars(self):
        """设置滚动条属性和信号连接"""
        # 垂直滚动条
        self.vertical_scrollbar.setPageStep(100)
        self.vertical_scrollbar.valueChanged.connect(self.on_vertical_scroll)
        
        # 水平滚动条
        self.horizontal_scrollbar.setPageStep(100)
        self.horizontal_scrollbar.valueChanged.connect(self.on_horizontal_scroll)
        
        # 初始隐藏滚动条
        self.vertical_scrollbar.setVisible(False)
        self.horizontal_scrollbar.setVisible(False)
    
    def setWidget(self, widget):
        """设置内容部件"""
        if self.content_widget:
            self.content_widget.deleteLater()
            
        self.content_widget = widget
        self.content_layout.addWidget(widget)
        
        # 延迟更新滚动条，等待布局完成
        QTimer.singleShot(0, self.update_scrollbars)
    
    def on_vertical_scroll(self, value):
        """垂直滚动处理"""
        self.vertical_scroll_value = value
        self.update_content_position()
    
    def on_horizontal_scroll(self, value):
        """水平滚动处理"""
        self.horizontal_scroll_value = value
        self.update_content_position()
    
    def update_content_position(self):
        """更新内容位置"""
        if not self.content_widget:
            return
            
        # 计算内容偏移
        viewport_size = self.viewport.size()
        content_size = self.content_widget.sizeHint()
        
        x_offset = -self.horizontal_scroll_value
        y_offset = -self.vertical_scroll_value
        
        # 如果内容小于视口，则居中显示
        if content_size.width() < viewport_size.width():
            x_offset = (viewport_size.width() - content_size.width()) // 2
            
        if content_size.height() < viewport_size.height():
            y_offset = (viewport_size.height() - content_size.height()) // 2
        
        # 移动内容部件
        self.content_widget.move(x_offset, y_offset)
    
    def update_scrollbars(self):
        """更新滚动条状态和范围"""
        if not self.content_widget:
            return
            
        viewport_size = self.viewport.size()
        content_size = self.content_widget.sizeHint()
        
        # 更新内容尺寸
        self.content_width = content_size.width()
        self.content_height = content_size.height()
        
        # 检查是否需要显示滚动条
        need_vertical = content_size.height() > viewport_size.height()
        need_horizontal = content_size.width() > viewport_size.width()
        
        # 显示/隐藏滚动条
        self.vertical_scrollbar.setVisible(need_vertical)
        self.horizontal_scrollbar.setVisible(need_horizontal)
        
        # 设置滚动条范围
        if need_vertical:
            self.vertical_scrollbar.setRange(0, max(0, content_size.height() - viewport_size.height()))
            self.vertical_scrollbar.setPageStep(viewport_size.height())
        
        if need_horizontal:
            self.horizontal_scrollbar.setRange(0, max(0, content_size.width() - viewport_size.width()))
            self.horizontal_scrollbar.setPageStep(viewport_size.width())
        
        # 更新内容位置
        self.update_content_position()
    
    def resizeEvent(self, event):
        """重写 resize 事件"""
        super().resizeEvent(event)
        self.update_scrollbars()
    
    def wheelEvent(self, event):
        """重写滚轮事件"""
        if self.vertical_scrollbar.isVisible():
            delta = event.angleDelta().y()
            new_value = self.vertical_scrollbar.value() - delta // 3
            self.vertical_scrollbar.setValue(new_value)
            event.accept()
        else:
            event.ignore()

class DemoContentWidget(QWidget):
    """演示用的内容部件"""
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 添加一些示例内容
        for i in range(20):
            label = QLabel(f"项目 {i+1}: 这是一个自定义滚动区域的演示内容 " * (i % 3 + 1))
            label.setWordWrap(True)
            label.setStyleSheet(f"""
                QLabel {{
                    background-color: {'#e8f4fd' if i % 2 == 0 else '#f0f8ff'};
                    padding: 12px;
                    border: 1px solid #d0d0d0;
                    border-radius: 5px;
                }}
            """)
            label.setMinimumWidth(400 if i % 2 == 0 else 300)
            layout.addWidget(label)
        
        # 添加一个宽内容测试水平滚动
        wide_label = QLabel("这是一个很宽的内容，用于测试水平滚动条的功能 " * 10)
        wide_label.setStyleSheet("""
            QLabel {
                background-color: #fff0f0;
                padding: 15px;
                border: 2px dashed #ff9999;
                border-radius: 5px;
            }
        """)
        wide_label.setMinimumWidth(1200)
        layout.addWidget(wide_label)

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("自定义 QScrollArea 实现")
        self.resize(600, 400)
        
        # 创建主部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 添加控制按钮
        control_layout = QHBoxLayout()
        
        btn_add_content = QPushButton("添加内容")
        btn_add_content.clicked.connect(self.add_content)
        
        btn_clear = QPushButton("清空内容")
        btn_clear.clicked.connect(self.clear_content)
        
        control_layout.addWidget(btn_add_content)
        control_layout.addWidget(btn_clear)
        control_layout.addStretch()
        
        main_layout.addLayout(control_layout)
        
        # 创建自定义滚动区域
        self.scroll_area = CustomScrollArea()
        self.scroll_area.setMinimumSize(400, 300)
        
        # 设置初始内容
        self.set_initial_content()
        
        main_layout.addWidget(self.scroll_area)
    
    def set_initial_content(self):
        """设置初始内容"""
        content_widget = DemoContentWidget()
        self.scroll_area.setWidget(content_widget)
    
    def add_content(self):
        """动态添加内容"""
        if not hasattr(self, 'content_count'):
            self.content_count = 21
        
        new_label = QLabel(f"动态添加的项目 {self.content_count}")
        new_label.setStyleSheet("""
            QLabel {
                background-color: #f0fff0;
                padding: 10px;
                border: 2px solid #99ff99;
                border-radius: 5px;
            }
        """)
        new_label.setMinimumWidth(350)
        
        # 获取当前内容部件的布局并添加新标签
        current_widget = self.scroll_area.content_widget
        if current_widget and hasattr(current_widget, 'layout'):
            current_widget.layout().addWidget(new_label)
            self.content_count += 1
            
            # 更新滚动条
            QTimer.singleShot(50, self.scroll_area.update_scrollbars)
    
    def clear_content(self):
        """清空内容"""
        if self.scroll_area.content_widget:
            self.scroll_area.content_widget.deleteLater()
            self.scroll_area.content_widget = None
            self.scroll_area.update_scrollbars()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())