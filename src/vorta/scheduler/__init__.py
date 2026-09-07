from __future__ import annotations

import logging
from datetime import datetime as dt
from datetime import timedelta
from typing import Any

from packaging import version
from PyQt6 import QtCore
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from vorta import application
from vorta.borg.check import BorgCheckJob
from vorta.borg.compact import BorgCompactJob
from vorta.borg.create import BorgCreateJob
from vorta.borg.list_repo import BorgListRepoJob
from vorta.borg.prune import BorgPruneJob
from vorta.i18n import translate
from vorta.notifications import VortaNotifications
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
from vorta.store.models import BackupProfileModel, EventLogModel, JobModel
from vorta.utils import borg_compat

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

        #: profiles being submitted, so a timer tick cannot submit one twice
        self._submitting: set[int] = set()

        # Scheduling is built first: restoring the pauses writes a status into its timers.
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
        notifier = VortaNotifications.pick()
        profile = BackupProfileModel.get_or_none(id=profile_id)

        if profile is None:
            logger.info('Profile not found. Maybe deleted?')
            return

        if profile_id in self._submitting:
            logger.debug('A run for profile %s is already being submitted.', profile_id)
            return

        # Skip if a job for this profile (repo) is already in progress
        if self.app.jobs_manager.is_worker_running(site=profile.repo.id):
            logger.debug('A job for repo %s is already active.', profile.repo.id)
            self.record_skip(profile, trigger, 'Repository is busy with another job.')
            self.pause(profile_id)
            return

        self._submitting.add(profile_id)
        try:
            logger.info('Starting background backup for %s', profile.name)
            notifier.deliver(
                self.tr('Vorta Backup'),
                self.tr('Starting background backup for %s.') % profile.name,
                level='info',
            )
            msg = BorgCreateJob.prepare(profile)
            if msg['ok']:
                logger.info('Preparation for backup successful.')
                msg['category'] = 'scheduled'
                job = BorgCreateJob(msg['cmd'], msg, profile.repo.id)
                job.result.connect(self.notify)
                self.app.jobs_manager.add_job(job)
            else:
                # Default to 'error': unexpected failures notify.
                # Expected skips (WiFi/metered) use 'info' to suppress.
                level = msg.get('level', 'error')
                if level == 'error':
                    logger.error('Conditions for backup not met. Aborting.')
                    logger.error(msg['message'])
                    notifier.deliver(
                        self.tr('Vorta Backup'),
                        translate('messages', msg['message']),
                        level='error',
                    )
                    status = JobModel.Status.FAILED.value
                else:
                    logger.info('Backup skipped: %s', msg['message'])
                    status = JobModel.Status.SKIPPED.value
                self.record_skip(profile, trigger, msg['message'], status=status)
                self.pause(profile_id)
        finally:
            self._submitting.discard(profile_id)

    def notify(self, result: dict[str, Any]) -> None:
        notifier = VortaNotifications.pick()
        profile_name = result['params']['profile_name']
        profile_id = result['params']['profile'].id

        if result['returncode'] in [0, 1]:
            notifier.deliver(
                self.tr('Vorta Backup'),
                self.tr('Backup successful for %s.') % profile_name,
                level='info',
            )
            logger.info('Backup creation successful.')
            # unpause scheduler
            self.unpause(result['params']['profile_id'])

            self.post_backup_tasks(profile_id)
        else:
            notifier.deliver(
                self.tr('Vorta Backup'),
                self.tr('Error during backup creation for %s.') % profile_name,
                level='error',
            )
            logger.error('Error during backup creation.')
            # pause scheduler
            # if a scheduled backup fails the scheduler should pause
            # temporarily.
            self.pause(result['params']['profile_id'])

        self.set_timer_for_profile(profile_id)

    def post_backup_tasks(self, profile_id: int) -> None:
        """
        Pruning and checking after successful backup.
        """
        profile = BackupProfileModel.get(id=profile_id)
        notifier = VortaNotifications.pick()
        logger.info('Doing post-backup jobs for %s', profile.name)
        if profile.prune_on:
            msg = BorgPruneJob.prepare(profile)
            if msg['ok']:
                job = BorgPruneJob(msg['cmd'], msg, profile.repo.id)
                self.app.jobs_manager.add_job(job)

                # Refresh archives
                msg = BorgListRepoJob.prepare(profile)
                if msg['ok']:
                    job = BorgListRepoJob(msg['cmd'], msg, profile.repo.id)
                    self.app.jobs_manager.add_job(job)

        validation_cutoff = dt.now() - timedelta(days=7 * profile.validation_weeks)
        recent_validations = (
            EventLogModel.select()
            .where(
                (EventLogModel.subcommand == 'check')
                & (EventLogModel.start_time > validation_cutoff)
                & (EventLogModel.repo_url == profile.repo.url)
            )
            .count()
        )
        if profile.validation_on and recent_validations == 0:
            msg = BorgCheckJob.prepare(profile)
            if msg['ok']:
                job = BorgCheckJob(msg['cmd'], msg, profile.repo.id)
                self.app.jobs_manager.add_job(job)

        compaction_cutoff = dt.now() - timedelta(days=7 * profile.compaction_weeks)
        recent_compactions = (
            EventLogModel.select()
            .where(
                (EventLogModel.subcommand == '--info')
                & (EventLogModel.start_time > compaction_cutoff)
                & (EventLogModel.repo_url == profile.repo.url)
            )
            .count()
        )

        if (
            profile.compaction_on
            and recent_compactions == 0
            and version.parse(borg_compat.version) >= version.parse("1.2")
        ):
            msg = BorgCompactJob.prepare(profile)
            if msg['ok']:
                job = BorgCompactJob(msg['cmd'], msg, profile.repo.id)
                self.app.jobs_manager.add_job(job)

        logger.info('Finished background task for profile %s', profile.name)
        notifier.deliver(
            self.tr('Vorta Backup'),
            self.tr('Post Backup Tasks successful for %s' % profile.name),
            level='info',
        )
