import sys
import os
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon
from vorta.main_window import MainWindow

app = QApplication(sys.argv)

# Create the tray
app.setQuitOnLastWindowClosed(False)
tray = QSystemTrayIcon()
icon = QIcon(os.path.join(os.path.dirname(__file__), 'UI/icons/hdd-o.png'))
tray.setIcon(icon)
tray.setVisible(True)

# Create the menu
menu = QMenu()
action = QAction("A menu item")
menu.addAction(action)
tray.setContextMenu(menu)

ex = MainWindow()
ex.show()
sys.exit(app.exec_())
