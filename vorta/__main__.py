import sys
import os
from PyQt5.QtWidgets import QApplication
from vorta.main_window import MainWindow
from vorta.tray_menu import TrayMenu

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
menu = TrayMenu(app)

ex = MainWindow()
ex.show()
sys.exit(app.exec_())
