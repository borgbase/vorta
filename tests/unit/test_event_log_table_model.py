from datetime import datetime as dt

from PyQt6.QtCore import QModelIndex, Qt

from vorta.store.models import BackupProfileModel, EventLogModel
from vorta.views.partials.event_log_table_model import EventLogTableModel


def _make_row(profile_id, start_time, category='scheduled', subcommand='create', repo_url='repo1', returncode=0):
    return EventLogModel.create(
        category=category,
        subcommand=subcommand,
        repo_url=repo_url,
        returncode=returncode,
        profile=profile_id,
        start_time=start_time,
    )


def test_model_is_empty_before_set_rows():
    """Column count is intrinsic; row count starts at zero."""
    model = EventLogTableModel()
    assert model.rowCount() == 0
    assert model.columnCount() == 5


def test_set_rows_populates_model():
    """`set_rows` replaces the contents and rowCount reflects the new data."""
    model = EventLogTableModel()
    profile = BackupProfileModel.get(id=1)

    rows = [
        _make_row(profile.id, dt(2024, 1, 10, 8, 0)),
        _make_row(profile.id, dt(2024, 1, 15, 12, 0), subcommand='prune'),
    ]
    model.set_rows(rows)

    assert model.rowCount() == 2


def test_data_returns_formatted_time_and_string_fields():
    """`data()` formats the timestamp and exposes raw string fields per column."""
    model = EventLogTableModel()
    profile = BackupProfileModel.get(id=1)
    model.set_rows([_make_row(profile.id, dt(2024, 1, 15, 10, 30), repo_url='test-repo-url')])

    def cell(column):
        return model.data(model.index(0, column), Qt.ItemDataRole.DisplayRole)

    assert cell(EventLogTableModel.COL_TIME) == '2024-01-15 10:30'
    assert cell(EventLogTableModel.COL_CATEGORY) == 'scheduled'
    assert cell(EventLogTableModel.COL_SUBCOMMAND) == 'create'
    assert cell(EventLogTableModel.COL_REPOSITORY) == 'test-repo-url'
    assert cell(EventLogTableModel.COL_RETURNCODE) == '0'


def test_data_returns_none_for_invalid_index_or_unsupported_role():
    """Non-DisplayRole queries and invalid indices yield None."""
    model = EventLogTableModel()
    profile = BackupProfileModel.get(id=1)
    model.set_rows([_make_row(profile.id, dt(2024, 1, 15, 10, 30))])

    assert model.data(QModelIndex()) is None
    assert model.data(model.index(0, 0), Qt.ItemDataRole.EditRole) is None


def test_header_data_returns_column_labels():
    """Horizontal headers expose the canonical column labels under DisplayRole."""
    model = EventLogTableModel()
    assert (
        model.headerData(EventLogTableModel.COL_TIME, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) == 'Time'
    )
    assert (
        model.headerData(EventLogTableModel.COL_REPOSITORY, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
        == 'Repository'
    )
    assert model.headerData(0, Qt.Orientation.Vertical, Qt.ItemDataRole.DisplayRole) is None
