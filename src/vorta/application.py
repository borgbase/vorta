import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PyQt6 import QtCore
from PyQt6.QtWidgets import QMessageBox

from vorta import config
from vorta.borg.break_lock import BorgBreakJob
from vorta.borg.create import BorgCreateJob
from vorta.borg.jobs_manager import JobsManager
from vorta.borg.version import BorgVersionJob
from vorta.i18n import init_translations, translate
from vorta.notifications import VortaNotifications
from vorta.profile_export import ProfileExport
from vorta.qt_single_application import QtSingleApplication
from vorta.scheduler import VortaScheduler
from vorta.store.connection import cleanup_db
from vorta.store.models import BackupProfileModel, SettingsModel
from vorta.tray_menu import TrayMenu
from vorta.utils import borg_compat, parse_args
from vorta.views.main_window import MainWindow

logger = logging.getLogger(__name__)

APP_ID = config.TEMP_DIR / "socket"


class VortaApp(QtSingleApplication):
    """
    All windows and QWidgets are children of this app.

    When running Borg-commands, the class `BorgJob` will emit events
    via the `VortaApp` class to which other windows will subscribe to.
    """

    backup_started_event = QtCore.pyqtSignal()
    backup_finished_event = QtCore.pyqtSignal(dict)
    backup_cancelled_event = QtCore.pyqtSignal()
    backup_log_event = QtCore.pyqtSignal(str, dict)
    backup_progress_event = QtCore.pyqtSignal(str)
    check_failed_event = QtCore.pyqtSignal(dict)

    def __init__(self, args_raw, single_app=False):
        super().__init__(str(APP_ID), args_raw)
        args = parse_args()
        if self.isRunning():
            if single_app:
                self.sendMessage("open main window")
                logger.info('An instance of Vorta is already running. Opening main window.')
                sys.exit()
            elif args.profile:
                self.sendMessage(f"create {args.profile}")
                logger.info('Creating backup using existing Vorta instance.')
                sys.exit()
        elif args.profile:
            sys.exit('Vorta must already be running for --create to work')

        init_translations(self)

        self.setQuitOnLastWindowClosed(False)
        self.jobs_manager = JobsManager()
        self.scheduler = VortaScheduler()

        self.setApplicationName("Vorta")

        # Import profile from ~/.vorta-init.json or add empty "Default" profile.
        self.bootstrap_profile()

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
        self.check_failed_event.connect(self.check_failed_response)
        self.backup_log_event.connect(self.react_to_log)
        self.aboutToQuit.connect(self.quit_app_action)
        self.set_borg_details_action()
        if sys.platform == 'darwin':
            self.check_darwin_permissions()

    def create_backups_cmdline(self, profile_name):
        profile = BackupProfileModel.get_or_none(name=profile_name)
        if profile is not None:
            if profile.repo is None:
                logger.warning(f"Add a repository to {profile_name}")
            self.create_backup_action(profile_id=profile.id)
        else:
            logger.warning(f"Invalid profile name {profile_name}")

    def quit_app_action(self):
        self.backup_cancelled_event.emit()
        del self.main_window
        self.tray.deleteLater()
        del self.tray
        cleanup_db()

    def create_backup_action(self, profile_id=None):
        if not profile_id:
            profile_id = self.main_window.current_profile.id

        profile = BackupProfileModel.get(id=profile_id)
        msg = BorgCreateJob.prepare(profile)
        if msg['ok']:
            job = BorgCreateJob(msg['cmd'], msg, profile.repo.id)
            self.jobs_manager.add_job(job)
        else:
            notifier = VortaNotifications.pick()
            notifier.deliver(
                self.tr('Vorta Backup'),
                translate('messages', msg['message']),
                level='error',
            )
            self.backup_progress_event.emit(f"[{profile.name}] {translate('messages', msg['message'])}")
            return None

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
        if not self.jobs_manager.is_worker_running():
            self.tray.set_tray_icon()

    def backup_cancelled_event_response(self):
        self.jobs_manager.cancel_all_jobs()
        self.tray.set_tray_icon()

    def message_received_event_response(self, message):
        if message == "open main window":
            self.open_main_window_action()
        elif message.startswith("create"):
            message = message[7:]  # Remove create
            if self.jobs_manager.is_worker_running():
                logger.warning("Cannot run while backups are already running")
            else:
                self.create_backups_cmdline(message)

    # No need to add this function to JobsManager because it doesn't require to lock a repo.
    def set_borg_details_action(self):
        params = BorgVersionJob.prepare()
        if not params['ok']:
            self._alert_missing_borg()
            return
        job = BorgVersionJob(params['cmd'], params)
        job.result.connect(self.set_borg_details_result)
        self.jobs_manager.add_job(job)

    def set_borg_details_result(self, result):
        """
        Receive result from BorgVersionJob.
        If no valid version was found, display an error.
        """
        if 'version' in result['data']:
            borg_compat.set_version(result['data']['version'], result['data']['path'])
            self.main_window.aboutTab.set_borg_details(borg_compat.version, borg_compat.path)
            self.main_window.repoTab.toggle_available_compression()
            self.main_window.archiveTab.toggle_compact_button_visibility()
            self.scheduler.reload_all_timers()  # Start timer after Borg version is set.
        else:
            self._alert_missing_borg()

    def _alert_missing_borg(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText(self.tr("No Borg Binary Found"))
        msg.setInformativeText(self.tr("Vorta was unable to locate a usable Borg Backup binary."))
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def check_darwin_permissions(self):
        """
        macOS restricts access to certain folders by default. For some folders, the user
        will get a prompt (e.g. Documents, Downloads), while others will cause file access
        errors.

        This function tries reading a file that is known to be restricted and warn the user about
        incomplete backups.
        """

        if not SettingsModel.get(key="check_full_disk_access").value:
            return

        test_path = Path('~/Library/Cookies').expanduser()
        if test_path.exists() and not os.access(test_path, os.R_OK):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse)
            msg.setText(self.tr("Vorta needs Full Disk Access for complete Backups"))
            msg.setInformativeText(
                self.tr(
                    "Without this, some files will not be accessible and you may end up with an incomplete "
                    "backup. Please set <b>Full Disk Access</b> permission for Vorta in "
                    "<a href='x-apple.systempreferences:com.apple.preference.security?Privacy'>"
                    "System Preferences > Security & Privacy</a>."
                )
            )
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
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
            msg.setIcon(QMessageBox.Icon.Critical)
            abortButton = msg.addButton(self.tr("Abort"), QMessageBox.ButtonRole.RejectRole)
            msg.addButton(self.tr("Continue"), QMessageBox.ButtonRole.AcceptRole)
            msg.setDefaultButton(abortButton)
            msg.setText(self.tr(f"The repository at {repo_url} might be in use elsewhere."))
            msg.setInformativeText(
                self.tr(
                    "Only break the lock if you are certain no other Borg process "
                    "on any machine is accessing the repository. Abort or break the lock?"
                )
            )
            msg.accepted.connect(lambda: self.break_lock(profile))
            self._msg = msg
            msg.show()
        elif msgid == 'LockFailed':
            repo_url = context.get('repo_url')
            msg = QMessageBox()
            msg.setText(
                self.tr(
                    f"You do not have permission to access the repository at {repo_url}. Gain access and try again."
                )
            )  # noqa: E501
            msg.setWindowTitle(self.tr("No Repository Permissions"))
            self._msg = msg
            msg.show()

    def break_lock(self, profile):
        params = BorgBreakJob.prepare(profile)
        if not params['ok']:
            self.backup_progress_event.emit(f"[{profile.name}] {params['message']}")
            return
        job = BorgBreakJob(params['cmd'], params)
        self.jobs_manager.add_job(job)

    def bootstrap_profile(self, bootstrap_file=None):
        # Necessary to dynamically load the variable from config during runtime
        # Check out pull request for #1682 for context
        bootstrap_file = bootstrap_file or config.PROFILE_BOOTSTRAP_FILE

        """
        Make sure there is at least one profile when first starting Vorta.
        Will either import a profile placed in ~/.vorta-init.json
        or add an empty "Default" profile.
        """
        if bootstrap_file.is_file():
            try:
                profile_export = ProfileExport.from_json(bootstrap_file)
                profile = profile_export.to_db(overwrite_profile=True, overwrite_settings=True)
            except Exception as exception:
                double_newline = os.linesep + os.linesep
                QMessageBox.critical(
                    None,
                    self.tr('Failed to import profile'),
                    "{}{}\"{}\"{}{}".format(
                        self.tr('Failed to import a profile from {}:').format(bootstrap_file),
                        double_newline,
                        str(exception),
                        double_newline,
                        self.tr('Consider removing or repairing this file to ' 'get rid of this message.'),
                    ),
                )
                return
            bootstrap_file.unlink()
            notifier = VortaNotifications.pick()
            notifier.deliver(
                self.tr('Profile import successful!'),
                self.tr('Profile {} imported.').format(profile.name),
                level='info',
            )
            logger.info('Profile {} imported.'.format(profile.name))
        if BackupProfileModel.select().count() == 0:
            default_profile = BackupProfileModel(name='Default')
            default_profile.save()

    def check_failed_response(self, result: Dict[str, Any]):
        """
        Process the signal that a repo consistency check failed.

        Displays a `QMessageBox` with an error message depending on the
        return code of the `BorgJob`.

        Parameters
        ----------
        repo_url : str
            The url of the repo of concern
        """
        # extract data from the params for the borg job
        repo_url = result['params']['repo_url']
        returncode = result['returncode']
        errors: List[Tuple[int, str]] = result['errors']
        error_message = errors[0][1] if errors else ''

        # Switch over returncodes
        if returncode == 0:
            # No fail
            logger.warning('VortaApp.check_failed_response was called with returncode 0')
        elif returncode == 130:
            # Keyboard interrupt
            pass
        else:  # Real error
            # Create QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)  # changed for warning
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setWindowTitle(self.tr('Repo Check Failed'))

            if returncode == 1:
                # warning
                msg.setIcon(QMessageBox.Icon.Warning)
                text = translate(
                    'VortaApp', 'Borg exited with warning status (rc 1). See the <a href="{0}">logs</a> for details.'
                ).format(config.LOG_DIR.as_uri())
                infotext = error_message
            elif returncode > 128:
                # 128+N - killed by signal N (e.g. 137 == kill -9)
                signal = returncode - 128
                text = self.tr('Repository data check for repo was killed by signal %s.') % (signal)
                infotext = self.tr('The process running the check job got a kill signal. Try again.')
            else:
                # Real error
                text = self.tr('Repository data check for repo %s failed. Error code %s') % (
                    repo_url,
                    returncode,
                )
                infotext = error_message + '\n'
                infotext += self.tr('Consider repairing or recreating the repository soon to avoid missing data.')

            msg.setText(text)
            msg.setInformativeText(infotext)
            # Display messagebox
            msg.exec()
