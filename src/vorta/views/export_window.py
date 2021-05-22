import logging
import os
from pathlib import Path

from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from vorta.keyring.abc import VortaKeyring
from vorta.models import BackupProfileModel  # noqa: F401
from vorta.utils import get_asset
from ..notifications import VortaNotifications
from ..profile_export import ProfileExport

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
