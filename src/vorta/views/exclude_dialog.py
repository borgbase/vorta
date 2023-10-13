import json
import os
import sys

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QAbstractItemView

from vorta.i18n import translate
from vorta.store.models import ExclusionModel
from vorta.utils import get_asset
from vorta.views.partials.exclusion_dialog import BaseExclusionDialog

uifile = get_asset('UI/excludedialog.ui')
ExcludeDialogUi, ExcludeDialogBase = uic.loadUiType(uifile)


class ExcludeDialog(BaseExclusionDialog, ExcludeDialogBase, ExcludeDialogUi):
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        self.allPresets = {}

        self.exclusionPresetsModel = QStandardItemModel()
        self.exclusionPresetsList.setModel(self.exclusionPresetsModel)
        self.exclusionPresetsModel.itemChanged.connect(self.preset_item_changed)
        self.exclusionPresetsList.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.exclusionPresetsList.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.exclusionPresetsList.setAlternatingRowColors(True)

        self.exclusionsPreviewText.setReadOnly(True)

        # help text
        self.customPresetsHelpText.setText(
            translate(
                "CustomPresetsHelp",
                "Patterns that you add here will be used to exclude files and folders from the backup. For more info on how to use patterns, see the <a href=\"https://borgbackup.readthedocs.io/en/stable/usage/help.html#borg-patterns\">documentation</a>. To add multiple patterns at once, use the \"Raw\" tab.",  # noqa: E501
            )
        )
        self.exclusionPresetsHelpText.setText(
            translate(
                "ExclusionPresetsHelp",
                "These presets are provided by the community and are a good starting point for excluding certain types of files. You can enable or disable them as you see fit. To see the patterns that comprise a preset, switch to the \"Preview\" tab after enabling it.",  # noqa: E501
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
                "This is a preview of the patterns that will be passed to borg for excluding files and folders from the backup.",  # noqa: E501
            )
        )

        self.populate_presets_list()

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

        for preset_file in sorted(os.listdir(bundle_dir)):
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

        # add a newline if there are custom exclusions
        if excludes:
            excludes += "\n"

        raw_excludes = self.profile.raw_exclusions
        if raw_excludes:
            excludes += "# raw exclusions\n"
            excludes += raw_excludes
            excludes += "\n"

        # go through all source=='preset' exclusions, find the name in the allPresets dict, and add the patterns
        for exclude in ExclusionModel.select().where(
            ExclusionModel.profile == self.profile,
            ExclusionModel.enabled,
            ExclusionModel.source == ExclusionModel.SourceFieldOptions.PRESET.value,
        ):
            excludes += f"\n# {exclude.name}\n"
            for pattern in self.allPresets[exclude.name]['patterns']:
                excludes += f"{pattern}\n"

        self.exclusionsPreviewText.setPlainText(excludes)
        self.profile.exclude_patterns = excludes
        self.profile.save()

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
