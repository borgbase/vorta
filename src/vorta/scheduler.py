import logging
import queue
import threading
import time
from datetime import date, timedelta
from enum import Enum
from queue import PriorityQueue

from PyQt5 import QtCore
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


# TODO: refactor to use QtCore.QTimer directly
class VortaScheduler(QtScheduler):
    def __init__(self, parent):
        super().__init__()
        self.app = parent
        self.start()
        self.reload()

        # Set timer to make sure background tasks are scheduled
        self.qt_timer = QtCore.QTimer()
        self.qt_timer.timeout.connect(self.reload)
        self.qt_timer.setInterval(45 * 60 * 1000)
        self.qt_timer.start()

    def tr(self, *args, **kwargs):
        scope = self.__class__.__name__
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
            elif profile.schedule_mode == 'fixed':
                trigger = cron.CronTrigger(hour=profile.schedule_fixed_hour,
                                           minute=profile.schedule_fixed_minute)
            if self.get_job(job_id) is not None and trigger is not None:
                self.reschedule_job(job_id, trigger=trigger)
                logger.debug('Job for profile %s was rescheduled.', profile.name)
            elif trigger is not None:
                self.add_job(
                    func=self.create_backup,
                    args=[profile.id],
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

    def create_backup(self, profile_id):
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


class VortaJob:
    """
    A job is a list of functions. Each function can have params.
    A job can be run on a site.
    func and params must always be lists.
    One job is run on one site. There is one queue for each site. A "site" is simply a repository in
    Vorta since borg can only run one task by repo. The site must implement a method get_id.
    """

    def __init__(self, func: list, params: list, site=0):
        self.func = func
        self.params = params
        self.__id = time.time()  # this id identify a job. It can be use to kill a job
        self.__status = JobStatus.OK  # the job can be runned. If False, the job is not run.
        self.site_id = site

    def get_jobs(self):
        return self.func, self.params

    def set_status(self, status):
        self.__status = status

    def get_status(self):
        return self.__status

    def get_site_id(self):
        return self.site_id


"""
Priority queue. The following priorities are defined :
0 : Safe. Default. The task is adding at the end of the queue.
1 : Safe. This task takes priority over default task. But if default task is already running, this task
has to wait. If a priority 2 is defined, this task will wait too.
2 : Use this only if you know what you do. The task becomes the priority. It will stop all tasks 0 or 1 if necessary.
But if a task of priority 2 or 3 is running, it will wait.
3 : really dangerous. It will stop the task whatever the priority (even 3) and run the task.
"""

"""
Don't use directly this private class ! Instead you can use VortaQueue bellow.
"""


class _QueueScheduler(PriorityQueue):
    """
    Be cautious when modified this class. It has to be reentrant and thrad-safe.
    This queue will not run the thread. It is the role of the calling function to start
    a thread in the function pass in the queue.
    """

    def __init__(self):
        ## private. Never edit this without a method
        self.__p_queue = queue.PriorityQueue()  # queue are thread-safe and reentrant in python

    def add_job(self, task: VortaJob, priority=0):
        """
        A VortaJob contain all information to run a job. Particularly, it contains a function and
        parameters. It can also contain more than one functions.
        """
        self.__p_queue.put((priority, task))
        # TODO This function must add the job to the database

    def get(self):
        return self.__p_queue.get()

    def cancel_job(self, id):
        # TODO
        pass

    def run(self):
        """
        Run the job in the queue. If no job are in the queue, the function waits until a job comes.
        :return:
        """
        # It's not active waiting since get block until there is item in the queue.
        while True:
            priority, vorta_job = self.get()

            if vorta_job.get_status() == JobStatus.OK:
                print("RUN JOB")
                func, params = vorta_job.get_jobs()
                for func_z, params_z in zip(func, params):
                    func_z(params_z)
            # TODO this job can be remove from the database now
            self.__p_queue.task_done()


"""
This class is a complete scheduler. Only use this class and not QueueScheduler.
Assertions :
 - The user only creates few repos with scheduling jobs. So, we don't need to delete a queue each time a queue is empty
 (it's problematic since I create one thread per queue/repo.).

"""


class VortaQueue():
    def __init__(self):
        self.__queues = {}  # we can use a dict since element of the dict are independent.

    def load_from_db(self):
        # load jobs from db if not running.
        pass

    def add_job(self, job: VortaJob, priority=0):
        """
        Return : This function return an id to identify a job. This id can be use to cancel this job.
        """
        if job.get_site_id() not in self.__queues:
            self.__queues[str(job.get_site_id())] = _QueueScheduler()
        self.__queues[str(job.get_site_id())].add_job(job, priority)

    def run(self):
        # each element of the dictionnary can be run in thread.
        # use sync async ???
        for queue in self.queues:
            q_thread = threading.Thread(target=queue.run)
            q_thread.start()

    def cancel_job(self, id):
        pass
