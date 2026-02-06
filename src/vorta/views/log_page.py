from PyQt6 import uic
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidgetItem,
)

from vorta import config
from vorta.store.models import EventLogModel
from vorta.utils import get_asset
from vorta.views.base_tab import BaseTab

uifile = get_asset('UI/log_page.ui')
LogTableUI, LogTableBase = uic.loadUiType(uifile)


class LogTableColumn:
    Time = 0
    Category = 1
    Subcommand = 2
    Repository = 3
    ReturnCode = 4


class LogPage(BaseTab, LogTableBase, LogTableUI):
    def __init__(self, parent=None, profile_provider=None):
        super().__init__(parent=parent, profile_provider=profile_provider)
        self.setupUi(self)
        self.init_ui()
        self.track_backup_finished(self.populate_logs)
        self.track_profile_change(self.populate_logs)

    def init_ui(self):
        self.logPage.setAlternatingRowColors(True)
        header = self.logPage.horizontalHeader()
        header.setVisible(True)
        [header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents) for i in range(5)]
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.logPage.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.logPage.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.logLink.setText(self.logLink.text().replace('file:///', f'file://{config.LOG_DIR}'))

        self.populate_logs()

    def populate_logs(self):
        profile = self.profile()
        event_logs = [
            s
            for s in EventLogModel.select()
            .where(EventLogModel.profile == profile.id)
            .order_by(EventLogModel.start_time.desc())
        ]

        sorting = self.logPage.isSortingEnabled()
        self.logPage.setSortingEnabled(False)
        self.logPage.setRowCount(len(event_logs))
        for row, log_line in enumerate(event_logs):
            formatted_time = log_line.start_time.strftime('%Y-%m-%d %H:%M')
            self.logPage.setItem(row, LogTableColumn.Time, QTableWidgetItem(formatted_time))
            self.logPage.setItem(row, LogTableColumn.Category, QTableWidgetItem(log_line.category))
            self.logPage.setItem(row, LogTableColumn.Subcommand, QTableWidgetItem(log_line.subcommand))
            self.logPage.setItem(row, LogTableColumn.Repository, QTableWidgetItem(log_line.repo_url))
            self.logPage.setItem(row, LogTableColumn.ReturnCode, QTableWidgetItem(str(log_line.returncode)))
        self.logPage.setSortingEnabled(sorting)
