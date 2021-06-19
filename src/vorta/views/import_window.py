from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox, QDialogButtonBox

from vorta.keyring.abc import VortaKeyring
from vorta.models import BackupProfileModel, SCHEMA_VERSION
from vorta.profile_export import VersionException
from vorta.views.export_window import ImportWindowUI, ImportWindowBase, logger


class ImportWindow(ImportWindowUI, ImportWindowBase):
    profile_imported = QtCore.pyqtSignal(BackupProfileModel)
    password_fill_finished = QtCore.pyqtSignal()
    next_password = QtCore.pyqtSignal()

    def __init__(self, profile_export):
        """
        @type profile_export: ProfileExport
        """
        super().__init__()
        self.profile_export = profile_export
        self.setupUi(self)
        self.buttonBox.rejected.connect(self.reject)
        self.setWindowTitle(self.tr("Import Profile"))
        if self.check_version():
            self.init_repo_password_field()
            self.init_overwrite_profile_checkbox()

    def check_version(self):
        if SCHEMA_VERSION >= 18 and self.profile_export.prof_x_repos is None:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
            self.repoPassword.setEnabled(False)
            self.overwriteExistingProfile.setEnabled(False)
            self.overwriteExistingSettings.setEnabled(False)
            self.askUser.setText(
                self.tr("You are trying to import an older profile format of vorta. We can't import your profile."))
            return False

        if SCHEMA_VERSION <= 17 and self.profile_export.prof_x_repos is not None:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
            self.repoPassword.setEnabled(False)
            self.overwriteExistingProfile.setEnabled(False)
            self.overwriteExistingSettings.setEnabled(False)
            self.askUser.setText(
                self.tr("You are trying to import a newer profile format of vorta. We can't import your profile "
                        "until you upgrade vorta > ? "))
            return False

        return True

    def init_repo_password_field(self):
        self.repo_id = 0
        self.repoPassword.textChanged[str].connect(self.on_repo_password_changed)
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self.next_password.connect(self.fill_next_password)
        # connect button to next password if user enter text
        self.buttonBox.accepted.connect(self.accept_user_input)
        self.password_fill_finished.connect(self.run_enabled)
        self.fill_next_password()

    def accept_user_input(self):
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self.repoPassword.setDisabled(True)
        self.repo_id += 1
        self.next_password.emit()

    def run_enabled(self):
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
        self.buttonBox.accepted.disconnect(self.accept_user_input)
        self.buttonBox.accepted.connect(self.run)

    def fill_next_password(self):
        """Try to prefill the borg passphrase either from the export or from the keyring."""
        prof_x_repos = self.profile_export.prof_x_repos
        repo_url = self.profile_export.get_repo_url(self.repo_id)
        repo_password = self.profile_export.get_repo_password(self.repo_id)
        if prof_x_repos and self.repo_id < len(prof_x_repos):
            # take password from file.
            if repo_password is not None:
                self.repoPassword.setText(repo_password)
                self.repoPassword.setDisabled(True)
                self.repoPassword.setToolTip(self.tr('The passphrase has been loaded from the export file'))
                self.repo_id += 1
                self.next_password.emit()

            # take password from keyring
            elif repo_url is not None:
                keyring = VortaKeyring.get_keyring()
                repo_password = keyring.get_password('vorta-repo', repo_url)
                if repo_password:
                    self.profile_export.set_repo_password(self.repo_id, repo_password)
                    self.repoPassword.setText(repo_password)
                    self.repoPassword.setDisabled(True)
                    self.repoPassword.setToolTip(self.tr('The passphrase has been loaded from your keyring'))
                    self.repo_id += 1
                    self.next_password.emit()

                # Take password from user
                else:
                    self.repoPassword.clear()
                    self.repoPassword.setEnabled(True)
                    self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
                    self.askUser.setText(
                        self.tr("Can't find the password for {} in your file or keyring. Please enter it if needed:".
                                format(repo_url)))
        else:
            self.password_fill_finished.emit()

    def on_repo_password_changed(self, repo_password):
        # password field is created if the user enters some text
        self.profile_export.set_repo_password(self.repo_id, repo_password)

    def init_overwrite_profile_checkbox(self):
        """Disable the overwrite profile checkbox if no profile with that name currently exists."""
        existing_backup_profile = BackupProfileModel.get_or_none(
            BackupProfileModel.name == self.profile_export.name
        )
        if not existing_backup_profile:
            self.overwriteExistingProfile.setChecked(False)
            self.overwriteExistingProfile.setEnabled(False)
            self.overwriteExistingProfile.setToolTip(
                self.tr(
                    'A profile with the name {} does not exist. Nothing to overwrite.'.format(self.profile_export.name)
                )
            )

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
                overwrite_profile=self.overwriteExistingProfile.isChecked(),
                overwrite_settings=self.overwriteExistingSettings.isChecked()
            )
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
            self.close()
