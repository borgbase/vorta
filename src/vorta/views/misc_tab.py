from PyQt5 import uic
from PyQt5.QtWidgets import QCheckBox, QToolButton

from vorta.i18n import translate
from vorta.utils import get_asset
from vorta.autostart import open_app_at_startup
from vorta.models import SettingsModel, BackupProfileMixin, get_misc_settings
from vorta._version import __version__
from vorta.config import LOG_DIR

uifile = get_asset('UI/misctab.ui')
MiscTabUI, MiscTabBase = uic.loadUiType(uifile)


class MiscTab(MiscTabBase, MiscTabUI, BackupProfileMixin):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)
        self.versionLabel.setText(__version__)
        self.logLink.setText(f'<a href="file://{LOG_DIR}"><span style="text-decoration:'
                             'underline; color:#0984e3;">Log</span></a>')

        for setting in SettingsModel.select().where(SettingsModel.type == 'checkbox'):
            x = filter(lambda s: s['key'] == setting.key, get_misc_settings())
            if not list(x):  # Skip settings that aren't specified in vorta.models.
                continue
            b = QCheckBox(translate('settings', setting.label))
            b.setCheckState(setting.value)
            b.setTristate(False)
            b.stateChanged.connect(lambda v, key=setting.key: self.save_setting(key, v))
            self.checkboxLayout.addWidget(b)

        if SettingsModel.get(key="disable_background_question").value:
            self.background_button = QToolButton()
            self.background_button.setText(SettingsModel.get(key="disable_background_question").label)
            self.background_button.clicked.connect(self.disable_background_question)
            self.buttonLayout.addWidget(self.background_button)

    def disable_background_question(self, x):
        self.save_setting("disable_background_question", x)
        self.background_button.setParent(None)
        del(self.background_button)

    def save_setting(self, key, new_value):
        setting = SettingsModel.get(key=key)
        setting.value = bool(new_value)
        setting.save()

        if key == 'autostart':
            open_app_at_startup(new_value)

    def set_borg_details(self, version, path):
        self.borgVersion.setText(version)
        self.borgPath.setText(path)
