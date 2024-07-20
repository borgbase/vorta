from PyQt6 import uic
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidgetItem,
)

from vorta import config
from vorta.store.models import EventLogModel
from vorta.utils import get_asset

uifile = get_asset('UI/log_page.ui')
LogTableUI, LogTableBase = uic.loadUiType(uifile)


class LogTableColumn:
    Time = 0
    Category = 1
    Subcommand = 2
    Repository = 3
    ReturnCode = 4


class LogPage(LogTableBase, LogTableUI):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.init_ui()

    def init_ui(self):
        self.logPage.setAlternatingRowColors(True)
        header = self.logPage.horizontalHeader()
        header.setVisible(True)
        [header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents) for i in range(5)]
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.logPage.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.logPage.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.logLink.setText(
            f'<a href="file://{config.LOG_DIR}"><span style="text-decoration:'
            'underline; color:#0984e3;">Click here</span></a> for complete logs.'
        )

        self.populate_logs()

    def populate_logs(self):
        event_logs = [s for s in EventLogModel.select().order_by(EventLogModel.start_time.desc())]

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
