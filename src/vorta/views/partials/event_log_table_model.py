"""
Qt table model exposing `EventLogModel` rows to the LogPage `QTableView`.

"""

from __future__ import annotations

from typing import Any, List, Optional

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt

from vorta.i18n import trans_late, translate
from vorta.store.models import EventLogModel


class EventLogTableModel(QAbstractTableModel):
    """Read-only table model for backup event log rows."""

    # Column indices in render order.
    COL_TIME = 0
    COL_CATEGORY = 1
    COL_SUBCOMMAND = 2
    COL_REPOSITORY = 3
    COL_RETURNCODE = 4

    _HEADERS = (
        trans_late('LogPage', 'Time'),
        trans_late('LogPage', 'Category'),
        trans_late('LogPage', 'Subcommand'),
        trans_late('LogPage', 'Repository'),
        trans_late('LogPage', 'Returncode'),
    )

    def __init__(self, parent: Optional[Any] = None):
        """Init."""
        super().__init__(parent)
        self._rows: List[EventLogModel] = []

    def set_rows(self, rows: List[EventLogModel]) -> None:
        """Replace the model contents and notify attached views."""
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None

        row = self._rows[index.row()]
        column = index.column()

        if column == self.COL_TIME:
            return row.start_time.strftime('%Y-%m-%d %H:%M')
        if column == self.COL_CATEGORY:
            return row.category
        if column == self.COL_SUBCOMMAND:
            return row.subcommand
        if column == self.COL_REPOSITORY:
            return row.repo_url
        if column == self.COL_RETURNCODE:
            return str(row.returncode)
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal and 0 <= section < len(self._HEADERS):
            return translate('LogPage', self._HEADERS[section])
        return None
