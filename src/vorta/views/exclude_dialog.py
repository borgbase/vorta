import json
import os
import sys

from PyQt6 import uic
from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QMessageBox,
)

from vorta.store.models import ExclusionModel
from vorta.utils import get_asset
from vorta.views.utils import get_colored_icon

uifile = get_asset('UI/excludedialog.ui')
ExcludeDialogUi, ExcludeDialogBase = uic.loadUiType(uifile)


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
        self.allPresets = {}

        self.customExclusionsModel = MandatoryInputItemModel()
        self.customExclusionsList.setModel(self.customExclusionsModel)
        self.customExclusionsModel.itemChanged.connect(self.custom_item_changed)
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

        self.exclusionPresetsModel = QStandardItemModel()
        self.exclusionPresetsList.setModel(self.exclusionPresetsModel)
        self.exclusionPresetsModel.itemChanged.connect(self.preset_item_changed)
        self.exclusionPresetsList.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.exclusionPresetsList.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.exclusionPresetsList.setAlternatingRowColors(True)
        self.exclusionPresetsList.setStyleSheet(
            '''
            QListView::item {
                padding: 20px 0px;
                border-bottom: .5px solid black;
            }
            QListView::item:selected {
                background-color: palette(highlight);
            }
            QListView::item::icon {
                padding-right: 10px;
            }
        '''
        )

        self.exclusionsPreviewText.setReadOnly(True)

        self.rawExclusionsSaveButton.clicked.connect(self.raw_exclusions_saved)

        self.bRemovePattern.clicked.connect(self.remove_pattern)
        self.bRemovePattern.setIcon(get_colored_icon('minus'))
        self.bAddPattern.clicked.connect(self.add_pattern)
        self.bAddPattern.setIcon(get_colored_icon('plus'))

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

    def populate_presets_list(self):
        if getattr(sys, 'frozen', False):
            # we are running in a bundle
            bundle_dir = os.path.join(sys._MEIPASS, 'assets/exclusion_presets')
        else:
            # we are running in a normal Python environment
            bundle_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../assets/exclusion_presets')

        for preset_file in os.listdir(bundle_dir):
            with open(os.path.join(bundle_dir, preset_file), 'r') as f:
                preset_data = json.load(f)
                for preset in preset_data:
                    item = QStandardItem(preset['name'])
                    item.setCheckable(True)
                    preset_model = ExclusionModel.get_or_none(
                        name=preset['name'],
                        source=ExclusionModel.SourceFieldOptions.PRESET.value,
                        profile=self.profile,
                    )

                    if preset_model:
                        item.setCheckState(Qt.CheckState.Checked if preset_model.enabled else Qt.CheckState.Unchecked)
                    else:
                        item.setCheckState(Qt.CheckState.Unchecked)

                    self.exclusionPresetsModel.appendRow(item)
                    self.allPresets[preset['name']] = {
                        'patterns': preset['patterns'],
                        'tags': preset['tags'],
                    }

    def populate_raw_exclusions_text(self):
        raw_excludes = self.profile.raw_exclusions
        if raw_excludes:
            self.rawExclusionsText.setPlainText(raw_excludes)

    def populate_preview_tab(self):
        excludes = ""

        if (
            ExclusionModel.select()
            .where(
                ExclusionModel.profile == self.profile,
                ExclusionModel.enabled,
                ExclusionModel.source == ExclusionModel.SourceFieldOptions.CUSTOM.value,
            )
            .count()
            > 0
        ):
            excludes = "# custom added rules\n"

        for exclude in ExclusionModel.select().where(
            ExclusionModel.profile == self.profile,
            ExclusionModel.enabled,
            ExclusionModel.source == ExclusionModel.SourceFieldOptions.CUSTOM.value,
        ):
            excludes += f"{exclude.name}\n"

        raw_excludes = self.profile.raw_exclusions
        if raw_excludes:
            excludes += "\n# raw exclusions\n"
            excludes += raw_excludes
            excludes += "\n"

        # go through all source=='preset' exclusions, find the name in the allPresets dict, and add the patterns
        for exclude in ExclusionModel.select().where(
            ExclusionModel.profile == self.profile,
            ExclusionModel.enabled,
            ExclusionModel.source == ExclusionModel.SourceFieldOptions.PRESET.value,
        ):
            excludes += f"\n#{exclude.name}\n"
            for pattern in self.allPresets[exclude.name]['patterns']:
                excludes += f"{pattern}\n"

        self.exclusionsPreviewText.setPlainText(excludes)

    def remove_pattern(self):
        indexes = self.customExclusionsList.selectedIndexes()
        for index in reversed(indexes):
            ExclusionModel.delete().where(
                ExclusionModel.name == index.data(),
                ExclusionModel.source == ExclusionModel.SourceFieldOptions.CUSTOM.value,
                ExclusionModel.profile == self.profile,
            ).execute()
            self.customExclusionsModel.removeRow(index.row())

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
            name=item.text(),
            source=ExclusionModel.SourceFieldOptions.PRESET.value,
            profile=self.profile,
        )
        if preset:
            preset.enabled = item.checkState() == Qt.CheckState.Checked
            preset.save()
        else:
            ExclusionModel.create(
                name=item.text(),
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
        self.profile.raw_exclusions = raw_excludes
        self.profile.save()

        self.populate_preview_tab()
