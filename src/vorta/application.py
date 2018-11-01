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
    backup_done = QtCore.pyqtSignal()
    backup_log = QtCore.pyqtSignal(str)

    def __init__(self, args):
        super().__init__(args)
        self.setQuitOnLastWindowClosed(False)
        self.scheduler = VortaScheduler(self)

        # Prepare tray and connect events.
        self.tray = TrayMenu(self)
        self.tray.start_backup.connect(self.create_backup)
        self.tray.open_main_window.connect(self.on_open_main_window)

        # Prepare main window
        self.main_window = MainWindow(self)

        if not getattr(sys, 'frozen', False):
            self.main_window.show()

    def cancel_backup(self):
        """Can't cancel background backups."""
        if self.thread and self.thread.isRunning():
            self.thread.mutex.unlock()
            self.thread.process.kill()
            self.thread.terminate()

    def create_backup(self):
        msg = BorgThread.prepare_runner()
        if msg['ok']:
            self.thread = BorgThread(msg['cmd'], msg['params'], parent=self)
            self.thread.updated.connect(self.backup_log.emit)
            self.thread.result.connect(self.create_backup_result)
            self.thread.start()
        return msg

    def on_open_main_window(self):
        self.main_window.show()
        self.main_window.raise_()

    def create_backup_result(self, result):
        self.backup_done.emit()

