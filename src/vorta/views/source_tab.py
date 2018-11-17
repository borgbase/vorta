from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog
from ..models import SourceDirModel, BackupProfileMixin
from ..utils import get_asset, choose_folder_dialog

uifile = get_asset('UI/sourcetab.ui')
SourceUI, SourceBase = uic.loadUiType(uifile)


class SourceTab(SourceBase, SourceUI, BackupProfileMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)

        self.sourceAdd.clicked.connect(self.source_add)
        self.sourceRemove.clicked.connect(self.source_remove)
        self.excludePatternsField.textChanged.connect(self.save_exclude_patterns)
        self.excludeIfPresentField.textChanged.connect(self.save_exclude_if_present)
        self.populate_from_profile()

    def populate_from_profile(self):
        profile = self.profile()
        self.excludePatternsField.textChanged.disconnect()
        self.excludeIfPresentField.textChanged.disconnect()
        self.sourceDirectoriesWidget.clear()
        self.excludePatternsField.clear()
        self.excludeIfPresentField.clear()

        for source in SourceDirModel.select().where(SourceDirModel.profile == profile):
            self.sourceDirectoriesWidget.addItem(source.dir)

        self.excludePatternsField.appendPlainText(profile.exclude_patterns)
        self.excludeIfPresentField.appendPlainText(profile.exclude_if_present)
        self.excludePatternsField.textChanged.connect(self.save_exclude_patterns)
        self.excludeIfPresentField.textChanged.connect(self.save_exclude_if_present)

    def source_add(self):
        new_source_folder = choose_folder_dialog(self, "Choose Backup Directory")
        if new_source_folder:
            new_source, created = SourceDirModel.get_or_create(dir=new_source_folder, profile=self.profile())
            if created:
                self.sourceDirectoriesWidget.addItem(new_source_folder)
                new_source.save()

    def source_remove(self):
        item = self.sourceDirectoriesWidget.takeItem(self.sourceDirectoriesWidget.currentRow())
        db_item = SourceDirModel.get(dir=item.text())
        db_item.delete_instance()
        item = None

    def save_exclude_patterns(self):
        profile = self.profile()
        profile.exclude_patterns = self.excludePatternsField.toPlainText()
        profile.save()

    def save_exclude_if_present(self):
        profile = self.profile()
        profile.exclude_if_present = self.excludeIfPresentField.toPlainText()
        profile.save()
