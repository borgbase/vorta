from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog, QDialogButtonBox
from playhouse.shortcuts import model_to_dict, dict_to_model
from vorta.models import db, BackupProfileModel, BackupProfileMixin, EventLogModel, SchemaVersion, \
    SourceFileModel, SettingsModel, ArchiveModel, WifiSettingModel, RepoModel, SCHEMA_VERSION
from vorta.utils import get_asset, keyring
from .utils import get_colored_icon
from pathlib import Path
import json
import datetime

uifile = get_asset('UI/backup.ui')
BackupWindowUI, BackupWindowBase = uic.loadUiType(uifile)


class BackupWindow(BackupWindowBase, BackupWindowUI, BackupProfileMixin):
    def __init__(self, profile):
        super().__init__()
        self.setupUi(self)
        self.profile = profile
        self.setWindowTitle(self.tr("Backup Profile"))
        self.fileButton.setIcon(get_colored_icon('folder-open'))
        self.fileButton.clicked.connect(self.get_file)
        self.buttonBox.accepted.connect(self.run)
        self.set_buttons(False)
        self.overrideExisting.hide()
        self.buttonBox.button(QDialogButtonBox.Open).hide()
        self.url = str(Path.home()) if self.profile.repo is None else self.profile.repo.url

        if self.profile.repo is not None and self.profile.repo.encryption == 'none':
            self.storePassword.hide()

    def get_file(self):
        self.fileName = QFileDialog.getSaveFileName(
            self,
            self.tr("Save profile"),
            self.url,
            self.tr("Vorta backup profile (*.vortabackup)"))
        if self.fileName[0] != '':
            self.locationLabel.setText(self.fileName[0])
        self.set_buttons(self.fileName[0] != '')

    def set_buttons(self, enabled):
        self.buttonBox.button(QDialogButtonBox.Save).setEnabled(enabled)
        self.buttonBox.button(QDialogButtonBox.Open).setEnabled(enabled)

    def run(self):
        json = self.profile_to_json(self.profile)
        if self.fileName[0] != '':
            file = open(self.fileName[0], 'w')
            file.write(json)
            file.close()
            self.accept()

    def profile_to_json(self, profile):
        # Profile to dict
        profile_dict = model_to_dict(profile)

        if self.storePassword.isChecked():
            profile_dict['password'] = keyring.get_password('vorta-repo', profile.repo.url)

        # Add SourceFileModel
        profile_dict['SourceFileModel'] = [
            model_to_dict(
                source,
                recurse=False) for source in SourceFileModel.select().where(
                SourceFileModel.profile == profile)]
        # Add ArchiveModel
        profile_dict['ArchiveModel'] = [
            model_to_dict(
                archive,
                recurse=False) for archive in ArchiveModel.select().where(
                ArchiveModel.repo == profile.repo.id)]
        # Add WifiSettingModel
        profile_dict['WifiSettingModel'] = [
            model_to_dict(
                wifi, recurse=False) for wifi in WifiSettingModel.select().where(
                WifiSettingModel.profile == profile.id)]
        # Add EventLogModel
        profile_dict['EventLogModel'] = [
            model_to_dict(s) for s in EventLogModel.select().order_by(
                EventLogModel.start_time.desc())]
        # Add SchemaVersion
        profile_dict['SchemaVersion'] = model_to_dict(SchemaVersion.get(id=1))
        # Add SettingsModel
        profile_dict['SettingsModel'] = [
            model_to_dict(s) for s in SettingsModel.select().where(
                SettingsModel.type == 'checkbox')]
        # dict to json string
        return json.dumps(profile_dict, default=self.converter, indent=4)

    def json_to_profile(self, jsonData):
        # Json string to dict
        profile_dict = json.loads(jsonData)

        if SCHEMA_VERSION < profile_dict['SchemaVersion']['version']:
            raise VersionException("Cannot use newer backup on older version")
        elif SCHEMA_VERSION > profile_dict['SchemaVersion']['version']:
            # Add model upgrading code here, only needed if not adding columns
            pass

        # Guarantee uniqueness of ids
        while BackupProfileModel.get_or_none(BackupProfileModel.id == profile_dict['id']) is not None:
            profile_dict['id'] += 1

        # Add suffix incase names are the same
        if BackupProfileModel.get_or_none(BackupProfileModel.name == profile_dict['name']) is not None:
            suffix = 1
            while BackupProfileModel.get_or_none(
                    BackupProfileModel.name == f"{profile_dict['name']}-{suffix}") is not None:
                suffix += 1
            profile_dict['name'] = f"{profile_dict['name']}-{suffix}"

        # Load existing repo or restore it
        repo = RepoModel.get_or_none(RepoModel.url == profile_dict['repo']['url'])
        if repo is None:
            # Load repo from backup
            while RepoModel.get_or_none(RepoModel.id == profile_dict['repo']['id']):
                profile_dict['repo']['id'] += 1
            repo = dict_to_model(RepoModel, profile_dict['repo'])
            repo.save(force_insert=True)
            self.returns['repo'] = True
        else:
            # Use pre-exisitng repo
            profile_dict['repo'] = model_to_dict(repo)

        if profile_dict.get('password'):
            keyring.set_password('vorta-repo', profile_dict['repo']['url'], profile_dict['password'])
            del profile_dict['password']

        if self.overrideExisting.isChecked():
            self.returns['overwrite'] = True
            db.drop_tables([SettingsModel])
            db.create_tables([SettingsModel])
            [dict_to_model(SettingsModel, setting).save(force_insert=True) for setting in profile_dict['SettingsModel']]
            db.drop_tables([EventLogModel])
            db.create_tables([EventLogModel])
            [dict_to_model(EventLogModel, event).save(force_insert=True) for event in profile_dict['EventLogModel']]
            db.drop_tables([WifiSettingModel])
            db.create_tables([WifiSettingModel])
            [dict_to_model(WifiSettingModel, wifi).save(force_insert=True) for wifi in profile_dict['WifiSettingModel']]

        for source in profile_dict['SourceFileModel']:
            source['profile'] = profile_dict['id']
            # Guarantee uniqueness of ids
            while SourceFileModel.get_or_none(SourceFileModel.id == source['id']) is not None:
                source['id'] += 1
            dict_to_model(SourceFileModel, source).save(force_insert=True)

        for archive in profile_dict['ArchiveModel']:
            archive['repo'] = profile_dict['repo']['id']
            # Guarantee uniqueness of ids
            while ArchiveModel.get_or_none(ArchiveModel.id == archive['id']) is not None:
                archive['id'] += 1
            if ArchiveModel.get_or_none(ArchiveModel.snapshot_id == archive['snapshot_id']) is None:
                dict_to_model(ArchiveModel, archive).save(force_insert=True)

        # Delete added dictionaries to make it match BackupProfileModel
        del profile_dict['SettingsModel']
        del profile_dict['SourceFileModel']
        del profile_dict['ArchiveModel']
        del profile_dict['EventLogModel']
        del profile_dict['WifiSettingModel']
        del profile_dict['SchemaVersion']

        # dict to profile
        self.new_profile = dict_to_model(BackupProfileModel, profile_dict)
        self.new_profile.save(force_insert=True)

    def converter(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.__str__()


class RestoreWindow(BackupWindow):
    def __init__(self, profile):
        super().__init__(profile)
        self.setWindowTitle(self.tr("Restore Profile"))
        self.overrideExisting.show()
        self.storePassword.hide()
        self.buttonBox.button(QDialogButtonBox.Save).hide()
        self.buttonBox.button(QDialogButtonBox.Open).show()

    def run(self):
        if self.fileName[0] is not None:
            file = open(self.fileName[0], 'r')
            jsonStr = file.read()
            file.close()
            try:
                self.returns = {}
                self.json_to_profile(jsonStr)
                self.errors.setText("")
                self.accept()
            except json.decoder.JSONDecodeError:
                self.errors.setText(self.tr("Invalid backup file"))
            except VersionException as e:
                self.errors.setText(str(e))

    def get_file(self):
        self.fileName = QFileDialog.getOpenFileName(
            self,
            self.tr("Load profile"),
            self.url,
            self.tr("Vorta backup profile (*.vortabackup)"))
        if self.fileName[0] != '':
            self.locationLabel.setText(self.fileName[0])
        self.set_buttons(self.fileName[0] != '')


class VersionException(Exception):
    pass
