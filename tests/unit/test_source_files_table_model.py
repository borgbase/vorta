from PyQt6.QtCore import QModelIndex, Qt

from vorta.store.models import SourceFileModel
from vorta.views.partials.source_files_table_model import SourceFilesModel


def _source(dir, dir_size=-1, dir_files_count=-1, path_isdir=False):
    """Build an in-memory SourceFileModel (not persisted) for feeding the model."""
    return SourceFileModel(dir=dir, dir_size=dir_size, dir_files_count=dir_files_count, path_isdir=path_isdir)


def test_model_is_empty_before_set_rows():
    """Column count is intrinsic; row count starts at zero."""
    model = SourceFilesModel()
    assert model.rowCount() == 0
    assert model.columnCount() == 3


def test_set_rows_populates_and_preserves_order():
    """`set_rows` replaces the contents and keeps the given row order."""
    model = SourceFilesModel()
    model.set_rows([_source('/a'), _source('/b'), _source('/c')])

    assert model.rowCount() == 3
    paths = [model.data(model.index(r, SourceFilesModel.COL_PATH)) for r in range(3)]
    assert paths == ['/a', '/b', '/c']


def test_display_data_for_calculated_directory():
    """A calculated directory shows its path, pretty size, and file count."""
    model = SourceFilesModel()
    model.set_rows([_source('/data', dir_size=1500, dir_files_count=12, path_isdir=True)])

    def cell(column):
        return model.data(model.index(0, column), Qt.ItemDataRole.DisplayRole)

    assert cell(SourceFilesModel.COL_PATH) == '/data'
    assert cell(SourceFilesModel.COL_SIZE) == '1.5 KB'
    assert cell(SourceFilesModel.COL_FILES) == '12'


def test_file_entry_has_no_file_count():
    """A single file shows its size but no file count."""
    model = SourceFilesModel()
    model.set_rows([_source('/f.txt', dir_size=1500, dir_files_count=99, path_isdir=False)])
    assert model.data(model.index(0, SourceFilesModel.COL_FILES)) == ''
    assert model.data(model.index(0, SourceFilesModel.COL_SIZE)) == '1.5 KB'


def test_uncalculated_source_renders_empty_size_and_count():
    """A freshly added source (size/count -1) renders blank cells, not numbers."""
    model = SourceFilesModel()
    model.set_rows([_source('/new', path_isdir=True)])
    assert model.data(model.index(0, SourceFilesModel.COL_SIZE)) == ''
    assert model.data(model.index(0, SourceFilesModel.COL_FILES)) == ''


def test_mark_calculating_shows_placeholder_then_clears():
    """`mark_calculating` shows the placeholder; `set_path_info` replaces it with results."""
    model = SourceFilesModel()
    model.set_rows([_source('/d', path_isdir=True)])

    model.mark_calculating('/d')
    assert model.data(model.index(0, SourceFilesModel.COL_SIZE)) == 'Calculating…'
    assert model.data(model.index(0, SourceFilesModel.COL_FILES)) == 'Calculating…'

    model.set_path_info('/d', 1500, 7, True)
    assert model.data(model.index(0, SourceFilesModel.COL_SIZE)) == '1.5 KB'
    assert model.data(model.index(0, SourceFilesModel.COL_FILES)) == '7'


def test_set_path_info_updates_backing_row_and_emits():
    """`set_path_info` writes through to the backing row and notifies views."""
    model = SourceFilesModel()
    source = _source('/d', path_isdir=True)
    model.set_rows([source])

    received = []
    model.dataChanged.connect(lambda tl, br, roles=[]: received.append((tl.row(), br.column())))

    assert model.set_path_info('/d', 2048, 3, True) is source
    assert source.dir_size == 2048
    assert source.dir_files_count == 3
    assert received == [(0, SourceFilesModel.COL_FILES)]


def test_set_path_info_for_unknown_path_is_a_noop():
    """A result arriving for a row removed mid-calculation is silently dropped (#1080 / #2435)."""
    model = SourceFilesModel()
    model.set_rows([_source('/kept', path_isdir=True)])

    assert model.set_path_info('/gone', 1000, 5, True) is None  # must not raise; caller skips save
    assert model.rowCount() == 1
    assert model.data(model.index(0, SourceFilesModel.COL_PATH)) == '/kept'


def test_add_source_appends_and_returns_row():
    """`add_source` appends a row and returns its index."""
    model = SourceFilesModel()
    model.set_rows([_source('/a')])

    row = model.add_source(_source('/b'))
    assert row == 1
    assert model.rowCount() == 2
    assert model.data(model.index(1, SourceFilesModel.COL_PATH)) == '/b'


def test_sort_role_returns_native_comparable_values():
    """SortRole yields raw values so size/count sort numerically, not by text."""
    model = SourceFilesModel()
    model.set_rows([_source('/z', dir_size=2048, dir_files_count=9, path_isdir=True)])

    def sort_value(column):
        return model.data(model.index(0, column), SourceFilesModel.SortRole)

    assert sort_value(SourceFilesModel.COL_PATH) == '/z'
    assert sort_value(SourceFilesModel.COL_SIZE) == 2048
    assert sort_value(SourceFilesModel.COL_FILES) == 9


def test_sort_role_orders_sizes_numerically():
    """Raw size sort keys order correctly where display strings would not."""
    model = SourceFilesModel()
    model.set_rows([_source('/big', dir_size=2048), _source('/small', dir_size=999)])

    keys = [model.data(model.index(r, SourceFilesModel.COL_SIZE), SourceFilesModel.SortRole) for r in range(2)]
    assert keys == [2048, 999]
    assert keys[1] < keys[0]  # 999 < 2048, even though '999 B' > '2.0 KB' as text


def test_file_count_sort_key_is_negative_for_files():
    """Files (no count) sort below any directory by using a -1 count key."""
    model = SourceFilesModel()
    model.set_rows([_source('/dir', dir_files_count=0, path_isdir=True), _source('/file', path_isdir=False)])

    keys = [model.data(model.index(r, SourceFilesModel.COL_FILES), SourceFilesModel.SortRole) for r in range(2)]
    assert keys == [0, -1]


def test_source_role_returns_backing_object():
    """SourceRole exposes the SourceFileModel so callers read it through the (auto-mapping) proxy."""
    model = SourceFilesModel()
    only = _source('/only')
    model.set_rows([only])

    for column in range(model.columnCount()):
        assert model.data(model.index(0, column), SourceFilesModel.SourceRole) is only


def test_source_at_returns_object_or_none():
    """source_at returns the backing SourceFileModel and None when out of range."""
    model = SourceFilesModel()
    only = _source('/only')
    model.set_rows([only])

    assert model.source_at(0) is only
    assert model.source_at(5) is None
    assert model.source_at(-1) is None


def test_path_tooltip_and_decoration():
    """The path column exposes its full path as a tooltip and a folder/file icon."""
    model = SourceFilesModel()
    model.set_rows([_source('/dir', path_isdir=True), _source('/file', path_isdir=False)])

    assert model.data(model.index(0, SourceFilesModel.COL_PATH), Qt.ItemDataRole.ToolTipRole) == '/dir'
    assert model.data(model.index(0, SourceFilesModel.COL_PATH), Qt.ItemDataRole.DecorationRole) is not None
    assert model.data(model.index(1, SourceFilesModel.COL_PATH), Qt.ItemDataRole.DecorationRole) is not None


def test_size_column_is_right_aligned():
    """The size column keeps the legacy right alignment."""
    model = SourceFilesModel()
    model.set_rows([_source('/a', dir_size=1500, path_isdir=True)])

    align = model.data(model.index(0, SourceFilesModel.COL_SIZE), Qt.ItemDataRole.TextAlignmentRole)
    assert align == Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


def test_header_data_returns_column_labels():
    """Horizontal headers expose the canonical labels, matching the legacy .ui."""
    model = SourceFilesModel()

    def header(column):
        return model.headerData(column, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)

    assert header(SourceFilesModel.COL_PATH) == 'Path'
    assert header(SourceFilesModel.COL_SIZE) == 'Size'
    assert header(SourceFilesModel.COL_FILES) == 'File Count'
    assert model.headerData(0, Qt.Orientation.Vertical, Qt.ItemDataRole.DisplayRole) is None


def test_data_returns_none_for_invalid_index_or_unsupported_role():
    """Invalid indices and unhandled roles yield None."""
    model = SourceFilesModel()
    model.set_rows([_source('/x')])

    assert model.data(QModelIndex()) is None
    assert model.data(model.index(0, SourceFilesModel.COL_PATH), Qt.ItemDataRole.EditRole) is None
