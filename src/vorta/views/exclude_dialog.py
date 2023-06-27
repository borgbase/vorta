from PyQt6 import uic
from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QAbstractItemView,
)

from vorta.utils import get_asset
from vorta.views.utils import get_colored_icon

uifile = get_asset('UI/excludedialog.ui')
ExcludeDialogUi, ExcludeDialogBase = uic.loadUiType(uifile)


class QCustomItemModel(QStandardItemModel):
    # When a user-added item in edit mode has no text, remove it from the list.
    def setData(self, index: QModelIndex, value, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.EditRole and value == '':
            self.removeRow(index.row())
            return True
        return super().setData(index, value, role)


class ExcludeDialog(ExcludeDialogBase, ExcludeDialogUi):
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.profile = profile
        self.setWindowTitle(self.tr('Add patterns to exclude'))

        self.customExcludesModel = QCustomItemModel()
        self.customExclusionsList.setModel(self.customExcludesModel)
        self.customExclusionsList.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.customExclusionsList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.customExclusionsList.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.customExclusionsList.setAlternatingRowColors(True)
        self.customExclusionsList.setStyleSheet(
            '''
            QListView::item {
                padding: 20px 0px;
                border-bottom: .5px solid black;
            }
            QListView::item:selected {
                background-color: palette(highlight);
            }

        '''
        )

        self.customExcludesModel.itemChanged.connect(self.item_changed)

        self.bRemovePattern.clicked.connect(self.remove_pattern)
        self.bRemovePattern.setIcon(get_colored_icon('minus'))
        self.bAddPattern.clicked.connect(self.add_pattern)
        self.bAddPattern.setIcon(get_colored_icon('plus'))

        self.exclusion_list = set()
        self.user_excluded_patterns = set()

        # Complete set of all exclusions selected by the user.
        self.exclusion_list = {
            "./.DS_Store": None,
            "./.Spotlight-V100": None,
            "./.Trashes": None,
            "./.fseventsd": None,
            "./.TemporaryItems": None,
        }
        # Custom patterns added by the user to exclude.
        self.user_excluded_patterns = {
            "./.DS_Store": None,
            "./.TemporaryItems": None,
            "node_modules": None,
            "env": None,
        }

        self.poupulate_custom_excludes()

    def poupulate_custom_excludes(self):
        for exclude in self.user_excluded_patterns:
            item = QStandardItem(exclude)
            item.setCheckable(True)
            item.setCheckState(Qt.CheckState.Checked if exclude in self.exclusion_list else Qt.CheckState.Unchecked)

            self.customExcludesModel.appendRow(item)

    def remove_pattern(self):
        indexes = self.customExclusionsList.selectedIndexes()
        for index in reversed(indexes):
            self.user_excluded_patterns.pop(index.data())
            self.customExclusionsList.model().removeRow(index.row())

    def add_pattern(self):
        '''
        Add an empty item to the list in editable mode
        '''
        item = QStandardItem('')
        item.setCheckable(True)
        item.setCheckState(Qt.CheckState.Checked)
        self.customExclusionsList.model().appendRow(item)
        self.customExclusionsList.edit(item.index())

    def item_changed(self, item):
        '''
        When the user checks or unchecks an item, add or remove it from the exclusion list.
        '''
        if item.checkState() == Qt.CheckState.Checked:
            self.exclusion_list[item.text()] = None
        else:
            self.exclusion_list.pop(item.text(), None)
