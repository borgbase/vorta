import peewee
import os
from datetime import datetime
from .config import SETTINGS_DIR

db = peewee.SqliteDatabase(os.path.join(SETTINGS_DIR, 'settings.db'))


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
    added_at = peewee.DateTimeField(default=datetime.utcnow)
    repo = peewee.ForeignKeyField(RepoModel, default=None, null=True)
    ssh_key = peewee.CharField(default=None, null=True)
    compression = peewee.CharField(default='lz4')
    exclude_patterns = peewee.TextField(null=True)
    exclude_if_present = peewee.TextField(null=True)

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


db.connect()
db.create_tables([RepoModel, BackupProfileModel, SourceDirModel, SnapshotModel])

BackupProfileModel.get_or_create(id=1, name='Default')
