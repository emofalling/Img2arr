# 调试专用
import logging

logger = logging.getLogger("lib/DebugQObjects.py")

from PySide6.QtWidgets import QWidget

from PySide6.QtCore import QObject

class QDebugBase():
    def __init__(self, *args, **kwargs):
        self.__type_name = self.__class__.__name__
        super().__init__(*args, **kwargs)
        self.__obj_name = self.objectName()
        self.destroyed.connect(lambda: logger.debug(f"{self.__type_name} \"{self.__obj_name}\" was destroyed"))
    def setObjectName(self, name: str) -> None:
        self.__obj_name = name
        super().setObjectName(name)
    def deleteLater(self) -> None:
        logger.debug(f"{self.__type_name} \"{self.__obj_name}\"::deleteLater() was called")
        super().deleteLater()

class QDebugWidget(QDebugBase, QWidget):
    pass