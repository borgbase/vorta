from PyQt6 import uic
from PyQt6.QtCore import QSortFilterProxyModel
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView

from vorta import config
from vorta.i18n.richtext import format_richtext, link
from vorta.store.models import EventLogModel
from vorta.utils import get_asset
from vorta.views.base_tab import BaseTab
from vorta.views.partials.event_log_table_model import EventLogTableModel

uifile = get_asset('UI/log_page.ui')
LogTableUI, LogTableBase = uic.loadUiType(uifile)


class LogPage(BaseTab, LogTableBase, LogTableUI):
    def __init__(self, parent=None, profile_provider=None):
        super().__init__(parent=parent, profile_provider=profile_provider)
        self.setupUi(self)

        self._model = EventLogTableModel(self)
        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self._model)
        self.logPage.setModel(self._proxy)

        self.init_ui()
        self.track_profile_change(self.populate_logs, call_now=True)
        self.track_backup_finished(self.populate_logs)

    def init_ui(self):
        self.logPage.setAlternatingRowColors(True)
        header = self.logPage.horizontalHeader()
        header.setVisible(True)
        for i in range(self._model.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(EventLogTableModel.COL_REPOSITORY, QHeaderView.ResizeMode.Stretch)
        self.logPage.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.logPage.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        template = self.logLink.text()
        log_link = link(f"file://{config.LOG_DIR}", self.tr('View the logs'))
        self.logLink.setText(format_richtext(template, log_link))

    def populate_logs(self):
        profile = self.profile()
        rows = list(
            EventLogModel.select().where(EventLogModel.profile == profile.id).order_by(EventLogModel.start_time.desc())
        )
        self._model.set_rows(rows)
