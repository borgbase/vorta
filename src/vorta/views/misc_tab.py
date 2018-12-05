from PyQt5 import uic
from PyQt5.QtWidgets import QCheckBox
from vorta.utils import get_asset, open_app_at_startup
from vorta.models import SettingsModel
from vorta._version import __version__

uifile = get_asset('UI/misctab.ui')
MiscTabUI, MiscTabBase = uic.loadUiType(uifile, from_imports=True, import_from='vorta.views')


class MiscTab(MiscTabBase, MiscTabUI):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)
        self.versionLabel.setText(__version__)

        for setting in SettingsModel.select().where(SettingsModel.type == 'checkbox'):
            b = QCheckBox(setting.label)
            b.setCheckState(setting.value)
            b.setTristate(False)
            b.stateChanged.connect(lambda v, key=setting.key: self.save_setting(key, v))
            self.checkboxLayout.addWidget(b)

    def save_setting(self, key, new_value):
        setting = SettingsModel.get(key=key)
        setting.value = bool(new_value)
        setting.save()

        if key == 'autostart':
            open_app_at_startup(new_value)
