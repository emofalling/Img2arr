"""
本程序可以单独打开，用于测试屏幕色域以及PySide6的支持性。
"""
import sys

from PySide6.QtWidgets import (
    QApplication, QMainWindow,
    QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget,
    QLabel, QPushButton,
    QSizePolicy,
)

from PySide6.QtCore import QObject

from PySide6.QtGui import QImage

from PySide6.QtCore import Qt

from PySide6.QtOpenGLWidgets import QOpenGLWidget

try:
    import OpenGL.GL as gl
    support_opengl = True
except ImportError:
    print("OpenGL库未找到，将无法显示OpenGL内容。")
    support_opengl = False

from lib.CustomWidgets import CustomUI

import numpy

print("正在生成测试图片...")

# 测试图片1: 数组uint16_t[H][W][C:4], H=250*4(R G B GRAY), W=65535
# 格式：Format_RGBX64
H_i = 250
W = 65536
img_depthtest_device = numpy.zeros((H_i*4, W, 4), dtype=numpy.uint16)
gradient = numpy.linspace(0, 65535, W, dtype=numpy.uint16)
img_depthtest_device[0:H_i, :, 0] = gradient
img_depthtest_device[H_i:2*H_i, :, 1] = gradient
img_depthtest_device[2*H_i:3*H_i, :, 2] = gradient
img_depthtest_device[3*H_i:4*H_i, :, 0] = gradient
img_depthtest_device[3*H_i:4*H_i, :, 1] = gradient
img_depthtest_device[3*H_i:4*H_i, :, 2] = gradient
# 测试图片2: 由测试图片1转换为uint8_t
# 格式：Format_RGB888
img_depthtest_device_uint8 = numpy.zeros((H_i*4, W, 3), dtype=numpy.uint8)
gradient_uint8 = numpy.linspace(0, 255, W, dtype=numpy.uint8)
img_depthtest_device_uint8[0:H_i, :, 0] = gradient_uint8
img_depthtest_device_uint8[H_i:2*H_i, :, 1] = gradient_uint8
img_depthtest_device_uint8[2*H_i:3*H_i, :, 2] = gradient_uint8
img_depthtest_device_uint8[3*H_i:4*H_i, :, 0] = gradient_uint8
img_depthtest_device_uint8[3*H_i:4*H_i, :, 1] = gradient_uint8
img_depthtest_device_uint8[3*H_i:4*H_i, :, 2] = gradient_uint8

print("测试图片生成完毕。")

class WinMain(QObject):
    def __init__(self, app: QApplication, win: QMainWindow):
        super().__init__()
        self.app = app
        self.win = win
        self.initcontext()
    def initcontext(self):
        # 主wdg
        self.main_widget = QWidget(self.win)
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.win.setCentralWidget(self.main_widget)
        # 标签页
        self.tabwidget = QTabWidget(self.win)
        self.main_layout.addWidget(self.tabwidget)
        # 色深测试
        self.colordepth = self.tab_ColorDepth()
        self.tabwidget.addTab(self.colordepth, '色深测试(常规)')
        # 色深测试(OpenGL)
        self.colordepth_gl = self.tab_ColorDepth_GL()
        self.tabwidget.addTab(self.colordepth_gl, '色深测试(OpenGL)')

    class tab_ColorDepth(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.initcontext()
            self.main_layout.addStretch(1)
        def initcontext(self):
            self.main_layout = QVBoxLayout()
            self.setLayout(self.main_layout)
            self.main_layout.addWidget(QLabel('色深测试'))
            self.main_layout.addWidget(QLabel('测试屏幕色深，用于判断显示器以及PySide6支持的色深。'))
            self.main_layout.addWidget(QLabel('\n设备色阶：'))
            dptest_img = CustomUI.GenerelPicViewer(img_depthtest_device, "设备色阶", format = QImage.Format.Format_RGBX64)
            dptest_img.setFixedHeight(300)
            self.main_layout.addWidget(dptest_img)
            
            self.main_layout.addWidget(QLabel('\n参考色阶：'))
            dptest_img_uint8 = CustomUI.GenerelPicViewer(img_depthtest_device_uint8, "8bit色阶", format = QImage.Format.Format_RGB888)
            dptest_img_uint8.setFixedHeight(300)
            self.main_layout.addWidget(dptest_img_uint8)


    
    class tab_ColorDepth_GL(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.initcontext()
            self.main_layout.addStretch(1)
        def initcontext(self):
            self.main_layout = QVBoxLayout()
            self.setLayout(self.main_layout)
            self.main_layout.addWidget(QLabel('色深测试(OpenGL)'))
            self.main_layout.addWidget(QLabel('测试OpenGL支持的色深，用于判断OpenGL驱动以及PySide6支持的色深。'))

            if not support_opengl:
                self.main_layout.addWidget(QLabel('\nOpenGL库未找到，无法显示OpenGL内容。执行以下命令以安装OpenGL库：'))
                text = QLabel('pip install PyOpenGL\npip install PyOpenGL_accelerate (可选)')
                # 可复制
                text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                self.main_layout.addWidget(text)
                return
        class GLWidget(QOpenGLWidget):
            def __init__(self, parent=None):
                super().__init__(parent)
            
            def initializeGL(self):
                ...
            




if __name__ == '__main__':
    app = QApplication()
    win = QMainWindow()
    win.setWindowTitle('ColorTest')
    winmain = WinMain(app, win)
    win.show()
    sys.exit(app.exec())