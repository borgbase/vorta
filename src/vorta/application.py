import logging
import os
import sys
import time

from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox

from vorta.borg.borg_thread import BorgThread
from vorta.borg.create import BorgCreateThread
from vorta.borg.version import BorgVersionThread
from vorta.borg.break_lock import BorgBreakThread
from vorta.config import TEMP_DIR
from vorta.i18n import init_translations, translate
from vorta.models import BackupProfileModel, SettingsModel, cleanup_db
from vorta.qt_single_application import QtSingleApplication
from vorta.scheduler import VortaScheduler
from vorta.tray_menu import TrayMenu
from vorta.utils import borg_compat, parse_args
from vorta.views.main_window import MainWindow
from vorta.notifications import VortaNotifications

logger = logging.getLogger(__name__)

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
    backup_log_event = QtCore.pyqtSignal(str, dict)
    backup_progress_event = QtCore.pyqtSignal(str)

    def __init__(self, args_raw, single_app=False):

        super().__init__(APP_ID, args_raw)
        args = parse_args()
        if self.isRunning():
            if single_app:
                self.sendMessage("open main window")
                print('An instance of Vorta is already running. Opening main window.')
                sys.exit()
            elif args.profile:
                self.sendMessage(f"create {args.profile}")
                print('Creating backup using existing Vorta instance.')
                sys.exit()
        elif args.profile:
            sys.exit('Vorta must already be running for --create to work')

        init_translations(self)

        self.setQuitOnLastWindowClosed(False)
        self.scheduler = VortaScheduler(self)
        self.setApplicationName("Vorta")

        # Prepare tray and main window
        self.tray = TrayMenu(self)
        self.main_window = MainWindow(self)

        if getattr(args, 'daemonize', False):
            pass
        elif SettingsModel.get(key='foreground').value:
            self.open_main_window_action()

        self.backup_started_event.connect(self.backup_started_event_response)
        self.backup_finished_event.connect(self.backup_finished_event_response)
        self.backup_cancelled_event.connect(self.backup_cancelled_event_response)
        self.message_received_event.connect(self.message_received_event_response)
        self.backup_log_event.connect(self.react_to_log)
        self.aboutToQuit.connect(self.quit_app_action)
        self.set_borg_details_action()
        self.installEventFilter(self)

    def create_backups_cmdline(self, profile_name):
        profile = BackupProfileModel.get_or_none(name=profile_name)
        if profile is not None:
            if profile.repo is None:
                logger.warning(f"Add a repository to {profile_name}")
            # Wait a bit in case something is running
            while BorgThread.is_running():
                time.sleep(0.1)
            self.create_backup_action(profile_id=profile.id)
        else:
            logger.warning(f"Invalid profile name {profile_name}")

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.ApplicationPaletteChange and isinstance(source, MainWindow):
            self.main_window.set_icons()
            self.main_window.repoTab.set_icons()
            self.main_window.archiveTab.set_icons()
            self.main_window.scheduleTab.set_icons()
        if event.type() == QtCore.QEvent.ApplicationPaletteChange and source == self.tray.contextMenu():
            self.tray.set_tray_icon()
        return False

    def quit_app_action(self):
        del self.main_window
        self.scheduler.shutdown()
        self.backup_cancelled_event.emit()
        cleanup_db()

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
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def toggle_main_window_visibility(self):
        if self.main_window.isVisible():
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
        elif message.startswith("create"):
            message = message[7:]  # Remove create
            if BorgThread.is_running():
                logger.warning("Cannot run while backups are already running")
            else:
                self.create_backups_cmdline(message)

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
        Receive result from BorgVersionThread.
        If no valid version was found, display an error.
        """
        if 'version' in result['data']:
            borg_compat.set_version(result['data']['version'], result['data']['path'])
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
        msg.exec()

    def react_to_log(self, mgs, context):
        """
        Trigger Vorta actions based on Borg logs. E.g. repo lock.
        """
        msgid = context.get('msgid')
        if msgid == 'LockTimeout':
            profile = BackupProfileModel.get(name=context['profile_name'])
            repo_url = context.get('repo_url')
            msg = QMessageBox()
            msg.setWindowTitle(self.tr("Repository In Use"))
            msg.setIcon(QMessageBox.Critical)
            abortButton = msg.addButton(self.tr("Abort"), QMessageBox.RejectRole)
            msg.addButton(self.tr("Continue"), QMessageBox.AcceptRole)
            msg.setDefaultButton(abortButton)
            msg.setText(self.tr(f"The repository at {repo_url} might be in use elsewhere."))
            msg.setInformativeText(self.tr("Only break the lock if you are certain no other Borg process "
                                   "on any machine is accessing the repository. Abort or break the lock?"))
            msg.accepted.connect(lambda: self.break_lock(profile))
            self._msg = msg
            msg.show()
        elif msgid == 'LockFailed':
            repo_url = context.get('repo_url')
            msg = QMessageBox()
            msg.setText(
                self.tr(
                    f"You do not have permission to access the repository at {repo_url}. Gain access and try again."))  # noqa: E501
            msg.setWindowTitle(self.tr("No Repository Permissions"))
            self._msg = msg
            msg.show()

    def break_lock(self, profile):
        params = BorgBreakThread.prepare(profile)
        if not params['ok']:
            self.set_progress(params['message'])
            return
        thread = BorgBreakThread(params['cmd'], params, parent=self)
        thread.start()
