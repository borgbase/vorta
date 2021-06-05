import os

from PyQt5 import uic, QtCore
from PyQt5.QtWidgets import QApplication, QMessageBox

from vorta.models import RepoModel, ArchiveModel, BackupProfileMixin
from vorta.utils import pretty_bytes, get_private_keys, get_asset, borg_compat
from .repo_add_dialog import AddRepoWindow, ExistingRepoWindow
from .ssh_dialog import SSHAddWindow
from .utils import get_colored_icon

uifile = get_asset('UI/repotab.ui')
RepoUI, RepoBase = uic.loadUiType(uifile)


class RepoTab(RepoBase, RepoUI, BackupProfileMixin):
    repo_changed = QtCore.pyqtSignal()
    repo_added = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)

        # Populate dropdowns
        self.repoSelector.model().item(0).setEnabled(False)
        self.repoSelector.addItem(self.tr('+ Initialize New Repository'), 'new')
        self.repoSelector.addItem(self.tr('+ Add Existing Repository'), 'existing')
        self.repoSelector.insertSeparator(3)
        self.populate_repositories()
        self.repoRemoveToolbutton.clicked.connect(self.repo_unlink_action)
        self.copyURLbutton.clicked.connect(self.copy_URL_action)

        # note: it is hard to describe these algorithms with attributes like low/medium/high
        # compression or speed on a unified scale. this is not 1-dimensional and also depends
        # on the input data. so we just tell what we know for sure.
        # "auto" is used for some slower / older algorithms to avoid wasting a lot of time
        # on uncompressible data.
        self.repoCompression.addItem(self.tr('LZ4 (modern, default)'), 'lz4')
        self.repoCompression.addItem(self.tr('Zstandard Level 3 (modern)'), 'zstd,3')
        self.repoCompression.addItem(self.tr('Zstandard Level 8 (modern)'), 'zstd,8')

        # zlib and lzma come from python stdlib and are there (and in borg) since long.
        # but maybe not much reason to start with these nowadays, considering zstd supports
        # a very wide range of compression levels and has great speed. if speed is more
        # important than compression, lz4 is even a little better.
        self.repoCompression.addItem(self.tr('ZLIB Level 6 (auto, legacy)'), 'auto,zlib,6')
        self.repoCompression.addItem(self.tr('LZMA Level 6 (auto, legacy)'), 'auto,lzma,6')
        self.repoCompression.addItem(self.tr('No Compression'), 'none')
        self.repoCompression.currentIndexChanged.connect(self.compression_select_action)

        self.toggle_available_compression()
        self.repoCompression.currentIndexChanged.connect(self.compression_select_action)

        self.init_ssh()
        self.sshComboBox.currentIndexChanged.connect(self.ssh_select_action)
        self.sshKeyToClipboardButton.clicked.connect(self.ssh_copy_to_clipboard_action)

        self.init_repo_stats()
        self.populate_from_profile()
        self.set_icons()

    def set_icons(self):
        self.repoRemoveToolbutton.setIcon(get_colored_icon('unlink'))
        self.sshKeyToClipboardButton.setIcon(get_colored_icon('copy'))
        self.copyURLbutton.setIcon(get_colored_icon('copy'))

    def set_repos(self):
        count = self.repoSelector.count()
        for _ in range(4, count):  # Repositories are listed after 4th entry in repoSelector
            self.repoSelector.removeItem(4)
        for repo in RepoModel.select():
            self.repoSelector.addItem(repo.url, repo.id)

    def populate_repositories(self):
        try:
            self.repoSelector.currentIndexChanged.disconnect(self.repo_select_action)
        except TypeError:  # raised when signal is not connected
            pass
        self.set_repos()
        self.populate_from_profile()
        self.repoSelector.currentIndexChanged.connect(self.repo_select_action)

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
        self.sshComboBox.addItem(self.tr('Automatically choose SSH Key (default)'), None)
        self.sshComboBox.addItem(self.tr('Create New Key'), 'new')
        for key in keys:
            self.sshComboBox.addItem(f'{key["filename"]} ({key["format"]})', key['filename'])

    def toggle_available_compression(self):
        use_zstd = borg_compat.check('ZSTD')
        for algo in ['zstd,3', 'zstd,8']:
            ix = self.repoCompression.findData(algo)
            self.repoCompression.model().item(ix).setEnabled(use_zstd)

    def ssh_select_action(self, index):
        if index == 1:
            ssh_add_window = SSHAddWindow()
            self._window = ssh_add_window  # For tests
            ssh_add_window.setParent(self, QtCore.Qt.Sheet)
            ssh_add_window.show()
            ssh_add_window.accepted.connect(self.init_ssh)
            ssh_add_window.rejected.connect(lambda: self.sshComboBox.setCurrentIndex(0))
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

                msg.setWindowTitle(self.tr("Public Key Copied to Clipboard"))
                msg.setText(self.tr(
                    "The selected public SSH key was copied to the clipboard. "
                    "Use it to set up remote repo permissions."))

            else:
                msg.setText(self.tr("Couldn't find public key."))
        else:
            msg.setText(self.tr("Select a public key from the dropdown first."))
        msg.show()

    def compression_select_action(self, index):
        profile = self.profile()
        profile.compression = self.repoCompression.currentData()
        profile.save()

    def repo_select_action(self, index):
        item_data = self.repoSelector.itemData(index)
        if index == 0:
            return
        elif item_data in ['new', 'existing']:
            if item_data == 'new':
                window = AddRepoWindow()
            else:
                window = ExistingRepoWindow()
            self._window = window  # For tests
            window.setParent(self, QtCore.Qt.Sheet)
            window.show()
            window.added_repo.connect(self.process_new_repo)
            window.rejected.connect(lambda: self.repoSelector.setCurrentIndex(0))
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

            self.set_repos()
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
            repo.delete_instance(recursive=True)  # This also deletes archives.
            self.repoSelector.setCurrentIndex(0)
            self.repoSelector.removeItem(selected_repo_index)
            msg.setWindowTitle(self.tr('Repository was Unlinked'))
            msg.setText(self.tr('You can always connect it again later.'))
            msg.show()

            self.repo_changed.emit()
            self.init_repo_stats()

    def copy_URL_action(self):
        if self.repoSelector.currentIndex() > 2:
            URL = self.repoSelector.currentText()
            QApplication.clipboard().setText(URL)
        else:
            msg = QMessageBox()
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setParent(self, QtCore.Qt.Sheet)
            msg.setText(self.tr("Select a repository from the dropdown first."))
            msg.show()
