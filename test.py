# Qt写一个OpenGL窗口的示例，拟合圆形
import sys
from math import cos, sin, pi
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtOpenGL import QGLWidget
from OpenGL.GL import *
from OpenGL.GLU import *


class GLWidget(QGLWidget):
    def __init__(self, parent=None):
        super(GLWidget, self).__init__(parent)

    def initializeGL(self):
        glClearColor(0, 0, 0, 1.0)  # Set background color to white
        glEnable(GL_POINT_SMOOTH)
        glPointSize(5.0)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(-1.5, 1.5, -1.5, 1.5)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()

        # Draw circle
        glColor3f(0.0, 0.0, 1.0)  # Blue color
        glBegin(GL_LINE_LOOP)
        for i in range(100):
            angle = 2 * pi * i / 100
            x = cos(angle)
            y = sin(angle)
            glVertex2f(x, y)
        glEnd()

        # Draw points on the circle
        glColor3f(1.0, 0.0, 0.0)  # Red color
        glBegin(GL_POINTS)
        for i in range(12):
            angle = 2 * pi * i / 12
            x = cos(angle)
            y = sin(angle)
            glVertex2f(x, y)
        glEnd()
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("OpenGL Circle")
        self.setGeometry(100, 100, 800, 600)

        glWidget = GLWidget(self)
        self.setCentralWidget(glWidget)
        self.show()
        # Set the central widget of the main window to be our OpenGL widget



if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
