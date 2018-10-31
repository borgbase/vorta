from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog
from ..models import SourceDirModel, BackupProfileMixin
from ..utils import get_asset

uifile = get_asset('UI/sourcetab.ui')
SourceUI, SourceBase = uic.loadUiType(uifile)


class SourceTab(SourceBase, SourceUI, BackupProfileMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)

        self.sourceAdd.clicked.connect(self.source_add)
        self.sourceRemove.clicked.connect(self.source_remove)
        for source in SourceDirModel.select():
            self.sourceDirectoriesWidget.addItem(source.dir)

        self.excludePatternsField.appendPlainText(self.profile.exclude_patterns)
        self.excludeIfPresentField.appendPlainText(self.profile.exclude_if_present)

        self.excludePatternsField.textChanged.connect(self.save_exclude_patterns)
        self.excludeIfPresentField.textChanged.connect(self.save_exclude_if_present)

    def source_add(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly
        options |= QFileDialog.DontUseNativeDialog
        fileName = QFileDialog.getExistingDirectory(
            self, "Choose Backup Directory", "", options=options)
        if fileName:
            new_source, created = SourceDirModel.get_or_create(dir=fileName)
            if created:
                self.sourceDirectoriesWidget.addItem(fileName)
                new_source.save()

    def source_remove(self):
        item = self.sourceDirectoriesWidget.takeItem(self.sourceDirectoriesWidget.currentRow())
        db_item = SourceDirModel.get(dir=item.text())
        db_item.delete_instance()
        item = None

    def save_exclude_patterns(self):
        profile = self.profile
        profile.exclude_patterns = self.excludePatternsField.toPlainText()
        profile.save()

    def save_exclude_if_present(self):
        profile = self.profile
        profile.exclude_if_present = self.excludeIfPresentField.toPlainText()
        profile.save()
