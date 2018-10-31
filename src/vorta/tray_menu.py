from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QMenu, QApplication, QSystemTrayIcon, QMessageBox, QDialog
from .views.main_window import MainWindow
from PyQt5.QtGui import QIcon

from .utils import get_asset
from .config import remove_config
from .borg_runner import BorgThread


class TrayMenu(QSystemTrayIcon):
    start_backup = QtCore.pyqtSignal()
    open_main_window = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        icon = QIcon(get_asset('icons/hdd-o.png'))
        QSystemTrayIcon.__init__(self, icon, parent)
        self.app = parent
        menu = QMenu()

        self.status = menu.addAction(self.app.scheduler.next_job)
        self.status.setEnabled(False)

        self.create_action = menu.addAction("Backup Now")
        self.create_action.triggered.connect(self.start_backup.emit)

        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self.open_main_window.emit)

        menu.addSeparator()

        exit_action = menu.addAction("Factory Reset")
        exit_action.triggered.connect(self.on_reset)

        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.on_exit_action)

        self.activated.connect(self.on_user_click)

        self.setContextMenu(menu)
        self.setVisible(True)
        self.show()

    def on_exit_action(self):
        self.app.quit()

    def on_reset(self):
        remove_config()
        self.app.quit()

    def on_user_click(self):
        """Adjust labels to reflect current status."""
        if BorgThread.is_running():
            self.status.setText('Backup in Progress')
            self.create_action.setText('Cancel Backup')
        else:
            self.status.setText(self.app.scheduler.next_job)
            self.create_action.setText('Backup Now')
