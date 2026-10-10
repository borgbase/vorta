"""Shared numeric-safe sort proxy for `QAbstractTableModel`-backed tables."""

from PyQt6.QtCore import QModelIndex, QSortFilterProxyModel, Qt


class SortProxyModel(QSortFilterProxyModel):
    """Sort proxy comparing `Qt.UserRole` keys in Python to avoid Qt's 32-bit int truncation."""

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        lv = left.data(Qt.ItemDataRole.UserRole)
        rv = right.data(Qt.ItemDataRole.UserRole)
        if lv is None:
            return rv is not None
        if rv is None:
            return False
        return lv < rv
