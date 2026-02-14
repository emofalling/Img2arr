from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QLineEdit, QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox, QRadioButton, QButtonGroup
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from lib.ExtensionPyABC import abcExt
from numpy import nan, full, float32
from ctypes import (
    CDLL,
    c_float, c_int, c_uint16, c_bool, c_size_t, c_uint, 
    Structure, POINTER,
    byref, sizeof
)

INT32_MAX = 2**31-1

def signal_format_int(i:int, format:str = "d"):
    if i == 0:
        return f"{i:{format}}"
    else:
        return f"{i:+{format}}"

class UI(abcExt.UI):
    def __init__(self):
        ...
    def ui_init(self, widget: QWidget, ext: CDLL, save: dict | None):
        # atomic_size_t* atomic_init_size_t(atomic_size_t* p, size_t v)
        self.ext = ext
        ext.atomic_init_size_t.argtypes = [POINTER(c_size_t), c_size_t]
        ext.atomic_init_size_t.restype = POINTER(c_size_t)
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # H
        h_layout = QHBoxLayout()
        layout.addLayout(h_layout)
        # h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.addWidget(QLabel("色调偏移: "))
        self.h_change = QSlider(Qt.Orientation.Horizontal)
        h_layout.addWidget(self.h_change)
        self.h_change.setRange(-180, 180)
        self.h_change.setValue(0)
        self.h_change.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.h_change.setTickInterval(30)
        self.h_change.setPageStep(60)
        self.h_change.valueChanged.connect(self.Update)
        self.h_num_text = QLabel("0°")
        self.h_num_text.setFixedWidth(QFontMetrics(self.h_num_text.font()).horizontalAdvance("+360°"))
        h_layout.addWidget(self.h_num_text)
        # S
        s_layout = QHBoxLayout()
        layout.addLayout(s_layout)
        # s_layout.setContentsMargins(0, 0, 0, 0)
        s_layout.addWidget(QLabel("饱和偏移: "))
        self.s_change = QSlider(Qt.Orientation.Horizontal)
        s_layout.addWidget(self.s_change)
        self.s_change.setRange(-100, 100)
        self.s_change.setValue(0)
        self.s_change.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.s_change.setTickInterval(10)
        self.s_change.setPageStep(20)
        self.s_change.valueChanged.connect(self.Update)
        self.s_num_text = QLabel("0%")
        self.s_num_text.setFixedWidth(QFontMetrics(self.s_num_text.font()).horizontalAdvance("+100%"))
        s_layout.addWidget(self.s_num_text)
        # V
        v_layout = QHBoxLayout()
        layout.addLayout(v_layout)
        # v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.addWidget(QLabel("亮度偏移: "))
        self.v_change = QSlider(Qt.Orientation.Horizontal)
        v_layout.addWidget(self.v_change)
        self.v_change.setRange(-255, 255)
        self.v_change.setValue(0)
        self.v_change.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.v_change.setTickInterval(15)
        self.v_change.setPageStep(15)
        self.v_change.valueChanged.connect(self.Update)
        self.v_num_text = QLabel("0")
        self.v_num_text.setFixedWidth(QFontMetrics(self.v_num_text.font()).horizontalAdvance("+255"))
        v_layout.addWidget(self.v_num_text)
        # 使用智能填充色调
        self.smart_fillH_check = QCheckBox("使用智能算法推算中性色像素的色相")
        layout.addWidget(self.smart_fillH_check)
        self.smart_fillH_check.stateChanged.connect(self.Update)
        # 不开启智能填充色调/开启之后的回退方案：保持 / 设置色相
        self.exception_process_text = QLabel("出现中性色时：")
        self.exception_process_text2 = QLabel("当智能算法无效时，回退方案：")
        layout.addWidget(self.exception_process_text)
        layout.addWidget(self.exception_process_text2)
        backup_layout = QVBoxLayout()
        layout.addLayout(backup_layout)
        backup_layout.setContentsMargins(20, 0, 0, 0)
        self.exception_process_text2.setVisible(False)
        self.exception_process_group = QButtonGroup()
        self.exception_process_group.setExclusive(True)
        self.exception_process_keep = QRadioButton("不进行色相和明度的调整")
        self.exception_process_keep.setChecked(True)
        exception_process_set_layout = QHBoxLayout()
        exception_process_set_layout.setContentsMargins(0, 0, 0, 0)
        backup_layout.addLayout(exception_process_set_layout)
        self.exception_process_set = QRadioButton("将色相设定为该值：")
        self.exception_process_group.addButton(self.exception_process_set, 0)
        self.exception_process_group.addButton(self.exception_process_keep, 1)
        backup_layout.addWidget(self.exception_process_keep)
        exception_process_set_layout.addWidget(self.exception_process_set)
        self.exception_process_set.toggled.connect(self.Update)
        self.EXCEPT_SET_H_value = QDoubleSpinBox()
        self.EXCEPT_SET_H_value.setRange(0.0, 360.0)
        self.EXCEPT_SET_H_value.setValue(0.0)
        exception_process_set_layout.addWidget(self.EXCEPT_SET_H_value)
        exception_process_set_layout.addWidget(QLabel("°"))
        exception_process_set_layout.addStretch()
        self.EXCEPT_SET_H_value.valueChanged.connect(self.Update)

        # 智能算法参数
        self.smart_fillH_param_label = QLabel("智能算法参数")
        layout.addWidget(self.smart_fillH_param_label)
        self.smart_fillH_param_widget = QWidget()
        smart_fillH_param_layout = QVBoxLayout()
        self.smart_fillH_param_widget.setLayout(smart_fillH_param_layout)
        smart_fillH_param_layout.setContentsMargins(20, 0, 0, 0)
        layout.addWidget(self.smart_fillH_param_widget)
        # 步长
        step_layout = QHBoxLayout()
        step_layout.setContentsMargins(0, 0, 0, 0)
        smart_fillH_param_layout.addLayout(step_layout)
        step_layout.addWidget(QLabel("步长："))
        self.step = QSpinBox()
        self.step.setRange(1, INT32_MAX)
        self.step.setValue(1)
        self.step.valueChanged.connect(self.Update)
        step_layout.addWidget(self.step)
        step_layout.addStretch()
        # 4/8方向扫描
        ways_layout = QHBoxLayout()
        smart_fillH_param_layout.addLayout(ways_layout)
        ways_layout.addWidget(QLabel("扫描方向数："))
        self.scan_8_ways = QComboBox()
        ways_layout.addWidget(self.scan_8_ways)
        self.scan_8_ways.addItem("4")
        self.scan_8_ways.addItem("8")
        self.scan_8_ways.setCurrentIndex(1)
        self.scan_8_ways.currentIndexChanged.connect(self.Update)
        ways_layout.addStretch()
        # 采样次数
        sample_times_layout = QHBoxLayout()
        smart_fillH_param_layout.addLayout(sample_times_layout)
        sample_times_layout.addWidget(QLabel("采样次数："))
        self.sample_times = QSpinBox()
        sample_times_layout.addWidget(self.sample_times)
        self.sample_times.setRange(1, INT32_MAX)
        self.sample_times.setValue(8)
        self.sample_times.valueChanged.connect(self.Update)
        sample_times_layout.addStretch()
        # MAD去噪k值
        mad_k_layout = QHBoxLayout()
        smart_fillH_param_layout.addLayout(mad_k_layout)
        mad_k_layout.addWidget(QLabel("MAD去噪k值："))
        self.mad_k = QDoubleSpinBox()
        mad_k_layout.addWidget(self.mad_k)
        self.mad_k.setRange(0.0, 114514.0)
        self.mad_k.setValue(3.0)
        self.mad_k.setSingleStep(0.2)
        self.mad_k.valueChanged.connect(self.Update)
        mad_k_layout.addStretch()
        # 缓存回写
        self.pre_write_h_check = QCheckBox("缓存回写")
        self.pre_write_h_check.setChecked(True)
        smart_fillH_param_layout.addWidget(self.pre_write_h_check)
        self.pre_write_h_check.stateChanged.connect(self.Update)
        # 色彩修复
        color_fix_layout = QHBoxLayout()
        layout.addLayout(color_fix_layout)
        self.fix_switch = QCheckBox("色相修复")
        self.fix_switch.setToolTip("应与智能算法配合使用。将明度低于特定值的像素判定为中性色。")
        color_fix_layout.addWidget(self.fix_switch)
        color_fix_layout.addWidget(QLabel("明度判定阈值：S<"))
        self.S_thr = QDoubleSpinBox()
        color_fix_layout.addWidget(self.S_thr)
        color_fix_layout.addStretch()
        self.S_thr.setRange(0.0, 1.0)
        self.S_thr.setValue(0.03)
        self.S_thr.setSingleStep(0.01)
        self.fix_switch.stateChanged.connect(self.Update)
        self.S_thr.valueChanged.connect(self.Update)
        # 将透明像素视为中性色
        self.transparent_as_neutral_check = QCheckBox("将透明像素视为中性色")
        layout.addWidget(self.transparent_as_neutral_check)
        self.transparent_as_neutral_check.stateChanged.connect(self.Update)


        self.smart_fillH_param_label.setVisible(False)
        self.smart_fillH_param_widget.setVisible(False)


    
    def Update(self):
        self.h_num_text.setText(f"{signal_format_int(self.h_change.value())}°")
        self.s_num_text.setText(f"{signal_format_int(self.s_change.value())}%")
        self.v_num_text.setText(f"{signal_format_int(self.v_change.value())}")
        if self.smart_fillH_check.isChecked():
            self.exception_process_text.setVisible(False)
            self.exception_process_text2.setVisible(True)
            self.smart_fillH_param_label.setVisible(True)
            self.smart_fillH_param_widget.setVisible(True)
        else:
            self.exception_process_text.setVisible(True)
            self.exception_process_text2.setVisible(False)
            self.smart_fillH_param_label.setVisible(False)
            self.smart_fillH_param_widget.setVisible(False)
        self.img2arr_notify_update()

    """
// The parameter parsing structure passed in by ext.py. It can be used as the output of the processing result.
typedef struct {
    float H_change; // 色调偏移量。建议范围是[-0.5, 0.5]对应[-180°, +180°]。运算后处理为模360°的值。
    float S_change; // 饱和度偏移量。建议范围是[-1.0, 1.0]对应[-100%, +100%]。钳位至[0, 1]区间内。
    int16_t V_change; // 明亮度偏移量。建议范围是[-255, 255]。钳位至[-255, 255]区间内。
    enum{ // 对于中性色，H未定义。本枚举定义了如何设定中性色的H值。
        EXCEPT_SET_H = 0, // 将H设定为特定值
        EXCEPT_IGNORE_S_H, // 忽略上述对S和H的偏移。
    }exception_process;
    /*
    对于中性色的异常处理方案：
    是否使用基于物理模型的智能算法设定中性色像素的H值。
    true:使用该方案，并且exception_process作为该方案无效时的备选方案。
    false:则直接应用exception_process。
    */
    bool smart_fillH;
    float EXCEPT_SET_H_value; // 当exception_process为EXCEPT_SET_H时，设定H的特定值。建议范围是[0, 1]对应[0, 360°]。

    float *h_buffer; // 用于预存储H通道的值来加速智能填充的速度。若为NULL则不使用。仅当使用了smart_fillH时有效。需要分配(width * height * sizeof(float))大小的内存。初始值应为NaN。
    atomic_size_t *h_buffer_sync; //用于同步所有线程完成h_buffer的写入。其初始值应为线程数

    bool pre_write_h; //仅当使用了smart_fillH且启用缓存时有效。当某个线程完成了对色相的解算，是否将其结果提前写入到 h_buffer中。能够加速智能填充的速度，同时使结果更为平滑。
    unsigned int step; // 仅当使用了smart_fillH有效。指定步长。
    bool scan_8_ways; // 仅当使用了smart_fillH有效。是否启用8方向(左上、上、右上、左、右、左下、下、右下)扫描。若位false，将只扫描4个方向(上、下、左、右)
    size_t sample_times; // 每个扫描点至多采样多少个数据点。
    float mad_k; // MAD去噪时的k值
    float S_thr; //[色彩修复]调整中性色的明度判定阈值。若S_thr<0，则无效，严格判定中性色；否则，当颜色的S < S_thr时，就会判定为中性色，可以结合smart_fillH来完成色彩修复。
    bool ignore_npixels; // 仅当使用了smart_fillH有效。是否在预计算阶段将透明像素视为中性色并填充。若为false，则忽略透明通道。
}__attribute__((packed)) args_t;
    """
    class args_t(Structure):
        _fields_ = [
            ("H_change", c_float),
            ("S_change", c_float),
            ("V_change", c_uint16),
            ("exception_process", c_int),
            ("smart_fillH", c_bool),
            ("EXCEPT_SET_H_value", c_float),
            ("h_buffer", POINTER(c_float)),
            ("h_buffer_sync", POINTER(c_size_t)),
            ("pre_write_h", c_bool),
            ("step", c_uint),
            ("scan_8_ways", c_bool),
            ("sample_times", c_size_t),
            ("mad_k", c_float),
            ("S_thr", c_float),
            ("ignore_npixels", c_bool),
        ]
        _pack_ = 1
    def update(self, arr, threads):
        H_change = self.h_change.value() / 360.0
        S_change = self.s_change.value() / 100.0
        V_change = self.v_change.value()
        exception_process = self.exception_process_group.checkedId()
        smart_fillH = self.smart_fillH_check.isChecked() # 启用智能算法
        EXCEPT_SET_H_value = self.EXCEPT_SET_H_value.value() / 360.0
        pre_write_h = self.pre_write_h_check.isChecked()
        step = self.step.value()
        scan_8_ways = self.scan_8_ways.currentIndex()
        sample_times = self.sample_times.value()
        mad_k = self.mad_k.value()
        ignore_npixels = self.transparent_as_neutral_check.isChecked()
        # S_thr = self.S_thr.value()
        if self.fix_switch.isChecked():
            S_thr = self.S_thr.value()
        else:
            S_thr = -1.0
        if True:
            h_buffer = (c_float * (arr.shape[1] * arr.shape[0]))(nan)
            h_buffer_sync = (c_size_t * 1)()
            self.ext.atomic_init_size_t(h_buffer_sync, threads)
        else:
            h_buffer = None
            h_buffer_sync = None

        arg = self.args_t(H_change=H_change,
                          S_change=S_change,
                          V_change=V_change,
                          exception_process=exception_process,
                          smart_fillH=smart_fillH,
                          EXCEPT_SET_H_value=EXCEPT_SET_H_value,
                          h_buffer=h_buffer,
                          h_buffer_sync=h_buffer_sync,
                          pre_write_h=pre_write_h,
                          step=step,
                          scan_8_ways=scan_8_ways,
                          sample_times=sample_times,
                          mad_k=mad_k,
                          S_thr=S_thr,
                          ignore_npixels=ignore_npixels
        )

        return byref(arg), sizeof(arg)