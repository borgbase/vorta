import logging
import queue
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from queue import PriorityQueue

from PyQt5 import QtCore
from PyQt5.QtCore import QObject, QThreadPool, QRunnable
from apscheduler.schedulers.qt import QtScheduler
from apscheduler.triggers import cron
from vorta.borg.check import BorgCheckThread
from vorta.borg.create import BorgCreateThread
from vorta.borg.list_repo import BorgListRepoThread
from vorta.borg.prune import BorgPruneThread
from vorta.i18n import translate

from vorta.models import BackupProfileModel, EventLogModel
from vorta.notifications import VortaNotifications

logger = logging.getLogger(__name__)
DEBUG = False


# TODO: refactor to use QtCore.QTimer directly
class VortaScheduler(QtScheduler):
    def __init__(self, parent):
        super().__init__()
        self.app = parent
        self.start()
        self.vorta_queue = VortaQueue()
        self.reload()

        # Set timer to make sure background tasks are scheduled
        self.qt_timer = QtCore.QTimer()
        self.qt_timer.timeout.connect(self.reload)
        self.qt_timer.setInterval(45 * 60 * 1000)
        self.qt_timer.start()
        self.scheduler = VortaQueue()

    def tr(self, *args, **kwargs):
        scope = self.__class__.__name__
        return translate(scope, *args, **kwargs)

    def reload(self):
        for profile in BackupProfileModel.select():
            trigger = None
            job_id = f'{profile.id}'
            repo_id = profile.repo.id
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
            elif profile.schedule_mode == 'fixed':
                trigger = cron.CronTrigger(hour=profile.schedule_fixed_hour,
                                           minute=profile.schedule_fixed_minute)
            if self.get_job(job_id) is not None and trigger is not None:
                self.reschedule_job(job_id, trigger=trigger)
                logger.debug('Job for profile %s was rescheduled.', profile.name)
            elif trigger is not None:
                self.add_job(
                    func=self.enqueue_create_backup,
                    args=[profile.id, repo_id, self.vorta_queue],
                    trigger=trigger,
                    id=job_id,
                    misfire_grace_time=180
                )
                logger.debug('New job for profile %s was added.', profile.name)
            elif self.get_job(job_id) is not None and trigger is None:
                self.remove_job(job_id)
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

    def enqueue_create_backup(self, profile_id, repo_id, vorta_queue):
        vorta_queue.add_job(FuncJobQueue(func=self.create_backup, params=[profile_id], site=repo_id))

    def create_backup(self, profile_id):
        if DEBUG:
            print("start backup for profile ", profile_id)
        notifier = VortaNotifications.pick()
        profile = BackupProfileModel.get(id=profile_id)

        logger.info('Starting background backup for %s', profile.name)
        notifier.deliver(self.tr('Vorta Backup'),
                         self.tr('Starting background backup for %s.') % profile.name,
                         level='info')
        msg = BorgCreateThread.prepare(profile)
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
        if DEBUG:
            print("End backup for profile ", profile_id)

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


class JobStatus(Enum):
    # dont add and option to put the item at the end of the queue.
    OK = 1
    PASS = 2


"""
To add a job to the vorta queue, you have to create a class which inherits JobQueue. The inherited class
must override run, cancel and get_site_id.

A 'site' represent a single queue. On a site, tasks are run one by one.
Between site, tasks are run concurrently. For Borg, a site
represents a repository since only one task can run on this repository.
So get_site_id must return the id of the repository. See FuncJobQueue class which inherits JobQueue.

Don't use run and cancel method directly. 'cancel' method in class VortaQueue
call your custom cancel and add_job in VortaQueue call 'run' when older job have been processed on his site.
"""


@dataclass(order=True)
class JobQueue(QObject):
    """
    func and params must always be lists.
    One job is run on one site. There is one queue for each site. A "site" is simply a repository in
    Vorta since borg can only run one task by repo. The site must implement a method get_id.
    """

    def __init__(self, priority=0):
        self.priority = priority
        self.__status = JobStatus.OK  # the job can be runned. If False, the job is not run.

    def set_status(self, status):
        self.__status = status

    def get_status(self):
        return self.__status

    def get_site_id(self):
        pass

    def cancel(self):
        pass

    def run(self):
        pass


class FuncJobQueue(JobQueue):
    # This is an exemple to add a task to the vorta queue.
    # 'run' method should be reentrant and thread-safe.
    def __init__(self, func, params: list, site=0, priority=0):
        super().__init__(priority)
        self.func = func
        self.params = params
        self.site_id = site

    def get_site_id(self):
        return self.site_id

    # This job can be dequeue but can't be cancelled. So a running FuncJobQueue can't be stopped.
    def cancel(self):
        pass

    def run(self):
        self.func(*self.params)


class _QueueScheduler(QRunnable, PriorityQueue):
    """
    Don't use directly this private class ! Instead you can use VortaQueue bellow.
    A _QueueScheduler represent a single site. On a site, tasks are processed successively. For Borg, a site
    represents a repository since only one task can run on this repository.
    """

    def __init__(self):
        super().__init__()
        self.__p_queue = queue.PriorityQueue()  # queues are thread-safe and reentrant in python

    def add_job(self, task: JobQueue):
        self.__p_queue.put((task.priority, task))
        # TODO This function must add the job to the database
        # self.add_to_db(job)

    def get(self):
        return self.__p_queue.get()

    def cancel_job(self, job: JobQueue):
        # Dequeue the job
        job.set_status(JobStatus.PASS)
        # if already runnning, call the cancel job
        job.cancel()

    def process_jobs(self):
        """
        Launch a loop. Each site handles its own queue and processes the tasks. If no job are in the queue,
        the site waits until a job comes. Since the loop is not launched in a thread,
        it is up to the calling function to do so.
        """
        # It's not active waiting since get block until there is item in the queue.
        while True:
            priority, vorta_job = self.get()
            if vorta_job.get_status() == JobStatus.OK:
                if DEBUG:
                    print("Run Job on repo : ", vorta_job.get_site_id())
                vorta_job.run()
                if DEBUG:
                    print("End job on repo: ", vorta_job.get_site_id())
            # TODO this job can be remove from the database now
            # self.remove_in_db(vorta_job)

    def run(self):
        # QRunnable inherited objects has to implement run method
        self.process_jobs()


class VortaQueue:
    """
    This class is a complete scheduler. Only use this class and not _QueueScheduler.
    """

    def __init__(self):
        self.__queues = {}  # we can use a dict since element of the dict are independent.
        # load job from db
        self.load_from_db()
        # use a threadpool -> This could be changed in the future
        self.threadpool = QThreadPool()

    def load_from_db(self):
        # TODO load tasks from db
        pass

    def add_job(self, job: JobQueue):
        """
        job must provide a function get_site_id. It's to the job to decide in which site running the job.
        This function is not thread safe. Always add a job from the main thread (ui loop).
        """
        if DEBUG:
            print("add Job")
        if job.get_site_id() not in self.__queues:
            self.__queues[job.get_site_id()] = _QueueScheduler()
            # run the loop
            self.threadpool.start(self.__queues[job.get_site_id()]) # start call the run method.
        self.__queues[job.get_site_id()].add_job(job)

    def cancel_job(self, job: JobQueue):
        # call cancel job of the site queue
        self.__queues[job.get_site_id].cancel_job(job)

    def is_running(self):
        pass
