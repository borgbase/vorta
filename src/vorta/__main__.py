import sys
import os
import peewee
from PyQt5.QtWidgets import QApplication

if getattr(sys, 'frozen', False):
    import sentry_sdk
    sentry_sdk.init("https://a4a23df3e44743d5b5c5f06417a9a809@sentry.io/1311799")

# Ensures resource file in icons-folder is found
from vorta.utils import get_asset
sys.path.append(os.path.dirname(get_asset('icons/collection.rc')))

from vorta.tray_menu import TrayMenu
from vorta.scheduler import init_scheduler
import vorta.models
from vorta.config import SETTINGS_DIR

sqlite_db = peewee.SqliteDatabase(os.path.join(SETTINGS_DIR, 'settings.db'))
vorta.models.init_db(sqlite_db)

app = QApplication(sys.argv)
app.thread = None
app.setQuitOnLastWindowClosed(False)
app.scheduler = init_scheduler()
TrayMenu(app)
app.profile = vorta.models.BackupProfileModel.get(id=1)

if not getattr(sys, 'frozen', False):
    from .views.main_window import MainWindow
    ex = MainWindow(app)
    ex.show()

sys.exit(app.exec_())
