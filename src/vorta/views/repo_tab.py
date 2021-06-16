import os

from PyQt5 import uic, QtCore
from PyQt5.QtWidgets import QApplication, QMessageBox

from vorta.models import RepoModel, ArchiveModel, BackupProfileMixin, BackupProfileModel
from vorta.utils import pretty_bytes, get_private_keys, get_asset, borg_compat
from .repo_add_dialog import AddRepoWindow, ExistingRepoWindow
from .ssh_dialog import SSHAddWindow
from .utils import get_colored_icon

uifile = get_asset('UI/repotab.ui')
RepoUI, RepoBase = uic.loadUiType(uifile)


class RepoTab(RepoBase, RepoUI):
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
        profile = BackupProfileModel.get(id=self.window().current_profile.id)
        count = self.repoSelector.count()
        for _ in range(4, count):  # Repositories are listed after 4th entry in repoSelector
            self.repoSelector.removeItem(4)
        repo_i = 3
        for repo in RepoModel.select():
            repo_i += 1
            self.repoSelector.addItem(repo.url, repo.id)
            self.repoSelector.setItemIcon(repo_i, get_colored_icon('times-solid'))

        repos = BackupProfileMixin.get_repos(profile.id)
        for repo in repos:
            active_repo = repo.repo.id + 3
            self.repoSelector.setItemIcon(active_repo, get_colored_icon('check-circle'))

    def populate_repositories(self):
        try:
            self.repoSelector.activated.disconnect(self.repo_select_action)
        except TypeError:  # raised when signal is not connected
            pass
        self.repoSelector.activated.connect(self.repo_select_action)
        self.set_repos()
        self.populate_from_profile()

    def populate_from_profile(self):
        profile = BackupProfileModel.get(id=self.window().current_profile.id)

        self.repoCompression.setCurrentIndex(self.repoCompression.findData(profile.compression))
        self.sshComboBox.setCurrentIndex(self.sshComboBox.findData(profile.ssh_key))
        self.init_repo_stats()

        repo_i = 3
        for repo in RepoModel.select():
            repo_i += 1
            self.repoSelector.setItemIcon(repo_i, get_colored_icon('times-solid'))

        repos = BackupProfileMixin.get_repos(profile.id)
        for prof_x_repo in repos:
            active_repo = prof_x_repo.repo.id + 3
            self.repoSelector.setItemIcon(active_repo, get_colored_icon('check-circle'))

    def init_repo_stats(self):
        profile = self.window().current_profile.id
        unique_csize = 0
        unique_size = 0
        total_size = 0
        encryption = ""

        query = BackupProfileMixin.get_repos(profile)

        for repo_i in query:
            repo = repo_i.repo
            if repo.unique_csize is not None:
                unique_csize += repo.unique_csize
            if repo.unique_size is not None:
                unique_size += repo.unique_size
            if repo.total_size is not None:
                total_size += repo.total_size
            if repo.encryption is not None:
                encryption += " %s" % (str(repo.encryption))

        self.sizeCompressed.setText(pretty_bytes(unique_csize))
        self.sizeDeduplicated.setText(pretty_bytes(unique_size))
        self.sizeOriginal.setText(pretty_bytes(total_size))
        self.repoEncryption.setText(str(encryption))
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
            profile = BackupProfileModel.get(id=self.window().current_profile.id)
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
        profile = BackupProfileModel.get(id=self.window().current_profile.id)
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
            profile = BackupProfileModel.get(id=self.window().current_profile.id)
            profile.repo = self.repoSelector.currentData()
            profile.save()
            # add repo if exist and remove either with add_repo
            is_created = BackupProfileMixin.delete_or_create(self, self.repoSelector.currentData())
            repo_i = self.repoSelector.currentIndex()
            if is_created:
                self.repoSelector.setItemIcon(repo_i, get_colored_icon('check-circle'))
            else:
                self.repoSelector.setItemIcon(repo_i, get_colored_icon('times-solid'))
            self.init_repo_stats()

    def process_new_repo(self, result):
        if result['returncode'] == 0:
            new_repo = RepoModel.get(url=result['params']['repo_url'])
            profile = BackupProfileModel.get(id=self.window().current_profile.id)
            profile.repo = new_repo.id
            profile.save()

            self.set_repos()
            self.repoSelector.setCurrentIndex(self.repoSelector.count() - 1)
            self.repo_select_action(self.repoSelector.count() - 1)
            self.repo_added.emit()
            self.init_repo_stats()

    def repo_unlink_action(self):
        profile = BackupProfileModel.get(id=self.window().current_profile.id)
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
