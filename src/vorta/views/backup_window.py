from PyQt5 import uic
from PyQt5 import QtCore
from PyQt5.QtWidgets import QFileDialog, QDialogButtonBox
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
        self.buttonBox.accepted.connect(self.run)
        self.buttonBox.rejected.connect(self.reject)
        self.set_button_box()

        self.overrideExisting.hide()

        profile = self.parent.current_profile
        self.keyring = get_keyring()
        if profile.repo is None or VortaDBKeyring().get_password('vorta-repo', profile.repo.url) is None:
            self.storePassword.hide()

    def set_button_box(self):
        self.buttonBox.button(QDialogButtonBox.Save).setText(self.tr("Save"))
        self.buttonBox.button(QDialogButtonBox.Cancel).setText(self.tr("Cancel"))
        self.buttonBox.button(QDialogButtonBox.Save).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.Open).hide()

    def profile_to_json(self, profile):
        ''' Convert profile to json string '''
        # Profile to dict
        profile_dict = model_to_dict(profile, exclude=[RepoModel.id])  # Have to retain profile ID

        if self.storePassword.isChecked():
            profile_dict['password'] = self.keyring.get_password('vorta-repo', profile.repo.url)

        # For all below, exclude ids to prevent collisions. DB will automatically reassign ids
        # Add SourceFileModel
        profile_dict['SourceFileModel'] = [
            model_to_dict(
                source,
                recurse=False, exclude=[SourceFileModel.id]) for source in SourceFileModel.select().where(
                SourceFileModel.profile == profile)]
        # Add ArchiveModel
        profile_dict['ArchiveModel'] = [
            model_to_dict(
                archive,
                recurse=False, exclude=[ArchiveModel.id]) for archive in ArchiveModel.select().where(
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

        # Convert dict of profile to json string
        return json.dumps(profile_dict, default=self.converter, indent=4)

    def get_file(self):
        ''' Get targetted save file with custom extension '''
        fileName = QFileDialog.getSaveFileName(
            self,
            self.tr("Save profile"),
            str(Path.home()),
            self.tr("Vorta backup profile (*.vortabackup);;All files (*)"))[0]
        if fileName:
            self.locationLabel.setText(fileName)
        self.buttonBox.button(QDialogButtonBox.Save).setEnabled(bool(fileName))

    def run(self):
        ''' Attempt to write backup to file '''
        profile = self.parent.current_profile
        json = self.profile_to_json(profile)
        try:
            with open(self.locationLabel.text(), 'w') as file:
                file.write(json)
        except (PermissionError, OSError):
            self.errors.setText(self.tr("Backup file unwritable."))
        else:
            self.errors.setText(self.tr("Backup written to {}").format(self.locationLabel.text()))
            self.locationLabel.setText("")
            self.buttonBox.button(QDialogButtonBox.Save).setEnabled(False)

    def converter(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.__str__()


class RestoreWindow(BackupWindow):
    profile_restored = QtCore.pyqtSignal(BackupProfileModel, dict)

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Restore Profile"))
        self.overrideExisting.show()
        self.storePassword.hide()

    def set_button_box(self):
        self.buttonBox.button(QDialogButtonBox.Open).setText(self.tr("Open"))
        self.buttonBox.button(QDialogButtonBox.Cancel).setText(self.tr("Cancel"))
        self.buttonBox.button(QDialogButtonBox.Open).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.Save).hide()

    def json_to_profile(self, jsonData):
        ''' Convert json string to profile and save '''
        # Json string to dict
        profile_dict = json.loads(jsonData)
        profile_schema = profile_dict['SchemaVersion']['version']
        returns = {}

        if SCHEMA_VERSION < profile_schema:
            raise VersionException()
        elif SCHEMA_VERSION > profile_schema:
            # Add model upgrading code here, only needed if not adding columns
            if profile_schema < 16:
                for sourcedir in profile_dict['SourceFileModel']:
                    sourcedir['dir_files_count'] = -1
                    sourcedir['dir_size'] = -1
                    sourcedir['path_isdir'] = False

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
            repo = dict_to_model(RepoModel, profile_dict['repo'])
            repo.save(force_insert=True)
            returns['repo'] = True
        else:
            # Use pre-exisitng repo
            profile_dict['repo'] = model_to_dict(repo)

        if profile_dict.get('password'):
            self.keyring.set_password('vorta-repo', profile_dict['repo']['url'], profile_dict['password'])
            del profile_dict['password']

        # Delete and recreate the tables to clear them
        if self.overrideExisting.isChecked():
            db.drop_tables([SettingsModel, EventLogModel, WifiSettingModel])
            db.create_tables([SettingsModel, EventLogModel, WifiSettingModel])
            SettingsModel.insert_many(profile_dict['SettingsModel']).execute()
            EventLogModel.insert_many(profile_dict['EventLogModel']).execute()
            WifiSettingModel.insert_many(profile_dict['WifiSettingModel']).execute()
            returns['overrideExisting'] = True

        # Set the profile ids to be match new profile
        for source in profile_dict['SourceFileModel']:
            source['profile'] = profile_dict['id']
        SourceFileModel.insert_many(profile_dict['SourceFileModel']).execute()

        # Restore only if repo added to prevent overwriting
        if returns.get('repo'):
            # Set the profile ids to be match new profile
            for archive in profile_dict['ArchiveModel']:
                archive['repo'] = repo.id
            profile_dict['repo'] = repo.id
            ArchiveModel.insert_many(profile_dict['ArchiveModel']).execute()

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

        return new_profile, returns

    def run(self):
        ''' Attempt to read backup file and restore profile '''
        def get_schema_version(jsonData):
            return json.loads(jsonData)['SchemaVersion']['version']

        with open(self.locationLabel.text(), 'r') as file:
            try:
                jsonStr = file.read()
                new_profile, returns = self.json_to_profile(jsonStr)
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
                self.errors.setText(self.tr("Newer backup files cannot be used on older versions."))
            except PermissionError:
                self.errors.setText(self.tr("Backup file unreadable due to lack of permissions."))
            except FileNotFoundError:
                self.errors.setText(self.tr("Backup file not found."))
            else:
                repo_url = new_profile.repo.url
                if self.keyring.get_password('vorta-repo', repo_url):
                    self.errors.setText(self.tr(f"Profile {new_profile.name} restored sucessfully"))
                else:
                    self.errors.setText(
                        self.tr(f"Password for {repo_url} cannot be found, consider unlinking and readding the repository."))  # noqa
                self.profile_restored.emit(new_profile, returns)

    def get_file(self):
        ''' Attempt to read backup from file '''
        fileName = QFileDialog.getOpenFileName(
            self,
            self.tr("Load profile"),
            str(Path.home()),
            self.tr("Vorta backup profile (*.vortabackup);;All files (*)"))[0]
        if fileName:
            self.locationLabel.setText(fileName)
        self.buttonBox.button(QDialogButtonBox.Open).setEnabled(bool(fileName))


class VersionException(Exception):
    ''' For when current_version < backup_version. Should only occur if downgrading '''
    pass
