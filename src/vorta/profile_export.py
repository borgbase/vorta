import datetime
import json
from json import JSONDecodeError

from playhouse.shortcuts import model_to_dict, dict_to_model

from vorta.keyring.abc import VortaKeyring
from vorta.models import RepoModel, SourceFileModel, WifiSettingModel, SchemaVersion, \
    SettingsModel, BackupProfileModel, db, SCHEMA_VERSION, init_db, BackupProfileMixin


class ProfileExport:
    def __init__(self, profile_dict):
        self._profile_dict = profile_dict

    @property
    def id(self):
        return self._profile_dict['id']

    @property
    def name(self):
        return self._profile_dict['name']

    @property
    def schema_version(self):
        return self._profile_dict['SchemaVersion']['version']

    # this property is not used
    @property
    def repo_url(self):
        if 'repo' in self._profile_dict and \
                type(self._profile_dict['repo']) == dict and 'url' in self._profile_dict['repo']:
            return self._profile_dict['repo']['url']

    # this property is not used
    @property
    def repo_password(self):
        return self._profile_dict['password'] if 'password' in self._profile_dict else None

    # this property is useless
    @property
    def prof_x_repos(self):
        return self._profile_dict['BackupProfileMixin'] if 'BackupProfileMixin' in self._profile_dict else None

    # this setter is useless
    @repo_password.setter
    def repo_password(self, password):
        self._profile_dict['password'] = password

    @classmethod
    def from_db(cls, profile, store_password=True, include_settings=True):
        profile_dict = model_to_dict(profile, exclude=[RepoModel.id])  # Have to retain profile ID

        # Add multiple repos
        profile_dict['BackupProfileMixin'] = [
            model_to_dict(
                repo,
                recurse=True,
                exclude=[BackupProfileMixin.id, BackupProfileMixin.repo.id])
            for repo in BackupProfileMixin.get_repos(profile)]

        keyring = VortaKeyring.get_keyring()
        if store_password:
            for repo in BackupProfileMixin.get_repos(profile):
                for repo_dict in profile_dict['BackupProfileMixin']:
                    repo_dict['repo']['password'] \
                        = keyring.get_password('vorta-repo', repo.repo.url)

        # For all below, exclude ids to prevent collisions. DB will automatically reassign ids
        # Add SourceFileModel
        profile_dict['SourceFileModel'] = [
            model_to_dict(
                source,
                recurse=False, exclude=[SourceFileModel.id]) for source in SourceFileModel.select().where(
                SourceFileModel.profile == profile)]
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

    def to_db(self, overwrite_profile=False, overwrite_settings=True):
        profile_schema = self._profile_dict['SchemaVersion']['version']
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

        existing_profile = None
        if overwrite_profile:
            existing_profile = BackupProfileModel.get_or_none(BackupProfileModel.name == self.name)
            if existing_profile:
                self._profile_dict['id'] = existing_profile.id
        if not overwrite_profile or not existing_profile:
            # Guarantee uniqueness of ids
            while BackupProfileModel.get_or_none(BackupProfileModel.id == self.id) is not None:
                self._profile_dict['id'] += 1

            # Add suffix incase names are the same
            if BackupProfileModel.get_or_none(BackupProfileModel.name == self.name) is not None:
                suffix = 1
                while BackupProfileModel.get_or_none(BackupProfileModel.name == f"{self.name}-{suffix}") is not None:
                    suffix += 1
                self._profile_dict['name'] = f"{self.name}-{suffix}"

        if self.prof_x_repos:
            for prof_x_repo in self.prof_x_repos:
                if 'password' in prof_x_repo['repo']:
                    keyring.set_password('vorta-repo', prof_x_repo['repo']['url'], prof_x_repo['repo']['password'])
                    del prof_x_repo['repo']['password']

        # Load existing repo or restore it

        if self.prof_x_repos:
            for prof_x_repo in self.prof_x_repos:
                prof_x_repo['profile']['id'] = self._profile_dict['id']
                repo = RepoModel.get_or_none(RepoModel.url == prof_x_repo['repo']['url'])
                if repo is None:
                    # Load repo from export
                    repo = dict_to_model(RepoModel, prof_x_repo['repo'])
                    repo.save(force_insert=True)

                prof_x_repo['repo'] = model_to_dict(repo)
                prof_x_repo_db = dict_to_model(BackupProfileMixin, prof_x_repo)
                prof_x_repo_db.save(force_insert=True)

        # Delete and recreate the tables to clear them
        if overwrite_settings:
            db.drop_tables([SettingsModel, WifiSettingModel])
            db.create_tables([SettingsModel, WifiSettingModel])
            SettingsModel.insert_many(self._profile_dict['SettingsModel']).execute()
            WifiSettingModel.insert_many(self._profile_dict['WifiSettingModel']).execute()

        # Set the profile ids to be match new profile
        for source in self._profile_dict['SourceFileModel']:
            source['profile'] = self.id
        SourceFileModel.insert_many(self._profile_dict['SourceFileModel']).execute()

        # Delete added dictionaries to make it match BackupProfileModel
        del self._profile_dict['SettingsModel']
        del self._profile_dict['SourceFileModel']
        del self._profile_dict['WifiSettingModel']
        del self._profile_dict['SchemaVersion']
        del self._profile_dict['BackupProfileMixin']

        # dict to profile
        new_profile = dict_to_model(BackupProfileModel, self._profile_dict)
        if overwrite_profile and existing_profile:
            force_insert = False
        else:
            force_insert = True
        new_profile.save(force_insert=force_insert)
        init_db()  # rerun db init code to perform the same operations on the new as as on application boot
        return new_profile

    @classmethod
    def from_json(cls, filename):
        with open(filename, 'r') as file:
            try:
                profile_export = ProfileExport(json.loads(file.read()))
            except JSONDecodeError as exception:
                raise ImportFailedException(
                    'This file does not contain valid JSON: {}'.format(str(exception))
                ) from exception
        return profile_export

    def to_json(self):
        return json.dumps(self._profile_dict, default=self._converter, indent=4)

    @staticmethod
    def _converter(obj):
        if isinstance(obj, datetime.datetime):
            return obj.__str__()


class VersionException(Exception):
    """ For when current_version < export_version. Should only occur if downgrading """
    pass


class ImportFailedException(Exception):
    """Raised when a profile could not be imported."""
    pass
