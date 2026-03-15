from datetime import datetime as dt
from datetime import timedelta as td
from unittest.mock import MagicMock

import pytest

import vorta.borg.borg_job
import vorta.scheduler
from vorta.scheduler import VortaScheduler
from vorta.store.models import BackupProfileModel, EventLogModel, JobModel

PROFILE_NAME = 'Default'


@pytest.fixture
def clockmock(monkeypatch):
    datetime_mock = MagicMock(wraps=dt)
    monkeypatch.setattr(vorta.scheduler, "dt", datetime_mock)

    return datetime_mock


@pytest.fixture
def mock_borg_create(mocker, borg_json_output):
    stdout, stderr = borg_json_output('create')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)
    mocker.patch.object(vorta.borg.borg_job.BorgJob, 'prepare_bin', return_value='borg')
    mocker.patch.object(vorta.borg.borg_job.os, 'set_blocking', return_value=None, create=True)
    mocker.patch.object(vorta.borg.borg_job.select, 'select', side_effect=lambda r, w, x, t: (r, w, x))


def test_job_model_defaults():
    profile = BackupProfileModel.get(name=PROFILE_NAME)

    job = JobModel.create(profile=profile, repo=profile.repo, job_type='create')

    assert job.source == JobModel.SourceFieldOptions.USER.value
    assert job.status == JobModel.StatusFieldOptions.PENDING.value
    assert job.event_log is None


def test_scheduler_creates_pending_job_record(clockmock):
    scheduler = VortaScheduler()
    time = dt(2020, 5, 6, 4, 30)
    clockmock.now.return_value = time

    profile = BackupProfileModel.get(name=PROFILE_NAME)
    profile.schedule_make_up_missed = False
    profile.schedule_mode = 'interval'
    profile.schedule_interval_unit = 'hours'
    profile.schedule_interval_count = 3
    profile.save()

    EventLogModel(
        subcommand='create',
        profile=profile.id,
        returncode=0,
        category='scheduled',
        start_time=time,
        end_time=time,
    ).save()

    scheduler.set_timer_for_profile(profile.id)

    job = JobModel.get()
    assert job.profile.id == profile.id
    assert job.repo.id == profile.repo.id
    assert job.job_type == 'create'
    assert job.source == JobModel.SourceFieldOptions.SCHEDULED.value
    assert job.status == JobModel.StatusFieldOptions.PENDING.value
    assert job.scheduled_for == time + td(hours=3)
    assert job.metadata == {'schedule_mode': 'interval'}


def test_scheduler_links_scheduled_job_result(qapp, qtbot, mock_borg_create):
    profile = BackupProfileModel.get(name=PROFILE_NAME)
    profile.validation_on = False
    profile.prune_on = False
    profile.compaction_on = False
    profile.save()

    job = JobModel.create(
        profile=profile,
        repo=profile.repo,
        job_type='create',
        source=JobModel.SourceFieldOptions.SCHEDULED.value,
        status=JobModel.StatusFieldOptions.PENDING.value,
        scheduled_for=dt.now(),
    )

    with qtbot.waitSignal(qapp.backup_finished_event, **pytest._wait_defaults):
        qapp.scheduler.create_backup(profile.id, job.id)

    job = JobModel.get_by_id(job.id)
    assert job.status == JobModel.StatusFieldOptions.SUCCESS.value
    assert job.event_log is not None
    assert job.queued_at is not None
    assert job.started_at is not None
    assert job.finished_at is not None


def test_scheduler_marks_repo_busy_job_skipped(qapp, mocker):
    profile = BackupProfileModel.get(name=PROFILE_NAME)
    job = JobModel.create(
        profile=profile,
        repo=profile.repo,
        job_type='create',
        source=JobModel.SourceFieldOptions.SCHEDULED.value,
        status=JobModel.StatusFieldOptions.PENDING.value,
        scheduled_for=dt.now(),
    )

    mocker.patch.object(qapp.jobs_manager, 'is_worker_running', return_value=True)

    qapp.scheduler.create_backup(profile.id, job.id)

    job = JobModel.get_by_id(job.id)
    assert job.status == JobModel.StatusFieldOptions.SKIPPED.value
    assert job.skip_reason_code == 'repo_busy'


def test_scheduler_marks_prepare_failure_job_skipped(qapp, mocker):
    profile = BackupProfileModel.get(name=PROFILE_NAME)
    job = JobModel.create(
        profile=profile,
        repo=profile.repo,
        job_type='create',
        source=JobModel.SourceFieldOptions.SCHEDULED.value,
        status=JobModel.StatusFieldOptions.PENDING.value,
        scheduled_for=dt.now(),
    )

    mocker.patch.object(vorta.scheduler.BorgCreateJob, 'prepare', return_value={'ok': False, 'message': 'Nope.'})

    qapp.scheduler.create_backup(profile.id, job.id)

    job = JobModel.get_by_id(job.id)
    assert job.status == JobModel.StatusFieldOptions.SKIPPED.value
    assert job.skip_reason_code == 'preparation_failed'
    assert job.skip_reason_text == 'Nope.'
