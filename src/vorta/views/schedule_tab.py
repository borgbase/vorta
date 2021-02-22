from PyQt5 import uic, QtCore
from PyQt5.QtWidgets import QListWidgetItem, QApplication, QTableView, QHeaderView, QTableWidgetItem
from vorta.utils import get_asset, get_sorted_wifis
from vorta.models import EventLogModel, WifiSettingModel, BackupProfileMixin
from vorta.views.utils import get_colored_icon

uifile = get_asset('UI/scheduletab.ui')
ScheduleUI, ScheduleBase = uic.loadUiType(uifile)


class LogTableColumn:
    Time = 0
    Category = 1
    Subcommand = 2
    Repository = 3
    ReturnCode = 4


class ScheduleTab(ScheduleBase, ScheduleUI, BackupProfileMixin):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)
        self.app = QApplication.instance()
        self.toolBox.setCurrentIndex(0)

        self.schedulerRadioMapping = {
            'off': self.scheduleOffRadio,
            'interval': self.scheduleIntervalRadio,
            'fixed': self.scheduleFixedRadio
        }

        # Set up log table
        self.logTableWidget.setAlternatingRowColors(True)
        header = self.logTableWidget.horizontalHeader()
        header.setVisible(True)
        [header.setSectionResizeMode(i, QHeaderView.ResizeToContents) for i in range(5)]
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        self.logTableWidget.setSelectionBehavior(QTableView.SelectRows)
        self.logTableWidget.setEditTriggers(QTableView.NoEditTriggers)

        # Populate with data
        self.populate_from_profile()
        self.set_icons()

        # Connect events
        self.scheduleApplyButton.clicked.connect(self.on_scheduler_apply)
        self.app.backup_finished_event.connect(self.populate_logs)
        self.dontRunOnMeteredNetworksCheckBox.stateChanged.connect(
            lambda new_val, attr='dont_run_on_metered_networks': self.save_profile_attr(attr, new_val))
        self.postBackupCmdLineEdit.textEdited.connect(
            lambda new_val, attr='post_backup_cmd': self.save_profile_attr(attr, new_val))
        self.preBackupCmdLineEdit.textEdited.connect(
            lambda new_val, attr='pre_backup_cmd': self.save_profile_attr(attr, new_val))
        self.createCmdLineEdit.textEdited.connect(
            lambda new_val, attr='create_backup_cmd': self.save_repo_attr(attr, new_val))

    def set_icons(self):
        self.toolBox.setItemIcon(0, get_colored_icon('clock-o'))
        self.toolBox.setItemIcon(1, get_colored_icon('wifi'))
        self.toolBox.setItemIcon(2, get_colored_icon('tasks'))
        self.toolBox.setItemIcon(3, get_colored_icon('terminal'))

    def populate_from_profile(self):
        """Populate current view with data from selected profile."""
        profile = self.profile()
        self.schedulerRadioMapping[profile.schedule_mode].setChecked(True)

        self.scheduleIntervalHours.setValue(profile.schedule_interval_hours)
        self.scheduleIntervalMinutes.setValue(profile.schedule_interval_minutes)
        self.scheduleFixedTime.setTime(
            QtCore.QTime(profile.schedule_fixed_hour, profile.schedule_fixed_minute))

        # Set checking options
        self.validationCheckBox.setCheckState(profile.validation_on)
        self.validationSpinBox.setValue(profile.validation_weeks)

        self.pruneCheckBox.setCheckState(profile.prune_on)
        self.validationCheckBox.setTristate(False)
        self.pruneCheckBox.setTristate(False)

        self.dontRunOnMeteredNetworksCheckBox.setChecked(profile.dont_run_on_metered_networks)

        self.preBackupCmdLineEdit.setText(profile.pre_backup_cmd)
        self.postBackupCmdLineEdit.setText(profile.post_backup_cmd)
        if profile.repo:
            self.createCmdLineEdit.setText(profile.repo.create_backup_cmd)
            self.createCmdLineEdit.setEnabled(True)
        else:
            self.createCmdLineEdit.setEnabled(False)

        self._draw_next_scheduled_backup()
        self.populate_wifi()
        self.populate_logs()

    def populate_wifi(self):
        self.wifiListWidget.clear()
        for wifi in get_sorted_wifis(self.profile()):
            item = QListWidgetItem()
            item.setText(wifi.ssid)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            if wifi.allowed:
                item.setCheckState(QtCore.Qt.Checked)
            else:
                item.setCheckState(QtCore.Qt.Unchecked)
            self.wifiListWidget.addItem(item)
        self.wifiListWidget.itemChanged.connect(self.save_wifi_item)

    def save_wifi_item(self, item):
        db_item = WifiSettingModel.get(ssid=item.text(), profile=self.profile().id)
        db_item.allowed = item.checkState() == 2
        db_item.save()

    def save_profile_attr(self, attr, new_value):
        profile = self.profile()
        setattr(profile, attr, new_value)
        profile.save()

    def save_repo_attr(self, attr, new_value):
        repo = self.profile().repo
        setattr(repo, attr, new_value)
        repo.save()

    def populate_logs(self):
        event_logs = [s for s in EventLogModel.select().order_by(EventLogModel.start_time.desc())]

        sorting = self.logTableWidget.isSortingEnabled()
        self.logTableWidget.setSortingEnabled(False)        # disable sorting while modifying the table.
        self.logTableWidget.setRowCount(len(event_logs))    # go ahead and set table length and then update the rows
        for row, log_line in enumerate(event_logs):
            formatted_time = log_line.start_time.strftime('%Y-%m-%d %H:%M')
            self.logTableWidget.setItem(row, LogTableColumn.Time, QTableWidgetItem(formatted_time))
            self.logTableWidget.setItem(row, LogTableColumn.Category, QTableWidgetItem(log_line.category))
            self.logTableWidget.setItem(row, LogTableColumn.Subcommand, QTableWidgetItem(log_line.subcommand))
            self.logTableWidget.setItem(row, LogTableColumn.Repository, QTableWidgetItem(log_line.repo_url))
            self.logTableWidget.setItem(row, LogTableColumn.ReturnCode, QTableWidgetItem(str(log_line.returncode)))
        self.logTableWidget.setSortingEnabled(sorting)      # restore sorting now that modifications are done

    def _draw_next_scheduled_backup(self):
        self.nextBackupDateTimeLabel.setText(self.app.scheduler.next_job_for_profile(self.profile().id))
        self.nextBackupDateTimeLabel.repaint()

    def on_scheduler_apply(self):
        profile = self.profile()

        # Save checking options
        profile.validation_weeks = self.validationSpinBox.value()
        profile.validation_on = self.validationCheckBox.isChecked()
        profile.prune_on = self.pruneCheckBox.isChecked()

        # Save scheduler timing and activate if needed.
        for label, obj in self.schedulerRadioMapping.items():
            if obj.isChecked():
                profile.schedule_mode = label
                profile.schedule_interval_hours = self.scheduleIntervalHours.value()
                profile.schedule_interval_minutes = self.scheduleIntervalMinutes.value()
                qtime = self.scheduleFixedTime.time()
                profile.schedule_fixed_hour, profile.schedule_fixed_minute = qtime.hour(), qtime.minute()
                profile.save()
                self.app.scheduler.reload()
                self._draw_next_scheduled_backup()
