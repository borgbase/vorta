import sys
from PyQt5.QtWidgets import QApplication

from .tray_menu import TrayMenu
from .scheduler import VortaScheduler
from .models import BackupProfileModel
from .borg_runner import BorgThread
from .views.main_window import MainWindow


class VortaApp(QApplication):
    def __init__(self, args):
        super().__init__(args)
        self.thread = None
        self.setQuitOnLastWindowClosed(False)
        self.scheduler = VortaScheduler(self)
        self.profile = BackupProfileModel.get(id=1)

        # Prepare tray and connect events.
        self.tray = TrayMenu(self)
        self.tray.start_backup.connect(self.on_create_backup)
        self.tray.open_main_window.connect(self.on_open_main_window)

        # Prepare main window
        self.main_window = MainWindow(self)

        if not getattr(sys, 'frozen', False):
            self.main_window.show()

    def on_create_backup(self):
        if self.thread and self.app.isRunning():
            self.app.process.kill()
            self.app.terminate()
        else:
            msg = BorgThread.prepare_runner()
            if msg['ok']:
                self.thread = BorgThread(msg['cmd'], msg['params'])
                self.thread.start()
            # TODO: error dialog

    def on_open_main_window(self):
        self.main_window.show()
