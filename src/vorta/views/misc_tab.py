from PyQt5 import uic
from PyQt5.QtWidgets import QCheckBox
from vorta.utils import get_asset, open_app_at_startup, format_archive_name
from vorta.models import SettingsModel, BackupProfileMixin
from vorta._version import __version__

uifile = get_asset('UI/misctab.ui')
MiscTabUI, MiscTabBase = uic.loadUiType(uifile, from_imports=True, import_from='vorta.views')


class MiscTab(MiscTabBase, MiscTabUI, BackupProfileMixin):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)
        self.versionLabel.setText(__version__)

        self.archiveNameTemplate.textChanged.connect(
            lambda tpl, key='archive_name': self.save_archive_template(tpl, key))
        self.prunePrefixTemplate.textChanged.connect(
            lambda tpl, key='prune_prefix': self.save_archive_template(tpl, key))
        self.archiveNameTemplate.setText(SettingsModel.get(key='archive_name').value_text)
        self.prunePrefixTemplate.setText(SettingsModel.get(key='prune_prefix').value_text)

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

    def save_archive_template(self, tpl, key):
        try:
            preview = 'Preview: ' + format_archive_name(self.profile(), tpl)
            setting = SettingsModel.get(key=key)
            setting.value_text = tpl
            setting.save()
        except Exception:
            preview = 'Error in archive name template.'

        if key == 'archive_name':
            self.archiveNamePreview.setText(preview)
        else:
            self.prunePrefixPreview.setText(preview)
