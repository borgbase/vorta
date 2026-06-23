import logging
from pathlib import PurePath

from peewee import fn
from PyQt6 import QtCore, QtGui, uic
from PyQt6.QtCore import QFileInfo, QMimeData, QPoint, QSortFilterProxyModel, Qt, QUrl, pyqtSlot
from PyQt6.QtGui import QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QHeaderView,
    QMenu,
    QTableWidgetItem,
)

from vorta.filedialog import VortaFileSelector
from vorta.store.models import SettingsModel, SourceFileModel
from vorta.utils import (
    FilePathInfoAsync,
    get_asset,
    pretty_bytes,
    sort_sizes,
)
from vorta.views.base_tab import BaseTab
from vorta.views.dialogs.archive.exclude import ExcludeDialog
from vorta.views.partials.source_files_table_model import SourceFilesModel
from vorta.views.utils import get_colored_icon

uifile = get_asset('UI/source_tab.ui')
SourceUI, SourceBase = uic.loadUiType(uifile)

logger = logging.getLogger(__name__)


class SizeItem(QTableWidgetItem):
    """Right-aligned, size-aware sortable cell, still consumed by archive_tab's QTableWidget."""

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


class SourceTab(BaseTab, SourceBase, SourceUI):
    updateThreads = []

    def __init__(self, parent=None, profile_provider=None):
        super().__init__(parent=parent, profile_provider=profile_provider)
        self.setupUi(parent)

        # Prepare source files view
        self.source_model = SourceFilesModel(self)
        self.source_proxy = QSortFilterProxyModel(self)
        self.source_proxy.setSourceModel(self.source_model)
        self.source_proxy.setSortRole(SourceFilesModel.SortRole)
        self.sourceFilesWidget.setModel(self.source_proxy)

        header = self.sourceFilesWidget.horizontalHeader()
        header.setVisible(True)
        header.setSortIndicatorShown(1)

        header.setSectionResizeMode(SourceFilesModel.COL_PATH, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(SourceFilesModel.COL_SIZE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(SourceFilesModel.COL_FILES, QHeaderView.ResizeMode.ResizeToContents)

        self.sourceFilesWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sourceFilesWidget.customContextMenuRequested.connect(self.sourceitem_contextmenu)
        self.sourceFilesWidget.setAlternatingRowColors(True)

        # Shortcuts
        shortcut_copy = QShortcut(QtGui.QKeySequence.StandardKey.Copy, self.sourceFilesWidget)
        shortcut_copy.activated.connect(self.source_copy)

        # Connect signals
        self.addButton.clicked.connect(self.source_add)
        self.removeButton.clicked.connect(self.source_remove)
        self.updateButton.clicked.connect(self.sources_update)
        self.bExclude.clicked.connect(self.show_exclude_dialog)
        header.sortIndicatorChanged.connect(self.update_sort_order)

        # Populate
        self.track_profile_change(call_now=True)
        self.set_icons()

        # Listen for events
        self.track_palette_change()

    def set_icons(self):
        "Used when changing between light- and dark mode"
        self.addButton.setIcon(get_colored_icon('plus'))
        self.removeButton.setIcon(get_colored_icon('minus'))
        self.updateButton.setIcon(get_colored_icon('refresh'))
        self.sourceFilesWidget.viewport().update()  # model rebuilds themed row icons lazily

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
        # Conversion int->str->int needed because QT limits int to 32-bit
        data_size = int(data_size)
        files_count = int(files_count)

        # Returns None if the source was removed while recalculating (#1080 / #2435).
        source = self.source_model.set_path_info(path, data_size, files_count, QFileInfo(path).isDir())
        if source is not None:
            source.save()
            self.update_total_size()
        self._discard_update_thread(path)

    def _discard_update_thread(self, path):
        for thrd in self.updateThreads[:]:
            if thrd.objectName() == path:
                try:
                    thrd.signal.disconnect(self.set_path_info)
                except (RuntimeError, TypeError):
                    pass
                self.updateThreads.remove(thrd)

    def update_path_info(self, path: str):
        """Mark ``path`` as calculating and spawn the worker that fills in its size/count.

        `set_path_info` applies the result, keyed on ``path`` rather than a row index so a
        row removed mid-calculation is skipped (#1080 / #2435).
        """
        logger.debug(f"Updating source {path}.")  # Debug #1080

        self.source_model.mark_calculating(path)
        getDir = FilePathInfoAsync(path, self.profile().get_combined_exclusion_string())
        getDir.signal.connect(self.set_path_info)
        getDir.setObjectName(path)
        self.updateThreads.append(getDir)  # this is ugly, is there a better way to keep the thread object?
        getDir.start()

    def add_source_to_table(self, source, update_data=None):
        if update_data is None:
            update_data = SettingsModel.get(key="get_srcpath_datasize").value

        self.source_model.add_source(source)

        if update_data:
            self.update_path_info(source.dir)
            logger.debug("Updated info for previously added item.")  # Debug #1080

    def populate_from_profile(self):
        profile = self.profile()
        sources = list(SourceFileModel.select().where(SourceFileModel.profile == profile))
        self.source_model.set_rows(sources)
        self.update_total_size()
        # Fetch the Sort by Column and order
        sourcetab_sort_column = int(SettingsModel.get(key='sourcetab_sort_column').str_value)
        sourcetab_sort_order = int(SettingsModel.get(key='sourcetab_sort_order').str_value)

        # Sort items as per settings
        self.sourceFilesWidget.sortByColumn(sourcetab_sort_column, Qt.SortOrder(sourcetab_sort_order))

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
        Update each source in the sources table.

        Calls `update_path_info` for each source to do the job.
        """
        row_count = self.source_model.rowCount()

        logger.debug(f"Updating sources ({row_count})")  # Debug #1080

        for row in range(row_count):
            self.update_path_info(self.source_model.source_at(row).dir)

    def source_add(self):
        # Selected paths from file dialog
        file_dialog = VortaFileSelector(
            self, window_title='Add Files and Folders', title='Select files and folders to include as sources:'
        )
        paths = file_dialog.get_paths()
        if paths:
            for path in paths:
                # Add sources to the table
                new_source, created = SourceFileModel.get_or_create(dir=path, profile=self.profile())
                if created:
                    self.add_source_to_table(new_source)
                    new_source.save()
            self.update_total_size()

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

        source = index.data(SourceFilesModel.SourceRole)
        if source is None:
            return
        path = PurePath(source.dir)

        data = QMimeData()
        data.setUrls([QUrl(path.as_uri())])
        data.setText(str(path))

        QApplication.clipboard().setMimeData(data)

    def source_remove(self):
        indexes = self.sourceFilesWidget.selectionModel().selectedRows()
        if not indexes:
            return
        # Resolve the backing sources up front; row indices shift once rows are removed.
        sources = [index.data(SourceFilesModel.SourceRole) for index in indexes]
        for source in sources:
            if source is None:
                continue
            source.delete_instance()
            self._discard_update_thread(source.dir)
            logger.debug(f"Removed source {source.dir}")
        self.populate_from_profile()

    def update_total_size(self):
        """
        Update the total size and files count for all sources.
        """
        total_size, total_files = (
            SourceFileModel.select(fn.SUM(SourceFileModel.dir_size), fn.SUM(SourceFileModel.dir_files_count))
            .where(SourceFileModel.profile == self.profile(), SourceFileModel.dir_size >= 0)
            .scalar(as_tuple=True)
        )

        if total_size is not None:
            total_files = total_files or 0
            self.totalSizeLabel.setText(
                self.tr("Total Size: {size}, {count} files").format(size=pretty_bytes(total_size), count=total_files)
            )
        else:
            self.totalSizeLabel.setText("")

    def show_exclude_dialog(self):
        window = ExcludeDialog(self.profile(), self)
        window.setParent(self, QtCore.Qt.WindowType.Sheet)
        self._window = window  # for testing
        window.show()

    # NOTE: This function is temporarily removed.
    # Reason: This paste option has been removed as part of the addition of new File Dialog.
    # This function is no longer used. Kept here for reference or possible future use.

    # def paste_text(self):
    #     sources = QApplication.clipboard().text().splitlines()
    #     invalidSources = ""
    #     for source in sources:
    #         if len(source) > 0:  # Ignore empty newlines
    #             if source.startswith('file://'):  # Allow pasting multiple files/folders copied from file manager
    #                 source = source[7:]
    #             if not os.path.exists(source):
    #                 invalidSources = invalidSources + "\n" + source
    #             else:
    #                 new_source, created = SourceFileModel.get_or_create(dir=source, profile=self.profile())
    #                 if created:
    #                     self.add_source_to_table(new_source)
    #                     new_source.save()

    #     if len(invalidSources) != 0:  # Check if any invalid paths
    #         msg = QMessageBox()
    #         msg.setText(self.tr("Some of your sources are invalid:") + invalidSources)
    #         self._msg = msg  # for testing
    #         msg.exec()
