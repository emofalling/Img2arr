# 扩展的编译管理器

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QStyleFactory, 
    QWidget, QFrame, QScrollArea,
    QLabel, QPushButton, QCheckBox, QSlider,
    QListWidget, QLineEdit, QPlainTextEdit, QTextEdit, 
    QHBoxLayout, QVBoxLayout, QSplitter,
    QTabWidget, QTabBar, QSizePolicy, 
    QMenu, QToolTip, QToolButton,
    QDialogButtonBox, QStyle, 
    QGraphicsView, QGraphicsScene, 
    QGraphicsPixmapItem, QGraphicsRectItem,
    QMessageBox, QFileDialog
)


from PySide6.QtGui import (QCloseEvent, QAction, 
    QPixmap, QImage, QPainter, QPalette, 
    QFontDatabase, QFont, QFontMetrics, 
    QTextOption, 
    QWheelEvent, QMouseEvent, QKeyEvent, QResizeEvent, QDragEnterEvent, QDropEvent, QContextMenuEvent,
    QColor, QPen, QBrush)

from PySide6.QtCore import Qt, QTimer, QObject, QMetaObject, QGenericArgument, Signal, QUrl, QRect, QRectF

from typing import Optional, Sequence, Iterator

import os, sys, subprocess, threading

import hashlib

import platform

import weakref

from lib import SpecialArch

runtime_name_list: list[str] = ['PlProcCore.cpp']



os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 获取CPU系统（小写）
system = platform.system().lower()
if system == "windows": soext = "dll"
elif system == "linux": soext = "so"
elif system == "darwin": soext = "dylib"
else: soext = "so"
# 获取CPU架构（小写）
arch = platform.machine().lower()
arch = SpecialArch.GetNormalArchName(arch)

platform_str = f"{system}_{arch}"

# 编译时。
COLOR_COMPILING = QColor(200, 200, 200, 150)
# 是最新的。
COLOR_SUCCRSS = QColor(0, 255, 0, 150)
# 原代码已更改，但是未重新编译。
COLOR_NOTLATEST = QColor(255, 255, 0, 150)
# 有源文件，但是没有编译。
COLOR_NOTARGET = QColor(10, 80, 255, 150)
# 编译失败。
COLOR_ERROR = QColor(255, 0, 0, 150)


def generate_hash(dir: str) -> str:
    """生成编译哈希。遍历dir底下所有.c/.cpp文件，计算哈希值，并返回hashhex"""
    hash = hashlib.sha256()
    # 遍历dir底下所有.c/.cpp文件，计算哈希值
    for path, dirs, files in os.walk(dir):
        for file in files:
            if file.endswith(".c") or file.endswith(".cpp"):
                with open(os.path.join(path, file), "rb") as f:
                    hash.update(f.read())
    return hash.hexdigest()

def save_hash(dir: str):
    """保存编译哈希。将dir底下所有.c/.cpp文件的哈希值添加到.hash文件中"""
    hashhex = generate_hash(dir)
    print("save_hash: hashhex=", hashhex)
    try:
        with open(os.path.join(dir, ".hash"), "r", encoding="utf-8") as f:
            hash_str = f.read()
    except FileNotFoundError:
        hash_str = ""
    except Exception as e:
        print("文件", os.path.join(dir, ".hash"), "读取失败:", e)
        return
    new_hashstr = ""
    hash_appended = False
    for line in hash_str.splitlines():
        arglist = line.split(":", 1)
        if len(arglist) < 2:
            continue
        platform = arglist[0]
        if platform == platform_str:
            if hash_appended:
                new_hashstr += f"{platform_str}:{hashhex}\n"
                hash_appended = True
        else:
            new_hashstr += line + "\n"
    if not hash_appended:
        new_hashstr += f"{platform_str}:{hashhex}\n"
        
    print("save_hash: new_hashstr=", new_hashstr)
    with open(os.path.join(dir, ".hash"), "w", encoding="utf-8") as f:
        f.write(new_hashstr)
    

def verify_hash(dir: str) -> bool | None:
    """验证编译哈希。验证dir底下所有.c/.cpp文件的哈希值是否与.hash文件一致. 若.hash不存在或不存在目标字段，则返回False。None表示读取文件失败"""
    hashfile = os.path.join(dir, ".hash")
    try:
        with open(hashfile, "r", encoding="utf-8") as f:
            hash_str = f.read()
    except FileNotFoundError:
        return None
    except Exception as e:
        print("文件", hashfile, "读取失败:", e)
        return None
    # 生成hash
    hashhex_target = generate_hash(dir)
    print("verify_hash: hashhex=", hashhex_target)
    # 分割hash，按行，每行格式为platform_str:hashhex
    for line in hash_str.splitlines():
        arglist = line.split(":", 1)
        if len(arglist) < 2:
            continue
        platform = arglist[0]
        hashhex = arglist[1]
        if platform != platform_str:
            continue
        if hashhex == hashhex_target:
            return True
    return False


class WinMain(QObject):
    def __init__(self, app: QApplication, win: QMainWindow):
        super().__init__()
        self.app = app
        self.win = win
        self.setwindow()
        self.setcontext()
    def setwindow(self):
        self.win.resize(800, 600)
        self.win.setWindowTitle("img2arr编译管理器")
        self.win.setWindowIcon(self.app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
    def setcontext(self):
        self.main_widget = QWidget()
        self.win.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout()
        self.main_widget.setLayout(self.main_layout)

        self.tabwdg = QTabWidget()
        self.main_layout.addWidget(self.tabwdg)

        self.runtime_wdg = QWidget()
        self.tabwdg.addTab(self.runtime_wdg, "运行库")

        # self.open_wdg = QWidget()
        # self.tabwdg.addTab(self.open_wdg, "打开")
        self.prep_wdg = QWidget()
        self.tabwdg.addTab(self.prep_wdg, "预处理")

        self.code_wdg = QWidget()
        self.tabwdg.addTab(self.code_wdg, "转码")

        self.out_wdg = QWidget()
        self.tabwdg.addTab(self.out_wdg, "输出")

        self.main_layout.addWidget(self.tabwdg)

        # 设置顶部菜单
        self.menu_bar = self.win.menuBar()
        self.file_menu = self.menu_bar.addMenu("界面")
        self.file_menu.addAction("重新加载", lambda: self.Reload())

        # F5: 重新加载
        self.win.keyPressEvent = lambda event: self.Reload() if event.key() == Qt.Key.Key_F5 else None



        self.setup_runtime_wdg()
        self.setup_prep_wdg()
        self.setup_code_wdg()
        self.setup_out_wdg()

        
    
    class CompileItem(QWidget):
        update_compile_state_signal = Signal(tuple)
        def __init__(self, dir: str, name: str, singlefile: bool = False):
            super().__init__()

            self_ref = weakref.ref(self)

            self.dir = dir
            self.name = name
            self.singlefile = singlefile
            self.state: str = ""
            if self.singlefile:
                self.target_output = f"{self.name[:self.name.rfind('.')]}_{platform_str}.{soext}"
            else:
                self.target_output = f"main_{platform_str}.{soext}"

            # self.setFrameShape(QFrame.Shape.Box) 
            # self.setFrameShadow(QFrame.Shadow.Plain)
            self.main_layout = QHBoxLayout()
            self.main_layout.setContentsMargins(2, 2, 2, 2)
            self.setLayout(self.main_layout)

            self.name_label = QLabel(name)
            self.main_layout.addWidget(self.name_label)
            
            self.compile_button = QPushButton("编译")
            rect = self.compile_button.fontMetrics().boundingRect(self.compile_button.text())
            self.compile_button.setFixedWidth(rect.width() + 10)
            self.main_layout.addWidget(self.compile_button, Qt.AlignmentFlag.AlignRight)
            self.compile_button.clicked.connect(self.compile)

            # 设置自身的右键菜单
            self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.customContextMenuRequested.connect(self.show_context_menu)


            self.update_compile_state_signal.connect(lambda args: self.update_compile_state(*args) if (self := self_ref()) else None)

            print("Target output:", os.path.join(self.dir, self.target_output))

            if os.path.isfile(os.path.join(self.dir, self.target_output)):
                hash_suc = verify_hash(self.dir)
                if hash_suc:
                    self.state = "ok"
                else:
                    self.state = "nocp"
            else:
                self.state = "notgt"


            self.update_compile_state()
        
        def show_context_menu(self, pos):
            menu = QMenu(self)
            if self.state == "ok":
                menu.addAction("强制编译", self.compile)
            elif self.state != "compiling":
                menu.addAction("编译", self.compile)
            menu.exec(self.mapToGlobal(pos))


        def update_compile_state(self, custom_color: Optional[QColor] = None, show_compile_button: Optional[bool] = None):
            self.setEnabled(True)
            self_palette = self.palette()
            if custom_color is not None:
                self_palette.setColor(QPalette.ColorRole.Base, custom_color)
            else:
                if self.state == "compiling":
                    self_palette.setColor(QPalette.ColorRole.Base, COLOR_COMPILING)
                    self.setToolTip("正在编译中")
                elif self.state == 'ok':
                    self_palette.setColor(QPalette.ColorRole.Base, COLOR_SUCCRSS)
                    self.setToolTip("编译结果是最新的")
                elif self.state == 'nocp':
                    self_palette.setColor(QPalette.ColorRole.Base, COLOR_NOTLATEST)
                    self.setToolTip("源代码发生更改，但尚未编译")
                elif self.state == 'notgt':
                    self_palette.setColor(QPalette.ColorRole.Base, COLOR_NOTARGET)
                    self.setToolTip("尚未编译")
                elif self.state == 'error':
                    self_palette.setColor(QPalette.ColorRole.Base, COLOR_ERROR)
                    self.setToolTip("编译失败。错误信息请见控制台输出。")
                else:
                    print("发生例外情况，state=", self.state)
            self.setPalette(self_palette)
            self.setAutoFillBackground(True)
            if show_compile_button is not None:
                self.compile_button.setVisible(show_compile_button)
            else:
                if self.state == 'ok':
                    self.compile_button.setVisible(False)
                else:
                    self.compile_button.setVisible(True)

            self.update()
        def compile_main(self):
            print("开始编译运行库:", self.name)
            try:
                if self.singlefile:
                    subprocess.run([
                        "g++",
                        self.name,
                        "-shared", "-fPIC",
                        "-o", f"{self.name[:self.name.rfind('.')]}_{platform_str}.{soext}",
                        "-O3",
                        "-std=c++23"
                    ], cwd=self.dir, check=True)
                else:
                    output = self.target_output
                    # raise Exception("暂不支持多文件编译")
                    # 若环境非Windows且底下有compile.sh，则调用compile.sh
                    if system != 'windows' and os.path.isfile(os.path.join(self.dir, "compile.sh")):
                        print("使用compile.sh")
                        subprocess.run([
                            "bash",
                            "compile.sh"
                        ], cwd=self.dir, check=True)
                    # 否则，如果系统是Windows且底下有compile.ps1，则调用compile.ps1
                    elif system == 'windows' and os.path.isfile(os.path.join(self.dir, "compile.ps1")):
                        print("使用compile.ps1")
                        subprocess.run([
                            "powershell.exe",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-File",
                            "compile.ps1",
                            output
                        ], cwd=self.dir, check=True)
                    # 否则，如果系统是Windows且底下有compile.bat，则调用compile.bat
                    elif system == 'windows' and os.path.isfile(os.path.join(self.dir, "compile.bat")):
                        print("使用compile.bat")
                        subprocess.run([
                            "cmd.exe",
                            "/c",
                            "compile.bat",
                            output
                        ], cwd=self.dir, check=True)
                    # 直接使用gcc编译
                    else:
                        # 如果存在main.c，则编译main.c
                        if os.path.isfile(os.path.join(self.dir, "main.c")):
                            subprocess.run([
                                "gcc",
                                "main.c",
                                "-shared", "-fPIC",
                                "-o", output,
                                "-O3"
                            ], cwd=self.dir, check=True)
                        # 否则，如果存在main.cpp，则编译main.cpp
                        elif os.path.isfile(os.path.join(self.dir, "main.cpp")):
                            subprocess.run([
                                "g++",
                                "main.cpp",
                                "-shared", "-fPIC",
                                "-o", output,
                                "-O3",
                            ], cwd=self.dir, check=True)
                        # 否则，提示错误
                        else:
                            raise Exception("未找到main.c或main.cpp")

            except Exception as e:
                print("编译失败，报错:", e)
                self.state = "error"
            else:
                print("编译成功")
                self.state = "ok"
                save_hash(self.dir)
            self.update_compile_state_signal.emit(())

        def compile(self):
            self.state = "compiling"
            self.update_compile_state_signal.emit(())
            self.setEnabled(False)
            threading.Thread(target=self.compile_main, daemon=True).start()

    class GeneralScrollFrame(QScrollArea):
        def __init__(self, parent=None):
            super().__init__(parent)

            self.setWidgetResizable(True)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

            self.setFrameShape(QFrame.Shape.NoFrame) # 无边框
            self.setContentsMargins(0, 0, 0, 0)
            self.setBackgroundRole(QPalette.ColorRole.Base)
            # 确保背景色生效
            self.setAutoFillBackground(True)
            self.main_widget = QWidget()
            self.setWidget(self.main_widget)
            self.main_layout = QVBoxLayout()
            self.main_layout.setContentsMargins(0, 0, 0, 0)
            self.main_layout.setSpacing(2)
            self.main_widget.setLayout(self.main_layout)


    def setup_runtime_wdg(self):
        self.runtime_layout = QVBoxLayout()
        self.runtime_wdg.setLayout(self.runtime_layout)

        self.runtime_scroll = self.GeneralScrollFrame()
        self.runtime_layout.addWidget(self.runtime_scroll)

        self.runtime_main_layout = self.runtime_scroll.main_layout

        self.load_runtime_wdg()

    def setup_general_wdg(self) -> tuple[QVBoxLayout, QVBoxLayout]:
        """通用。返回两个布局，第一个是主布局，第二个是项目列表布局"""
        layout = QVBoxLayout()

        scroll = self.GeneralScrollFrame()
        layout.addWidget(scroll)

        main_layout = scroll.main_layout

        return layout, main_layout


    def load_generel_wdg(self, main_layout: QVBoxLayout, dir_name_list: list[tuple[str, str]]):
        # 清空main_layout
        while main_layout.count():
            wdg = main_layout.takeAt(0).widget()
            if wdg is not None:
                wdg.deleteLater()
        # 重新布局
        for dir_name, name in dir_name_list:
            wdg = self.CompileItem(dir_name, name)
            main_layout.addWidget(wdg)
        main_layout.addStretch()

    def load_runtime_wdg(self):
        # 清空self.runtime_main_layout
        while self.runtime_main_layout.count():
            wdg = self.runtime_main_layout.takeAt(0).widget()
            if wdg is not None:
                wdg.deleteLater()
        # 重新布局
        for name in runtime_name_list:
            wdg = self.CompileItem('./lib', name, singlefile=True)
            self.runtime_main_layout.addWidget(wdg)
        
        self.runtime_main_layout.addStretch()
    
    def setup_prep_wdg(self):
        self.prep_layout, self.prep_main_layout = self.setup_general_wdg()
        self.prep_wdg.setLayout(self.prep_layout)

        self.load_prep_wdg()

    def load_prep_wdg(self):
        dirlist = os.listdir("./prep/img")

        dir_name_list: list[tuple[str, str]] = []
        for dir_name in dirlist:
            dir_name_list.append((f"./prep/img/{dir_name}", dir_name))

        self.load_generel_wdg(self.prep_main_layout, dir_name_list)
    
    def setup_code_wdg(self):
        self.code_layout, self.code_main_layout = self.setup_general_wdg()
        self.code_wdg.setLayout(self.code_layout)
        self.load_code_wdg()
        
    def load_code_wdg(self):
        dirlist = os.listdir("./code/img")
        dir_name_list: list[tuple[str, str]] = []
        for dir_name in dirlist:
            dir_name_list.append((f"./code/img/{dir_name}", dir_name))
        self.load_generel_wdg(self.code_main_layout, dir_name_list)

    def setup_out_wdg(self):
        self.out_layout, self.out_main_layout = self.setup_general_wdg()
        self.out_wdg.setLayout(self.out_layout)
        self.load_out_wdg()
    
    def load_out_wdg(self):
        dirlist = os.listdir("./out/img")
        dir_name_list: list[tuple[str, str]] = []
        for dir_name in dirlist:
            dir_name_list.append((f"./out/img/{dir_name}", dir_name))
        self.load_generel_wdg(self.out_main_layout, dir_name_list)
    
    def Reload(self):
        self.load_runtime_wdg()
        self.load_prep_wdg()
        self.load_code_wdg()
        self.load_out_wdg()






    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = QMainWindow()
    WinMain(app, win)
    win.show()
    sys.exit(app.exec())