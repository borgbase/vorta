import logging

from PyQt6 import QtCore, uic
from PyQt6.QtCore import QDateTime, QLocale
from PyQt6.QtWidgets import QApplication

from vorta.i18n import get_locale
from vorta.scheduler import ScheduleStatusType
from vorta.utils import get_asset
from vorta.views.base_tab import BaseTab

logger = logging.getLogger(__name__)
uifile = get_asset('UI/schedule_page.ui')
SchedulePageUI, SchedulePageBase = uic.loadUiType(uifile)


class SchedulePage(BaseTab, SchedulePageBase, SchedulePageUI):
    def __init__(self, parent=None, profile_provider=None):
        super().__init__(parent=parent, profile_provider=profile_provider)
        self.setupUi(self)
        self.hasPopulatedScheduleFields = False

        self.schedulerRadioMapping = {
            'off': self.scheduleOffRadio,
            'interval': self.scheduleIntervalRadio,
            'fixed': self.scheduleFixedRadio,
        }

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

        self.bind_profile_attr(self.missedBackupsCheckBox.stateChanged, 'schedule_make_up_missed')
        self.bind_profile_attr(self.pruneCheckBox.stateChanged, 'prune_on')
        self.bind_profile_attr(self.validationCheckBox.stateChanged, 'validation_on')
        self.bind_profile_attr(self.validationWeeksCount.valueChanged, 'validation_weeks')
        self.bind_profile_attr(self.compactionCheckBox.stateChanged, 'compaction_on')
        self.bind_profile_attr(self.compactionWeeksCount.valueChanged, 'compaction_weeks')

        self.track_signal(self.app.scheduler.schedule_changed, self.draw_next_scheduled_backup)
        self.track_profile_change(call_now=True)
        self.hasPopulatedScheduleFields = True

    def on_scheduler_change(self, _):
        # Wait until we've populated fields _from_ the schedule before populating them back
        if not self.hasPopulatedScheduleFields:
            return

        logger.debug("Updating schedule due to field change")
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
