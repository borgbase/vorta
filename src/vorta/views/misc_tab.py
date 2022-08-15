import logging
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCheckBox, QFormLayout, QLabel, QSizePolicy, QSpacerItem
from vorta._version import __version__
from vorta.config import LOG_DIR
from vorta.i18n import translate
from vorta.store.models import BackupProfileMixin, SettingsModel
from vorta.store.settings import get_misc_settings
from vorta.utils import get_asset, search

uifile = get_asset('UI/misctab.ui')
MiscTabUI, MiscTabBase = uic.loadUiType(uifile)

logger = logging.getLogger(__name__)


class MiscTab(MiscTabBase, MiscTabUI, BackupProfileMixin):
    def __init__(self, parent=None):
        """Init."""
        super().__init__(parent)
        self.setupUi(parent)
        self.versionLabel.setText(__version__)
        self.logLink.setText(
            f'<a href="file://{LOG_DIR}"><span style="text-decoration:' 'underline; color:#0984e3;">Log</span></a>'
        )

        self.checkboxLayout = QFormLayout(self.frameSettings)
        self.checkboxLayout.setSpacing(4)
        self.checkboxLayout.setHorizontalSpacing(8)
        self.checkboxLayout.setContentsMargins(0, 0, 0, 12)
        self.checkboxLayout.setFormAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.populate()

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
                cb.setCheckState(setting.value)
                cb.setTristate(False)
                cb.stateChanged.connect(lambda v, key=setting.key: self.save_setting(key, v))

                # add widget
                self.checkboxLayout.setWidget(i, QFormLayout.ItemRole.FieldRole, cb)

                # increase i
                i += 1

    def save_setting(self, key, new_value):
        setting = SettingsModel.get(key=key)
        setting.value = bool(new_value)
        setting.save()

    def set_borg_details(self, version, path):
        self.borgVersion.setText(version)
        self.borgPath.setText(path)
