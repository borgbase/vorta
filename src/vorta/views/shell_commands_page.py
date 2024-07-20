from PyQt6 import uic
from PyQt6.QtWidgets import QLineEdit, QWidget

from vorta.store.models import BackupProfileMixin
from vorta.utils import get_asset


class ShellCommandsPage(QWidget, BackupProfileMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        uifile = get_asset('UI/shell_commands_page.ui')
        uic.loadUi(uifile, self)

        self.preBackupCmdLineEdit: QLineEdit = self.findChild(QLineEdit, 'preBackupCmdLineEdit')
        self.postBackupCmdLineEdit: QLineEdit = self.findChild(QLineEdit, 'postBackupCmdLineEdit')
        self.createCmdLineEdit: QLineEdit = self.findChild(QLineEdit, 'createCmdLineEdit')
        profile = self.profile()
        if profile.repo:
            self.createCmdLineEdit.setText(profile.repo.create_backup_cmd)
            self.createCmdLineEdit.setEnabled(True)
        else:
            self.createCmdLineEdit.setEnabled(False)

        self.setup_connections()

    def setup_connections(self):
        self.preBackupCmdLineEdit.textEdited.connect(
            lambda new_val, attr='pre_backup_cmd': self.save_profile_attr(attr, new_val)
        )
        self.postBackupCmdLineEdit.textEdited.connect(
            lambda new_val, attr='post_backup_cmd': self.save_profile_attr(attr, new_val)
        )
        self.createCmdLineEdit.textEdited.connect(
            lambda new_val, attr='create_backup_cmd': self.save_repo_attr(attr, new_val)
        )

    def save_profile_attr(self, attr, new_value):
        profile = self.profile()
        setattr(profile, attr, new_value)
        profile.save()

    def save_repo_attr(self, attr, new_value):
        repo = self.profile().repo
        setattr(repo, attr, new_value)
        repo.save()
