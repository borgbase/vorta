from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QMenu, QApplication, QSystemTrayIcon, QMessageBox, QDialog
from .views.main_window import MainWindow
from PyQt5.QtGui import QIcon

from .utils import get_asset
from .config import remove_config
from .borg_runner import BorgThread

class TrayMenu(QSystemTrayIcon):
    def __init__(self, parent=None):
        icon = QIcon(get_asset('icons/hdd-o.png'))
        QSystemTrayIcon.__init__(self, icon, parent)
        self.app = parent
        menu = QMenu()

        self.status = menu.addAction(self._get_scheduler_status())
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
        ex = MainWindow(self.app)
        ex.show()

    def on_exit_action(self):
        QApplication.instance().quit()

    def on_reset(self):
        remove_config()
        QApplication.instance().quit()

    def on_create_backup(self):
        if self.app.thread and self.app.thread.isRunning():
            self.app.thread.process.kill()
            self.app.thread.terminate()
        else:
            msg = BorgThread.prepare_runner()
            if msg['ok']:
                self.app.thread = BorgThread(msg['cmd'], msg['params'])
                self.app.thread.start()
            # TODO: error dialog

    def on_user_click(self):
        """Adjust labels to reflect current status."""
        if self.app.thread and self.app.thread.isRunning():
            self.status.setText('Backup in Progress')
            self.create_action.setText('Cancel Backup')
        else:
            self.status.setText(self._get_scheduler_status())
            self.create_action.setText('Backup Now')

    def _get_scheduler_status(self):
        if self.app.scheduler is not None:
            job = self.app.scheduler.get_job('create-backup')
            return f"Next run: {job.next_run_time.strftime('%Y-%m-%d %H:%M')}"
        else:
            return 'No backups scheduled'
