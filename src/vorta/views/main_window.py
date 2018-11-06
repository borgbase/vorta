from PyQt5.QtWidgets import QShortcut
from PyQt5 import uic, QtCore
from PyQt5.QtGui import QKeySequence
from ..config import APP_NAME
from .repo_tab import RepoTab
from .source_tab import SourceTab
from .snapshots_tab import SnapshotTab
from .schedule_tab import ScheduleTab
from ..utils import get_asset
from vorta.borg.borg_thread import BorgThread


uifile = get_asset('UI/mainwindow.ui')
MainWindowUI, MainWindowBase = uic.loadUiType(uifile, from_imports=True, import_from='vorta.views')


class MainWindow(MainWindowBase, MainWindowUI):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle(APP_NAME)
        self.app = parent
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowMinimizeButtonHint)

        # Load tab models
        self.repoTab = RepoTab(self.repoTabSlot)
        self.sourceTab = SourceTab(self.sourceTabSlot)
        self.snapshotTab = SnapshotTab(self.snapshotTabSlot)
        self.scheduleTab = ScheduleTab(self.scheduleTabSlot)

        self.repoTab.repo_changed.connect(self.snapshotTab.populate)
        self.repoTab.repo_added.connect(self.snapshotTab.list_action)
        self.createStartBtn.clicked.connect(self.app.create_backup_action)
        self.cancelButton.clicked.connect(self.app.backup_cancelled_event.emit)

        QShortcut(QKeySequence("Ctrl+W"), self).activated.connect(self.on_close_window)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.on_close_window)

        self.app.backup_started_event.connect(self.backup_started_event)
        self.app.backup_finished_event.connect(self.backup_finished_event)
        self.app.backup_log_event.connect(self.set_status)
        self.app.backup_cancelled_event.connect(self.backup_cancelled_event)

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

    def _toggle_buttons(self, create_enabled=True):
        self.createStartBtn.setEnabled(create_enabled)
        self.createStartBtn.repaint()
        self.cancelButton.setEnabled(not create_enabled)
        self.cancelButton.repaint()

    def backup_started_event(self):
            self.set_status(progress_max=0)
            self._toggle_buttons(create_enabled=False)

    def backup_finished_event(self):
        self.set_status(progress_max=100)
        self._toggle_buttons(create_enabled=True)
        self.snapshotTab.populate()
        self.repoTab.init_repo_stats()

    def backup_cancelled_event(self):
        self._toggle_buttons(create_enabled=True)
        self.set_status(progress_max=100)
        self.set_status('Backup cancelled')

