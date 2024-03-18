import logging
from pathlib import Path

from PyQt6 import QtCore, uic
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QFontMetrics, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QListWidgetItem,
    QMessageBox,
    QToolTip,
)

from vorta.profile_export import ImportFailedException, ProfileExport
from vorta.store.models import BackupProfileModel, SettingsModel
from vorta.utils import (
    borg_compat,
    get_asset,
    get_network_status_monitor,
    is_system_tray_available,
)
from vorta.views.partials.loading_button import LoadingButton
from vorta.views.utils import get_colored_icon

from .about_tab import AboutTab
from .archive_tab import ArchiveTab
from .export_window import ExportWindow
from .import_window import ImportWindow
from .misc_tab import MiscTab
from .profile_add_edit_dialog import AddProfileWindow, EditProfileWindow
from .repo_tab import RepoTab
from .schedule_tab import ScheduleTab
from .source_tab import SourceTab

uifile = get_asset('UI/mainwindow.ui')
MainWindowUI, MainWindowBase = uic.loadUiType(uifile)

logger = logging.getLogger(__name__)


class MainWindow(MainWindowBase, MainWindowUI):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle('Vorta for Borg Backup')
        self.app = parent
        self.setWindowIcon(get_colored_icon("icon"))
        self.setWindowFlags(QtCore.Qt.WindowType.WindowCloseButtonHint | QtCore.Qt.WindowType.WindowMinimizeButtonHint)
        self.createStartBtn = LoadingButton(self.tr("Start Backup"))
        self.gridLayout.addWidget(self.createStartBtn, 0, 0, 1, 1)
        self.createStartBtn.setGif(get_asset("icons/loading"))

        # set log label height to two lines
        fontmetrics: QFontMetrics = self.logText.fontMetrics()
        self.logText.setMinimumHeight(fontmetrics.lineSpacing() * 2 + fontmetrics.leading())

        # Use previous window state
        previous_window_width = SettingsModel.get(key='previous_window_width')
        previous_window_height = SettingsModel.get(key='previous_window_height')
        self.resize(int(previous_window_width.str_value), int(previous_window_height.str_value))

        # Select previously used profile, if available
        prev_profile_id = SettingsModel.get(key='previous_profile_id')
        self.current_profile = BackupProfileModel.get_or_none(id=prev_profile_id.str_value)
        if self.current_profile is None:
            self.current_profile = BackupProfileModel.select().order_by('name').first()

        # Load tab models
        self.repoTab = RepoTab(self.repoTabSlot)
        self.sourceTab = SourceTab(self.sourceTabSlot)
        self.archiveTab = ArchiveTab(self.archiveTabSlot, app=self.app)
        self.scheduleTab = ScheduleTab(self.scheduleTabSlot)
        self.miscTab = MiscTab(self.SettingsTabSlot)
        self.aboutTab = AboutTab(self.AboutTabSlot)
        self.aboutTab.set_borg_details(borg_compat.version, borg_compat.path)
        self.miscWidget.hide()
        self.tabWidget.setCurrentIndex(0)

        self.repoTab.repo_changed.connect(self.archiveTab.populate_from_profile)
        self.repoTab.repo_changed.connect(self.scheduleTab.populate_from_profile)
        self.repoTab.repo_added.connect(self.archiveTab.refresh_archive_list)
        self.miscTab.refresh_archive.connect(self.archiveTab.populate_from_profile)

        self.miscButton.clicked.connect(self.toggle_misc_visibility)
        self.createStartBtn.clicked.connect(self.app.create_backup_action)
        self.cancelButton.clicked.connect(self.app.backup_cancelled_event.emit)

        QShortcut(QKeySequence("Ctrl+W"), self).activated.connect(self.on_close_window)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.on_close_window)

        self.app.backup_started_event.connect(self.backup_started_event)
        self.app.backup_finished_event.connect(self.backup_finished_event)
        self.app.backup_log_event.connect(self.set_log)
        self.app.backup_progress_event.connect(self.set_progress)
        self.app.backup_cancelled_event.connect(self.backup_cancelled_event)

        # Init profile list
        self.populate_profile_selector()
        self.profileSelector.itemClicked.connect(self.profile_clicked_action)
        self.profileSelector.currentItemChanged.connect(self.profile_selection_changed_action)
        self.profileRenameButton.clicked.connect(self.profile_rename_action)
        self.profileExportButton.clicked.connect(self.profile_export_action)
        self.profileDeleteButton.clicked.connect(self.profile_delete_action)
        self.profileAddButton.addAction(self.tr("Create new profile"), self.profile_add_action)
        self.profileAddButton.addAction(self.tr("Import from file…"), self.profile_import_action)

        # OS-specific startup options:
        if not get_network_status_monitor().is_network_status_available():
            # Hide Wifi-rule section in schedule tab.
            self.scheduleTab.wifiListLabel.hide()
            self.scheduleTab.wifiListWidget.hide()
            self.scheduleTab.page_2.hide()
            self.scheduleTab.toolBox.removeItem(1)

        # Connect to existing thread.
        if self.app.jobs_manager.is_worker_running():
            self.createStartBtn.setEnabled(False)
            self.createStartBtn.start()
            self.cancelButton.setEnabled(True)

        # Connect to palette change
        QApplication.instance().paletteChanged.connect(lambda p: self.set_icons())

        self.set_icons()

    def on_close_window(self):
        self.close()

    def set_icons(self):
        self.profileAddButton.setIcon(get_colored_icon('plus'))
        self.profileRenameButton.setIcon(get_colored_icon('edit'))
        self.profileExportButton.setIcon(get_colored_icon('file-import-solid'))
        self.profileDeleteButton.setIcon(get_colored_icon('minus'))
        self.miscButton.setIcon(get_colored_icon('settings_wheel'))

    def set_progress(self, text=''):
        self.progressText.setText(text)
        self.progressText.repaint()

    def set_log(self, text=''):
        self.logText.setText(text)
        self.logText.repaint()

    def _toggle_buttons(self, create_enabled=True):
        if create_enabled:
            self.createStartBtn.stop()
        else:
            self.createStartBtn.start()
        self.createStartBtn.setEnabled(create_enabled)
        self.createStartBtn.repaint()
        self.cancelButton.setEnabled(not create_enabled)
        self.cancelButton.repaint()

    def populate_profile_selector(self):
        # Clear the previous entries
        self.profileSelector.clear()

        # Keep track of the current item to be selected (if any)
        current_item = None

        # Add items to the QListWidget
        for profile in BackupProfileModel.select().order_by(BackupProfileModel.name):
            item = QListWidgetItem(profile.name)
            item.setData(Qt.ItemDataRole.UserRole, profile.id)

            self.profileSelector.addItem(item)

            if profile.id == self.current_profile.id:
                current_item = item

        # Set the current profile as selected
        if current_item:
            self.profileSelector.setCurrentItem(current_item)

    def profile_selection_changed_action(self, index):
        profile = self.profileSelector.currentItem()
        backup_profile_id = profile.data(Qt.ItemDataRole.UserRole) if profile else None
        if not backup_profile_id:
            return
        self.current_profile = BackupProfileModel.get(id=backup_profile_id)
        self.archiveTab.populate_from_profile()
        self.repoTab.populate_from_profile()
        self.sourceTab.populate_from_profile()
        self.scheduleTab.populate_from_profile()
        SettingsModel.update({SettingsModel.str_value: self.current_profile.id}).where(
            SettingsModel.key == 'previous_profile_id'
        ).execute()
        self.archiveTab.toggle_compact_button_visibility()

    def profile_clicked_action(self):
        if self.miscWidget.isVisible():
            self.toggle_misc_visibility()

    def profile_rename_action(self):
        backup_profile_id = self.profileSelector.currentItem().data(Qt.ItemDataRole.UserRole)
        window = EditProfileWindow(rename_existing_id=backup_profile_id)
        self.window = window  # For tests
        window.setParent(self, QtCore.Qt.WindowType.Sheet)
        window.open()
        window.profile_changed.connect(self.profile_add_edit_result)
        window.rejected.connect(lambda: self.profileSelector.setCurrentIndex(self.profileSelector.currentIndex()))

    def profile_delete_action(self):
        if self.profileSelector.count() > 1:
            to_delete_id = self.profileSelector.currentItem().data(Qt.ItemDataRole.UserRole)
            to_delete = BackupProfileModel.get(id=to_delete_id)

            msg = self.tr("Are you sure you want to delete profile '{}'?".format(to_delete.name))
            reply = QMessageBox.question(
                self,
                self.tr("Confirm deletion"),
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                to_delete.delete_instance(recursive=True)
                self.app.scheduler.remove_job(to_delete_id)  # Remove pending jobs
                self.profileSelector.takeItem(self.profileSelector.currentRow())
                self.profile_selection_changed_action(0)

        else:
            warn = self.tr("Cannot delete the last profile.")
            point = QPoint(0, int(self.profileDeleteButton.size().height() / 2))
            QToolTip.showText(self.profileDeleteButton.mapToGlobal(point), warn)

    def profile_add_action(self):
        window = AddProfileWindow()
        self.window = window  # For tests
        window.setParent(self, QtCore.Qt.WindowType.Sheet)
        window.open()
        window.profile_changed.connect(self.profile_add_edit_result)
        window.rejected.connect(lambda: self.profileSelector.setCurrentIndex(self.profileSelector.currentIndex()))

    def profile_export_action(self):
        """
        React to pressing "Export Profile" button and save current
        profile as .json file.
        """
        window = ExportWindow(profile=self.current_profile.refresh())
        self.window = window
        window.setParent(self, QtCore.Qt.WindowType.Sheet)
        window.show()

    def profile_import_action(self):
        """
        React to "Import Profile". Ask to select a .json file and import it as
        new profile.
        """

        def profile_imported_event(profile):
            QMessageBox.information(
                None,
                self.tr('Profile import successful!'),
                self.tr('Profile {} imported.').format(profile.name),
            )
            self.repoTab.populate_from_profile()
            self.scheduleTab.populate_logs()
            self.scheduleTab.populate_wifi()
            self.miscTab.populate()
            self.populate_profile_selector()

        filename = QFileDialog.getOpenFileName(
            self,
            self.tr("Load profile"),
            str(Path.home()),
            self.tr("JSON (*.json);;All files (*)"),
        )[0]
        if filename:
            try:
                profile_export = ProfileExport.from_json(filename)
            except ImportFailedException as exception:
                QMessageBox.critical(None, self.tr('Failed to import profile'), str(exception))
                return
            window = ImportWindow(profile_export=profile_export)
            self.window = window
            window.setParent(self, QtCore.Qt.WindowType.Sheet)
            window.profile_imported.connect(profile_imported_event)
            window.show()

    def profile_add_edit_result(self, profile_name, profile_id):
        # Profile is renamed
        if self.profileSelector.currentItem().data(Qt.ItemDataRole.UserRole) == profile_id:
            self.profileSelector.currentItem().setText(profile_name)
        # Profile is added
        else:
            profile = QListWidgetItem(profile_name)
            profile.setData(Qt.ItemDataRole.UserRole, profile_id)
            self.profileSelector.addItem(profile)
            self.profileSelector.setCurrentItem(profile)

    def toggle_misc_visibility(self):
        if self.miscWidget.isVisible():
            self.miscWidget.hide()
            self.tabWidget.setCurrentIndex(0)
            self.miscButton.setStyleSheet("font-weight: normal;")
            self.tabWidget.show()
        else:
            self.tabWidget.hide()
            self.miscWidget.setCurrentIndex(0)
            self.miscButton.setStyleSheet("font-weight: bold;")
            self.miscWidget.show()

    def backup_started_event(self):
        self._toggle_buttons(create_enabled=False)
        self.archiveTab._toggle_all_buttons(enabled=False)
        self.set_log('')

    def backup_finished_event(self):
        self.archiveTab.populate_from_profile()
        self.repoTab.init_repo_stats()
        self.scheduleTab.populate_logs()

        if not self.app.jobs_manager.is_worker_running() and (
            self.archiveTab.remaining_refresh_archives == 0 or self.archiveTab.remaining_refresh_archives == 1
        ):  # Either the refresh is done or this is the last archive to refresh.
            self._toggle_buttons(create_enabled=True)
            self.archiveTab._toggle_all_buttons(enabled=True)

    def backup_cancelled_event(self):
        self._toggle_buttons(create_enabled=True)
        self.set_log(self.tr('Task cancelled'))
        self.archiveTab.cancel_action()

    def closeEvent(self, event):
        # Save window state in SettingsModel
        SettingsModel.update({SettingsModel.str_value: str(self.width())}).where(
            SettingsModel.key == 'previous_window_width'
        ).execute()
        SettingsModel.update({SettingsModel.str_value: str(self.height())}).where(
            SettingsModel.key == 'previous_window_height'
        ).execute()

        if not is_system_tray_available():
            if SettingsModel.get(key="enable_background_question").value:
                msg = QMessageBox()
                msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg.setParent(self, QtCore.Qt.WindowType.Sheet)
                msg.setText(self.tr("Should Vorta continue to run in the background?"))
                msg.button(QMessageBox.StandardButton.Yes).clicked.connect(
                    lambda: self.miscTab.save_setting("disable_background_state", True)
                )
                msg.button(QMessageBox.StandardButton.No).clicked.connect(
                    lambda: (
                        self.miscTab.save_setting("disable_background_state", False),
                        self.app.quit(),
                    )
                )
                msg.setWindowTitle(self.tr("Quit"))
                dont_show_box = QCheckBox(self.tr("Don't show this again"))
                dont_show_box.clicked.connect(lambda x: self.miscTab.save_setting("enable_background_question", not x))
                dont_show_box.setTristate(False)
                msg.setCheckBox(dont_show_box)
                msg.exec()
            elif not SettingsModel.get(key="disable_background_state").value:
                self.app.quit()
        event.accept()
