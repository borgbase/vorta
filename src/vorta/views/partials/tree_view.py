from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt

import os
import abc

from vorta.utils import get_dict_from_list, pretty_bytes


class FolderItem:
    def __init__(
        self,
        path,
        name,
        modified,
        files_with_attributes,
        nested_file_list,
        selected_files_folders=None,
        parent=None,
    ):
        self.parentItem = parent
        self.path = path
        self.itemData = [name, modified]
        self.childItems = []
        self.checkedState = False
        self.files_with_attributes = files_with_attributes
        self.nested_file_list = nested_file_list
        self.selected_files_folders = selected_files_folders

        # Pre-filter children
        self._filtered_children = []
        search_path = os.path.join(self.path, name)
        if parent is None:  # Find path for root folder
            for root_folder in nested_file_list.keys():
                self._filtered_children.append((0, "", root_folder, "",))
        else:
            self.checkedState = (
                parent.checkedState
            )  # If there is a parent, use its checked-status.

            # This adds direct children.
            self._filtered_children = [
                f for f in files_with_attributes if search_path == f[3]
            ]

            # Add nested folders.
            for immediate_child in get_dict_from_list(
                nested_file_list, search_path.split("/")
            ).keys():
                if not [
                    True
                    for child in self._filtered_children
                    if child[2] == immediate_child
                ]:
                    self._filtered_children.append(
                        (0, "", immediate_child, search_path)
                    )

        self.is_loaded = False

    def load_children(self):
        for child_item in self._filtered_children:
            if child_item[0] > 0:  # This is a file
                self.childItems.append(
                    FileItem(
                        name=child_item[2],
                        modified=child_item[1],
                        size=child_item[0],
                        files_with_attributes=self.files_with_attributes,
                        nested_file_list=self.nested_file_list,
                        selected_files_folders=self.selected_files_folders,
                        parent=self,
                    )
                )
            else:  # Folder
                self.childItems.append(
                    FolderItem(
                        path=child_item[3],
                        name=child_item[2],
                        modified=child_item[1],
                        files_with_attributes=self.files_with_attributes,
                        nested_file_list=self.nested_file_list,
                        selected_files_folders=self.selected_files_folders,
                        parent=self,
                    )
                )
        self.is_loaded = True

    def setCheckedState(self, value):
        if value == 2:
            self.checkedState = True
            self.selected_files_folders.add(
                os.path.join(
                    self.parentItem.path, self.parentItem.data(0), self.itemData[0]
                )
            )
        else:
            self.checkedState = False
            path_to_remove = os.path.join(
                self.parentItem.path, self.parentItem.data(0), self.itemData[0]
            )
            if path_to_remove in self.selected_files_folders:
                self.selected_files_folders.remove(path_to_remove)

        if hasattr(self, "childItems"):
            for child in self.childItems:
                child.setCheckedState(value)

    def getCheckedState(self):
        if self.checkedState:
            return Qt.Checked
        else:
            return Qt.Unchecked

    def child(self, row):
        return self.childItems[row]

    def childCount(self):
        return len(self._filtered_children)

    def columnCount(self):
        return 3

    def data(self, column):
        if column <= 1:
            return self.itemData[column]
        else:
            return None

    def parent(self):
        return self.parentItem

    def row(self):
        if self.parentItem:
            return self.parentItem.childItems.index(self)

        return 0


class FileItem(FolderItem):
    def __init__(
        self,
        name,
        modified,
        size,
        files_with_attributes,
        nested_file_list,
        selected_files_folders=None,
        parent=None,
    ):
        self.parentItem = parent
        self.itemData = [name, modified, size]
        self.checkedState = parent.checkedState
        self.files_with_attributes = files_with_attributes
        self.nested_file_list = nested_file_list
        self.selected_files_folders = selected_files_folders

    def childCount(self):
        return 0

    def columnCount(self):
        return 3

    def data(self, column):
        if column == 1:
            return self.itemData[column]
        elif column == 2:
            return pretty_bytes(self.itemData[column])
        elif column == 0:
            return self.itemData[column]

    def parent(self):
        return self.parentItem

    def row(self):
        return self.parentItem.childItems.index(self)


class TreeModel(QAbstractItemModel):
    __metaclass__ = abc.ABCMeta

    column_names = ["Name", "Modified", "Size"]

    def __init__(
        self,
        files_with_attributes,
        nested_file_list,
        selected_files_folders=None,
        parent=None,
    ):
        super(TreeModel, self).__init__(parent)

        self.rootItem = FolderItem(
            path="",
            name="",
            files_with_attributes=files_with_attributes,
            nested_file_list=nested_file_list,
            selected_files_folders=selected_files_folders,
            modified=None,
        )
        self.rootItem.load_children()

    def columnCount(self, parent):
        return 3

    @abc.abstractmethod
    def data(self, index, role):
        return

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.CheckStateRole:
            item = index.internalPointer()
            item.setCheckedState(value)
            self.dataChanged.emit(QModelIndex(), QModelIndex(), [])

        return True

    def canFetchMore(self, index):
        if not index.isValid():
            return False
        item = index.internalPointer()
        return not item.is_loaded

    def fetchMore(self, index):
        item = index.internalPointer()
        item.load_children()

    @abc.abstractmethod
    def flags(self, index):
        return

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.column_names[section]

        return None

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent):
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()
