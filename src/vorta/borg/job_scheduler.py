import queue
from abc import abstractmethod
from enum import Enum

from PyQt5 import QtCore
from PyQt5.QtCore import QObject, QRunnable, QThreadPool

DEBUG = False


class JobStatus(Enum):
    # dont add and option to put the item at the end of the queue.
    OK = 1
    CANCEL = 2


class Job(QObject):
    """
    To add a job to the vorta queue, you have to create a class which inherits Job. The inherited class
    must override run, cancel and get_site_id. Since Job inherits from QObject, you can use pyqt signal.
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
    @abstractmethod
    def repo_id(self):
        pass

    """
        Cancel can be called when the job is not started. It is the responsability of FuncJob to not cancel job if
        no job is running.
        The cancel mehod of JobsManager calls the cancel method on the running jobs only. Others jobs are dequeued.
    """

    @abstractmethod
    def cancel(self):
        pass

    # Put the code which must be run for a repo here. The code must be reentrant.
    @abstractmethod
    def run(self):
        pass


class _Queue(QRunnable):
    """
    Don't use directly this private class ! Instead you can use JobsManager bellow.
    A _Queue represent a single site. On a site, tasks are processed successively. For Borg, a site
    represents a repository since only one task can run on this repository.
    """

    def __init__(self, site_id, nb_workers_running: QtCore.QSemaphore, threadpool):
        super().__init__()
        self.setAutoDelete(False)
        self.__p_queue = queue.Queue()  # queues are thread-safe and reentrant in python
        self.worker_is_running = False
        self.site_id = site_id
        self.timeout = 2
        self.current_job = None
        self.nb_workers_running = nb_workers_running
        self.threadpool = threadpool
        self.mut_start_site = QtCore.QMutex()

    def add_job(self, task: Job):
        self.__p_queue.put(task)
        # If the site is dead, run the site again
        self.mut_start_site.lock()
        if self.worker_is_running is False:
            if DEBUG:
                print("Restart Site ", task.repo_id())
            self.worker_is_running = True
            self.threadpool.start(self)
        self.mut_start_site.unlock()
        # TODO This function must add the job to the database
        # self.add_to_db(job)

    def get_job(self, timeout):
        return self.__p_queue.get(timeout=timeout)

    def cancel_all_jobs(self):
        end_job = Job()
        end_job.set_status(JobStatus.CANCEL)

        self.mut_start_site.lock()
        # Stop the loop
        self.worker_is_running = False
        # if the site is waiting for a Job, send a cancel Job
        self.__p_queue.put(end_job)
        # cancel the current job
        if self.current_job is not None:
            self.current_job.cancel()

        self.mut_start_site.unlock()

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
        if DEBUG:
            print("Enter Process jobs")
        while self.worker_is_running:
            if DEBUG:
                print("WAIT FOR A JOB")
            try:
                job = self.get_job(self.timeout)  # Wait for 2 seconds
                self.nb_workers_running.release()
                self.current_job = job
                if job.get_status() == JobStatus.OK:
                    if DEBUG:
                        print("Run Job on repo : ", job.repo_id())
                    job.run()
                    if DEBUG:
                        print("End job on repo: ", job.repo_id())
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

    def __init__(self):
        self.__queues = {}
        # load job from db
        self.load_from_db()
        # use a threadpool -> This could be changed in the future
        self.threadpool = QThreadPool()
        self.mut_queues = QtCore.QMutex()

    @classmethod
    def is_worker_running(cls):
        # The user can't start a backup if a job is running. The scheduler can.
        nb_workers = cls.nb_workers_running.available()
        return True if nb_workers > 0 else False

    @classmethod
    def reset_nb_workers(cls):
        del cls.nb_workers_running
        cls.nb_workers_running = QtCore.QSemaphore()

    def get_site(self, site):
        self.mut_queues.lock()
        if site not in self.__queues:
            if DEBUG:
                print("Create a site ", site)
            self.__queues[site] = _Queue(site, JobsManager.nb_workers_running, self.threadpool)
        self.mut_queues.unlock()
        return self.__queues.get(site)

    def load_from_db(self):
        # TODO load tasks from db
        pass

    def add_job(self, job: Job):
        # This function MUST BE thread safe.
        if DEBUG:
            print("Add Job on site ", job.repo_id(), type(job.repo_id()))

        if not isinstance(job.repo_id(), (int, str)):
            print("get_site_id must return an integer or str . A ", type(job.repo_id()), " has be returned : ",
                  job.repo_id())
            return 1
        self.get_site(job.repo_id()).add_job(job)

    """
    Ask to all queues to cancel all jobs.
    There is no guarantee that all tasks will be removed. If some jobs are added before lock from another thread,
    it will not be cancelled. That's why, it's strongly advised to add jobs from the main UI loop.
    """
    def cancel_all_jobs(self):
        # Lock dict to avoid someone else adding a new site during cancel operation
        self.mut_queues.lock()
        for id_site, site in self.__queues.items():
            # don't use get_site since mut_queue is already locked
            site.cancel_all_jobs()
        self.__queues.clear()
        if DEBUG:
            print("End Cancel")
        self.threadpool.waitForDone()
        self.mut_queues.unlock()

    def cancel_job(self, job: Job):
        # call cancel job of the site queue
        self.__queues[job.repo_id].cancel_job(job)
