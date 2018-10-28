import os
from PyQt5 import uic, QtCore
from PyQt5.QtWidgets import QFileDialog
from .models import SourceDirModel
from .utils import get_relative_asset

uifile = get_relative_asset('UI/sourcetab.ui')
SourceUI, SourceBase = uic.loadUiType(uifile)


class SourceTab(SourceBase, SourceUI):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)
        self.profile = self.window().profile

        self.sourceAdd.clicked.connect(self.source_add)
        self.sourceRemove.clicked.connect(self.source_remove)
        for source in SourceDirModel.select():
            self.sourceDirectoriesWidget.addItem(source.dir)

    def source_add(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly
        options |= QFileDialog.DontUseNativeDialog
        fileName = QFileDialog.getExistingDirectory(
            self, "Choose Backup Directory", "", options=options)
        if fileName:
            self.sourceDirectoriesWidget.addItem(fileName)
            new_source = SourceDirModel(dir=fileName)
            new_source.save()

    def source_remove(self):
        item = self.sourceDirectoriesWidget.takeItem(self.sourceDirectoriesWidget.currentRow())
        db_item = SourceDirModel.get(dir=item.text())
        db_item.delete_instance()
        item = None
