import os
import sys
import fcntl
import sip

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
import qdarkstyle

from .i18n import init_translations, translate
from .tray_menu import TrayMenu
from .scheduler import VortaScheduler
from .models import BackupProfileModel, SettingsModel
from .borg.create import BorgCreateThread
from .views.main_window import MainWindow
from .utils import parse_args, set_tray_icon
from vorta.config import SETTINGS_DIR


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

    def __init__(self, args_raw, single_app=False):

        # Ensure only one app instance is running.
        # From https://stackoverflow.com/questions/220525/
        #              ensure-a-single-instance-of-an-application-in-linux#221159
        if single_app:
            pid_file = os.path.join(SETTINGS_DIR, 'vorta.pid')
            lockfile = open(pid_file, 'w+')
            try:
                fcntl.lockf(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.lockfile = lockfile
            except OSError:
                print('An instance of Vorta is already running.')
                sys.exit(1)

        super().__init__(args_raw)
        init_translations(self)

        self.setQuitOnLastWindowClosed(False)
        self.scheduler = VortaScheduler(self)

        # Prepare system tray icon
        self.tray = TrayMenu(self)

        # Apply dark stylesheet
        if SettingsModel.get(key='use_dark_theme').value:
            self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

        args = parse_args()
        if hasattr(args, 'foreground') and args.foreground:
            self.open_main_window_action()

        self.backup_started_event.connect(self.backup_started_event_response)
        self.backup_finished_event.connect(self.backup_finished_event_response)
        self.backup_cancelled_event.connect(self.backup_cancelled_event_response)

    def create_backup_action(self, profile_id=None):
        if not profile_id:
            profile_id = self.main_window.current_profile.id

        profile = BackupProfileModel.get(id=profile_id)
        msg = BorgCreateThread.prepare(profile)
        if msg['ok']:
            thread = BorgCreateThread(msg['cmd'], msg, parent=self)
            thread.start()
        else:
            self.backup_log_event.emit(translate('messages', msg['message']))

    def open_main_window_action(self):
        self.main_window = MainWindow(self)
        self.main_window.show()
        self.main_window.raise_()

    def toggle_main_window_visibility(self):
        main_window_open = hasattr(self, 'main_window') and not sip.isdeleted(self.main_window)
        if main_window_open:
            self.main_window.close()
        else:
            self.open_main_window_action()

    def backup_started_event_response(self):
        set_tray_icon(self.tray, active=True)

    def backup_finished_event_response(self):
        set_tray_icon(self.tray)

    def backup_cancelled_event_response(self):
        set_tray_icon(self.tray)
