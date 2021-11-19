import logging
import threading
from datetime import datetime as dt, date, timedelta

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
from vorta.borg.check import BorgCheckJob
from vorta.borg.create import BorgCreateJob
from vorta.borg.list_repo import BorgListRepoJob
from vorta.borg.prune import BorgPruneJob
from vorta.i18n import translate

from vorta.store.models import BackupProfileModel, EventLogModel
from vorta.notifications import VortaNotifications

logger = logging.getLogger(__name__)


class VortaScheduler(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.timers = dict()  # keep mapping of profiles to timers
        self.app = QApplication.instance()
        self.lock = threading.Lock()

        # Set additional timer to make sure background tasks stay scheduled.
        # E.g. after hibernation
        self.qt_timer = QtCore.QTimer()
        self.qt_timer.timeout.connect(self.reload_all_timers)
        self.qt_timer.setInterval(15 * 60 * 1000)
        self.qt_timer.start()

    def tr(self, *args, **kwargs):
        scope = self.__class__.__name__
        return translate(scope, *args, **kwargs)

    def set_timer_for_profile(self, profile_id):
        """
        Set a timer for next scheduled backup run of this profile.

        Removes existing jobs if set to manual only or no repo is assigned.

        Else will look for previous scheduled backups and catch up if
        schedule_make_up_missed is enabled.

        Or, if catch-up is not enabled, will add interval to last run to find
        next suitable backup time.
        """
        profile = BackupProfileModel.get_or_none(id=profile_id)
        if profile is None:  # profile doesn't exist any more.
            return

        # First stop and remove any existing timer for this profile
        self.lock.acquire()
        if profile_id in self.timers:
            self.remove_job(profile_id)

        # If no repo is set or only manual backups, just return without
        # replacing the job we removed above.
        if profile.repo is None or profile.schedule_mode == 'off':
            logger.debug('Scheduler for profile %s is disabled.', profile_id)
            self.lock.release()
            return

        logger.info('Setting timer for profile %s', profile_id)

        last_run_log = EventLogModel.select().where(
            EventLogModel.subcommand == 'create',
            EventLogModel.category == 'scheduled',
            EventLogModel.profile == profile.id,
        ).order_by(EventLogModel.end_time.desc()).first()

        # Desired interval between scheduled backups. Uses datetime.timedelta() units.
        if profile.schedule_mode == 'interval':
            interval = {profile.schedule_interval_unit: profile.schedule_interval_count}
        elif profile.schedule_mode == 'fixed':
            interval = {'days': 1}

        # If last run was too long ago and catch-up is enabled, run now
        if profile.schedule_make_up_missed \
                and last_run_log is not None \
                and last_run_log.end_time + timedelta(**interval) < dt.now():
            logger.debug('Catching up by running job for %s', profile.name)
            self.lock.release()
            self.create_backup(profile.id)
            return

        # If the job never ran, use midnight as random starting point
        if last_run_log is None:
            last_run = dt.now().replace(hour=0, minute=0)
        else:
            last_run = last_run_log.end_time

        # Squash seconds to get nice starting time
        last_run = last_run.replace(second=0, microsecond=0)

        # Fixed time is a special case of days=1 interval
        if profile.schedule_mode == 'fixed':
            last_run = last_run.replace(hour=profile.schedule_fixed_hour, minute=profile.schedule_fixed_minute)

        # Add interval to last run time to arrive at next run.
        next_run = last_run
        now = dt.now()
        while next_run < now:
            next_run += timedelta(**interval)

        logger.debug('Scheduling next run for %s', next_run)
        timer_ms = (next_run - dt.now()).total_seconds() * 1000
        timer = QtCore.QTimer()
        timer.setSingleShot(True)
        timer.setInterval(int(timer_ms))
        timer.timeout.connect(lambda: self.create_backup(profile_id))
        timer.start()
        self.timers[profile_id] = {'qtt': timer, 'dt': next_run}

        self.lock.release()

    def reload_all_timers(self):
        logger.debug('Refreshing all scheduler timers')
        for profile in BackupProfileModel.select():
            self.set_timer_for_profile(profile.id)

    def next_job(self):
        next_job = now = dt.now()
        next_profile = None
        for profile_id, timer in self.timers.items():
            if next_job == now and timer['dt'] > next_job and timer['qtt'].isActive():
                next_job = timer['dt']
                next_profile = profile_id
            elif next_job > now and timer['dt'] < next_job and timer['qtt'].isActive():
                next_job = timer['dt']
                next_profile = profile_id

        if next_profile is not None:
            profile = BackupProfileModel.get_or_none(id=next_profile)
            return f"{next_job.strftime('%H:%M')} ({profile.name})"
        else:
            return self.tr('None scheduled')

    def next_job_for_profile(self, profile_id):
        job = self.timers.get(profile_id)
        if job is None:
            return self.tr('None scheduled')
        else:
            return job['dt'].strftime('%Y-%m-%d %H:%M')

    def create_backup(self, profile_id):
        notifier = VortaNotifications.pick()
        profile = BackupProfileModel.get_or_none(id=profile_id)

        if profile is None:
            logger.info('Profile not found. Maybe deleted?')
            return

        # Skip if a job for this profile (repo) is already in progress
        if self.app.jobs_manager.is_worker_running(site=profile.repo.id):
            logger.debug('A job for repo %s is already active.', profile.repo.id)
            return

        self.lock.acquire()
        logger.info('Starting background backup for %s', profile.name)
        notifier.deliver(self.tr('Vorta Backup'),
                         self.tr('Starting background backup for %s.') % profile.name,
                         level='info')
        msg = BorgCreateJob.prepare(profile)
        if msg['ok']:
            logger.info('Preparation for backup successful.')
            msg['category'] = 'scheduled'
            job = BorgCreateJob(msg['cmd'], msg, profile.repo.id)
            job.result.connect(self.notify)
            self.app.jobs_manager.add_job(job)
        else:
            logger.error('Conditions for backup not met. Aborting.')
            logger.error(msg['message'])
            notifier.deliver(self.tr('Vorta Backup'), translate('messages', msg['message']), level='error')
        self.lock.release()

    def notify(self, result):
        notifier = VortaNotifications.pick()
        profile_name = result['params']['profile_name']
        profile_id = result['params']['profile'].id

        if result['returncode'] in [0, 1]:
            notifier.deliver(self.tr('Vorta Backup'),
                             self.tr('Backup successful for %s.') % profile_name,
                             level='info')
            logger.info('Backup creation successful.')
            self.post_backup_tasks(profile_id)
        else:
            notifier.deliver(self.tr('Vorta Backup'), self.tr('Error during backup creation.'), level='error')
            logger.error('Error during backup creation.')

        self.set_timer_for_profile(profile_id)

    def post_backup_tasks(self, profile_id):
        """
        Pruning and checking after successful backup.
        """
        profile = BackupProfileModel.get(id=profile_id)
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

        validation_cutoff = date.today() - timedelta(days=7 * profile.validation_weeks)
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
            msg = BorgCheckJob.prepare(profile)
            if msg['ok']:
                job = BorgCheckJob(msg['cmd'], msg, profile.repo.id)
                self.app.jobs_manager.add_job(job)

        logger.info('Finished background task for profile %s', profile.name)

    def remove_job(self, profile_id):
        if profile_id in self.timers:
            self.timers[profile_id]['qtt'].stop()
            del self.timers[profile_id]
