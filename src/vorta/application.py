import os
import sys
import sip
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox

from vorta.borg.create import BorgCreateThread
from vorta.borg.version import BorgVersionThread
from vorta.config import TEMP_DIR
from vorta.i18n import init_translations, translate
from vorta.models import BackupProfileModel, SettingsModel
from vorta.qt_single_application import QtSingleApplication
from vorta.scheduler import VortaScheduler
from vorta.tray_menu import TrayMenu
from vorta.utils import borg_compat, parse_args
from vorta.views.main_window import MainWindow
from vorta.notifications import VortaNotifications

APP_ID = os.path.join(TEMP_DIR, "socket")


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
    backup_progress_event = QtCore.pyqtSignal(str)

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

        args = parse_args()
        if getattr(args, 'daemonize', False):
            pass
        elif SettingsModel.get(key='foreground').value:
            self.open_main_window_action()

        self.backup_started_event.connect(self.backup_started_event_response)
        self.backup_finished_event.connect(self.backup_finished_event_response)
        self.backup_cancelled_event.connect(self.backup_cancelled_event_response)
        self.message_received_event.connect(self.message_received_event_response)
        self.set_borg_details_action()
        self.installEventFilter(self)

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.ApplicationPaletteChange and type(source) == MainWindow:
            self.main_window.set_icons()
            self.main_window.repoTab.set_icons()
            self.main_window.archiveTab.set_icons()
            self.main_window.scheduleTab.set_icons()
        if event.type() == QtCore.QEvent.ApplicationPaletteChange and source == self.tray.contextMenu():
            self.tray.set_tray_icon()
        return False

    def create_backup_action(self, profile_id=None):
        if not profile_id:
            profile_id = self.main_window.current_profile.id

        profile = BackupProfileModel.get(id=profile_id)
        msg = BorgCreateThread.prepare(profile)
        if msg['ok']:
            thread = BorgCreateThread(msg['cmd'], msg, parent=self)
            thread.start()
        else:
            notifier = VortaNotifications.pick()
            notifier.deliver(self.tr('Vorta Backup'), translate('messages', msg['message']), level='error')
            self.backup_progress_event.emit(translate('messages', msg['message']))

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
        self.tray.set_tray_icon(active=True)

    def backup_finished_event_response(self):
        self.tray.set_tray_icon()

    def backup_cancelled_event_response(self):
        self.tray.set_tray_icon()

    def message_received_event_response(self, message):
        if message == "open main window":
            self.open_main_window_action()

    def set_borg_details_action(self):
        params = BorgVersionThread.prepare()
        if not params['ok']:
            self._alert_missing_borg()
            return
        thread = BorgVersionThread(params['cmd'], params, parent=self)
        thread.result.connect(self.set_borg_details_result)
        thread.start()

    def set_borg_details_result(self, result):
        """
        Receive result from BorgVersionThread. If MainWindow is open, set the version in misc tab.
        If no valid version was found, display an error.
        """
        if 'version' in result['data']:
            borg_compat.set_version(result['data']['version'], result['data']['path'])
            if self._main_window_exists():
                self.main_window.miscTab.set_borg_details(borg_compat.version, borg_compat.path)
                self.main_window.repoTab.toggle_available_compression()
        else:
            self._alert_missing_borg()

    def _alert_missing_borg(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(self.tr("No Borg Binary Found"))
        msg.setInformativeText(self.tr("Vorta was unable to locate a usable Borg Backup binary."))
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
