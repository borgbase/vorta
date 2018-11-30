import os
from PyQt5 import uic, QtCore
from PyQt5.QtWidgets import QApplication, QMessageBox

from ..models import RepoModel, ArchiveModel, BackupProfileMixin
from .repo_add_dialog import AddRepoWindow, ExistingRepoWindow
from ..utils import pretty_bytes, get_private_keys, get_asset
from .ssh_dialog import SSHAddWindow

uifile = get_asset('UI/repotab.ui')
RepoUI, RepoBase = uic.loadUiType(uifile, from_imports=True, import_from='vorta.views')


class RepoTab(RepoBase, RepoUI, BackupProfileMixin):
    repo_changed = QtCore.pyqtSignal()
    repo_added = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)

        # Populate dropdowns
        self.repoSelector.model().item(0).setEnabled(False)
        self.repoSelector.addItem('Initialize New Repository', 'init')
        self.repoSelector.addItem('Add Existing Repository', 'existing')
        for repo in RepoModel.select():
            self.repoSelector.addItem(repo.url, repo.id)

        self.repoSelector.currentIndexChanged.connect(self.repo_select_action)
        self.repoRemoveToolbutton.clicked.connect(self.repo_unlink_action)

        self.repoCompression.addItem('LZ4 (default)', 'lz4')
        self.repoCompression.addItem('Zstandard (medium)', 'zstd')
        self.repoCompression.addItem('LZMA (high)', 'lzma,6')
        self.repoCompression.addItem('No Compression', 'none')
        self.repoCompression.currentIndexChanged.connect(self.compression_select_action)

        self.init_ssh()
        self.sshComboBox.currentIndexChanged.connect(self.ssh_select_action)
        self.sshKeyToClipboardButton.clicked.connect(self.ssh_copy_to_clipboard_action)

        self.init_repo_stats()
        self.populate_from_profile()

    def populate_from_profile(self):
        profile = self.profile()
        if profile.repo:
            self.repoSelector.setCurrentIndex(self.repoSelector.findData(profile.repo.id))
        else:
            self.repoSelector.setCurrentIndex(0)

        self.repoCompression.setCurrentIndex(self.repoCompression.findData(profile.compression))
        self.sshComboBox.setCurrentIndex(self.sshComboBox.findData(profile.ssh_key))
        self.init_repo_stats()

    def init_repo_stats(self):
        repo = self.profile().repo
        if repo is not None:
            self.sizeCompressed.setText(pretty_bytes(repo.unique_csize))
            self.sizeDeduplicated.setText(pretty_bytes(repo.unique_size))
            self.sizeOriginal.setText(pretty_bytes(repo.total_size))
            self.repoEncryption.setText(str(repo.encryption))
        else:
            self.sizeCompressed.setText('')
            self.sizeDeduplicated.setText('')
            self.sizeOriginal.setText('')
            self.repoEncryption.setText('')
        self.repo_changed.emit()

    def init_ssh(self):
        keys = get_private_keys()
        self.sshComboBox.clear()
        self.sshComboBox.addItem('Automatically choose SSH Key (default)', None)
        self.sshComboBox.addItem('Create New Key', 'new')
        for key in keys:
            self.sshComboBox.addItem(f'{key["filename"]} ({key["format"]})', key['filename'])

    def ssh_select_action(self, index):
        if index == 1:
            ssh_add_window = SSHAddWindow()
            ssh_add_window.setParent(self, QtCore.Qt.Sheet)
            ssh_add_window.show()
            if ssh_add_window.exec_():
                self.init_ssh()
            else:
                self.sshComboBox.setCurrentIndex(0)
        else:
            profile = self.profile()
            profile.ssh_key = self.sshComboBox.itemData(index)
            profile.save()

    def ssh_copy_to_clipboard_action(self):
        msg = QMessageBox()
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setParent(self, QtCore.Qt.Sheet)

        index = self.sshComboBox.currentIndex()
        if index > 1:
            ssh_key_filename = self.sshComboBox.itemData(index)
            ssh_key_path = os.path.expanduser(f'~/.ssh/{ssh_key_filename}.pub')
            if os.path.isfile(ssh_key_path):
                pub_key = open(ssh_key_path).read().strip()
                clipboard = QApplication.clipboard()
                clipboard.setText(pub_key)

                msg.setText("Public Key Copied to Clipboard")
                msg.setInformativeText(
                    "The selected public SSH key was copied to the clipboard. "
                    "Use it to set up remote repo permissions.")

            else:
                msg.setText("Couldn't find public key.")
        else:
            msg.setText("Select a public key from the dropdown first.")
        msg.exec_()

    def compression_select_action(self, index):
        profile = self.profile()
        profile.compression = self.repoCompression.currentData()
        profile.save()

    def repo_select_action(self, index):
        if index == 0:
            return
        if index <= 2:
            if index == 1:
                window = AddRepoWindow()
            else:
                window = ExistingRepoWindow()
            window.setParent(self, QtCore.Qt.Sheet)
            window.show()
            if window.exec_():
                self.process_new_repo(window.result)
            else:
                self.repoSelector.setCurrentIndex(0)

        else:
            profile = self.profile()
            profile.repo = self.repoSelector.currentData()
            profile.save()
            self.init_repo_stats()

    def process_new_repo(self, result):
        if result['returncode'] == 0:
            new_repo = RepoModel.get(url=result['params']['repo_url'])
            profile = self.profile()
            profile.repo = new_repo.id
            profile.save()

            self.repoSelector.addItem(new_repo.url, new_repo.id)
            self.repoSelector.setCurrentIndex(self.repoSelector.count() - 1)
            self.repo_added.emit()
            self.init_repo_stats()

    def repo_unlink_action(self):
        profile = self.profile()
        self.init_repo_stats()
        msg = QMessageBox()
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setParent(self, QtCore.Qt.Sheet)
        selected_repo_id = self.repoSelector.currentData()
        selected_repo_index = self.repoSelector.currentIndex()
        if selected_repo_index > 2:
            repo = RepoModel.get(id=selected_repo_id)
            ArchiveModel.delete().where(ArchiveModel.repo_id == repo.id).execute()
            profile.repo = None
            profile.save()
            repo.delete_instance(recursive=True)  # This also deletes snapshots.
            self.repoSelector.setCurrentIndex(0)
            self.repoSelector.removeItem(selected_repo_index)
            msg.setText('Repository was Unlinked')
            msg.setInformativeText('You can always connect it again later.')
            msg.exec_()

            self.repo_changed.emit()
            self.init_repo_stats()
