from PyQt6 import QtCore, uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
)

from vorta.i18n import translate
from vorta.store.models import SettingsModel
from vorta.store.settings import get_grouped_checkbox_settings
from vorta.utils import get_asset
from vorta.views.base_tab import BaseTab
from vorta.views.partials.tooltip_button import ToolTipButton
from vorta.views.utils import get_colored_icon

uifile = get_asset('UI/misc_tab.ui')
MiscTabUI, MiscTabBase = uic.loadUiType(uifile)


class MiscTab(BaseTab, MiscTabBase, MiscTabUI):
    refresh_archive = QtCore.pyqtSignal()

    def __init__(self, parent=None, profile_provider=None):
        """Init."""
        super().__init__(parent=parent, profile_provider=profile_provider)
        self.setupUi(parent)

        self.checkboxLayout = QFormLayout(self.frameSettings)
        self.checkboxLayout.setSpacing(4)
        self.checkboxLayout.setHorizontalSpacing(8)
        self.checkboxLayout.setContentsMargins(0, 0, 0, 12)
        self.checkboxLayout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
        self.checkboxLayout.setFormAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.tooltip_buttons = []

        self.populate()

        # Connect to events
        self.track_palette_change()

    def populate(self):
        """
        Populate the misc tab with the settings widgets.

        Groups and per-group settings come from `get_grouped_checkbox_settings()`,
        which already filters out platform-irrelevant groups and legacy DB rows.
        """
        # clear layout
        while self.checkboxLayout.count():
            child = self.checkboxLayout.takeAt(0)
            self.checkboxLayout.removeItem(child)
            if child.widget():
                child.widget().deleteLater()
        self.tooltip_buttons = []

        i = 0
        for group_name, settings in get_grouped_checkbox_settings():
            # add spacer between groups
            if i > 0:
                spacer = QSpacerItem(20, 4, vPolicy=QSizePolicy.Policy.Fixed)
                self.checkboxLayout.setItem(i, QFormLayout.ItemRole.LabelRole, spacer)
                i += 1

            # add label for group
            label = QLabel()
            label.setText(translate('settings', group_name) + ':')
            self.checkboxLayout.setWidget(i, QFormLayout.ItemRole.LabelRole, label)

            # add settings widget of the group
            for setting in settings:
                # create widget
                cb = QCheckBox(translate('settings', setting.label))
                cb.setToolTip(setting.tooltip)
                cb.setCheckState(Qt.CheckState(setting.value))
                cb.setTristate(False)
                cb.stateChanged.connect(lambda v, key=setting.key: self.save_setting(key, v))
                if setting.key == 'enable_fixed_units':
                    cb.stateChanged.connect(self.refresh_archive.emit)

                tb = ToolTipButton()
                tb.setToolTip(setting.tooltip)

                cbl = QHBoxLayout()
                cbl.addWidget(cb)
                if setting.tooltip:
                    cbl.addWidget(tb)
                cbl.addItem(QSpacerItem(0, 0, hPolicy=QSizePolicy.Policy.Expanding))

                # add widget
                self.checkboxLayout.setLayout(i, QFormLayout.ItemRole.FieldRole, cbl)
                self.tooltip_buttons.append(tb)

                # increase i
                i += 1

        self.set_icons()

    def set_icons(self):
        """Set or update the icons in this view."""
        for button in self.tooltip_buttons:
            button.setIcon(get_colored_icon('help-about'))

    def save_setting(self, key, new_value):
        setting = SettingsModel.get(key=key)
        setting.value = bool(new_value)
        setting.save()
