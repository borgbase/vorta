from dateutil import parser
from PyQt5.QtWidgets import QApplication, QShortcut
from PyQt5 import uic
from PyQt5.QtGui import QKeySequence
from ..config import APP_NAME
from ..models import SnapshotModel, BackupProfileModel
from ..borg_runner import BorgThread
from .repo_tab import RepoTab
from .source_tab import SourceTab
from .snapshots_tab import SnapshotTab
from ..utils import get_relative_asset


uifile = get_relative_asset('UI/mainwindow.ui', __file__)
MainWindowUI, MainWindowBase = uic.loadUiType(uifile)


class MainWindow(MainWindowBase, MainWindowUI):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle(APP_NAME)
        self.profile = BackupProfileModel.get(id=1)
        self.app = QApplication.instance()

        self.repoTab = RepoTab(self.repoTabSlot)
        self.repoTab.repo_changed.connect(lambda: self.snapshotTab.populate())

        self.sourceTab = SourceTab(self.sourceTabSlot)
        self.snapshotTab = SnapshotTab(self.snapshotTabSlot)

        self.createStartBtn.clicked.connect(self.create_action)
        self.cancelButton.clicked.connect(self.cancel_create_action)

        QShortcut(QKeySequence("Ctrl+W"), self).activated.connect(self.on_close_window)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.on_close_window)

        # Connect to existing thread.
        if self.app.thread and self.app.thread.isRunning():
            self.createStartBtn.setEnabled(False)
            self.cancelButton.setEnabled(True)
            self.set_status('Connected to existing backup process.', progress_max=0)
            self.app.thread.updated.connect(self.create_update_log)
            self.app.thread.result.connect(self.create_get_result)

    def on_close_window(self):
        self.close()

    def set_status(self, text=None, progress_max=None):
        if text:
            self.createProgressText.setText(text)
        if progress_max is not None:
            self.createProgress.setRange(0, progress_max)
        self.createProgressText.repaint()

    def create_action(self):
        thread_msg = BorgThread.create_thread_factory()
        if thread_msg['ok']:
            self.set_status(thread_msg['message'], progress_max=0)
            self.createStartBtn.setEnabled(False)
            self.createStartBtn.repaint()
        thread = thread_msg['thread']
        thread.updated.connect(self.create_update_log)
        thread.result.connect(self.create_get_result)
        thread.start()

    def create_update_log(self, text):
        self.set_status(text)

    def cancel_create_action(self):
        try:
            self.app.thread.terminate()
            self.app.thread.wait()
            self.createStartBtn.setEnabled(True)
            self.createStartBtn.repaint()
            self.set_status(progress_max=100)
        except:
            pass

    def create_get_result(self, result):
        self.createStartBtn.setEnabled(True)
        self.createStartBtn.repaint()
        self.set_status(progress_max=100)
        if result['returncode'] == 0:
            new_snapshot, created = SnapshotModel.get_or_create(
                snapshot_id=result['data']['archive']['id'],
                defaults={
                    'name': result['data']['archive']['name'],
                    'time': parser.parse(result['data']['archive']['start']),
                    'repo': self.profile.repo
                }
            )
            new_snapshot.save()
            if 'cache' in result['data'] and created:
                stats = result['data']['cache']['stats']
                repo = self.profile.repo
                repo.total_size = stats['total_size']
                repo.unique_csize = stats['unique_csize']
                repo.unique_size = stats['unique_size']
                repo.total_unique_chunks = stats['total_unique_chunks']
                repo.save()
            self.snapshotTab.populate()

