import json
import os
from datetime import datetime

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHeaderView

from vorta.utils import get_asset, get_dict_from_list, nested_dict
from vorta.views.partials.tree_view import TreeModel

uifile = get_asset("UI/extractdialog.ui")
ExtractDialogUI, ExtractDialogBase = uic.loadUiType(uifile)


class ExtractDialog(ExtractDialogBase, ExtractDialogUI):
    def __init__(self, fs_data, archive):
        super().__init__()
        self.setupUi(self)

        nested_file_list = nested_dict()
        self.selected = set()

        def parse_json_line(data):
            size = data["size"]
            # python >= 3.7
            # modified = datetime.fromisoformat(data["mtime"]).ctime()
            # python < 3.7
            try:
                modified = datetime.strptime(data["mtime"], "%Y-%m-%dT%H:%M:%S.%f").ctime()
            except ValueError:
                modified = datetime.strptime(data["mtime"], "%Y-%m-%dT%H:%M:%S").ctime()
            dirpath, name = os.path.split(data["path"])
            # add to nested dict of folders to find nested dirs.
            d = get_dict_from_list(nested_file_list, dirpath.split("/"))
            if name not in d:
                d[name] = {}
            return size, modified, name, dirpath, data["type"]

        # handle case of a single line of result, which will already be a dict
        lines = [fs_data] if isinstance(fs_data, dict) else \
            [json.loads(line) for line in fs_data.split('\n') if line]

        files_with_attributes = [parse_json_line(line) for line in lines]

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
