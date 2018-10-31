import peewee
import json
from datetime import datetime

db = peewee.Proxy()


class JSONField(peewee.TextField):
    """
    Class to "fake" a JSON field with a text field. Not efficient but works nicely

    From: https://gist.github.com/rosscdh/f4f26758b0228f475b132c688f15af2b
    """
    def db_value(self, value):
        """Convert the python value for storage in the database."""
        return value if value is None else json.dumps(value)

    def python_value(self, value):
        """Convert the database value to a pythonic value."""
        return value if value is None else json.loads(value)



class RepoModel(peewee.Model):
    """A single remote repo with unique URL."""
    url = peewee.CharField(unique=True)
    added_at = peewee.DateTimeField(default=datetime.utcnow)
    encryption = peewee.CharField(null=True)
    unique_size = peewee.IntegerField(null=True)
    unique_csize = peewee.IntegerField(null=True)
    total_size = peewee.IntegerField(null=True)
    total_unique_chunks = peewee.IntegerField(null=True)

    class Meta:
        database = db


class BackupProfileModel(peewee.Model):
    """Allows the user to switch between different configurations."""
    name = peewee.CharField()
    added_at = peewee.DateTimeField(default=datetime.now)
    repo = peewee.ForeignKeyField(RepoModel, default=None, null=True)
    ssh_key = peewee.CharField(default=None, null=True)
    compression = peewee.CharField(default='lz4')
    exclude_patterns = peewee.TextField(null=True)
    exclude_if_present = peewee.TextField(null=True)
    schedule_mode = peewee.CharField(default='off')
    schedule_interval_hours = peewee.IntegerField(default=3)
    schedule_interval_minutes = peewee.IntegerField(default=42)
    schedule_fixed_hour = peewee.IntegerField(default=3)
    schedule_fixed_minute = peewee.IntegerField(default=42)
    validation_on = peewee.BooleanField(default=True)
    validation_weeks = peewee.IntegerField(default=3)
    prune_on = peewee.BooleanField(default=False)
    prune_hour = peewee.IntegerField(default=2)
    prune_day = peewee.IntegerField(default=7)
    prune_week = peewee.IntegerField(default=4)
    prune_month = peewee.IntegerField(default=6)
    prune_year = peewee.IntegerField(default=2)

    class Meta:
        database = db


class SourceDirModel(peewee.Model):
    """A folder to be backed up, related to a Backup Configuration."""
    dir = peewee.CharField()
    config = peewee.ForeignKeyField(BackupProfileModel, default=1)
    added_at = peewee.DateTimeField(default=datetime.utcnow)

    class Meta:
        database = db


class SnapshotModel(peewee.Model):
    """A snapshot to a specific remote repository."""
    snapshot_id = peewee.CharField(unique=True)
    name = peewee.CharField()
    repo = peewee.ForeignKeyField(RepoModel, backref='snapshots')
    time = peewee.DateTimeField()

    def formatted_time(self):
        return

    class Meta:
        database = db


class WifiSettingModel(peewee.Model):
    """Save Wifi Settings"""
    ssid = peewee.CharField()
    last_connected = peewee.DateTimeField()
    allowed = peewee.BooleanField(default=True)
    profile = peewee.ForeignKeyField(BackupProfileModel, default=1)

    class Meta:
        database = db


class EventLogModel(peewee.Model):
    """Keep a log of background jobs."""
    start_time = peewee.DateTimeField(default=datetime.now)
    category = peewee.CharField()
    subcommand = peewee.CharField(null=True)
    message = peewee.CharField(null=True)
    returncode = peewee.IntegerField(default=1)
    params = JSONField(null=True)
    profile = peewee.ForeignKeyField(BackupProfileModel, default=1)

    class Meta:
        database = db


class BackupProfileMixin:
    """Extend to support multiple profiles later."""

    @property
    def profile(self):
        return BackupProfileModel.get(id=1)


def init_db(con):
    db.initialize(con)
    db.connect()
    db.create_tables([RepoModel, BackupProfileModel, SourceDirModel,
                      SnapshotModel, WifiSettingModel, EventLogModel])

    BackupProfileModel.get_or_create(id=1, name='Default')
