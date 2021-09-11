import logging
import os
import queue
import signal
from datetime import date, timedelta
from enum import Enum
from subprocess import TimeoutExpired

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
        self.vorta_queue = JobsManager()
        self.reload()

        # Set timer to make sure background tasks are scheduled
        self.qt_timer = QtCore.QTimer()
        self.qt_timer.timeout.connect(self.reload)
        self.qt_timer.setInterval(45 * 60 * 1000)
        self.qt_timer.start()

    def cancel_all_jobs(self):
        if DEBUG:
            print("Cancel all Jobs on Vorta Queue")
        self.vorta_queue.cancel_all_jobs()

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
                if profile.repo is not None:
                    repo_id = profile.repo.id
                else:
                    repo_id = -1
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
        vorta_queue.add_job(CreateJobSched(profile_id=profile_id, site=repo_id))


class JobStatus(Enum):
    # dont add and option to put the item at the end of the queue.
    OK = 1
    CANCEL = 2


class Job(QObject):
    """
    To add a job to the vorta queue, you have to create a class which inherits Job. The inherited class
    must override run, cancel and get_site_id.
    """

    def __init__(self):
        super().__init__()
        self.__status = JobStatus.OK  # the job can be launched. If False, the job is not run.

    # Keep default
    def set_status(self, status):
        self.__status = status

    # Keep default
    def get_status(self):
        return self.__status

    # Must return the site id. In borg case, it is the id of the repository.
    def get_site_id(self):
        pass

    """
        Cancel can be called when the job is not started. It is the responsability of FuncJob to not cancel job if
        no job is running.
        The cancel mehod of JobsManager calls the cancel method on the running jobs only. Others jobs are dequeued.
    """

    def cancel(self):
        pass

    # Put the code which must be run for a repo here. The code must be reentrant.
    def run(self):
        pass


class FuncJob(Job):
    # This is an exemple to add a task to the vorta queue.
    # func must return an object of type BorgThread

    def __init__(self, func, params: list = [], site=0):
        super().__init__()
        self.func = func
        self.params = params
        self.site_id = site
        self.thread = None

    def get_site_id(self):
        return self.site_id

    def cancel(self):
        if DEBUG:
            print("Cancel curent Job on site: ", self.site_id)
        self.set_status(JobStatus.CANCEL)
        if self.thread is not None:
            if DEBUG:
                print("Thread Not None")
            self.thread.process.send_signal(signal.SIGINT)
            try:
                self.thread.process.wait(timeout=3)
            except TimeoutExpired:
                os.killpg(os.getpgid(self.thread.process.pid), signal.SIGTERM)
            self.thread.quit()
            self.thread.wait()

    #  We suppose that the function return an object of type BorgThread.
    def run(self):
        thread = self.func(*self.params)
        if thread is not None:
            self.thread = thread
            thread.wait()


class CreateJobSched(Job):

    # Since the scheduler do some stuff after the thread has ended, we can't use FuncJob

    def __init__(self, profile_id, site=0):
        super().__init__()
        self.profile_id = profile_id
        self.site_id = site
        self.thread = None

    def get_site_id(self):
        return self.site_id

    def cancel(self):
        if DEBUG:
            print("Cancel curent Job on site: ", self.site_id)
        self.set_status(JobStatus.CANCEL)
        if self.thread is not None:
            if DEBUG:
                print("Thread Not None")
            self.thread.process.send_signal(signal.SIGINT)
            try:
                self.thread.process.wait(timeout=3)
            except TimeoutExpired:
                os.killpg(os.getpgid(self.thread.process.pid), signal.SIGTERM)
            self.thread.quit()
            self.thread.wait()

    def run(self):
        profile_id = self.profile_id
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
            self.thread = thread
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


class _Queue(QRunnable):
    """
    Don't use directly this private class ! Instead you can use JobsManager bellow.
    A _Queue represent a single site. On a site, tasks are processed successively. For Borg, a site
    represents a repository since only one task can run on this repository.
    """

    def __init__(self, site_id, nb_workers_running: QtCore.QSemaphore):
        super().__init__()
        self.setAutoDelete(False)
        self.__p_queue = queue.Queue()  # queues are thread-safe and reentrant in python
        self.worker_is_running = False
        self.site_id = site_id
        self.timeout = 2
        self.current_job = None
        self.nb_workers_running = nb_workers_running

    def add_job(self, task: Job):
        self.__p_queue.put(task)
        # TODO This function must add the job to the database
        # self.add_to_db(job)

    def get_job(self, timeout):
        return self.__p_queue.get(timeout=timeout)

    def cancel_all_jobs(self):
        if DEBUG:
            print("Cancel job")
        # end process_jobs
        self.worker_is_running = False
        # cancel the current job
        if self.current_job is not None:
            self.current_job.cancel()
        end_job = Job()
        end_job.set_status(JobStatus.CANCEL)
        # if job is waiting for a Job, send a cancel Job
        self.add_job(end_job)

    def cancel_job(self, job: Job):
        # Dequeue the job
        job.set_status(JobStatus.CANCEL)
        # if already runnning, call the cancel job
        job.cancel()

    def process_jobs(self):
        """
        Launch a loop. Each site handles its own queue and processes the tasks. If no job are in the queue,
        the site waits until a job comes. If no jobs come, a timeout ends the loop.
        Since the loop is not launched in a thread, it is up to the calling function to do so.
        """
        self.worker_is_running = True
        while self.worker_is_running:
            if DEBUG:
                print("WAIT FOR A JOB")
            try:
                job = self.get_job(self.timeout)  # Wait for 2 seconds
                self.nb_workers_running.release()
                self.current_job = job
                if job.get_status() == JobStatus.OK:
                    if DEBUG:
                        print("Run Job on repo : ", job.get_site_id())
                    job.run()
                    if DEBUG:
                        print("End job on repo: ", job.get_site_id())
                self.nb_workers_running.acquire()
                # TODO this job can be remove from the database now
                # self.remove_in_db(job)
            except queue.Empty:
                if DEBUG:
                    print("Timeout on site: ", self.site_id)
                self.worker_is_running = False

    def run(self):
        # QRunnable inherited objects has to implement run method
        self.process_jobs()


class JobsManager:
    """
    This class is a complete scheduler. Only use this class and not _Queue. This class MUST BE use
    as a singleton.
    """

    nb_workers_running = QtCore.QSemaphore()

    @classmethod
    def is_worker_running(cls):
        # The user can't start a backup if a job is running. The scheduler can.
        nb_workers = cls.nb_workers_running.available()
        return True if nb_workers > 0 else False

    @classmethod
    def reset_nb_workers(cls):
        del cls.nb_workers_running
        cls.nb_workers_running = QtCore.QSemaphore()

    def __init__(self):
        self.__queues = {}
        # load job from db
        self.load_from_db()
        # use a threadpool -> This could be changed in the future
        self.threadpool = QThreadPool()
        self.lock_add_site = QtCore.QMutex()

    def test_get_site(self, site):
        return self.__queues.get(site)

    def get_site(self, site):
        self.lock_add_site.lock()
        if site not in self.__queues:
            if DEBUG:
                print("Create a site ", site)
            self.__queues[site] = _Queue(site, JobsManager.nb_workers_running)
        # If the site is dead, run the site again
        if self.__queues[site].worker_is_running is False:
            self.threadpool.start(self.__queues[site])
        self.lock_add_site.unlock()
        return self.__queues.get(site)

    def load_from_db(self):
        # TODO load tasks from db
        pass

    def add_job(self, job: Job):
        # This function MUST BE thread safe.
        if DEBUG:
            print("Add Job on site ", job.get_site_id(), type(job.get_site_id()))

        if type(job.get_site_id()) is not int:
            print("get_site_id must return an integer. A ", type(job.get_site_id()), " has be returned.")
            return 1
        self.get_site(job.get_site_id()).add_job(job)

    # Ask to all queues to cancel all jobs. This is what the user expects when he presses the cancel button.
    def cancel_all_jobs(self):
        for id_site, site in self.__queues.items():
            site.cancel_all_jobs()
        self.__queues.clear()
        # reset the semaphore
        JobsManager.reset_nb_workers()
        if DEBUG:
            print("End Cancel")

    def cancel_job(self, job: Job):
        # call cancel job of the site queue
        self.__queues[job.get_site_id].cancel_job(job)
