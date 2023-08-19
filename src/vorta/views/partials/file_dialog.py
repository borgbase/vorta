from abc import ABCMeta, abstractmethod
from pathlib import PurePath

from PyQt6.QtCore import (
    QMimeData,
    QModelIndex,
    QPoint,
    Qt,
    QUrl,
)
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication, QDialog, QMenu, QTreeView

from vorta.views.utils import get_colored_icon


class BaseFileDialog(QDialog):
    __metaclass__ = ABCMeta

    def __init__(self, model):
        super().__init__()
        self.setupUi(self)

        self.model = model
        self.model.setParent(self)

        self.treeView: QTreeView
        self.treeView.setUniformRowHeights(True)  # Allows for scrolling optimizations.
        self.treeView.setAlternatingRowColors(True)
        self.treeView.setTextElideMode(Qt.TextElideMode.ElideMiddle)  # to better see name of paths

        # custom context menu
        self.treeView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.treeview_context_menu)

        # shortcuts
        shortcut_copy = QShortcut(QKeySequence.StandardKey.Copy, self.treeView)
        shortcut_copy.activated.connect(self.copy_item)

        # add sort proxy model
        self.sortproxy = self.get_sort_proxy_model()
        self.sortproxy.setSourceModel(self.model)
        self.treeView.setModel(self.sortproxy)
        self.sortproxy.sorted.connect(self.slot_sorted)

        self.treeView.setSortingEnabled(True)

        # signals

        self.comboBoxDisplayMode.currentIndexChanged.connect(self.change_display_mode)
        diff_result_display_mode = self.get_diff_result_display_mode()
        self.comboBoxDisplayMode.setCurrentIndex(int(diff_result_display_mode))
        self.bFoldersOnTop.toggled.connect(self.sortproxy.keepFoldersOnTop)
        self.bCollapseAll.clicked.connect(self.treeView.collapseAll)

        self.bSearch.clicked.connect(self.submitSearchPattern)
        self.sortproxy.searchStringError.connect(self.searchStringError)

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        # Add a cross icon inside the search field to clear the search string
        self.searchWidget.setClearButtonEnabled(True)
        # self.searchLineEdit.textChanged.connect(self.searchLineEditChanged)

        self.set_icons()

        # Connect to palette change
        QApplication.instance().paletteChanged.connect(lambda p: self.set_icons())

    @abstractmethod
    def get_sort_proxy_model(self):
        pass

    @abstractmethod
    def get_diff_result_display_mode(self):
        pass

    @abstractmethod
    def set_archive_names(self):
        pass

    def copy_item(self, index: QModelIndex = None):
        """
        Copy a diff item path to the clipboard.

        Copies the first selected item if no index is specified.
        """
        if index is None or (not index.isValid()):
            indexes = self.treeView.selectionModel().selectedRows()

            if not indexes:
                return

            index = indexes[0]

        index = self.sortproxy.mapToSource(index)
        item = index.internalPointer()
        path = PurePath('/', *item.path)

        data = QMimeData()
        data.setUrls([QUrl(path.as_uri())])
        data.setText(str(path))

        QApplication.clipboard().setMimeData(data)

    def treeview_context_menu(self, pos: QPoint):
        """Display a context menu for `treeView`."""
        index = self.treeView.indexAt(pos)
        if not index.isValid():
            # popup only for items
            return

        menu = QMenu(self.treeView)

        menu.addAction(get_colored_icon('copy'), self.tr("Copy"), lambda: self.copy_item(index))

        if self.model.getMode() != self.model.DisplayMode.FLAT:
            menu.addSeparator()
            menu.addAction(
                get_colored_icon('angle-down-solid'),
                self.tr("Expand recursively"),
                lambda: self.treeView.expandRecursively(index),
            )

        menu.popup(self.treeView.viewport().mapToGlobal(pos))

    def slot_sorted(self, column, order):
        """React to the tree view being sorted."""
        # reveal selection
        selectedRows = self.treeView.selectionModel().selectedRows()
        if selectedRows:
            self.treeView.scrollTo(selectedRows[0])

    def keyPressEvent(self, event):
        if event.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter] and self.searchWidget.hasFocus():
            self.submitSearchPattern()
        else:
            super().keyPressEvent(event)

    def submitSearchPattern(self):
        self.sortproxy.setSearchString(self.searchWidget.text())

    def searchStringError(self, error: bool):
        self.searchWidget.setStyleSheet("border: 2px solid red;" if error else "")
