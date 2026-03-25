import os
from pathlib import PurePath

from PyQt6 import QtCore, uic
from PyQt6.QtCore import QMimeData, Qt, QUrl
from PyQt6.QtWidgets import QApplication, QLayout, QMenu, QMessageBox

from vorta.i18n import trans_late, translate
from vorta.i18n.richtext import escape, format_richtext, link
from vorta.store.models import ArchiveModel, RepoModel
from vorta.utils import borg_compat, get_asset, get_private_keys, pretty_bytes
from vorta.views.dialogs.repo.repo_add import AddRepoWindow, ExistingRepoWindow
from vorta.views.dialogs.repo.repo_change_passphrase import ChangeBorgPassphraseWindow
from vorta.views.dialogs.repo.ssh import SSHAddWindow

from .base_tab import BaseTab
from .utils import get_colored_icon

uifile = get_asset('UI/repo_tab.ui')
RepoUI, RepoBase = uic.loadUiType(uifile)


class RepoTab(BaseTab, RepoBase, RepoUI):
    repo_changed = QtCore.pyqtSignal()
    repo_added = QtCore.pyqtSignal()

    def __init__(self, parent=None, profile_provider=None):
        super().__init__(parent=parent, profile_provider=profile_provider)
        self.setupUi(parent)

        self.borgbase_sentence = trans_late('Form', 'For simple and secure backup hosting, try %1.')
        self.compression_help_text = trans_late('Form', 'Help on compression types')
        self._set_link_texts()

        # Populate dropdowns
        self.copyURLbutton.clicked.connect(self.copy_URL_action)

        # init repo add button
        self.menuAddRepo = QMenu(self.bAddRepo)
        self.menuAddRepo.addAction(self.tr("New Repository…"), self.new_repo)
        self.menuAddRepo.addAction(self.tr("Existing Repository…"), self.add_existing_repo)
        self.bAddRepo.setMenu(self.menuAddRepo)

        # init repo util button
        self.menuRepoUtil = QMenu(self.bRepoUtil)
        self.menuRepoUtil.addAction(self.tr("Unlink Repository…"), self.repo_unlink_action).setIcon(
            get_colored_icon("unlink")
        )
        self.menuRepoUtil.addAction(self.tr("Change Passphrase…"), self.repo_change_passphrase_action).setIcon(
            get_colored_icon("key")
        )
        self.bRepoUtil.setMenu(self.menuRepoUtil)

        # Compression algorithms setup
        self.repoCompression.addItem(self.tr('LZ4 (modern, default)'), 'lz4')
        self.repoCompression.addItem(self.tr('Zstandard Level 3 (modern)'), 'zstd,3')
        self.repoCompression.addItem(self.tr('Zstandard Level 8 (modern)'), 'zstd,8')
        self.repoCompression.addItem(self.tr('ZLIB Level 6 (auto, legacy)'), 'auto,zlib,6')
        self.repoCompression.addItem(self.tr('LZMA Level 6 (auto, legacy)'), 'auto,lzma,6')
        self.repoCompression.addItem(self.tr('No Compression'), 'none')
        self.repoCompression.currentIndexChanged.connect(self.compression_select_action)

        self.toggle_available_compression()

        self.init_ssh()
        self.sshComboBox.currentIndexChanged.connect(self.ssh_select_action)
        self.sshKeyToClipboardButton.clicked.connect(self.ssh_copy_to_clipboard_action)
        self.bAddSSHKey.clicked.connect(self.create_ssh_key)

        self.set_icons()

        # Connect the checkbox to our switch
        self.checkAdvanced.toggled.connect(self.on_advanced_toggled)

        # Ensure the checkbox is physically at the front for clicking
        self.checkAdvanced.raise_()

        # Start with the advanced buttons hidden (Standard View)
        self.checkAdvanced.setChecked(False)
        self.on_advanced_toggled(False)

        # Connect to events
        self.track_palette_change()
        self.track_profile_change(call_now=True)
        self.track_backup_finished(self.init_repo_stats)

    def _set_link_texts(self):
        borgbase_template = self.borgbaseLinkLabel.text()
        borgbase_sentence = format_richtext(
            escape(translate('Form', self.borgbase_sentence)),
            link('https://www.borgbase.com/?utm_source=vorta&utm_medium=app', 'BorgBase'),
        )
        self.borgbaseLinkLabel.setText(format_richtext(borgbase_template, borgbase_sentence))

        compression_template = self.compressionHelpLink.text()
        compression_link = link(
            'https://borgbackup.readthedocs.io/en/stable/usage/help.html#borg-help-compression',
            translate('Form', self.compression_help_text),
        )
        self.compressionHelpLink.setText(format_richtext(compression_template, compression_link))

    def set_icons(self):
        self.bAddSSHKey.setIcon(get_colored_icon("plus"))
        self.bAddRepo.setIcon(get_colored_icon("plus"))
        self.bRepoUtil.setIcon(get_colored_icon("ellipsis-v"))
        self.sshKeyToClipboardButton.setIcon(get_colored_icon('copy'))
        self.copyURLbutton.setIcon(get_colored_icon('copy'))

    def set_repos(self):
        self.repoSelector.clear()
        self.repoSelector.addItem(self.tr('No repository selected'), None)
        for repo in RepoModel.select():
            self.repoSelector.addItem(f"{repo.name + ' - ' if repo.name else ''}{repo.url}", repo.id)
            self.repoSelector.setItemData(self.repoSelector.count() - 1, repo.url, QtCore.Qt.ItemDataRole.ToolTipRole)

    def populate_from_profile(self):
        try:
            self.repoSelector.currentIndexChanged.disconnect(self.repo_select_action)
        except TypeError:
            pass

        self.set_repos()
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
        na = self.tr('N/A', "Not available.")
        self.tr("Select a repository first.")
        self.tr("Try refreshing the metadata of any archive.")

        repo: RepoModel = self.repo()
        if repo is not None:
            for child in self.frameRepoSettings.children():
                if hasattr(child, 'setEnabled'):
                    child.setEnabled(True)

            ssh_enabled = repo.is_remote_repo()
            self.sshComboBox.setEnabled(ssh_enabled)
            self.sshKeyToClipboardButton.setEnabled(ssh_enabled)

            if repo.unique_csize is not None:
                self.sizeCompressed.setText(pretty_bytes(repo.unique_csize))
            else:
                self.sizeCompressed.setText(na)

            if repo.unique_size is not None:
                self.sizeDeduplicated.setText(pretty_bytes(repo.unique_size))
            else:
                self.sizeDeduplicated.setText(na)

            if repo.total_size is not None:
                self.sizeOriginal.setText(pretty_bytes(repo.total_size))
            else:
                self.sizeOriginal.setText(na)

            self.repoEncryption.setText(str(repo.encryption))
        else:
            # Disable generic settings if no repo is selected
            for child in self.frameRepoSettings.children():
                if not isinstance(child, QLayout) and hasattr(child, 'setEnabled'):
                    child.setEnabled(False)

            self.bAddSSHKey.setEnabled(True)
            # Ensure toggle remains active even without a repository selected
            self.checkAdvanced.setEnabled(True)

            self.sizeCompressed.setText(na)
            self.sizeDeduplicated.setText(na)
            self.sizeOriginal.setText(na)
            self.repoEncryption.setText(na)

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
            if ix != -1:
                self.repoCompression.model().item(ix).setEnabled(use_zstd)

    def ssh_select_action(self, index):
        self.save_profile_attr('ssh_key', self.sshComboBox.itemData(index))

    def create_ssh_key(self):
        self._window = SSHAddWindow()
        self._window.setParent(self, QtCore.Qt.WindowType.Sheet)
        self._window.rejected.connect(self.init_ssh)
        self._window.failure.connect(self.create_ssh_key_failure)
        self._window.open()

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
                msg.setText(self.tr("The selected public SSH key was copied to the clipboard."))
            else:
                msg.setText(self.tr("Could not find public key."))
        else:
            msg.setText(self.tr("Select a public key from the dropdown first."))
        msg.show()

    def compression_select_action(self, index):
        self.save_profile_attr('compression', self.repoCompression.currentData())

    def new_repo(self):
        self._window = AddRepoWindow()
        self._window.setParent(self, QtCore.Qt.WindowType.Sheet)
        self._window.added_repo.connect(self.process_new_repo)
        self._window.open()

    def add_existing_repo(self):
        self._window = ExistingRepoWindow()
        self._window.setParent(self, QtCore.Qt.WindowType.Sheet)
        self._window.added_repo.connect(self.process_new_repo)
        self._window.open()

    def repo_select_action(self):
        self.save_profile_attr('repo', self.repoSelector.currentData())
        self.init_repo_stats()

    def process_new_repo(self, result):
        if result['returncode'] == 0:
            new_repo = RepoModel.get(url=result['params']['repo_url'])
            self.save_profile_attr('repo', new_repo.id)
            self.set_repos()
            self.repoSelector.setCurrentIndex(self.repoSelector.findData(new_repo.id))
            self.repo_added.emit()
            self.init_repo_stats()

    def repo_unlink_action(self):
        selected_repo_id = self.repoSelector.currentData()
        if not selected_repo_id:
            return

        try:
            self.repoSelector.currentIndexChanged.disconnect(self.repo_select_action)
        except TypeError:
            pass

        profile = self.profile()
        repo = RepoModel.get(id=selected_repo_id)
        repo_deleted = not repo.is_shared_with_other_profiles(excluding_profile_id=profile.id)
        profile.repo = None
        profile.save()
        if repo_deleted:
            repo.delete_instance(recursive=True)
            self.repoSelector.removeItem(self.repoSelector.currentIndex())

        self.repoSelector.setCurrentIndex(0)
        self.repo_changed.emit()
        self.populate_from_profile()

    def copy_URL_action(self):
        selected_repo_id = self.repoSelector.currentData()
        if not selected_repo_id:
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

    def repo_change_passphrase_action(self):
        if not self.profile().repo.encryption.startswith('repokey'):
            msg = QMessageBox()
            msg.setParent(self, QtCore.Qt.WindowType.Sheet)
            msg.setWindowTitle(self.tr("Invalid Encryption Type"))
            msg.setText(self.tr("Encryption type must be repokey."))
            msg.show()
            return
        self._window = ChangeBorgPassphraseWindow(self.profile())
        self._window.setParent(self, QtCore.Qt.WindowType.Sheet)
        self._window.change_borg_passphrase.connect(self._handle_passphrase_change_result)
        self._window.open()

    def _handle_passphrase_change_result(self, result):
        msg = QMessageBox()
        msg.setParent(self, QtCore.Qt.WindowType.Sheet)
        if result['returncode'] == 0:
            msg.setText(self.tr("The borg passphrase was successfully changed."))
        else:
            msg.setText(self.tr("Unable to change the repository passphrase. Please try again."))
        msg.show()

    def on_advanced_toggled(self, checked):
        """Magic switch: Hide/Show settings."""
        self.labelSSHKey.setVisible(checked)
        self.sshComboBox.setVisible(checked)
        self.bAddSSHKey.setVisible(checked)
        self.sshKeyToClipboardButton.setVisible(checked)

        self.labelCompression.setVisible(checked)
        self.repoCompression.setVisible(checked)
        self.compressionHelpLink.setVisible(checked)
