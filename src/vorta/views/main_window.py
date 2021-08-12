from pathlib import Path

from PyQt5 import QtCore, uic
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut, QMessageBox, QCheckBox, QMenu, QToolTip, QFileDialog

from vorta.borg.borg_thread import BorgThread
from vorta.models import BackupProfileModel, SettingsModel
from vorta.utils import borg_compat, get_asset, is_system_tray_available, get_network_status_monitor
from vorta.views.partials.loading_button import LoadingButton
from vorta.views.utils import get_colored_icon
from vorta.profile_export import ProfileExport, ImportFailedException
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


class MainWindow(MainWindowBase, MainWindowUI):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle('Vorta for Borg Backup')
        self.app = parent
        self.setWindowIcon(get_colored_icon("icon"))
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowMinimizeButtonHint)
        self.createStartBtn = LoadingButton(self.tr("Start Backup"))
        self.gridLayout.addWidget(self.createStartBtn, 0, 0, 1, 1)
        self.createStartBtn.setGif(get_asset("icons/loading"))

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
        self.miscTab = MiscTab(self.miscTabSlot)
        self.miscTab.set_borg_details(borg_compat.version, borg_compat.path)
        self.tabWidget.setCurrentIndex(0)

        self.repoTab.repo_changed.connect(self.archiveTab.populate_from_profile)
        self.repoTab.repo_changed.connect(self.scheduleTab.populate_from_profile)
        self.repoTab.repo_added.connect(self.archiveTab.list_action)
        self.tabWidget.currentChanged.connect(self.scheduleTab._draw_next_scheduled_backup)

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
        self.profileSelector.currentIndexChanged.connect(self.profile_select_action)
        self.profileRenameButton.clicked.connect(self.profile_rename_action)
        self.profileExportButton.clicked.connect(self.profile_export_action)
        self.profileDeleteButton.clicked.connect(self.profile_delete_action)
        profile_add_menu = QMenu()
        profile_add_menu.addAction(self.tr('Import from file...'), self.profile_import_action)
        self.profileAddButton.setMenu(profile_add_menu)
        self.profileAddButton.clicked.connect(self.profile_add_action)

        # OS-specific startup options:
        if not get_network_status_monitor().is_network_status_available():
            # Hide Wifi-rule section in schedule tab.
            self.scheduleTab.wifiListLabel.hide()
            self.scheduleTab.wifiListWidget.hide()
            self.scheduleTab.page_2.hide()
            self.scheduleTab.toolBox.removeItem(1)

        # Connect to existing thread.
        if BorgThread.is_running():
            self.createStartBtn.setEnabled(False)
            self.createStartBtn.start()
            self.cancelButton.setEnabled(True)

        self.set_icons()

    def on_close_window(self):
        self.close()

    def set_icons(self):
        self.profileAddButton.setIcon(get_colored_icon('plus'))
        self.profileRenameButton.setIcon(get_colored_icon('edit'))
        self.profileExportButton.setIcon(get_colored_icon('file-import-solid'))
        self.profileDeleteButton.setIcon(get_colored_icon('trash'))

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
        self.profileSelector.clear()
        for profile in BackupProfileModel.select().order_by(BackupProfileModel.name):
            self.profileSelector.addItem(profile.name, profile.id)
        current_profile_index = self.profileSelector.findData(self.current_profile.id)
        self.profileSelector.setCurrentIndex(current_profile_index)

    def profile_select_action(self, index):
        backup_profile_id = self.profileSelector.currentData()
        if not backup_profile_id:
            return
        self.current_profile = BackupProfileModel.get(id=backup_profile_id)
        self.archiveTab.populate_from_profile()
        self.repoTab.populate_from_profile()
        self.sourceTab.populate_from_profile()
        self.scheduleTab.populate_from_profile()
        SettingsModel.update({SettingsModel.str_value: self.current_profile.id}) \
            .where(SettingsModel.key == 'previous_profile_id') \
            .execute()

    def profile_rename_action(self):
        window = EditProfileWindow(rename_existing_id=self.profileSelector.currentData())
        self.window = window  # For tests
        window.setParent(self, QtCore.Qt.Sheet)
        window.open()
        window.profile_changed.connect(self.profile_add_edit_result)
        window.rejected.connect(lambda: self.profileSelector.setCurrentIndex(self.profileSelector.currentIndex()))

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

        else:
            warn = self.tr("Can't delete the last profile.")
            point = QPoint(0, self.profileDeleteButton.size().height() / 2)
            QToolTip.showText(self.profileDeleteButton.mapToGlobal(point), warn)

    def profile_add_action(self):
        window = AddProfileWindow()
        self.window = window  # For tests
        window.setParent(self, QtCore.Qt.Sheet)
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
        window.setParent(self, QtCore.Qt.Sheet)
        window.show()

    def profile_import_action(self):
        """
        React to "Import Profile". Ask to select a .json file and import it as
        new profile.
        """
        def profile_imported_event(profile):
            QMessageBox.information(None,
                                    self.tr('Profile import successful!'),
                                    self.tr('Profile {} imported.').format(profile.name))
            self.repoTab.populate_repositories()
            self.scheduleTab.populate_logs()
            self.scheduleTab.populate_wifi()
            self.miscTab.populate()
            self.populate_profile_selector()

        filename = QFileDialog.getOpenFileName(
            self,
            self.tr("Load profile"),
            str(Path.home()),
            self.tr("JSON (*.json);;All files (*)"))[0]
        if filename:
            try:
                profile_export = ProfileExport.from_json(filename)
            except ImportFailedException as exception:
                QMessageBox.critical(None,
                                     self.tr('Failed to import profile'),
                                     self.tr(str(exception)))
                return
            window = ImportWindow(profile_export=profile_export)
            self.window = window
            window.setParent(self, QtCore.Qt.Sheet)
            window.profile_imported.connect(profile_imported_event)
            window.show()

    def profile_add_edit_result(self, profile_name, profile_id):
        # Profile is renamed
        if self.profileSelector.currentData() == profile_id:
            self.profileSelector.setItemText(self.profileSelector.currentIndex(), profile_name)
        # Profile is added
        else:
            self.profileSelector.addItem(profile_name, profile_id)
            self.profileSelector.setCurrentIndex(self.profileSelector.count() - 1)

    def backup_started_event(self):
        self._toggle_buttons(create_enabled=False)
        self.archiveTab._toggle_all_buttons(enabled=False)
        self.set_log('')

    def backup_finished_event(self):
        self._toggle_buttons(create_enabled=True)
        self.archiveTab._toggle_all_buttons(enabled=True)
        self.archiveTab.populate_from_profile()
        self.repoTab.init_repo_stats()
        self.scheduleTab.populate_logs()

    def backup_cancelled_event(self):
        self._toggle_buttons(create_enabled=True)
        self.set_log(self.tr('Task cancelled'))
        self.archiveTab.cancel_action()

    def closeEvent(self, event):
        # Save window state in SettingsModel
        SettingsModel.update({SettingsModel.str_value: str(self.width())}) \
            .where(SettingsModel.key == 'previous_window_width') \
            .execute()
        SettingsModel.update({SettingsModel.str_value: str(self.height())}) \
            .where(SettingsModel.key == 'previous_window_height') \
            .execute()

        if not is_system_tray_available():
            if SettingsModel.get(key="enable_background_question").value:
                msg = QMessageBox()
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.setParent(self, QtCore.Qt.Sheet)
                msg.setText(self.tr("Should Vorta continue to run in the background?"))
                msg.button(QMessageBox.Yes).clicked.connect(
                    lambda: self.miscTab.save_setting("disable_background_state", True))
                msg.button(QMessageBox.No).clicked.connect(lambda: (self.miscTab.save_setting(
                    "disable_background_state", False), self.app.quit()))
                msg.setWindowTitle(self.tr("Quit"))
                dont_show_box = QCheckBox(self.tr("Don't show this again"))
                dont_show_box.clicked.connect(lambda x: self.miscTab.save_setting("enable_background_question", not x))
                dont_show_box.setTristate(False)
                msg.setCheckBox(dont_show_box)
                msg.exec()
            elif not SettingsModel.get(key="disable_background_state").value:
                self.app.quit()
        event.accept()
