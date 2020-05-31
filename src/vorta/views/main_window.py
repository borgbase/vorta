import sys

from PyQt5 import QtCore, uic
from PyQt5.QtWidgets import QShortcut, QMessageBox
from PyQt5.QtGui import QKeySequence

from vorta.borg.borg_thread import BorgThread
from vorta.i18n import trans_late
from vorta.models import BackupProfileModel, SettingsModel
from vorta.utils import borg_compat, get_asset, is_system_tray_available
from vorta.views.utils import get_colored_icon

from .archive_tab import ArchiveTab
from .misc_tab import MiscTab
from .profile_add_edit_dialog import AddProfileWindow, EditProfileWindow
from .repo_tab import RepoTab
from .schedule_tab import ScheduleTab
from .source_tab import SourceTab

uifile = get_asset('UI/mainwindow.ui')
MainWindowUI, MainWindowBase = uic.loadUiType(uifile)


class MainWindow(MainWindowBase, MainWindowUI):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle('Vorta for Borg Backup')
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.app = parent
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowMinimizeButtonHint)

        # Select previously used profile, if available
        prev_profile_id = SettingsModel.get(key='previous_profile_id')
        self.current_profile = BackupProfileModel.get_or_none(id=prev_profile_id.str_value)
        if self.current_profile is None:
            self.current_profile = BackupProfileModel.select().order_by('name').first()

        # Load tab models
        self.repoTab = RepoTab(self.repoTabSlot)
        self.sourceTab = SourceTab(self.sourceTabSlot)
        self.archiveTab = ArchiveTab(self.archiveTabSlot)
        self.scheduleTab = ScheduleTab(self.scheduleTabSlot)
        self.miscTab = MiscTab(self.miscTabSlot)
        self.miscTab.set_borg_details(borg_compat.version, borg_compat.path)
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
        for profile in BackupProfileModel.select().order_by(BackupProfileModel.name):
            self.profileSelector.addItem(profile.name, profile.id)
        current_profile_index = self.profileSelector.findData(self.current_profile.id)
        self.profileSelector.setCurrentIndex(current_profile_index)
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

        self.set_icons()

    def on_close_window(self):
        self.close()

    def set_icons(self):
        self.profileAddButton.setIcon(get_colored_icon('plus'))
        self.profileRenameButton.setIcon(get_colored_icon('edit'))
        self.profileDeleteButton.setIcon(get_colored_icon('trash'))

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
        SettingsModel.update({SettingsModel.str_value: self.current_profile.id})\
            .where(SettingsModel.key == 'previous_profile_id')\
            .execute()

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
            msg = self.tr("Are you sure you want to delete profile '{}'?".format(to_delete.name))
            reply = QMessageBox.question(self, self.tr("Confirm deletion"),
                                         msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            if reply == QMessageBox.Yes:
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

    def closeEvent(self, event):
        if not is_system_tray_available():
            run_in_background = QMessageBox.question(self,
                                                     trans_late("MainWindow QMessagebox",
                                                                "Quit"),
                                                     trans_late("MainWindow QMessagebox",
                                                                "Should Vorta continue to run in the background?"),
                                                     QMessageBox.Yes | QMessageBox.No)
            if run_in_background == QMessageBox.No:
                self.app.quit()
        event.accept()
