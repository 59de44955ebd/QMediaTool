"""
QMediaTool - MyTreeWidget class
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTreeWidget


class MyTreeWidget (QTreeWidget):

    def keyPressEvent (self, event):
        if event.key() == Qt.Key_Space or event.key() == Qt.Key_Return:
            if self.currentItem():
                self.itemDoubleClicked.emit(self.currentItem(), 0)
        else:
            super().keyPressEvent(event)
