import logging
from typing import Dict
from playhouse import signals

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
)

from vorta import config
from vorta._version import __version__
from vorta.i18n import translate
from vorta.store.models import BackupProfileMixin, SettingsModel
from vorta.store.settings import get_misc_settings
from vorta.utils import get_asset, search
from vorta.views.partials.tooltip_button import ToolTipButton
from vorta.views.utils import get_colored_icon

uifile = get_asset('UI/misctab.ui')
MiscTabUI, MiscTabBase = uic.loadUiType(uifile)

logger = logging.getLogger(__name__)


class MiscTab(MiscTabBase, MiscTabUI, BackupProfileMixin):
    def __init__(self, parent=None):
        """Init."""
        super().__init__(parent)
        self.setupUi(parent)
        self.settings_checkboxes: Dict[str, QCheckBox] = {}

        self.versionLabel.setText(__version__)
        self.logLink.setText(
            f'<a href="file://{config.LOG_DIR}"><span style="text-decoration:'
            'underline; color:#0984e3;">Log</span></a>'
        )

        self.checkboxLayout = QFormLayout(self.frameSettings)
        self.checkboxLayout.setSpacing(4)
        self.checkboxLayout.setHorizontalSpacing(8)
        self.checkboxLayout.setContentsMargins(0, 0, 0, 12)
        self.checkboxLayout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
        self.checkboxLayout.setFormAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.tooltip_buttons = []
        signals.post_save.connect(self.on_setting_update, sender=SettingsModel)

        self.populate()

        # Connect to palette change
        QApplication.instance().paletteChanged.connect(lambda p: self.set_icons())

    def populate(self):
        """
        Populate the misc tab with the settings widgets.

        Uses `create_group_widget` to construct the layout groups.
        """
        # clear layout
        while self.checkboxLayout.count():
            child = self.checkboxLayout.takeAt(0)
            self.checkboxLayout.removeItem(child)
            if child.widget():
                child.widget().deleteLater()
        self.tooltip_buttons = []

        # dynamically add widgets for settings
        misc_settings = get_misc_settings()

        i = 0
        for group in (
            SettingsModel.select(SettingsModel.group)
            .distinct(True)
            .where(SettingsModel.group != '')
            .order_by(SettingsModel.group.asc())
        ):
            # add spacer
            if i > 0:
                spacer = QSpacerItem(20, 4, vPolicy=QSizePolicy.Policy.Fixed)
                self.checkboxLayout.setItem(i, QFormLayout.ItemRole.LabelRole, spacer)
                i += 1

            # add label for next group
            label = QLabel()
            label.setText(translate('settings', group.group) + ':')
            self.checkboxLayout.setWidget(i, QFormLayout.ItemRole.LabelRole, label)

            # add settings widget of the group
            for setting in SettingsModel.select().where(
                SettingsModel.type == 'checkbox', SettingsModel.group == group.group
            ):
                # Skip settings that aren't specified in vorta.store.models.
                if not search(setting.key, misc_settings, lambda d: d['key']):
                    logger.warning('Unknown setting {}'.format(setting.key))
                    continue

                # create widget
                cb = QCheckBox(translate('settings', setting.label))
                cb.setChecked(setting.value)
                cb.setToolTip(setting.tooltip)
                cb.setCheckState(Qt.CheckState(setting.value))
                cb.setTristate(False)
                cb.stateChanged.connect(lambda v, key=setting.key: self.save_setting(key, v))

                tb = ToolTipButton()
                tb.setToolTip(setting.tooltip)

                cbl = QHBoxLayout()
                cbl.addWidget(cb)
                if setting.tooltip:
                    cbl.addWidget(tb)
                cbl.addItem(QSpacerItem(0, 0, hPolicy=QSizePolicy.Policy.Expanding))

                # add widget
                self.settings_checkboxes[setting.key] = cb
                self.checkboxLayout.setLayout(i, QFormLayout.ItemRole.FieldRole, cbl)
                self.tooltip_buttons.append(tb)

                # increase i
                i += 1

        self.set_icons()

    def on_setting_update(self, sender, instance: SettingsModel, created=False):
        """
        Handle a update of the settings db.
        Non-PyQt slot for peewee's `playhouse.signals` api.
        It calls `update_checkbox`.
        Parameters
        ----------
        sender : Type[SettingsModel]
            table sending model
        instance : SettingsModel
            The model instance (row) saved.
        created : bool, optional
            Whether it was newly created, by default False
        """
        if not created and instance.type == 'checkbox':
            self.update_checkbox(instance.key, instance.value)

    def update_checkbox(self, key, value):
        """
        Update the checkbox for a setting with a given key.
        Parameters
        ----------
        key : str
            The key of the setting to update.
        value : bool
            The value to set the checkbox to.
        """
        checkbox = self.settings_checkboxes.get(key)
        if checkbox:
            checkbox.setChecked(value)

    def set_icons(self):
        """Set or update the icons in this view."""
        for button in self.tooltip_buttons:
            button.setIcon(get_colored_icon('help-about'))

    def save_setting(self, key, new_value):
        setting = SettingsModel.get(key=key)
        setting.value = bool(new_value)
        setting.save()

    def set_borg_details(self, version, path):
        self.borgVersion.setText(version)
        self.borgPath.setText(path)
