from PyQt5 import uic, QtCore
from PyQt5.QtWidgets import QListWidgetItem, QApplication, QTableView, QHeaderView, QTableWidgetItem
from ..utils import get_asset, get_sorted_wifis
from ..models import EventLogModel, WifiSettingModel, BackupProfileMixin

uifile = get_asset('UI/scheduletab.ui')
ScheduleUI, ScheduleBase = uic.loadUiType(uifile, from_imports=True, import_from='vorta.views')


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

        self.scheduleApplyButton.clicked.connect(self.on_scheduler_apply)
        self.app.backup_finished_event.connect(self.init_logs)

        self.init_logs()
        self.populate_from_profile()

    def populate_from_profile(self):
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

        self._draw_next_scheduled_backup()
        self.init_wifi()

    def init_wifi(self):
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

    def init_logs(self):
        self.logTableWidget.setAlternatingRowColors(True)
        header = self.logTableWidget.horizontalHeader()
        header.setVisible(True)
        [header.setSectionResizeMode(i, QHeaderView.ResizeToContents) for i in range(5)]
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        self.logTableWidget.setSelectionBehavior(QTableView.SelectRows)
        self.logTableWidget.setEditTriggers(QTableView.NoEditTriggers)

        event_logs = [s for s in EventLogModel.select().order_by(EventLogModel.start_time.desc())]

        for row, log_line in enumerate(event_logs):
            self.logTableWidget.insertRow(row)
            formatted_time = log_line.start_time.strftime('%Y-%m-%d %H:%M')
            self.logTableWidget.setItem(row, 0, QTableWidgetItem(formatted_time))
            self.logTableWidget.setItem(row, 1, QTableWidgetItem(log_line.category))
            self.logTableWidget.setItem(row, 2, QTableWidgetItem(log_line.subcommand))
            self.logTableWidget.setItem(row, 3, QTableWidgetItem(log_line.repo_url))
            self.logTableWidget.setItem(row, 4, QTableWidgetItem(str(log_line.returncode)))
        self.logTableWidget.setRowCount(len(event_logs))
        self._draw_next_scheduled_backup()

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
