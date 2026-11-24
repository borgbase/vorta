from __future__ import annotations

import logging
from datetime import datetime

import peewee as pw
from playhouse.migrate import Operation, SqliteMigrator, migrate

from .models import (
    DB,
    ArchiveModel,
    BackupProfileModel,
    EventLogModel,
    RepoModel,
    SchemaVersion,
    SettingsModel,
    SourceFileModel,
    WifiSettingModel,
)

logger = logging.getLogger(__name__)


def run_migrations(current_schema: SchemaVersion, db_connection: pw.SqliteDatabase) -> None:
    """
    Apply new schema versions to database.

    See http://docs.peewee-orm.com/en/latest/peewee/playhouse.html#schema-migrations
    """
    migrator = SqliteMigrator(db_connection)

    if current_schema.version < 4:  # version 3 to 4
        _apply_schema_update(
            current_schema,
            4,
            migrator.add_column(ArchiveModel._meta.table_name, 'duration', pw.FloatField(null=True)),
            migrator.add_column(ArchiveModel._meta.table_name, 'size', pw.IntegerField(null=True)),
        )
    if current_schema.version < 5:
        _apply_schema_update(
            current_schema,
            5,
            migrator.drop_not_null(WifiSettingModel._meta.table_name, 'last_connected'),
        )

    if current_schema.version < 6:
        _apply_schema_update(
            current_schema,
            6,
            migrator.add_column(EventLogModel._meta.table_name, 'repo_url', pw.CharField(null=True)),
        )

    if current_schema.version < 7:
        _apply_schema_update(
            current_schema,
            7,
            migrator.rename_column(SourceFileModel._meta.table_name, 'config_id', 'profile_id'),
            migrator.drop_column(EventLogModel._meta.table_name, 'profile_id'),
            migrator.add_column(EventLogModel._meta.table_name, 'profile', pw.CharField(null=True)),
        )

    if current_schema.version < 8:
        _apply_schema_update(
            current_schema,
            8,
            migrator.add_column(
                BackupProfileModel._meta.table_name,
                'prune_keep_within',
                pw.CharField(null=True),
            ),
        )

    if current_schema.version < 9:
        _apply_schema_update(
            current_schema,
            9,
            migrator.add_column(
                BackupProfileModel._meta.table_name,
                'new_archive_name',
                pw.CharField(default="{hostname}-{profile_slug}-{now:%Y-%m-%dT%H:%M:%S}"),
            ),
            migrator.add_column(
                BackupProfileModel._meta.table_name,
                'prune_prefix',
                pw.CharField(default="{hostname}-{profile_slug}-"),
            ),
        )

    if current_schema.version < 10:
        _apply_schema_update(
            current_schema,
            10,
            migrator.add_column(
                BackupProfileModel._meta.table_name,
                'pre_backup_cmd',
                pw.CharField(default=''),
            ),
            migrator.add_column(
                BackupProfileModel._meta.table_name,
                'post_backup_cmd',
                pw.CharField(default=''),
            ),
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
            current_schema,
            12,
            migrator.add_column(
                RepoModel._meta.table_name,
                'extra_borg_arguments',
                pw.CharField(default=''),
            ),
        )

    if current_schema.version < 13:
        # Migrate ArchiveModel data to new table to remove unique constraint from snapshot_id column.
        tables = DB.get_tables()
        if ArchiveModel.select().count() == 0 and 'snapshotmodel' in tables:
            cursor = DB.execute_sql('select * from snapshotmodel;')
            fields = [
                ArchiveModel.id,
                ArchiveModel.snapshot_id,
                ArchiveModel.name,
                ArchiveModel.repo,
                ArchiveModel.time,
                ArchiveModel.duration,
                ArchiveModel.size,
            ]
            data = [row for row in cursor.fetchall()]
            with DB.atomic():
                size = 1000
                for i in range(0, len(data), size):
                    ArchiveModel.insert_many(data[i : i + size], fields=fields).execute()

        _apply_schema_update(current_schema, 13)

    if current_schema.version < 14:
        _apply_schema_update(
            current_schema,
            14,
            migrator.add_column(SettingsModel._meta.table_name, 'str_value', pw.CharField(default='')),
        )

    if current_schema.version < 15:
        _apply_schema_update(
            current_schema,
            15,
            migrator.add_column(
                BackupProfileModel._meta.table_name,
                'dont_run_on_metered_networks',
                pw.BooleanField(default=True),
            ),
        )

    if current_schema.version < 16:
        _apply_schema_update(
            current_schema,
            16,
            migrator.add_column(
                SourceFileModel._meta.table_name,
                'dir_size',
                pw.BigIntegerField(default=-1),
            ),
            migrator.add_column(
                SourceFileModel._meta.table_name,
                'dir_files_count',
                pw.BigIntegerField(default=-1),
            ),
            migrator.add_column(
                SourceFileModel._meta.table_name,
                'path_isdir',
                pw.BooleanField(default=False),
            ),
        )

    if current_schema.version < 17:
        _apply_schema_update(
            current_schema,
            17,
            migrator.add_column(
                RepoModel._meta.table_name,
                'create_backup_cmd',
                pw.CharField(default=''),
            ),
        )

    if current_schema.version < 18:
        _apply_schema_update(
            current_schema,
            18,
            migrator.add_column(
                BackupProfileModel._meta.table_name,
                'schedule_interval_unit',
                pw.CharField(default='hours'),
            ),
            migrator.add_column(
                BackupProfileModel._meta.table_name,
                'schedule_interval_count',
                pw.IntegerField(default=3),
            ),
            migrator.add_column(
                BackupProfileModel._meta.table_name,
                'schedule_make_up_missed',
                pw.BooleanField(default=False),
            ),
            migrator.add_column(
                EventLogModel._meta.table_name,
                'end_time',
                pw.DateTimeField(default=datetime.now),
            ),
        )

    if current_schema.version < 19:
        _apply_schema_update(
            current_schema,
            19,
            migrator.add_column(SettingsModel._meta.table_name, 'group', pw.CharField(default='')),
        )

    if current_schema.version < 20:
        _apply_schema_update(
            current_schema,
            20,
            migrator.add_column(SettingsModel._meta.table_name, 'tooltip', pw.CharField(default='')),
        )

    if current_schema.version < 21:
        _apply_schema_update(
            current_schema,
            21,
            migrator.add_column(
                ArchiveModel._meta.table_name,
                'trigger',
                pw.CharField(null=True),
            ),
        )

    if current_schema.version < 22:
        _apply_schema_update(
            current_schema,
            22,
            migrator.add_column(
                RepoModel._meta.table_name,
                'name',
                pw.CharField(default=''),
            ),
        )

    if current_schema.version < 23:
        _apply_schema_update(
            current_schema,
            23,
            migrator.add_column(
                BackupProfileModel._meta.table_name,
                'compaction_on',
                pw.BooleanField(default=True),
            ),
            migrator.add_column(
                BackupProfileModel._meta.table_name,
                'compaction_weeks',
                pw.IntegerField(default=3),
            ),
        )


def _apply_schema_update(current_schema: SchemaVersion, version_after: int, *operations: Operation) -> None:
    with DB.atomic():
        for operation in operations:
            if not _adds_existing_column(operation):
                migrate(operation)
        current_schema.version = version_after
        current_schema.changed_at = datetime.now()
        current_schema.save()


def _adds_existing_column(operation: Operation) -> bool:
    """
    Check if `operation` adds a column that the table already has.

    A database can already contain parts of a newer schema while its schema version is older,
    e.g. after an earlier migration was only partly applied. Adding such a column again fails with
    "duplicate column name" and Vorta can't start, so these operations are skipped.
    """
    # peewee 3 stores the name of the migrator method, peewee 4 the function itself.
    method = getattr(operation, 'method', None) or operation.fn.__name__
    if method != 'add_column':
        return False
    table, column_name = operation.args[:2]
    if column_name not in {column.name for column in operation.migrator.database.get_columns(table)}:
        return False
    logger.warning('Column %s.%s already exists, skipping it in the schema migration.', table, column_name)
    return True
