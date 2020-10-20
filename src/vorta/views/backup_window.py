from PyQt5 import uic
from PyQt5 import QtCore
from PyQt5.QtWidgets import QFileDialog
from playhouse.shortcuts import model_to_dict, dict_to_model
from vorta.models import db, BackupProfileModel, BackupProfileMixin, EventLogModel, SchemaVersion, \
    SourceFileModel, SettingsModel, ArchiveModel, WifiSettingModel, RepoModel, SCHEMA_VERSION
from vorta.utils import get_asset
from vorta.keyring.db import VortaDBKeyring
from vorta.keyring.abc import get_keyring
from .utils import get_colored_icon
from pathlib import Path
import json
import datetime

uifile = get_asset('UI/backupwindow.ui')
BackupWindowUI, BackupWindowBase = uic.loadUiType(uifile)


class BackupWindow(BackupWindowBase, BackupWindowUI, BackupProfileMixin):
    def __init__(self, parent):
        super().__init__()
        self.setupUi(self)
        self.parent = parent
        self.setWindowTitle(self.tr("Backup Profile"))
        self.fileButton.setIcon(get_colored_icon('folder-open'))
        self.fileButton.clicked.connect(self.get_file)
        self.saveButton.clicked.connect(self.run)
        self.cancelButton.clicked.connect(self.reject)
        self.saveButton.setEnabled(False)
        self.overrideExisting.hide()

        profile = self.profile()
        self.keyring = get_keyring()
        self.url = str(Path.home()) if profile.repo is None else profile.repo.url

        if profile.repo is None or VortaDBKeyring().get_password('vorta-repo', profile.repo.url) is None:
            self.storePassword.hide()

    def profile(self):
        return self.parent.current_profile

    def profile_to_json(self, profile):
        # Profile to dict
        profile_dict = model_to_dict(profile)

        if self.storePassword.isChecked():
            profile_dict['password'] = self.keyring.get_password('vorta-repo', profile.repo.url)

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

    def get_file(self):
        fileName = QFileDialog.getSaveFileName(
            self,
            self.tr("Save profile"),
            self.url,
            self.tr("Vorta backup profile (*.vortabackup);;All files (*)"))[0]
        if fileName:
            self.locationLabel.setText(fileName)
        self.saveButton.setEnabled(bool(fileName))

    def run(self):
        profile = self.profile()
        json = self.profile_to_json(profile)
        with open(self.locationLabel.text(), 'w') as file:
            try:
                file.write(json)
                self.errors.setText(self.tr("Backup written to {}").format(self.locationLabel.text()))
                self.locationLabel.setText("")
                self.saveButton.setEnabled(False)
            except PermissionError:
                self.errors.setText(self.tr("Cannot write backup file"))

    def converter(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.__str__()


class RestoreWindow(BackupWindow):
    profile_restored = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Restore Profile"))
        self.saveButton.setText(self.tr("Open"))
        self.overrideExisting.show()
        self.storePassword.hide()

    def json_to_profile(self, jsonData):
        # Json string to dict
        profile_dict = json.loads(jsonData)

        if SCHEMA_VERSION < profile_dict['SchemaVersion']['version']:
            raise VersionException()
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
            self.keyring.set_password('vorta-repo', profile_dict['repo']['url'], profile_dict['password'])
            del profile_dict['password']

        if self.overrideExisting.isChecked():
            self.returns['overwrite'] = True
            db.drop_tables([SettingsModel])
            db.create_tables([SettingsModel])
            db.drop_tables([EventLogModel])
            db.create_tables([EventLogModel])
            db.drop_tables([WifiSettingModel])
            db.create_tables([WifiSettingModel])
            SettingsModel.insert_many(profile_dict['SettingsModel']).execute()
            EventLogModel.insert_many(profile_dict['EventLogModel']).execute()
            WifiSettingModel.insert_many(profile_dict['WifiSettingModel']).execute()

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
            if not ArchiveModel.get_or_none(ArchiveModel.snapshot_id == archive['snapshot_id']):
                dict_to_model(ArchiveModel, archive).save(force_insert=True)

        # Delete added dictionaries to make it match BackupProfileModel
        del profile_dict['SettingsModel']
        del profile_dict['SourceFileModel']
        del profile_dict['ArchiveModel']
        del profile_dict['EventLogModel']
        del profile_dict['WifiSettingModel']
        del profile_dict['SchemaVersion']

        # dict to profile
        new_profile = dict_to_model(BackupProfileModel, profile_dict)
        new_profile.save(force_insert=True)

        return new_profile

    def run(self):
        def get_schema_version(jsonData):
            return json.loads(jsonData)['SchemaVersion']['version']

        with open(self.locationLabel.text(), 'r') as file:
            try:
                jsonStr = file.read()
                self.returns = {}
                self.new_profile = self.json_to_profile(jsonStr)
                repo_url = self.new_profile.repo.url
                if self.keyring.get_password('vorta-repo', repo_url):
                    self.errors.setText(self.tr(f"Profile {self.new_profile.name} restored sucessfully"))
                    self.profile_restored.emit()
                else:
                    self.errors.setText(
                        self.tr(f"Password for {repo_url} cannot be found, consider unlinking and readding the repository"))  # noqa
            except (json.decoder.JSONDecodeError, KeyError):
                self.errors.setText(self.tr("Invalid backup file"))
            except AttributeError as e:
                # Runs when model upgrading code in json_to_profile incomplete
                schema_message = "Current schema: {0}\n Backup schema: {1}".format(
                    SCHEMA_VERSION, get_schema_version(jsonStr))
                self.errors.setText(
                    self.tr("Schema upgrade failure, file a bug report with the link in the Misc tab "
                            "with the following error: \n {0} \n {1}").format(str(e), schema_message))
            except VersionException:
                self.errors.setText(self.tr("Cannot use newer backup on older version"))
            except PermissionError:
                self.errors.setText(self.tr("Cannot read backup file"))

    def get_file(self):
        fileName = QFileDialog.getOpenFileName(
            self,
            self.tr("Load profile"),
            self.url,
            self.tr("Vorta backup profile (*.vortabackup);;All files (*)"))[0]
        if fileName:
            self.locationLabel.setText(fileName)
        self.saveButton.setEnabled(bool(fileName))


class VersionException(Exception):
    pass
