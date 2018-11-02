import sys
import os
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication

from .tray_menu import TrayMenu
from .scheduler import VortaScheduler
from .models import BackupProfileModel, SnapshotModel, BackupProfileMixin
from .borg_runner import BorgThread
from .views.main_window import MainWindow


class VortaApp(QApplication, BackupProfileMixin):
    """
    All windows and QWidgets are children of this app.

    When running Borg-commands, the class `BorgThread` will emit events
    via the `VortaApp` class to which other windows will subscribe to.
    """

    backup_started_event = QtCore.pyqtSignal()
    backup_finished_event = QtCore.pyqtSignal(dict)
    backup_cancelled_event = QtCore.pyqtSignal()
    backup_log_event = QtCore.pyqtSignal(str)

    def __init__(self, args):
        super().__init__(args)
        self.setQuitOnLastWindowClosed(False)
        self.scheduler = VortaScheduler(self)

        # Prepare tray and main window
        self.tray = TrayMenu(self)
        self.main_window = MainWindow(self)
        self.main_window.show()

    def create_backup_action(self):
        msg = BorgThread.prepare_create_cmd()
        if msg['ok']:
            self.thread = BorgThread(msg['cmd'], msg['params'], parent=self)
            self.thread.start()
        else:
            self.backup_log_event.emit(msg['message'])

    def open_main_window_action(self):
        self.main_window.show()
        self.main_window.raise_()


