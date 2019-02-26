import sys
from PyQt5.QtWidgets import QShortcut
from PyQt5 import uic, QtCore
from PyQt5.QtGui import QKeySequence
from .repo_tab import RepoTab
from .source_tab import SourceTab
from .archive_tab import ArchiveTab
from .schedule_tab import ScheduleTab
from .misc_tab import MiscTab
from .profile_add_edit_dialog import AddProfileWindow, EditProfileWindow
from ..utils import get_asset
from ..models import BackupProfileModel
from vorta.borg.borg_thread import BorgThread
from vorta.views.utils import get_theme_class


uifile = get_asset('UI/mainwindow.ui')
MainWindowUI, MainWindowBase = uic.loadUiType(uifile, from_imports=True, import_from=get_theme_class())


class MainWindow(MainWindowBase, MainWindowUI):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle('Vorta for Borg Backup')
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.app = parent
        self.current_profile = BackupProfileModel.select().order_by('id').first()
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowMinimizeButtonHint)

        # Load tab models
        self.repoTab = RepoTab(self.repoTabSlot)
        self.sourceTab = SourceTab(self.sourceTabSlot)
        self.archiveTab = ArchiveTab(self.archiveTabSlot)
        self.scheduleTab = ScheduleTab(self.scheduleTabSlot)
        self.miscTabSlot = MiscTab(self.miscTabSlot)
        self.tabWidget.setCurrentIndex(0)

        self.repoTab.repo_changed.connect(self.archiveTab.populate_from_profile)
        self.repoTab.repo_added.connect(self.archiveTab.list_action)
        self.tabWidget.currentChanged.connect(self.scheduleTab._draw_next_scheduled_backup)

        self.createStartBtn.clicked.connect(self.app.create_backup_action)
        self.cancelButton.clicked.connect(self.app.backup_cancelled_event.emit)

        QShortcut(QKeySequence("Ctrl+W"), self).activated.connect(self.on_close_window)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.on_close_window)

        self.app.backup_started_event.connect(self.backup_started_event)
        self.app.backup_finished_event.connect(self.backup_finished_event)
        self.app.backup_log_event.connect(self.set_status)
        self.app.backup_cancelled_event.connect(self.backup_cancelled_event)

        # Init profile list
        for profile in BackupProfileModel.select():
            self.profileSelector.addItem(profile.name, profile.id)
        self.profileSelector.setCurrentIndex(0)
        self.profileSelector.currentIndexChanged.connect(self.profile_select_action)
        self.profileRenameButton.clicked.connect(self.profile_rename_action)
        self.profileDeleteButton.clicked.connect(self.profile_delete_action)
        self.profileAddButton.clicked.connect(self.profile_add_action)

        # OS-specific startup options:
        if sys.platform != 'darwin':
            # Hide Wifi-rule section in schedule tab.
            self.scheduleTab.wifiListLabel.hide()
            self.scheduleTab.wifiListWidget.hide()
            self.scheduleTab.page_2.hide()
            self.scheduleTab.toolBox.removeItem(1)

        # Connect to existing thread.
        if BorgThread.is_running():
            self.createStartBtn.setEnabled(False)
            self.cancelButton.setEnabled(True)
            self.set_status(self.tr('Backup in progress.'), progress_max=0)

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

    def profile_select_action(self, index):
        self.current_profile = BackupProfileModel.get(id=self.profileSelector.currentData())
        self.archiveTab.populate_from_profile()
        self.repoTab.populate_from_profile()
        self.sourceTab.populate_from_profile()
        self.scheduleTab.populate_from_profile()

    def profile_rename_action(self):
        window = EditProfileWindow(rename_existing_id=self.profileSelector.currentData())
        window.setParent(self, QtCore.Qt.Sheet)
        window.show()
        if window.exec_():
            self.profileSelector.setItemText(self.profileSelector.currentIndex(), window.edited_profile.name)

    def profile_delete_action(self):
        if self.profileSelector.count() > 1:
            to_delete = BackupProfileModel.get(id=self.profileSelector.currentData())

            # Remove pending background jobs
            to_delete_id = str(to_delete.id)
            if self.app.scheduler.get_job(to_delete_id):
                self.app.scheduler.remove_job(to_delete_id)

            to_delete.delete_instance(recursive=True)
            self.profileSelector.removeItem(self.profileSelector.currentIndex())
            self.profile_select_action(0)

    def profile_add_action(self):
        window = AddProfileWindow()
        window.setParent(self, QtCore.Qt.Sheet)
        window.show()
        if window.exec_() and window.edited_profile:
            self.profileSelector.addItem(window.edited_profile.name, window.edited_profile.id)
            self.profileSelector.setCurrentIndex(self.profileSelector.count() - 1)
        else:
            self.profileSelector.setCurrentIndex(self.profileSelector.currentIndex())

    def backup_started_event(self):
        self.set_status(progress_max=0)
        self._toggle_buttons(create_enabled=False)

    def backup_finished_event(self):
        self.set_status(progress_max=100)
        self._toggle_buttons(create_enabled=True)
        self.archiveTab.populate_from_profile()
        self.repoTab.init_repo_stats()

    def backup_cancelled_event(self):
        self._toggle_buttons(create_enabled=True)
        self.set_status(progress_max=100)
        self.set_status(self.tr('Task cancelled'))
