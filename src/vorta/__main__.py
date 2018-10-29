import sys
from PyQt5.QtWidgets import QApplication
from vorta.tray_menu import TrayMenu
from vorta.scheduler import init_scheduler
from vorta.models import BackupProfileModel

app = QApplication(sys.argv)
app.thread = None
app.setQuitOnLastWindowClosed(False)
TrayMenu(app)
app.scheduler = init_scheduler()
app.profile = BackupProfileModel.get(id=1)

if not getattr(sys, 'frozen', False):
    from .views.main_window import MainWindow
    ex = MainWindow()
    ex.show()

sys.exit(app.exec_())
