import os
from dateutil import parser
from PyQt5 import uic, QtCore

from .models import RepoModel, SourceDirModel, SnapshotModel, BackupProfileModel
from .repo_add import AddRepoWindow, ExistingRepoWindow
from .borg_runner import BorgThread
from .utils import prettyBytes, get_private_keys
from .ssh_add import SSHAddWindow

uifile = os.path.join(os.path.dirname(__file__), 'UI/repotab.ui')
RepoUI, RepoBase = uic.loadUiType(uifile)


class RepoTab(RepoBase, RepoUI):
    repo_changed = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)
        self.profile = self.window().profile

        self.repoSelector.model().item(0).setEnabled(False)
        self.repoSelector.addItem('Initialize New Repository', 'init')
        self.repoSelector.addItem('Add Existing Repository', 'existing')
        for repo in RepoModel.select():
            self.repoSelector.addItem(repo.url, repo.id)

        if self.profile.repo:
            self.repoSelector.setCurrentIndex(self.repoSelector.findData(self.profile.repo.id))
        self.repoSelector.currentIndexChanged.connect(self.repo_select_action)

        self.repoCompression.addItem('LZ4 (default)', 'lz4')
        self.repoCompression.addItem('Zstandard (medium)', 'zstd')
        self.repoCompression.addItem('LZMA (high)', 'lzma,6')
        self.repoCompression.setCurrentIndex(self.repoCompression.findData(self.profile.compression))
        self.repoCompression.currentIndexChanged.connect(self.compression_select_action)

        self.init_ssh()
        self.init_repo_stats()

    def init_repo_stats(self):
        self.sizeCompressed.setText(prettyBytes(self.profile.repo.unique_csize))
        self.sizeDeduplicated.setText(prettyBytes(self.profile.repo.unique_size))
        self.sizeOriginal.setText(prettyBytes(self.profile.repo.total_size))
        self.repoEncryption.setText(str(self.profile.repo.encryption))
        self.repo_changed.emit(self.profile.repo.id)

    def init_ssh(self):
        keys = get_private_keys()
        for key in keys:
            self.sshComboBox.addItem(f'{key["filename"]} ({key["format"]}:{key["fingerprint"]})', key['filename'])
        self.sshComboBox.currentIndexChanged.connect(self.ssh_select_action)

    def ssh_select_action(self, index):
        if index == 1:
            ssh_add_window = SSHAddWindow()
            ssh_add_window.setParent(self, QtCore.Qt.Sheet)
            ssh_add_window.show()
            if ssh_add_window.exec_():
                self.init_ssh()
        else:
            self.profile.ssh_key = self.sshComboBox.itemData(index)
            self.profile.save()
            print('set ssh key to', self.profile.ssh_key)


    def compression_select_action(self, index):
        self.profile.compression = self.repoCompression.currentData()
        self.profile.save()

    def repo_select_action(self, index):
        if index <= 2:
            if index == 1:
                repo_add_window = AddRepoWindow()
            else:
                repo_add_window = ExistingRepoWindow()

            repo_add_window.setParent(self, QtCore.Qt.Sheet)
            repo_add_window.show()
            if repo_add_window.exec_():
                params = repo_add_window.get_values()

                if index == 1:
                    cmd = ["borg", "init", "--log-json", f"--encryption={params['encryption']}", params['repo_url']]
                else:
                    cmd = ["borg", "list", "--json", params['repo_url']]

                self.set_status('Connecting to repo...', 0)
                thread = BorgThread(self, cmd, params)
                thread.updated.connect(self.repo_add_update_log)
                thread.result.connect(self.repo_add_result)
                thread.start()
        else:
            self.profile.repo = self.repoSelector.currentData()
            self.profile.save()
            self.init_repo_stats()

    def repo_add_update_log(self, text):
        self.set_status(text)

    def repo_add_result(self, result):
        if result['returncode'] == 0:
            self.set_status('Successfully connected to repo.', 100)
            new_repo, _ = RepoModel.get_or_create(
                url=result['params']['repo_url'],
                defaults={
                    'password': result['params']['password'],
                    # 'encryption': result['params'].get('encryption', '')
                }
            )
            if 'cache' in result['data']:
                stats = result['data']['cache']['stats']
                new_repo.total_size = stats['total_size']
                new_repo.unique_csize = stats['unique_csize']
                new_repo.unique_size = stats['unique_size']
                new_repo.total_unique_chunks = stats['total_unique_chunks']
                new_repo.encryption = result['data']['encryption']['mode']
            new_repo.save()
            self.profile.repo = new_repo.id
            self.profile.save()

            if 'archives' in result['data'].keys():
                for snapshot in result['data']['archives']:
                    new_snapshot, _ = SnapshotModel.get_or_create(
                        snapshot_id=snapshot['id'],
                        defaults={
                            'repo': new_repo.id,
                            'name': snapshot['name'],
                            'time': parser.parse(snapshot['time'])
                        }
                    )
                    new_snapshot.save()
            self.repoSelector.addItem(new_repo.url, new_repo.id)
            self.repoSelector.setCurrentIndex(self.repoSelector.count()-1)
            self.init_snapshots()
