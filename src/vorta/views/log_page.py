from PyQt6 import uic
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidgetItem,
)

from vorta import config
from vorta.store.models import EventLogModel
from vorta.utils import get_asset

uifile = get_asset('UI/logpage.ui')
LogTableUI, LogTableBase = uic.loadUiType(uifile)


class LogTableColumn:
    Time = 0
    Category = 1
    Subcommand = 2
    Repository = 3
    ReturnCode = 4


class LogPanel(LogTableBase, LogTableUI):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.init_ui()

    def init_ui(self):
        self.logTableWidget.setAlternatingRowColors(True)
        header = self.logTableWidget.horizontalHeader()
        header.setVisible(True)
        [header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents) for i in range(5)]
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.logTableWidget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.logTableWidget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.logLink.setText(
            f'<a href="file://{config.LOG_DIR}"><span style="text-decoration:'
            'underline; color:#0984e3;">Click here</span></a> for complete logs.'
        )

        self.populate_logs()

    def populate_logs(self):
        event_logs = [s for s in EventLogModel.select().order_by(EventLogModel.start_time.desc())]

        sorting = self.logTableWidget.isSortingEnabled()
        self.logTableWidget.setSortingEnabled(False)
        self.logTableWidget.setRowCount(len(event_logs))
        for row, log_line in enumerate(event_logs):
            formatted_time = log_line.start_time.strftime('%Y-%m-%d %H:%M')
            self.logTableWidget.setItem(row, LogTableColumn.Time, QTableWidgetItem(formatted_time))
            self.logTableWidget.setItem(row, LogTableColumn.Category, QTableWidgetItem(log_line.category))
            self.logTableWidget.setItem(row, LogTableColumn.Subcommand, QTableWidgetItem(log_line.subcommand))
            self.logTableWidget.setItem(row, LogTableColumn.Repository, QTableWidgetItem(log_line.repo_url))
            self.logTableWidget.setItem(row, LogTableColumn.ReturnCode, QTableWidgetItem(str(log_line.returncode)))
        self.logTableWidget.setSortingEnabled(sorting)
