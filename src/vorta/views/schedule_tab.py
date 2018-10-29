from PyQt5 import uic, QtCore
from PyQt5.QtWidgets import QListWidgetItem, QApplication, QTableView, QHeaderView, QTableWidgetItem
from ..utils import get_asset, get_sorted_wifis
from ..scheduler import init_scheduler
from ..models import EventLogModel

uifile = get_asset('UI/scheduletab.ui')
ScheduleUI, ScheduleBase = uic.loadUiType(uifile)

class ScheduleTab(ScheduleBase, ScheduleUI):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)
        self.profile = self.window().profile
        self.app = QApplication.instance()

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

        self.scheduleApplyButton.clicked.connect(self.on_scheduler_apply)

        self.set_next_backup_datetime()
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

    def set_next_backup_datetime(self):
        if self.app.scheduler is not None:
            job = self.app.scheduler.get_job('create-backup')
            self.nextBackupDateTimeLabel.setText(job.next_run_time.strftime('%Y-%m-%d %H:%M'))
        else:
            self.nextBackupDateTimeLabel.setText('Off')
        self.nextBackupDateTimeLabel.repaint()

    def on_scheduler_apply(self):
        for label, obj in self.schedulerRadioMapping.items():
            if obj.isChecked():
                self.profile.schedule_mode = label
                self.profile.schedule_interval_hours = self.scheduleIntervalHours.value()
                self.profile.schedule_interval_minutes = self.scheduleIntervalMinutes.value()
                qtime = self.scheduleFixedTime.time()
                self.profile.schedule_fixed_hour, self.profile.schedule_fixed_minute = qtime.hour(), qtime.minute()
                self.profile.save()
                self.app.scheduler = init_scheduler()
                self.set_next_backup_datetime()



    def init_log(self):
        pass
