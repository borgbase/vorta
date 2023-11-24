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
from vorta.store.models import ExclusionModel
from vorta.utils import get_asset
from vorta.views.utils import get_colored_icon, get_exclusion_presets

uifile = get_asset('UI/excludedialog.ui')
ExcludeDialogUi, ExcludeDialogBase = uic.loadUiType(uifile)


class MandatoryInputItemModel(QStandardItemModel):
    '''
    A model that prevents the user from adding an empty item to the list.
    '''

    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.profile = profile

    def setData(self, index: QModelIndex, value, role: int = ...) -> bool:
        # When a user-added item in edit mode has no text, remove it from the list.
        if role == Qt.ItemDataRole.EditRole and value == '':
            self.removeRow(index.row())
            return True
        if role == Qt.ItemDataRole.EditRole and ExclusionModel.get_or_none(name=value, profile=self.profile):
            self.removeRow(index.row())
            QMessageBox.critical(
                self.parent(),
                'Error',
                'This exclusion already exists.',
            )
            return False

        return super().setData(index, value, role)


class ExcludeDialog(ExcludeDialogBase, ExcludeDialogUi):
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.profile = profile

        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.allPresets = get_exclusion_presets()
        self.buttonBox.rejected.connect(self.close)

        self.customExclusionsModel = MandatoryInputItemModel(profile=profile)
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

        self.exclusionPresetsModel = QStandardItemModel()
        self.exclusionPresetsList.setModel(self.exclusionPresetsModel)
        self.exclusionPresetsModel.itemChanged.connect(self.preset_item_changed)
        self.exclusionPresetsList.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.exclusionPresetsList.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.exclusionPresetsList.setAlternatingRowColors(True)

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
                "Patterns that you add here will be used to exclude files and folders from the backup. For more info on how to use patterns, see the <a href=\"https://borgbackup.readthedocs.io/en/stable/usage/help.html#borg-patterns\">documentation</a>. To add multiple patterns at once, use the \"Raw\" tab.",  # noqa: E501
            )
        )
        self.exclusionPresetsHelpText.setText(
            translate(
                "ExclusionPresetsHelp",
                "These presets are provided by the community and are a good starting point for excluding certain types of files. You can enable or disable them as you see fit. To see the patterns that are used for each preset, switch to the \"Preview\" tab after enabling it.",  # noqa: E501
            )
        )
        self.rawExclusionsHelpText.setText(
            translate(
                "RawExclusionsHelp",
                "You can use this field to add multiple patterns at once. Each pattern should be on a separate line.",
            )
        )
        self.exclusionsPreviewHelpText.setText(
            translate(
                "ExclusionsPreviewHelp",
                "This is a preview of the patterns that will be used to exclude files and folders from the backup.",
            )
        )

        self.populate_custom_exclusions_list()
        self.populate_presets_list()
        self.populate_raw_exclusions_text()
        self.populate_preview_tab()

    def populate_custom_exclusions_list(self):
        user_excluded_patterns = {
            e.name: e.enabled
            for e in self.profile.exclusions.select()
            .where(ExclusionModel.source == ExclusionModel.SourceFieldOptions.CUSTOM.value)
            .order_by(ExclusionModel.name)
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

    def populate_presets_list(self):
        for preset_slug in self.allPresets.keys():
            item = QStandardItem(self.allPresets[preset_slug]['name'])
            item.setCheckable(True)
            item.setData(preset_slug, Qt.ItemDataRole.UserRole)
            preset_model = ExclusionModel.get_or_none(
                name=preset_slug,
                source=ExclusionModel.SourceFieldOptions.PRESET.value,
                profile=self.profile,
            )

            if preset_model:
                item.setCheckState(Qt.CheckState.Checked if preset_model.enabled else Qt.CheckState.Unchecked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)

            self.exclusionPresetsModel.appendRow(item)

    def populate_raw_exclusions_text(self):
        raw_excludes = self.profile.exclude_patterns
        if raw_excludes:
            self.rawExclusionsText.setPlainText(raw_excludes)

    def populate_preview_tab(self):
        excludes = self.profile.get_combined_exclusion_string()
        self.exclusionsPreviewText.setPlainText(excludes)

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
                ExclusionModel.delete().where(
                    ExclusionModel.name == index.data(),
                    ExclusionModel.source == ExclusionModel.SourceFieldOptions.CUSTOM.value,
                    ExclusionModel.profile == self.profile,
                ).execute()
                self.customExclusionsModel.removeRow(index.row())
        else:
            ExclusionModel.delete().where(
                ExclusionModel.name == index.data(),
                ExclusionModel.source == ExclusionModel.SourceFieldOptions.CUSTOM.value,
                ExclusionModel.profile == self.profile,
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
        if not ExclusionModel.get_or_none(
            name=item.text(), source=ExclusionModel.SourceFieldOptions.CUSTOM.value, profile=self.profile
        ):
            ExclusionModel.create(
                name=item.text(), source=ExclusionModel.SourceFieldOptions.CUSTOM.value, profile=self.profile
            )

        ExclusionModel.update(enabled=item.checkState() == Qt.CheckState.Checked).where(
            ExclusionModel.name == item.text(),
            ExclusionModel.source == ExclusionModel.SourceFieldOptions.CUSTOM.value,
            ExclusionModel.profile == self.profile,
        ).execute()

        self.populate_preview_tab()

    def preset_item_changed(self, item):
        '''
        Create or update the preset in the database.
        If the user unchecks the preset, set enabled to False, otherwise set it to True.
        If the preset doesn't exist, create it and set enabled to True.
        '''
        preset = ExclusionModel.get_or_none(
            name=item.data(Qt.ItemDataRole.UserRole),
            source=ExclusionModel.SourceFieldOptions.PRESET.value,
            profile=self.profile,
        )
        if preset:
            preset.enabled = item.checkState() == Qt.CheckState.Checked
            preset.save()
        else:
            ExclusionModel.create(
                name=item.data(Qt.ItemDataRole.UserRole),
                source=ExclusionModel.SourceFieldOptions.PRESET.value,
                profile=self.profile,
                enabled=item.checkState() == Qt.CheckState.Checked,
            )

        self.populate_preview_tab()

    def raw_exclusions_saved(self):
        '''
        When the user saves changes in the raw exclusions text box, add it to the database.
        '''
        raw_excludes = self.rawExclusionsText.toPlainText()
        self.profile.exclude_patterns = raw_excludes
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
