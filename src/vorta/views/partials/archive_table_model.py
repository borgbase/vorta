"""
Qt table model exposing `ArchiveModel` rows to the ArchiveTab `QTableView`.

"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QObject, QSortFilterProxyModel, Qt
from PyQt6.QtGui import QIcon

from vorta.i18n import trans_late, translate
from vorta.store.models import ArchiveModel
from vorta.utils import find_best_unit_for_sizes, pretty_bytes, uses_dark_mode
from vorta.views.utils import get_colored_icon

#: Decimal digits shown in the size column.
SIZE_DECIMAL_DIGITS = 1


class ArchiveTableModel(QAbstractTableModel):
    """Table model for backup archive rows; the name column is editable for in-place rename."""

    # Column indices in render order (matching the legacy QTableWidget layout).
    COL_TIME = 0
    COL_SIZE = 1
    COL_DURATION = 2
    COL_MOUNT = 3
    COL_NAME = 4
    COL_TRIGGER = 5

    #: Role returning native, comparable values for sorting via a proxy model.
    SortRole = Qt.ItemDataRole.UserRole
    #: Role returning the backing ArchiveModel; auto-mapped through the sort proxy.
    ArchiveRole = Qt.ItemDataRole.UserRole + 1

    _HEADERS = (
        trans_late('Form', 'Date'),
        trans_late('Form', 'Size'),
        trans_late('Form', 'Duration'),
        trans_late('Form', 'Mount Point'),
        trans_late('Form', 'Name'),
        trans_late('Form', 'Trigger'),
    )

    _TRIGGER_ICONS = {'scheduled': 'clock-o', 'user': 'user'}

    def __init__(self, parent: Optional[QObject] = None):
        """Init."""
        super().__init__(parent)
        self._rows: List[ArchiveModel] = []
        self._mount_points: Dict[str, str] = {}
        self._fixed_unit: Optional[int] = None
        self._icon_cache: Dict[str, QIcon] = {}  # themed icons; invalidated on dark-mode switch
        self._icon_cache_dark: Optional[bool] = None

    def set_rows(
        self,
        rows: List[ArchiveModel],
        mount_points: Optional[Dict[str, str]] = None,
        use_fixed_units: bool = False,
    ) -> None:
        """Replace the model contents and notify attached views.

        ``mount_points`` maps archive name to its current mount path; ``use_fixed_units``
        (injected by the view) pins all rows to one shared size unit.
        """
        self.beginResetModel()
        self._rows = list(rows)
        self._mount_points = dict(mount_points or {})
        if use_fixed_units:
            self._fixed_unit = find_best_unit_for_sizes((r.size for r in self._rows), precision=SIZE_DECIMAL_DIGITS)
        else:
            self._fixed_unit = None
        self.endResetModel()

    def set_mount_points(self, mount_points: Optional[Dict[str, str]] = None) -> None:
        """Update mount paths and refresh the Mount Point column in place (no full reset)."""
        self._mount_points = dict(mount_points or {})
        if self._rows:
            top = self.index(0, self.COL_MOUNT)
            bottom = self.index(len(self._rows) - 1, self.COL_MOUNT)
            self.dataChanged.emit(top, bottom, [Qt.ItemDataRole.DisplayRole])

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

        row = self._rows[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            return self._display_data(row, column)
        if role == Qt.ItemDataRole.EditRole and column == self.COL_NAME:
            return row.name  # pre-fill the rename editor with the current name
        if role == self.SortRole:
            return self._sort_data(row, column)
        if role == self.ArchiveRole:
            return row  # proxy-safe accessor: the proxy forwards data() through mapToSource
        if role == Qt.ItemDataRole.DecorationRole and column == self.COL_TRIGGER:
            return self._trigger_icon(row)
        if role == Qt.ItemDataRole.ToolTipRole and column == self.COL_TRIGGER:
            return self._trigger_tooltip(row)
        return None

    def _display_data(self, row: ArchiveModel, column: int) -> Any:
        if column == self.COL_TIME:
            return row.time.strftime('%Y-%m-%d %H:%M')
        if column == self.COL_SIZE:
            return pretty_bytes(row.size, fixed_unit=self._fixed_unit, precision=SIZE_DECIMAL_DIGITS)
        if column == self.COL_DURATION:
            if row.duration is None:
                return ''
            return str(timedelta(seconds=round(row.duration)))
        if column == self.COL_MOUNT:
            return self._mount_points.get(row.name, '')
        if column == self.COL_NAME:
            return row.name
        return None  # trigger column is icon-only

    def _sort_data(self, row: ArchiveModel, column: int) -> Any:
        """Native comparable value used by the sort proxy."""
        if column == self.COL_TIME:
            return row.time
        if column == self.COL_SIZE:
            return row.size or 0
        if column == self.COL_DURATION:
            return row.duration or 0
        if column == self.COL_MOUNT:
            return self._mount_points.get(row.name, '')
        if column == self.COL_NAME:
            return row.name
        if column == self.COL_TRIGGER:
            return row.trigger or ''
        return None

    def _trigger_icon(self, row: ArchiveModel) -> Any:
        icon_name = self._TRIGGER_ICONS.get(row.trigger)
        if icon_name is None:
            return None
        dark = uses_dark_mode()
        if dark != self._icon_cache_dark:  # theme switched: themed icons are stale
            self._icon_cache.clear()
            self._icon_cache_dark = dark
        if icon_name not in self._icon_cache:
            self._icon_cache[icon_name] = get_colored_icon(icon_name)
        return self._icon_cache[icon_name]

    def _trigger_tooltip(self, row: ArchiveModel) -> Any:
        if row.trigger == 'scheduled':
            return translate('ArchiveTab', 'Scheduled')
        if row.trigger == 'user':
            return translate('ArchiveTab', 'User initiated')
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)
        if index.isValid() and index.column() == self.COL_NAME:
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        """Store an in-place edited archive name; the view performs the real rename.

        This overwrites ``row.name`` before the rename runs; the view relies on having
        stashed ``renamed_archive_original_name`` at edit-start to recover the old name.
        """
        if not index.isValid() or role != Qt.ItemDataRole.EditRole or index.column() != self.COL_NAME:
            return False
        self._rows[index.row()].name = value
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
        return True

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


class ArchiveSortProxyModel(QSortFilterProxyModel):
    """Sort proxy that compares `SortRole` keys in Python to avoid Qt's 32-bit int truncation."""

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        lv = left.data(ArchiveTableModel.SortRole)
        rv = right.data(ArchiveTableModel.SortRole)
        if lv is None:
            return True
        if rv is None:
            return False
        return lv < rv
