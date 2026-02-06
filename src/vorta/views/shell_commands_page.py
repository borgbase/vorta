from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QLabel, QLineEdit, QWidget

from vorta.i18n.richtext import code, escape, format_richtext, italic, link
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
        self.shellCommandsHelpLabel: QLabel = self.findChild(QLabel, 'shellCommandsHelpLabel')
        self.borgCreateHelpLabel: QLabel = self.findChild(QLabel, 'borgCreateHelpLabel')
        self._set_help_texts()
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
        self._profile_changed_connection = QApplication.instance().profile_changed_event.connect(
            self.populate_from_profile
        )
        self.destroyed.connect(self._on_destroyed)

    def _set_help_texts(self):
        commands_template = self.shellCommandsHelpLabel.text()
        commands_sentence = format_richtext(
            escape(
                self.tr(
                    'Run custom shell commands before and after each backup. The actual backup and post-backup '
                    'command will only run, if the pre-backup command exits without error (return code 0). '
                    'Available variables: %1'
                )
            ),
            code('$repo_url, $profile_name, $profile_slug, $returncode'),
        )
        self.shellCommandsHelpLabel.setText(format_richtext(commands_template, commands_sentence))

        borg_template = self.borgCreateHelpLabel.text()
        borg_sentence = format_richtext(
            escape(self.tr('Extra arguments for %1. Possible options are listed in %2.')),
            italic('borg create'),
            link(
                'https://borgbackup.readthedocs.io/en/stable/usage/create.html',
                self.tr('the borg documentation'),
            ),
        )
        self.borgCreateHelpLabel.setText(format_richtext(borg_template, borg_sentence))

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

    def save_profile_attr(self, attr, new_value):
        profile = self.profile()
        setattr(profile, attr, new_value)
        profile.save()

    def save_repo_attr(self, attr, new_value):
        repo = self.profile().repo
        setattr(repo, attr, new_value)
        repo.save()

    def _on_destroyed(self):
        try:
            QApplication.instance().profile_changed_event.disconnect(self._profile_changed_connection)
        except (TypeError, RuntimeError):
            pass
