from PyQt5 import uic
from ..models import SourceFileModel, BackupProfileMixin, SettingsModel
from ..utils import get_asset, choose_file_dialog, pretty_bytes, FilePathInfoAsync
from PyQt5 import QtCore
from PyQt5.QtCore import QFileInfo
from PyQt5.QtWidgets import QApplication, QMessageBox, QTableWidgetItem, QHeaderView
import os

uifile = get_asset('UI/sourcetab.ui')
SourceUI, SourceBase = uic.loadUiType(uifile)


class SourceTab(SourceBase, SourceUI, BackupProfileMixin):
    updateThreads = []
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)
        
        headerTxt=["Path","Type","Size","Elements Count"]

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
        
    def set_path_info(self,path,data_size,files_count):
        items = self.sourceFilesWidget.findItems(path,QtCore.Qt.MatchExactly)
        for item in items:
            self.sourceFilesWidget.item(item.row(),2).setText(pretty_bytes(data_size))
            self.sourceFilesWidget.item(item.row(),3).setText(format(files_count))
            db_item = SourceFileModel.get(dir=path)
            db_item.dir_size = data_size
            db_item.dir_files_count = files_count
            db_item.save()
            

    def add_source_to_table(self,source,update_data):
        indexRow = self.sourceFilesWidget.rowCount()
        self.sourceFilesWidget.insertRow(indexRow)
        itemPath = QTableWidgetItem(source.dir)
        self.sourceFilesWidget.setItem(indexRow,0,itemPath)
        if source.path_isdir == True:
            self.sourceFilesWidget.setItem(indexRow,1,QTableWidgetItem("<DIR>"))
        else:
            self.sourceFilesWidget.setItem(indexRow,1,QTableWidgetItem("<File>"))
        if update_data == True:
            self.sourceFilesWidget.setItem(indexRow,2,QTableWidgetItem("load..."))
            self.sourceFilesWidget.setItem(indexRow,3,QTableWidgetItem("load..."))
            getDir = FilePathInfoAsync(source.dir)
            getDir.signal.connect(self.set_path_info)
            self.updateThreads.append(getDir) # this is ugly, is there a better way to keep the thread object?
            getDir.start()
        else: # Use cached data from DB
            if source.dir_size < 0:
                self.sourceFilesWidget.setItem(indexRow,2,QTableWidgetItem("N/A"))
                self.sourceFilesWidget.setItem(indexRow,3,QTableWidgetItem("N/A"))
            else:
                self.sourceFilesWidget.setItem(indexRow,2,QTableWidgetItem(pretty_bytes(source.dir_size)))
                self.sourceFilesWidget.setItem(indexRow,3,QTableWidgetItem(format(source.dir_files_count)))

    def populate_from_profile(self):
        profile = self.profile()
        self.excludePatternsField.textChanged.disconnect()
        self.excludeIfPresentField.textChanged.disconnect()
        self.sourceFilesWidget.clearContents()
        self.excludePatternsField.clear()
        self.excludeIfPresentField.clear()

        for source in SourceFileModel.select().where(SourceFileModel.profile == profile):
            self.add_source_to_table(source,False)

        self.excludePatternsField.appendPlainText(profile.exclude_patterns)
        self.excludeIfPresentField.appendPlainText(profile.exclude_if_present)
        self.excludePatternsField.textChanged.connect(self.save_exclude_patterns)
        self.excludeIfPresentField.textChanged.connect(self.save_exclude_if_present)

    def source_add(self, want_folder):
        def receive():
            dirs = dialog.selectedFiles()
            for dir in dirs:
                new_source, created = SourceFileModel.get_or_create(dir=dir, 
                                                                    dir_size=-1, 
                                                                    dir_files_count=-1, 
                                                                    path_isdir=QFileInfo(dir).isDir(), 
                                                                    profile=self.profile())
                if created:
                    self.add_source_to_table(new_source,SettingsModel.get(key="get_srcpath_datasize").value)
                    new_source.save()

        msg = self.tr("Choose directory to back up") if want_folder else self.tr("Choose file(s) to back up")
        dialog = choose_file_dialog(self, msg, want_folder=want_folder)
        dialog.open(receive)

    def source_remove(self):
        indexes = self.sourceFilesWidget.selectionModel().selectedRows()
        # sort indexes, starting with lowest
        indexes.sort()
        # remove each selected row, starting with highest index (otherways, higher indexes become invalid)
        for index in reversed(indexes):
            db_item = SourceFileModel.get(dir=self.sourceFilesWidget.item(index.row(),0).text())
            db_item.delete_instance()
            self.sourceFilesWidget.removeRow(index.row())

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
