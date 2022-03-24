import logging
import threading
from datetime import datetime as dt
from datetime import timedelta
from typing import Dict, Union

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication

from vorta.borg.check import BorgCheckJob
from vorta.borg.create import BorgCreateJob
from vorta.borg.list_repo import BorgListRepoJob
from vorta.borg.prune import BorgPruneJob
from vorta.i18n import translate
from vorta.notifications import VortaNotifications
from vorta.store.models import BackupProfileModel, EventLogModel

logger = logging.getLogger(__name__)


class VortaScheduler(QtCore.QObject):

    #: The schedule for the profile with the given id changed.
    schedule_changed = QtCore.pyqtSignal(int)

    def __init__(self):
        super().__init__()

        #: mapping of profiles to timers
        self.timers: Dict[int, Dict[str, Union[QtCore.QTimer, dt]]] = dict()

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

    def set_timer_for_profile(self, profile_id: int):
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

        with self.lock:  # Acquire lock

            if profile_id in self.timers:
                self.remove_job(profile_id)  # reset schedule

            if profile.repo is None:  # No backups without repo set
                logger.debug(
                    'Nothing scheduled for profile %s because of unset repo.',
                    profile_id)

            if profile.schedule_mode == 'off':
                logger.debug('Scheduler for profile %s is disabled.', profile_id)
                return

            logger.info('Setting timer for profile %s', profile_id)

            # determine last backup time
            last_run_log = EventLogModel.select().where(
                EventLogModel.subcommand == 'create',
                EventLogModel.category == 'scheduled',
                EventLogModel.profile == profile.id,
                0 <= EventLogModel.returncode <= 1,
            ).order_by(EventLogModel.end_time.desc()).first()

            if last_run_log is None:
                # look for non scheduled (manual) backup runs
                last_run_log = EventLogModel.select().where(
                    EventLogModel.subcommand == 'create',
                    EventLogModel.profile == profile.id,
                    0 <= EventLogModel.returncode <= 1,
                ).order_by(EventLogModel.end_time.desc()).first()

            # calculate next scheduled time
            if profile.schedule_mode == 'interval':
                if last_run_log is None:
                    last_time = dt.now()
                else:
                    last_time = last_run_log.end_time

                interval = {profile.schedule_interval_unit: profile.schedule_interval_count}
                next_time = last_time + timedelta(**interval)

            elif profile.schedule_mode == 'fixed':
                if last_run_log is None:
                    last_time = dt.now()
                else:
                    last_time = last_run_log.end_time + timedelta(days=1)

                next_time = last_time.replace(
                    hour=profile.schedule_fixed_hour,
                    minute=profile.schedule_fixed_minute)

            else:
                # unknown schedule mode
                raise ValueError(
                    "Unknown schedule mode '{}'".format(profile.schedule_mode))

            # handle missing of a scheduled time
            if next_time <= dt.now():

                if profile.schedule_make_up_missed:
                    self.lock.release()
                    try:
                        logger.debug('Catching up by running job for %s (%s)',
                                     profile.name, profile_id)
                        self.create_backup(profile_id)
                    finally:
                        self.lock.acquire()  # with-statement will try to release

                    return  # create_backup will lead to a call to this method

                # calculate next time from now
                if profile.schedule_mode == 'interval':
                    # next_time % interval should be 0
                    # while next_time > now
                    delta = dt.now() - last_time
                    next_time = dt.now() - delta % timedelta(**interval)
                    next_time += timedelta(**interval)

                elif profile.schedule_mode == 'fixed':
                    if next_time.date() == dt.now().date():
                        # time for today has passed, schedule for tomorrow
                        next_time += timedelta(days=1)
                    else:
                        # schedule for today
                        next_time = dt.now().replace(
                            hour=profile.schedule_fixed_hour,
                            minute=profile.schedule_fixed_minute)

            # start QTimer
            timer_ms = (next_time - dt.now()).total_seconds() * 1000

            if timer_ms < 2**31 - 1:
                logger.debug('Scheduling next run for %s', next_time)

                timer = QtCore.QTimer()
                timer.setSingleShot(True)
                timer.setInterval(int(timer_ms))
                timer.timeout.connect(lambda: self.create_backup(profile_id))
                timer.start()

                self.timers[profile_id] = {'qtt': timer, 'dt': next_time}
            else:
                # int to big to pass it to qt which expects a c++ int
                # wait 15 min for regular reschedule
                logger.debug(
                    f"Couldn't schedule for {next_time} because "
                    f"timer value {timer_ms} too large.")

        # Emit signal so that e.g. the GUI can react to the new schedule
        self.schedule_changed.emit(profile_id)

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

        validation_cutoff = dt.now() - timedelta(days=7 * profile.validation_weeks)
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
