from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMenu, QAction, QApplication, QSystemTrayIcon
from vorta.main_window import MainWindow
from PyQt5.QtGui import QIcon

from .utils import get_relative_asset
from .config import remove_config
from .borg_runner import BorgThread

class TrayMenu(QSystemTrayIcon):
    def __init__(self, parent=None):
        icon = QIcon(get_relative_asset('UI/icons/hdd-o.png'))
        QSystemTrayIcon.__init__(self, icon, parent)
        self.app = parent
        menu = QMenu()

        self.status = menu.addAction("Sleeping")
        self.status.setEnabled(False)

        self.create_action = menu.addAction("Backup Now")
        self.create_action.triggered.connect(self.on_create_backup)

        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self.on_settings_action)

        menu.addSeparator()

        exit_action = menu.addAction("Factory Reset")
        exit_action.triggered.connect(self.on_reset)

        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.on_exit_action)

        self.activated.connect(self.on_user_click)

        self.setContextMenu(menu)
        self.setVisible(True)
        self.show()

    def on_settings_action(self):
        ex = MainWindow()
        ex.show()

    def on_exit_action(self):
        QApplication.instance().quit()

    def on_reset(self):
        remove_config()
        QApplication.instance().quit()

    def on_create_backup(self):
        thread_msg = BorgThread.create_thread_factory()
        if thread_msg['ok']:
            thread_msg['thread'].start()
        else:
            error_dialog = QtWidgets.QErrorMessage()
            error_dialog.showMessage(thread_msg['message'])
            error_dialog.show()

    def on_cancel_backup(self):
        if self.app.thread and self.app.thread.isRunning():
            self.app.thread.terminate()

    def on_user_click(self):
        if self.app.thread and self.app.thread.isRunning():
            self.status.setText('Backup in Progress')
            self.create_action.setText('Cancel Backup')
            self.create_action.triggered.connect(self.on_cancel_backup)
        else:
            self.status.setText('Sleeping')
            self.create_action.setText('Backup Now')
            self.create_action.triggered.connect(self.on_create_backup)
