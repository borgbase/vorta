from PyQt6 import uic
from PyQt6.QtCore import QModelIndex, QObject, Qt
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QMenu,
    QMessageBox,
    QStyledItemDelegate,
)

from vorta.i18n import translate
from vorta.store.models import ExcludeIfPresentModel
from vorta.utils import get_asset
from vorta.views.utils import get_colored_icon

uifile = get_asset('UI/excludeifpresentdialog.ui')
ExcludeIfPresentDialogUi, ExcludeIfPresentDialogBase = uic.loadUiType(uifile)


class MandatoryInputItemModel(QStandardItemModel):
    '''
    A model that prevents the user from adding an empty item to the list.
    '''

    def __init__(self, parent=None):
        super().__init__(parent)

    def setData(self, index: QModelIndex, value, role: int = ...) -> bool:
        # When a user-added item in edit mode has no text, remove it from the list.
        if role == Qt.ItemDataRole.EditRole and value == '':
            self.removeRow(index.row())
            return True
        if role == Qt.ItemDataRole.EditRole and ExcludeIfPresentModel.get_or_none(ExcludeIfPresentModel.name == value):
            QMessageBox.critical(
                self.parent(),
                'Error',
                'This exclusion already exists.',
            )
            self.removeRow(index.row())
            return False

        return super().setData(index, value, role)


class ExcludeIfPresentDialog(ExcludeIfPresentDialogBase, ExcludeIfPresentDialogUi):
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.profile = profile
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self.buttonBox.rejected.connect(self.close)

        self.customExclusionsModel = MandatoryInputItemModel()
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

        # help text
        self.customPresetsHelpText.setOpenExternalLinks(True)
        self.customPresetsHelpText.setText(
            translate(
                "CustomPresetsHelp",
                "You can add names of filesystem objects (e.g. a file or folder name) which, when contained within another folder, will prevent the containing folder from being backed up. This option will exclude a directory if a specific file or folder is present in that directory. For more info, see the <a href=\"https://borgbackup.readthedocs.io/en/stable/usage/create.html\">documentation</a>. To add multiple names at once, use the \"Raw\" tab.",  # noqa: E501
            )
        )
        self.rawExclusionsHelpText.setText(
            translate(
                "RawExclusionsHelp",
                "You can use this field to add multiple names at once. Each name should be on a separate line. You can also add comments with #, which will be ignored when the list is parsed.",  # noqa: E501
            )
        )
        self.exclusionsPreviewHelpText.setText(
            translate(
                "ExclusionsPreviewHelp",
                "This is a preview of all the names which will be passed to Borg's --exclude-if-present option.",  # noqa: E501
            )
        )

        self.populate_custom_exclusions_list()
        self.populate_raw_exclusions_text()
        self.populate_preview_tab()

    def populate_custom_exclusions_list(self):
        user_excluded_patterns = {
            e.name: e.enabled
            for e in self.profile.exclude_if_present_patterns.select().order_by(ExcludeIfPresentModel.name)
        }

        for (exclude, enabled) in user_excluded_patterns.items():
            item = QStandardItem(exclude)
            item.setCheckable(True)
            item.setCheckState(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
            self.customExclusionsModel.appendRow(item)

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

    def populate_raw_exclusions_text(self):
        raw_excludes = self.profile.raw_exclude_if_present
        if raw_excludes:
            self.rawExclusionsText.setPlainText(raw_excludes)

    def populate_preview_tab(self):
        excludes = ""

        if (
            ExcludeIfPresentModel.select()
            .where(
                ExcludeIfPresentModel.profile == self.profile,
                ExcludeIfPresentModel.enabled,
            )
            .count()
            > 0
        ):
            excludes = "# custom added rules\n"

        for exclude in ExcludeIfPresentModel.select().where(
            ExcludeIfPresentModel.profile == self.profile,
            ExcludeIfPresentModel.enabled,
        ):
            excludes += f"{exclude.name}\n"

        # add a newline if there are custom exclusions
        if excludes:
            excludes += "\n"

        raw_excludes = self.profile.raw_exclude_if_present
        if raw_excludes:
            excludes += "# raw exclusions\n"
            excludes += raw_excludes
            excludes += "\n"

        self.exclusionsPreviewText.setPlainText(excludes)
        self.profile.exclude_if_present = excludes
        self.profile.save()

    def copy_preview_to_clipboard(self):
        cb = QApplication.clipboard()
        cb.clear(mode=cb.Mode.Clipboard)
        cb.setText(self.exclusionsPreviewText.toPlainText(), mode=cb.Mode.Clipboard)

    def remove_pattern(self, index=None):
        '''
        Remove the selected item(s) from the list and the database.
        If there is no index, this was called from the context menu and the indexes are passed in.
        '''
        if not index:
            indexes = self.customExclusionsList.selectedIndexes()
            for index in reversed(sorted(indexes)):
                ExcludeIfPresentModel.delete().where(
                    ExcludeIfPresentModel.name == index.data(),
                    ExcludeIfPresentModel.profile == self.profile,
                ).execute()
                self.customExclusionsModel.removeRow(index.row())
        else:
            ExcludeIfPresentModel.delete().where(
                ExcludeIfPresentModel.name == index.data(),
                ExcludeIfPresentModel.profile == self.profile,
            ).execute()
            self.customExclusionsModel.removeRow(index.row())

        self.populate_preview_tab()

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

    def custom_item_changed(self, item):
        '''
        When the user checks or unchecks an item, update the database.
        When the user adds a new item, add it to the database.
        '''
        if not ExcludeIfPresentModel.get_or_none(name=item.text(), profile=self.profile):
            ExcludeIfPresentModel.create(name=item.text(), profile=self.profile)

        ExcludeIfPresentModel.update(enabled=item.checkState() == Qt.CheckState.Checked).where(
            ExcludeIfPresentModel.name == item.text(),
            ExcludeIfPresentModel.profile == self.profile,
        ).execute()

        self.populate_preview_tab()

    def raw_exclusions_saved(self):
        '''
        When the user saves changes in the raw exclusions text box, add it to the database.
        '''
        raw_excludes = self.rawExclusionsText.toPlainText()
        self.profile.raw_exclude_if_present = raw_excludes
        self.profile.save()

        self.populate_preview_tab()

    def eventFilter(self, source, event):
        '''
        When the user presses the delete key, remove the selected items.
        '''
        if event.type() == event.Type.KeyPress and event.key() == Qt.Key.Key_Delete:
            self.remove_pattern()
            return True
        return QObject.eventFilter(self, source, event)
