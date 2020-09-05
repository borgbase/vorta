from PyQt5 import uic
from ..models import SourceFileModel, BackupProfileMixin
from ..utils import get_asset, choose_file_dialog, pretty_bytes, FilePathInfoAsync
from PyQt5.QtWidgets import QApplication, QMessageBox, QTableWidgetItem, QHeaderView
import os

uifile = get_asset('UI/sourcetab.ui')
SourceUI, SourceBase = uic.loadUiType(uifile)


class SourceTab(SourceBase, SourceUI, BackupProfileMixin):
    updateThreads = []
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)
        
        headerTxt=["Path","Type","Size","Folder/\nFiles Count"]

        self.sourceFilesWidget.setColumnCount(len(headerTxt))
        header = self.sourceFilesWidget.horizontalHeader()

        header.setVisible(True)
        header.setSortIndicatorShown(1)
        
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.sourceFilesWidget.setHorizontalHeaderLabels(headerTxt)

        self.sourceAddFolder.clicked.connect(lambda: self.source_add(want_folder=True))
        self.sourceAddFile.clicked.connect(lambda: self.source_add(want_folder=False))
        self.sourceRemove.clicked.connect(self.source_remove)
        self.paste.clicked.connect(self.paste_text)
        self.excludePatternsField.textChanged.connect(self.save_exclude_patterns)
        self.excludeIfPresentField.textChanged.connect(self.save_exclude_if_present)
        self.populate_from_profile()
        
    def set_path_info(self,path,datasize,filecount):
        items = self.sourceFilesWidget.findItems(path,QtCore.Qt.MatchExactly)
        for item in items:
            self.sourceFilesWidget.item(item.row(),2).setText(pretty_bytes(datasize))
            self.sourceFilesWidget.item(item.row(),3).setText(format(filecount))

    def add_source_to_table(self,path):
        indexRow = self.sourceFilesWidget.rowCount()
        self.sourceFilesWidget.insertRow(indexRow)
        itemPath = QTableWidgetItem(path)
        self.sourceFilesWidget.setItem(indexRow,0,itemPath)
        self.sourceFilesWidget.setItem(indexRow,1,QTableWidgetItem("DIR"))
        self.sourceFilesWidget.setItem(indexRow,2,QTableWidgetItem("load..."))
        self.sourceFilesWidget.setItem(indexRow,3,QTableWidgetItem("load..."))
        getDir = FilePathInfoAsync(path)
        getDir.signal.connect(self.set_path_info)
        self.updateThreads.append(getDir)
        getDir.start()

    def populate_from_profile(self):
        profile = self.profile()
        self.excludePatternsField.textChanged.disconnect()
        self.excludeIfPresentField.textChanged.disconnect()
        self.sourceFilesWidget.clearContents()
        self.excludePatternsField.clear()
        self.excludeIfPresentField.clear()

        for source in SourceFileModel.select().where(SourceFileModel.profile == profile):
            self.add_source_to_table(source.dir)

        self.excludePatternsField.appendPlainText(profile.exclude_patterns)
        self.excludeIfPresentField.appendPlainText(profile.exclude_if_present)
        self.excludePatternsField.textChanged.connect(self.save_exclude_patterns)
        self.excludeIfPresentField.textChanged.connect(self.save_exclude_if_present)

    def source_add(self, want_folder):
        def receive():
            dirs = dialog.selectedFiles()
            for dir in dirs:
                new_source, created = SourceFileModel.get_or_create(dir=dir, profile=self.profile())
                if created:
                    self.add_source_to_table(dir)
                    new_source.save()

        msg = self.tr("Choose directory to back up") if want_folder else self.tr("Choose file(s) to back up")
        dialog = choose_file_dialog(self, msg, want_folder=want_folder)
        dialog.open(receive)

    def source_remove(self):
        indexes = self.sourceFilesWidget.selectionModel().selectedIndexes()
        # sort indexes, starting with lowest
        indexes.sort()
        # remove each selected entry, starting with highest index (otherways, higher indexes become invalid)
        for index in reversed(indexes):
            item = self.sourceFilesWidget.takeItem(index.row())
            db_item = SourceFileModel.get(dir=item.text())
            db_item.delete_instance()

    def save_exclude_patterns(self):
        profile = self.profile()
        profile.exclude_patterns = self.excludePatternsField.toPlainText()
        profile.save()

    def save_exclude_if_present(self):
        profile = self.profile()
        profile.exclude_if_present = self.excludeIfPresentField.toPlainText()
        profile.save()

    def paste_text(self):
        sources = QApplication.clipboard().text().splitlines()
        invalidSources = ""
        for source in sources:
            if len(source) > 0:  # Ignore empty newlines
                if not os.path.exists(source):
                    invalidSources = invalidSources + "\n" + source
                else:
                    new_source, created = SourceFileModel.get_or_create(dir=source, profile=self.profile())
                    if created:
                        self.sourceFilesWidget.addItem(source)
                        new_source.save()

        if len(invalidSources) != 0:  # Check if any invalid paths
            msg = QMessageBox()
            msg.setText("Some of your sources are invalid:" + invalidSources)
            msg.exec()
