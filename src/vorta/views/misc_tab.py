from PyQt5 import uic
from PyQt5.QtWidgets import QCheckBox

from vorta.i18n import translate
from vorta.utils import get_asset
from vorta.autostart import open_app_at_startup
from vorta.models import SettingsModel, BackupProfileMixin, get_misc_settings
from vorta._version import __version__
from vorta.config import LOG_DIR
from vorta.borg.config import BorgConfigThread

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

        self.load_from_config()
        self.overrideFreeSpace.clicked.connect(self.save_to_config)

    def save_setting(self, key, new_value):
        setting = SettingsModel.get(key=key)
        setting.value = bool(new_value)
        setting.save()

        if key == 'autostart':
            open_app_at_startup(new_value)

    def set_borg_details(self, version, path):
        self.borgVersion.setText(version)
        self.borgPath.setText(path)

    def load_from_config(self):
        if self.profile().repo.is_remote_repo():
            self.overrideFreeSpace.setEnabled(False)
        else:
            self.overrideFreeSpace.setEnabled(True)
            self.run_config(['additional_free_space'])  # To load checkbox

        self.errorText.setText('')
        self.errorText.repaint()

    def set_checkbox_state(self, result):
        if 'additional_free_space' in result:
            spaceOverride = result['data'] != 0
            self.overrideFreeSpace.setChecked(spaceOverride)

    def save_to_config(self):
        if self.overrideFreeSpace.isChecked():
            self.run_config(['additional_free_space', '999T'])
        else:
            self.run_config(['additional_free_space', '0'])

    def run_config(self, values):
        params = BorgConfigThread.prepare(self.profile(), values)
        if params['ok']:
            thread = BorgConfigThread(params['cmd'], params, parent=self)
            if len(values) % 2 == 1:  # To check if its getting the value
                thread.result.connect(self.set_checkbox_state)
            self.thread = thread  # Needs to be connected to self for tests to work.
            self.thread.start()
            return params
        else:
            self._set_status(params['message'])

    def _set_status(self, text):
        self.errorText.setText(text)
        self.errorText.repaint()
