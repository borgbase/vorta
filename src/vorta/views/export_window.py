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
from ..notifications import VortaNotifications
from ..profile_export import ProfileExport, VersionException

uifile_import = get_asset('UI/exportwindow.ui')
ExportWindowUI, ExportWindowBase = uic.loadUiType(uifile_import)
uifile_export = get_asset('UI/importwindow.ui')
ImportWindowUI, ImportWindowBase = uic.loadUiType(uifile_export)
logger = logging.getLogger(__name__)


class ExportWindow(ExportWindowBase, ExportWindowUI):
    def __init__(self, parent):
        super().__init__()
        self.setupUi(self)
        self.parent = parent
        self.setWindowTitle(self.tr("Export Profile"))
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
        """ Attempt to write profile export to file """
        filename = self.get_file()
        if not filename:
            return False
        profile = self.parent.current_profile
        json_string = ProfileExport.from_db(profile, self.storePassword.isChecked()).to_json()
        try:
            with open(filename, 'w') as file:
                file.write(json_string)
        except (PermissionError, OSError):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle(self.tr('Profile export file unwritable'))
            msg.setText(self.tr('The file {} could not be created. Please choose another location.')
                        .format(filename))
            msg.exec()
            return False
        else:
            notifier = VortaNotifications.pick()
            notifier.deliver(self.tr('Profile export successful!'),
                             self.tr('Profile export written to {}.').format(filename), level='info')
            self.close()


class ImportWindow(ImportWindowUI, ImportWindowBase):
    profile_imported = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.setupUi(self)
        self.parent = parent
        self.fileButton.setIcon(get_colored_icon('folder-open'))
        self.fileButton.clicked.connect(self.get_file)
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self.buttonBox.accepted.connect(self.run)
        self.buttonBox.rejected.connect(self.reject)
        self.setWindowTitle(self.tr("Import Profile"))

    def run(self):
        """ Attempt to read a profile export and import it """
        def get_schema_version(jsonData):
            return json.loads(jsonData)['SchemaVersion']['version']

        with open(self.locationLabel.text(), 'r') as file:
            try:
                json_string = file.read()
                new_profile = ProfileExport.from_json(json_string).to_db(
                    override_settings=self.overrideExisting.isChecked())
            except (json.decoder.JSONDecodeError, KeyError) as e:
                logger.error(e)
                self.errors.setText(self.tr("Invalid profile export file"))
            except AttributeError as e:
                logger.error(e)
                # Runs when model upgrading code in json_to_profile incomplete
                schema_message = "Current schema: {0}\n Profile export schema: {1}".format(
                    SCHEMA_VERSION, get_schema_version(json_string))
                self.errors.setText(
                    self.tr("Schema upgrade failure, file a bug report with the link in the Misc tab "
                            "with the following error: \n {0} \n {1}").format(str(e), schema_message))
                raise e
            except VersionException as e:
                logger.error(e)
                self.errors.setText(self.tr("Newer profile export files cannot be used on older versions."))
            except PermissionError as e:
                logger.error(e)
                self.errors.setText(self.tr("Cannot read profile export file due to permission error."))
            except FileNotFoundError as e:
                logger.error(e)
                self.errors.setText(self.tr("Profile export file not found."))
            else:
                if new_profile.repo:
                    repo_url = new_profile.repo.url
                    keyring = VortaKeyring.get_keyring()
                    if keyring.get_password('vorta-repo', repo_url):
                        self.errors.setText(self.tr(f"Profile {new_profile.name} imported sucessfully."))
                    else:
                        self.errors.setText(
                            self.tr(
                                f"Profile {new_profile.name} imported, but the password for {repo_url} cannot be found, consider unlinking and readding the repository."))  # noqa
                self.profile_imported.emit()
                notifier = VortaNotifications.pick()
                notifier.deliver(self.tr('Profile import successful!'),
                                 self.tr('Profile imported from {}.').format(self.locationLabel.text()),
                                 level='info')
                self.close()

    def get_file(self):
        """ Attempt to read profile export from file """
        filename = QFileDialog.getOpenFileName(
            self,
            self.tr("Load profile"),
            str(Path.home()),
            self.tr("JSON (*.json);;All files (*)"))[0]
        if filename:
            self.locationLabel.setText(filename)
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(bool(filename))
