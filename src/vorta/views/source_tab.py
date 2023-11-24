import logging
import os
from pathlib import PurePath

from PyQt6 import QtCore, QtGui, uic
from PyQt6.QtCore import QFileInfo, QMimeData, QPoint, Qt, QUrl, pyqtSlot
from PyQt6.QtGui import QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QHeaderView,
    QMenu,
    QMessageBox,
    QTableWidgetItem,
)

from vorta.store.models import BackupProfileMixin, SettingsModel, SourceFileModel
from vorta.utils import (
    FilePathInfoAsync,
    choose_file_dialog,
    get_asset,
    pretty_bytes,
    sort_sizes,
)
from vorta.views.exclude_dialog import ExcludeDialog
from vorta.views.utils import get_colored_icon

uifile = get_asset('UI/sourcetab.ui')
SourceUI, SourceBase = uic.loadUiType(uifile)

logger = logging.getLogger(__name__)


class SourceColumn:
    Path = 0
    Size = 1
    FilesCount = 2


class SizeItem(QTableWidgetItem):
    def __init__(self, s):
        super().__init__(s)
        self.setTextAlignment(Qt.AlignmentFlag.AlignVCenter + Qt.AlignmentFlag.AlignRight)

    def __lt__(self, other):
        if other.text() == '':
            return False
        elif self.text() == '':
            return True
        else:
            return sort_sizes([self.text(), other.text()]) == [
                self.text(),
                other.text(),
            ]


class FilesCount(QTableWidgetItem):
    def __lt__(self, other):
        # Verify that conversion is only performed on valid integers
        # If one of the 2 elements is no number, put these elements at the end
        # This is important if the text is "Calculating..." or ""
        if self.text().isdigit() and other.text().isdigit():
            return int(self.text()) < int(other.text())  # Compare & return result
        else:
            if not self.text().isdigit():
                return 1  # Move one down if current item has no valid count
            if not other.text().isdigit():
                return 0


class SourceTab(SourceBase, SourceUI, BackupProfileMixin):
    updateThreads = []

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)

        # Prepare source files view
        header = self.sourceFilesWidget.horizontalHeader()
        header.setVisible(True)
        header.setSortIndicatorShown(1)

        header.setSectionResizeMode(SourceColumn.Path, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(SourceColumn.Size, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(SourceColumn.FilesCount, QHeaderView.ResizeMode.ResizeToContents)

        self.sourceFilesWidget.setSortingEnabled(True)
        self.sourceFilesWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sourceFilesWidget.customContextMenuRequested.connect(self.sourceitem_contextmenu)

        # Prepare add button
        self.addMenu = QMenu(self.addButton)
        self.addFilesAction = self.addMenu.addAction(self.tr("Files"), lambda: self.source_add(want_folder=False))
        self.addFoldersAction = self.addMenu.addAction(self.tr("Folders"), lambda: self.source_add(want_folder=True))
        self.pasteAction = self.addMenu.addAction(self.tr("Paste"), self.paste_text)

        self.addButton.setMenu(self.addMenu)

        # shortcuts
        shortcut_copy = QShortcut(QtGui.QKeySequence.StandardKey.Copy, self.sourceFilesWidget)
        shortcut_copy.activated.connect(self.source_copy)

        # Connect signals
        self.removeButton.clicked.connect(self.source_remove)
        self.updateButton.clicked.connect(self.sources_update)
        self.bExclude.clicked.connect(self.show_exclude_dialog)
        header.sortIndicatorChanged.connect(self.update_sort_order)

        # Connect to palette change
        QApplication.instance().paletteChanged.connect(lambda p: self.set_icons())

        # Populate
        self.populate_from_profile()
        self.set_icons()

    def set_icons(self):
        "Used when changing between light- and dark mode"
        self.addButton.setIcon(get_colored_icon('plus'))
        self.removeButton.setIcon(get_colored_icon('minus'))
        self.updateButton.setIcon(get_colored_icon('refresh'))
        self.addFilesAction.setIcon(get_colored_icon('file'))
        self.addFoldersAction.setIcon(get_colored_icon('folder'))
        self.pasteAction.setIcon(get_colored_icon('paste'))

        for row in range(self.sourceFilesWidget.rowCount()):
            path_item = self.sourceFilesWidget.item(row, SourceColumn.Path)
            db_item = SourceFileModel.get(dir=path_item.text(), profile=self.profile())

            if db_item.path_isdir:
                path_item.setIcon(get_colored_icon('folder'))
            else:
                path_item.setIcon(get_colored_icon('file'))

    @pyqtSlot(QPoint)
    def sourceitem_contextmenu(self, pos: QPoint):
        """Show a context menu for the source item at `pos`."""
        # index under cursor
        index = self.sourceFilesWidget.indexAt(pos)
        if not index.isValid():
            return  # popup only for items

        menu = QMenu(self.sourceFilesWidget)

        menu.addAction(
            get_colored_icon('copy'),
            self.tr("Copy"),
            lambda: self.source_copy(index=index),
        )
        menu.addAction(get_colored_icon('minus'), self.tr("Remove"), self.source_remove)

        menu.popup(self.sourceFilesWidget.viewport().mapToGlobal(pos))

    def set_path_info(self, path, data_size, files_count):
        # disable sorting temporarily
        sorting = self.sourceFilesWidget.isSortingEnabled()
        self.sourceFilesWidget.setSortingEnabled(False)

        items = self.sourceFilesWidget.findItems(path, QtCore.Qt.MatchFlag.MatchExactly)
        # Conversion int->str->int needed because QT limits int to 32-bit
        data_size = int(data_size)
        files_count = int(files_count)

        for item in items:
            db_item = SourceFileModel.get(dir=path, profile=self.profile())
            if QFileInfo(path).isDir():
                self.sourceFilesWidget.item(item.row(), SourceColumn.FilesCount).setText(format(files_count))
                db_item.path_isdir = True
                self.sourceFilesWidget.item(item.row(), SourceColumn.Path).setIcon(get_colored_icon('folder'))
            else:
                # No files count, if entry itself is a file
                self.sourceFilesWidget.item(item.row(), SourceColumn.FilesCount).setText("")
                db_item.path_isdir = False
                self.sourceFilesWidget.item(item.row(), SourceColumn.Path).setIcon(get_colored_icon('file'))

            self.sourceFilesWidget.item(item.row(), SourceColumn.Size).setText(pretty_bytes(data_size))

            db_item.dir_size = data_size
            db_item.dir_files_count = files_count
            db_item.save()
        # Remove thread from list when it's done
        for thrd in self.updateThreads:
            if thrd.objectName() == path:
                self.updateThreads.remove(thrd)

        # enable sorting again
        self.sourceFilesWidget.setSortingEnabled(sorting)

    def update_path_info(self, index_row: int):
        """
        Update the information for the source in the given table row.

        This displays `Calculating...` in the updated rows and creates a
        `FilePathInfoAsync` instance to get the new information.
        The method `set_path_info` will update the row with the information
        provided by this instance.

        Parameters
        ----------
        index_row : int
            The index of the row to update.
        """
        logger.debug(f"Updating source in row {index_row}.")  # Debug #1080

        path = self.sourceFilesWidget.item(index_row, SourceColumn.Path).text()
        self.sourceFilesWidget.item(index_row, SourceColumn.Size).setText(self.tr("Calculating…"))
        self.sourceFilesWidget.item(index_row, SourceColumn.FilesCount).setText(self.tr("Calculating…"))
        getDir = FilePathInfoAsync(path, self.profile().exclude_patterns)
        getDir.signal.connect(self.set_path_info)
        getDir.setObjectName(path)
        self.updateThreads.append(getDir)  # this is ugly, is there a better way to keep the thread object?
        getDir.start()

    def add_source_to_table(self, source, update_data=None):
        # disable sorting temporarily
        sorting = self.sourceFilesWidget.isSortingEnabled()
        self.sourceFilesWidget.setSortingEnabled(False)

        if update_data is None:
            update_data = SettingsModel.get(key="get_srcpath_datasize").value

        index_row = self.sourceFilesWidget.rowCount()
        self.sourceFilesWidget.setRowCount(self.sourceFilesWidget.rowCount() + 1)
        # Insert all items on current row, add tooltip containing the path name
        new_item = QTableWidgetItem(source.dir)
        new_item.setToolTip(source.dir)
        self.sourceFilesWidget.setItem(index_row, SourceColumn.Path, new_item)
        self.sourceFilesWidget.setItem(index_row, SourceColumn.Size, SizeItem(""))
        self.sourceFilesWidget.setItem(index_row, SourceColumn.FilesCount, FilesCount(""))

        logger.debug(f"Added item number {index_row}" + f" from {self.sourceFilesWidget.rowCount()}")

        if update_data:
            self.update_path_info(index_row)

            # Debug #1080
            logger.debug("Updated info for previously added item.")

        else:  # Use cached data from DB
            if source.dir_size > -1:
                self.sourceFilesWidget.item(index_row, SourceColumn.Size).setText(pretty_bytes(source.dir_size))

                if source.path_isdir:
                    self.sourceFilesWidget.item(index_row, SourceColumn.FilesCount).setText(
                        format(source.dir_files_count)
                    )
                    self.sourceFilesWidget.item(index_row, SourceColumn.Path).setIcon(get_colored_icon('folder'))
                else:
                    self.sourceFilesWidget.item(index_row, SourceColumn.Path).setIcon(get_colored_icon('file'))

        # enable sorting again
        self.sourceFilesWidget.setSortingEnabled(sorting)

    def populate_from_profile(self):
        profile = self.profile()
        self.sourceFilesWidget.setRowCount(0)  # Clear rows

        for source in SourceFileModel.select().where(SourceFileModel.profile == profile):
            self.add_source_to_table(source, False)

        # Fetch the Sort by Column and order
        sourcetab_sort_column = int(SettingsModel.get(key='sourcetab_sort_column').str_value)
        sourcetab_sort_order = int(SettingsModel.get(key='sourcetab_sort_order').str_value)

        # Sort items as per settings
        self.sourceFilesWidget.sortItems(sourcetab_sort_column, Qt.SortOrder(sourcetab_sort_order))

    def update_sort_order(self, column: int, order: int):
        """Save selected sort by column and order to settings"""
        SettingsModel.update({SettingsModel.str_value: str(column)}).where(
            SettingsModel.key == 'sourcetab_sort_column'
        ).execute()
        SettingsModel.update({SettingsModel.str_value: str(order.value)}).where(
            SettingsModel.key == 'sourcetab_sort_order'
        ).execute()

    def sources_update(self):
        """
        Update each row in the sources table.

        Calls `update_path_info` for each row. to do the job.
        """
        row_count = self.sourceFilesWidget.rowCount()

        logger.debug(f"Updating sources ({row_count})")  # Debug #1080

        for row in range(0, row_count):
            self.update_path_info(row)  # Update data for each entry

    def source_add(self, want_folder):
        def receive():
            dirs = dialog.selectedFiles()
            for dir in dirs:
                if not os.access(dir, os.R_OK):
                    msg = QMessageBox()
                    msg.setText(self.tr(f"You don't have read access to {dir}."))
                    msg.exec()
                    return

                new_source, created = SourceFileModel.get_or_create(dir=dir, profile=self.profile())
                if created:
                    self.add_source_to_table(new_source)
                    new_source.save()

        msg = self.tr("Choose directory to back up") if want_folder else self.tr("Choose file(s) to back up")
        dialog = choose_file_dialog(self, msg, want_folder=want_folder)
        dialog.open(receive)

    def source_copy(self, index=None):
        """
        Copy a source path to the clipboard.

        Copies the first selected source if no index is specified.
        """
        if index is None:
            indexes = self.sourceFilesWidget.selectionModel().selectedRows()

            if not indexes:
                return

            index = indexes[0]

        path = PurePath(self.sourceFilesWidget.item(index.row(), SourceColumn.Path).text())

        data = QMimeData()
        data.setUrls([QUrl(path.as_uri())])
        data.setText(str(path))

        QApplication.clipboard().setMimeData(data)

    def source_remove(self):
        indexes = self.sourceFilesWidget.selectionModel().selectedRows()
        profile = self.profile()
        # sort indexes, starting with lowest
        indexes.sort()
        # remove each selected row, starting with highest index (otherways, higher indexes become invalid)
        for index in reversed(indexes):
            db_item = SourceFileModel.get(
                dir=self.sourceFilesWidget.item(index.row(), SourceColumn.Path).text(),
                profile=profile,
            )
            db_item.delete_instance()
            self.sourceFilesWidget.removeRow(index.row())

            logger.debug(f"Removed source in row {index.row()}")

    def show_exclude_dialog(self):
        window = ExcludeDialog(self.profile(), self)
        window.setParent(self, QtCore.Qt.WindowType.Sheet)
        self._window = window  # for testing
        window.show()

    def paste_text(self):
        sources = QApplication.clipboard().text().splitlines()
        invalidSources = ""
        for source in sources:
            if len(source) > 0:  # Ignore empty newlines
                if source.startswith('file://'):  # Allow pasting multiple files/folders copied from file manager
                    source = source[7:]
                if not os.path.exists(source):
                    invalidSources = invalidSources + "\n" + source
                else:
                    new_source, created = SourceFileModel.get_or_create(dir=source, profile=self.profile())
                    if created:
                        self.add_source_to_table(new_source)
                        new_source.save()

        if len(invalidSources) != 0:  # Check if any invalid paths
            msg = QMessageBox()
            msg.setText(self.tr("Some of your sources are invalid:") + invalidSources)
            self._msg = msg  # for testing
            msg.exec()
