from PyQt6 import QtCore, uic
from PyQt6.QtCore import QDateTime, QLocale
from PyQt6.QtWidgets import QApplication

from vorta.i18n import get_locale
from vorta.scheduler import ScheduleStatusType
from vorta.store.models import BackupProfileMixin
from vorta.utils import get_asset

uifile = get_asset('UI/schedule_page.ui')
SchedulePageUI, SchedulePageBase = uic.loadUiType(uifile)


class SchedulePage(SchedulePageBase, SchedulePageUI, BackupProfileMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app = QApplication.instance()
        self.setupUi(self)

        self.schedulerRadioMapping = {
            'off': self.scheduleOffRadio,
            'interval': self.scheduleIntervalRadio,
            'fixed': self.scheduleFixedRadio,
        }

        self.populate_from_profile()

        self.scheduleIntervalUnit.addItem(self.tr('Minutes'), 'minutes')
        self.scheduleIntervalUnit.addItem(self.tr('Hours'), 'hours')
        self.scheduleIntervalUnit.addItem(self.tr('Days'), 'days')
        self.scheduleIntervalUnit.addItem(self.tr('Weeks'), 'weeks')

        self.framePeriodic.setEnabled(False)
        self.frameDaily.setEnabled(False)
        self.frameValidation.setEnabled(False)
        self.frameCompaction.setEnabled(False)

        self.scheduleIntervalRadio.toggled.connect(self.framePeriodic.setEnabled)
        self.scheduleFixedRadio.toggled.connect(self.frameDaily.setEnabled)
        self.validationCheckBox.toggled.connect(self.frameValidation.setEnabled)
        self.compactionCheckBox.toggled.connect(self.frameCompaction.setEnabled)

        for label, obj in self.schedulerRadioMapping.items():
            obj.clicked.connect(self.on_scheduler_change)
        self.scheduleIntervalCount.valueChanged.connect(self.on_scheduler_change)
        self.scheduleIntervalUnit.currentIndexChanged.connect(self.on_scheduler_change)
        self.scheduleFixedTime.timeChanged.connect(self.on_scheduler_change)

        self.missedBackupsCheckBox.stateChanged.connect(
            lambda new_val, attr='schedule_make_up_missed': self.save_profile_attr(attr, new_val)
        )
        self.pruneCheckBox.stateChanged.connect(lambda new_val, attr='prune_on': self.save_profile_attr(attr, new_val))
        self.validationCheckBox.stateChanged.connect(
            lambda new_val, attr='validation_on': self.save_profile_attr(attr, new_val)
        )
        self.validationWeeksCount.valueChanged.connect(
            lambda new_val, attr='validation_weeks': self.save_profile_attr(attr, new_val)
        )
        self.compactionCheckBox.stateChanged.connect(
            lambda new_val, attr='compaction_on': self.save_profile_attr(attr, new_val)
        )
        self.compactionWeeksCount.valueChanged.connect(
            lambda new_val, attr='compaction_weeks': self.save_profile_attr(attr, new_val)
        )

        self.app.scheduler.schedule_changed.connect(lambda pid: self.draw_next_scheduled_backup())

    def on_scheduler_change(self, _):
        profile = self.profile()
        for label, obj in self.schedulerRadioMapping.items():
            if obj.isChecked():
                profile.schedule_mode = label
                profile.schedule_interval_unit = self.scheduleIntervalUnit.currentData()
                profile.schedule_interval_count = self.scheduleIntervalCount.value()
                qtime = self.scheduleFixedTime.time()
                profile.schedule_fixed_hour, profile.schedule_fixed_minute = (
                    qtime.hour(),
                    qtime.minute(),
                )
                profile.save()

        self.app.scheduler.set_timer_for_profile(profile.id)
        self.draw_next_scheduled_backup()

    def populate_from_profile(self):
        profile = self.profile()
        self.schedulerRadioMapping[profile.schedule_mode].setChecked(True)
        self.scheduleIntervalUnit.setCurrentIndex(self.scheduleIntervalUnit.findData(profile.schedule_interval_unit))
        self.scheduleIntervalCount.setValue(profile.schedule_interval_count)
        self.scheduleFixedTime.setTime(QtCore.QTime(profile.schedule_fixed_hour, profile.schedule_fixed_minute))

        self.validationCheckBox.setCheckState(
            QtCore.Qt.CheckState.Checked if profile.validation_on else QtCore.Qt.CheckState.Unchecked
        )
        self.validationWeeksCount.setValue(profile.validation_weeks)

        self.compactionCheckBox.setCheckState(
            QtCore.Qt.CheckState.Checked if profile.compaction_on else QtCore.Qt.CheckState.Unchecked
        )
        self.compactionWeeksCount.setValue(profile.compaction_weeks)

        self.pruneCheckBox.setCheckState(
            QtCore.Qt.CheckState.Checked if profile.prune_on else QtCore.Qt.CheckState.Unchecked
        )
        self.missedBackupsCheckBox.setCheckState(
            QtCore.Qt.CheckState.Checked if profile.schedule_make_up_missed else QtCore.Qt.CheckState.Unchecked
        )

        self.draw_next_scheduled_backup()

    def draw_next_scheduled_backup(self):
        status = self.app.scheduler.next_job_for_profile(self.profile().id)
        if status.type in (
            ScheduleStatusType.SCHEDULED,
            ScheduleStatusType.TOO_FAR_AHEAD,
        ):
            time = QDateTime.fromMSecsSinceEpoch(int(status.time.timestamp() * 1000))
            text = get_locale().toString(time, QLocale.FormatType.LongFormat)
        elif status.type == ScheduleStatusType.NO_PREVIOUS_BACKUP:
            text = self.tr('Run a manual backup first')
        else:
            text = self.tr('None scheduled')

        self.nextBackupDateTimeLabel.setText(text)
        self.nextBackupDateTimeLabel.repaint()

    def save_profile_attr(self, attr, new_value):
        profile = self.profile()
        setattr(profile, attr, new_value)
        profile.save()

    def save_repo_attr(self, attr, new_value):
        repo = self.profile().repo
        setattr(repo, attr, new_value)
        repo.save()
