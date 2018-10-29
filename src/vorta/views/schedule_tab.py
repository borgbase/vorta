import plistlib

from PyQt5 import uic, QtCore
from PyQt5.QtWidgets import QFileDialog, QListWidgetItem
from ..models import SourceDirModel
from ..utils import get_asset, get_sorted_wifis

uifile = get_asset('UI/scheduletab.ui')
ScheduleUI, ScheduleBase = uic.loadUiType(uifile)


class ScheduleTab(ScheduleBase, ScheduleUI):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)
        self.profile = self.window().profile

        self.init_wifi()

    def init_wifi(self):
        for wifi in get_sorted_wifis():
            item = QListWidgetItem()
            item.setText(wifi['ssid'])
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            if wifi['allowed']:
                item.setCheckState(QtCore.Qt.Checked)
            self.wifiListWidget.addItem(item)
