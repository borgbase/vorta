from PyQt5 import uic, QtCore
from PyQt5.QtWidgets import QListWidgetItem, QApplication, QTableView, QHeaderView, QTableWidgetItem
from ..utils import get_asset, get_sorted_wifis
from ..models import EventLogModel, WifiSettingModel, BackupProfileMixin

uifile = get_asset('UI/scheduletab.ui')
ScheduleUI, ScheduleBase = uic.loadUiType(uifile, from_imports=True, import_from='vorta.views')


class ScheduleTab(ScheduleBase, ScheduleUI, BackupProfileMixin):
    prune_intervals = ['hour', 'day', 'week', 'month', 'year']

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)
        self.app = QApplication.instance()

        # Set scheduler values
        self.schedulerRadioMapping = {
            'off': self.scheduleOffRadio,
            'interval': self.scheduleIntervalRadio,
            'fixed': self.scheduleFixedRadio
        }
        self.schedulerRadioMapping[self.profile.schedule_mode].setChecked(True)

        self.scheduleIntervalHours.setValue(self.profile.schedule_interval_hours)
        self.scheduleIntervalMinutes.setValue(self.profile.schedule_interval_minutes)
        self.scheduleFixedTime.setTime(
            QtCore.QTime(self.profile.schedule_fixed_hour, self.profile.schedule_fixed_minute))

        # Set checking options
        self.validationCheckBox.setCheckState(self.profile.validation_on)
        self.validationCheckBox.setTristate(False)
        self.validationSpinBox.setValue(self.profile.validation_weeks)

        # Set pruning options
        self.pruneCheckBox.setCheckState(self.profile.prune_on)
        for i in self.prune_intervals:
            getattr(self, f'prune_{i}').setValue(getattr(self.profile, f'prune_{i}'))

        self.scheduleApplyButton.clicked.connect(self.on_scheduler_apply)

        self.nextBackupDateTimeLabel.setText(self.app.scheduler.next_job)
        self.init_wifi()
        self.init_logs()

    def init_wifi(self):
        for wifi in get_sorted_wifis():
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
        db_item = WifiSettingModel.get(ssid=item.text(), profile=self.profile.id)
        db_item.allowed = item.checkState() == 2
        db_item.save()

    def init_logs(self):
        header = self.logTableWidget.horizontalHeader()
        header.setVisible(True)
        [header.setSectionResizeMode(i, QHeaderView.ResizeToContents) for i in range(5)]
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        self.logTableWidget.setSelectionBehavior(QTableView.SelectRows)
        self.logTableWidget.setEditTriggers(QTableView.NoEditTriggers)

        event_logs = [s for s in EventLogModel.select()]

        for row, log_line in enumerate(event_logs):
            self.logTableWidget.insertRow(row)
            formatted_time = log_line.start_time.strftime('%Y-%m-%d %H:%M')
            self.logTableWidget.setItem(row, 0, QTableWidgetItem(formatted_time))
            self.logTableWidget.setItem(row, 1, QTableWidgetItem(log_line.category))
            self.logTableWidget.setItem(row, 2, QTableWidgetItem(log_line.subcommand))
            self.logTableWidget.setItem(row, 3, QTableWidgetItem(log_line.message))
            self.logTableWidget.setItem(row, 4, QTableWidgetItem(str(log_line.returncode)))
        self.logTableWidget.setRowCount(len(event_logs))

    def on_scheduler_apply(self):
        profile = self.profile

        # Save checking options
        profile.validation_weeks = self.validationSpinBox.value()
        profile.validation_on = self.validationCheckBox.isChecked()

        # Save pruning options
        profile.prune_on = self.pruneCheckBox.isChecked()
        for i in self.prune_intervals:
            setattr(profile, f'prune_{i}', getattr(self, f'prune_{i}').value())

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
                self.nextBackupDateTimeLabel.setText(self.app.scheduler.next_job)
                self.nextBackupDateTimeLabel.repaint()
