from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from .tray_menu import TrayMenu
from .scheduler import VortaScheduler
from .models import BackupProfileModel
from .borg.create import BorgCreateThread
from .views.main_window import MainWindow
from .utils import get_asset


class VortaApp(QApplication):
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

        self.backup_started_event.connect(self.backup_started_event_response)
        self.backup_finished_event.connect(self.backup_finished_event_response)

    def create_backup_action(self, profile_id=None):
        if not profile_id:
            profile_id = self.main_window.current_profile.id

        profile = BackupProfileModel.get(id=profile_id)
        msg = BorgCreateThread.prepare(profile)
        if msg['ok']:
            thread = BorgCreateThread(msg['cmd'], msg, parent=self)
            thread.start()
        else:
            self.backup_log_event.emit(msg['message'])

    def open_main_window_action(self):
        self.main_window.show()
        self.main_window.raise_()

    def backup_started_event_response(self):
        icon = QIcon(get_asset('icons/hdd-o-active.png'))
        self.tray.setIcon(icon)

    def backup_finished_event_response(self):
        icon = QIcon(get_asset('icons/hdd-o.png'))
        self.tray.setIcon(icon)
