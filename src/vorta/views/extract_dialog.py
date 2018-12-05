import sys
import os
import datetime
from collections import namedtuple

from PyQt5 import uic
from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt
from PyQt5.QtWidgets import QApplication, QHeaderView

from vorta.utils import get_asset, pretty_bytes, get_dict_from_list, nested_dict

uifile = get_asset('UI/extractdialog.ui')
ExtractDialogUI, ExtractDialogBase = uic.loadUiType(uifile)
ISO_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'

files_with_attributes = []
nested_file_list = nested_dict()
selected_files_folders = set()


class ExtractDialog(ExtractDialogBase, ExtractDialogUI):
    def __init__(self, fs_data, archive):
        super().__init__()
        self.setupUi(self)
        global files_with_attributes, nested_file_list, selected_files_folders

        def parse_line(line):
            size, modified, full_path = line.split('\t')
            size = int(size)
            dir, name = os.path.split(full_path)

            # add to nested dict of folders to find nested dirs.
            d = get_dict_from_list(nested_file_list, dir.split('/'))
            if name not in d:
                d[name] = {}

            return size, modified, name, dir

        files_with_attributes = [parse_line(l) for l in fs_data.split('\n')[:-1]]

        model = TreeModel()

        view = self.treeView
        view.setAlternatingRowColors(True)
        view.setUniformRowHeights(True)  # Allows for scrolling optimizations.
        view.setModel(model)
        header = view.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        self.archiveNameLabel.setText(f'{archive.name}, {archive.time}')
        self.cancelButton.clicked.connect(self.close)
        self.extractButton.clicked.connect(self.accept)
        self.selected = selected_files_folders


class FolderItem:
    def __init__(self, path, name, modified, parent=None):
        self.parentItem = parent
        self.path = path
        self.itemData = [name, modified]
        self.childItems = []
        self.checkedState = False

        # Pre-filter children
        self._filtered_children = []
        search_path = os.path.join(self.path, name)
        if parent is None:  # Find path for root folder
            for root_folder in nested_file_list.keys():
                self._filtered_children.append((0, '', root_folder, '', ))
        else:
            self.checkedState = parent.checkedState  # If there is a parent, use its checked-status.

            # This adds direct children.
            self._filtered_children = [f for f in files_with_attributes if search_path == f[3]]

            # Add nested folders.
            for immediate_child in get_dict_from_list(nested_file_list, search_path.split('/')).keys():
                if not [True for child in self._filtered_children if child[2] == immediate_child]:
                    self._filtered_children.append((0, '', immediate_child, search_path))

        self.is_loaded = False

    def load_children(self):
        for child_item in self._filtered_children:
            if child_item[0] > 0:  # This is a file
                self.childItems.append(FileItem(
                    name=child_item[2],
                    modified=child_item[1],
                    size=child_item[0],
                    parent=self))
            else:  # Folder
                self.childItems.append(
                    FolderItem(
                        path=child_item[3],
                        name=child_item[2],
                        modified=child_item[1],
                        parent=self))

        self.is_loaded = True

    def setCheckedState(self, value):
        if value == 2:
            self.checkedState = True
            selected_files_folders.add(
                os.path.join(self.parentItem.path, self.parentItem.data(0), self.itemData[0]))
        else:
            self.checkedState = False
            path_to_remove = os.path.join(self.parentItem.path, self.parentItem.data(0), self.itemData[0])
            if path_to_remove in selected_files_folders:
                selected_files_folders.remove(path_to_remove)

        if hasattr(self, 'childItems'):
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
    def __init__(self, name, modified, size, parent=None):
        self.parentItem = parent
        self.itemData = [name, modified, size]  # dt.strptime(modified, ISO_FORMAT)
        self.checkedState = parent.checkedState

    def childCount(self):
        return 0

    def columnCount(self):
        return 3

    def data(self, column):
        if column == 1:
            return self.itemData[column]  # .strftime('%Y-%m-%dT%H:%M')
        elif column == 2:
            return pretty_bytes(self.itemData[column])
        elif column == 0:
            return self.itemData[column]

    def parent(self):
        return self.parentItem

    def row(self):
        return self.parentItem.childItems.index(self)


class TreeModel(QAbstractItemModel):
    column_names = ['Name', 'Modified', 'Size']

    def __init__(self, parent=None):
        super(TreeModel, self).__init__(parent)

        self.rootItem = FolderItem(path='', name='', modified=None)
        self.rootItem.load_children()

    def columnCount(self, parent):
        return 3

    def data(self, index, role):
        if not index.isValid():
            return None

        item = index.internalPointer()

        if role == Qt.DisplayRole:
            return item.data(index.column())
        elif role == Qt.CheckStateRole and index.column() == 0:
            return item.getCheckedState()
        else:
            return None

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

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable

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


if __name__ == '__main__':
    """
    For local testing:

    borg list --progress --info --log-json --format="{size:8d}{TAB}{mtime}{TAB}{path}{NL}"
    """
    FakeArchive = namedtuple('Archive', ['name', 'time'])
    app = QApplication(sys.argv)
    test_list = open('/Users/manu/Downloads/nyx2-list.txt').read()

    archive = FakeArchive('test-archive', datetime.datetime.now())
    view = ExtractDialog(test_list, archive)
    view.show()
    sys.exit(app.exec_())
