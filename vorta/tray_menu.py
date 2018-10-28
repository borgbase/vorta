from PyQt5.QtWidgets import QMenu, QAction, QApplication, QSystemTrayIcon
from vorta.main_window import MainWindow
from PyQt5.QtGui import QIcon
from .utils import get_relative_asset
from .config import remove_config

class TrayMenu(QSystemTrayIcon):
    def __init__(self, parent=None):
        icon = QIcon(get_relative_asset('UI/icons/hdd-o.png'))
        QSystemTrayIcon.__init__(self, icon, parent)

        menu = QMenu()
        settings_action = menu.addAction("Settings")
        # settings_action.setEnabled(False)
        # settings_action.setText('In Progress')
        settings_action.setIcon(icon)
        settings_action.triggered.connect(self.on_settings_action)

        menu.addSeparator()

        exit_action = menu.addAction("Factory Reset")
        exit_action.triggered.connect(self.on_reset)

        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.on_exit_action)

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
