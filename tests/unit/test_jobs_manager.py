import logging
import queue
import threading

from vorta.borg.jobs_manager import JobInterface, JobsManager, SiteWorker

SITE = 'test-site'


class RaisingJob(JobInterface):
    def repo_id(self):
        return SITE

    def cancel(self):
        pass

    def run(self):
        raise RuntimeError('job failed')


class FlagJob(JobInterface):
    def __init__(self):
        super().__init__()
        self.ran = threading.Event()

    def repo_id(self):
        return SITE

    def cancel(self):
        pass

    def run(self):
        self.ran.set()


def test_worker_survives_a_raising_job(qapp, monkeypatch, caplog):
    hook_calls = []
    monkeypatch.setattr(threading, 'excepthook', hook_calls.append)
    jobs = queue.Queue()
    # Held here, so these main-thread QObjects are not destroyed on the worker thread.
    first, second = RaisingJob(), FlagJob()
    jobs.put(first)
    jobs.put(second)
    worker = SiteWorker(jobs=jobs)

    with caplog.at_level(logging.ERROR):
        worker.start()
        worker.join(timeout=5)

    assert not worker.is_alive()
    assert second.ran.is_set()
    assert worker.current_job is None
    assert any(r.levelno == logging.ERROR and 'RaisingJob' in r.getMessage() for r in caplog.records)
    assert hook_calls == []


def test_jobs_manager_runs_the_next_job_after_a_raising_one(qapp):
    manager = JobsManager()
    first, second = RaisingJob(), FlagJob()

    manager.add_job(first)
    manager.add_job(second)

    assert second.ran.wait(timeout=5)
    for worker in list(manager.workers.values()):
        worker.join(timeout=5)
    assert not manager.is_worker_running(SITE)
