from PyQt5 import uic
from ..models import SourceDirModel, BackupProfileMixin
from ..utils import get_asset, choose_folder_dialog

uifile = get_asset('UI/sourcetab.ui')
SourceUI, SourceBase = uic.loadUiType(uifile)


class SourceTab(SourceBase, SourceUI, BackupProfileMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)

        self.sourceAddFolder.clicked.connect(lambda: self.source_add(want_folder=True))
        self.sourceAddFile.clicked.connect(lambda: self.source_add(want_folder=False))
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

    def source_add(self, want_folder):
        def receive():
            dir = dialog.selectedFiles()
            if dir:
                new_source, created = SourceDirModel.get_or_create(dir=dir[0], profile=self.profile())
                if created:
                    self.sourceDirectoriesWidget.addItem(dir[0])
                    new_source.save()

        item = "directory" if want_folder else "file"
        dialog = choose_folder_dialog(self, "Choose %s to back up" % item, want_folder=want_folder)
        self._file_dialog = dialog  # for pytest
        dialog.open(receive)

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
