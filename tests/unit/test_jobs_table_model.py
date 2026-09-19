from datetime import datetime as dt

from PyQt6.QtCore import Qt

from vorta.scheduler import PendingJob
from vorta.store.models import JobModel
from vorta.views.partials.jobs_filter_proxy import JobsFilterProxyModel
from vorta.views.partials.jobs_table_model import JobRow, JobsTableModel


def _make_record(
    created_at,
    status=JobModel.Status.SKIPPED.value,
    reason='Repository is busy with another job.',
    profile_name='Default',
    repo_url='test-repo-url',
):
    return JobModel.create(
        profile=1,
        profile_name=profile_name,
        repo_url=repo_url,
        job_type=JobModel.Type.BACKUP.value,
        status=status,
        trigger=JobModel.Trigger.SCHEDULED.value,
        reason=reason,
        created_at=created_at,
    )


def _make_pending(
    scheduled_at,
    status=JobModel.Status.SCHEDULED.value,
    profile_name='Default',
    repo_url='test-repo-url',
):
    return PendingJob(1, profile_name, repo_url, scheduled_at, status)


def test_data_exposes_record_fields():
    """A stored job renders its own status, trigger and reason."""
    model = JobsTableModel()
    model.set_rows([JobRow.from_record(_make_record(dt(2024, 1, 15, 10, 30)))])

    def cell(column):
        return model.data(model.index(0, column), Qt.ItemDataRole.DisplayRole)

    assert cell(JobsTableModel.COL_TIME) == '2024-01-15 10:30'
    assert cell(JobsTableModel.COL_PROFILE) == 'Default'
    assert cell(JobsTableModel.COL_REPOSITORY) == 'test-repo-url'
    assert cell(JobsTableModel.COL_TYPE) == 'backup'
    assert cell(JobsTableModel.COL_TRIGGER) == 'scheduled'
    assert cell(JobsTableModel.COL_STATUS) == 'skipped'
    assert cell(JobsTableModel.COL_REASON) == 'Repository is busy with another job.'


def test_pending_run_renders_as_a_scheduled_backup():
    """A run that only exists as a timer reads as scheduled, with nothing to explain."""
    model = JobsTableModel()
    model.set_rows([JobRow.from_pending(_make_pending(dt(2024, 1, 16, 9, 0)))])

    def cell(column):
        return model.data(model.index(0, column), Qt.ItemDataRole.DisplayRole)

    assert cell(JobsTableModel.COL_TIME) == '2024-01-16 09:00'
    assert cell(JobsTableModel.COL_PROFILE) == 'Default'
    assert cell(JobsTableModel.COL_REPOSITORY) == 'test-repo-url'
    assert cell(JobsTableModel.COL_TYPE) == 'backup'
    assert cell(JobsTableModel.COL_TRIGGER) == 'scheduled'
    assert cell(JobsTableModel.COL_STATUS) == 'scheduled'
    assert cell(JobsTableModel.COL_REASON) is None


def test_pending_run_keeps_the_status_the_scheduler_gave_it():
    """A paused profile still holds a time, and the row says so rather than claiming a run is coming."""
    model = JobsTableModel()
    model.set_rows([JobRow.from_pending(_make_pending(dt(2024, 1, 16, 9, 0), JobModel.Status.PAUSED.value))])

    assert model.data(model.index(0, JobsTableModel.COL_STATUS), Qt.ItemDataRole.DisplayRole) == 'paused'


def test_sort_keys_compare_raw_values():
    """The shared sort proxy sorts on `UserRole`, so times must compare as times, not as strings."""
    model = JobsTableModel()
    model.set_rows(
        [
            JobRow.from_record(_make_record(dt(2024, 1, 15, 10, 30))),
            JobRow.from_pending(_make_pending(dt(2024, 1, 16, 9, 0))),
        ]
    )

    def key(row, column):
        return model.data(model.index(row, column), Qt.ItemDataRole.UserRole)

    assert key(0, JobsTableModel.COL_TIME) < key(1, JobsTableModel.COL_TIME)
    assert key(0, JobsTableModel.COL_STATUS) == 'skipped'


def _filtered_rows():
    """Two stored jobs and one pending run, spread over two profiles and two repositories."""
    return [
        JobRow.from_record(_make_record(dt(2024, 1, 15, 10, 30), repo_url='repo-a')),
        JobRow.from_record(
            _make_record(
                dt(2024, 1, 15, 11, 30),
                status=JobModel.Status.FAILED.value,
                profile_name='Photos',
                repo_url='repo-b',
            )
        ),
        JobRow.from_pending(_make_pending(dt(2024, 1, 16, 9, 0), profile_name='Photos', repo_url='repo-a')),
    ]


def _proxy_over(rows):
    model = JobsTableModel()
    model.set_rows(rows)
    proxy = JobsFilterProxyModel()
    proxy.setSourceModel(model)
    return model, proxy


def test_unfiltered_proxy_shows_every_row():
    """No selection means no filtering, so the page renders exactly as it did before filters existed."""
    _, proxy = _proxy_over(_filtered_rows())

    assert proxy.rowCount() == 3


def test_each_filter_narrows_the_rows_on_its_own():
    """Every filterable column drops the rows that do not carry the selected value."""
    for column, value, expected in (
        (JobsTableModel.COL_PROFILE, 'Photos', 2),
        (JobsTableModel.COL_REPOSITORY, 'repo-a', 2),
        (JobsTableModel.COL_STATUS, JobModel.Status.FAILED.value, 1),
    ):
        _, proxy = _proxy_over(_filtered_rows())
        proxy.set_filter(column, value)

        assert proxy.rowCount() == expected


def test_two_filters_combine_as_and():
    """Selections narrow each other rather than widening the result."""
    _, proxy = _proxy_over(_filtered_rows())

    proxy.set_filter(JobsTableModel.COL_PROFILE, 'Photos')
    proxy.set_filter(JobsTableModel.COL_REPOSITORY, 'repo-a')

    statuses = [proxy.data(proxy.index(row, JobsTableModel.COL_STATUS)) for row in range(proxy.rowCount())]
    assert statuses == [JobModel.Status.SCHEDULED.value]


def test_qt_own_filtering_still_composes():
    """`filterAcceptsRow` chains to the base class, so `setFilterFixedString` is not silently ignored."""
    _, proxy = _proxy_over(_filtered_rows())

    proxy.setFilterKeyColumn(JobsTableModel.COL_REPOSITORY)
    proxy.setFilterFixedString('repo-b')

    assert proxy.rowCount() == 1


def test_clearing_a_filter_restores_the_hidden_rows():
    """Selecting "All" again has to undo the narrowing, not leave the proxy stuck."""
    _, proxy = _proxy_over(_filtered_rows())

    proxy.set_filter(JobsTableModel.COL_STATUS, JobModel.Status.FAILED.value)
    proxy.set_filter(JobsTableModel.COL_STATUS, None)

    assert proxy.rowCount() == 3


def test_filter_survives_a_reload_of_the_source_rows():
    """A backup finishing mid-filter must not reset the view the user set up."""
    model, proxy = _proxy_over(_filtered_rows())
    proxy.set_filter(JobsTableModel.COL_PROFILE, 'Photos')

    model.set_rows(
        _filtered_rows()
        + [JobRow.from_record(_make_record(dt(2024, 1, 17, 8, 0), profile_name='Photos', repo_url='repo-c'))]
    )

    assert proxy.rowCount() == 3
