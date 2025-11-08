from PySide6.QtWidgets import (QApplication, QWidget, QMainWindow, 
                               QFrame, QMenu, 
                               QHBoxLayout, QVBoxLayout,
                               QLabel, QPushButton, QCheckBox, 
                               QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
                               QMessageBox, 
                               QSizePolicy, 
)
from PySide6.QtCore import (Qt, QObject, QRectF
                            
)

from PySide6.QtGui import (QPixmap, QPainter, QImage, QColor, QBrush, 
                           QResizeEvent, QWheelEvent, QContextMenuEvent, QKeyEvent
)

import weakref

import os.path

from functools import partial

from numpy.typing import NDArray

import logging

logger = logging.getLogger(os.path.basename(__file__))

# img.shape: (h, w, c)
IMG_SHAPE_H = 0
IMG_SHAPE_W = 1
IMG_SHAPE_C = 2

class CustomUI:
    """自定义UI。不需要实例化"""
    @staticmethod
    def MsgBoxQuesion_WithCheckButton(win: QWidget, title: str, text: str, check_text: str, 
                                      icon:    QMessageBox.Icon           = QMessageBox.Icon.Question, 
                                      buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      default: QMessageBox.StandardButton = QMessageBox.StandardButton.No
                                     ) -> tuple[int, bool]:
        """消息框，但多了一个复选框，通常用于“不再提示”等功能"""
        # 创建消息框
        msg_box = QMessageBox(win)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setStandardButtons(buttons)
        msg_box.setDefaultButton(default)

        # 设置图标
        msg_box.setIcon(icon)

        # 添加不再提示复选框
        check_box = QCheckBox(check_text)
        msg_box.setCheckBox(check_box)

        # 显示消息框并获取结果
        return (msg_box.exec(), check_box.isChecked())
    @staticmethod
    def MsgBox_WithDetail(win: QWidget, title: str, text: str, inftext: str, detail: str, 
                         icon:    QMessageBox.Icon           = QMessageBox.Icon.Information, 
                         buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok
                        ) -> int:
        """消息框，但多了一个详细信息按钮"""

        msg_box = QMessageBox(win)
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setInformativeText(inftext)
        msg_box.setDetailedText(detail)
        msg_box.setStandardButtons(buttons)
        return msg_box.exec()
    @staticmethod
    class GenerelPicViewer(QWidget):
        """一个通用的图片查看器。继承于QWidget"""
        def __init__(self, img: NDArray, prefix = ""):
            super().__init__()
            self_ref = weakref.ref(self)
            self.prefix = prefix
            # self_ref = weakref.ref(self)
            # 创建布局管理器
            self.viewer_layout = QVBoxLayout()
            self.setLayout(self.viewer_layout)
            # 标题布局
            self.title_layout = QHBoxLayout()
            self.viewer_layout.addLayout(self.title_layout)
            # 100%按钮，左侧
            self.btn_100 = QPushButton("100%")
            self.title_layout.addWidget(self.btn_100)
            # 创建标题文本，居中，尽可能占满，无边距
            self.title = QLabel()
            self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            self.title_layout.addWidget(self.title)
            # 自适应按钮，右侧
            self.btn_auto = QPushButton("自适应")
            self.title_layout.addWidget(self.btn_auto)

            # 创建GraphicsView和GraphicsScene
            self.gpview = QGraphicsView()
            self.viewer_layout.addWidget(self.gpview)
            self.scene = QGraphicsScene()
            self.gpview.setScene(self.scene)
            # 创建QPixmap并添加到GraphicsScene中
            self.qpixmap_item = QGraphicsPixmapItem()
            self.scene.addItem(self.qpixmap_item)
            # 设置gpview的基本属性
            self.gpview.setFrameShape(QFrame.Shape.NoFrame) # 无边框
            self.gpview.setRenderHint(QPainter.RenderHint.Antialiasing)  # 抗锯齿
            # self.gpview.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)  # 平滑像素图变换 # 会导致棋盘格模糊
            self.gpview.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)  # 以鼠标位置为变换锚点
            self.gpview.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)          # 以鼠标位置为缩放锚点
            self.gpview.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)  # 需要时显示滚动条(水平)
            self.gpview.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded) # 需要时显示滚动条(垂直)
            # 背景棋盘格
            self.gpview.setBackgroundBrush(CustomBrush.Chessboard())
            # 自动/手动缩放回调
            self.autoscale = True
            self.gpview.resizeEvent = lambda e: (self := self_ref()) and self.__gpview_resizeEvent(e)
            self.gpview.wheelEvent = lambda e: (self := self_ref()) and self.__gpview_wheelEvent(e)
            # 使画面能拖动
            self.gpview.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.btn_100.clicked.connect(lambda: (self := self_ref()) and self.__btn_100_click())
            self.btn_auto.clicked.connect(lambda: (self := self_ref()) and self.__btn_auto_click())
            # 隐藏自适应按钮，但不移出布局
            self.btn_auto.setVisible(False)

            self.gpview.contextMenuEvent = lambda e: (self := self_ref()) and self.__gpview_contextMenuEvent(e)
            self.gpview.keyPressEvent = lambda e: (self := self_ref()) and self.__gpview_keyPressEvent(e)
            # 刷新
            self.update_arr(img)
        # 绑定100%按钮的点击事件
        def __btn_100_click(self):
            # self = self_ref()
            # if self is None: return
            # 设置自适应缩放为false
            self.autoscale = False
            self.btn_auto.setVisible(True)
            self.btn_100.setVisible(False)
            # 重置缩放
            self.gpview.resetTransform()
        # 绑定自适应按钮的点击事件
        def __btn_auto_click(self):
            # self = self_ref()
            # if self is None: return
            # 设置自适应缩放为true
            self.autoscale = True
            self.btn_auto.setVisible(False)
            # 刷新
            # self.__gpview_resizeEvent(None)
            self.gpview.resizeEvent(QResizeEvent(self.gpview.size(), self.gpview.size()))
        # 自动缩放事件（仅在autoscale为True时生效）
        def __gpview_resizeEvent(self, e: QResizeEvent):
            # self = self_ref()
            # if self is None: return
            if self.autoscale:
                # 获取rect
                vrect = self.gpview.viewport().rect()
                srect = self.scene.itemsBoundingRect()
                # 如果视图小于等于图片原始大小，则缩放
                if vrect.width() <= self.img_width or vrect.height() <= self.img_height:
                    self.gpview.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
                    self.btn_100.setVisible(True)
                # 否则，不缩放，但居中
                else:
                    self.gpview.resetTransform()
                    self.btn_100.setVisible(False)
                    off_x = (vrect.width() - srect.width()) / 2
                    off_y = (vrect.height() - srect.height()) / 2
                    self.gpview.translate(off_x, off_y)
            # 调用gpview的resizeEvent函数
            QGraphicsView.resizeEvent(self.gpview, e)
        # 手动缩放事件（生效，且会使autoscale为False）
        def __gpview_wheelEvent(self, e: QWheelEvent):
            # self = self_ref()
            # if self is None: return
            angle = e.angleDelta().y()
            scale = 1 + angle / 1200
            self.gpview.scale(scale, scale)
            # 如果当前缩放比例不等于100%，则显示100%按钮
            # print(self.gpview.transform().m11())
            self.btn_100.setVisible(abs(self.gpview.transform().m11() - 1.0) > 0.01)
            if self.autoscale:
                self.autoscale = False
                self.btn_auto.setVisible(True)
        # 给gpview添加右键菜单
        def __gpview_contextMenuEvent(self, e: QContextMenuEvent):
            # self = self_ref()
            # if self is None: return
            self_ref = weakref.ref(self)
            # 创建菜单
            menu = QMenu(self.gpview)
            # 添加菜单项
            action = menu.addAction("复制图片")
            # 绑定菜单项的点击事件
            action.triggered.connect(lambda: (self := self_ref()) and self.copy_img( ))
            # 显示菜单
            menu.exec(e.globalPos())
        # 或者gpview上Ctrl+C复制图片
        def __gpview_keyPressEvent(self, e: QKeyEvent):
            # self = self_ref()
            # if self is None: return
            if e.key() == Qt.Key.Key_C and e.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.copy_img()
        def update_arr(self, img: NDArray):
            """更换数组"""
            # self.img = img
            self.img_width = img.shape[IMG_SHAPE_W]
            self.img_height = img.shape[IMG_SHAPE_H]
            
            # 直接使用numpy数组的数据指针创建QImage，避免拷贝
            bytes_per_line = img.shape[IMG_SHAPE_C] * self.img_width  # RGBA8888格式，每像素4字节
            self.qimage = QImage(img.data, self.img_width, self.img_height, bytes_per_line, QImage.Format.Format_RGBA8888)
            
            # 创建QPixmap
            self.qpixmap = QPixmap.fromImage(self.qimage)
            self.qpixmap_item.setPixmap(self.qpixmap)

            # 更新场景矩形以确保尺寸正确
            self.scene.setSceneRect(QRectF(0, 0, self.img_width, self.img_height))

            # 更新
            self.gpview.resizeEvent(QResizeEvent(self.gpview.size(), self.gpview.size()))

            # 刷新文本
            self.title.setText(f"{self.prefix}    {self.img_width}x{self.img_height}px")
    
        def update_(self):
            """更新画面"""
            self.qpixmap.convertFromImage(self.qimage)
            self.qpixmap_item.setPixmap(self.qpixmap)

        def copy_img(self):
            """将img复制到剪贴板"""
            clipboard = QApplication.clipboard()
            clipboard.setImage(self.qimage)
        def __del__(self):
            logger.info(f"图片预览 {self.prefix} 删除")



class CustomBrush:
    """自定义画刷"""
    @staticmethod
    def Chessboard():
        """棋盘格纹理"""
        # 创建单个棋盘格单元（2x2格子）
        grid_size = 10
        tile_size = 10 * 2
        tile_pixmap = QPixmap(tile_size, tile_size)
        tile_pixmap.fill(Qt.GlobalColor.transparent)

        # 绘制棋盘格模式
        painter = QPainter(tile_pixmap)
        colors = [QColor(240, 240, 240), QColor(255, 255, 255)]

        for y in range(2):
            for x in range(2):
                color_idx = (x + y) % 2
                painter.fillRect(x * grid_size, y * grid_size, grid_size, grid_size, colors[color_idx])
        painter.end()
        # 创建棋盘格纹理
        brush = QBrush(tile_pixmap)
        return brush