import datetime
import json

from playhouse.shortcuts import model_to_dict, dict_to_model

from vorta.keyring.abc import VortaKeyring
from vorta.models import RepoModel, SourceFileModel, WifiSettingModel, EventLogModel, SchemaVersion, \
    SettingsModel, BackupProfileModel, db, SCHEMA_VERSION


class ProfileExport:
    def __init__(self, profile_dict):
        self._profile_dict = profile_dict

    @property
    def schema_version(self):
        return self._profile_dict['SchemaVersion']['version']

    @property
    def repo_url(self):
        if 'repo' in self._profile_dict and 'url' in self._profile_dict['repo']:
            return self._profile_dict['repo']['url']
        return None

    @property
    def repo_password(self):
        return self._profile_dict['password'] if 'password' in self._profile_dict else None

    @repo_password.setter
    def repo_password(self, password):
        self._profile_dict['password'] = password

    @classmethod
    def from_db(cls, profile, store_password=True, include_settings=True):
        profile_dict = model_to_dict(profile, exclude=[RepoModel.id])  # Have to retain profile ID

        keyring = VortaKeyring.get_keyring()
        if store_password:
            profile_dict['password'] = keyring.get_password('vorta-repo', profile.repo.url)

        # For all below, exclude ids to prevent collisions. DB will automatically reassign ids
        # Add SourceFileModel
        profile_dict['SourceFileModel'] = [
            model_to_dict(
                source,
                recurse=False, exclude=[SourceFileModel.id]) for source in SourceFileModel.select().where(
                SourceFileModel.profile == profile)]
        # Add EventLogModel
        profile_dict['EventLogModel'] = [
            model_to_dict(s) for s in EventLogModel.select().order_by(
                EventLogModel.start_time.desc())]
        # Add SchemaVersion
        profile_dict['SchemaVersion'] = model_to_dict(SchemaVersion.get(id=1))

        if include_settings:
            # Add WifiSettingModel
            profile_dict['WifiSettingModel'] = [
                model_to_dict(
                    wifi, recurse=False) for wifi in WifiSettingModel.select().where(
                    WifiSettingModel.profile == profile.id)]
            # Add SettingsModel
            profile_dict['SettingsModel'] = [
                model_to_dict(s, exclude=[SettingsModel.id]) for s in SettingsModel]
        return ProfileExport(profile_dict)

    def to_db(self, override_settings=True):
        profile_schema = self._profile_dict['SchemaVersion']['version']
        returns = {}

        keyring = VortaKeyring.get_keyring()

        if SCHEMA_VERSION < profile_schema:
            raise VersionException()
        elif SCHEMA_VERSION > profile_schema:
            # Add model upgrading code here, only needed if not adding columns
            if profile_schema < 16:
                for sourcedir in self._profile_dict['SourceFileModel']:
                    sourcedir['dir_files_count'] = -1
                    sourcedir['dir_size'] = -1
                    sourcedir['path_isdir'] = False

        # Guarantee uniqueness of ids
        while BackupProfileModel.get_or_none(BackupProfileModel.id == self._profile_dict['id']) is not None:
            self._profile_dict['id'] += 1

        # Add suffix incase names are the same
        if BackupProfileModel.get_or_none(BackupProfileModel.name == self._profile_dict['name']) is not None:
            suffix = 1
            while BackupProfileModel.get_or_none(
                BackupProfileModel.name == f"{self._profile_dict['name']}-{suffix}") is not None:
                suffix += 1
            self._profile_dict['name'] = f"{self._profile_dict['name']}-{suffix}"

        # Load existing repo or restore it
        if self._profile_dict['repo']:
            repo = RepoModel.get_or_none(RepoModel.url == self._profile_dict['repo']['url'])
            if repo is None:
                # Load repo from export
                repo = dict_to_model(RepoModel, self._profile_dict['repo'])
                repo.save(force_insert=True)
                returns['repo'] = True
            else:
                # Use pre-exisitng repo
                self._profile_dict['repo'] = model_to_dict(repo)

        if self._profile_dict.get('password'):
            keyring.set_password('vorta-repo', self._profile_dict['repo']['url'], self._profile_dict['password'])
            del self._profile_dict['password']

        # Delete and recreate the tables to clear them
        if override_settings:
            db.drop_tables([SettingsModel, EventLogModel, WifiSettingModel])
            db.create_tables([SettingsModel, EventLogModel, WifiSettingModel])
            SettingsModel.insert_many(self._profile_dict['SettingsModel']).execute()
            EventLogModel.insert_many(self._profile_dict['EventLogModel']).execute()
            WifiSettingModel.insert_many(self._profile_dict['WifiSettingModel']).execute()
            returns['overrideExisting'] = True

        # Set the profile ids to be match new profile
        for source in self._profile_dict['SourceFileModel']:
            source['profile'] = self._profile_dict['id']
        SourceFileModel.insert_many(self._profile_dict['SourceFileModel']).execute()

        # Delete added dictionaries to make it match BackupProfileModel
        del self._profile_dict['SettingsModel']
        del self._profile_dict['SourceFileModel']
        del self._profile_dict['EventLogModel']
        del self._profile_dict['WifiSettingModel']
        del self._profile_dict['SchemaVersion']

        # dict to profile
        new_profile = dict_to_model(BackupProfileModel, self._profile_dict)
        new_profile.save(force_insert=True)
        return new_profile

    @classmethod
    def from_json(cls, json_string):
        return ProfileExport(json.loads(json_string))

    def to_json(self):
        return json.dumps(self._profile_dict, default=self._converter, indent=4)

    @staticmethod
    def _converter(obj):
        if isinstance(obj, datetime.datetime):
            return obj.__str__()


class VersionException(Exception):
    """ For when current_version < export_version. Should only occur if downgrading """
    pass
