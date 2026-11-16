from datetime import datetime as dt
from datetime import timedelta

import pytest
from PyQt6.QtCore import QModelIndex, Qt

from vorta.store.models import BackupProfileModel, EventLogModel
from vorta.views.log_page import LogPage
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
    assert model.columnCount() == 6


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


@pytest.mark.parametrize('role', [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.UserRole])
def test_data_returns_formatted_time_and_string_fields(role):
    """`data()` formats the timestamp and exposes raw string fields per column."""
    model = EventLogTableModel()
    profile = BackupProfileModel.get(id=1)
    model.set_rows([_make_row(profile.id, dt(2024, 1, 15, 10, 30), repo_url='test-repo-url')])

    def cell(column):
        return model.data(model.index(0, column), role)

    assert cell(EventLogTableModel.COL_TIME) == '2024-01-15 10:30'
    assert cell(EventLogTableModel.COL_CATEGORY) == 'scheduled'
    assert cell(EventLogTableModel.COL_SUBCOMMAND) == 'create'
    assert cell(EventLogTableModel.COL_REPOSITORY) == 'test-repo-url'
    assert cell(EventLogTableModel.COL_RETURNCODE) == '0'


def test_data_returns_none_for_invalid_index_or_unsupported_role():
    """Unsupported roles and invalid indices yield None."""
    model = EventLogTableModel()
    profile = BackupProfileModel.get(id=1)
    model.set_rows([_make_row(profile.id, dt(2024, 1, 15, 10, 30))])

    assert model.data(QModelIndex()) is None
    assert model.data(model.index(0, 0), Qt.ItemDataRole.EditRole) is None


def test_header_data_returns_column_labels():
    """Horizontal headers expose the canonical column labels under DisplayRole."""
    model = EventLogTableModel()
    assert model.headerData(EventLogTableModel.COL_DURATION, Qt.Orientation.Horizontal) == 'Duration'
    assert (
        model.headerData(EventLogTableModel.COL_TIME, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) == 'Time'
    )
    assert (
        model.headerData(EventLogTableModel.COL_REPOSITORY, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
        == 'Repository'
    )
    assert model.headerData(0, Qt.Orientation.Vertical, Qt.ItemDataRole.DisplayRole) is None


@pytest.mark.parametrize(
    'seconds, returncode, expected',
    [
        (0, 0, '0:00:00'),
        (1.6, 0, '0:00:02'),
        (65, 1, '0:01:05'),
        (3600, 2, '1:00:00'),
        (90061, 0, '1 day, 1:01:01'),
        (20, -2, '0:00:20'),
        (20, -1, ''),
        (-10, 0, ''),
    ],
)
def test_duration(seconds, returncode, expected):
    start = dt(2026, 1, 1, 23, 59)
    row = EventLogModel(start_time=start, end_time=start + timedelta(seconds=seconds), returncode=returncode)
    model = EventLogTableModel()
    model.set_rows([row])
    index = model.index(0, model.COL_DURATION)
    assert model.data(index) == expected
    assert model.data(index, Qt.ItemDataRole.UserRole) == (seconds if expected else None)


@pytest.mark.parametrize('missing', ['start_time', 'end_time'])
def test_duration_with_missing_timestamp(missing):
    row = EventLogModel(start_time=dt(2026, 1, 1), end_time=dt(2026, 1, 2), returncode=0)
    setattr(row, missing, None)
    model = EventLogTableModel()
    model.set_rows([row])
    assert model.data(model.index(0, model.COL_DURATION)) == ''


def test_log_page_sorts_duration_numerically(qapp, qtbot):
    profile = BackupProfileModel.get(id=1)
    start = dt(2026, 1, 1)
    for seconds in [36000, 7200, 90000]:
        EventLogModel.create(
            category='user',
            profile=profile.id,
            subcommand='check',
            returncode=0,
            start_time=start,
            end_time=start + timedelta(seconds=seconds),
        )
    page = LogPage(profile_provider=lambda: profile)
    qtbot.addWidget(page)
    proxy = page.logPage.model()
    proxy.sort(EventLogTableModel.COL_DURATION, Qt.SortOrder.AscendingOrder)
    assert [proxy.index(i, EventLogTableModel.COL_DURATION).data() for i in range(3)] == [
        '2:00:00',
        '10:00:00',
        '1 day, 1:00:00',
    ]
