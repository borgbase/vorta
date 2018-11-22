from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTreeWidgetItem, QHeaderView

from ..utils import get_asset

uifile = get_asset('UI/extractdialog.ui')
ExtractDialogUI, ExtractDialogBase = uic.loadUiType(uifile)
n = 0

class ExtractDialog(ExtractDialogBase, ExtractDialogUI):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        d = {'key1': 'value1',
             'key2': ['value2', 'value', 'value4'],
             'key5': {'another key1': 'another value1',
                      'another key2': ['value2', 'value', 'value4']}
             }

        # add some nested folders
        for i in range(6, 200):
            d[f'folder-{i}'] = {'another key1': 'another value1',
                                'another key2': ['value2', 'value', 'value4']}
            for j in range(50):
                d[f'folder-{i}'][f'large folder {j}'] = {'another key1': 'another value1',
                                                        'another key2': ['value2', 'value', 'value4']}

        # add top-level folders to test scroll performance
        for f in range(1000000):
            d[f'flat folder {f}'] = 'no subfolders. test'

        self.d = d

        t = self.fileTree
        t.setColumnCount(2)
        t.setHeaderLabels(['File/Foldername', 'Size', 'Modified'])
        t.setAlternatingRowColors(True)
        t.setUniformRowHeights(True)  # Allows for scrolling optimizations.
        header = t.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        self.extractButton.clicked.connect(self.build_tree)

    def build_tree(self):
        fill_item(self.fileTree.invisibleRootItem(), self.d)
        print('Added test items', n)

def fill_item(item, value):
    global n
    # item.setExpanded(True)
    if type(value) is dict:
        for key, val in sorted(value.items()):
            child = QTreeWidgetItem()
            child.setText(0, str(key))
            child.setText(1, str(key))
            child.setText(2, str(key))
            child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
            child.setCheckState(0, Qt.Unchecked)
            item.addChild(child)
            n+=1
            fill_item(child, val)
    elif type(value) is list:
        for val in value:
            child = QTreeWidgetItem()
            child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
            child.setCheckState(0, Qt.Unchecked)
            item.addChild(child)
            n+=1
            if type(val) is dict:
                child.setText(0, '[dict]')
                fill_item(child, val)
            elif type(val) is list:
                child.setText(0, '[list]')
                fill_item(child, val)
            else:
                child.setText(0, str(val))
    else:
        child = QTreeWidgetItem()
        child.setText(0, str(value))
        child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
        child.setCheckState(0, Qt.Unchecked)
        item.addChild(child)
        n+=1

