import peewee
import os
from datetime import datetime
import vorta.config as config

db = peewee.SqliteDatabase(os.path.join(config.SETTINGS_DIR, 'settings.db'))


class RepoModel(peewee.Model):
    """A single remote repo with unique URL."""
    url = peewee.CharField(unique=True)
    password = peewee.CharField()
    added_at = peewee.DateTimeField(default=datetime.utcnow)
    encryption = peewee.CharField()

    class Meta:
        database = db


class BackupConfigModel(peewee.Model):
    """Allows the user to switch between different configurations."""
    name = peewee.CharField()
    added_at = peewee.DateTimeField(default=datetime.utcnow)
    repo = peewee.ForeignKeyField(RepoModel, default=None, null=True)

    class Meta:
        database = db


class SourceDirModel(peewee.Model):
    """A folder to be backed up, related to a Backup Configuration."""
    dir = peewee.CharField()
    config = peewee.ForeignKeyField(BackupConfigModel, default=1)
    added_at = peewee.DateTimeField(default=datetime.utcnow)

    class Meta:
        database = db


class SnapshotModel(peewee.Model):
    """A snapshot to a specific remote repository."""
    id = peewee.CharField(primary_key=True)
    name = peewee.CharField()
    repo = peewee.ForeignKeyField(RepoModel)
    time = peewee.DateTimeField()

    class Meta:
        database = db


db.connect()
db.create_tables([RepoModel, BackupConfigModel, SourceDirModel, SnapshotModel])

BackupConfigModel.get_or_create(id=1, name='Default')
