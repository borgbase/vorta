import logging
import queue
import threading
from abc import abstractmethod

from PyQt6.QtCore import QObject, pyqtSlot

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
        Cancel can be called when the job is not started. It is the responsibility of FuncJob to not cancel job if
        no job is running.
        The cancel method of JobsManager calls the cancel method on the running jobs only. Other jobs are dequeued.
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
        job = None
        while True:
            try:
                job = self.jobs.get(False)
                self.current_job = job
                logger.debug("Start job on site: %s", job.repo_id())
                job.run()
                self.current_job = None
                logger.debug("Finish job for site: %s", job.repo_id())
            except queue.Empty:
                if job is not None:
                    logger.debug("No more jobs for site: %s", job.repo_id())
                return


class JobsManager(QObject):
    """
    This class is a complete scheduler. Only use this class and not SiteWorker.
    This class MUST BE use as a singleton.

    Inspired by https://stackoverflow.com/a/50265824/3983708
    """

    def __init__(self):
        super().__init__()
        self.queued_jobs = dict()  # job list by site (queue)
        self.active_jobs = dict()  # current (job, inhibitor) by site

    def is_worker_running(self, site=None):
        """
        See if there are any active jobs.
        The user can't start a backup if a job is running. The scheduler can.

        Checks if a job is queued or currently running for the site
        """
        return (site in self.queued_jobs and self.queued_jobs[site]) or (
            site in self.active_jobs and self.active_jobs[site]
        )

    def add_job(self, job):
        logger.debug("Add job for site %s", job.repo_id())

        if not isinstance(job.repo_id(), (int, str)):
            logger.error("repo_id( must be an int or str. Got %s", type(job.repo_id()))
            return 1

        repo_id = job.repo_id()

        # There is no active job here, we can start it
        if repo_id not in self.active_jobs:
            self._job_start(job)
        else:
            if repo_id not in self.queued_jobs:
                self.queued_jobs[repo_id] = []
            self.queued_jobs[repo_id].append(job)

    def cancel_all_jobs(self):
        """
        Remove pending jobs and ask all workers to cancel their current jobs.
        """
        raise NotImplementedError()
        with self.jobs_lock:
            for site_id, worker in self.workers.items():
                if worker.is_alive():  # if a worker is active, first empty the queue
                    while not self.jobs[site_id].empty():
                        try:
                            self.jobs[site_id].get(False)
                        except queue.Empty:
                            continue
                        self.jobs[site_id].task_done()
                if worker.current_job is not None:
                    worker.current_job.cancel()

        logger.info("Finished cancelling all jobs")

    def _job_start(self, job):
        # Assumes inside the jobs_lock
        # Move the job onto the current thread so emissions happen on the right thread
        inhibitor = job.get_inhibitor()
        job.result.connect(lambda _r: self._job_ended(job.repo_id()))
        self.active_jobs[job.repo_id()] = (job, inhibitor)
        inhibitor.inhibit()
        job.run()

    @pyqtSlot(QObject)
    def _job_ended(self, repo_id: str):
        # Release the active inhibitor and then see if there is another queued job
        # Assumes internal state is as expected
        _, inhibitor = self.active_jobs[repo_id]
        inhibitor.uninhibit()

        del self.active_jobs[repo_id]

        if repo_id in self.queued_jobs and self.queued_jobs[repo_id]:
            next_job = self.queued_jobs[repo_id].pop(0)
            self._job_start(next_job)
