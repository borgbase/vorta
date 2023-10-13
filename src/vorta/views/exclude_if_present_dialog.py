from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QStandardItem

from vorta.i18n import translate
from vorta.store.models import ExcludeIfPresentModel
from vorta.utils import get_asset
from vorta.views.partials.exclusion_dialog import BaseExclusionDialog

uifile = get_asset('UI/excludeifpresentdialog.ui')
ExcludeIfPresentDialogUi, ExcludeIfPresentDialogBase = uic.loadUiType(uifile)


class ExcludeIfPresentDialog(BaseExclusionDialog, ExcludeIfPresentDialogBase, ExcludeIfPresentDialogUi):
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)

        # help text
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
