"""Filter proxy narrowing the jobs table to rows matching a value per column."""

from typing import Dict, Optional

from PyQt6.QtCore import QModelIndex, QObject, Qt

from vorta.views.partials.sort_proxy import SortProxyModel


class JobsFilterProxyModel(SortProxyModel):
    """Sort proxy that also drops rows whose columns do not hold the selected values."""

    def __init__(self, parent: Optional[QObject] = None):
        """Init."""
        super().__init__(parent)
        self._filters: Dict[int, str] = {}

    def set_filter(self, column: int, value: Optional[str]) -> None:
        """Keep only rows whose `column` holds `value`, or every row when `value` is None."""
        if self._filters.get(column) == value:
            return
        if value is None:
            self._filters.pop(column, None)
        else:
            self._filters[column] = value
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        for column, wanted in self._filters.items():
            index = model.index(source_row, column, source_parent)
            if index.data(Qt.ItemDataRole.UserRole) != wanted:
                return False
        return super().filterAcceptsRow(source_row, source_parent)
