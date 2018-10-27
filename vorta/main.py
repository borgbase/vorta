import os
import platform
from datetime import datetime as dt
from dateutil import parser
from PyQt5.QtWidgets import QApplication, QFileDialog, QTableWidgetItem, QTableView, QTableWidget
from PyQt5 import uic, QtCore, QtGui, QtWidgets

from .repo_add import AddRepoWindow, ExistingRepoWindow
from .ssh_add import SSHAddWindow
from .config import APP_NAME, reset_app
from .models import RepoModel, SourceDirModel, SnapshotModel, BackupProfileModel
from .ssh_keys import get_private_keys
from .borg_runner import BorgThread
from .utils import prettyByes


uifile = os.path.join(os.path.dirname(__file__), 'UI/mainwindow.ui')
MainWindowUI, MainWindowBase = uic.loadUiType(uifile)


class MainWindow(MainWindowBase, MainWindowUI):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle(APP_NAME)
        self.profile = BackupProfileModel.get(id=1)
        self.init_repo()
        self.init_source()
        self.init_snapshots()
        self.init_compression()
        self.init_ssh()

        self.createStartBtn.clicked.connect(self.create_action)
        self.actionResetApp.triggered.connect(self.menu_reset)

    def set_status(self, text=None, progress_max=None):
        if text:
            self.createProgressText.setText(text)
        if progress_max is not None:
            self.createProgress.setRange(0, progress_max)
        self.createProgressText.repaint()

    def create_action(self):
        n_backup_folders = self.sourceDirectoriesWidget.count()
        if n_backup_folders == 0:
            self.set_status('Add some folders to back up first.')
            return
        self.set_status('Starting Backup.', progress_max=0)
        self.createStartBtn.setEnabled(False)
        self.createStartBtn.repaint()

        repo_id = self.repoSelector.currentData()
        repo = RepoModel.get(id=repo_id)
        cmd = ['borg', 'create', '--log-json', '--json', '-C', self.profile.compression,
               f'{repo.url}::{platform.node()}-{dt.now().isoformat()}'
        ]
        for i in range(n_backup_folders):
            cmd.append(self.sourceDirectoriesWidget.item(i).text())

        thread = BorgThread(self, cmd, {})
        thread.updated.connect(self.create_update_log)
        thread.result.connect(self.create_get_result)
        thread.start()

    def create_update_log(self, text):
        self.set_status(text)

    def create_get_result(self, result):
        self.createStartBtn.setEnabled(True)
        self.createStartBtn.repaint()
        if result['returncode'] == 0:
            self.set_status('Finished backup.', 100)
            new_snapshot = SnapshotModel(
                snapshot_id=result['data']['archive']['id'],
                name=result['data']['archive']['name'],
                time=parser.parse(result['data']['archive']['start']),
                repo=self.repoSelector.currentData()
            )
            new_snapshot.save()
            if 'cache' in result['data']:
                stats = result['data']['cache']['stats']
                repo = self.profile.repo
                repo.total_size = stats['total_size']
                repo.unique_csize = stats['unique_csize']
                repo.unique_size = stats['unique_size']
                repo.total_unique_chunks = stats['total_unique_chunks']
                repo.save()
            self.init_snapshots()

    def init_source(self):
        self.sourceAdd.clicked.connect(self.source_add)
        self.sourceRemove.clicked.connect(self.source_remove)
        for source in SourceDirModel.select():
            self.sourceDirectoriesWidget.addItem(source.dir)

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

    def init_snapshots(self):
        if self.profile.repo:
            snapshots = [s for s in self.profile.repo.snapshots.select()]

            for row, snapshot in enumerate(snapshots):
                self.snapshotTable.insertRow(row)
                self.snapshotTable.setItem(row, 0, QTableWidgetItem(snapshot.name))
                formatted_time = snapshot.time.strftime('%Y-%m-%d %H:%M')
                self.snapshotTable.setItem(row, 1, QTableWidgetItem(formatted_time))

            self.sizeCompressed.setText(prettyByes(self.profile.repo.unique_csize))
            self.sizeDeduplicated.setText(prettyByes(self.profile.repo.unique_size))
            self.sizeOriginal.setText(prettyByes(self.profile.repo.total_size))
            self.repoEncryption.setText(str(self.profile.repo.encryption))
            self.snapshotTable.setRowCount(len(snapshots))

        header = self.snapshotTable.horizontalHeader()
        header.setVisible(True)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)

        self.snapshotTable.setSelectionBehavior(QTableView.SelectRows)
        self.snapshotTable.setEditTriggers(QTableView.NoEditTriggers)

        self.snapshotMountButton.clicked.connect(self.snapshot_mount)
        self.snapshotDeleteButton.clicked.connect(self.snapshot_mount)
        self.snapshotRefreshButton.clicked.connect(self.snapshot_mount)

    def snapshot_mount(self):
        cmd = ['borg', 'mount', '--log-json']
        row_selected = self.snapshotTable.selectionModel().selectedRows()
        if row_selected:
            snapshot_cell = self.snapshotTable.item(row_selected[0].row(), 0)
            if snapshot_cell:
                snapshot_name = snapshot_cell.text()
                cmd.append(f'{self.profile.repo.url}::{snapshot_name}')
            else:
                cmd.append(f'{self.profile.repo.url}')
        else:
            cmd.append(f'{self.profile.repo.url}')

        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly
        options |= QFileDialog.DontUseNativeDialog
        mountPoint = QFileDialog.getExistingDirectory(
            self, "Choose Mount Point", "", options=options)
        if mountPoint:
            cmd.append(mountPoint)

            self.set_status('Mounting snapshot into folder', 0)
            thread = BorgThread(self, cmd, {})
            thread.updated.connect(self.mount_update_log)
            thread.result.connect(self.mount_get_result)
            thread.start()

    def mount_update_log(self, text):
        self.mountErrors.setText(text)

    def mount_get_result(self, result):
        self.set_status(progress_max=100)
        if result['returncode'] == 0:
            self.set_status('Mounted successfully.')

    def init_compression(self):
        self.repoCompression.addItem('LZ4 (default)', 'lz4')
        self.repoCompression.addItem('Zstandard (medium)', 'zstd')
        self.repoCompression.addItem('LZMA (high)', 'lzma,6')
        self.repoCompression.setCurrentIndex(self.repoCompression.findData(self.profile.compression))
        self.repoCompression.currentIndexChanged.connect(self.compression_select_action)

    def compression_select_action(self, index):
        self.profile.compression = self.repoCompression.currentData()
        self.profile.save()

    def init_repo(self):
        self.repoSelector.model().item(0).setEnabled(False)
        self.repoSelector.addItem('Initialize New Repository', 'init')
        self.repoSelector.addItem('Add Existing Repository', 'existing')
        for repo in RepoModel.select():
            self.repoSelector.addItem(repo.url, repo.id)

        if self.profile.repo:
            self.repoSelector.setCurrentIndex(self.repoSelector.findData(self.profile.repo.id))
        self.repoSelector.currentIndexChanged.connect(self.repo_select_action)

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
            self.init_snapshots()

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

    def source_add(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly
        options |= QFileDialog.DontUseNativeDialog
        fileName = QFileDialog.getExistingDirectory(
            self, "Choose Backup Directory", "", options=options)
        if fileName:
            self.sourceDirectoriesWidget.addItem(fileName)
            new_source = SourceDirModel(dir=fileName)
            new_source.save()

    def source_remove(self):
        item = self.sourceDirectoriesWidget.takeItem(self.sourceDirectoriesWidget.currentRow())
        db_item = SourceDirModel.get(dir=item.text())
        db_item.delete_instance()
        item = None

    def menu_reset(self):
        reset_app()
        QApplication.instance().quit()
