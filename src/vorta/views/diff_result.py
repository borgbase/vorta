import json
import os
import re

from PyQt5 import uic
from PyQt5.QtCore import Qt, QVariant
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QHeaderView

from vorta.utils import (get_asset, get_dict_from_list, nested_dict, uses_dark_mode)

from vorta.views.partials.tree_view import TreeModel

uifile = get_asset('UI/diffresult.ui')
DiffResultUI, DiffResultBase = uic.loadUiType(uifile)


class DiffResult(DiffResultBase, DiffResultUI):
    def __init__(self, fs_data, archive_newer, archive_older, json_lines):
        super().__init__()
        self.setupUi(self)

        if json_lines:
            # If fs_data is already a dict, then there was just a single json-line
            # and the default handler already parsed into json dict, otherwise
            # fs_data is a str, and needs to be split and parsed into json dicts
            lines = [fs_data] if isinstance(fs_data, dict) else \
                    [json.loads(line) for line in fs_data.split('\n') if line]
        else:
            lines = [line for line in fs_data.split('\n') if line]

        files_with_attributes, nested_file_list = parse_diff_json_lines(lines) \
            if json_lines else parse_diff_lines(lines)
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


def parse_diff_json_lines(diffs):
    files_with_attributes = []
    nested_file_list = nested_dict()

    for item in diffs:
        dirpath, name = os.path.split(item['path'])

        # add to nested dict of folders to find nested dirs.
        d = get_dict_from_list(nested_file_list, dirpath.split('/'))
        if name not in d:
            d[name] = {}

        # added link, removed link, changed link
        # modified (added, removed), added (size), removed (size)
        # added directory, removed directory
        # owner (old_user, new_user, old_group, new_group))
        # mode (old_mode, new_mode)
        size = 0
        change_type = None
        change_type_priority = 0
        file_type = '-'
        for change in item['changes']:
            # if more than one type of change has happened for this file/dir/link, then report the most important
            # (higher priority)
            if {'type': 'modified'} == change:
                # modified, but can't compare ids
                if change_type_priority < 3:
                    change_type = 'modified'
                    change_type_priority = 3
            elif change['type'] == 'modified':
                # only reveal 'added' to match what happens in non-json parsing - maybe update dialog to show more info.
                # size = change['added'] - change['removed']
                size = change['added']
                if change_type_priority < 3:
                    # non-json-lines mode only reports owner changes as 'modified' in the tree - maybe update dialog to
                    # show more info.
                    # change_type = '{:>9} {:>9}'.format(pretty_bytes(change['added'], precision=1, sign=True),
                    #                                    pretty_bytes(-change['removed'], precision=1, sign=True))
                    change_type = 'modified'
                    change_type_priority = 3
            elif change['type'] in ['added', 'removed', 'added link', 'removed link', 'changed link',
                                    'added directory', 'removed directory']:
                if change['type'] in ['added directory', 'removed directory']:
                    file_type = 'd'
                size = change.get('size', 0)
                if change_type_priority < 2:
                    change_type = change['type'].split()[0]     # 'added', 'removed' or 'changed'
                    change_type_priority = 2
            elif change['type'] == 'mode':
                # mode change can occur along with previous changes - don't override
                if change_type_priority < 4:
                    change_type = '[{} -> {}]'.format(change['old_mode'], change['new_mode'])
                    change_type_priority = 4
            elif change['type'] == 'owner':
                # owner change can occur along with previous changes - don't override
                if change_type_priority < 1:
                    # non-json-lines mode only reports owner changes as 'modified' in the tree - matbe update dialog to
                    # show more info.
                    # change_type = '{}:{} -> {}:{}'.format(change['old_user'], change['old_group'],
                    #                                       change['new_user'], change['new_group'])
                    change_type = 'modified'
                    change_type_priority = 1
        assert change_type  # either no changes, or unrecognized change(s)

        files_with_attributes.append((size, change_type, name, dirpath, file_type))

    return (files_with_attributes, nested_file_list)


def parse_diff_lines(diff_lines):
    nested_file_list = nested_dict()

    def parse_line(line):
        line_split = line.split()
        file_type = '-'
        if line_split[0] in {'added', 'removed', 'changed'}:
            change_type = line_split[0]
            if line_split[1] in ['directory', 'link']:
                if line_split[1] in ['directory']:
                    file_type = 'd'
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

        return size, change_type, name, dir, file_type

    files_with_attributes = [parse_line(line) for line in diff_lines if line]

    return files_with_attributes, nested_file_list


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
    def __init__(self, files_with_attributes, nested_file_list, parent=None,):
        super().__init__(
            files_with_attributes, nested_file_list, parent=parent
        )
        dark_mode = uses_dark_mode()
        self.red = QVariant(QColor(Qt.red)) if dark_mode else QVariant(QColor(Qt.darkRed))
        self.green = QVariant(QColor(Qt.green)) if dark_mode else QVariant(QColor(Qt.darkGreen))
        self.yellow = QVariant(QColor(Qt.yellow)) if dark_mode else QVariant(QColor(Qt.darkYellow))

    def data(self, index, role):
        if not index.isValid():
            return None

        item = index.internalPointer()

        if role == Qt.ForegroundRole:
            if item.itemData[1] == 'removed':
                return self.red
            elif item.itemData[1] == 'added':
                return self.green
            elif item.itemData[1] == 'modified' or item.itemData[1].startswith('['):
                return self.yellow

        if role == Qt.DisplayRole:
            return item.data(index.column())
        else:
            return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled
