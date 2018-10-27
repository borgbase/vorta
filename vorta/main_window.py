import os
import platform
from datetime import datetime as dt
from dateutil import parser
from PyQt5.QtWidgets import QApplication
from PyQt5 import uic

from .config import APP_NAME, remove_config
from .models import SnapshotModel, BackupProfileModel, SourceDirModel
from .borg_runner import BorgThread
from .repo_tab import RepoTab
from .source_tab import SourceTab
from .snapshots_tab import SnapshotTab


uifile = os.path.join(os.path.dirname(__file__), 'UI/mainwindow.ui')
MainWindowUI, MainWindowBase = uic.loadUiType(uifile)


class MainWindow(MainWindowBase, MainWindowUI):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle(APP_NAME)
        self.profile = BackupProfileModel.get(id=1)

        self.repoTab = RepoTab(self.repoTabSlot)
        self.repoTab.repo_changed.connect(lambda: self.snapshotTab.populate())

        self.sourceTab = SourceTab(self.sourceTabSlot)
        self.snapshotTab = SnapshotTab(self.snapshotTabSlot)

        self.createStartBtn.clicked.connect(self.create_action)
        self.actionResetApp.triggered.connect(self.menu_reset)

    def set_status(self, text=None, progress_max=None):
        if text:
            self.createProgressText.setText(text)
        if progress_max is not None:
            self.createProgress.setRange(0, progress_max)
        self.createProgressText.repaint()

    def create_action(self):
        n_backup_folders = SourceDirModel.select().count()
        if n_backup_folders == 0:
            self.set_status('Add some folders to back up first.')
            return
        self.set_status('Starting Backup.', progress_max=0)
        self.createStartBtn.setEnabled(False)
        self.createStartBtn.repaint()

        repo = self.profile.repo
        cmd = ['borg', 'create', '--list', '--info', '--log-json', '--json', '-C', self.profile.compression,
               f'{repo.url}::{platform.node()}-{dt.now().isoformat()}'
        ]
        for f in SourceDirModel.select():
            cmd.append(f.dir)

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
            self.set_status(progress_max=100)
            new_snapshot = SnapshotModel(
                snapshot_id=result['data']['archive']['id'],
                name=result['data']['archive']['name'],
                time=parser.parse(result['data']['archive']['start']),
                repo=self.profile.repo
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
            self.snapshotTab.populate()

    def menu_reset(self):
        remove_config()
        QApplication.instance().quit()
