from PyQt6 import uic
from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QAbstractItemView, QMessageBox

from vorta.store.models import ExclusionModel, RawExclusionModel
from vorta.utils import get_asset
from vorta.views.utils import get_colored_icon

uifile = get_asset('UI/excludedialog.ui')
ExcludeDialogUi, ExcludeDialogBase = uic.loadUiType(uifile)


class QCustomItemModel(QStandardItemModel):
    # When a user-added item in edit mode has no text, remove it from the list.
    def __init__(self, parent=None):
        super().__init__(parent)

    def setData(self, index: QModelIndex, value, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.EditRole and value == '':
            self.removeRow(index.row())
            return True
        if role == Qt.ItemDataRole.EditRole and ExclusionModel.get_or_none(ExclusionModel.name == value):
            QMessageBox.critical(
                self.parent(),
                'Error',
                'This exclusion already exists.',
            )
            self.removeRow(index.row())
            return False

        return super().setData(index, value, role)


class ExcludeDialog(ExcludeDialogBase, ExcludeDialogUi):
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.profile = profile

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

        self.exclusionsPreviewText.setReadOnly(True)
        self.rawExclusionsSaveButton.clicked.connect(self.raw_exclusions_saved)

        self.customExcludesModel.itemChanged.connect(self.item_changed)

        self.bRemovePattern.clicked.connect(self.remove_pattern)
        self.bRemovePattern.setIcon(get_colored_icon('minus'))
        self.bAddPattern.clicked.connect(self.add_pattern)
        self.bAddPattern.setIcon(get_colored_icon('plus'))

        self.populate_custom_exclusions_list()
        self.populate_raw_exclusions_text()
        self.populate_preview_tab()

    def populate_custom_exclusions_list(self):
        user_excluded_patterns = {
            e.name: e.enabled
            for e in self.profile.exclusions.select()
            .where(ExclusionModel.source == 'custom')
            .order_by(ExclusionModel.date_added.desc())
        }

        for (exclude, enabled) in user_excluded_patterns.items():
            item = QStandardItem(exclude)
            item.setCheckable(True)
            item.setCheckState(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
            self.customExcludesModel.appendRow(item)

    def populate_raw_exclusions_text(self):
        raw_excludes = RawExclusionModel.get_or_none(profile=self.profile)
        if raw_excludes:
            self.rawExclusionsText.setPlainText(raw_excludes.patterns)

    def populate_preview_tab(self):
        excludes = ""
        for exclude in ExclusionModel.select().where(
            ExclusionModel.profile == self.profile,
            ExclusionModel.enabled,
            ExclusionModel.source == 'custom',
        ):
            excludes += f"{exclude.name}\n"

        raw_excludes = RawExclusionModel.get_or_none(profile=self.profile)
        if raw_excludes:
            excludes += raw_excludes.patterns

        self.exclusionsPreviewText.setPlainText(excludes)

    def remove_pattern(self):
        indexes = self.customExclusionsList.selectedIndexes()
        for index in reversed(indexes):
            ExclusionModel.delete().where(
                ExclusionModel.name == index.data(),
                ExclusionModel.source == 'custom',
                ExclusionModel.profile == self.profile,
            ).execute()
            self.customExcludesModel.removeRow(index.row())

        self.populate_preview_tab()

    def add_pattern(self):
        '''
        Add an empty item to the list in editable mode.
        '''
        item = QStandardItem('')
        item.setCheckable(True)
        item.setCheckState(Qt.CheckState.Checked)
        self.customExclusionsList.model().appendRow(item)
        self.customExclusionsList.edit(item.index())
        self.customExclusionsList.scrollToBottom()

    def item_changed(self, item):
        '''
        When the user checks or unchecks an item, update the database.
        When the user adds a new item, add it to the database.
        '''
        if not ExclusionModel.get_or_none(name=item.text(), source='custom', profile=self.profile):
            ExclusionModel.create(name=item.text(), source='custom', profile=self.profile)

        ExclusionModel.update(enabled=item.checkState() == Qt.CheckState.Checked).where(
            ExclusionModel.name == item.text(),
            ExclusionModel.source == 'custom',
            ExclusionModel.profile == self.profile,
        ).execute()

        self.populate_preview_tab()

    def raw_exclusions_saved(self):
        '''
        When the user saves changes in the raw exclusions text box, add it to the database.
        '''
        raw_excludes = self.rawExclusionsText.toPlainText()
        raw_excludes_model = RawExclusionModel.get_or_none(profile=self.profile)
        if raw_excludes_model:
            raw_excludes_model.patterns = raw_excludes
            raw_excludes_model.save()
        else:
            RawExclusionModel.create(profile=self.profile, patterns=raw_excludes)

        self.populate_preview_tab()
