from PyQt6 import uic
from PyQt6.QtWidgets import QApplication

from vorta import application
from vorta.store.models import BackupProfileMixin
from vorta.utils import get_asset
from vorta.views.log_page import LogPage
from vorta.views.networks_page import NetworksPage
from vorta.views.schedule_page import SchedulePage
from vorta.views.shell_commands_page import ShellCommandsPage
from vorta.views.utils import get_colored_icon

uifile = get_asset('UI/schedule_tab.ui')
ScheduleUI, ScheduleBase = uic.loadUiType(uifile)


class ScheduleTab(ScheduleBase, ScheduleUI, BackupProfileMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)
        self.app: application.VortaApp = QApplication.instance()
        self.toolBox.setCurrentIndex(0)
        self.set_icons()
        self.init_log_page()
        self.init_shell_commands_page()
        self.init_networks_page()
        self.init_schedule_page()
        self.app.paletteChanged.connect(lambda p: self.set_icons())

        self.app.backup_finished_event.connect(self.logPage.populate_logs)

    def init_log_page(self):
        self.logPage = LogPage(self)
        self.logLayout.addWidget(self.logPage)
        self.logPage.show()

    def init_shell_commands_page(self):
        self.shellCommandsPage = ShellCommandsPage(self)
        self.shellCommandsLayout.addWidget(self.shellCommandsPage)
        self.shellCommandsPage.show()

    def init_networks_page(self):
        self.networksPage = NetworksPage(self)
        self.networksLayout.addWidget(self.networksPage)
        self.networksPage.show()

    def init_schedule_page(self):
        self.schedulePage = SchedulePage(self)
        self.scheduleLayout.addWidget(self.schedulePage)
        self.schedulePage.show()

    def set_icons(self):
        self.toolBox.setItemIcon(0, get_colored_icon('clock-o'))
        self.toolBox.setItemIcon(1, get_colored_icon('wifi'))
        self.toolBox.setItemIcon(2, get_colored_icon('tasks'))
        self.toolBox.setItemIcon(3, get_colored_icon('terminal'))
