import json
import logging
from pathlib import Path

from PyQt5 import QtCore
from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog, QDialogButtonBox, QMessageBox

from vorta.keyring.abc import VortaKeyring
from vorta.models import SCHEMA_VERSION
from vorta.utils import get_asset
from .utils import get_colored_icon
from ..config_backup import ConfigBackup, VersionException
from ..notifications import VortaNotifications

uifile_import = get_asset('UI/backupwindow.ui')
BackupWindowUI, BackupWindowBase = uic.loadUiType(uifile_import)
uifile_export = get_asset('UI/restorewindow.ui')
RestoreWindowUI, RestoreWindowBase = uic.loadUiType(uifile_export)
logger = logging.getLogger(__name__)


class BackupWindow(BackupWindowBase, BackupWindowUI):
    def __init__(self, parent):
        super().__init__()
        self.setupUi(self)
        self.parent = parent
        self.setWindowTitle(self.tr("Backup Profile"))
        self.buttonBox.accepted.connect(self.run)
        self.buttonBox.rejected.connect(self.reject)

        self.keyring = VortaKeyring.get_keyring()
        profile = self.parent.current_profile
        if profile.repo is None or self.keyring.get_password('vorta-repo', profile.repo.url) is None:
            self.storePassword.hide()

    def get_file(self):
        """ Get targetted save file with custom extension """
        fileName = QFileDialog.getSaveFileName(
            self,
            self.tr("Save profile"),
            str(Path.home()),
            "JSON (*.json)")[0]
        if fileName:
            if not fileName.endswith('.json'):
                fileName += '.json'
        return fileName

    def run(self):
        """ Attempt to write backup to file """
        filename = self.get_file()
        if not filename:
            return False
        profile = self.parent.current_profile
        json_string = ConfigBackup.from_db(profile, self.storePassword.isChecked()).to_json()
        try:
            with open(filename, 'w') as file:
                file.write(json_string)
        except (PermissionError, OSError):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle(self.tr('Backup file unwritable'))
            msg.setText(self.tr('The file {} could not be created. Please choose another location.')
                        .format(filename))
            msg.exec()
            return False
        else:
            notifier = VortaNotifications.pick()
            notifier.deliver(self.tr('Config backup successful!'),
                             self.tr('Config backup written to {}.').format(filename), level='info')
            self.close()


class RestoreWindow(RestoreWindowUI, RestoreWindowBase):
    profile_restored = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.setupUi(self)
        self.parent = parent
        self.fileButton.setIcon(get_colored_icon('folder-open'))
        self.fileButton.clicked.connect(self.get_file)
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self.buttonBox.accepted.connect(self.run)
        self.buttonBox.rejected.connect(self.reject)
        self.setWindowTitle(self.tr("Restore Profile"))

    def run(self):
        """ Attempt to read backup file and restore profile """

        def get_schema_version(jsonData):
            return json.loads(jsonData)['SchemaVersion']['version']

        with open(self.locationLabel.text(), 'r') as file:
            try:
                json_string = file.read()
                new_profile = ConfigBackup.from_json(json_string).to_db(
                    override_settings=self.overrideExisting.isChecked())
            except (json.decoder.JSONDecodeError, KeyError) as e:
                logger.error(e)
                self.errors.setText(self.tr("Invalid backup file"))
            except AttributeError as e:
                logger.error(e)
                # Runs when model upgrading code in json_to_profile incomplete
                schema_message = "Current schema: {0}\n Backup schema: {1}".format(
                    SCHEMA_VERSION, get_schema_version(json_string))
                self.errors.setText(
                    self.tr("Schema upgrade failure, file a bug report with the link in the Misc tab "
                            "with the following error: \n {0} \n {1}").format(str(e), schema_message))
                raise e
            except VersionException as e:
                logger.error(e)
                self.errors.setText(self.tr("Newer backup files cannot be used on older versions."))
            except PermissionError as e:
                logger.error(e)
                self.errors.setText(self.tr("Cannot read backup file due to permission error."))
            except FileNotFoundError as e:
                logger.error(e)
                self.errors.setText(self.tr("Backup file not found."))
            else:
                if new_profile.repo:
                    repo_url = new_profile.repo.url
                    keyring = VortaKeyring.get_keyring()
                    if keyring.get_password('vorta-repo', repo_url):
                        self.errors.setText(self.tr(f"Profile {new_profile.name} restored sucessfully."))
                    else:
                        self.errors.setText(
                            self.tr(
                                f"Profile {new_profile.name} restored, but the password for {repo_url} cannot be found, consider unlinking and readding the repository."))  # noqa
                self.profile_restored.emit()
                notifier = VortaNotifications.pick()
                notifier.deliver(self.tr('Config restore successful!'),
                                 self.tr('Config backup restored from {}.').format(self.locationLabel.text()),
                                 level='info')
                self.close()

    def get_file(self):
        """ Attempt to read backup from file """
        filename = QFileDialog.getOpenFileName(
            self,
            self.tr("Load profile"),
            str(Path.home()),
            self.tr("JSON (*.json);;All files (*)"))[0]
        if filename:
            self.locationLabel.setText(filename)
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(bool(filename))
