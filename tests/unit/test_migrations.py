import peewee as pw
import pytest
from playhouse.migrate import SqliteMigrator, migrate

from vorta.store.connection import SCHEMA_VERSION
from vorta.store.migrations import run_migrations
from vorta.store.models import (
    DB,
    ArchiveModel,
    BackupProfileModel,
    RepoModel,
    SchemaVersion,
    SettingsModel,
)

# Columns added by the schema updates after version 20.
COLUMNS_ADDED_AFTER_V20 = [
    (ArchiveModel._meta.table_name, 'trigger'),
    (RepoModel._meta.table_name, 'name'),
    (BackupProfileModel._meta.table_name, 'compaction_on'),
    (BackupProfileModel._meta.table_name, 'compaction_weeks'),
]


@pytest.fixture
def partly_migrated_db(tmp_path):
    """
    A database at schema version 19 that already has the `settingsmodel.tooltip` column of version 20,
    like a database where an earlier migration was only partly applied.
    """
    db = pw.SqliteDatabase(str(tmp_path / 'settings.sqlite'))
    previous_db = DB.obj
    DB.initialize(db)
    db.connect()
    db.create_tables([RepoModel, BackupProfileModel, SettingsModel, ArchiveModel, SchemaVersion])

    migrator = SqliteMigrator(db)
    migrate(*(migrator.drop_column(table, column) for table, column in COLUMNS_ADDED_AFTER_V20))
    SchemaVersion.create(id=1, version=19)

    yield db

    db.close()
    DB.initialize(previous_db)


def column_names(db, table):
    return {column.name for column in db.get_columns(table)}


def test_migrations_skip_existing_columns(partly_migrated_db):
    assert 'tooltip' in column_names(partly_migrated_db, SettingsModel._meta.table_name)
    for table, column in COLUMNS_ADDED_AFTER_V20:
        assert column not in column_names(partly_migrated_db, table)

    run_migrations(SchemaVersion.get(id=1), partly_migrated_db)

    assert SchemaVersion.get(id=1).version == SCHEMA_VERSION
    assert 'tooltip' in column_names(partly_migrated_db, SettingsModel._meta.table_name)
    for table, column in COLUMNS_ADDED_AFTER_V20:
        assert column in column_names(partly_migrated_db, table)
