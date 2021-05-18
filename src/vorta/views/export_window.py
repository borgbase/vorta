import logging
import os
from pathlib import Path

from PyQt5 import QtCore
from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from vorta.keyring.abc import VortaKeyring
from vorta.models import SCHEMA_VERSION, BackupProfileModel
from vorta.utils import get_asset
from ..notifications import VortaNotifications
from ..profile_export import ProfileExport, VersionException

uifile_import = get_asset('UI/exportwindow.ui')
ExportWindowUI, ExportWindowBase = uic.loadUiType(uifile_import)
uifile_export = get_asset('UI/importwindow.ui')
ImportWindowUI, ImportWindowBase = uic.loadUiType(uifile_export)
logger = logging.getLogger(__name__)


class ExportWindow(ExportWindowBase, ExportWindowUI):
    def __init__(self, profile):
        """
        @type profile: BackupProfileModel
        """
        super().__init__()
        self.profile = profile
        self.setupUi(self)
        self.setWindowTitle(self.tr("Export Profile"))
        self.buttonBox.accepted.connect(self.run)
        self.buttonBox.rejected.connect(self.reject)

        self.keyring = VortaKeyring.get_keyring()
        profile = self.profile
        if profile.repo is None or self.keyring.get_password('vorta-repo', profile.repo.url) is None:
            self.storePassword.setCheckState(False)
            self.storePassword.setDisabled(True)
            self.storePassword.setToolTip(self.tr('The current profile_export has no password'))

    def get_file(self):
        """ Get targeted save file with custom extension """
        default_file = os.path.join(Path.home(), '{}.json'.format(self.profile.name))
        file_name = QFileDialog.getSaveFileName(
            self,
            self.tr("Save profile_export"),
            default_file,
            "JSON (*.json)")[0]
        if file_name:
            if not file_name.endswith('.json'):
                file_name += '.json'
        return file_name

    def on_error(self, error, message):
        logger.error(error)
        QMessageBox.critical(None,
                             self.tr("Error while exporting"),
                             message)
        self.close()

    def run(self):
        """ Attempt to write profile_export export to file """
        filename = self.get_file()
        if not filename:
            return False
        profile = self.profile
        json_string = ProfileExport.from_db(profile, self.storePassword.isChecked()).to_json()
        try:
            with open(filename, 'w') as file:
                file.write(json_string)
        except (PermissionError, OSError) as e:
            self.on_error(
                e,
                self.tr('The file {} could not be created. Please choose another location.').format(filename)
            )
            return False
        else:
            notifier = VortaNotifications.pick()
            notifier.deliver(self.tr('Profile export successful!'),
                             self.tr('Profile export written to {}.').format(filename), level='info')
            self.close()


class ImportWindow(ImportWindowUI, ImportWindowBase):
    profile_imported = QtCore.pyqtSignal(BackupProfileModel)

    def __init__(self, profile_export):
        """
        @type profile_export: ProfileExport
        """
        super().__init__()
        self.profile_export = profile_export
        self.setupUi(self)
        self.repoPassword.textChanged[str].connect(self.on_repo_password_changed)
        if profile_export.repo_password:
            self.repoPassword.setText(profile_export.repo_password)
            self.repoPassword.setDisabled(True)
            self.repoPassword.setToolTip(self.tr('The passphrase has been loaded from the export file'))
        elif profile_export.repo_url:
            keyring = VortaKeyring.get_keyring()
            repo_password = keyring.get_password('vorta-repo', profile_export.repo_url)
            if repo_password:
                self.repoPassword.setText(repo_password)
                self.repoPassword.setDisabled(True)
                self.repoPassword.setToolTip(self.tr('The passphrase has been loaded from your keyring'))
        self.buttonBox.accepted.connect(self.run)
        self.buttonBox.rejected.connect(self.reject)
        self.setWindowTitle(self.tr("Import Profile"))

    def on_repo_password_changed(self, password):
        self.profile_export.repo_password = password

    def on_error(self, error, message):
        logger.error(error)
        QMessageBox.critical(None,
                             self.tr("Error while importing"),
                             message)
        self.close()

    def run(self):
        """ Attempt to read a profile export and import it """
        try:
            new_profile = self.profile_export.to_db(
                override_settings=self.overrideExisting.isChecked())
        except AttributeError as e:
            # Runs when model upgrading code in json_to_profile incomplete
            schema_message = "Current schema: {0}\n Profile export schema: {1}".format(
                SCHEMA_VERSION, self.profile_export.schema_version)
            self.on_error(e, self.tr("Schema upgrade failure, file a bug report with the link in the Misc tab "
                                     "with the following error: \n {0} \n {1}").format(str(e), schema_message))
        except VersionException as e:
            self.on_error(e, self.tr("Newer profile_export export files cannot be used on older versions."))
        except PermissionError as e:
            self.on_error(e, self.tr("Cannot read profile_export export file due to permission error."))
        except FileNotFoundError as e:
            self.on_error(e, self.tr("Profile export file not found."))
        else:
            self.profile_imported.emit(new_profile)
            notifier = VortaNotifications.pick()
            notifier.deliver(self.tr('Profile import successful!'),
                             self.tr('Profile {} imported.').format(new_profile.name),
                             level='info')
            self.close()
