from PyQt6 import QtCore, uic
from PyQt6.QtCore import QDateTime, QLocale
from PyQt6.QtWidgets import QApplication

from vorta import application
from vorta.i18n import get_locale
from vorta.scheduler import ScheduleStatusType
from vorta.store.models import BackupProfileMixin
from vorta.utils import get_asset
from vorta.views.log_panel import LogTableWidget
from vorta.views.networks_panel import NetworksPanel
from vorta.views.shell_commands_panel import ShellCommandsPanel
from vorta.views.utils import get_colored_icon

uifile = get_asset('UI/scheduletab.ui')
ScheduleUI, ScheduleBase = uic.loadUiType(uifile)


class ScheduleTab(ScheduleBase, ScheduleUI, BackupProfileMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)
        self.app: application.VortaApp = QApplication.instance()
        self.toolBox.setCurrentIndex(0)

        self.schedulerRadioMapping = {
            'off': self.scheduleOffRadio,
            'interval': self.scheduleIntervalRadio,
            'fixed': self.scheduleFixedRadio,
        }

        self.init_log_panel()
        self.init_shell_commands_panel()
        self.init_networks_panel()

        self.populate_from_profile()
        self.set_icons()

        # Scheduler intervals we know
        self.scheduleIntervalUnit.addItem(self.tr('Minutes'), 'minutes')
        self.scheduleIntervalUnit.addItem(self.tr('Hours'), 'hours')
        self.scheduleIntervalUnit.addItem(self.tr('Days'), 'days')
        self.scheduleIntervalUnit.addItem(self.tr('Weeks'), 'weeks')

        # Enable/Disable entries on button state changed
        self.framePeriodic.setEnabled(False)
        self.frameDaily.setEnabled(False)
        self.frameValidation.setEnabled(False)

        self.scheduleIntervalRadio.toggled.connect(self.framePeriodic.setEnabled)
        self.scheduleFixedRadio.toggled.connect(self.frameDaily.setEnabled)
        self.validationCheckBox.toggled.connect(self.frameValidation.setEnabled)

        self.app.backup_finished_event.connect(self.logTableWidget.populate_logs)

        # Scheduler events
        for label, obj in self.schedulerRadioMapping.items():
            obj.clicked.connect(self.on_scheduler_change)
        self.scheduleIntervalCount.valueChanged.connect(self.on_scheduler_change)
        self.scheduleIntervalUnit.currentIndexChanged.connect(self.on_scheduler_change)
        self.scheduleFixedTime.timeChanged.connect(self.on_scheduler_change)

        # Network and shell commands events
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

        # Connect to schedule update
        self.app.scheduler.schedule_changed.connect(lambda pid: self.draw_next_scheduled_backup())

        # Connect to palette change
        self.app.paletteChanged.connect(lambda p: self.set_icons())

    def init_log_panel(self):
        self.logTableWidget = LogTableWidget(self)
        self.logTableLayout.addWidget(self.logTableWidget)
        self.logTableWidget.show()

    def init_shell_commands_panel(self):
        self.shellCommandsPanel = ShellCommandsPanel(self)
        self.shellCommandsLayout.addWidget(self.shellCommandsPanel)
        self.shellCommandsPanel.show()

    def init_networks_panel(self):
        self.networksPanel = NetworksPanel(self)
        self.networksLayout.addWidget(self.networksPanel)  # Add this line to attach the NetworksPanel to its layout
        self.networksPanel.show()

    def on_scheduler_change(self, _):
        profile = self.profile()
        # Save scheduler settings, apply new scheduler and display next task for profile.
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
        self.scheduleIntervalUnit.setCurrentIndex(self.scheduleIntervalUnit.findData(profile.schedule_interval_unit))
        self.scheduleIntervalCount.setValue(profile.schedule_interval_count)

        # Set fixed daily time scheduler options
        self.scheduleFixedTime.setTime(QtCore.QTime(profile.schedule_fixed_hour, profile.schedule_fixed_minute))

        # Set borg-check options
        self.validationCheckBox.setCheckState(
            QtCore.Qt.CheckState.Checked if profile.validation_on else QtCore.Qt.CheckState.Unchecked
        )
        self.validationWeeksCount.setValue(profile.validation_weeks)

        # Other checkbox options
        self.pruneCheckBox.setCheckState(
            QtCore.Qt.CheckState.Checked if profile.prune_on else QtCore.Qt.CheckState.Unchecked
        )
        self.missedBackupsCheckBox.setCheckState(
            QtCore.Qt.CheckState.Checked if profile.schedule_make_up_missed else QtCore.Qt.CheckState.Unchecked
        )
        self.networksPanel.meteredNetworksCheckBox.setChecked(False if profile.dont_run_on_metered_networks else True)

        if profile.repo:
            self.shellCommandsPanel.createCmdLineEdit.setText(profile.repo.create_backup_cmd)
            self.shellCommandsPanel.createCmdLineEdit.setEnabled(True)
        else:
            self.shellCommandsPanel.createCmdLineEdit.setEnabled(False)

        self.logTableWidget.populate_logs()
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
