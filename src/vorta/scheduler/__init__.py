from __future__ import annotations

import logging
from datetime import datetime as dt
from typing import Any

from PyQt6 import QtCore
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from vorta import application
from vorta.i18n import translate
from vorta.scheduler.execution import SchedulerExecution
from vorta.scheduler.scheduling import (
    MAX_TIMER_MS,
    PENDING_STATUSES,
    RESCHEDULE_INTERVAL_MS,
    TIMER_GRACE_MS,
    PendingJob,
    SchedulerTimers,
    ScheduleStatus,
    ScheduleStatusType,
    arm_deadline_timer,
)
from vorta.scheduler.state import WAKE_CHECK_INTERVAL_MS, WAKE_GAP_THRESHOLD, SchedulerState
from vorta.store.models import BackupProfileModel, JobModel

logger = logging.getLogger(__name__)

__all__ = [
    'MAX_TIMER_MS',
    'PENDING_STATUSES',
    'RESCHEDULE_INTERVAL_MS',
    'TIMER_GRACE_MS',
    'WAKE_CHECK_INTERVAL_MS',
    'WAKE_GAP_THRESHOLD',
    'PendingJob',
    'ScheduleStatus',
    'ScheduleStatusType',
    'VortaScheduler',
    'arm_deadline_timer',
]


class VortaScheduler(QtCore.QObject):
    #: The schedule for a profile changed.
    schedule_changed = QtCore.pyqtSignal()

    #: A job outcome was recorded.
    jobs_changed = QtCore.pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        self.app: application.VortaApp = QApplication.instance()

        # Execution first: it starts nothing, and the other two arm timers that route back into it.
        self._execution = SchedulerExecution(self)
        # Scheduling before State: restoring the pauses writes a status into its timers.
        self._timers = SchedulerTimers(self)
        self._state = SchedulerState(self)
        self._state.restore_pauses()

        # connect signals
        self.app.backup_finished_event.connect(lambda res: self.set_timer_for_profile(res['params']['profile_id']))

    @property
    def timers(self) -> dict[int, dict[str, QTimer | dt | ScheduleStatusType | None]]:
        return self._timers.timers

    @property
    def lock(self):
        return self._timers.lock

    @property
    def qt_timer(self) -> QTimer:
        return self._timers.qt_timer

    @property
    def net_status(self):
        return self._timers.net_status

    @net_status.setter
    def net_status(self, monitor) -> None:
        self._timers.net_status = monitor

    @property
    def _net_up(self) -> bool:
        return self._timers._net_up

    @_net_up.setter
    def _net_up(self, up: bool) -> None:
        self._timers._net_up = up

    @property
    def pauses(self) -> dict[int, tuple[dt, QtCore.QTimer]]:
        return self._state.pauses

    @property
    def wake_timer(self) -> QTimer:
        return self._state.wake_timer

    @QtCore.pyqtSlot(bool)
    def loginSuspendNotify(self, suspend: bool) -> None:
        self._state.loginSuspendNotify(suspend)

    @QtCore.pyqtSlot()
    def checkForResume(self) -> None:
        self._state.checkForResume()

    @QtCore.pyqtSlot(bool)
    def networkStatusChanged(self, up: bool) -> None:
        self._timers.networkStatusChanged(up)

    def tr(self, *args: Any, **kwargs: Any) -> str:
        scope = self.__class__.__name__
        return translate(scope, *args, **kwargs)

    def pause(self, profile_id: int, until: dt | None = None) -> None:
        self._state.pause(profile_id, until)

    def unpause(self, profile_id: int) -> None:
        self._state.unpause(profile_id)

    def clear_pause(self, profile_id: int) -> None:
        self._state.clear_pause(profile_id)

    def paused(self, profile_id: int) -> bool:
        return self._state.paused(profile_id)

    def record_skip(
        self,
        profile: BackupProfileModel,
        trigger: str,
        reason: str,
        status: str = JobModel.Status.SKIPPED.value,
        scheduled_at: dt | None = None,
    ) -> None:
        self._state.record_skip(profile, trigger, reason, status=status, scheduled_at=scheduled_at)

    def record_start(self, profile: BackupProfileModel, trigger: str) -> int | None:
        return self._state.record_start(profile, trigger)

    def record_finish(
        self, record_id: int, status: str, log_entry_id: int | None = None, reason: str | None = None
    ) -> None:
        self._state.record_finish(record_id, status, log_entry_id, reason)

    def set_timer_for_profile(self, profile_id: int) -> None:
        """Set a timer for next scheduled backup run of this profile, and run a missed one."""
        catch_up = self._timers.arm_profile(profile_id)
        if catch_up is not None:
            self.create_backup(catch_up, trigger=JobModel.Trigger.CATCHUP.value)

    def reload_all_timers(self) -> None:
        self._timers.reload_all_timers()

    def remove_job(self, profile_id: int) -> None:
        self._timers.remove_job(profile_id)

    def mark_paused(self, profile: BackupProfileModel, until: dt) -> None:
        self._timers.mark_paused(profile, until)

    def next_job(self) -> str:
        return self._timers.next_job()

    def next_job_for_profile(self, profile_id: int) -> ScheduleStatus:
        return self._timers.next_job_for_profile(profile_id)

    def pending_jobs(self) -> list[PendingJob]:
        return self._timers.pending_jobs()

    def create_backup(self, profile_id: int, trigger: str = JobModel.Trigger.SCHEDULED.value) -> None:
        self._execution.create_backup(profile_id, trigger)

    def notify(self, result: dict[str, Any]) -> None:
        self._execution.notify(result)

    def post_backup_tasks(self, profile_id: int) -> None:
        self._execution.post_backup_tasks(profile_id)
