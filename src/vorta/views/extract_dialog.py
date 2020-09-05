import sys
import os
import datetime
from collections import namedtuple

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QHeaderView

from vorta.utils import get_asset, get_dict_from_list, nested_dict
from vorta.views.partials.tree_view import TreeModel

uifile = get_asset("UI/extractdialog.ui")
ExtractDialogUI, ExtractDialogBase = uic.loadUiType(uifile)


class ExtractDialog(ExtractDialogBase, ExtractDialogUI):
    def __init__(self, fs_data, archive):
        super().__init__()
        self.setupUi(self)

        files_with_attributes = []
        nested_file_list = nested_dict()
        self.selected = set()

        def parse_line(line):
            size, modified, full_path = line.split("\t")
            size = int(size)
            dir, name = os.path.split(full_path)

            # add to nested dict of folders to find nested dirs.
            d = get_dict_from_list(nested_file_list, dir.split("/"))
            if name not in d:
                d[name] = {}

            return size, modified, name, dir

        for line in fs_data.split("\n"):
            try:
                files_with_attributes.append(parse_line(line))
            except ValueError:
                pass

        model = ExtractTree(files_with_attributes, nested_file_list, self.selected)

        view = self.treeView
        view.setAlternatingRowColors(True)
        view.setUniformRowHeights(True)  # Allows for scrolling optimizations.
        view.setModel(model)
        header = view.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        self.archiveNameLabel.setText(f"{archive.name}, {archive.time}")
        self.cancelButton.clicked.connect(self.close)
        self.extractButton.clicked.connect(self.accept)


class ExtractTree(TreeModel):
    def __init__(
        self,
        files_with_attributes,
        nested_file_list,
        selected_files_folders,
        parent=None,
    ):
        super().__init__(
            files_with_attributes, nested_file_list, selected_files_folders, parent
        )

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

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable


if __name__ == "__main__":
    """
    For local testing:

    borg list --progress --info --log-json --format="{size:8d}{TAB}{mtime}{TAB}{path}{NL}"
    """
    FakeArchive = namedtuple("Archive", ["name", "time"])
    app = QApplication(sys.argv)
    test_list = open("/Users/manu/Downloads/nyx2-list.txt").read()

    archive = FakeArchive("test-archive", datetime.datetime.now())
    view = ExtractDialog(test_list, archive)
    view.show()
    sys.exit(app.exec_())
