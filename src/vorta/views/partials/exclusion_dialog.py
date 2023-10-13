from PyQt6.QtCore import QModelIndex, QObject, Qt
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QMenu,
    QMessageBox,
    QStyledItemDelegate,
)

from vorta.store.models import ExclusionModel
from vorta.views.utils import get_colored_icon


class MandatoryInputItemModel(QStandardItemModel):
    '''
    A model that prevents the user from adding an empty item to the list.
    '''

    def __init__(self, parent=None, model=None):
        super().__init__(parent)
        self.model = model

    def setData(self, index: QModelIndex, value, role: int = ...) -> bool:
        # When a user-added item in edit mode has no text, remove it from the list.
        if role == Qt.ItemDataRole.EditRole and value == '':
            self.removeRow(index.row())
            return True
        if role == Qt.ItemDataRole.EditRole and ExclusionModel.get_or_none(self.model.name == value):
            QMessageBox.critical(
                self.parent(),
                'Error',
                'This exclusion already exists.',
            )
            self.removeRow(index.row())
            return False

        return super().setData(index, value, role)


class BaseExclusionDialog(QDialog):
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.profile = profile
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self.buttonBox.rejected.connect(self.close)

        self.customExclusionsModel = MandatoryInputItemModel(model=ExclusionModel)
        self.customExclusionsList.setModel(self.customExclusionsModel)
        self.customExclusionsModel.itemChanged.connect(self.custom_item_changed)
        self.customExclusionsList.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.customExclusionsList.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.customExclusionsList.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.customExclusionsList.setAlternatingRowColors(True)
        self.customExclusionsListDelegate = QStyledItemDelegate()
        self.customExclusionsList.setItemDelegate(self.customExclusionsListDelegate)
        self.customExclusionsListDelegate.closeEditor.connect(self.custom_pattern_editing_finished)
        # allow removing items with the delete key with event filter
        self.installEventFilter(self)
        # context menu
        self.customExclusionsList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customExclusionsList.customContextMenuRequested.connect(self.custom_exclusions_context_menu)

        self.exclusionsPreviewText.setReadOnly(True)

        self.rawExclusionsText.textChanged.connect(self.raw_exclusions_saved)

        self.bRemovePattern.clicked.connect(self.remove_pattern)
        self.bRemovePattern.setIcon(get_colored_icon('minus'))
        self.bPreviewCopy.clicked.connect(self.copy_preview_to_clipboard)
        self.bPreviewCopy.setIcon(get_colored_icon('copy'))
        self.bAddPattern.clicked.connect(self.add_pattern)
        self.bAddPattern.setIcon(get_colored_icon('plus'))

        self.customPresetsHelpText.setOpenExternalLinks(True)

        self.populate_custom_exclusions_list()
        self.populate_raw_exclusions_text()
        self.populate_preview_tab()

    def custom_exclusions_context_menu(self, pos):
        # index under cursor
        index = self.customExclusionsList.indexAt(pos)
        if not index.isValid():
            return

        selected_rows = self.customExclusionsList.selectedIndexes()

        if selected_rows and index not in selected_rows:
            return  # popup only for selected items

        menu = QMenu(self.customExclusionsList)
        menu.addAction(
            get_colored_icon('copy'),
            self.tr('Copy'),
            lambda: QApplication.clipboard().setText(index.data()),
        )

        # Remove and Toggle can work with multiple items selected
        menu.addAction(
            get_colored_icon('minus'),
            self.tr('Remove'),
            lambda: self.remove_pattern(index if not selected_rows else None),
        )
        menu.addAction(
            get_colored_icon('check-circle'),
            self.tr('Toggle'),
            lambda: self.toggle_custom_pattern(index if not selected_rows else None),
        )

        menu.popup(self.customExclusionsList.viewport().mapToGlobal(pos))

    def copy_preview_to_clipboard(self):
        cb = QApplication.clipboard()
        cb.clear(mode=cb.Mode.Clipboard)
        cb.setText(self.exclusionsPreviewText.toPlainText(), mode=cb.Mode.Clipboard)

    def toggle_custom_pattern(self, index=None):
        '''
        Toggle the check state of the selected item(s).
        If there is no index, this was called from the context menu and the indexes are passed in.
        '''
        if not index:
            indexes = self.customExclusionsList.selectedIndexes()
            for index in indexes:
                item = self.customExclusionsModel.itemFromIndex(index)
                if item.checkState() == Qt.CheckState.Checked:
                    item.setCheckState(Qt.CheckState.Unchecked)
                else:
                    item.setCheckState(Qt.CheckState.Checked)
        else:
            item = self.customExclusionsModel.itemFromIndex(index)
            if item.checkState() == Qt.CheckState.Checked:
                item.setCheckState(Qt.CheckState.Unchecked)
            else:
                item.setCheckState(Qt.CheckState.Checked)

    def add_pattern(self):
        '''
        Add an empty item to the list in editable mode.
        Don't add an item if the user is already editing an item.
        '''
        if self.customExclusionsList.state() == QAbstractItemView.State.EditingState:
            return
        item = QStandardItem('')
        item.setCheckable(True)
        item.setCheckState(Qt.CheckState.Checked)
        self.customExclusionsList.model().appendRow(item)
        self.customExclusionsList.edit(item.index())
        self.customExclusionsList.scrollToBottom()

    def custom_pattern_editing_finished(self, editor):
        '''
        Go through all items in the list and if any of them are empty, remove them.
        Handles the case where the user presses the escape key to cancel editing.
        '''
        for row in range(self.customExclusionsModel.rowCount()):
            item = self.customExclusionsModel.item(row)
            if item.text() == '':
                self.customExclusionsModel.removeRow(row)

    def eventFilter(self, source, event):
        '''
        When the user presses the delete key, remove the selected items.
        '''
        if event.type() == event.Type.KeyPress and event.key() == Qt.Key.Key_Delete:
            self.remove_pattern()
            return True
        return QObject.eventFilter(self, source, event)
