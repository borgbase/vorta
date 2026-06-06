from datetime import datetime as dt

from PyQt6.QtCore import QModelIndex, Qt

from vorta.store.models import ArchiveModel
from vorta.views.partials.archive_table_model import ArchiveTableModel


def _archive(name, time, size=1000, duration=60, trigger='user'):
    """Build an in-memory ArchiveModel (not persisted) for feeding the model."""
    return ArchiveModel(name=name, time=time, size=size, duration=duration, trigger=trigger, snapshot_id='x')


def test_model_is_empty_before_set_rows():
    """Column count is intrinsic; row count starts at zero."""
    model = ArchiveTableModel()
    assert model.rowCount() == 0
    assert model.columnCount() == 6


def test_set_rows_populates_and_preserves_order():
    """`set_rows` replaces the contents and keeps the given row order."""
    model = ArchiveTableModel()
    model.set_rows(
        [
            _archive('a', dt(2024, 1, 3)),
            _archive('b', dt(2024, 1, 1)),
            _archive('c', dt(2024, 1, 2)),
        ]
    )

    assert model.rowCount() == 3
    names = [model.data(model.index(r, ArchiveTableModel.COL_NAME)) for r in range(3)]
    assert names == ['a', 'b', 'c']


def test_display_data_formats_each_column():
    """`data()` formats time/size/duration and exposes name; trigger is icon-only."""
    model = ArchiveTableModel()
    model.set_rows([_archive('my-archive', dt(2024, 1, 15, 10, 30), size=1500, duration=90, trigger='user')])

    def cell(column):
        return model.data(model.index(0, column), Qt.ItemDataRole.DisplayRole)

    assert cell(ArchiveTableModel.COL_TIME) == '2024-01-15 10:30'
    assert cell(ArchiveTableModel.COL_SIZE) == '1.5 KB'
    assert cell(ArchiveTableModel.COL_DURATION) == '0:01:30'
    assert cell(ArchiveTableModel.COL_MOUNT) == ''
    assert cell(ArchiveTableModel.COL_NAME) == 'my-archive'
    assert cell(ArchiveTableModel.COL_TRIGGER) is None


def test_mount_point_is_shown_when_present():
    """The mount column reflects the mount_points map passed to set_rows."""
    model = ArchiveTableModel()
    model.set_rows([_archive('m', dt(2024, 1, 1))], mount_points={'m': '/mnt/x'})
    assert model.data(model.index(0, ArchiveTableModel.COL_MOUNT)) == '/mnt/x'


def test_duration_none_renders_empty():
    """A null duration renders as an empty string."""
    model = ArchiveTableModel()
    model.set_rows([_archive('d', dt(2024, 1, 1), duration=None)])
    assert model.data(model.index(0, ArchiveTableModel.COL_DURATION)) == ''


def test_fixed_units_share_one_unit_across_rows():
    """With use_fixed_units, every row uses the same unit; dynamic sizes each independently."""
    model = ArchiveTableModel()
    rows = [_archive('small', dt(2024, 1, 1), size=2000), _archive('big', dt(2024, 1, 2), size=5_000_000_000)]

    model.set_rows(rows, use_fixed_units=True)
    fixed = [model.data(model.index(r, ArchiveTableModel.COL_SIZE)) for r in range(2)]
    assert fixed == ['2.0 KB', '5000000.0 KB']  # both rows pinned to the same shared unit

    model.set_rows(rows, use_fixed_units=False)
    assert model.data(model.index(1, ArchiveTableModel.COL_SIZE)) == '5.0 GB'  # dynamic: own best unit


def test_sort_role_returns_native_comparable_values():
    """SortRole yields raw values so columns sort numerically/chronologically, not by text."""
    model = ArchiveTableModel()
    t = dt(2024, 1, 15, 10, 30)
    model.set_rows([_archive('z-name', t, size=2048, duration=12.5, trigger='scheduled')])

    def sort_value(column):
        return model.data(model.index(0, column), ArchiveTableModel.SortRole)

    assert sort_value(ArchiveTableModel.COL_TIME) == t
    assert sort_value(ArchiveTableModel.COL_SIZE) == 2048
    assert sort_value(ArchiveTableModel.COL_DURATION) == 12.5
    assert sort_value(ArchiveTableModel.COL_NAME) == 'z-name'
    assert sort_value(ArchiveTableModel.COL_TRIGGER) == 'scheduled'


def test_sort_role_orders_sizes_numerically():
    """Raw size sort keys order correctly where display strings would not."""
    model = ArchiveTableModel()
    model.set_rows([_archive('big', dt(2024, 1, 1), size=2048), _archive('small', dt(2024, 1, 2), size=999)])

    keys = [model.data(model.index(r, ArchiveTableModel.COL_SIZE), ArchiveTableModel.SortRole) for r in range(2)]
    assert keys == [2048, 999]
    assert keys[1] < keys[0]  # 999 < 2048, even though '999 B' > '2.0 kB' as text


def test_only_name_column_is_editable():
    """The name column is editable; the others are not."""
    model = ArchiveTableModel()
    model.set_rows([_archive('n', dt(2024, 1, 1))])

    name_flags = model.flags(model.index(0, ArchiveTableModel.COL_NAME))
    time_flags = model.flags(model.index(0, ArchiveTableModel.COL_TIME))
    assert name_flags & Qt.ItemFlag.ItemIsEditable
    assert not (time_flags & Qt.ItemFlag.ItemIsEditable)


def test_set_data_updates_name_and_emits_datachanged():
    """Editing the name updates the backing row and notifies views."""
    model = ArchiveTableModel()
    model.set_rows([_archive('old', dt(2024, 1, 1))])

    received = []
    model.dataChanged.connect(lambda tl, br, roles=[]: received.append((tl.row(), tl.column())))

    assert model.setData(model.index(0, ArchiveTableModel.COL_NAME), 'new') is True
    assert model.archive_at(0).name == 'new'
    assert received == [(0, ArchiveTableModel.COL_NAME)]


def test_set_data_rejects_non_name_column_or_wrong_role():
    """setData only accepts EditRole writes to the name column."""
    model = ArchiveTableModel()
    model.set_rows([_archive('x', dt(2024, 1, 1))])

    assert model.setData(model.index(0, ArchiveTableModel.COL_TIME), 'y') is False
    assert model.setData(model.index(0, ArchiveTableModel.COL_NAME), 'y', Qt.ItemDataRole.DisplayRole) is False


def test_archive_at_returns_object_or_none():
    """archive_at returns the backing ArchiveModel and None when out of range."""
    model = ArchiveTableModel()
    only = _archive('only', dt(2024, 1, 1))
    model.set_rows([only])

    assert model.archive_at(0) is only
    assert model.archive_at(5) is None
    assert model.archive_at(-1) is None


def test_trigger_icon_and_tooltip():
    """The trigger column exposes an icon and tooltip per trigger kind."""
    model = ArchiveTableModel()
    model.set_rows(
        [
            _archive('s', dt(2024, 1, 1), trigger='scheduled'),
            _archive('u', dt(2024, 1, 2), trigger='user'),
            _archive('n', dt(2024, 1, 3), trigger=None),
        ]
    )

    def deco(row):
        return model.data(model.index(row, ArchiveTableModel.COL_TRIGGER), Qt.ItemDataRole.DecorationRole)

    def tooltip(row):
        return model.data(model.index(row, ArchiveTableModel.COL_TRIGGER), Qt.ItemDataRole.ToolTipRole)

    assert deco(0) is not None and deco(1) is not None
    assert deco(2) is None
    assert tooltip(0) == 'Scheduled'
    assert tooltip(1) == 'User initiated'
    assert tooltip(2) is None


def test_header_data_returns_column_labels():
    """Horizontal headers expose the canonical labels; the icon column is blank."""
    model = ArchiveTableModel()
    assert (
        model.headerData(ArchiveTableModel.COL_TIME, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) == 'Date'
    )
    assert (
        model.headerData(ArchiveTableModel.COL_NAME, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) == 'Name'
    )
    assert model.headerData(ArchiveTableModel.COL_TRIGGER, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) == ''
    assert model.headerData(0, Qt.Orientation.Vertical, Qt.ItemDataRole.DisplayRole) is None


def test_data_returns_none_for_invalid_index_or_unsupported_role():
    """Invalid indices and unhandled roles yield None."""
    model = ArchiveTableModel()
    model.set_rows([_archive('x', dt(2024, 1, 1))])

    assert model.data(QModelIndex()) is None
    assert model.data(model.index(0, ArchiveTableModel.COL_TIME), Qt.ItemDataRole.EditRole) is None
