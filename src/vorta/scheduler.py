import logging
import time
from datetime import datetime as dt, date, timedelta
import threading
from PyQt5 import QtCore
from vorta.borg.check import BorgCheckThread
from vorta.borg.create import BorgCreateThread
from vorta.borg.list_repo import BorgListRepoThread
from vorta.borg.prune import BorgPruneThread
from vorta.i18n import translate

from vorta.models import BackupProfileModel, EventLogModel
from vorta.notifications import VortaNotifications

logger = logging.getLogger(__name__)

# http://ilearnstuff.blogspot.com/2012/09/qthread-best-practices-when-qthread.html
# https://stackoverflow.com/questions/20324804/how-to-use-qthread-correctly-in-pyqt-with-movetothread

class VortaScheduler(QtCore.QObject):
    process_jobs_signal = QtCore.pyqtSignal()

    def __init__(self, app):
        super().__init__()
        self.jobs = {}
        self.app = app
        self.process_jobs_signal.connect(self.process_jobs)

    @classmethod
    def get_scheduler_thread(cls):
        worker = cls()
        workerThread = QtCore.QThread()
        timer = QtCore.QTimer()
        worker.moveToThread(workerThread)
        timer.moveToThread(workerThread)
        timer.timeout.connect(worker.process_jobs)
        timer.setInterval(1000)
        workerThread.started.connect(timer.start)
        worker.timer = timer
        workerThread.worker = worker
        workerThread.start()
        return workerThread

    def tr(self, *args, **kwargs):
        scope = self.__class__.__name__
        return translate(scope, *args, **kwargs)

    @QtCore.pyqtSlot
    def process_jobs(self):
        print("processing started from :" + str(threading.get_ident()))
        # First run scheduled backups. 2 minutes grace time
        for profile_id, job_time in self.jobs.items():
            if job_time > dt.now() + timedelta(minutes=2) \
                    and job_time < dt.now() + timedelta(minutes=2):
                self.create_backup(profile_id)

        # Check future schedule for all profiles
        for profile in BackupProfileModel.select():
            if profile.schedule_mode == 'off':
                continue

            next_run = self.jobs.get(profile.id, dt.now())
            if next_run is not None and next_run > dt.now():
                continue

            # Job has no next_run set. Let's figure one out.
            last_run = EventLogModel.select().where(
                EventLogModel.subcommand == 'create',
                EventLogModel.category == 'scheduled',
                EventLogModel.profile == profile.id,
            ).order_by(EventLogModel.start_time.desc()).first()
            print('last', last_run, profile.schedule_make_up_missed)

            if profile.schedule_mode == 'interval':
                interval = {profile.schedule_interval_unit: profile.schedule_interval_hours}
            elif profile.schedule_mode == 'fixed':
                interval = {'days': 1}

            # If last run was too long ago, catch up now
            if profile.schedule_make_up_missed \
                    and last_run is not None \
                    and last_run.start_time + timedelta(**interval) < dt.now():
                logger.debug('Catching up by running job for %s', profile.name)
                time.sleep(10)
                # self.create_backup(profile.id)

            # If the job never ran, start now.
            if last_run is None:
                last_run = dt.now()
            else:
                last_run = last_run.start_time

            # Fixed time is a special case of days = 1
            if profile.schedule_mode == 'fixed':
                last_run.hour = profile.schedule_fixed_hour
                last_run.minut = profile.schedule_fixed_minut

            # Add interval to arrive at next run.
            next_run = last_run
            while next_run < dt.now():
                next_run += timedelta(**interval)

            logger.debug('New job for profile %s was added for %s.', profile.name, next_run)
            self.jobs[profile.id] = next_run

        next_wakeup_seconds = 60*40
        if self.jobs:
            nearest_job = sorted(self.jobs.items(), key=lambda x: x[1])[0]
            print(nearest_job)
            next_wakeup_seconds = (nearest_job[1] - dt.now()).seconds
        self.timer.setInterval(next_wakeup_seconds)
        logger.debug('Next wakeup in %s seconds', next_wakeup_seconds)

    @property
    def next_job(self):
        if len(self.jobs) > 0:
            self.jobs.sort(key=lambda job: job[0])
            profile = BackupProfileModel.get(id=int(jobs[0][1]))
            return f"{self.jobs[0][0].strftime('%H:%M')} ({profile.name})"
        else:
            return self.tr('None scheduled')

    def next_job_for_profile(self, profile_id):
        job = self.jobs.get(profile_id)
        if job is None:
            return self.tr('None scheduled')
        else:
            return job.next_run_time.strftime('%Y-%m-%d %H:%M')

    def create_backup(self, profile_id):
        notifier = VortaNotifications.pick()
        profile = BackupProfileModel.get(id=profile_id)

        logger.info('Starting background backup for %s', profile.name)
        notifier.deliver(self.tr('Vorta Backup'),
                         self.tr('Starting background backup for %s.') % profile.name,
                         level='info')

        msg = BorgCreateThread.prepare(profile)
        msg['initiator'] = 'scheduled'
        if msg['ok']:
            logger.info('Preparation for backup successful.')
            thread = BorgCreateThread(msg['cmd'], msg)
            thread.start()
            thread.wait()
            if thread.process.returncode in [0, 1]:
                notifier.deliver(self.tr('Vorta Backup'),
                                 self.tr('Backup successful for %s.') % profile.name,
                                 level='info')
                logger.info('Backup creation successful.')
                self.post_backup_tasks(profile_id)
            else:
                notifier.deliver(self.tr('Vorta Backup'), self.tr('Error during backup creation.'), level='error')
                logger.error('Error during backup creation.')
        else:
            logger.error('Conditions for backup not met. Aborting.')
            logger.error(msg['message'])
            notifier.deliver(self.tr('Vorta Backup'), translate('messages', msg['message']), level='error')

    def post_backup_tasks(self, profile_id):
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
            msg = BorgCheckThread.prepare(profile)
            if msg['ok']:
                check_thread = BorgCheckThread(msg['cmd'], msg)
                check_thread.start()
                check_thread.wait()

        logger.info('Finished background task for profile %s', profile.name)
