import copy
import datetime
import json
import logging
from json import JSONDecodeError

from playhouse.shortcuts import dict_to_model, model_to_dict

from vorta.keyring.abc import VortaKeyring
from vorta.store.connection import DB, SCHEMA_VERSION, init_db
from vorta.store.models import (
    BackupProfileModel,
    ExclusionModel,
    RepoModel,
    SchemaVersion,
    SettingsModel,
    SourceFileModel,
    WifiSettingModel,
)
from vorta.store.settings import get_misc_settings

logger = logging.getLogger(__name__)


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

    @property
    def repo_url(self):
        if (
            'repo' in self._profile_dict
            and isinstance(self._profile_dict['repo'], dict)
            and 'url' in self._profile_dict['repo']
        ):
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
            model_to_dict(source, recurse=False, exclude=[SourceFileModel.id])
            for source in SourceFileModel.select().where(SourceFileModel.profile == profile)
        ]
        # Add ExclusionModel
        profile_dict['ExclusionModel'] = [
            model_to_dict(exclusion, recurse=False, exclude=[ExclusionModel.id])
            for exclusion in ExclusionModel.select().where(ExclusionModel.profile == profile)
        ]
        # Add SchemaVersion
        profile_dict['SchemaVersion'] = model_to_dict(SchemaVersion.get(id=1))

        if include_settings:
            # Add WifiSettingModel
            profile_dict['WifiSettingModel'] = [
                model_to_dict(wifi, recurse=False, exclude=[WifiSettingModel.id])
                for wifi in WifiSettingModel.select().where(WifiSettingModel.profile == profile.id)
            ]
            # Add SettingsModel
            profile_dict['SettingsModel'] = [model_to_dict(s, exclude=[SettingsModel.id]) for s in SettingsModel]
        return ProfileExport(profile_dict)

    def to_db(self, overwrite_profile=False, overwrite_settings=True):
        # Select the keyring before any DB write: the choice depends on the current `use_system_keyring`.
        keyring = VortaKeyring.get_keyring()
        profile_dict = copy.deepcopy(self._profile_dict)

        profile_schema = profile_dict['SchemaVersion']['version']
        if SCHEMA_VERSION < profile_schema:
            raise VersionException()
        elif SCHEMA_VERSION > profile_schema:
            # Add model upgrading code here, only needed if not adding columns
            if profile_schema < 16:
                for sourcedir in profile_dict.get('SourceFileModel', []):
                    sourcedir['dir_files_count'] = -1
                    sourcedir['dir_size'] = -1
                    sourcedir['path_isdir'] = False

        # Pop the extra sections so the rest matches BackupProfileModel.
        # A missing section leaves the existing rows alone, an empty one clears them.
        sections = {}
        for key in ('SettingsModel', 'WifiSettingModel', 'SourceFileModel', 'ExclusionModel'):
            if key in profile_dict:
                sections[key] = profile_dict.pop(key)
        password = profile_dict.pop('password', None)
        profile_dict.pop('SchemaVersion')
        repo_url = self.repo_url

        # IMMEDIATE takes the write lock upfront, so a concurrent writer is waited for via the busy timeout.
        with DB.atomic('IMMEDIATE'):
            profile_id = profile_dict['id']
            profile_name = profile_dict['name']
            existing_profile = None
            if overwrite_profile:
                existing_profile = BackupProfileModel.get_or_none(BackupProfileModel.name == profile_name)
                if existing_profile:
                    profile_id = existing_profile.id
            if not existing_profile:
                # Guarantee uniqueness of ids
                while BackupProfileModel.get_or_none(BackupProfileModel.id == profile_id) is not None:
                    profile_id += 1

                # Add suffix in case names are the same
                if BackupProfileModel.get_or_none(BackupProfileModel.name == profile_name) is not None:
                    suffix = 1
                    while (
                        BackupProfileModel.get_or_none(BackupProfileModel.name == f"{profile_name}-{suffix}")
                        is not None
                    ):
                        suffix += 1
                    profile_name = f"{profile_name}-{suffix}"
            profile_dict['id'] = profile_id
            profile_dict['name'] = profile_name

            # Load existing repo or restore it
            if profile_dict.get('repo'):
                repo = RepoModel.get_or_none(RepoModel.url == repo_url)
                if repo is None:
                    repo = dict_to_model(RepoModel, profile_dict['repo'])
                    repo.save(force_insert=True)
                profile_dict['repo'] = model_to_dict(repo)

            # Raises AttributeError on keys unknown to this schema, which rolls back the whole import.
            new_profile = dict_to_model(BackupProfileModel, profile_dict)
            new_profile.save(force_insert=existing_profile is None)

            for key, model in (
                ('SourceFileModel', SourceFileModel),
                ('ExclusionModel', ExclusionModel),
                ('WifiSettingModel', WifiSettingModel),
            ):
                # A new profile must not inherit rows orphaned under its id.
                if key not in sections and existing_profile:
                    continue
                rows = sections.get(key, [])
                for row in rows:
                    row.pop('id', None)
                    row['profile'] = profile_id
                model.delete().where(model.profile == profile_id).execute()
                model.insert_many(rows).execute()

            if overwrite_settings and 'SettingsModel' in sections:
                self._update_settings(sections['SettingsModel'])

        if password and repo_url and keyring is not None:
            try:
                keyring.set_password('vorta-repo', repo_url, password)
            except Exception:
                logger.warning('Could not store the imported repository password.', exc_info=True)

        init_db()  # rerun db init code to perform the same operations on the new as as on application boot
        return new_profile

    @staticmethod
    def _update_settings(rows):
        """Update existing settings in place, except machine-local ones. Never inserts rows."""
        skipped_keys = {s['key'] for s in get_misc_settings() if s['type'] == 'internal'} | {'use_system_keyring'}
        for row in rows:
            key = row.get('key')
            if key in skipped_keys:
                continue
            values = {field: row[field] for field in ('value', 'str_value') if field in row}
            if values:
                SettingsModel.update(**values).where(SettingsModel.key == key).execute()

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
    """For when current_version < export_version. Should only occur if downgrading"""

    pass


class ImportFailedException(Exception):
    """Raised when a profile could not be imported."""

    pass
