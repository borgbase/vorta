import sys
from PyQt5.QtWidgets import QApplication
from .tray_menu import TrayMenu
from .scheduler import init_scheduler

app = QApplication(sys.argv)
app.thread = None
app.setQuitOnLastWindowClosed(False)
TrayMenu(app)
app.scheduler = init_scheduler()

sys.exit(app.exec_())
