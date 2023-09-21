import os
from pathlib import PurePath

from PyQt6 import QtCore, uic
from PyQt6.QtCore import QMimeData, QUrl
from PyQt6.QtWidgets import QApplication, QLayout, QMenu, QMessageBox

from vorta.store.models import ArchiveModel, BackupProfileMixin, RepoModel
from vorta.utils import borg_compat, get_asset, get_private_keys, pretty_bytes

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
        self.repoRemoveToolbutton.clicked.connect(self.repo_unlink_action)
        self.copyURLbutton.clicked.connect(self.copy_URL_action)

        # init repo add button
        self.menuAddRepo = QMenu(self.bAddRepo)

        self.menuAddRepo.addAction(self.tr("New Repository…"), self.new_repo)
        self.menuAddRepo.addAction(self.tr("Existing Repository…"), self.add_existing_repo)

        self.bAddRepo.setMenu(self.menuAddRepo)

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
        self.bAddSSHKey.clicked.connect(self.create_ssh_key)

        self.set_icons()

        # Connect to palette change
        QApplication.instance().paletteChanged.connect(lambda p: self.set_icons())

        self.populate_from_profile()  # needs init of ssh and compression items

    def set_icons(self):
        self.bAddSSHKey.setIcon(get_colored_icon("plus"))
        self.bAddRepo.setIcon(get_colored_icon("plus"))
        self.repoRemoveToolbutton.setIcon(get_colored_icon('unlink'))
        self.sshKeyToClipboardButton.setIcon(get_colored_icon('copy'))
        self.copyURLbutton.setIcon(get_colored_icon('copy'))

    def set_repos(self):
        self.repoSelector.clear()
        self.repoSelector.addItem(self.tr('No repository selected'), None)
        # set tooltip = url for each item in the repoSelector
        for repo in RepoModel.select():
            self.repoSelector.addItem(f"{repo.name + ' - ' if repo.name else ''}{repo.url}", repo.id)
            self.repoSelector.setItemData(self.repoSelector.count() - 1, repo.url, QtCore.Qt.ItemDataRole.ToolTipRole)

    def populate_from_profile(self):
        try:
            self.repoSelector.currentIndexChanged.disconnect(self.repo_select_action)
        except TypeError:  # raised when signal is not connected
            pass

        # populate repositories
        self.set_repos()

        # load profile configuration
        profile = self.profile()
        if profile.repo:
            self.repoSelector.setCurrentIndex(self.repoSelector.findData(profile.repo.id))
        else:
            self.repoSelector.setCurrentIndex(0)

        self.repoCompression.setCurrentIndex(self.repoCompression.findData(profile.compression))
        self.sshComboBox.setCurrentIndex(self.sshComboBox.findData(profile.ssh_key))
        self.init_repo_stats()

        self.repoSelector.currentIndexChanged.connect(self.repo_select_action)

    def init_repo_stats(self):
        """Set the strings of the repo stats labels."""
        # prepare translations
        na = self.tr('N/A', "Not available.")
        no_repo_selected = self.tr("Select a repository first.")
        refresh = self.tr("Try refreshing the metadata of any archive.")

        # set labels
        repo: RepoModel = self.profile().repo
        if repo is not None:
            # remove *unset* item
            self.repoSelector.removeItem(self.repoSelector.findData(None))

            # Start with every element enabled, then disable SSH-related if relevant
            for child in self.frameRepoSettings.children():
                child.setEnabled(True)
            # local repo doesn't use ssh
            ssh_enabled = repo.is_remote_repo()
            # self.bAddSSHKey.setEnabled(ssh_enabled)
            # otherwise one cannot add a ssh key for adding a repo
            self.sshComboBox.setEnabled(ssh_enabled)
            self.sshKeyToClipboardButton.setEnabled(ssh_enabled)

            # update stats
            if repo.unique_csize is not None:
                self.sizeCompressed.setText(pretty_bytes(repo.unique_csize))
                self.sizeCompressed.setToolTip('')
            else:
                self.sizeCompressed.setText(na)
                self.sizeCompressed.setToolTip(refresh)

            if repo.unique_size is not None:
                self.sizeDeduplicated.setText(pretty_bytes(repo.unique_size))
                self.sizeDeduplicated.setToolTip('')
            else:
                self.sizeDeduplicated.setText(na)
                self.sizeDeduplicated.setToolTip(refresh)

            if repo.total_size is not None:
                self.sizeOriginal.setText(pretty_bytes(repo.total_size))
                self.sizeOriginal.setToolTip('')
            else:
                self.sizeOriginal.setText(na)
                self.sizeOriginal.setToolTip(refresh)

            self.repoEncryption.setText(str(repo.encryption))
        else:
            # Compression and SSH key are only valid entries for a repo
            # Yet Add SSH key button must be enabled for bootstrapping
            for child in self.frameRepoSettings.children():
                if not isinstance(child, QLayout):
                    child.setEnabled(False)
            self.bAddSSHKey.setEnabled(True)

            # unset stats
            self.sizeCompressed.setText(na)
            self.sizeCompressed.setToolTip(no_repo_selected)

            self.sizeDeduplicated.setText(na)
            self.sizeDeduplicated.setToolTip(no_repo_selected)

            self.sizeOriginal.setText(na)
            self.sizeOriginal.setToolTip(no_repo_selected)

            self.repoEncryption.setText(na)
            self.repoEncryption.setToolTip(no_repo_selected)

        self.repo_changed.emit()

    def init_ssh(self):
        keys = get_private_keys()
        self.sshComboBox.clear()
        self.sshComboBox.addItem(self.tr('Automatically choose SSH Key (default)'), None)
        for key in keys:
            self.sshComboBox.addItem(f'{key}', key)

    def toggle_available_compression(self):
        use_zstd = borg_compat.check('ZSTD')
        for algo in ['zstd,3', 'zstd,8']:
            ix = self.repoCompression.findData(algo)
            self.repoCompression.model().item(ix).setEnabled(use_zstd)

    def ssh_select_action(self, index):
        profile = self.profile()
        profile.ssh_key = self.sshComboBox.itemData(index)
        profile.save()

    def create_ssh_key(self):
        """Open a dialog to create an ssh key."""
        ssh_add_window = SSHAddWindow()
        self._window = ssh_add_window  # For tests
        ssh_add_window.setParent(self, QtCore.Qt.WindowType.Sheet)
        ssh_add_window.rejected.connect(self.init_ssh)
        ssh_add_window.failure.connect(self.create_ssh_key_failure)
        ssh_add_window.open()

    def create_ssh_key_failure(self, exit_code):
        msg = QMessageBox()
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setParent(self, QtCore.Qt.WindowType.Sheet)
        msg.setText(self.tr(f'Error during key generation. Exited with code {exit_code}.'))
        msg.show()

    def ssh_copy_to_clipboard_action(self):
        msg = QMessageBox()
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setParent(self, QtCore.Qt.WindowType.Sheet)

        index = self.sshComboBox.currentIndex()
        if index > 0:
            ssh_key_filename = self.sshComboBox.itemData(index)
            ssh_key_path = os.path.expanduser(f'~/.ssh/{ssh_key_filename}.pub')
            if os.path.isfile(ssh_key_path):
                pub_key = open(ssh_key_path).read().strip()
                clipboard = QApplication.clipboard()
                clipboard.setText(pub_key)

                msg.setWindowTitle(self.tr("Public Key Copied to Clipboard"))
                msg.setText(
                    self.tr(
                        "The selected public SSH key was copied to the clipboard. "
                        "Use it to set up remote repo permissions."
                    )
                )
            else:
                msg.setText(self.tr("Could not find public key."))
        else:
            msg.setText(self.tr("Select a public key from the dropdown first."))
        msg.show()

    def compression_select_action(self, index):
        profile = self.profile()
        profile.compression = self.repoCompression.currentData()
        profile.save()

    def new_repo(self):
        """Open a dialog to create a new repo and add it to vorta."""
        window = AddRepoWindow()
        self._window = window  # For tests
        window.setParent(self, QtCore.Qt.WindowType.Sheet)
        window.added_repo.connect(self.process_new_repo)
        # window.rejected.connect(lambda: self.repoSelector.setCurrentIndex(0))
        window.open()

    def add_existing_repo(self):
        """Open a dialog to add a existing repo to vorta."""
        window = ExistingRepoWindow()
        self._window = window  # For tests
        window.setParent(self, QtCore.Qt.WindowType.Sheet)
        window.added_repo.connect(self.process_new_repo)
        # window.rejected.connect(lambda: self.repoSelector.setCurrentIndex(0))
        window.open()

    def repo_select_action(self):
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
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setParent(self, QtCore.Qt.WindowType.Sheet)

        selected_repo_id = self.repoSelector.currentData()
        selected_repo_index = self.repoSelector.currentIndex()

        if not selected_repo_id:
            # QComboBox is empty / repo unset
            return

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
        self.populate_from_profile()

    def copy_URL_action(self):
        selected_repo_id = self.repoSelector.currentData()
        if not selected_repo_id:
            # QComboBox is empty / repo unset
            return

        repo = RepoModel.get(id=selected_repo_id)

        url = repo.url
        data = QMimeData()

        if not repo.is_remote_repo():
            path = PurePath(url)
            data.setUrls([QUrl(path.as_uri())])
            data.setText(str(path))
        else:
            data.setText(url)

        QApplication.clipboard().setMimeData(data)
