from PySide6.QtWidgets import QApplication
from PySide6.QtOpenGLWidgets import QOpenGLWidget  
from PySide6.QtCore import QTimer
from PySide6.QtGui import QSurfaceFormat
import OpenGL.GL as gl
 
class OpenGLWidget(QOpenGLWidget):
    def __init__(self, start_gray=0, end_gray=1, parent=None):
        super().__init__(parent)
        self.start_gray = start_gray  # 左侧灰度值 (0.0-1.0)
        self.end_gray = end_gray      # 右侧灰度值 (0.0-1.0)
        
        # 设置OpenGL版本和配置
        format = QSurfaceFormat()
        # 设置16bit位深
        format.setRedBufferSize(16)
        format.setGreenBufferSize(16)
        format.setBlueBufferSize(16)
        format.setAlphaBufferSize(16)
        
        self.setFormat(format)

    def setGradientValues(self, start, end):
        """设置渐变灰度值"""
        self.start_gray = max(0.0, min(1.0, start))
        self.end_gray = max(0.0, min(1.0, end))
        self.update()

    def initializeGL(self):
        """初始化OpenGL"""
        # 清除颜色设为黑色
        gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        
        # 启用必要的功能
        gl.glEnable(gl.GL_DEPTH_TEST)
        
        # 启用平滑着色以实现渐变
        gl.glShadeModel(gl.GL_SMOOTH)
        
        # 启用混合（如果需要透明度）
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    def paintGL(self):
        """绘制渐变矩形"""
        # 清除缓冲区
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        
        # 设置投影矩阵（正交投影，覆盖整个窗口）
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(0.0, 1.0, 0.0, 1.0, -1.0, 1.0)
        
        # 设置模型视图矩阵
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        
        # 禁用光照，确保使用顶点颜色
        gl.glDisable(gl.GL_LIGHTING)
        
        # 绘制全屏渐变矩形
        gl.glBegin(gl.GL_QUADS)
        
        # 左下角 - 使用start灰度
        gl.glColor3f(self.start_gray, self.start_gray, self.start_gray)
        gl.glVertex2f(0.0, 0.0)
        
        # 右下角 - 使用end灰度
        gl.glColor3f(self.end_gray, self.end_gray, self.end_gray)
        gl.glVertex2f(1.0, 0.0)
        
        # 右上角 - 使用end灰度
        gl.glColor3f(self.end_gray, self.end_gray, self.end_gray)
        gl.glVertex2f(1.0, 1.0)
        
        # 左上角 - 使用start灰度
        gl.glColor3f(self.start_gray, self.start_gray, self.start_gray)
        gl.glVertex2f(0.0, 1.0)
        
        gl.glEnd()
        
        # 恢复OpenGL状态
        gl.glEnable(gl.GL_DEPTH_TEST)

    def resizeGL(self, width, height):
        """处理窗口大小变化"""
        gl.glViewport(0, 0, width, height)
 
if __name__ == "__main__":
    app = QApplication([])
    widget = OpenGLWidget()
    widget.show()
    app.exec()