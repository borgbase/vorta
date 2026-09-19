from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView

from vorta.store.models import JobModel
from vorta.utils import get_asset
from vorta.views.base_tab import BaseTab
from vorta.views.partials.jobs_filter_proxy import JobsFilterProxyModel
from vorta.views.partials.jobs_table_model import JobRow, JobsTableModel

uifile = get_asset('UI/jobs_page.ui')
JobsPageUI, JobsPageBase = uic.loadUiType(uifile)

RECORD_LIMIT = 200


class JobsPage(BaseTab, JobsPageBase, JobsPageUI):
    def __init__(self, parent=None, profile_provider=None):
        super().__init__(parent=parent, profile_provider=profile_provider)
        self.setupUi(self)

        self._model = JobsTableModel(self)
        self._proxy = JobsFilterProxyModel(self)
        self._proxy.setSourceModel(self._model)
        self.jobsTable.setModel(self._proxy)

        self._pending = []
        self._records = []

        self.init_ui()
        self.track_backup_finished(self.reload_records)
        self.track_signal(self.app.scheduler.jobs_changed, self.reload_records)
        self.track_signal(self.app.scheduler.schedule_changed, self.reload_pending)
        self.reload_records()
        self.reload_pending()

    def init_ui(self):
        self.init_filters()
        self.jobsTable.setAlternatingRowColors(True)
        header = self.jobsTable.horizontalHeader()
        header.setVisible(True)
        for i in range(self._model.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(JobsTableModel.COL_REASON, QHeaderView.ResizeMode.Stretch)
        self.jobsTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.jobsTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.jobsTable.sortByColumn(JobsTableModel.COL_TIME, Qt.SortOrder.DescendingOrder)

    def init_filters(self):
        for combo, column in (
            (self.profileFilter, JobsTableModel.COL_PROFILE),
            (self.repoFilter, JobsTableModel.COL_REPOSITORY),
            (self.statusFilter, JobsTableModel.COL_STATUS),
        ):
            combo.addItem(self.tr('All'), None)
            combo.currentIndexChanged.connect(lambda i, c=combo, col=column: self.on_filter_changed(c, col))

        for status in JobModel.Status:
            self.statusFilter.addItem(status.value, status.value)

    def on_filter_changed(self, combo, column):
        self._proxy.set_filter(column, combo.currentData())

    def reload_records(self):
        records = JobModel.select().order_by(JobModel.created_at.desc()).limit(RECORD_LIMIT)
        self._records = [JobRow.from_record(record) for record in records]
        self._redraw()

    def reload_pending(self):
        self._pending = [JobRow.from_pending(pending) for pending in self.app.scheduler.pending_jobs()]
        self._redraw()

    def _redraw(self):
        rows = self._pending + self._records
        self._refresh_row_filters(rows)
        self._model.set_rows(rows)

    def _refresh_row_filters(self, rows):
        for combo, values in (
            (self.profileFilter, {r.profile_name for r in rows if r.profile_name}),
            (self.repoFilter, {r.repo_url for r in rows if r.repo_url}),
        ):
            # Keep the selection on offer: a pending run can leave the rows on an unrelated event.
            selected = combo.currentData()
            choices = sorted(values | {selected}) if selected else sorted(values)
            if choices == [combo.itemData(i) for i in range(1, combo.count())]:
                continue

            combo.blockSignals(True)
            combo.clear()
            combo.addItem(self.tr('All'), None)
            for value in choices:
                combo.addItem(value, value)
            combo.setCurrentIndex(combo.findData(selected) if selected else 0)
            combo.blockSignals(False)
