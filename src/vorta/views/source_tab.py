from PyQt5 import uic
from ..models import SourceFileModel, BackupProfileMixin
from ..utils import get_asset, choose_file_dialog
from PyQt5.QtWidgets import QApplication, QMessageBox
import os

uifile = get_asset('UI/sourcetab.ui')
SourceUI, SourceBase = uic.loadUiType(uifile)


class SourceTab(SourceBase, SourceUI, BackupProfileMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)

        self.sourceAddFolder.clicked.connect(lambda: self.source_add(want_folder=True))
        self.sourceAddFile.clicked.connect(lambda: self.source_add(want_folder=False))
        self.sourceRemove.clicked.connect(self.source_remove)
        self.paste.clicked.connect(self.paste_text)
        self.excludePatternsField.textChanged.connect(self.save_exclude_patterns)
        self.excludeIfPresentField.textChanged.connect(self.save_exclude_if_present)
        self.oneFilesystem.stateChanged.connect(self.save_one_filesystem)
        self.excludeCache.stateChanged.connect(self.save_exclude_caches)
        self.populate_from_profile()

    def populate_from_profile(self):
        profile = self.profile()
        self.excludePatternsField.textChanged.disconnect()
        self.excludeIfPresentField.textChanged.disconnect()
        self.oneFilesystem.stateChanged.disconnect()
        self.excludeCache.stateChanged.disconnect()
        self.sourceFilesWidget.clear()
        self.excludePatternsField.clear()
        self.excludeIfPresentField.clear()

        for source in SourceFileModel.select().where(SourceFileModel.profile == profile):
            self.sourceFilesWidget.addItem(source.dir)

        self.excludePatternsField.appendPlainText(profile.exclude_patterns)
        self.excludeIfPresentField.appendPlainText(profile.exclude_if_present)
        self.oneFilesystem.setChecked(profile.one_filesystem)
        self.excludeCache.setChecked(profile.exclude_caches)
        self.excludePatternsField.textChanged.connect(self.save_exclude_patterns)
        self.excludeIfPresentField.textChanged.connect(self.save_exclude_if_present)
        self.oneFilesystem.stateChanged.connect(self.save_one_filesystem)
        self.excludeCache.stateChanged.connect(self.save_exclude_caches)

    def source_add(self, want_folder):
        def receive():
            dir = dialog.selectedFiles()
            if dir:
                new_source, created = SourceFileModel.get_or_create(dir=dir[0], profile=self.profile())
                if created:
                    self.sourceFilesWidget.addItem(dir[0])
                    new_source.save()

        msg = self.tr("Choose directory to back up") if want_folder else self.tr("Choose file to back up")
        dialog = choose_file_dialog(self, msg, want_folder=want_folder)
        dialog.open(receive)

    def source_remove(self):
        item = self.sourceFilesWidget.takeItem(self.sourceFilesWidget.currentRow())
        if item:
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

    def save_exclude_caches(self):
        profile = self.profile()
        profile.exclude_caches = self.excludeCache.isChecked()
        profile.save()

    def save_one_filesystem(self):
        profile = self.profile()
        profile.one_filesystem = self.oneFilesystem.isChecked()
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
