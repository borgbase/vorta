import sys
import os
import platform
from datetime import datetime as dt
from PyQt5.QtWidgets import QApplication, QFileDialog, QTableWidgetItem, QTableView
from PyQt5 import uic, QtCore, QtGui

from .repo_add import AddRepoWindow, ExistingRepoWindow
from .repo_init import InitRepoWindow
from .ssh_add import SSHAddWindow
from .config import APP_NAME, reset_app
from .models import RepoModel, SourceDirModel, SnapshotModel, BackupProfileModel
from .ssh_keys import get_private_keys
from .borg_runner import BorgThread


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

    def create_action(self):
        repo_id = self.repoSelector.currentData()
        repo = RepoModel.get(id=repo_id)
        cmd = ['borg', 'create', '--log-json', '--json',
               f'{repo.url}::{platform.node()}-{dt.now().isoformat()}'
        ]
        for i in range(self.sourceDirectoriesWidget.count()):
            cmd.append(self.sourceDirectoriesWidget.item(i).text())
        self.createProgress.setRange(0, 0)
        thread = BorgThread(self, cmd, {})
        thread.updated.connect(self.create_update_log)
        thread.result.connect(self.create_get_result)
        thread.start()

    def create_update_log(self, text):
        self.createProgressText.setText(text)

    def create_get_result(self, result):
        self.createProgress.setRange(0, 100)
        print(result)
        if result['returncode'] == 0:
            self.createProgressText.setText('Finished backup.')
            new_snapshot = SnapshotModel(
                name=result['data']['archive']['name'],
                time=result['data']['archive']['start'],
                repo=self.repoSelector.currentData()
            )

    def init_repo(self):
        self.repoSelector.model().item(0).setEnabled(False)
        self.repoSelector.addItem('Initialize New Repository', 'init')
        self.repoSelector.addItem('Add Existing Repository', 'existing')
        for repo in RepoModel.select():
            self.repoSelector.addItem(repo.url, repo.id)

        if self.profile.repo:
            self.repoSelector.setCurrentIndex(self.repoSelector.findData(self.profile.repo.id))
        self.repoSelector.currentIndexChanged.connect(self.repo_select_action)

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
        snapshots = [s for s in SnapshotModel.select()]
        self.snapshotTable.setRowCount(len(snapshots))

        for row, snapshot in enumerate(snapshots):
            self.snapshotTable.insertRow(row)
            self.snapshotTable.setItem(row, 0, QTableWidgetItem(snapshot.name))
            self.snapshotTable.setItem(row, 1, QTableWidgetItem(snapshot.time))
        self.snapshotTable.resizeColumnsToContents()
        self.snapshotTable.horizontalHeader().setVisible(True)
        self.snapshotTable.setSelectionBehavior(QTableView.SelectRows)
        self.snapshotTable.setEditTriggers(QTableView.NoEditTriggers)

    def init_compression(self):
        self.repoCompression.addItem('LZ4 (default)', 'lz4')
        self.repoCompression.addItem('Zstandard (medium)', 'zstd')
        self.repoCompression.addItem('LZMA (high)', 'lzma,6')

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

                init_window = InitRepoWindow(cmd, params)
                init_window.setParent(self, QtCore.Qt.Sheet)
                init_window.show()
                init_window._thread.start()
                init_window._thread.result.connect(self.repo_add_result)
        else:
            self.profile.repo = self.repoSelector.currentData()
            self.profile.save()

    def repo_add_result(self, result):
        print(result)
        if result['returncode'] == 0:
            new_repo, _ = RepoModel.get_or_create(
                url=result['params']['repo_url'],
                defaults={
                    'password': result['params']['password'],
                    'encryption': 'na'
                }
            )
            new_repo.save()

            if 'archives' in result['data'].keys():
                for snapshot in result['data']['archives']:
                    new_snapshot, _ = SnapshotModel.get_or_create(
                        id=snapshot['id'],
                        defaults={
                            'repo': new_repo.id,
                            'name': snapshot['name'],
                            'time': snapshot['time']
                        }
                    )
                    new_snapshot.save()
            self.repoSelector.addItem(new_repo.url, new_repo.id)
            self.repoSelector.setCurrentIndex(self.repoSelector.count()-1)

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
