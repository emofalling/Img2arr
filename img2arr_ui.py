# Img2arr的UI部分
# 性能和功能丰富性起见，使用PySide实现（我已经在Tk上踩过太多坑了）
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QStyleFactory, 
    QWidget, QFrame, QScrollArea,
    QLabel, QPushButton, QCheckBox, QSlider,
    QListWidget, QLineEdit, QPlainTextEdit, QTextEdit, 
    QHBoxLayout, QVBoxLayout, QGridLayout, 
    QSplitter,
    QTabWidget, QTabBar, QSizePolicy, 
    QMenu, QToolTip, QToolButton,
    QDialogButtonBox, QStyle, 
    QGraphicsView, QGraphicsScene, 
    QGraphicsPixmapItem, QGraphicsRectItem,
    QMessageBox, QFileDialog, QInputDialog
)

from PySide6.QtGui import (QCloseEvent, 
    QPixmap, QImage, QPainter, QPalette, 
    QFontDatabase, QFont, QFontMetrics, 
    QTextOption, 
    QWheelEvent, QMouseEvent, QKeyEvent, QResizeEvent, QDragEnterEvent, QDropEvent, QContextMenuEvent,
    QColor, QPen, QBrush)

from PySide6.QtCore import Qt, QTimer, QObject, QMetaObject, QGenericArgument, Signal, QUrl, QRect, QRectF, Slot

from threading import Thread, Condition

import queue

import logging
import logging.config

import sys, os
import gc
import time
import json
import weakref
import traceback

from functools import partial
from itertools import islice

from typing import (
    Callable, Optional, Sequence, Literal, 
    TypeVar,
)

import typing

from lib.CustomWidgets import (
    CustomUI, CustomBrush
)

from lib import ExtensionPyABC

from lib.datatypes import JsonDataType

import numpy
from numpy.typing import NDArray

import backend  # 后端

from lib.DebugQObjects import QDebugWidget

ENCODING = "utf-8"

def InitLogging():
    with open("logging_config.json", "r", encoding=ENCODING) as f:
        logging.config.dictConfig(json.load(f))

InitLogging()

logger = logging.getLogger(os.path.basename(__file__))

self_dir = os.path.dirname(__file__)
SETTINGFILE = os.path.join(self_dir, "setting.json")

thread: int = 0

pipe_update_mode = backend.PRE_PIPE_MODES.PIPE_MODE_DEFAULT

# 实时刷新。对于一切预览的更新，都刷新其界面。
# True表示启用实时刷新，此时无论怎么操作，界面都会实时更新。
# False表示禁用实时刷新，仅当最后一次操作完成后，界面才会更新。
# True时，存在内存指针溢出问题
view_realtime_update = False

DEVICES_DEFAULT = [0, 1, 2, 3]

defaultSetting: dict[str, JsonDataType] = {
#     "LastOpenDir": "",
#     "directlyCloseWelcome": False,
#     "Devices": [0, 1, 2, 3],
#     "Parallel.Threads": 0, # 使用逻辑核心数
}

def LoadSet():
    """加载设置。文件不存在会报错"""
    with open(SETTINGFILE, "r", encoding=ENCODING) as f:
        global defaultSetting
        defaultSetting = json.load(f)

def GetSet(key: str) -> Optional[JsonDataType]:
    """获取设置中的值。若不存在则返回None"""
    return defaultSetting.get(key, None)

def SaveSet():
    """保存设置"""
    with open(SETTINGFILE, "w", encoding=ENCODING) as f:
        json.dump(defaultSetting, f, 
                  indent=4, ensure_ascii=False)

def SetSet(key: str, value, nosync: bool = False):
    """设置设置中的值"""
    defaultSetting[key] = value
    if not nosync:
        SaveSet()
    logger.info(f"全局设置更新：{key} = {value}, 临时设置：{nosync}")

def DelSet(key: str, nosync: bool = False) -> bool:
    """删除设置中的值。若键不存在则返回False，删除成功返回True"""
    is_del = False
    if key in defaultSetting:
        del defaultSetting[key]
        is_del = True
    if not nosync:
        SaveSet()
    logger.info(f"删除全局设置项：{key}, 临时设置：{nosync}, 成功：{is_del}")
    return is_del
    
def InitSet():
    """初始化设置"""
    
    setting_file_path = os.path.join(self_dir, SETTINGFILE)
    
    if not os.path.exists(setting_file_path):
        logger.info("未找到设置文件，将创建并使用默认设置")
        SaveSet()
        return
    
    try:
        LoadSet()
        logger.info("设置文件加载成功")
    except Exception as e:
        logger.warning(f"加载设置失败，错误信息：{e}，将使用默认设置")
        SaveSet()

def AutoFmtTime(s: float):
    if s >= 1.0:
        return f"{s:.2f}s"
    elif s >= 1e-3:
        return f"{s*1e3:.2f}ms"
    elif s >= 1e-6:
        return f"{s*1e6:.2f}μs"
    else:
        return f"{s*1e9:.2f}ns"

def AutoFmtSize(s: int) -> tuple[float, str]:
    if s >= 1e9:
        return (s/1e9, "GB")
    elif s >= 1e6:
        return (s/1e6, "MB")
    elif s >= 1e3:
        return (s/1e3, "KB")
    else:
        return (s, "B")


"""
标签页对象须知：
如果传入的QWidget具有DestroyEvent方法，则：
    当标签页被关闭时，会调用该QWidget的DestroyEvent方法，返回True则将会销毁该QWidget，返回False则不会销毁该QWidget。
    否则，直接销毁该QWidget。
"""

class WinMain(QObject):
    load_signal = Signal(str)
    new_pagemain_signal = Signal(str, object)
    
    def __init__(self, app: QApplication, win: QMainWindow):
        super().__init__()
        self.app = app
        self.win = win
        self.win.closeEvent = self.closeEvent # 关闭窗口时的回调
        self.setwindow()
        self.setcontext()
        self.ext = ({}, {}, {}, {})
        # 连接加载完成信号到Main方法
        # self.load_signal = Signals.SignalNoArg()
        self.load_signal.connect(self.Main, Qt.ConnectionType.AutoConnection)
        self.new_pagemain_signal.connect(self.NewPageMain, Qt.ConnectionType.AutoConnection)

        # 打开图片的线程
        self.load_queue = queue.Queue()
        open_file_thr = Thread(target=self.thread_Open, daemon=True)
        open_file_thr.start()

        # 在窗口加载后，线程加载扩展
        QTimer.singleShot(0, lambda: Thread(target=self.Load, daemon=True).start())
    def setwindow(self):
        """设置窗体属性"""
        # 标题
        self.win.setWindowTitle("Img2arr")
        # 设置窗体大小
        geometry = GetSet("WinGeometry")
        if isinstance(geometry, list):
            # 如果是(-1, -1, -4, -5),表示最大化
            if geometry == [-1, -1, -4, -5]:
                self.win.showMaximized()
            else:
                self.win.setGeometry(QRect(*geometry))

    def setstyle(self):
        """设置统一样式"""
    status_signal = Signal(str)
    def setcontext(self):
        """设置窗体内容"""
        self_ref = weakref.ref(self)
        # 创建主Widget
        self.main_widget = QWidget(self.win)
        self.win.setCentralWidget(self.main_widget)
        # 创建主布局
        self.main_layout = QVBoxLayout(self.main_widget)
        # 设置布局边界为0
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        # 获取状态栏
        self.status_bar = self.win.statusBar()
        self.status_bar.showMessage("准备初始化")
        # 创建一个QTabWidget，并添加一个标签页
        self.tabwdg = QTabWidget(self.main_widget)
        # 添加x
        self.tabwdg.setTabsClosable(True)
        # 添加拖动
        self.tabwdg.setMovable(True)
        # 绑定关闭标签页事件
        self.tabwdg.tabCloseRequested.connect(self.closeTab)
        # 绑定按键事件
        def tabwdg_keyPressEvent(event: QKeyEvent):
            # Home:跳到第一个标签页
            if event.key() == Qt.Key.Key_Home:
                self.tabwdg.setCurrentIndex(0)
            # End:跳到最后一个标签页
            elif event.key() == Qt.Key.Key_End:
                self.tabwdg.setCurrentIndex(self.tabwdg.count() - 1)
            # Del:删除当前标签页
            elif event.key() == Qt.Key.Key_Delete:
                self.closeTab(self.tabwdg.currentIndex())
            else:
                event.ignore()
        self.tabwdg.keyPressEvent = tabwdg_keyPressEvent

        # 标签页右键菜单
        def tabwdg_contextMenuEvent(event: QContextMenuEvent):
            # 获取右键的标签页索引
            index = self.tabwdg.tabBar().tabAt(event.pos())
            # 获取当前标签页
            current_tab = self.tabwdg.widget(index) if index != -1 else None
            # 如果当前标签页存在
            if current_tab:
                # 创建菜单
                menu = QMenu(self.tabwdg)
                # 添加菜单项
                menu.addAction("重命名", lambda: self.renameTab(index))
                menu.addSeparator()
                menu.addAction("关闭", lambda: self.closeTab(index))
                menu.addAction("关闭所有", lambda: self.closeAllTabs())
                menu.addSeparator()
                menu.addAction("移出到新窗口", lambda: self.moveTabToNewWindow(index))

                # 显示菜单
                menu.exec(event.globalPos())
        self.tabwdg.contextMenuEvent = tabwdg_contextMenuEvent

        # 绑定主UI
        self.main_layout.addWidget(self.tabwdg)
        # 创建状态的Signal
        self.status_signal.connect(
            lambda text: self.setstatus(text, False) if (self := self_ref()) else logger.error("资源管理错误: self_ref() 返回 None")
        )
    def setstatus(self, text: str | None, thread: bool = False):
        """设置状态栏文本"""
        if thread:
            self.status_signal.emit(text)
            return
        if text is None or text == "":
            self.status_bar.clearMessage()
        else:
            self.status_bar.showMessage(text)
    @Slot(str)
    def Main(self, error: str):
        """当环境准备好之后，要执行的函数"""
        if error:
            QMessageBox.critical(self.win, "错误", error)
            return
        if self.ext_err_list:
            # 格式化错误主信息（简洁版）
            errinfo_short = f"共 {len(self.ext_err_list)} 个扩展导入失败，将忽略这些扩展。\n详情可复制下方详细信息。"

            # 格式化详细错误信息（可复制）
            errinfo_detailed = ""
            for path, err in self.ext_err_list:
                errinfo_detailed += f"{path}:\n    {err.__class__.__name__}: {err}\n\n"

            # 创建错误消息框
            CustomUI.MsgBox_WithDetail(self.win, "错误", "扩展导入失败", errinfo_short, errinfo_detailed, QMessageBox.Icon.Critical, QMessageBox.StandardButton.Ok)

        # 创建欢迎页
        self.welcome_page = self.WelcomePage(self)
        self.welcome()
        # 测试页
        # self.test()
    def Load(self):
        """窗体启动完成后，要初始化的函数。这部分将作为线程执行（因此需特别注意线程安全）"""
        time_start = time.perf_counter()
        error = ""
        # 加载扩展
        self.setstatus("准备导入扩展", True)
        try:
            self.LoadExts()
        except:
            logger.critical("扩展加载器出现错误:", exc_info=True)
            error = "扩展加载器出现错误，请查看日志。"
        self.setstatus("测试", True)
        if not error:
            self.setstatus(f"就绪，启动时间：{(time.perf_counter() - time_start)*1000:.2f}ms", True)
        else:
            self.setstatus(error, True)
            
        # 发送信号，通知主线程
        self.load_signal.emit(error)

    def LoadExts(self):
        self.ext_err_list: list[tuple[str, Exception]] = []
        def errf(path: str, err: Exception):
            """导入错误处理函数"""
            self.ext_err_list.append((path, err))
        def loadf(package: str):
            self.setstatus(f"加载扩展 {package}", True)
        
        devices = GetSet("Devices")
        if not isinstance(devices, list) or not all(isinstance(i, int) for i in devices):
            logging.warning("设备配置错误，将使用默认设备: [0, 1, 2, 3]")
            devices = DEVICES_DEFAULT

        self.ext = backend.load_exts(loadf, errf, reload_feautures=typing.cast(Sequence[int], devices)) # pylance ***
    
    @Slot(str, object)
    def NewPageMain(self, file: str, pipe: backend.Img2arrPIPE):
        # 通知接收函数：创建PageMain
        title = os.path.basename(file)
        tab = PageMain(self.tabwdg, self.win, title, pipe)
        id = self.tabwdg.addTab(tab, title)
        # 切换到此tab
        self.tabwdg.setCurrentIndex(id)
        
    def openfiles(self):#
        """打开文件"""
        FILTERS = [
            "All Files (*)",
            "Image Files (*.png *.jpg *.bmp)"
        ]
        last_dir = GetSet("LastOpenDir")
        if not isinstance(last_dir, str):
            last_dir = ""
        file, filter = QFileDialog.getOpenFileNames(self.win, "打开文件", last_dir, ";;".join(FILTERS), FILTERS[1])
        if file:
            SetSet("LastOpenDir", os.path.dirname(file[0]))
            # 添加到队列
            for f in file:
                self.load_queue.put(f)
    def thread_Open(self):
        while True:
            if self.load_queue.empty():
                # self.setstatus("就绪", True)
                self.setstatus(None, True)
            data = self.load_queue.get()
            if isinstance(data, str):
                # 文件路径
                self.setstatus(f"正在打开文件：{data}", True)
                file = data
                try:
                    pipe = backend.Img2arrPIPE(file, self.ext)
                except:
                    logger.error(f"{file} 打开失败。错误信息:", exc_info=True)
                    continue
                self.new_pagemain_signal.emit(file, pipe)
                del file
            else:
                pipe = None # 以后要改
            # 一定要清理资源！！！
            # 如果不del pipe，会产生两份引用
            # 一份是emit的pipe，另一份是局部变量pipe
            # 如果不删除，局部变量pipe会一直驻留在内存中，导致删不掉
            del pipe, data
    class WelcomePage(QWidget):
        def __init__(self, parent: "WinMain"):
            super().__init__()

            self.parent_ref = weakref.ref(parent)

            self.main()
        
        def main(self):
            parent = self.parent_ref()
            if parent is None:
                logger.error("WelcomePage: parent_ref is None")
                return
    
            layout = QVBoxLayout(self)
    
            in_widget = QWidget()
            in_layout = QVBoxLayout()
            in_widget.setLayout(in_layout)
    
    
            button = QPushButton("打开文件")
            button.clicked.connect(parent.openfiles)
    
            cb = QCheckBox("性能模式")
            
            def cb_change(state: int):
                global pipe_update_mode
                if state == Qt.CheckState.Checked.value:
                    pipe_update_mode = backend.PRE_PIPE_MODES.PIPE_MODE_SPEED
                    logger.debug("切换为性能模式")
                else:
                    pipe_update_mode = backend.PRE_PIPE_MODES.PIPE_MODE_DEFAULT
                    logger.debug("切换为默认模式")
            cb.stateChanged.connect(cb_change)
                
    
            # 使用addWidget的alignment参数直接实现居中
            layout.addWidget(in_widget, alignment=Qt.AlignmentFlag.AlignCenter)
            in_layout.addWidget(button)
            in_layout.addWidget(cb)
    
            # 添加一个标识，表示这是欢迎页面
            self.setObjectName("welcome")
    
            # 设置Widget可以接收文件拖进来
            self.setAcceptDrops(True)
            # 添加事件
            def dragEnterEvent(event: QDragEnterEvent):
                # 仅接受文件，不接受文件夹
                if event.mimeData().hasUrls():
                    event.acceptProposedAction()
    
            def dropEvent(event: QDropEvent):
                urls = event.mimeData().urls()
                files = []
                for url in urls:
                    file = url.toLocalFile()
                    if os.path.isfile(file):
                        files.append(file)
                if files:
                    for file in files:
                        parent.load_queue.put(file)
                
            self.dragEnterEvent = dragEnterEvent
            self.dropEvent = dropEvent
        def DestroyEvent(self) -> bool:
            # 对于欢迎页面，询问性关闭
            parent = self.parent_ref()
            if parent is None:
                logger.error("WelcomePage: parent_ref is None")
                return True
            
            # 如果没有选择不再提示，弹出消息框询问是否关闭
            if GetSet("directlyCloseWelcome"):
                return True
            else:
                # 获取自身标签页名称
                title = parent.tabwdg.tabText(parent.tabwdg.indexOf(self))
                result, check = CustomUI.MsgBoxQuesion_WithCheckButton(parent.win, "确认关闭", f"真的要关闭{title}页吗？", "不再提示（可从设置恢复）")
                if result == QMessageBox.StandardButton.Yes and check:
                    SetSet("directlyCloseWelcome", True)
                return result == QMessageBox.StandardButton.Yes
    def welcome(self):
        """欢迎"""
        self.tabwdg.addTab(self.welcome_page, "欢迎")
    
    def renameTab(self, index: int):
        cur_text = self.tabwdg.tabText(index)
        # 输入对话框
        while True:
            text, ok = QInputDialog.getText(self.win, "重命名", "请输入新的标签名：", text=cur_text)
            if not ok: return
            pass_empty = GetSet("directlyRenameTabToEmpty")
            if text == "" and not pass_empty:
                sel, check = CustomUI.MsgBoxQuesion_WithCheckButton(
                    self.win,
                    "重命名",
                    "真的要将标签名改为空吗？",
                    "不再提示（可从设置恢复）",
                )
                if sel == QMessageBox.StandardButton.Yes:
                    if check: SetSet("directlyRenameTabToEmpty", True)
                    break
            else:
                break
        self.tabwdg.setTabText(index, text)
    
    def RemoveTab(self, index: int):
        # 获取index所对widget
        tab_widget = self.tabwdg.widget(index)
        # 删除tab
        self.tabwdg.removeTab(index)
        # 删除widget
        # tab_widget.setParent(None)
        tab_widget.deleteLater()
        gc.collect()

    def closeTab(self, index: int):
        # 判断是否为欢迎页面
        qw = self.tabwdg.widget(index)
        # 如果有自定义方法DestroyEvent，则调用以判断是否关闭
        destroy_method = getattr(qw, "DestroyEvent", None)
        if destroy_method is not None:
            close = destroy_method()
            if not close: 
                return
        self.RemoveTab(index)
    def closeAllTabs(self):
        while self.tabwdg.count() > 1:
            self.closeTab(1)
        # 输出自身ObjectTree
        self.main_widget.dumpObjectTree()
    def moveTabToNewWindow(self, index: int):
        # 获取index所对widget
        tab_widget = self.tabwdg.widget(index)
        # gc.collect()
        # 创建新窗口
        title = f"img2arr - {self.tabwdg.tabText(index)}"
        win = TabNewWindow(self.win, title, tab_widget)
        win_gemetry = self.win.geometry()
        win.setGeometry(
            win_gemetry.x() + 100, 
            win_gemetry.y() + 100, 
            win_gemetry.width(), 
            win_gemetry.height()
        )
        win.show()
        # 删除tab
        # self.tabwdg.removeTab(index)


    def closeEvent(self, event: QCloseEvent):
        # 创建线程，但不daemon
        self.close_thread = Thread(target=self.Close, args=(event,))
        self.close_thread.start()
        QMainWindow.closeEvent(self.win, event)
    def Close(self, event: QCloseEvent):
        """当窗口关闭时，要执行的函数。在别的线程中执行"""
        # 保存当前窗口的位置
        geometry = self.win.geometry()
        if self.win.isMaximized():
            # 最大化，保存(-1, -1, -4, -5)
            SetSet("WinGeometry", [-1, -1, -4, -5])
        else: #保存位置和大小
            SetSet("WinGeometry", [geometry.x(), geometry.y(), geometry.width(), geometry.height()])

        # 关闭Backend
        backend.Close()
        pass

class TabNewWindow(QMainWindow):
    def __init__(self, parent_win: Optional[QWidget], title: str, widget_in: QWidget):
        super().__init__(parent_win)
        self.setWindowTitle(title)
        self.main_wdg = QWidget(self)
        self.setCentralWidget(self.main_wdg)
        self.main_layout = QVBoxLayout(self.main_wdg)
        self.main_wdg.setLayout(self.main_layout)
        self.main_layout.addWidget(widget_in)

class PageMain(QDebugWidget):
    PreOutViewUpdateSignal = Signal(tuple)
    CodeViewerOutViewUpdateSignal = Signal(tuple)
    def __init__(self, parent: Optional[QWidget], win: QMainWindow, title: str, pipe: backend.Img2arrPIPE):
        super().__init__(parent)
        self.setObjectName(f"PageMain: {title}")
        self_ref = weakref.ref(self)
        # self.app = app
        self.win = win
        # self.pipe = backend.Img2arrPIPE(file, ext)
        self.pipe = pipe
        # 预处理项列表
        self.pre_list: list[PreProcessor] = []
        # 预处理刷新条件变量
        self.pre_update_notify: Optional[Condition] = Condition()
        self.pre_update_index: int | None = None # 线程更新时的索引。None表示更新完毕。
        # 预处理输出预览更新信号
        self.PreOutViewUpdateSignal.connect(lambda args: self.PreUpdateOutViewer(*args) if (self := self_ref()) else logger.error("资源管理错误: self_ref() 返回 None"))
        # 供给转码器的self.pipe.pre的副本。避免潜在的内存泄漏.
        self.pre_copy: NDArray | None = None
        
        # 编码器名称。空字符串表示未选择编码器
        self.code_name = ""
        # 编码器py部分。当有新的编码器被选择时，会覆盖为新的编码器py部分或None。
        self.code_py: ExtensionPyABC.abcExt.UI | None = None
        # 编码器刷新条件变量
        self.code_update_notify: Optional[Condition] = Condition()
        self.code_is_need_update = False # 编码器是否需要更新。将在唤醒前同时将其赋值为True以表示需要更新
        # 编码预览输出预览更新信号（不是编码输出
        self.CodeViewerOutViewUpdateSignal.connect(lambda args: self.CodeUpdateOutViewer(*args) if (self := self_ref()) else logger.error("资源管理错误: self_ref() 返回 None"))

        # 输出器名称。空字符串表示未选择输出器
        self.out_name = ""
        # 输出器py部分。当有新的输出器被选择时，会覆盖为新的输出器py部分或None。
        self.out_py: ExtensionPyABC.abcExt.UI | None = None


        # 预处理器线程
        self.pre_args_thread = Thread(target=self.PreUpdateThread, daemon=True)
        self.pre_args_thread_state: Literal["run", "idle"] = "idle"
        self.pre_args_thread.start()
        # 编码器线程
        self.code_args_thread = Thread(target=self.CodeUpdateThread, daemon=True)
        self.code_args_thread_state: Literal["run", "idle"] = "idle"
        self.code_args_thread.start()

        self.main()
    def main(self):
        self_ref = weakref.ref(self)
        # 创建布局管理器
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        # 6个QWidget
        self.base_out = QDebugWidget()
        self.base_out.setObjectName(f"{self.objectName()}:base_out")
        self.pre_out = QDebugWidget()
        self.pre_out.setObjectName(f"{self.objectName()}:pre_out")
        self.pre_args = QDebugWidget()
        self.pre_args.setObjectName(f"{self.objectName()}:pre_args")
        self.code_args = QDebugWidget()
        self.code_args.setObjectName(f"{self.objectName()}:code_args")
        self.code_out = QDebugWidget()
        self.code_out.setObjectName(f"{self.objectName()}:code_out")
        self.out_args = QDebugWidget()
        self.out_args.setObjectName(f"{self.objectName()}:out_args")
        self.frames = [self.base_out, self.pre_args, self.pre_out, self.code_args, self.code_out, self.out_args]
        # 设置属性
        for f in self.frames:
            f.setMinimumSize(10, 10)  # 设置最小尺寸防止自动收缩
            f.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            f.setContentsMargins(0, 0, 0, 0)

        # 初始化
        self.init_base_out()
        self.init_pre_args()
        self.init_pre_out()
        self.init_code_args()
        self.init_code_out()
        self.init_out_args()

        # 竖分割线
        self.splitter_major = QSplitter(Qt.Orientation.Horizontal)
        # 3个子横分割线
        self.splitter_minor1 = QSplitter(Qt.Orientation.Vertical)
        self.splitter_minor2 = QSplitter(Qt.Orientation.Vertical)
        self.splitter_minor3 = QSplitter(Qt.Orientation.Vertical)
        # 将子分割线添加到主分割线中
        self.splitter_major.addWidget(self.splitter_minor1)
        self.splitter_major.addWidget(self.splitter_minor2)
        self.splitter_major.addWidget(self.splitter_minor3)
        # 依次添加到子分割线中
        self.splitter_minor1.addWidget(self.base_out)
        self.splitter_minor1.addWidget(self.pre_args)
        self.splitter_minor2.addWidget(self.pre_out)
        self.splitter_minor2.addWidget(self.code_args)
        self.splitter_minor3.addWidget(self.code_out)
        self.splitter_minor3.addWidget(self.out_args)
        # 将主分割线添加到布局管理器中
        self.main_layout.addWidget(self.splitter_major)
        # 设置主子分割线的分配比相同
        self.splitter_major.setSizes([1, 1, 1])
        self.splitter_minor1.setSizes([1, 1])
        self.splitter_minor2.setSizes([1, 1])
        self.splitter_minor3.setSizes([1, 1])

    def init_base_out(self):
        self.base_out_viewer = CustomUI.GenerelPicViewer(self.pipe.img, "原图")
        self.base_out_layout = QVBoxLayout()
        self.base_out_layout.setContentsMargins(0, 0, 0, 0)
        self.base_out.setLayout(self.base_out_layout)
        self.base_out_layout.addWidget(self.base_out_viewer)

    def init_pre_args(self):
        self_ref = weakref.ref(self)
        # 创建布局
        self.pre_top_widget = QWidget()
        # self.pre_top_widget.setContentsMargins(0, 0, 0, 0)
        
        self.pre_args_layout = QVBoxLayout()
        self.pre_args.setLayout(self.pre_args_layout)

        self.pre_args_layout.addWidget(self.pre_top_widget)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        self.pre_top_widget.setLayout(top_layout)
        # 提示文本
        title = QLabel("预处理")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        top_layout.addWidget(title)
        # 计算时间文本
        self.pre_calc_time = QLabel("-- ")
        self.pre_calc_time.setAlignment(Qt.AlignmentFlag.AlignRight)
        top_layout.addWidget(self.pre_calc_time)
        # 底部scrollarea
        self.pre_args_scrollarea = QScrollArea()
        self.pre_args_layout.addWidget(self.pre_args_scrollarea)
        # 设置基本属性
        self.pre_args_scrollarea.setWidgetResizable(True)
        # 有垂直滚动条没有水平滚动条
        self.pre_args_scrollarea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.pre_args_scrollarea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # 背景为透明，边距为0
        # self.pre_args_scrollarea.setFrameShape(QFrame.Shape.NoFrame) # 无边框
        self.pre_args_scrollarea.setContentsMargins(0, 0, 0, 0)
        self.pre_args_scrollarea.setBackgroundRole(QPalette.ColorRole.Base)
        # 确保背景色生效
        self.pre_args_scrollarea.setAutoFillBackground(True)
        # 创建容器Widget，边距为0，向下无限扩展
        self.pre_args_main = QDebugWidget()
        self.pre_args_main.setObjectName(f"{self.objectName()}:pre_args_main")
        self.pre_args_main.setContentsMargins(0, 0, 0, 0)
        self.pre_args_main.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        # 给pre_args_scrollarea
        self.pre_args_scrollarea.setWidget(self.pre_args_main)
        # 创建布局管理器
        self.pre_args_main_layout = QVBoxLayout()
        self.pre_args_main.setLayout(self.pre_args_main_layout)
        self.pre_args_main.setContentsMargins(0, 0, 0, 0)
        # QVBoxLayout: 预处理器列表
        self.pre_args_list = QVBoxLayout()
        self.pre_args_main_layout.addLayout(self.pre_args_list)

        # 底部按钮：添加预处理器，占满宽度
        self.pre_args_add = QPushButton("添加预处理器")
        self.pre_args_main_layout.addWidget(self.pre_args_add)
        # self.pre_args_layout.addWidget(self.pre_args_add)
        # 选择预处理器
        def addPreProcessor():
            self = self_ref()
            if self is None: return
            name = self.ui_select_Processor(backend.EXT_TYPE_PREP, "img")
            if name is not None:
                self.AddPreProcessor(name)
        self.pre_args_add.clicked.connect(addPreProcessor)
        # 底部弹簧
        self.pre_args_main_layout.addStretch(1)

        # 设置self.pre_top_widget右键菜单
        def top_contextMenuEvent(event: QContextMenuEvent):
            self = self_ref()
            if self is None: return
            menu = QMenu(self.pre_top_widget)
            # 创建菜单项
            action1 = menu.addAction("重置预处理管线")
            action1.triggered.connect(lambda: self.Pre_Reset(True) if (self := self_ref()) else logger.error("资源管理错误: self_ref() 返回 None"))
            # 显示菜单
            menu.exec(event.globalPos())
        self.pre_top_widget.contextMenuEvent = top_contextMenuEvent

        # 刷新预处理。当前是为了刷新pre_copy，未来可以用于预设加载
        self.Pre_Update()


    def init_pre_out(self):
        self.pre_out_viewer = CustomUI.GenerelPicViewer(self.pipe.pre, "预处理")
        self.pre_out_layout = QVBoxLayout()
        self.pre_out_layout.setContentsMargins(0, 0, 0, 0)
        self.pre_out.setLayout(self.pre_out_layout)
        self.pre_out_layout.addWidget(self.pre_out_viewer)
    
    def init_code_args(self):
        self_ref = weakref.ref(self)

        self.code_args_layout = QVBoxLayout()
        self.code_args.setLayout(self.code_args_layout)
        # 顶部wdg
        self.code_top_widget = QWidget()
        self.code_top_widget.setContentsMargins(0, 0, 0, 0)
        self.code_args_layout.addWidget(self.code_top_widget)
        # 顶部布局
        self.code_top_layout = QHBoxLayout()
        self.code_top_layout.setContentsMargins(0, 0, 0, 0)
        self.code_top_widget.setLayout(self.code_top_layout)
        # 提示文本
        self.code_top_layout.addWidget(QLabel("编码："), alignment=Qt.AlignmentFlag.AlignLeft)
        self.code_main_text = QLabel("--")
        self.code_top_layout.addWidget(self.code_main_text, alignment=Qt.AlignmentFlag.AlignLeft)
        self.code_select_button = QPushButton("选择")
        # 设置宽度为文字宽度，高度为文字高度
        rect = self.code_select_button.fontMetrics().boundingRect("选择")
        self.code_select_button.setFixedWidth(rect.width() + 10)
        # self.code_select_button.setFixedHeight(rect.height())
        self.code_top_layout.addWidget(self.code_select_button, alignment=Qt.AlignmentFlag.AlignLeft)
        # 此处添加弹簧
        self.code_top_layout.addStretch(1)
        # 计算时间
        self.code_calc_time = QLabel("-- ")
        self.code_top_layout.addWidget(self.code_calc_time, alignment=Qt.AlignmentFlag.AlignRight)

        # 选择编码器
        def selectCode():
            self = self_ref()
            if self is None: return
            name = self.ui_select_Processor(backend.EXT_TYPE_CODE, "img")
            if name is not None:
                self.SelectCode(name)
        self.code_select_button.clicked.connect(selectCode)


        # 主要布局，将通过更换QWidget的方式来实现控制台更换显示
        self.code_args_scrollarea = QScrollArea()
        # 设置基本属性
        self.code_args_scrollarea.setWidgetResizable(True)
        # self.code_args_scrollarea.setFrameShape(QFrame.Shape.NoFrame) # 无边框
        self.code_args_scrollarea.setContentsMargins(0, 0, 0, 0)
        self.code_args_scrollarea.setBackgroundRole(QPalette.ColorRole.Base)
        # 确保背景色生效
        self.code_args_scrollarea.setAutoFillBackground(True)
        # 有垂直滚动条和水平滚动条
        self.code_args_scrollarea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.code_args_scrollarea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.code_args_scrollarea.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.code_args_layout.addWidget(self.code_args_scrollarea)
        # 内部默认Widget（显示文本）
        self.code_args_default = QWidget()
        self.code_args_default.setContentsMargins(0, 0, 0, 0)
        self.code_args_default.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.code_args_scrollarea.setWidget(self.code_args_default)
        self.code_args_default_layout = QVBoxLayout()
        self.code_args_default_layout.setContentsMargins(0, 0, 0, 0)
        # 灰色文本
        self.code_args_default_text = QLabel("请选择一个编码器以显示控制台")
        self.code_args_default_text.setStyleSheet("color: gray;")
        # 上层空余空间 20%, 下层空余空间 80%
        self.code_args_default_layout.addStretch(2)
        self.code_args_default_layout.addWidget(self.code_args_default_text, alignment=Qt.AlignmentFlag.AlignCenter)
        self.code_args_default_layout.addStretch(8)
        # 默认文本
        self.code_args_default.setLayout(self.code_args_default_layout)
    
    def init_code_out(self):
        self.code_out_viewer = CustomUI.GenerelPicViewer(self.pipe.code_view, "编码")
        self.code_out_layout = QVBoxLayout()
        self.code_out_layout.setContentsMargins(0, 0, 0, 0)
        self.code_out.setLayout(self.code_out_layout)
        self.code_out_layout.addWidget(self.code_out_viewer)
    
    class OutPreviewTextEdit(ExtensionPyABC.OutPreviewTextEdit):
        """Out部分的预览TextEdit
        resize_function: 当窗口大小改变时调用的函数
        """
        resize_function: Optional[Callable[[], None]] = None
        def __init__(self, parent=None):
            super().__init__(parent)
        def resizeEvent(self, event):
            if self.resize_function is not None:
                self.resize_function()
            super().resizeEvent(event)
        def getEquivalentWidth(self) -> int:
            """获取等效单行显示宽度"""
            # 计算可用宽度
            horizontal_margin = (self.frameWidth() + self.document().documentMargin()) * 2
            usable_width = self.viewport().width() - horizontal_margin

            # 计算可用高度和行数
            line_height = self.fontMetrics().height()
            vertical_margin = (self.frameWidth() + self.document().documentMargin()) * 2
            usable_height = self.viewport().height() - vertical_margin
            max_rows = max(1, int(usable_height // line_height))

            return int(usable_width * max_rows)
    
    def init_out_args(self):
        self_ref = weakref.ref(self)

        self.out_args_layout = QVBoxLayout()
        self.out_args.setLayout(self.out_args_layout)
        # 顶部wdg
        self.out_top_widget = QWidget()
        # self.out_top_widget.setContentsMargins(0, 0, 0, 0)
        self.out_args_layout.addWidget(self.out_top_widget)
        # 顶部布局
        self.out_top_layout = QHBoxLayout()
        self.out_top_layout.setContentsMargins(0, 0, 0, 0)
        self.out_top_widget.setLayout(self.out_top_layout)
        # 提示文本
        self.out_top_layout.addWidget(QLabel("输出："), alignment=Qt.AlignmentFlag.AlignLeft)
        self.out_main_text = QLabel("--")
        self.out_top_layout.addWidget(self.out_main_text, alignment=Qt.AlignmentFlag.AlignLeft)
        self.out_select_button = QPushButton("选择")
        # 设置宽度为文字宽度，高度为文字高度
        rect = self.out_select_button.fontMetrics().boundingRect("选择")
        self.out_select_button.setFixedWidth(rect.width() + 10)
        # self.out_select_button.setFixedHeight(rect.height())
        self.out_top_layout.addWidget(self.out_select_button, alignment=Qt.AlignmentFlag.AlignLeft)
        # 此处添加弹簧
        self.out_top_layout.addStretch(1)
        # 计算时间
        self.out_calc_time = QLabel("-- ")
        self.out_top_layout.addWidget(self.out_calc_time, alignment=Qt.AlignmentFlag.AlignRight)
        # 选择编码器
        def selectOut():
            self = self_ref()
            if self is None: return
            name = self.ui_select_Processor(backend.EXT_TYPE_OUT, "img")
            if name is not None:
                self.SelectOut(name)
        self.out_select_button.clicked.connect(selectOut)


        # 分隔栏
        self.out_splitter = QSplitter(Qt.Orientation.Vertical)
        self.out_splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.out_args_layout.addWidget(self.out_splitter)
        # 第一层：主布局
        self.out_args_scrollarea = QScrollArea()
        self.out_splitter.addWidget(self.out_args_scrollarea)
        # 设置基本属性
        self.out_args_scrollarea.setWidgetResizable(True)
        # self.out_args_scrollarea.setFrameShape(QFrame.Shape.NoFrame) # 无边框
        self.out_args_scrollarea.setContentsMargins(0, 0, 0, 0)
        self.out_args_scrollarea.setBackgroundRole(QPalette.ColorRole.Base)
        # 确保背景色生效
        self.out_args_scrollarea.setAutoFillBackground(True)
        # 有垂直滚动条和水平滚动条
        self.out_args_scrollarea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.out_args_scrollarea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.out_args_scrollarea.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # 内部默认Widget（显示文本）
        self.out_args_default = QWidget()
        self.out_args_default.setContentsMargins(0, 0, 0, 0)
        self.out_args_default.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.out_args_scrollarea.setWidget(self.out_args_default)
        self.out_args_default_layout = QVBoxLayout()
        self.out_args_default_layout.setContentsMargins(0, 0, 0, 0)
        # 灰色文本
        self.out_args_default_text = QLabel("请选择一个编码器以显示控制台")
        self.out_args_default_text.setStyleSheet("color: gray;")
        # 上层空余空间 20%, 下层空余空间 80%
        self.out_args_default_layout.addStretch(2)
        self.out_args_default_layout.addWidget(self.out_args_default_text, alignment=Qt.AlignmentFlag.AlignCenter)
        self.out_args_default_layout.addStretch(8)
        # 默认文本
        self.out_args_default.setLayout(self.out_args_default_layout)
        # 第二层：预览
        self.out_preview_widget = QWidget()
        # self.out_preview_widget.setContentsMargins(0, 0, 0, 0)
        self.out_preview_layout = QVBoxLayout()
        self.out_preview_layout.setContentsMargins(0, 0, 0, 0)
        self.out_preview_widget.setLayout(self.out_preview_layout)
        self.out_splitter.addWidget(self.out_preview_widget)
        # 文本
        self.out_preview_layout.addWidget(QLabel("预览"), alignment=Qt.AlignmentFlag.AlignLeft)
        # 预览的QTextEdit
        self.out_preview = self.OutPreviewTextEdit()
        self.out_preview.setReadOnly(True)
        self.out_preview.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.out_preview.setWordWrapMode(QTextOption.WrapMode.WrapAnywhere)
        self.out_preview_layout.addWidget(self.out_preview)
        # 选择字体
        if "Consolas" in QFontDatabase.families():
            self.out_preview.setFont(QFont("Consolas"))
        elif "Courier" in QFontDatabase.families():
            self.out_preview.setFont(QFont("Courier"))
        elif "Monospace" in QFontDatabase.families():
            self.out_preview.setFont(QFont("Monospace"))

        # 默认隐藏
        self.out_preview_widget.setVisible(False)
        # 隐藏垂直滑动条
        self.out_preview.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # 绑定resize函数
        self.out_preview.resize_function = lambda: self.OutPreUpdate() if (self := self_ref()) else logger.error("资源管理错误: self_ref() 返回 None")

        # 第三层：保存。其QWidget为Flxed.
        self.out_save_widget = QWidget()
        # self.out_save_widget.setContentsMargins(0, 0, 0, 0)
        self.out_save_layout = QVBoxLayout()
        self.out_save_layout.setContentsMargins(0, 0, 0, 0)
        self.out_save_widget.setLayout(self.out_save_layout)
        self.out_splitter.addWidget(self.out_save_widget)
        # 保存按钮
        self.out_save_path_layout = QHBoxLayout()
        self.out_save_layout.addLayout(self.out_save_path_layout)
        self.out_save_path_layout.addWidget(QLabel("保存路径："))
        self.out_save_path = QLineEdit()
        self.out_save_path.setPlaceholderText("请输入保存路径")
        self.out_save_path_layout.addWidget(self.out_save_path)
        self.out_save_path_button = QPushButton("浏览...")
        self.out_save_path_button.setFixedWidth(self.out_save_path_button.fontMetrics().boundingRect(self.out_save_path_button.text()).width() + 10)
        # margin = self.out_save_path_button.contentsMargins()
        # text_width = self.out_save_path_button.fontMetrics().boundingRect(self.out_save_path_button.text()).width()
        # total_width = text_width + margin.left() + margin.right()#  + 8  # 8像素缓冲
        # self.out_save_path_button.setFixedWidth(total_width)
        self.out_save_path_layout.addWidget(self.out_save_path_button)
        # 浏览按钮点击事件
        def out_save_path_button_clicked():
            self = self_ref()
            if self is None: return
            # 获取之前的保存路径
            path = self.out_save_path.text()
            FILTERS = [
                "All Files (*)",
                "Text Files (*.txt)"
            ]
            path, _ = QFileDialog.getSaveFileName(self.win, "选择保存路径", os.path.dirname(path), ";;".join(FILTERS), FILTERS[1])
            if path:
                self.out_save_path.setText(path)
        self.out_save_path_button.clicked.connect(out_save_path_button_clicked)
        # 保存按钮
        self.out_save_button = QPushButton("保存")
        self.out_save_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.out_save_layout.addWidget(self.out_save_button)
        self.out_save_widget.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        # 保存按钮绑定函数
        def out_save_button_clicked():
            self = self_ref()
            if self is None: return
            path = self.out_save_path.text()
            if path == "":
                QMessageBox.critical(self.win, "错误", "未选择保存路径！")
                return
            if not self.out_name:
                QMessageBox.critical(self.win, "错误", "没有选择输出！")
                return
            try:
                self.test_OutSave(path)
            except Exception as e:
                logger.error(f"保存失败：", exc_info=True)
                QMessageBox.critical(self.win, "错误", f"保存失败：{e}")
                return
            QMessageBox.information(self.win, "提示", "保存成功")
        self.out_save_button.clicked.connect(out_save_button_clicked)
        # 如果OutSavePath有值，则设置到输入框
        OutSavePath = GetSet("OutSavePath")
        if isinstance(OutSavePath, str) and OutSavePath != "":
            self.out_save_path.setText(OutSavePath)
        # 保存输入框绑定函数
        def out_save_path_textChanged():
            self = self_ref()
            if self is None: return
            path = self.out_save_path.text()
            # 保存到setting
            SetSet("OutSavePath", path)
        self.out_save_path.textChanged.connect(out_save_path_textChanged)



    def ui_select_Processor(self, stage: int, type: str) -> str | None:
        """选择某个阶段的处理器，返回str或None."""
        # 创建顶层窗口
        dialog = QDialog(self.win)
        dialog.setWindowTitle("选择处理器")
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        # 创建布局
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        # 提示文本
        layout.addWidget(QLabel("请选择目标处理器："))
        # 子布局
        layout_sub = QHBoxLayout()
        layout.addLayout(layout_sub)
        # 左半部分：预处理器列表
        pre_args_list = QListWidget()
        layout_sub.addWidget(pre_args_list)
        # 右半部分：布局
        layout_sub_right = QVBoxLayout()
        layout_sub.addLayout(layout_sub_right)
        # 说明
        pre_args_desc = QPlainTextEdit()
        pre_args_desc.setReadOnly(True)
        pre_args_desc.setPlaceholderText("选择一个处理器以查看说明")
        layout_sub_right.addWidget(pre_args_desc)
        # 确认和取消按钮
        dialogbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        # 点击后退出
        dialogbox.rejected.connect(dialog.reject)
        dialogbox.accepted.connect(dialog.accept)
        layout.addWidget(dialogbox)
        # 初始化列表
        pre_list: list[str] = []
        pre_names: list[str] = []
        # 按照索引顺序存储说明。None表示没有说明
        pre_description: list[str | None] = []
        # 按照索引顺序存储作者。None表示没有作者
        pre_author: list[str | None] = []
        # 按照索引顺序存储版本。None表示没有版本
        pre_version: list[str | None] = []
        for k, v in self.pipe.extdc[stage][type].items():
            pre_names.append(k)
            info = v[backend.EXT_OP_INFO]
            pre_list.append(info["name"])
            pre_description.append(info.get("description", None))
            pre_author.append(info.get("author", None))
            pre_version.append(info.get("version", None))
        pre_args_list.addItems(pre_list)
        # 列表项点击事件
        def pre_args_list_itemClicked(item):
            # 获取选择的索引
            index = pre_args_list.currentRow()
            # 字符串
            text = ""
            text += "说明：\n    "
            # 获取说明
            desc = pre_description[index]
            if desc:
                text += desc.replace("\n", "\n    ")
            else:
                text += "无"
            author = pre_author[index]
            if author:
                text += "\n作者：\n    "
                text += author.replace("\n", "\n    ")
            version = pre_version[index]
            if version:
                text += "\n版本：\n    "
                text += version.replace("\n", "\n    ")
            # 选中
            pre_args_desc.setPlainText(text)
            # 设置dialogbox增加Ok
            dialogbox.setStandardButtons(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            # 设置Ok为默认按钮
            dialogbox.button(QDialogButtonBox.StandardButton.Ok).setDefault(True)
        # 列表项双击事件
        def pre_args_list_itemDoubleClicked(item):
            # accept关闭
            dialog.accept()
        pre_args_list.itemClicked.connect(pre_args_list_itemClicked)
        pre_args_list.itemDoubleClicked.connect(pre_args_list_itemDoubleClicked)

        # 显示并获取结果
        eo = dialog.exec()
        if eo != QDialog.DialogCode.Accepted:
            return None
        # 获取选择的索引
        index = pre_args_list.currentRow()
        # 获取扩展文件夹名
        name = pre_names[index]
        return name

    def AddPreProcessor(self, name: str):
        """添加预处理器"""

        self_ref = weakref.ref(self)

        
        # 获取name对应的列表
        ext = self.pipe.extdc[backend.EXT_TYPE_PREP]["img"][name]
        # 获取name
        main_name = ext[backend.EXT_OP_INFO]["name"]

        # 获取Python部分
        py_base: ExtensionPyABC.abcExt | None = ext[backend.EXT_OP_EXT]
        if py_base is not None and hasattr(py_base, "UI"):
            py = py_base.UI()
        else:
            py = None
        
        # 创建UI
        prep = PreProcessor(self_ref, name, main_name, 
                            py)
        ui = prep.ui
        ui_in = prep.ui_in
        # 添加到列表，并显示在界面上
        self.pre_args_list.addWidget(ui)
        self.pre_list.append(prep)
        

        err_cause = ""
        
        if py is not None and hasattr(py, "ui_init"):
            # 调用ui_init。若没有此函数则认为没有UI
            try:
                py.ui_init(ui_in, ext[backend.EXT_OP_CDLL], None)
            except:
                logger.error(f"控制台 {name} 加载失败:", exc_info=True)
                CustomUI.MsgBox_WithDetail(self.win, "错误", "预处理器加载失败", f"预处理器初始化失败，错误信息请展开", traceback.format_exc(), QMessageBox.Icon.Critical, QMessageBox.StandardButton.Ok)
                err_cause = "控制台加载失败"
        else:
            err_cause = "没有控制台"
        # 错误，则处理
        if err_cause:
                
            # 添加错误label及其布局
            ui_in_layout = QHBoxLayout()
            ui_in_layout.setContentsMargins(10, 10, 10, 10)  # 确保布局边距为0
            # ui_in_layout.setSpacing(0)  # 确保布局内部件间距为0
            # ui_in_layout.setStretchFactor(ui_in, 0)  # 设置不拉伸
            ui_in.setLayout(ui_in_layout)
            text = QLabel(err_cause)
            text.setMinimumSize(0, 0)
            
            # 关键修改：垂直策略使用 Minimum 而非 Ignored
            # text.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            
            text.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
            text.setForegroundRole(QPalette.ColorRole.Dark)
            ui_in_layout.addWidget(text)
            
            # 可选：确保QLabel不会在垂直方向扩展
            # text.setFixedHeight(text.sizeHint().height())
            
            # 调试：背景为红色
            # text.setStyleSheet("background-color: red;")
        # 更新
        self.Pre_Update(max(len(self.pre_list) - 2, 0))
 
    def Pre_FindIndex(self, pre: "PreProcessor"):
        """获取预处理项的索引。失败返回-1"""
        # return self.pre_list.index(pre) # 不可以！！！
        pre_id = id(pre)
        for i, obj in enumerate(self.pre_list):
            if id(obj) == pre_id:
                return i
        return -1
    def Pre_Move(self, index: int, direction: int):
        """将一个预处理项进行移动。   
        index: 需要移动的预处理项的索引
        direction: 移动的方向。-1为上移一格，1为下移一格
        """
        target = index + direction
        assert index >= 0 , "源位置不能小于0"
        assert index < len(self.pre_list), "源位置不能大于预处理项的数量"
        assert target >= 0 , "目标未知不能小于0"
        assert target < len(self.pre_list), "目标未知不能大于预处理项的数量"
        # 获取index和target对应的预处理ui
        index_ui = self.pre_list[index].ui
        # target_ui = self.pre_list[target].ui
        # 交换位置
        self.pre_list[index], self.pre_list[target] = self.pre_list[target], self.pre_list[index]
        # 交换界面位置
        self.pre_args_list.removeWidget(index_ui)
        self.pre_args_list.insertWidget(target, index_ui)
        # 更新
        self.Pre_Update(min(index, target))

    def Pre_Reset(self, no_update: bool = False):
        """重置预处理管线缓存"""
        # 重置链
        self.pipe.resetPrePIPE()
        # 从头更新一次
        if not no_update: self.Pre_Update(0)
    
    # 更新预处理管线的线程
    def PreUpdateThread(self):
        """更新预处理管线的线程"""
        while True:
            # 更新状态
            self.pre_args_thread_state = 'idle'
            if self.pre_update_notify is None:
                break
            with self.pre_update_notify:
                self.pre_update_notify.wait()
            if self.pre_update_notify is None: # 结束
                break
            # 更新状态
            self.pre_args_thread_state = 'run'
            resized = False # 是否需要更新输出尺寸
            self.PreOutViewUpdateSignal.emit((False, -1, None))
            time_calc_start, time_calc_end = 0, 0 # 预先初始化，避免Unbound
            while self.pre_update_index is not None:
                # 如果更新之后没有再需要更新的，此时self.pre_update_index显然为None，自然结束
                # 如果计算过程中拖动了，则self.pre_update_index会再次被赋值为需要更新的index，自然触发下一次更新
                index = self.pre_update_index
                self.pre_update_index = None
                if index is None: # 以防万一
                    continue
                time_calc_start = time.perf_counter()
                time_calc_end = time_calc_start  # 预先初始化为相同值
                try:
                    resized = self._Pre_Update(index) or resized # 任意一次需要更新尺寸，则最终需要更新
                except:
                    logger.error(f"预处理 {self.pre_list[index].name} 处理失败:", exc_info=True)
                    break
                time_calc_end = time.perf_counter()
                if view_realtime_update:
                    # 为了确保下一次更新时不会因上一次的内存范围缩小而导致段错误，所以刷新界面显示务必先复制一层内存
                    if self.pre_copy is None or resized:
                        self.pre_copy = self.pipe.pre.copy()
                    else:
                        numpy.copyto(self.pre_copy, self.pipe.pre, 'no')
                    self.PreOutViewUpdateSignal.emit((True, time_calc_end - time_calc_start, resized))
                    resized = False # 重置，防止多次更新
                    # 刷新编码
                    self.code_is_need_update = True
                    if self.code_update_notify:
                        with self.code_update_notify:
                            self.code_update_notify.notify_all()
            else:
                # 成功

                if not view_realtime_update:
                    if self.pre_copy is None or resized:
                        self.pre_copy = self.pipe.pre.copy()
                    else:
                        numpy.copyto(self.pre_copy, self.pipe.pre, 'no')
                    self.PreOutViewUpdateSignal.emit((True, time_calc_end - time_calc_start, resized))
                    # 刷新编码
                    self.code_is_need_update = True
                    
                    if self.code_update_notify:
                        with self.code_update_notify:
                            self.code_update_notify.notify_all()
                continue
            # 失败
            if not view_realtime_update:
                self.PreOutViewUpdateSignal.emit((False, "错误！", None))
        logger.info("预处理刷新线程 结束")

    def PreUpdateOutViewer(self, update_view: bool, t: float | int | str, resized: bool):
        """更新预处理输出"""
        arr = self.pre_copy
        if t == -1:
            t_str = "正在计算…"
        elif isinstance(t, str):
            t_str = t
        else:
            t_str = AutoFmtTime(t)
        self.pre_calc_time.setText(t_str)
        # 选择更新方式
        time_update_start = time.perf_counter()
        if update_view:
            if arr is None:
                logger.error("update_view为True，但arr为None")
            elif resized:
                # 数组尺寸发生变化，需要重新加载
                self.pre_out_viewer.update_arr(arr)
            else:
                self.pre_out_viewer.update_()
        time_update_end = time.perf_counter()
        # 创建提示文本
        mid_buf_len = len(self.pipe.img_pre_buf)
        # 计算大小
        mem_size = 0
        for buf in self.pipe.img_pre_buf:
            mem_size += buf.arr.nbytes
        autofmt_memsize, autofmt_memsize_unit = AutoFmtSize(mem_size)
        self.pre_top_widget.setToolTip(f"计算耗时：{t_str}\n更新耗时：{AutoFmtTime(time_update_end - time_update_start)}\n中间缓冲区：{mid_buf_len} 个, {autofmt_memsize:.2f} {autofmt_memsize_unit}")
        # 如果self.out_name为空，解除self.pre_copy对数组副本的引用
        if not self.out_name:
            # self.pre_copy = None
            pass


    def Pre_Delete(self, index: int):
        """删除预处理器"""
        # 获取对应索引的预处理项
        obj = self.pre_list[index]
        # 移除界面中对应索引的预处理项
        # obj.ui.setParent(None)
        obj.ui.deleteLater()
        # 删除self.pre_list中的元素
        del self.pre_list[index]
        # 删除wdg
        # obj.setParent(None)
        obj.deleteLater()
        # 重置（其实不需要）
        # self.ResetPre()
        # 计算需要更新的index
        new_i = index - 1
        if new_i < 0:
            new_i = 0
        self.Pre_Update(new_i)

    def Pre_Update(self, index: int = 0):
        # 设置必要的参数
        self.pre_update_index = index
        # 通知线程更新
        if self.pre_update_notify:
            with self.pre_update_notify:
                self.pre_update_notify.notify_all()
    def _Pre_Update(self, index: int = 0) -> bool:
        """更新预处理管线"""
        # print("Start")
        it = self.pipe.Pre(index, len(self.pre_list) == 0)
        # 设置工作模式
        it.mode = pipe_update_mode
        # 获取i的有效索引
        i = it.i
        # 再设置回去
        it.set_index(i)
        # print(f"i: {index}, Avaliable i: {i}")
        # 遍历从i到末尾
        for i, obj in enumerate(islice(self.pre_list, i, None), start = i):
            # print(f"预处理 {i} 开始")
            # 禁用，则name="", 参数为空
            if obj.enabled:
                py = obj.py
                name = obj.name
            else:
                py = None
                name = ""
            if py is not None and hasattr(py, "update"):
                try:
                    arg: ExtensionPyABC.CPointerArgType
                    arglen: int
                    arg, arglen = py.update(it.current_buf(unsafe=True).arr, self.pipe.tasks if self.pipe.tasks > 0 else self.pipe.plproc.get_threads())  # 如果函数返回两个值
                except:
                    logger.error(f"预处理 {i} 更新失败，错误信息：", exc_info=True)
                    continue
            else:
                arg, arglen = backend.NULLPTR, 0
            
            it.next(name, arg, arglen, i == 0, i == len(self.pre_list) - 1)

            # 获取中间缓冲区的长度
            # print("Buflen:", len(it.img_pre_buf))

            if py is not None and hasattr(py, "update_end"):
                try:
                    py.update_end(arg, arglen)
                except:
                    logger.error(f"预处理 {i} 更新结束失败，错误信息：", exc_info=True)
                    continue
        if it.pre_resized is None:
            logger.error("it.pre_resized 为 None")
            return True
        return it.pre_resized
    
    def SelectCode(self, name: str):
        """选择编码器"""

        self_ref = weakref.ref(self)
        
        new_wdg = None
        
        # 获取name对应的列表
        ext = self.pipe.extdc[backend.EXT_TYPE_CODE]["img"][name]
        # 获取name
        main_name = ext[backend.EXT_OP_INFO]["name"]
        # 尝试获取Python部分
        py_base = ext[backend.EXT_OP_EXT]
        if py_base is not None and hasattr(py_base, "UI"):
            py = py_base.UI()
        else:
            py = None

        err_cause = ""

        if py is not None and hasattr(py, "ui_init"):
            try:
                # 创建QWidget，并初始化
                new_wdg = QWidget()
                # 初始化UI
                py.ui_init(new_wdg, ext[backend.EXT_OP_CDLL], None)
                # 尝试绑定py.img2arr_notify_update
                def update_notify():
                    self = self_ref()
                    assert self is not None, "PageMain 已被销毁，不能再用了，一定是代码有问题"
                    self.code_is_need_update = True
                    if self.code_update_notify:
                        with self.code_update_notify:
                            self.code_update_notify.notify_all()
                py.img2arr_notify_update = update_notify
            except:
                logger.error(f"编码器 {name} 初始化失败，错误信息：", exc_info=True)
                err_cause = "初始化失败"
        else:
            err_cause = "没有控制台"
        # 更新文本
        self.code_main_text.setText(main_name)
        # 移除现有的QWidget，若不是code_args_default，则删除
        wdg = self.code_args_scrollarea.takeWidget()
        if wdg != self.code_args_default:
            # wdg.setParent(None)
            wdg.deleteLater()
        # 如果err_cause不为空，则显示错误信息，且self.code_py覆盖为None
        if err_cause:
            self.code_py = None
            self.code_args_default_text.setText(err_cause)
            self.code_args_scrollarea.setWidget(self.code_args_default)
        # 否则，换上新的wdg，并设置self.code_py为py
        else:
            self.code_py = py
            if new_wdg is not None:
                self.code_args_scrollarea.setWidget(new_wdg)
            else:
                logger.error(f"编码器 {name} 没有返回QWidget，但err_cause却为空")

        # 设置self.code_name
        self.code_name = name
        # 更新编码输出
        self.code_is_need_update = True
        if self.code_update_notify:
            with self.code_update_notify: 
                self.code_update_notify.notify_all()
    
    def _CodeViewUpdate(self):
        """更新编码预览输出，由CodeUpdateThread调用"""
        # 取副本
        arr = self.pre_copy
        if arr is None:
            logger.error("self.pre_copy 为 None")
            return False, False
        # 调用py，获取参数
        if self.code_py is not None and hasattr(self.code_py, "update"):
            args: ExtensionPyABC.CPointerArgType
            arglen: int
            args, arglen = self.code_py.update(arr, self.pipe.tasks if self.pipe.tasks > 0 else self.pipe.plproc.get_threads())
        else:
            args, arglen = backend.NULLPTR, 0
        # 调用编码预览
        ret = self.pipe.CodeView(self.code_name, args, arglen, arr)
        # 调用py的update_end（如果有）
        if self.code_py is not None and hasattr(self.code_py, "update_end"):
            try:
                self.code_py.update_end(args, arglen)
            except:
                logger.error(f"编码器控制台 update_end 调用失败，错误信息：", exc_info=True)
        return ret
 
    def CodeUpdateThread(self):
        """更新编码输出的线程"""
        self_ref = weakref.ref(self)
        while True:
            # 更新状态
            self.code_args_thread_state = 'idle'
            if self.code_update_notify is None: # 结束
                break
            with self.code_update_notify:
                self.code_update_notify.wait()
            if self.code_update_notify is None: # 结束
                break
            # 更新状态
            self.code_args_thread_state = 'run'
            resized = False # 是否需要更新输出尺寸
            self.CodeViewerOutViewUpdateSignal.emit((False, -1, None))
            time_calc_start = 0
            time_calc_end = 0
            while self.code_is_need_update:
                need_update = self.code_is_need_update
                self.code_is_need_update = False
                if not need_update: # 以防万一
                    continue
                time_calc_start = time.perf_counter()
                try:
                    if self.code_name != "":
                        _, new_resized = self._CodeViewUpdate()
                    else:
                        new_resized = False
                    resized = resized or new_resized # 任意一次需要更新尺寸，则最终需要更新
                except:
                    logger.error(f"编码器 {self.code_name} 更新失败，错误信息：", exc_info=True)
                    break
                time_calc_end = time.perf_counter()
                if view_realtime_update:
                    self.CodeViewerOutViewUpdateSignal.emit((True, time_calc_end - time_calc_start, resized, self.pipe.code_view.copy()))
                    self.OutPreUpdate()
                    resized = False # 重置，防止多次更新
            else:
                # 成功
                if not view_realtime_update:
                    self.CodeViewerOutViewUpdateSignal.emit((True, time_calc_end - time_calc_start, resized, self.pipe.code_view.copy()))
                    self.OutPreUpdate()
                continue
            # 失败
            if not view_realtime_update:
                self.CodeViewerOutViewUpdateSignal.emit((False, "错误！", None))
        
        logger.info("编码刷新线程 结束")
    
    def CodeUpdateOutViewer(self, update_view: bool, t: float | int | str, resized: bool, arr: Optional[NDArray] = None):
        if t == -1:
            t_str = "正在计算…"
        elif isinstance(t, str):
            t_str = t
        else:
            t_str = AutoFmtTime(t)
        self.code_calc_time.setText(t_str)
        # 选择更新方式
        time_update_start = time.perf_counter()
        if update_view:
            if arr is None:
                logger.error("update_view为True，但arr为None")
            elif resized:
                # 数组尺寸发生变化，需要重新加载
                self.code_out_viewer.update_arr(arr)
            else:
                # self.code_out_viewer.update_()
                self.code_out_viewer.update_arr(arr)
        time_update_end = time.perf_counter()
        # 创建提示文本
        self.code_top_widget.setToolTip(f"计算耗时：{t_str}\n更新耗时：{AutoFmtTime(time_update_end - time_update_start)}")

    def SelectOut(self, name: str):
        """选择输出"""

        # 格式与SelectCode相仿
        self_ref = weakref.ref(self)
        new_wdg = None

        # 获取name对应的输出
        ext = self.pipe.extdc[backend.EXT_TYPE_OUT]["img"][name]
        # 获取name
        main_name = ext[backend.EXT_OP_INFO]["name"]
        # 尝试获取Python部分
        py_base = ext[backend.EXT_OP_EXT]
        if py_base is not None and hasattr(py_base, "UI"):
            py = py_base.UI()
        else:
            py = None

        err_cause = ""

        if py is not None and hasattr(py, "ui_init"):
            try:
                # 创建QWidget，并初始化
                new_wdg = QWidget() 
                # 初始化UI
                py.ui_init(new_wdg, ext[backend.EXT_OP_CDLL], None)
                # 尝试绑定py.img2arr_notify_update
                def update_notify():
                    self = self_ref()
                    if self is None: 
                        logger.error("self_ref()返回None")
                        return

                    # 更新预览
                    self.OutPreUpdate()
                py.img2arr_notify_update = update_notify
                py.preview_textedit = self.out_preview
            except:
                logger.error(f"编码器 {name} 初始化失败，错误信息：", exc_info=True)
                err_cause = "初始化失败"
        else:
            err_cause = "没有控制台"
        # 更新文本
        self.out_main_text.setText(main_name)
        # 移除现有的QWidget，若不是code_args_default，则删除
        wdg = self.out_args_scrollarea.takeWidget()
        if wdg != self.out_args_default:
            # wdg.setParent(None)
            wdg.deleteLater()
        # 如果err_cause不为空，则显示错误信息，且self.code_py覆盖为None
        if err_cause:
            self.out_py = None
            self.out_args_default_text.setText(err_cause)
            self.out_args_scrollarea.setWidget(self.out_args_default)
        else:
            self.out_py = py
            if new_wdg is not None:
                self.out_args_scrollarea.setWidget(new_wdg)
            else:
                logger.error(f"编码器 {name} 没有返回QWidget，但err_cause却为空")
        
        # 设置self.out_name
        self.out_name = name
        # 刷新
        self.OutPreUpdate()

    def OutPreUpdate(self):
        # 如果有，先更新code_out
        if self.code_name:
            self.CodeUpdate()
        # 更新预览输出
        if self.out_py is not None and hasattr(self.out_py, "update_preview"):
            try:
                res = self.out_py.update_preview(self.pipe.code_out)
            except:
                logger.error(f"输出 {self.out_name} 更新失败，错误信息：", exc_info=True)
                return
            if res is False: # 当且仅当type(res) == bool 且 res == False 时，不显示预览
                # 隐藏预览
                self.out_preview_widget.setVisible(False)
            else:
                # 显示预览
                self.out_preview_widget.setVisible(True)

    def CodeUpdate(self):
        
        # 刷新code_out输出部分
        # 调用py，获取参数
        if self.code_py is not None and hasattr(self.code_py, "update"):
            args: ExtensionPyABC.CPointerArgType
            arglen: int
            args, arglen = self.code_py.update(self.pipe.pre, self.pipe.tasks if self.pipe.tasks > 0 else self.pipe.plproc.get_threads())
        else:
            args, arglen = backend.NULLPTR, 0
        # 调用编码预览
        if self.code_name:
            try:
                ret = self.pipe.Code(self.code_name, args, arglen)
            except:
                logger.error(f"编码器 {self.code_name} 更新失败，错误信息：", exc_info=True)
        else:
            logger.error("没有选择编码器！")
        # 调用py的update_end（如果有）
        if self.code_py is not None and hasattr(self.code_py, "update_end"):
            try:
                self.code_py.update_end(args, arglen)
            except:
                logger.error(f"编码器控制台 update_end 调用失败，错误信息：", exc_info=True)

    def test_OutSave(self, filepath: str):

        # 调用Python部分获取参数
        if self.out_py is not None and hasattr(self.out_py, "update"):
            try:
                args: ExtensionPyABC.CPointerArgType
                arglen: int
                args, arglen = self.out_py.update(self.pipe.code_out, threads)
            except:
                logger.error(f"输出 {self.out_name} 更新失败，错误信息：", exc_info=True)
                return
        else:
            args = backend.NULLPTR
            arglen = 0
        # 调用输出
        if self.out_name:
            ret = self.pipe.Out(self.out_name, args, arglen)
        else:
            logger.error("没有选择输出！")
        # 调用py的update_end（如果有）
        if self.out_py is not None and hasattr(self.out_py, "update_end"):
            try:
                self.out_py.update_end(args, arglen)
            except:
                logger.error(f"输出 {self.out_name} 控制台 update_end 调用失败，错误信息：", exc_info=True)
        # 保存
        self.pipe.out.tofile(filepath)


    def DestroyEvent(self) -> bool:
        """当即将被关闭标签页时调用
        返回是否允许关闭"""
        # 若任意一线程正在运行，则通过对话框询问是否关闭
        if self.pre_args_thread_state == 'idle' and self.code_args_thread_state == 'idle':
            return True
        ret = QMessageBox.question(self, "关闭", "计算线程仍在运行。是否仍然关闭？\n（关闭后，计算线程不会立即停止，且可能会产生非致命性错误）", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)

        return ret == QMessageBox.StandardButton.Yes
    
    def deleteLater(self):
        """清理回调"""
        logger.info("主页面被deleteLater()")
        # 删除线程
        notify = self.pre_update_notify
        self.pre_update_notify = None
        if notify:
            with notify:
                notify.notify_all()
        notify = self.code_update_notify
        self.code_update_notify = None
        if notify:
            with notify:
                notify.notify_all()
        # 删除所有预处理器界面
        for obj in self.pre_list:
            # obj.setParent(None)
            obj.deleteLater()
        # 删除编码器界面
        # self.code_args_scrollarea.takeWidget().deleteLater()
        # 手动删除所有图片查看器
        # self.base_out_viewer.deleteLater()
        # self.pre_out_viewer.deleteLater()
        # 断开信号
        try: self.PreOutViewUpdateSignal.disconnect()
        except: pass
        try: self.CodeViewerOutViewUpdateSignal.disconnect()
        except: pass
        # 绑定删除信号
        self.destroyed.connect(lambda: logger.info("主页面成功被destroyed()"))
        # 删除自身
        super().deleteLater()
    def __del__(self):
        logger.info("主页面被__del__()")

PageMainSelf = TypeVar('PageMainSelf', bound=PageMain)

class PreProcessor(QObject):
    def __init__(self, pagemain_ref: weakref.ref[PageMainSelf], name: str, title: str, py: ExtensionPyABC.abcExt.UI | None):
        super().__init__()
        self_ref = weakref.ref(self)
        self.pagemain_ref = pagemain_ref
        self.py = py
        self.name = name
        self.title = title
        self.enabled = True
        # 设置py的绑定函数
        # print("自身id:", id(self))
        # print(type(self.py))
        if self.py is not None:
            # print("挂载回调")
            self.py.img2arr_notify_update = lambda: self.img2arr_notify_update() if (self := self_ref()) else logger.error("资源管理错误: self_ref() 返回 None")
        self.ui, self.ui_in = self.init_ui()
    @property
    def pagemain(self) -> PageMain:
        ref = self.pagemain_ref()
        assert ref is not None, "pagemain_ref is None"
        return ref
    
    def img2arr_notify_update(self):
        # self = self_ref()
        # if not self: return
        self_i = self.pagemain.Pre_FindIndex(self)
        # print("img2arr_notify_update", self_i, "对象id:", id(self))
        self.pagemain.Pre_Update(self_i)

    update_tiptext_signal = Signal(str)

    def init_ui(self) -> tuple[QWidget, QWidget]:
        ui = QWidget()
        ui.setMinimumSize(0, 0)

        self_ref = weakref.ref(self)
        # 1. 水平忽略内部组件拉伸，同时尽可能拉伸；垂直最小化
        ui.setSizePolicy(
            QSizePolicy.Policy.Ignored, 
            # QSizePolicy.Policy.MinimumExpanding
            QSizePolicy.Policy.Minimum
        )
        # 自身布局
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        ui.setLayout(layout)
        # 上层QWidget
        wdg_upper = QWidget()
        # 占满宽度，最小高度
        wdg_upper.setSizePolicy(    
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Minimum
        )
        # 添加到布局
        layout.addWidget(wdg_upper)
        # 创建悬停提示
        wdg_upper.setToolTip("提示")
        # 添加布局
        layout_upper = QHBoxLayout()
        layout_upper.setContentsMargins(0, 0, 0, 0)

        # 添加右键菜单
        def wdg_upper_contextMenuEvent(event: QContextMenuEvent):
            self = self_ref()
            if not self: return
            # 获取自身i
            i = self.pagemain.Pre_FindIndex(self)
            maxi = len(self.pagemain.pre_list) - 1
            # 创建菜单
            menu = QMenu()
            # 添加删除选项
            action = menu.addAction("删除")
            # 菜单点击事件
            action.triggered.connect(lambda: self.pagemain.Pre_Delete(i) if (self := self_ref()) else logger.error("资源管理错误: self_ref() 返回 None"))
            # 上移
            action = menu.addAction("上移")
            # 若i=0，则禁用
            action.setEnabled(i != 0)
            # 菜单点击事件
            action.triggered.connect(lambda: self.pagemain.Pre_Move(i, -1) if (self := self_ref()) else logger.error("资源管理错误: self_ref() 返回 None"))
            # 下移
            action = menu.addAction("下移")
            # 若i=len-1，则禁用
            action.setEnabled(i != maxi)
            # 菜单点击事件
            action.triggered.connect(lambda: self.pagemain.Pre_Move(i, 1) if (self := self_ref()) else logger.error("资源管理错误: self_ref() 返回 None"))
            # 显示菜单
            menu.exec(event.globalPos())
        wdg_upper.contextMenuEvent = wdg_upper_contextMenuEvent

        # 设置为全局左对齐
        layout_upper.setAlignment(Qt.AlignmentFlag.AlignLeft)
        wdg_upper.setLayout(layout_upper)
        # 添加折叠icon（SP_TitleBarShadeButton）
        collapse = QToolButton()
        style = QApplication.style()
        collapse.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TitleBarShadeButton))
        # layout_upper.addWidget(collapse)

        # 添加CheckBox,选中
        cb = QCheckBox()
        cb.setChecked(True)
        layout_upper.addWidget(cb)
        # 添加文本
        text = QLabel(self.title)
        layout_upper.addWidget(text)
        # 添加斜体文本，颜色为dark，可被选中
        tiptext = QLabel()
        tiptext.setStyleSheet("font-style: italic; color: gray;")
        tiptext.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout_upper.addWidget(tiptext)
        tiptext_ref = weakref.ref(tiptext)

        self.update_tiptext_signal.connect(lambda text: tiptext.setText(text) if (tiptext := tiptext_ref()) else logger.error("资源管理错误: tiptext_ref() 返回 None"))

        # 如果py不为None, 绑定回调
        if self.py is not None:
            # 线程安全的方式来更新tiptext
            def img2arr_UpdateTiptext(text: str):
                self = self_ref()
                if not self: return
                self.update_tiptext_signal.emit(text)
            self.py.img2arr_UpdateTiptext = img2arr_UpdateTiptext

        # 添加QScrollArea
        scroll = CustomUI.FakeQScrollArea()
        # scroll = QScrollArea()
        # scroll = CustomUI.SeniorQScrollArea()
        scroll.setMinimumSize(0, 0)
        # scroll.setStyleSheet("background-color: blue;") #调试用
        # 2. 水平忽略内部组件拉伸，同时尽可能拉伸；垂直手动调整
        scroll.setSizePolicy(
            QSizePolicy.Policy.Ignored, 
            # QSizePolicy.Policy.Minimum
            QSizePolicy.Policy.Preferred
        )
        layout.addWidget(scroll)
        # 设置
        scroll.setWidgetResizable(True)
        scroll.setBackgroundRole(QPalette.ColorRole.Base)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # 事件，cb未选中，则tiptext带删除线，同时禁用scroll
        def cb_stateChanged(state: int):
            self = self_ref()
            if not self: return
            # QMessageBox.critical(ui, "错误", "未实现预处理扩展的启用/禁用功能！将在未来版本中实现")
            # cb.setChecked(True)
            # return
            if state == Qt.CheckState.Unchecked.value:
                tiptext.setStyleSheet("font-style: italic; color: gray; text-decoration: line-through;")
                self.enabled = False
            else:
                tiptext.setStyleSheet("font-style: italic; color: gray;")
                self.enabled = True
            scroll.setEnabled(self.enabled)
            # 发送更新通知
            self.img2arr_notify_update()
        
        cb.stateChanged.connect(cb_stateChanged)
        # 创建uwidg是scroll的widget
        uwidg = QWidget(ui)
        uwidg.setMinimumSize(0, 0)
        # 3. 水平拉伸，垂直自适应
        uwidg.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            # QSizePolicy.Policy.Minimum
            QSizePolicy.Policy.Preferred
        )
            
        scroll.setWidget(uwidg)

        # 当uwidg resize时，更新scroll的fixedHeight
        def uwidg_resizeEvent(event: QResizeEvent):
            self = self_ref()
            if not self: return
            QWidget.resizeEvent(scroll, event)
            scroll.setFixedHeight(uwidg.height() + 10)
            # logger.debug(f"uwidg_resizeEvent: {event.size()}")
        # uwidg.resizeEvent = uwidg_resizeEvent

        return ui, uwidg
    def deleteLater(self):
        logger.info(f"{self.title} 删除")
        super().deleteLater()

   

if __name__ == "__main__":
    # 初始化设置
    # 加载配置
    InitSet()
    # 初始化线程数
    threads_local = GetSet("Parallel.Threads")
    if not isinstance(threads_local, int) or threads_local < 0:
        SetSet("Parallel.Threads", 0)
        threads_local = 0
    threads = int(threads_local)
    backend.SetParallelThreads(threads)
    # 加载UI
    app = QApplication(sys.argv)
    # 获取所有风格
    styles = QStyleFactory.keys()
    logger.debug(f"可用风格：\n{'\n'.join(styles)}")
    # 设置风格
    # app.setStyle("Fusion")
    # 设置第三方风格
    # from qt_material import apply_stylesheet
    # apply_stylesheet(app, theme='dark_teal.xml')
    win = QMainWindow()

    main = WinMain(app, win) # 直接调用WinMain会导致事件函数无法绑定
    win.show()
    sys.exit(app.exec())
else:
    import img2arr # 加载命令行版本