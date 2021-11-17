from PyQt5 import uic, QtCore
from PyQt5.QtWidgets import QListWidgetItem, QApplication, QTableView, QHeaderView, QTableWidgetItem
from vorta.utils import get_asset, get_sorted_wifis
from vorta.store.models import EventLogModel, WifiSettingModel, BackupProfileMixin
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

        # Scheduler intervals we know
        self.scheduleIntervalUnit.addItem(self.tr('Minutes'), 'minutes')
        self.scheduleIntervalUnit.addItem(self.tr('Hours'), 'hours')
        self.scheduleIntervalUnit.addItem(self.tr('Days'), 'days')
        self.scheduleIntervalUnit.addItem(self.tr('Weeks'), 'weeks')

        # Populate with data
        self.populate_from_profile()
        self.set_icons()

        # Connect events
        self.app.backup_finished_event.connect(self.populate_logs)

        # Scheduler events
        for label, obj in self.schedulerRadioMapping.items():
            obj.clicked.connect(self.on_scheduler_change)
        self.scheduleIntervalCount.valueChanged.connect(self.on_scheduler_change)
        self.scheduleIntervalUnit.currentIndexChanged.connect(self.on_scheduler_change)
        self.scheduleFixedTime.timeChanged.connect(self.on_scheduler_change)

        # Network and shell commands events
        self.dontRunOnMeteredNetworksCheckBox.stateChanged.connect(
            lambda new_val, attr='dont_run_on_metered_networks': self.save_profile_attr(attr, new_val))
        self.postBackupCmdLineEdit.textEdited.connect(
            lambda new_val, attr='post_backup_cmd': self.save_profile_attr(attr, new_val))
        self.preBackupCmdLineEdit.textEdited.connect(
            lambda new_val, attr='pre_backup_cmd': self.save_profile_attr(attr, new_val))
        self.createCmdLineEdit.textEdited.connect(
            lambda new_val, attr='create_backup_cmd': self.save_repo_attr(attr, new_val))
        self.missedBackupsCheckBox.stateChanged.connect(
            lambda new_val, attr='schedule_make_up_missed': self.save_profile_attr(attr, new_val))
        self.pruneCheckBox.stateChanged.connect(
            lambda new_val, attr='prune_on': self.save_profile_attr(attr, new_val))
        self.validationCheckBox.stateChanged.connect(
            lambda new_val, attr='validation_on': self.save_profile_attr(attr, new_val))
        self.validationWeeksCount.valueChanged.connect(
            lambda new_val, attr='validation_weeks': self.save_profile_attr(attr, new_val))

    def on_scheduler_change(self, _):
        profile = self.profile()
        # Save scheduler settings, apply new scheduler and display next task for profile.
        for label, obj in self.schedulerRadioMapping.items():
            if obj.isChecked():
                profile.schedule_mode = label
                profile.schedule_interval_unit = self.scheduleIntervalUnit.currentData()
                profile.schedule_interval_count = self.scheduleIntervalCount.value()
                qtime = self.scheduleFixedTime.time()
                profile.schedule_fixed_hour, profile.schedule_fixed_minute = qtime.hour(), qtime.minute()
                profile.save()

        self.app.scheduler.set_timer_for_profile(profile.id)
        self.draw_next_scheduled_backup()

    def set_icons(self):
        self.toolBox.setItemIcon(0, get_colored_icon('clock-o'))
        self.toolBox.setItemIcon(1, get_colored_icon('wifi'))
        self.toolBox.setItemIcon(2, get_colored_icon('tasks'))
        self.toolBox.setItemIcon(3, get_colored_icon('terminal'))

    def populate_from_profile(self):
        """Populate current view with data from selected profile."""
        profile = self.profile()
        self.schedulerRadioMapping[profile.schedule_mode].setChecked(True)

        # Set interval scheduler options
        self.scheduleIntervalUnit.setCurrentIndex(
            self.scheduleIntervalUnit.findData(profile.schedule_interval_unit))
        self.scheduleIntervalCount.setValue(profile.schedule_interval_count)

        # Set fixed daily time scheduler options
        self.scheduleFixedTime.setTime(
            QtCore.QTime(profile.schedule_fixed_hour, profile.schedule_fixed_minute))

        # Set borg-check options
        self.validationCheckBox.setCheckState(QtCore.Qt.Checked if profile.validation_on else QtCore.Qt.Unchecked)
        self.validationWeeksCount.setValue(profile.validation_weeks)

        # Other checkbox options
        self.pruneCheckBox.setCheckState(
            QtCore.Qt.Checked if profile.prune_on else QtCore.Qt.Unchecked)
        self.missedBackupsCheckBox.setCheckState(
            QtCore.Qt.Checked if profile.schedule_make_up_missed else QtCore.Qt.Unchecked)
        self.dontRunOnMeteredNetworksCheckBox.setChecked(
            QtCore.Qt.Checked if profile.dont_run_on_metered_networks else QtCore.Qt.Unchecked)

        self.preBackupCmdLineEdit.setText(profile.pre_backup_cmd)
        self.postBackupCmdLineEdit.setText(profile.post_backup_cmd)
        if profile.repo:
            self.createCmdLineEdit.setText(profile.repo.create_backup_cmd)
            self.createCmdLineEdit.setEnabled(True)
        else:
            self.createCmdLineEdit.setEnabled(False)

        self.populate_wifi()
        self.populate_logs()

    def draw_next_scheduled_backup(self):
        self.nextBackupDateTimeLabel.setText(self.app.scheduler.next_job_for_profile(self.profile().id))
        self.nextBackupDateTimeLabel.repaint()

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
