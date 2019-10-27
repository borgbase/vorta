import logging
import datetime

from apscheduler.schedulers.qt import QtScheduler
from apscheduler.triggers import cron, interval, date
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.events import EVENT_JOB_EXECUTED
from vorta.borg.check import BorgCheckThread
from vorta.borg.create import BorgCreateThread
from vorta.borg.list_repo import BorgListRepoThread
from vorta.borg.prune import BorgPruneThread
from vorta.config import DB_PATH
from vorta.i18n import translate

from .models import BackupProfileModel, EventLogModel
from .notifications import VortaNotifications

logger = logging.getLogger(__name__)


def trigger_equal(trig1, trig2):
    if not isinstance(trig1, type(trig2)):
        return False

    if hasattr(trig1, 'run_date'):
        # DateTrigger
        return trig1.run_date == trig2.run_date
    elif hasattr(trig1, 'interval_length'):
        # IntervalTrigger
        return trig1.interval_length == trig2.interval_length
    elif hasattr(trig1, 'fields'):
        # CronTrigger
        return trig1.fields == trig2.fields
    else:
        # unhandled trigger type
        raise NotImplementedError


class VortaScheduler(QtScheduler):
    failed_profiles = set()

    def __init__(self, parent):
        super().__init__()
        self.app = parent

        # persist jobs to database to continue schedule of relative interval jobs
        self.configure(jobstores={'default': SQLAlchemyJobStore(url=f'sqlite:///{DB_PATH}')})

        # used for rescheduling of failed jobs
        self.add_listener(self.backup_done, EVENT_JOB_EXECUTED)

        self.start()
        self.reload()

    def backup_done(self, event):
        job_id = event.job_id

        # remove prefix of retry job if it was one
        regular_job_id = job_id.split('retry_')[-1]
        profile_id = int(regular_job_id)

        # schedule retry if job has failed
        if profile_id in self.failed_profiles:
            self.retry_job(regular_job_id, minutes=5)
            logger.debug(f"Job {job_id} failed, profile {profile_id} will be retried shortly")
        else:
            logger.debug(f"Job {job_id} was successful")

    def is_regular_job(self, job_id):
        return not job_id.startswith('retry_')

    def get_retry_jobs(self):
        return [job for job in super().get_jobs() if not self.is_regular_job(job.id)]

    def get_jobs(self):
        # filter out retry jobs so other parts of the code don't hiccup
        return [job for job in super().get_jobs() if self.is_regular_job(job.id)]

    def retry_job(self, job_id, *args, **kwargs):
        job = self.get_job(f'{job_id}')
        if job is None:
            logger.warn(f"Cannot find job {job_id}, cannot retry")
            return

        run_date = datetime.datetime.now() + datetime.timedelta(*args, **kwargs)
        trig = date.DateTrigger(run_date)

        # apscheduler times are aware, but it is easier to compare naive timestamps
        if job.next_run_time.replace(tzinfo=None) < run_date:
            logger.debug("Next job trigger is sooner than planned retry, give up retrying")
            return

        self.add_job(
            job.func,
            args=[int(job_id)],
            trigger=trig,
            id=f"retry_{job_id}",
            misfire_grace_time=180,
            coalesce=True,
            replace_existing=True,
        )

    @classmethod
    def tr(cls, *args, **kwargs):
        scope = cls.__class__.__name__
        return translate(scope, *args, **kwargs)

    def reload(self):
        for profile in BackupProfileModel.select():
            trigger = None
            job_id = f'{profile.id}'
            if profile.schedule_mode == 'interval':
                if profile.schedule_interval_hours >= 24:
                    days = profile.schedule_interval_hours // 24
                    leftover_hours = profile.schedule_interval_hours % 24

                    if leftover_hours == 0:
                        cron_hours = '1'
                    else:
                        cron_hours = f'*/{leftover_hours}'

                    trigger = cron.CronTrigger(day=f'*/{days}',
                                               hour=cron_hours,
                                               minute=profile.schedule_interval_minutes)
                else:
                    trigger = cron.CronTrigger(hour=f'*/{profile.schedule_interval_hours}',
                                               minute=profile.schedule_interval_minutes)

            elif profile.schedule_mode == 'everyday':
                trigger = interval.IntervalTrigger(days=1)

            elif profile.schedule_mode == 'fixed':
                trigger = cron.CronTrigger(hour=profile.schedule_fixed_hour,
                                           minute=profile.schedule_fixed_minute)

            job = self.get_job(job_id)
            if job is not None and trigger is not None:
                if not trigger_equal(job.trigger, trigger):
                    self.reschedule_job(job_id, trigger=trigger)
                    notifier = VortaNotifications.pick()
                    notifier.deliver(self.tr('Vorta Scheduler'), self.tr('Background scheduler was changed.'))
                    logger.debug('Job for profile %s was rescheduled.', profile.name)
            elif trigger is not None:
                self.add_job(
                    func=self.create_backup,
                    args=[profile.id],
                    trigger=trigger,
                    id=job_id,
                    misfire_grace_time=180,
                    coalesce=True,
                    replace_existing=True,
                )
                logger.debug('New job for profile %s was added.', profile.name)
            elif job is not None and trigger is None:
                job.remove()
                logger.debug('Job for profile %s was removed.', profile.name)

    @property
    def next_job(self):
        self.wakeup()
        self._process_jobs()
        jobs = []
        for job in self.get_jobs():
            jobs.append((job.next_run_time, job.id))

        if jobs:
            jobs.sort(key=lambda job: job[0])
            profile = BackupProfileModel.get(id=int(jobs[0][1]))
            return f"{jobs[0][0].strftime('%H:%M')} ({profile.name})"
        else:
            return self.tr('None scheduled')

    def next_job_for_profile(self, profile_id):
        self.wakeup()
        job = self.get_job(str(profile_id))
        if job is None:
            return self.tr('None scheduled')
        else:
            return job.next_run_time.strftime('%Y-%m-%d %H:%M')

    @classmethod
    def create_backup(cls, profile_id):
        notifier = VortaNotifications.pick()
        profile = BackupProfileModel.get(id=profile_id)

        logger.info('Starting background backup for %s', profile.name)
        notifier.deliver(cls.tr('Vorta Backup'),
                         cls.tr('Starting background backup for %s.') % profile.name,
                         level='info')

        msg = BorgCreateThread.prepare(profile)
        if msg['ok']:
            logger.info('Preparation for backup successful.')
            thread = BorgCreateThread(msg['cmd'], msg)
            thread.start()
            thread.wait()
            if thread.process.returncode in [0, 1]:
                notifier.deliver(cls.tr('Vorta Backup'),
                                 cls.tr('Backup successful for %s.') % profile.name,
                                 level='info')
                logger.info('Backup creation successful.')
                cls.failed_profiles = cls.failed_profiles - set([profile_id])
                cls.post_backup_tasks(profile_id)
                return
            else:
                notifier.deliver(cls.tr('Vorta Backup'), cls.tr('Error during backup creation.'), level='error')
                logger.error('Error during backup creation.')
        else:
            logger.error('Conditions for backup not met. Aborting.')
            logger.error(msg['message'])
            notifier.deliver(cls.tr('Vorta Backup'), translate('messages', msg['message']), level='error')

        # backup failed, so mark for retrying
        cls.failed_profiles.add(profile_id)

    @classmethod
    def post_backup_tasks(cls, profile_id):
        """
        Pruning and checking after successful backup.
        """
        profile = BackupProfileModel.get(id=profile_id)
        logger.info('Doing post-backup jobs for %s', profile.name)
        if profile.prune_on:
            msg = BorgPruneThread.prepare(profile)
            if msg['ok']:
                prune_thread = BorgPruneThread(msg['cmd'], msg)
                prune_thread.start()
                prune_thread.wait()

                # Refresh archives
                msg = BorgListRepoThread.prepare(profile)
                if msg['ok']:
                    list_thread = BorgListRepoThread(msg['cmd'], msg)
                    list_thread.start()
                    list_thread.wait()

        validation_cutoff = datetime.date.today() - datetime.timedelta(days=7 * profile.validation_weeks)
        recent_validations = EventLogModel.select().where(
            (
                EventLogModel.subcommand == 'check'
            ) & (
                EventLogModel.start_time > validation_cutoff
            ) & (
                EventLogModel.repo_url == profile.repo.url
            )
        ).count()
        if profile.validation_on and recent_validations == 0:
            msg = BorgCheckThread.prepare(profile)
            if msg['ok']:
                check_thread = BorgCheckThread(msg['cmd'], msg)
                check_thread.start()
                check_thread.wait()

        logger.info('Finished background task for profile %s', profile.name)
