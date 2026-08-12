from datetime import datetime as dt

from PyQt6.QtCore import Qt

from vorta.scheduler import PendingJob
from vorta.store.models import JobModel
from vorta.views.partials.jobs_table_model import JobRow, JobsTableModel


def _make_record(created_at, status=JobModel.Status.SKIPPED.value, reason='Repository is busy with another job.'):
    return JobModel.create(
        profile=1,
        profile_name='Default',
        repo_url='test-repo-url',
        job_type=JobModel.Type.BACKUP.value,
        status=status,
        trigger=JobModel.Trigger.SCHEDULED.value,
        reason=reason,
        created_at=created_at,
    )


def _make_pending(scheduled_at):
    return PendingJob(1, 'Default', 'test-repo-url', scheduled_at)


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
