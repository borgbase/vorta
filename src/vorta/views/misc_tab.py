from PyQt5 import uic
from PyQt5.QtWidgets import QCheckBox

from vorta._version import __version__
from vorta.config import LOG_DIR
from vorta.i18n import translate
from vorta.store.settings import get_misc_settings
from vorta.store.models import SettingsModel, BackupProfileMixin
from vorta.utils import get_asset

uifile = get_asset('UI/misctab.ui')
MiscTabUI, MiscTabBase = uic.loadUiType(uifile)


class MiscTab(MiscTabBase, MiscTabUI, BackupProfileMixin):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)
        self.versionLabel.setText(__version__)
        self.logLink.setText(f'<a href="file://{LOG_DIR}"><span style="text-decoration:'
                             'underline; color:#0984e3;">Log</span></a>')

        self.populate()

    def populate(self):
        # clear layout
        while self.checkboxLayout.count():
            child = self.checkboxLayout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        # dynamically add widgets for settings
        for setting in SettingsModel.select().where(SettingsModel.type == 'checkbox'):
            x = filter(lambda s: s['key'] == setting.key, get_misc_settings())
            if not list(x):  # Skip settings that aren't specified in vorta.store.models.
                continue
            b = QCheckBox(translate('settings', setting.label))
            b.setCheckState(setting.value)
            b.setTristate(False)
            b.stateChanged.connect(lambda v, key=setting.key: self.save_setting(key, v))
            self.checkboxLayout.addWidget(b)

    def save_setting(self, key, new_value):
        setting = SettingsModel.get(key=key)
        setting.value = bool(new_value)
        setting.save()

    def set_borg_details(self, version, path):
        self.borgVersion.setText(version)
        self.borgPath.setText(path)
