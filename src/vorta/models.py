"""
This module provides the app's data store using Peewee with SQLite.

At the bottom there is a simple schema migration system.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta as rd

import peewee as pw
from playhouse.migrate import SqliteMigrator, migrate

from vorta.i18n import trans_late
from vorta.utils import slugify

SCHEMA_VERSION = 17

db = pw.Proxy()


class JSONField(pw.TextField):
    """
    Class to "fake" a JSON field with a text field. Not efficient but works nicely.

    From: https://gist.github.com/rosscdh/f4f26758b0228f475b132c688f15af2b
    """

    def db_value(self, value):
        """Convert the python value for storage in the database."""
        return value if value is None else json.dumps(value)

    def python_value(self, value):
        """Convert the database value to a pythonic value."""
        return value if value is None else json.loads(value)


class RepoModel(pw.Model):
    """A single remote repo with unique URL."""
    url = pw.CharField(unique=True)
    added_at = pw.DateTimeField(default=datetime.now)
    encryption = pw.CharField(null=True)
    unique_size = pw.IntegerField(null=True)
    unique_csize = pw.IntegerField(null=True)
    total_size = pw.IntegerField(null=True)
    total_unique_chunks = pw.IntegerField(null=True)
    create_backup_cmd = pw.CharField(default='')
    extra_borg_arguments = pw.CharField(default='')

    def is_remote_repo(self):
        return not self.url.startswith('/')

    class Meta:
        database = db


class RepoPassword(pw.Model):
    """Fallback to save repo passwords. Only used if no Keyring available."""
    url = pw.CharField(unique=True)
    password = pw.CharField()

    class Meta:
        database = db


class BackupProfileModel(pw.Model):
    """Allows the user to switch between different configurations."""
    name = pw.CharField()
    added_at = pw.DateTimeField(default=datetime.now)
    repo = pw.ForeignKeyField(RepoModel, default=None, null=True)
    ssh_key = pw.CharField(default=None, null=True)
    compression = pw.CharField(default='lz4')
    exclude_patterns = pw.TextField(null=True)
    exclude_if_present = pw.TextField(null=True)
    schedule_mode = pw.CharField(default='off')
    schedule_interval_hours = pw.IntegerField(default=3)
    schedule_interval_minutes = pw.IntegerField(default=42)
    schedule_fixed_hour = pw.IntegerField(default=3)
    schedule_fixed_minute = pw.IntegerField(default=42)
    validation_on = pw.BooleanField(default=True)
    validation_weeks = pw.IntegerField(default=3)
    prune_on = pw.BooleanField(default=False)
    prune_hour = pw.IntegerField(default=2)
    prune_day = pw.IntegerField(default=7)
    prune_week = pw.IntegerField(default=4)
    prune_month = pw.IntegerField(default=6)
    prune_year = pw.IntegerField(default=2)
    prune_keep_within = pw.CharField(default='10H', null=True)
    new_archive_name = pw.CharField(default="{hostname}-{now:%Y-%m-%d-%H%M%S}")
    prune_prefix = pw.CharField(default="{hostname}-")
    pre_backup_cmd = pw.CharField(default='')
    post_backup_cmd = pw.CharField(default='')
    dont_run_on_metered_networks = pw.BooleanField(default=True)

    def refresh(self):
        return type(self).get(self._pk_expr())

    def slug(self):
        return slugify(self.name)

    class Meta:
        database = db


class SourceFileModel(pw.Model):
    """A folder to be backed up, related to a Backup Configuration."""
    dir = pw.CharField()
    dir_size = pw.BigIntegerField(default=-1)
    dir_files_count = pw.BigIntegerField(default=-1)
    path_isdir = pw.BooleanField(default=False)
    profile = pw.ForeignKeyField(BackupProfileModel, default=1)
    added_at = pw.DateTimeField(default=datetime.utcnow)

    class Meta:
        database = db
        table_name = 'sourcedirmodel'


class ArchiveModel(pw.Model):
    """An archive in a remote repository."""
    snapshot_id = pw.CharField()
    name = pw.CharField()
    repo = pw.ForeignKeyField(RepoModel, backref='archives')
    time = pw.DateTimeField()
    duration = pw.FloatField(null=True)
    size = pw.IntegerField(null=True)

    def formatted_time(self):
        return

    class Meta:
        database = db


class WifiSettingModel(pw.Model):
    """Save Wifi Settings"""
    ssid = pw.CharField()
    last_connected = pw.DateTimeField(null=True)
    allowed = pw.BooleanField(default=True)
    profile = pw.ForeignKeyField(BackupProfileModel, default=1)

    class Meta:
        database = db


class EventLogModel(pw.Model):
    """Keep a log of background jobs."""
    start_time = pw.DateTimeField(default=datetime.now)
    category = pw.CharField()
    subcommand = pw.CharField(null=True)
    message = pw.CharField(null=True)
    returncode = pw.IntegerField(default=1)
    params = JSONField(null=True)
    profile = pw.CharField(null=True)
    repo_url = pw.CharField(null=True)

    class Meta:
        database = db


class SchemaVersion(pw.Model):
    """Keep DB version to apply the correct migrations."""
    version = pw.IntegerField()
    changed_at = pw.DateTimeField(default=datetime.now)

    class Meta:
        database = db


class SettingsModel(pw.Model):
    """App settings unrelated to a single profile or repo"""
    key = pw.CharField(unique=True)
    value = pw.BooleanField(default=False)
    str_value = pw.CharField(default='')
    label = pw.CharField()
    type = pw.CharField()

    class Meta:
        database = db


class BackupProfileMixin:
    """Extend to support multiple profiles later."""

    def profile(self):
        return BackupProfileModel.get(id=self.window().current_profile.id)


def _apply_schema_update(current_schema, version_after, *operations):
    with db.atomic():
        migrate(*operations)
        current_schema.version = version_after
        current_schema.changed_at = datetime.now()
        current_schema.save()


def get_misc_settings():
    ''' Global settings that apply per platform '''
    # Default settings for all platforms.
    settings = [
        {
            'key': 'enable_notifications', 'value': True, 'type': 'checkbox',
            'label': trans_late('settings',
                                'Display notifications when background tasks fail')
        },
        {
            'key': 'enable_notifications_success', 'value': False, 'type': 'checkbox',
            'label': trans_late('settings',
                                'Also notify about successful background tasks')
        },
        {
            'key': 'autostart', 'value': False, 'type': 'checkbox',
            'label': trans_late('settings',
                                'Automatically start Vorta at login')
        },
        {
            'key': 'foreground', 'value': True, 'type': 'checkbox',
            'label': trans_late('settings',
                                'Open main window on startup')
        },
        {
            'key': 'get_srcpath_datasize', 'value': True, 'type': 'checkbox',
            'label': trans_late('settings',
                                'Get statistics of file/folder when added')
        },
        {
            'key': 'use_system_keyring', 'value': True, 'type': 'checkbox',
            'label': trans_late('settings',
                                'Store repository passwords in system keychain, if available.')
        },
        {
            'key': 'override_mount_permissions', 'value': False, 'type': 'checkbox',
            'label': trans_late('settings',
                                'Try to replace existing permissions when mounting an archive.')
        },
        {
            'key': 'previous_profile_id', 'str_value': '1', 'type': 'internal',
            'label': 'Previously selected profile'
        },
        {
            'key': 'previous_window_width', 'str_value': '800', 'type': 'internal',
            'label': 'Previous window width'
        },
        {
            'key': 'previous_window_height', 'str_value': '600', 'type': 'internal',
            'label': 'Previous window height'
        },
    ]
    if sys.platform == 'darwin':
        settings += [
            {
                'key': 'check_for_updates', 'value': True, 'type': 'checkbox',
                'label': trans_late('settings',
                                    'Check for updates on startup')
            },
            {
                'key': 'updates_include_beta', 'value': False, 'type': 'checkbox',
                'label': trans_late('settings',
                                    'Include pre-release versions when checking for updates')
            },
        ]
    else:
        settings += [
            {
                'key': 'enable_background_question', 'value': True, 'type': 'checkbox',
                'label': trans_late('settings',
                                    'Display background exit dialog')
            },
            {
                'key': 'disable_background_state', 'value': False, 'type': 'internal',
                'label': 'Previous background exit button state'
            }
        ]
    return settings


def cleanup_db():
    # Clean up database
    db.execute_sql("VACUUM")
    db.close()


def init_db(con=None):
    if con is not None:
        os.umask(0o0077)
        db.initialize(con)
        db.connect()
    db.create_tables([RepoModel, RepoPassword, BackupProfileModel, SourceFileModel, SettingsModel,
                      ArchiveModel, WifiSettingModel, EventLogModel, SchemaVersion])

    # Delete old log entries after 3 months.
    three_months_ago = datetime.now() - timedelta(days=180)
    EventLogModel.delete().where(EventLogModel.start_time < three_months_ago)

    # Migrations
    # See http://docs.peewee-orm.com/en/latest/peewee/playhouse.html#schema-migrations
    current_schema, created = SchemaVersion.get_or_create(id=1, defaults={'version': SCHEMA_VERSION})
    current_schema.save()
    if created or current_schema.version == SCHEMA_VERSION:
        pass
    else:
        migrator = SqliteMigrator(con)

    if current_schema.version < 4:  # version 3 to 4
        _apply_schema_update(
            current_schema, 4,
            migrator.add_column(ArchiveModel._meta.table_name, 'duration', pw.FloatField(null=True)),
            migrator.add_column(ArchiveModel._meta.table_name, 'size', pw.IntegerField(null=True))
        )
    if current_schema.version < 5:
        _apply_schema_update(
            current_schema, 5,
            migrator.drop_not_null(WifiSettingModel._meta.table_name, 'last_connected'),
        )

    if current_schema.version < 6:
        _apply_schema_update(
            current_schema, 6,
            migrator.add_column(EventLogModel._meta.table_name, 'repo_url', pw.CharField(null=True))
        )

    if current_schema.version < 7:
        _apply_schema_update(
            current_schema, 7,
            migrator.rename_column(SourceFileModel._meta.table_name, 'config_id', 'profile_id'),
            migrator.drop_column(EventLogModel._meta.table_name, 'profile_id'),
            migrator.add_column(EventLogModel._meta.table_name, 'profile', pw.CharField(null=True))
        )

    if current_schema.version < 8:
        _apply_schema_update(
            current_schema, 8,
            migrator.add_column(BackupProfileModel._meta.table_name,
                                'prune_keep_within', pw.CharField(null=True)))

    if current_schema.version < 9:
        _apply_schema_update(
            current_schema, 9,
            migrator.add_column(BackupProfileModel._meta.table_name, 'new_archive_name',
                                pw.CharField(default="{hostname}-{profile_slug}-{now:%Y-%m-%dT%H:%M:%S}")),
            migrator.add_column(BackupProfileModel._meta.table_name, 'prune_prefix',
                                pw.CharField(default="{hostname}-{profile_slug}-")),
        )

    if current_schema.version < 10:
        _apply_schema_update(
            current_schema, 10,
            migrator.add_column(BackupProfileModel._meta.table_name, 'pre_backup_cmd',
                                pw.CharField(default='')),
            migrator.add_column(BackupProfileModel._meta.table_name, 'post_backup_cmd',
                                pw.CharField(default='')),
        )

    if current_schema.version < 11:
        _apply_schema_update(current_schema, 11)
        for profile in BackupProfileModel:
            if profile.compression == 'zstd':
                profile.compression = 'zstd,3'
            if profile.compression == 'lzma,6':
                profile.compression = 'auto,lzma,6'
            profile.save()

    if current_schema.version < 12:
        _apply_schema_update(
            current_schema, 12,
            migrator.add_column(RepoModel._meta.table_name,
                                'extra_borg_arguments', pw.CharField(default='')))

    if current_schema.version < 13:
        # Migrate ArchiveModel data to new table to remove unique constraint from snapshot_id column.
        tables = db.get_tables()
        if ArchiveModel.select().count() == 0 and 'snapshotmodel' in tables:
            cursor = db.execute_sql('select * from snapshotmodel;')
            fields = [ArchiveModel.id, ArchiveModel.snapshot_id, ArchiveModel.name, ArchiveModel.repo,
                      ArchiveModel.time, ArchiveModel.duration, ArchiveModel.size]
            data = [row for row in cursor.fetchall()]
            with db.atomic():
                size = 1000
                for i in range(0, len(data), size):
                    ArchiveModel.insert_many(data[i: i + size], fields=fields).execute()

        _apply_schema_update(current_schema, 13)

    if current_schema.version < 14:
        _apply_schema_update(
            current_schema, 14,
            migrator.add_column(SettingsModel._meta.table_name,
                                'str_value', pw.CharField(default='')))

    if current_schema.version < 15:
        _apply_schema_update(
            current_schema, 15,
            migrator.add_column(BackupProfileModel._meta.table_name,
                                'dont_run_on_metered_networks', pw.BooleanField(default=True))
        )

    if current_schema.version < 16:
        _apply_schema_update(
            current_schema, 16,
            migrator.add_column(SourceFileModel._meta.table_name,
                                'dir_size', pw.BigIntegerField(default=-1)),
            migrator.add_column(SourceFileModel._meta.table_name,
                                'dir_files_count', pw.BigIntegerField(default=-1)),
            migrator.add_column(SourceFileModel._meta.table_name,
                                'path_isdir', pw.BooleanField(default=False))
        )

    if current_schema.version < 17:
        _apply_schema_update(
            current_schema, 17,
            migrator.add_column(RepoModel._meta.table_name,
                                'create_backup_cmd', pw.CharField(default=''))
        )

    # Create missing settings and update labels. Leave setting values untouched.
    for setting in get_misc_settings():
        s, created = SettingsModel.get_or_create(key=setting['key'], defaults=setting)
        s.label = setting['label']
        s.save()

    # Delete old log entries after 3 months.
    three_months_ago = datetime.now() - rd(months=3)
    EventLogModel.delete().where(EventLogModel.start_time < three_months_ago).execute()
