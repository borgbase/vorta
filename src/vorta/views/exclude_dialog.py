from PyQt6 import uic
from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QAbstractItemView,
)

from vorta.store.models import ExclusionModel
from vorta.utils import get_asset
from vorta.views.utils import get_colored_icon

uifile = get_asset('UI/excludedialog.ui')
ExcludeDialogUi, ExcludeDialogBase = uic.loadUiType(uifile)


class QCustomItemModel(QStandardItemModel):
    # When a user-added item in edit mode has no text, remove it from the list.
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.profile = profile

    def setData(self, index: QModelIndex, value, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            if value == '':
                self.removeRow(index.row())
                return True
            ExclusionModel.create(name=value, source='user', profile=self.profile)

        return super().setData(index, value, role)


class ExcludeDialog(ExcludeDialogBase, ExcludeDialogUi):
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.profile = profile
        # Complete set of all exclusions selected by the user, these are finally passed to Borg.
        self.exclusion_set = {e.name for e in self.profile.exclusions.select().where(ExclusionModel.enabled)}
        # Custom patterns added by the user to exclude.
        self.user_excluded_patterns = []

        self.customExcludesModel = QCustomItemModel(self.profile)
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

        self.populate_custom_exclusions_list()
        self.populate_raw_excludes()

    def populate_custom_exclusions_list(self):
        self.user_excluded_patterns = {
            e.name: e.enabled
            for e in self.profile.exclusions.select()
            .where(ExclusionModel.source == 'user')
            .order_by(ExclusionModel.date_added.desc())
        }

        for (exclude, enabled) in self.user_excluded_patterns.items():
            item = QStandardItem(exclude)
            item.setCheckable(True)
            item.setCheckState(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
            self.customExcludesModel.appendRow(item)

    def populate_raw_excludes(self):
        raw_excludes = ""
        for exclude in self.exclusion_set:
            raw_excludes += f"{exclude}\n"
        self.rawExclusions.setPlainText(raw_excludes)

    def remove_pattern(self):
        indexes = self.customExclusionsList.selectedIndexes()
        for index in reversed(indexes):
            self.user_excluded_patterns.pop(index.data())
            self.exclusion_set.remove(index.data())
            ExclusionModel.delete().where(
                ExclusionModel.name == index.data(),
                ExclusionModel.source == 'user',
                ExclusionModel.profile == self.profile,
            ).execute()
            self.customExcludesModel.removeRow(index.row())

    def add_pattern(self):
        '''
        Add an empty item to the list in editable mode
        '''
        item = QStandardItem('')
        item.setCheckable(True)
        item.setCheckState(Qt.CheckState.Checked)
        self.customExclusionsList.model().appendRow(item)
        self.customExclusionsList.edit(item.index())
        self.customExclusionsList.scrollToBottom()

    def item_changed(self, item):
        '''
        When the user checks or unchecks an item, add or remove it from the exclusion list.
        '''
        ExclusionModel.update(enabled=item.checkState() == Qt.CheckState.Checked).where(
            ExclusionModel.name == item.text(), ExclusionModel.source == 'user', ExclusionModel.profile == self.profile
        ).execute()

        if item.checkState() == Qt.CheckState.Checked:
            self.exclusion_set.add(item.text())
        else:
            self.exclusion_set.remove(item.text())

        self.populate_raw_excludes()
