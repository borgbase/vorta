"""
This module provides the app's data store using Peewee with SQLite.

At the bottom there is a simple schema migration system.
"""

import json
from datetime import datetime

import peewee as pw
from playhouse import signals

from vorta.utils import slugify

DB = pw.Proxy()


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


class BaseModel(signals.Model):
    """Common model superclass."""


class RepoModel(BaseModel):
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
        database = DB


class RepoPassword(BaseModel):
    """Fallback to save repo passwords. Only used if no Keyring available."""

    url = pw.CharField(unique=True)
    password = pw.CharField()

    class Meta:
        database = DB


class BackupProfileModel(BaseModel):
    """Allows the user to switch between different configurations."""

    name = pw.CharField()
    added_at = pw.DateTimeField(default=datetime.now)
    repo = pw.ForeignKeyField(RepoModel, default=None, null=True)
    ssh_key = pw.CharField(default=None, null=True)
    compression = pw.CharField(default='lz4')
    exclude_patterns = pw.TextField(null=True)
    exclude_if_present = pw.TextField(null=True)
    schedule_mode = pw.CharField(default='off')
    schedule_interval_count = pw.IntegerField(default=3)
    schedule_interval_unit = pw.CharField(default='hours')
    schedule_fixed_hour = pw.IntegerField(default=3)
    schedule_fixed_minute = pw.IntegerField(default=42)
    schedule_interval_hours = pw.IntegerField(default=3)  # no longer used
    schedule_interval_minutes = pw.IntegerField(default=42)  # no longer used
    schedule_make_up_missed = pw.BooleanField(default=True)
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
        database = DB


class SourceFileModel(BaseModel):
    """A folder to be backed up, related to a Backup Configuration."""

    dir = pw.CharField()
    dir_size = pw.BigIntegerField(default=-1)
    dir_files_count = pw.BigIntegerField(default=-1)
    path_isdir = pw.BooleanField(default=False)
    profile = pw.ForeignKeyField(BackupProfileModel, default=1)
    added_at = pw.DateTimeField(default=datetime.utcnow)

    class Meta:
        database = DB
        table_name = 'sourcedirmodel'


class ArchiveModel(BaseModel):
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
        database = DB


class WifiSettingModel(BaseModel):
    """Save Wifi Settings"""

    ssid = pw.CharField()
    last_connected = pw.DateTimeField(null=True)
    allowed = pw.BooleanField(default=True)
    profile = pw.ForeignKeyField(BackupProfileModel, default=1)

    class Meta:
        database = DB


class EventLogModel(BaseModel):
    """Keep a log of background jobs."""

    start_time = pw.DateTimeField(default=datetime.now)
    end_time = pw.DateTimeField(default=datetime.now)
    category = pw.CharField()
    subcommand = pw.CharField(null=True)
    message = pw.CharField(null=True)
    returncode = pw.IntegerField(default=-1)
    params = JSONField(null=True)
    profile = pw.CharField(null=True)
    repo_url = pw.CharField(null=True)

    class Meta:
        database = DB


class SchemaVersion(BaseModel):
    """Keep DB version to apply the correct migrations."""

    version = pw.IntegerField()
    changed_at = pw.DateTimeField(default=datetime.now)

    class Meta:
        database = DB


class SettingsModel(BaseModel):
    """App settings unrelated to a single profile or repo"""

    key = pw.CharField(unique=True)
    value = pw.BooleanField(default=False)
    str_value = pw.CharField(default='')
    label = pw.CharField()
    group = pw.CharField(default='')  # Settings group name and label
    tooltip = pw.CharField(default='')  # optional tooltip for `checkbox` type
    type = pw.CharField()

    class Meta:
        database = DB


class BackupProfileMixin:
    """Extend to support multiple profiles later."""

    def profile(self):
        return BackupProfileModel.get(id=self.window().current_profile.id)
