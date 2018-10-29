import sys
import os
from PyQt5.QtWidgets import QApplication

# Ensures resource file in icons-folder is found
from vorta.utils import get_asset
sys.path.append(os.path.dirname(get_asset('icons/collection.rc')))

from vorta.tray_menu import TrayMenu
from vorta.scheduler import init_scheduler
from vorta.models import BackupProfileModel


app = QApplication(sys.argv)
app.thread = None
app.setQuitOnLastWindowClosed(False)
app.scheduler = init_scheduler()
TrayMenu(app)
app.profile = BackupProfileModel.get(id=1)

if not getattr(sys, 'frozen', False):
    from .views.main_window import MainWindow
    ex = MainWindow()
    ex.show()

sys.exit(app.exec_())
