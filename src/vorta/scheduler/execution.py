from __future__ import annotations

import logging
from datetime import datetime as dt
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from packaging import version

from vorta.borg.borg_job import BorgJob
from vorta.borg.check import BorgCheckJob
from vorta.borg.compact import BorgCompactJob
from vorta.borg.create import BorgCreateJob
from vorta.borg.list_repo import BorgListRepoJob
from vorta.borg.prune import BorgPruneJob
from vorta.i18n import translate
from vorta.notifications import VortaNotifications
from vorta.store.models import BackupProfileModel, EventLogModel, JobModel
from vorta.utils import borg_compat

if TYPE_CHECKING:
    from vorta.scheduler import VortaScheduler

logger = logging.getLogger(__name__)


def worst_error(errors: list[tuple[int, str]] | None) -> str | None:
    """The most severe message Borg logged, to show as the reason a run failed."""
    if not errors:
        return None

    worst = max(level for level, _ in errors)
    return next(message for level, message in errors if level == worst)


class SchedulerExecution:
    """Submitted backup runs, their results and the post-backup tasks."""

    def __init__(self, scheduler: VortaScheduler) -> None:
        self.scheduler = scheduler

        #: profiles being submitted, so a timer tick cannot submit one twice
        self._submitting: set[int] = set()

        #: post-backup jobs still running per profile, and whether one of them failed
        self._post_backup_pending: dict[int, int] = {}
        self._post_backup_failed: dict[int, bool] = {}

    def create_backup(self, profile_id: int, trigger: str) -> None:
        notifier = VortaNotifications.pick()
        profile = BackupProfileModel.get_or_none(id=profile_id)

        if profile is None:
            logger.info('Profile not found. Maybe deleted?')
            return

        if profile_id in self._submitting:
            logger.debug('A run for profile %s is already being submitted.', profile_id)
            return

        # Skip if a job for this profile (repo) is already in progress
        if self.scheduler.app.jobs_manager.is_worker_running(site=profile.repo.id):
            logger.debug('A job for repo %s is already active.', profile.repo.id)
            self.scheduler.record_skip(profile, trigger, 'Repository is busy with another job.')
            self.scheduler.pause(profile_id)
            return

        self._submitting.add(profile_id)
        try:
            logger.info('Starting background backup for %s', profile.name)
            notifier.deliver(
                self.scheduler.tr('Vorta Backup'),
                self.scheduler.tr('Starting background backup for %s.') % profile.name,
                level='info',
            )
            msg = BorgCreateJob.prepare(profile)
            if msg['ok']:
                logger.info('Preparation for backup successful.')
                msg['category'] = 'scheduled'
                msg['job_record_id'] = self.scheduler.record_start(profile, trigger)
                # The timer that fired still holds this run as pending; `notify` re-arms it afterwards.
                self.scheduler.remove_job(profile_id)
                self.scheduler.schedule_changed.emit()
                job = BorgCreateJob(msg['cmd'], msg, profile.repo.id)
                job.result.connect(self.scheduler.notify)
                self.scheduler.app.jobs_manager.add_job(job)
            else:
                # Default to 'error': unexpected failures notify.
                # Expected skips (WiFi/metered) use 'info' to suppress.
                level = msg.get('level', 'error')
                if level == 'error':
                    logger.error('Conditions for backup not met. Aborting.')
                    logger.error(msg['message'])
                    notifier.deliver(
                        self.scheduler.tr('Vorta Backup'),
                        translate('messages', msg['message']),
                        level='error',
                    )
                    status = JobModel.Status.FAILED.value
                else:
                    logger.info('Backup skipped: %s', msg['message'])
                    status = JobModel.Status.SKIPPED.value
                self.scheduler.record_skip(profile, trigger, msg['message'], status=status)
                self.scheduler.pause(profile_id)
        finally:
            self._submitting.discard(profile_id)

    def notify(self, result: dict[str, Any]) -> None:
        notifier = VortaNotifications.pick()
        profile_name = result['params']['profile_name']
        profile_id = result['params']['profile'].id
        succeeded = result['returncode'] in [0, 1]

        record_id = result['params'].get('job_record_id')
        if record_id is not None:
            status = JobModel.Status.COMPLETED.value if succeeded else JobModel.Status.FAILED.value
            reason = None if succeeded else worst_error(result.get('errors'))
            self.scheduler.record_finish(record_id, status, result.get('log_entry_id'), reason)

        if succeeded:
            notifier.deliver(
                self.scheduler.tr('Vorta Backup'),
                self.scheduler.tr('Backup successful for %s.') % profile_name,
                level='info',
            )
            logger.info('Backup creation successful.')
            # unpause scheduler
            self.scheduler.unpause(result['params']['profile_id'])

            self.scheduler.post_backup_tasks(profile_id)
        else:
            notifier.deliver(
                self.scheduler.tr('Vorta Backup'),
                self.scheduler.tr('Error during backup creation for %s.') % profile_name,
                level='error',
            )
            logger.error('Error during backup creation.')
            # pause scheduler
            # if a scheduled backup fails the scheduler should pause
            # temporarily.
            self.scheduler.pause(result['params']['profile_id'])

        self.scheduler.set_timer_for_profile(profile_id)

    def post_backup_tasks(self, profile_id: int) -> None:
        """
        Pruning and checking after successful backup.
        """
        profile = BackupProfileModel.get_or_none(id=profile_id)
        if profile is None:
            logger.info('Profile not found. Maybe deleted?')
            return

        logger.info('Doing post-backup jobs for %s', profile.name)
        jobs: list[BorgJob] = []
        if profile.prune_on:
            msg = BorgPruneJob.prepare(profile)
            if msg['ok']:
                jobs.append(BorgPruneJob(msg['cmd'], msg, profile.repo.id))

                # Refresh archives
                msg = BorgListRepoJob.prepare(profile)
                if msg['ok']:
                    jobs.append(BorgListRepoJob(msg['cmd'], msg, profile.repo.id))

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
                jobs.append(BorgCheckJob(msg['cmd'], msg, profile.repo.id))

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
                jobs.append(BorgCompactJob(msg['cmd'], msg, profile.repo.id))

        if not jobs:
            self._notify_post_backup_tasks_done(profile.name, failed=False)
            return

        # Notify once all queued jobs have finished, not when they are queued.
        # Start a fresh count: jobs of an earlier batch that were cancelled from the queue never report back.
        self._post_backup_pending[profile.id] = len(jobs)
        self._post_backup_failed.pop(profile.id, None)
        for job in jobs:
            job.result.connect(self.scheduler.post_backup_task_finished)
            self.scheduler.app.jobs_manager.add_job(job)

    def post_backup_task_finished(self, result: dict[str, Any]) -> None:
        profile_id = result['params']['profile_id']
        if profile_id not in self._post_backup_pending:
            return

        if result['returncode'] not in [0, 1]:
            self._post_backup_failed[profile_id] = True

        self._post_backup_pending[profile_id] -= 1
        if self._post_backup_pending[profile_id] > 0:
            return

        del self._post_backup_pending[profile_id]
        failed = self._post_backup_failed.pop(profile_id, False)
        self._notify_post_backup_tasks_done(result['params']['profile_name'], failed)

    def _notify_post_backup_tasks_done(self, profile_name: str, failed: bool) -> None:
        logger.info('Finished background task for profile %s', profile_name)
        notifier = VortaNotifications.pick()
        if failed:
            notifier.deliver(
                self.scheduler.tr('Vorta Backup'),
                self.scheduler.tr('Post Backup Tasks failed for %s') % profile_name,
                level='error',
            )
        else:
            notifier.deliver(
                self.scheduler.tr('Vorta Backup'),
                self.scheduler.tr('Post Backup Tasks successful for %s') % profile_name,
                level='info',
            )
