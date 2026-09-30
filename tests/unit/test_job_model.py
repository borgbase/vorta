from datetime import datetime, timedelta

import vorta.store.connection
from vorta.store.models import EventLogModel, JobModel


def test_job_links_to_event_log():
    """A job's execution result is reached through the event_log relation."""
    log = EventLogModel.create(category='scheduled', subcommand='create')
    job = JobModel.create(profile=1, status=JobModel.Status.COMPLETED.value, event_log=log)

    assert job.event_log.id == log.id
    assert [j.id for j in log.jobs] == [job.id]


def test_old_jobs_are_purged_on_init():
    """Job records older than six months are dropped when the DB is opened."""
    old = JobModel.create(profile=1, created_at=datetime.now() - timedelta(days=200))
    recent = JobModel.create(profile=1, created_at=datetime.now() - timedelta(days=20))

    vorta.store.connection.init_db()

    assert JobModel.get_or_none(id=old.id) is None
    assert JobModel.get_or_none(id=recent.id) is not None
