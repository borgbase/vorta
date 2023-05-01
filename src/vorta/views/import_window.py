from PyQt6 import QtCore
from PyQt6.QtWidgets import QMessageBox

from vorta.keyring.abc import VortaKeyring
from vorta.profile_export import VersionException
from vorta.store.connection import SCHEMA_VERSION
from vorta.store.models import BackupProfileModel
from vorta.views.export_window import ImportWindowBase, ImportWindowUI, logger


class ImportWindow(ImportWindowUI, ImportWindowBase):
    profile_imported = QtCore.pyqtSignal(BackupProfileModel)

    def __init__(self, profile_export):
        """
        @type profile_export: ProfileExport
        """
        super().__init__()
        self.profile_export = profile_export
        self.setupUi(self)
        self.init_repo_password_field(profile_export)
        self.init_overwrite_profile_checkbox()
        self.buttonBox.accepted.connect(self.run)
        self.buttonBox.rejected.connect(self.reject)
        self.setWindowTitle(self.tr("Import Profile"))

    def init_repo_password_field(self, profile_export):
        """Try to prefill the borg passphrase either from the export or from the keyring."""
        self.repoPassword.textChanged[str].connect(self.on_repo_password_changed)
        if profile_export.repo_password:
            self.repoPassword.setText(profile_export.repo_password)
            self.repoPassword.setDisabled(True)
            self.repoPassword.setToolTip(self.tr('Enter passphrase (already loaded from the export file)'))
        elif profile_export.repo_url:
            keyring = VortaKeyring.get_keyring()
            repo_password = keyring.get_password('vorta-repo', profile_export.repo_url)
            if repo_password:
                self.repoPassword.setText(repo_password)
                self.repoPassword.setDisabled(True)
                self.repoPassword.setToolTip(self.tr('Enter passphrase (already loaded from your keyring)'))

    def init_overwrite_profile_checkbox(self):
        """Disable the overwrite profile checkbox if no profile with that name currently exists."""
        existing_backup_profile = BackupProfileModel.get_or_none(BackupProfileModel.name == self.profile_export.name)
        if not existing_backup_profile:
            self.overwriteExistingProfile.setChecked(False)
            self.overwriteExistingProfile.setEnabled(False)
            self.overwriteExistingProfile.setToolTip(self.tr('(Name is not used yet)'))

    def on_repo_password_changed(self, password):
        self.profile_export.repo_password = password

    def on_error(self, error, message):
        logger.error(error)
        QMessageBox.critical(None, self.tr("Error while importing"), message)
        self.close()

    def run(self):
        """Attempt to read a profile export and import it"""
        try:
            new_profile = self.profile_export.to_db(
                overwrite_profile=self.overwriteExistingProfile.isChecked(),
                overwrite_settings=self.overwriteExistingSettings.isChecked(),
            )
        except AttributeError as e:
            # Runs when model upgrading code in json_to_profile incomplete
            schema_message = "Current schema: {0}\n Profile export schema: {1}".format(
                SCHEMA_VERSION, self.profile_export.schema_version
            )
            self.on_error(
                e,
                self.tr(
                    "Schema upgrade failure, file a bug report with the link in the Misc tab "
                    "with the following error: \n {0} \n {1}"
                ).format(str(e), schema_message),
            )
        except VersionException as e:
            self.on_error(
                e,
                self.tr("Newer profile_export export files cannot be used on older versions."),
            )
        except PermissionError as e:
            self.on_error(
                e,
                self.tr("Cannot read profile_export export file due to permission error."),
            )
        except FileNotFoundError as e:
            self.on_error(e, self.tr("Profile export file not found."))
        else:
            self.profile_imported.emit(new_profile)
            self.close()
