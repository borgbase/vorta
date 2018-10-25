import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5 import uic
import appdirs

appname = "Locutus"
appauthor = "BorgBase"
appdirs.user_data_dir(appname, appauthor)
appdirs.user_log_dir(appname, appauthor)

#load both ui file
uifile = os.path.join(os.path.dirname(__file__), 'UI/mainwindow.ui')
form_1, base_1 = uic.loadUiType(uifile)

class Example(base_1, form_1):
    def __init__(self):
        super(base_1,self).__init__()
        self.setupUi(self)
        self.pushButton.clicked.connect(self.change)
        self.actiontest.triggered.connect(self.change)

    def change(self):
        self.textEdit.setText('Hello Smu!!')
        self.progressBar.setValue(35)
        self.openFileNameDialog()

    def openFileNameDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly
        options |= QFileDialog.DontUseNativeDialog
        fileName = QFileDialog.getExistingDirectory(
            self, "Choose Backup Directory", "", options=options)
        if fileName:
            print(fileName)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Example()
    ex.show()
    sys.exit(app.exec_())
