from datetime import datetime as dt

from vorta.store.models import BackupProfileModel, EventLogModel
from vorta.views.viewmodels.log_page_viewmodel import LogPageViewModel


def test_get_event_logs_returns_data():
    """Test that the ViewModel returns log entries for a profile."""
    viewmodel = LogPageViewModel()
    profile = BackupProfileModel.get(id=1)

    EventLogModel.create(
        category='scheduled',
        subcommand='create',
        repo_url='test-repo-url',
        returncode=0,
        profile=profile.id,
        start_time=dt(2024, 1, 15, 10, 30),
    )

    logs = viewmodel.get_event_logs(profile.id)

    assert len(logs) == 1
    assert logs[0].category == 'scheduled'
    assert logs[0].subcommand == 'create'
    assert logs[0].repo_url == 'test-repo-url'
    assert logs[0].returncode == 0


def test_get_event_logs_empty_profile():
    """Test that the ViewModel returns an empty list for a profile with no logs."""
    viewmodel = LogPageViewModel()
    profile = BackupProfileModel.get(id=1)

    logs = viewmodel.get_event_logs(profile.id)

    assert len(logs) == 0


def test_get_event_logs_ordering():
    """Test that logs are returned in descending order by start_time."""
    viewmodel = LogPageViewModel()
    profile = BackupProfileModel.get(id=1)

    EventLogModel.create(
        category='scheduled',
        subcommand='create',
        repo_url='repo1',
        returncode=0,
        profile=profile.id,
        start_time=dt(2024, 1, 10, 8, 0),
    )
    EventLogModel.create(
        category='scheduled',
        subcommand='prune',
        repo_url='repo1',
        returncode=0,
        profile=profile.id,
        start_time=dt(2024, 1, 15, 12, 0),
    )
    EventLogModel.create(
        category='user',
        subcommand='create',
        repo_url='repo1',
        returncode=0,
        profile=profile.id,
        start_time=dt(2024, 1, 12, 9, 0),
    )

    logs = viewmodel.get_event_logs(profile.id)

    assert len(logs) == 3
    assert logs[0].start_time > logs[1].start_time
    assert logs[1].start_time > logs[2].start_time
