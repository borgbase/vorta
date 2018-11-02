from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QMenu, QApplication, QSystemTrayIcon, QMessageBox, QDialog
from .views.main_window import MainWindow
from PyQt5.QtGui import QIcon

from .utils import get_asset
from .borg_runner import BorgThread


class TrayMenu(QSystemTrayIcon):
    def __init__(self, parent=None):
        icon = QIcon(get_asset('icons/hdd-o.png'))
        QSystemTrayIcon.__init__(self, icon, parent)
        self.app = parent
        menu = QMenu()

        self.status = menu.addAction(self.app.scheduler.next_job)
        self.status.setEnabled(False)

        self.create_action = menu.addAction("Backup Now")
        self.create_action.triggered.connect(self.app.create_backup_action)

        self.cancel_action = menu.addAction("Cancel Backup")
        self.cancel_action.triggered.connect(self.app.backup_cancelled_event.emit)
        self.cancel_action.setVisible(False)

        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self.app.open_main_window_action)

        menu.addSeparator()

        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.app.quit)

        self.activated.connect(self.on_user_click)

        self.setContextMenu(menu)
        self.setVisible(True)
        self.show()

    def on_user_click(self):
        """Adjust labels to reflect current status."""
        if BorgThread.is_running():
            self.status.setText('Backup in Progress')
            self.create_action.setVisible(False)
            self.cancel_action.setVisible(True)
        else:
            self.status.setText(f'Next Task: {self.app.scheduler.next_job}')
            self.create_action.setVisible(True)
            self.cancel_action.setVisible(False)
