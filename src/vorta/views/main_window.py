from PyQt5.QtWidgets import QShortcut
from PyQt5 import uic
from PyQt5.QtGui import QKeySequence
from ..config import APP_NAME
from .repo_tab import RepoTab
from .source_tab import SourceTab
from .snapshots_tab import SnapshotTab
from .schedule_tab import ScheduleTab
from ..utils import get_asset
from ..borg_runner import BorgThread


uifile = get_asset('UI/mainwindow.ui')
MainWindowUI, MainWindowBase = uic.loadUiType(uifile, from_imports=True, import_from='vorta.views')


class MainWindow(MainWindowBase, MainWindowUI):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle(APP_NAME)
        self.app = parent

        # Load tab models
        self.repoTab = RepoTab(self.repoTabSlot)
        self.sourceTab = SourceTab(self.sourceTabSlot)
        self.snapshotTab = SnapshotTab(self.snapshotTabSlot)
        self.scheduleTab = ScheduleTab(self.scheduleTabSlot)

        self.repoTab.repo_changed.connect(lambda: self.snapshotTab.populate())
        self.createStartBtn.clicked.connect(self.backup_start)
        self.cancelButton.clicked.connect(self.backup_cancel)

        QShortcut(QKeySequence("Ctrl+W"), self).activated.connect(self.on_close_window)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.on_close_window)

        # Connect to existing thread.
        if BorgThread.is_running():
            self.createStartBtn.setEnabled(False)
            self.cancelButton.setEnabled(True)
            self.set_status('Backup in progress.', progress_max=0)

    def on_close_window(self):
        self.close()

    def set_status(self, text=None, progress_max=None):
        if text:
            self.createProgressText.setText(text)
        if progress_max is not None:
            self.createProgress.setRange(0, progress_max)
        self.createProgressText.repaint()

    def backup_start(self):
        msg = self.app.create_backup()
        if msg['ok']:
            self.set_status(msg['message'], progress_max=0)
            self.createStartBtn.setEnabled(False)
            self.createStartBtn.repaint()
            self.app.backup_done.connect(self.backup_done)
            self.app.backup_log.connect(self.create_update_log)
        else:
            self.set_status(msg['message'])

    def create_update_log(self, text):
        self.set_status(text)

    def backup_cancel(self):
        self.app.cancel_backup()
        self.createStartBtn.setEnabled(True)
        self.createStartBtn.repaint()
        self.set_status(progress_max=100)
        self.set_status('Backup cancelled')


    def backup_done(self):
        self.createStartBtn.setEnabled(True)
        self.createStartBtn.repaint()
        self.set_status(progress_max=100)
        self.snapshotTab.populate()
