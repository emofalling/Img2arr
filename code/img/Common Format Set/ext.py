from numpy import uint8, zeros
from numpy.typing import NDArray
from ctypes import CDLL, c_int, c_uint8, c_bool, c_size_t, c_char_p, POINTER, Structure, cast, byref, sizeof
import weakref

from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QCheckBox, QSlider, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QSizePolicy, QFileDialog, QMessageBox

from PySide6.QtCore import Qt, QTimer, QObject, Signal

from PySide6.QtGui import QPalette, QColor, QFontMetrics, QIntValidator

from lib.ExtensionPyABC import abcExt

import logging, os.path

logger = logging.getLogger(os.path.basename(os.path.dirname(__file__)))

    
class UI(abcExt.UI):
    def __init__(self):
        pass
    def ui_init(self, widget: QWidget, ext: CDLL, save: dict | None):
        self_ref = weakref.ref(self)
        self.lut: NDArray[uint8] | None = None

        layout = QVBoxLayout(widget)
        widget.setLayout(layout)

        list_layout = QHBoxLayout()
        list_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(list_layout)

        list_layout.addWidget(QLabel("格式: "))

        self.list = QComboBox()
        self.list.currentIndexChanged.connect(lambda: self.img2arr_notify_update() if (self := self_ref()) else None)
        list_layout.addWidget(self.list)
        # 设置水平拉伸
        self.list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # 添加项
        self.list.addItems([
            "不要选这个",
            "RGB565",
            "RGB332"
        ])
        self.list_format_map = [
            None,
            'RGB 5 6 5',
            'RGB 3 3 2'
        ]
        self.list.setCurrentIndex(1) # 默认RGB565

        # 使用LUT
        self.use_lut = QCheckBox("使用LUT")
        layout.addWidget(self.use_lut)
        self.use_lut.stateChanged.connect(lambda: self.img2arr_notify_update() if (self := self_ref()) else None)

        # LUT部分 Widget
        lut_widget = QWidget()
        layout.addWidget(lut_widget)
        lut_layout = QVBoxLayout(lut_widget)
        lut_layout.setContentsMargins(20, 0, 0, 0)
        lut_widget.setLayout(lut_layout)

        # 刷新lut_widget显隐
        def refresh_lut_widget():
            if self.use_lut.isChecked(): 
                lut_widget.show()
            else: 
                lut_widget.hide()

        self.use_lut.stateChanged.connect(refresh_lut_widget)

        # LUT路径
        lut_path_layout = QHBoxLayout()
        lut_layout.addLayout(lut_path_layout)

        self.lut_path_label = QLabel("LUT文件: ")
        lut_path_layout.addWidget(self.lut_path_label)

        self.lut_path_edit = QLineEdit()
        lut_path_layout.addWidget(self.lut_path_edit)

        # LUT路径按钮
        def open_lut_file_dialog():
            self = self_ref()
            if not self: return

            path, _ = QFileDialog.getOpenFileName()
            if not path:
                return

            self.lut_path_edit.setText(path)
            # self.open_lut()
        
        lut_button = QPushButton("浏览")
        lut_path_layout.addWidget(lut_button)
        lut_button.clicked.connect(open_lut_file_dialog)
        # lineedit绑定open_lut
        self.lut_path_edit.textChanged.connect(lambda: self.open_lut(silence=True) if (self := self_ref()) else None)

        # 警告文本，默认隐藏，可复制
        self.warn_label = QLabel("当前LUT文件存在问题，但显示在了一个错误的时机")
        self.warn_label.setStyleSheet('color: red')
        self.warn_label.setWordWrap(True)
        self.warn_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByKeyboard | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        lut_layout.addWidget(self.warn_label)
        self.warn_label.hide()

        # 在预览时使用LUT
        self.lut_in_preview = QCheckBox("在预览中使用LUT")
        lut_layout.addWidget(self.lut_in_preview)
        self.lut_in_preview.stateChanged.connect(lambda: self.img2arr_notify_update() if (self := self_ref()) else None)

        # 底部弹簧
        layout.addStretch()

        refresh_lut_widget()
    def open_lut(self, silence: bool = False):
        cur_format = self.list.currentIndex()
        try:
            with open(self.lut_path_edit.text(), "r", encoding='ascii') as f:
                def read_next_line() -> str:
                    while True:
                        line = f.readline().strip()
                        if not line: raise ValueError('行数不足')
                        if line.startswith("#"): continue
                        break
                    return line
                # 读取输入格式
                input_format = read_next_line()
                if input_format != 'RGB 8 8 8':
                    raise ValueError(f'不支持的LUT输入格式: {input_format}')
                # 读取输出格式
                output_format = read_next_line()
                try:
                    target_output_format = self.list_format_map[cur_format]
                except IndexError:
                    raise ValueError('LUT输出格式尚未支持')
                if output_format is None: raise ValueError(f'当前选项不支持LUT')
                if output_format != target_output_format: raise ValueError(f'LUT输出格式与当前模式不匹配, 当前为 {output_format}, 需要的格式是 {target_output_format}')
                # 读取数据
                lut = zeros(256*3, dtype=uint8)
                for i in range(lut.size):
                    lut[i] = int(read_next_line())
                self.lut = lut
                
            if not silence:
                QMessageBox.information(None, "成功", f"打开LUT文件成功: {self.lut_path_edit.text()}", QMessageBox.StandardButton.Ok)
            self.img2arr_notify_update()
        except Exception as e:
            err_msg = f"打开LUT文件失败: \n{e.__class__.__name__}: {e}"
            if not silence:
                logger.warning(err_msg)
                QMessageBox.critical(None, "错误", err_msg, QMessageBox.StandardButton.Ok)
            self.warn_label.setText(err_msg)
            self.warn_label.show()
        else:
            self.warn_label.hide()
    """
    typedef struct {
        // 这里填写参数列表
        // Fill in the output parameter list here

        // mode 转换模式
        int mode;
        // LUT: R+G+B。应有256*3=768个元素，每个元素在0~<当前色彩空间最大值>之间。
        uint8_t *lut;
        // 是否在预览中使用LUT。
        bool use_lut_in_preview;
    }__attribute__((packed)) args_t;
    """
    class args_t(Structure):
        _fields_ = [
            ("mode", c_int),
            # LUT: R+G+B。应有256*3=768个元素，每个元素在0~<当前色彩空间最大值>之间。
            ("lut", POINTER(c_uint8)),
            # 是否在预览中使用LUT。
            ("use_lut_in_preview", c_bool)
        ]
        _pack_ = 1


    def update(self, arr, threads: int):
        fmt_enum = self.list.currentIndex()
        # fmt_enum_ct = c_int(fmt_enum)
        # return byref(fmt_enum_ct), sizeof(fmt_enum_ct)
        args = UI.args_t(mode=fmt_enum)
        args.mode = fmt_enum
        if self.lut is None or not self.use_lut.isChecked(): args.lut = None
        else: 
            args.lut = self.lut.ctypes.data_as(POINTER(c_uint8))
            print("使用LUT")
        args.use_lut_in_preview = self.lut_in_preview.isChecked() and self.use_lut.isChecked()
        return byref(args), sizeof(args)


