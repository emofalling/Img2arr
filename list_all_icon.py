import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QScrollArea, QWidget, 
                               QLabel, QGridLayout, QStyle, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon


class IconBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qt 内置图标浏览器 - 完整版")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件和滚动区域
        scroll_area = QScrollArea()
        central_widget = QWidget()
        self.setCentralWidget(scroll_area)
        scroll_area.setWidget(central_widget)
        scroll_area.setWidgetResizable(True)
        
        # 创建网格布局
        layout = QGridLayout(central_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setHorizontalSpacing(15)
        layout.setVerticalSpacing(8)
        
        # 获取所有 StandardPixmap 枚举值
        standard_pixmaps = self.get_standard_pixmaps()
        
        # 添加标题行
        titles = ["图标", "枚举名称", "数值", "详细描述", "使用场景"]
        for col, title in enumerate(titles):
            label = QLabel(f"<b>{title}</b>")
            label.setStyleSheet("background-color: #e0e0e0; padding: 8px; border: 1px solid #ccc;")
            layout.addWidget(label, 0, col)
        
        # 显示所有图标
        for row, (enum_value, name, value) in enumerate(standard_pixmaps, 1):
            # 显示图标
            icon = self.style().standardIcon(enum_value)
            icon_label = QLabel()
            icon_label.setFixedSize(48, 48)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet("border: 1px solid #ccc; background-color: white; padding: 5px;")
            
            if not icon.isNull():
                pixmap = icon.pixmap(32, 32)
                icon_label.setPixmap(pixmap)
            else:
                icon_label.setText("N/A")
                icon_label.setStyleSheet("border: 1px solid #ccc; background-color: #f0f0f0; padding: 5px; color: #666;")
            
            layout.addWidget(icon_label, row, 0)
            
            # 显示枚举名称
            name_label = QLabel(name)
            name_label.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; padding: 5px;")
            layout.addWidget(name_label, row, 1)
            
            # 显示数值
            value_label = QLabel(str(value))
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_label.setStyleSheet("padding: 5px;")
            layout.addWidget(value_label, row, 2)
            
            # 显示详细描述
            description, usage = self.get_pixmap_description(enum_value)
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("padding: 5px;")
            layout.addWidget(desc_label, row, 3)
            
            # 显示使用场景
            usage_label = QLabel(usage)
            usage_label.setWordWrap(True)
            usage_label.setStyleSheet("padding: 5px; color: #666;")
            layout.addWidget(usage_label, row, 4)
    
    def get_standard_pixmaps(self):
        """获取所有 StandardPixmap 枚举值和名称"""
        pixmaps = []
        # 获取 QStyle.StandardPixmap 的所有属性
        for name in dir(QStyle.StandardPixmap):
            if not name.startswith('_') and name.startswith('SP_'):
                value = getattr(QStyle.StandardPixmap, name)
                pixmaps.append((value, name, int(value)))  # 确保值是整数
        
        # 按数值排序
        pixmaps.sort(key=lambda x: x[2])
        return pixmaps
    
    def get_pixmap_description(self, enum_value):
        """根据 StandardPixmap 枚举值获取描述信息"""
        # 完整的描述映射
        descriptions = {
            # 对话框按钮图标
            QStyle.StandardPixmap.SP_DialogOkButton: ("确定按钮图标", "对话框中的确定/确认按钮"),
            QStyle.StandardPixmap.SP_DialogCancelButton: ("取消按钮图标", "对话框中的取消/关闭按钮"),
            QStyle.StandardPixmap.SP_DialogOpenButton: ("打开按钮图标", "文件打开对话框中的打开按钮"),
            QStyle.StandardPixmap.SP_DialogSaveButton: ("保存按钮图标", "文件保存对话框中的保存按钮"),
            QStyle.StandardPixmap.SP_DialogCloseButton: ("关闭按钮图标", "对话框中的关闭按钮"),
            QStyle.StandardPixmap.SP_DialogApplyButton: ("应用按钮图标", "对话框中的应用按钮"),
            QStyle.StandardPixmap.SP_DialogResetButton: ("重置按钮图标", "对话框中的重置按钮"),
            QStyle.StandardPixmap.SP_DialogDiscardButton: ("丢弃按钮图标", "对话框中的丢弃/放弃按钮"),
            QStyle.StandardPixmap.SP_DialogYesButton: ("是按钮图标", "对话框中的是按钮"),
            QStyle.StandardPixmap.SP_DialogNoButton: ("否按钮图标", "对话框中的否按钮"),
            QStyle.StandardPixmap.SP_DialogHelpButton: ("帮助按钮图标", "对话框中的帮助按钮"),
            
            # 消息框图标
            QStyle.StandardPixmap.SP_MessageBoxInformation: ("信息图标", "消息框中的信息提示图标"),
            QStyle.StandardPixmap.SP_MessageBoxWarning: ("警告图标", "消息框中的警告提示图标"),
            QStyle.StandardPixmap.SP_MessageBoxCritical: ("错误图标", "消息框中的严重错误提示图标"),
            QStyle.StandardPixmap.SP_MessageBoxQuestion: ("问号图标", "消息框中的问题提示图标"),
            
            # 文件系统图标
            QStyle.StandardPixmap.SP_DesktopIcon: ("桌面图标", "代表桌面或主屏幕"),
            QStyle.StandardPixmap.SP_ComputerIcon: ("计算机图标", "代表计算机或我的电脑"),
            QStyle.StandardPixmap.SP_DriveFDIcon: ("软驱图标", "代表软盘驱动器"),
            QStyle.StandardPixmap.SP_DriveHDIcon: ("硬盘图标", "代表硬盘驱动器"),
            QStyle.StandardPixmap.SP_DriveCDIcon: ("光驱图标", "代表CD/DVD驱动器"),
            QStyle.StandardPixmap.SP_DriveDVDIcon: ("DVD图标", "代表DVD驱动器"),
            QStyle.StandardPixmap.SP_DriveNetIcon: ("网络驱动器图标", "代表网络驱动器"),
            QStyle.StandardPixmap.SP_FileIcon: ("文件图标", "通用文件图标"),
            QStyle.StandardPixmap.SP_DirIcon: ("文件夹图标", "关闭的文件夹图标"),
            QStyle.StandardPixmap.SP_DirOpenIcon: ("打开文件夹图标", "打开的文件夹图标"),
            QStyle.StandardPixmap.SP_DirLinkIcon: ("文件夹链接图标", "文件夹快捷方式图标"),
            QStyle.StandardPixmap.SP_FileLinkIcon: ("文件链接图标", "文件快捷方式图标"),
            
            # 箭头图标
            QStyle.StandardPixmap.SP_ArrowUp: ("向上箭头", "向上方向指示或排序升序"),
            QStyle.StandardPixmap.SP_ArrowDown: ("向下箭头", "向下方向指示或排序降序"),
            QStyle.StandardPixmap.SP_ArrowLeft: ("向左箭头", "向左方向指示或后退"),
            QStyle.StandardPixmap.SP_ArrowRight: ("向右箭头", "向右方向指示或前进"),
            QStyle.StandardPixmap.SP_ArrowBack: ("后退箭头", "导航后退按钮"),
            QStyle.StandardPixmap.SP_ArrowForward: ("前进箭头", "导航前进按钮"),
            
            # 媒体控制图标
            QStyle.StandardPixmap.SP_MediaPlay: ("播放图标", "媒体播放按钮"),
            QStyle.StandardPixmap.SP_MediaPause: ("暂停图标", "媒体暂停按钮"),
            QStyle.StandardPixmap.SP_MediaStop: ("停止图标", "媒体停止按钮"),
            QStyle.StandardPixmap.SP_MediaSeekForward: ("快进图标", "媒体快进按钮"),
            QStyle.StandardPixmap.SP_MediaSeekBackward: ("快退图标", "媒体快退按钮"),
            QStyle.StandardPixmap.SP_MediaSkipForward: ("下一曲图标", "媒体下一曲按钮"),
            QStyle.StandardPixmap.SP_MediaSkipBackward: ("上一曲图标", "媒体上一曲按钮"),
            QStyle.StandardPixmap.SP_MediaVolume: ("音量图标", "音量控制"),
            QStyle.StandardPixmap.SP_MediaVolumeMuted: ("静音图标", "音量静音"),
            
            # 工具栏图标
            QStyle.StandardPixmap.SP_TitleBarMenuButton: ("标题栏菜单按钮", "窗口标题栏的菜单按钮"),
            QStyle.StandardPixmap.SP_TitleBarMinButton: ("最小化按钮", "窗口标题栏的最小化按钮"),
            QStyle.StandardPixmap.SP_TitleBarMaxButton: ("最大化按钮", "窗口标题栏的最大化按钮"),
            QStyle.StandardPixmap.SP_TitleBarCloseButton: ("关闭按钮", "窗口标题栏的关闭按钮"),
            QStyle.StandardPixmap.SP_TitleBarNormalButton: ("还原按钮", "窗口标题栏的还原按钮"),
            QStyle.StandardPixmap.SP_TitleBarShadeButton: ("收起按钮", "窗口标题栏的收起按钮"),
            QStyle.StandardPixmap.SP_TitleBarUnshadeButton: ("展开按钮", "窗口标题栏的展开按钮"),
            
            # 其他常用图标
            QStyle.StandardPixmap.SP_LineEditClearButton: ("清除按钮", "文本输入框的清除内容按钮"),
            QStyle.StandardPixmap.SP_DialogYesToAllButton: ("全部是按钮", "对话框中的全部是按钮"),
            QStyle.StandardPixmap.SP_DialogNoToAllButton: ("全部否按钮", "对话框中的全部否按钮"),
            QStyle.StandardPixmap.SP_DialogSaveAllButton: ("全部保存按钮", "对话框中的全部保存按钮"),
            QStyle.StandardPixmap.SP_DialogAbortButton: ("中止按钮", "对话框中的中止按钮"),
            QStyle.StandardPixmap.SP_DialogRetryButton: ("重试按钮", "对话框中的重试按钮"),
            QStyle.StandardPixmap.SP_DialogIgnoreButton: ("忽略按钮", "对话框中的忽略按钮"),
            
            # 命令图标
            QStyle.StandardPixmap.SP_CommandLink: ("命令链接", "命令链接按钮的箭头图标"),
        }
        
        # 如果找不到对应的描述，返回默认值
        if enum_value in descriptions:
            return descriptions[enum_value]
        else:
            # 尝试通过枚举值名称猜测描述
            name = ""
            for key, value in QStyle.StandardPixmap.__dict__.items():
                if value == enum_value and key.startswith('SP_'):
                    name = key
                    break
            
            if "Dir" in name:
                return ("文件夹相关图标", "文件系统或目录操作")
            elif "File" in name:
                return ("文件相关图标", "文件操作或文件类型")
            elif "Arrow" in name:
                return ("方向箭头图标", "导航或方向指示")
            elif "Media" in name:
                return ("媒体控制图标", "音频视频播放控制")
            elif "Dialog" in name:
                return ("对话框按钮图标", "对话框中的操作按钮")
            elif "MessageBox" in name:
                return ("消息框图标", "信息提示和警告")
            else:
                return ("标准图标", "Qt内置标准图标")
    def showEvent(self, event):
        """窗口显示时调整列宽"""
        super().showEvent(event)
        # 给一些时间让布局完成，然后调整列宽
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self.adjustColumnWidths)
    
    def adjustColumnWidths(self):
        """调整列宽以获得更好的显示效果"""
        # 这里可以添加自动调整列宽的代码
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IconBrowser()
    window.show()
    sys.exit(app.exec())