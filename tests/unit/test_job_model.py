from vorta.store.models import EventLogModel, JobModel


def test_job_links_to_event_log():
    """A job's execution result is reached through the event_log relation."""
    log = EventLogModel.create(category='scheduled', subcommand='create')
    job = JobModel.create(profile=1, status='done', event_log=log)

    assert job.event_log.id == log.id
    assert list(log.job)[0].id == job.id
