from PyQt6 import uic
from PyQt6.QtWidgets import QLineEdit, QWidget

from vorta.utils import get_asset
from vorta.views.base_tab import BaseTab


class ShellCommandsPage(BaseTab, QWidget):
    def __init__(self, parent=None, profile_provider=None):
        super().__init__(parent=parent, profile_provider=profile_provider)
        uifile = get_asset('UI/shell_commands_page.ui')
        uic.loadUi(uifile, self)

        self.preBackupCmdLineEdit: QLineEdit = self.findChild(QLineEdit, 'preBackupCmdLineEdit')
        self.postBackupCmdLineEdit: QLineEdit = self.findChild(QLineEdit, 'postBackupCmdLineEdit')
        self.createCmdLineEdit: QLineEdit = self.findChild(QLineEdit, 'createCmdLineEdit')
        self.populate_from_profile()

        self.preBackupCmdLineEdit.textEdited.connect(
            lambda new_val, attr='pre_backup_cmd': self.save_profile_attr(attr, new_val)
        )
        self.postBackupCmdLineEdit.textEdited.connect(
            lambda new_val, attr='post_backup_cmd': self.save_profile_attr(attr, new_val)
        )
        self.createCmdLineEdit.textEdited.connect(
            lambda new_val, attr='create_backup_cmd': self.save_repo_attr(attr, new_val)
        )
        self.track_profile_change()

    def populate_from_profile(self):
        profile = self.profile()
        if profile.repo:
            self.createCmdLineEdit.setText(profile.repo.create_backup_cmd)
            self.createCmdLineEdit.setEnabled(True)

            self.preBackupCmdLineEdit.setText(profile.pre_backup_cmd)
            self.preBackupCmdLineEdit.setEnabled(True)

            self.postBackupCmdLineEdit.setText(profile.post_backup_cmd)
            self.postBackupCmdLineEdit.setEnabled(True)
        else:
            self.createCmdLineEdit.setEnabled(False)
            self.preBackupCmdLineEdit.setEnabled(False)
            self.postBackupCmdLineEdit.setEnabled(False)
