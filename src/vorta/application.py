import os
import sys

import qdarkstyle
from PyQt5 import QtCore

import sip
from vorta.borg.version import BorgVersionThread
from vorta.config import STATE_DIR

from .borg.create import BorgCreateThread
from .i18n import init_translations, translate
from .models import BackupProfileModel, SettingsModel
from .qt_single_application import QtSingleApplication
from .scheduler import VortaScheduler
from .tray_menu import TrayMenu
from .utils import borg_compat, parse_args, set_tray_icon
from .views.main_window import MainWindow

APP_ID = os.path.join(STATE_DIR, "socket")


class VortaApp(QtSingleApplication):
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

        super().__init__(APP_ID, args_raw)
        if self.isRunning() and single_app:
            self.sendMessage("open main window")
            print('An instance of Vorta is already running. Opening main window.')
            sys.exit()

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
        self.message_received_event.connect(self.message_received_event_response)

        self.set_borg_details_action()

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

    def _main_window_exists(self):
        return hasattr(self, 'main_window') and not sip.isdeleted(self.main_window)

    def toggle_main_window_visibility(self):
        if self._main_window_exists():
            self.main_window.close()
        else:
            self.open_main_window_action()

    def backup_started_event_response(self):
        set_tray_icon(self.tray, active=True)

    def backup_finished_event_response(self):
        set_tray_icon(self.tray)

    def backup_cancelled_event_response(self):
        set_tray_icon(self.tray)

    def message_received_event_response(self, message):
        if message == "open main window":
            self.open_main_window_action()

    def set_borg_details_action(self):
        params = BorgVersionThread.prepare()
        if not params['ok']:
            return
        thread = BorgVersionThread(params['cmd'], params, parent=self)
        thread.result.connect(self.set_borg_details_result)
        thread.start()

    def set_borg_details_result(self, result):
        borg_compat.set_version(result['data']['version'], result['data']['path'])
        if self._main_window_exists():
            self.main_window.miscTab.set_borg_details(borg_compat.version, borg_compat.path)
            self.main_window.repoTab.toggle_available_compression()
