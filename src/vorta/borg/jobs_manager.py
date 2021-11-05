import queue
from enum import Enum
import logging
import threading

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    # dont add and option to put the item at the end of the queue.
    OK = 1
    CANCEL = 2


class SiteWorker(threading.Thread):
    """
    Runs jobs for a single site (mostly a single repo) in sequence. Used by JobsManager. Each
    site handles its own queue and processes the tasks. If no jobs are in the queue, the site
    waits until a job comes. If no jobs come, a timeout ends the loop. Since the loop is not
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
                if job.get_status() == JobStatus.OK:
                    logger.debug("Start job on site: %s", job.site_id)
                    job.run()
                    logger.debug("Finish job for site: %s", job.site_id)
            except queue.Empty:
                logger.debug("No more jobs for site: %s", job.site_id)
                return


class JobsManager:
    """
    This class is a complete scheduler. Only use this class and not SiteWorker.
    This class MUST BE use as a singleton.

    Inspired by https://stackoverflow.com/a/50265824/3983708
    """
    def __init__(self):
        self.jobs = {}  # jobs by site > queue
        self.workers = {}  # threads by site

    def is_worker_running(self):
        """
        See if there are any active jobs. The user can't start a backup if a job is
        running. The scheduler can.
        """
        for _, worker in self.workers.items():
            if worker.is_alive():
                return True
        return False

    def add_job(self, job):
        logger.debug("Add job for site %s", job.site_id)

        if not isinstance(job.site_id, (int, str)):
            logger.error("site_id must be an int or str. Got %s", type(job.repo_id()))
            return 1

        # Ensure a job queue exists for site/repo
        if job.site_id not in self.jobs:
            self.jobs[job.site_id] = queue.Queue()
        self.jobs[job.site_id].put(job)

        # If there is an existing thread for this site, do nothing. It will just
        # take the next job from the queue. If not, start a new thread.
        if job.site_id in self.workers and self.workers[job.site_id].is_alive():
            return
        else:
            self.workers[job.site_id] = SiteWorker(jobs=self.jobs[job.site_id])
            self.workers[job.site_id].start()

    def cancel_all_jobs(self):
        """
        Remove pending jobs and ask to all workers to cancel their current jobs.
        """
        for site_id, worker in self.workers.items():
            if worker.is_alive():
                while not self.jobs[site_id].empty():
                    try:
                        self.jobs[site_id].get(False)
                    except queue.Empty:
                        continue
                    self.jobs[site_id].task_done()
            worker.current_job.cancel()

        logger.info("Finished cancelling all jobs")
