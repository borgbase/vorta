"""Qt table model exposing `SourceFileModel` rows to the SourceTab `QTableView`."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QObject, QSortFilterProxyModel, Qt

from vorta.i18n import trans_late, translate
from vorta.store.models import SourceFileModel
from vorta.utils import pretty_bytes, uses_dark_mode
from vorta.views.utils import get_colored_icon


class SourceFilesModel(QAbstractTableModel):
    """Table model for backup source rows; rows update in place during size recalculation."""

    COL_PATH = 0
    COL_SIZE = 1
    COL_FILES = 2

    #: Role returning native, comparable values for sorting via a proxy model.
    SortRole = Qt.ItemDataRole.UserRole
    #: Role returning the backing SourceFileModel; auto-mapped through the sort proxy.
    SourceRole = Qt.ItemDataRole.UserRole + 1

    _HEADERS = (
        trans_late('Form', 'Path'),
        trans_late('Form', 'Size'),
        trans_late('Form', 'File Count'),
    )

    _CALCULATING = trans_late('SourceTab', 'Calculating…')

    def __init__(self, parent: Optional[QObject] = None):
        """Init."""
        super().__init__(parent)
        self._rows: List[SourceFileModel] = []
        self._calculating: Set[str] = set()
        self._icon_cache: Dict[str, Any] = {}  # themed icons; invalidated on dark-mode switch
        self._icon_cache_dark: Optional[bool] = None

    def set_rows(self, rows: List[SourceFileModel]) -> None:
        """Replace the model contents and notify attached views."""
        self.beginResetModel()
        self._rows = list(rows)
        self._calculating.clear()
        self.endResetModel()

    def add_source(self, source: SourceFileModel) -> int:
        """Append ``source`` as a new row and return its row index."""
        row = len(self._rows)
        self.beginInsertRows(QModelIndex(), row, row)
        self._rows.append(source)
        self.endInsertRows()
        return row

    def source_at(self, row: int) -> Optional[SourceFileModel]:
        """Return the `SourceFileModel` backing ``row``, or None if out of range."""
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def mark_calculating(self, path: str) -> None:
        """Show ``Calculating…`` for the row matching ``path`` until results arrive."""
        self._calculating.add(path)
        row = self._row_for_path(path)
        if row is not None:
            self.dataChanged.emit(self.index(row, self.COL_SIZE), self.index(row, self.COL_FILES))

    def set_path_info(self, path: str, data_size: int, files_count: int, is_dir: bool) -> Optional[SourceFileModel]:
        """Apply recalculated size/count to the row matching ``path`` and return it.

        Keyed on ``path`` rather than a stored row index; returns None when no row matches
        (e.g. the source was removed mid-calculation, #1080 / #2435) so the caller skips persistence.
        """
        self._calculating.discard(path)
        row = self._row_for_path(path)
        if row is None:
            return None
        source = self._rows[row]
        source.dir_size = data_size
        source.dir_files_count = files_count
        source.path_isdir = is_dir
        self.dataChanged.emit(self.index(row, self.COL_PATH), self.index(row, self.COL_FILES))
        return source

    def _row_for_path(self, path: str) -> Optional[int]:
        for row, source in enumerate(self._rows):
            if source.dir == path:
                return row
        return None

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        source = self._rows[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            return self._display_data(source, column)
        if role == self.SortRole:
            return self._sort_data(source, column)
        if role == self.SourceRole:
            return source  # proxy-safe accessor: the proxy forwards data() through mapToSource
        if role == Qt.ItemDataRole.ToolTipRole and column == self.COL_PATH:
            return source.dir
        if role == Qt.ItemDataRole.DecorationRole and column == self.COL_PATH:
            return self._path_icon(source)
        if role == Qt.ItemDataRole.TextAlignmentRole and column == self.COL_SIZE:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return None

    def _display_data(self, source: SourceFileModel, column: int) -> Any:
        if column == self.COL_PATH:
            return source.dir
        if column == self.COL_SIZE:
            if source.dir in self._calculating:
                return translate('SourceTab', self._CALCULATING)
            if source.dir_size > -1:
                return pretty_bytes(source.dir_size)
            return ''
        if column == self.COL_FILES:
            if source.dir in self._calculating:
                return translate('SourceTab', self._CALCULATING)
            if source.path_isdir and source.dir_files_count > -1:
                return str(source.dir_files_count)
            return ''
        return None

    def _sort_data(self, source: SourceFileModel, column: int) -> Any:
        """Native comparable value used by the sort proxy."""
        if column == self.COL_PATH:
            return source.dir
        if column == self.COL_SIZE:
            return source.dir_size
        if column == self.COL_FILES:
            return source.dir_files_count if source.path_isdir else -1
        return None

    def _path_icon(self, source: SourceFileModel) -> Any:
        icon_name = 'folder' if source.path_isdir else 'file'
        dark = uses_dark_mode()
        if dark != self._icon_cache_dark:
            self._icon_cache.clear()
            self._icon_cache_dark = dark
        if icon_name not in self._icon_cache:
            self._icon_cache[icon_name] = get_colored_icon(icon_name)
        return self._icon_cache[icon_name]

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal and 0 <= section < len(self._HEADERS):
            return translate('Form', self._HEADERS[section])
        return None


class SortProxyModel(QSortFilterProxyModel):
    """Sort proxy comparing `SortRole` keys in Python to avoid Qt's 32-bit int truncation."""

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        lv = left.data(SourceFilesModel.SortRole)
        rv = right.data(SourceFilesModel.SortRole)
        if lv is None:
            return True
        if rv is None:
            return False
        return lv < rv
