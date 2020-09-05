import os
import re

from PyQt5 import uic
from PyQt5.QtCore import Qt, QVariant
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QHeaderView

from vorta.utils import (get_asset, get_dict_from_list, nested_dict)

from vorta.views.partials.tree_view import TreeModel

uifile = get_asset('UI/diffresult.ui')
DiffResultUI, DiffResultBase = uic.loadUiType(uifile)


class DiffResult(DiffResultBase, DiffResultUI):
    def __init__(self, fs_data, archive_newer, archive_older):
        super().__init__()
        self.setupUi(self)

        files_with_attributes, nested_file_list = parse_diff_lines(fs_data.split('\n'))
        model = DiffTree(files_with_attributes, nested_file_list)

        view = self.treeView
        view.setAlternatingRowColors(True)
        view.setUniformRowHeights(True)  # Allows for scrolling optimizations.
        view.setModel(model)
        header = view.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        self.archiveNameLabel_1.setText(f'{archive_newer.name}')
        self.archiveNameLabel_2.setText(f'{archive_older.name}')
        self.okButton.clicked.connect(self.accept)


def parse_diff_lines(diff_lines):
    files_with_attributes = []
    nested_file_list = nested_dict()

    def parse_line(line):
        if line:
            line_split = line.split()
        else:
            return 0, "", "", ""

        if line_split[0] in {'added', 'removed', 'changed'}:
            change_type = line_split[0]
            if line_split[1] in ['directory', 'link']:
                size = 0
                full_path = re.search(r'^\w+ \w+ +(.*)', line).group(1)
            else:
                significand = line_split[1]
                unit = line_split[2]
                size = calc_size(significand, unit)
                full_path = re.search(r'^\w+ +\S+ \w?B (.*)', line).group(1)
        else:
            size_change = re.search(r' *[\+-]?(\d+\.*\d*) (\w?B) +[\+-]?.+\w?B ', line)
            if size_change:
                significand = size_change.group(1)
                unit = size_change.group(2)
                size = calc_size(significand, unit)
                rest_of_line = line[size_change.end(0):]
            else:
                size = 0
                rest_of_line = line

            owner_change = re.search(r' *(\[[^:]+:[^\]]+ -> [^:]+:[^\]]+\]) ', rest_of_line)
            if owner_change:
                rest_of_line = rest_of_line[owner_change.end(0):]

            permission_change = re.search(r' *(\[.{24}\]) ', rest_of_line)
            if permission_change:
                change_type = permission_change.group(1)
                rest_of_line = rest_of_line[permission_change.end(0):]
            else:
                change_type = "modified"

            full_path = rest_of_line.lstrip(' ')

        dir, name = os.path.split(full_path)

        # add to nested dict of folders to find nested dirs.
        d = get_dict_from_list(nested_file_list, dir.split('/'))
        if name not in d:
            d[name] = {}

        return size, change_type, name, dir

    for line in diff_lines:
        files_with_attributes.append(parse_line(line))

    return (files_with_attributes, nested_file_list)


def calc_size(significand, unit):
    if unit == 'B':
        return int(significand)
    elif unit == 'kB':
        return int(float(significand) * 10**3)
    elif unit == 'MB':
        return int(float(significand) * 10**6)
    elif unit == 'GB':
        return int(float(significand) * 10**9)
    elif unit == 'TB':
        return int(float(significand) * 10**12)


class DiffTree(TreeModel):
    def __init__(
        self,
        files_with_attributes,
        nested_file_list,
        parent=None,
    ):
        super().__init__(
            files_with_attributes, nested_file_list, parent=parent
        )

    def data(self, index, role):
        if not index.isValid():
            return None

        item = index.internalPointer()

        if role == Qt.ForegroundRole:
            if item.itemData[1] == 'removed':
                return QVariant(QColor(Qt.red))
            elif item.itemData[1] == 'added':
                return QVariant(QColor(Qt.green))
            elif item.itemData[1] == 'modified' or item.itemData[1].startswith('['):
                return QVariant(QColor(Qt.darkYellow))

        if role == Qt.DisplayRole:
            return item.data(index.column())
        else:
            return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled
