import enum
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePath
from typing import Optional, Union

from PyQt6 import uic
from PyQt6.QtCore import (
    QDateTime,
    QLocale,
    QMimeData,
    QModelIndex,
    QPoint,
    Qt,
    QThread,
    QUrl,
)
from PyQt6.QtGui import QColor, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QDialogButtonBox,
    QHeaderView,
    QMenu,
    QPushButton,
)

from vorta.store.models import SettingsModel
from vorta.utils import borg_compat, get_asset, pretty_bytes, uses_dark_mode
from vorta.views.utils import get_colored_icon

from .partials.treemodel import (
    FileSystemItem,
    FileTreeModel,
    FileTreeSortProxyModel,
    path_to_str,
    relative_path,
)

uifile = get_asset("UI/extractdialog.ui")
ExtractDialogUI, ExtractDialogBase = uic.loadUiType(uifile)

logger = logging.getLogger(__name__)


class ParseThread(QThread):
    """A thread parsing diff results."""

    def __init__(self, fs_data: str, model, parent=None):
        """Init."""
        super().__init__(parent)
        self.model = model
        self.fs_data = fs_data

    def run(self) -> None:
        """Do the work"""
        # handle case of a single line of result, which will already be a dict
        if isinstance(self.fs_data, dict):
            lines = [self.fs_data]
        else:
            lines = [json.loads(line) for line in self.fs_data.split("\n") if line]

        parse_json_lines(lines, self.model)


class ExtractDialog(ExtractDialogBase, ExtractDialogUI):
    """
    Show the contents of an archive and allow choosing what to extract.
    """

    def __init__(self, archive, model):
        """Init."""
        super().__init__()
        self.setupUi(self)

        self.model = model
        self.model.setParent(self)

        view = self.treeView
        view.setAlternatingRowColors(True)
        view.setUniformRowHeights(True)  # Allows for scrolling optimizations.

        # custom context menu
        self.treeView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.treeview_context_menu)

        # add sort proxy model
        self.sortproxy = ExtractSortProxyModel(self)
        self.sortproxy.setSourceModel(self.model)
        view.setModel(self.sortproxy)
        self.sortproxy.sorted.connect(self.slot_sorted)

        view.setSortingEnabled(True)

        # header
        header = view.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        # shortcuts
        shortcut_copy = QShortcut(QKeySequence.StandardKey.Copy, self.treeView)
        shortcut_copy.activated.connect(self.copy_item)

        # add extract button to button box
        self.extractButton = QPushButton(self)
        self.extractButton.setObjectName("extractButton")
        self.extractButton.setText(self.tr("Extract"))

        self.buttonBox.addButton(self.extractButton, QDialogButtonBox.ButtonRole.AcceptRole)

        self.archiveNameLabel.setText(f"{archive.name}, {archive.time}")
        diff_result_display_mode = SettingsModel.get(key='extract_files_display_mode').str_value

        # connect signals
        self.comboBoxDisplayMode.currentIndexChanged.connect(self.change_display_mode)
        self.comboBoxDisplayMode.setCurrentIndex(int(diff_result_display_mode))
        self.bFoldersOnTop.toggled.connect(self.sortproxy.keepFoldersOnTop)
        self.bCollapseAll.clicked.connect(self.treeView.collapseAll)

        self.buttonBox.rejected.connect(self.close)
        self.buttonBox.accepted.connect(self.accept)

        self.set_icons()

        # Connect to palette change
        QApplication.instance().paletteChanged.connect(lambda p: self.set_icons())

    def retranslateUi(self, dialog):
        """Retranslate strings in ui."""
        super().retranslateUi(dialog)

        # setupUi calls retranslateUi
        if hasattr(self, "extractButton"):
            self.extractButton.setText(self.tr("Extract"))

    def set_icons(self):
        """Set or update the icons in the right color scheme."""
        self.bFoldersOnTop.setIcon(get_colored_icon('folder-on-top'))
        self.bCollapseAll.setIcon(get_colored_icon('angle-up-solid'))
        self.comboBoxDisplayMode.setItemIcon(0, get_colored_icon("view-list-tree"))
        self.comboBoxDisplayMode.setItemIcon(1, get_colored_icon("view-list-tree"))

    def slot_sorted(self, column, order):
        """React to the tree view being sorted."""
        # reveal selection
        selectedRows = self.treeView.selectionModel().selectedRows()
        if selectedRows:
            self.treeView.scrollTo(selectedRows[0])

    def copy_item(self, index: QModelIndex = None):
        """
        Copy an item path to the clipboard.

        Copies the first selected item if no index is specified.
        """
        if index is None or (not index.isValid()):
            indexes = self.treeView.selectionModel().selectedRows()

            if not indexes:
                return

            index = indexes[0]

        index = self.sortproxy.mapToSource(index)
        item: ExtractFileItem = index.internalPointer()
        path = PurePath('/', *item.path)

        data = QMimeData()
        data.setUrls([QUrl(path.as_uri())])
        data.setText(str(path))

        QApplication.clipboard().setMimeData(data)

    def change_display_mode(self, selection: int):
        """
        Change the display mode of the tree view

        The `selection` parameter specifies the index of the selected mode in
        `comboBoxDisplayMode`.

        """
        if selection == 0:
            mode = FileTreeModel.DisplayMode.TREE
        elif selection == 1:
            mode = FileTreeModel.DisplayMode.SIMPLIFIED_TREE
        else:
            raise Exception("Unknown item in comboBoxDisplayMode with index {}".format(selection))

        SettingsModel.update({SettingsModel.str_value: str(selection)}).where(
            SettingsModel.key == 'extract_files_display_mode'
        ).execute()

        self.model.setMode(mode)

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


def parse_json_lines(lines, model: "ExtractTree"):
    """Parse json output of `borg list`."""
    for item in lines:
        path = PurePath(item["path"])

        size = item["size"]
        mode = item["mode"]
        file_type = FileType(mode[0])
        user = item["user"]
        group = item["group"]
        health = item["healthy"]
        source_path = item["source"] if "source" in item else None

        # For python >= 3.7 this would work
        # modified = datetime.fromisoformat(item["mtime"]).ctime()
        # for python == 3.6 this must do the job
        # try:
        #     modified = datetime.strptime(item["mtime"], "%Y-%m-%dT%H:%M:%S.%f")
        # except ValueError:
        #     modified = datetime.strptime(item["mtime"], "%Y-%m-%dT%H:%M:%S")

        modified = QDateTime.fromString(
            item['isomtime' if borg_compat.check('V122') else 'mtime'], Qt.DateFormat.ISODateWithMs
        )

        model.addItem(
            (
                path,
                FileData(file_type, size, mode, user, group, health, modified, source_path),
            )
        )


# ---- Sorting ---------------------------------------------------------------


class ExtractSortProxyModel(FileTreeSortProxyModel):
    """
    Sort a ExtractTree model.
    """

    def choose_data(self, index: QModelIndex):
        """Choose the data of index used for comparison."""
        item: ExtractFileItem = index.internalPointer()
        column = index.column()

        if column == 0:
            # file name
            return self.extract_path(index)
        elif column == 1:
            return item.data.last_modified
        elif column == 2:
            return item.data.size
        else:
            return item.data.health


# ---- ExtractTree -----------------------------------------------------------


class FileType(enum.Enum):
    """File type of an item inside a borg archive."""

    FILE = "-"
    DIRECTORY = "d"
    SYMBOLIC_LINK = "l"
    LINK = SYMBOLIC_LINK
    HARD_LINK = "h"
    FIFO = "p"
    SOCKET = "s"
    CHRDEV = "c"
    BLKDEV = "b"


@dataclass
class FileData:
    """The data linked to a item inside a borg archive."""

    file_type: FileType
    size: int
    mode: str
    user: str
    group: str
    health: bool
    last_modified: QDateTime
    source_path: Optional[str] = None  # only relevant for links

    checkstate: Qt.CheckState = Qt.CheckState.Unchecked  # whether to extract the file (0, 1 or 2)
    checked_children: int = 0  # number of children checked


ExtractFileItem = FileSystemItem[FileData]


class ExtractTree(FileTreeModel[FileData]):
    """The file tree model for diff results."""

    def _make_filesystemitem(self, path, data):
        return super()._make_filesystemitem(path, data)

    def _merge_data(self, item, data):
        if data:
            logger.debug("Overriding data for {}".format(path_to_str(item.path)))
        return super()._merge_data(item, data)

    def _flat_filter(self, item):
        """
        Return whether an item is part of the flat model representation.

        The item's data might have not been set yet.
        """
        return item.data and not item.children

    def _simplify_filter(self, item: ExtractFileItem) -> bool:
        """
        Return whether an item may be merged in simplified mode.

        Allows simplification for every item.
        """
        return True

    def _process_child(self, child):
        """
        Process a new child.

        This can make some changes to the child's data like
        setting a default value if the child's data is None.
        This can also update the data of the parent.
        This must emit `dataChanged` if data is changed.

        Parameters
        ----------
        child : FileSystemItem
            The child that was added.
        """
        parent = child._parent

        if not child.data:
            child.data = FileData(FileType.DIRECTORY, 0, "", "", "", True, datetime.now())

        if child.data.size != 0:
            # update size
            size = child.data.size

            def add_size(parent):
                if parent is self.root:
                    return

                if parent.data is None:
                    raise Exception("Item {} without data".format(path_to_str(parent.path)))
                else:
                    parent.data.size += size

                # update parent
                parent = parent._parent
                if parent:
                    add_size(parent)

            add_size(parent)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """
        Returns the number of columns for the children of the given parent.

        This corresponds to the number of data (column) entries shown
        for each item in the tree view.

        Parameters
        ----------
        parent : QModelIndex, optional
            The index of the parent, by default QModelIndex()

        Returns
        -------
        int
            The number of rows.
        """
        # name, last modified, size, health
        return 4

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: Union[int, Qt.ItemDataRole] = Qt.ItemDataRole.DisplayRole,
    ):
        """
        Get the data for the given role and section in the given header.

        The header is identified by its orientation.
        For horizontal headers, the section number corresponds to
        the column number. Similarly, for vertical headers,
        the section number corresponds to the row number.

        Parameters
        ----------
        section : int
            The row or column number.
        orientation : Qt.Orientation
            The orientation of the header.
        role : int, optional
            The data role, by default Qt.ItemDataRole.DisplayRole

        Returns
        -------Improve
        Any
            The data for the specified header section.
        """
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if section == 0:
                return self.tr("Name")
            elif section == 1:
                return self.tr("Last Modified")
            elif section == 2:
                return self.tr("Size")
            elif section == 3:
                return self.tr("Health")

        return None

    def data(self, index: QModelIndex, role: Union[int, Qt.ItemDataRole] = Qt.ItemDataRole.DisplayRole):
        """
        Get the data for the given role and index.

        The indexes internal pointer references the corresponding
        `FileSystemItem`.

        Parameters
        ----------
        index : QModelIndex
            The index of the item.
        role : int, optional
            The data role, by default Qt.ItemDataRole.DisplayRole

        Returns
        -------
        Any
            The data, return None if no data is available for the role.
        """
        if not index.isValid():
            return None

        item: ExtractFileItem = index.internalPointer()
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if column == 0:
                # name
                if self.mode == self.DisplayMode.FLAT:
                    return path_to_str(item.path)

                if self.mode == self.DisplayMode.SIMPLIFIED_TREE:
                    parent = index.parent()
                    if parent == QModelIndex():
                        return path_to_str(relative_path(self.root.path, item.path))

                    return path_to_str(relative_path(parent.internalPointer().path, item.path))

                # standard tree mode
                return item.subpath
            elif column == 1:
                # last modified
                return QLocale.system().toString(item.data.last_modified, QLocale.FormatType.ShortFormat)
            elif column == 2:
                # size
                return pretty_bytes(item.data.size)
            else:
                # health
                return

        if role == Qt.ItemDataRole.BackgroundRole and column == 3:
            # health indicator
            if item.data.health:
                return QColor(Qt.GlobalColor.green) if uses_dark_mode() else QColor(Qt.GlobalColor.darkGreen)
            else:
                return QColor(Qt.GlobalColor.red) if uses_dark_mode() else QColor(Qt.GlobalColor.darkRed)

        if role == Qt.ItemDataRole.ToolTipRole:
            if column == 0:
                # name column -> display fullpath
                return path_to_str(item.path)

            # info/data tooltip -> no real size limitation
            tooltip_template = (
                "{name}\n"
                + "\n"
                + "{filetype}\n"
                + "{permissions}\n"
                + "{user} {group}\n"
                + "Modified: {last_modified}\n"
                + "Health: {health}\n"
            )

            # format
            if item.data.file_type == FileType.FILE:
                filetype = self.tr("File")
            elif item.data.file_type == FileType.DIRECTORY:
                filetype = self.tr("Directory")
            elif item.data.file_type == FileType.LINK:
                filetype = self.tr("Symbolic link")
            elif item.data.file_type == FileType.FIFO:
                filetype = self.tr("FIFO pipe")
            elif item.data.file_type == FileType.HARD_LINK:
                filetype = self.tr("Hard link")
            elif item.data.file_type == FileType.SOCKET:
                filetype = self.tr("Socket")
            elif item.data.file_type == FileType.BLKDEV:
                filetype = self.tr("Block special file")
            elif item.data.file_type == FileType.CHRDEV:
                filetype = self.tr("Character special file")
            else:
                raise Exception("Unknown filetype {}".format(item.data.file_type))

            modified = QLocale.system().toString(item.data.last_modified)

            if item.data.health:
                health = self.tr("healthy")
            else:
                health = self.tr("broken")

            tooltip = tooltip_template.format(
                name=item.path[-1],
                filetype=filetype,
                permissions=item.data.mode,
                user=item.data.user,
                group=item.data.group,
                last_modified=modified,
                health=health,
            )

            if item.data.source_path:
                tooltip += self.tr("Linked to: {}").format(item.data.source_path)

            return tooltip

        if role == Qt.ItemDataRole.CheckStateRole and column == 0:
            return item.data.checkstate

    def setData(
        self,
        index: QModelIndex,
        value: Union[int, Qt.CheckState],
        role: Union[int, Qt.ItemDataRole] = Qt.ItemDataRole.CheckStateRole,
    ) -> bool:
        """
        Sets the role data for the item at index to value.

        Returns true if successful; otherwise returns false.
        The dataChanged() signal should be emitted if the data was
        successfully set.
        """
        if role != Qt.ItemDataRole.CheckStateRole:
            return False

        # convert int to enum member
        # PyQt6 will pass Ints where there were IntEnums in PyQt5
        if isinstance(value, int):
            value = Qt.CheckState(value)
        if isinstance(role, int):
            role = Qt.ItemDataRole(role)

        item: ExtractFileItem = index.internalPointer()

        if value == item.data.checkstate:
            return True

        super_index = index.parent()
        if super_index == QModelIndex():
            super_item = self.root
        else:
            super_item: ExtractFileItem = super_index.internalPointer()

        parent = item._parent
        while parent != super_item:
            if value == Qt.CheckState.Unchecked:
                # must have been one of the others previously
                parent.data.checked_children -= 1
            elif item.data.checkstate == Qt.CheckState.Unchecked:  # old value
                # change from partially checked to checked
                # or the other way around does not change this count
                parent.data.checked_children += 1

            if parent.data.checked_children:
                parent.data.checkstate = Qt.CheckState.PartiallyChecked
            else:
                parent.data.checkstate = Qt.CheckState.Unchecked

            parent = parent._parent

        if super_index != QModelIndex():
            if value == Qt.CheckState.Unchecked:
                # must have been one of the others previously
                super_item.data.checked_children -= 1
            elif item.data.checkstate == Qt.CheckState.Unchecked:
                # change from partially checked to checked
                # or the other way around does not change this count
                super_item.data.checked_children += 1

            # update parent's state and possibly the parent's parent's state
            if super_item.data.checked_children:
                self.setData(super_index, Qt.CheckState.PartiallyChecked, role)
            else:
                self.setData(super_index, Qt.CheckState.Unchecked, role)

        # update state of the children without changing their parents' states
        if value != Qt.CheckState.PartiallyChecked:
            self.set_checkstate_recursively(index, value)

        # update this item's state
        item.data.checkstate = value
        self.dataChanged.emit(index, index, (role,))

        return True

    def set_checkstate_recursively(self, index: QModelIndex, value: Qt.CheckState):
        """
        Set the checkstate of the children of an index recursively.

        Parameters
        ----------
        index : QModelIndex
            The parent index to start with.
        value : Qt.CheckState
            The state to set.
        """

        number_children = self.rowCount(index)
        if not number_children:
            return

        index.internalPointer().data.checked_children = 0 if value == Qt.CheckState.Unchecked else number_children

        item = index.internalPointer()
        for i in range(number_children):
            child = self.index(i, 0, index)
            child_item: ExtractFileItem = child.internalPointer()
            child_item.data.checkstate = value

            # set state of hidden items
            parent = child_item._parent
            while parent != item:
                # hidden parent must have 1 child
                parent.data.checked_children = 0 if value == Qt.CheckState.Unchecked else self.rowCount(child)
                parent.data.checkstate = value

                parent = parent._parent

            # set state of this child's children
            self.set_checkstate_recursively(child, value)

        self.dataChanged.emit(
            self.index(0, 0, index),
            self.index(0, number_children - 1, index),
            (Qt.ItemDataRole.CheckStateRole,),
        )

    def flags(self, index: QModelIndex):
        """
        Returns the item flags for the given index.

        The base class implementation returns a combination of flags
        that enables the item (ItemIsEnabled) and
        allows it to be selected (ItemIsSelectable).

        Parameters
        ----------
        index : QModelIndex
            The index.

        Returns
        -------
        Qt.ItemFlags
            The flags.
        """
        flags = super().flags(index)
        if index.column() == 0:
            flags |= Qt.ItemFlag.ItemIsUserCheckable

        return flags
