import sys
from PyQt5.QtWidgets import QApplication
from vorta.tray_menu import TrayMenu

app = QApplication(sys.argv)
app.thread = None
app.setQuitOnLastWindowClosed(False)
menu = TrayMenu(app)

sys.exit(app.exec_())
