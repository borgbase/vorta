import sys
from PyQt5.QtWidgets import QApplication
from vorta.main import MainWindow

app = QApplication(sys.argv)
ex = MainWindow()
ex.show()
sys.exit(app.exec_())
