import queue
import logging
import threading
from abc import abstractmethod
from PyQt5.QtCore import QObject

logger = logging.getLogger(__name__)


class JobInterface(QObject):
    """
    To add a job to the vorta queue, you have to create a class which inherits Job. The inherited class
    must override run, cancel and repo_id. Since JobInterface inherits from QObject, you can use pyqt signal.
    """

    def __init__(self):
        super().__init__()

    # Must return the site id. In borg case, it is the id of the repository.
    @abstractmethod
    def repo_id(self):
        pass

    @abstractmethod
    def cancel(self):
        """
        Cancel can be called when the job is not started. It is the responsability of FuncJob to not cancel job if
        no job is running.
        The cancel mehod of JobsManager calls the cancel method on the running jobs only. Other jobs are dequeued.
        """
        pass

    # Put the code which must be run for a repo here. The code must be reentrant.
    @abstractmethod
    def run(self):
        pass


class SiteWorker(threading.Thread):
    """
    Runs jobs for a single site (mostly a single repo) in sequence. Used by JobsManager. Each
    site handles its own queue and processes the tasks. Since the loop is not
    launched in a thread, it is up to the calling function to do so.
    """

    def __init__(self, jobs):
        super().__init__()
        self.jobs = jobs
        self.current_job = None

    def run(self):
        while True:
            try:
                job = self.jobs.get(False)
                self.current_job = job
                logger.debug("Start job on site: %s", job.repo_id())
                job.run()
                logger.debug("Finish job for site: %s", job.repo_id())
            except queue.Empty:
                logger.debug("No more jobs for site: %s", job.repo_id())
                return


class JobsManager:
    """
    This class is a complete scheduler. Only use this class and not SiteWorker.
    This class MUST BE use as a singleton.

    Inspired by https://stackoverflow.com/a/50265824/3983708
    """

    def __init__(self):
        self.jobs = dict()  # jobs by site > queue
        self.workers = dict()  # threads by site
        self.jobs_lock = threading.Lock()  # for atomic queue operations, like cancelling

    def is_worker_running(self, site=None):
        """
        See if there are any active jobs. The user can't start a backup if a job is
        running. The scheduler can.
        """
        # Check status for specific site (repo)
        if site in self.workers:
            return self.workers[site].is_alive()
        else:
            return False

        # Check if *any* worker is active
        for _, worker in self.workers.items():
            if worker.is_alive():
                return True
        return False

    def add_job(self, job):
        logger.debug("Add job for site %s", job.repo_id())

        if not isinstance(job.repo_id(), (int, str)):
            logger.error("repo_id( must be an int or str. Got %s", type(job.repo_id()))
            return 1

        # Ensure a job queue exists for site/repo
        with self.jobs_lock:
            if job.repo_id() not in self.jobs:
                self.jobs[job.repo_id()] = queue.Queue()
        # Don't need lock when adding a job
        self.jobs[job.repo_id()].put(job)

        # If there is an existing thread for this site, do nothing. It will just
        # take the next job from the queue. If not, start a new thread.
        with self.jobs_lock:
            if job.repo_id() in self.workers and self.workers[job.repo_id()].is_alive():
                return
            else:
                self.workers[job.repo_id()] = SiteWorker(jobs=self.jobs[job.repo_id()])
                self.workers[job.repo_id()].start()

    def cancel_all_jobs(self):
        """
        Remove pending jobs and ask all workers to cancel their current jobs.
        """
        with self.jobs_lock:
            for site_id, worker in self.workers.items():
                if worker.is_alive():  # if a worker is active, first empty the queue
                    while not self.jobs[site_id].empty():
                        try:
                            self.jobs[site_id].get(False)
                        except queue.Empty:
                            continue
                        self.jobs[site_id].task_done()
                worker.current_job.cancel()

        logger.info("Finished cancelling all jobs")
