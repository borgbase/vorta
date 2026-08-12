"""
Qt table model exposing scheduled and recorded jobs to the JobsPage `QTableView`.

"""

from __future__ import annotations

from datetime import datetime as dt
from typing import TYPE_CHECKING, Any, List, NamedTuple, Optional

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt

from vorta.i18n import trans_late, translate
from vorta.store.models import JobModel

if TYPE_CHECKING:
    from vorta.scheduler import PendingJob


class JobRow(NamedTuple):
    """One row of the jobs table, from either a stored record or a pending run."""

    time: dt
    profile_name: Optional[str]
    repo_url: Optional[str]
    job_type: Optional[str]
    trigger: Optional[str]
    status: str
    reason: Optional[str]

    @classmethod
    def from_record(cls, job: JobModel) -> 'JobRow':
        return cls(
            time=job.created_at,
            profile_name=job.profile_name,
            repo_url=job.repo_url,
            job_type=job.job_type,
            trigger=job.trigger,
            status=job.status,
            reason=job.reason,
        )

    @classmethod
    def from_pending(cls, pending: 'PendingJob') -> 'JobRow':
        return cls(
            time=pending.scheduled_at,
            profile_name=pending.profile_name,
            repo_url=pending.repo_url,
            job_type=JobModel.Type.BACKUP.value,
            trigger=JobModel.Trigger.SCHEDULED.value,
            status=JobModel.Status.SCHEDULED.value,
            reason=None,
        )


class JobsTableModel(QAbstractTableModel):
    """Read-only table model for pending and recorded scheduler jobs."""

    # Column indices in render order.
    COL_TIME = 0
    COL_PROFILE = 1
    COL_REPOSITORY = 2
    COL_TYPE = 3
    COL_TRIGGER = 4
    COL_STATUS = 5
    COL_REASON = 6

    _HEADERS = (
        trans_late('JobsPage', 'Time'),
        trans_late('JobsPage', 'Profile'),
        trans_late('JobsPage', 'Repository'),
        trans_late('JobsPage', 'Type'),
        trans_late('JobsPage', 'Trigger'),
        trans_late('JobsPage', 'Status'),
        trans_late('JobsPage', 'Reason'),
    )

    def __init__(self, parent: Optional[Any] = None):
        """Init."""
        super().__init__(parent)
        self._rows: List[JobRow] = []

    def set_rows(self, rows: List[JobRow]) -> None:
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
            return row.time.strftime('%Y-%m-%d %H:%M')
        if column == self.COL_PROFILE:
            return row.profile_name
        if column == self.COL_REPOSITORY:
            return row.repo_url
        if column == self.COL_TYPE:
            return row.job_type
        if column == self.COL_TRIGGER:
            return row.trigger
        if column == self.COL_STATUS:
            return row.status
        if column == self.COL_REASON:
            return row.reason
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
            return translate('JobsPage', self._HEADERS[section])
        return None
