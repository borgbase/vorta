from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timedelta

import peewee as pw
from peewee import Tuple, fn
from playhouse import signals

from vorta import config
from vorta.autostart import open_app_at_startup
from vorta.log import set_file_logging

from .migrations import run_migrations
from .models import (
    DB,
    ArchiveModel,
    BackupProfileModel,
    EventLogModel,
    ExclusionModel,
    JobModel,
    RepoModel,
    RepoPassword,
    SchedulerPauseModel,
    SchemaVersion,
    SettingsModel,
    SourceFileModel,
    WifiSettingModel,
)
from .settings import get_misc_settings

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 23


@signals.post_save(sender=SettingsModel)
def setup_autostart(model_class: type, instance: SettingsModel, created: bool) -> None:
    if instance.key == 'autostart':
        open_app_at_startup(instance.value)


@signals.post_save(sender=SettingsModel)
def setup_file_logging(model_class: type, instance: SettingsModel, created: bool) -> None:
    # Also runs at startup, since init_db() saves every setting.
    if instance.key == 'enable_file_logging':
        set_file_logging(bool(instance.value))


def cleanup_db() -> None:
    # Clean up database
    DB.execute_sql("VACUUM")
    DB.close()


def recover_interrupted_jobs() -> None:
    """Runs still marked as running at startup belong to a process that died mid-backup."""
    try:
        JobModel.update(
            status=JobModel.Status.INTERRUPTED.value,
            reason='Vorta stopped while this backup was running.',
        ).where(JobModel.status == JobModel.Status.RUNNING.value).execute()
    except pw.PeeweeException:
        logger.warning('Could not recover interrupted jobs.', exc_info=True)


def file_logging_enabled(con: pw.SqliteDatabase) -> bool:
    """Read the `enable_file_logging` setting before init_db(), so the logger is set up correctly from the start."""
    if not os.path.exists(con.database):  # first start: let init_db() create the file with the right umask
        return True
    try:
        with con.connection_context(), con.bind_ctx([SettingsModel]):
            enabled = (
                SettingsModel.select(SettingsModel.value).where(SettingsModel.key == 'enable_file_logging').scalar()
            )
    except pw.PeeweeException:  # settings table not created yet
        return True
    return enabled is None or bool(enabled)


def init_db(con: pw.SqliteDatabase | None = None) -> None:
    if con is not None:
        os.umask(0o0077)
        DB.initialize(con)
        DB.connect()
    DB.create_tables(
        [
            RepoModel,
            RepoPassword,
            BackupProfileModel,
            SourceFileModel,
            SettingsModel,
            ArchiveModel,
            WifiSettingModel,
            EventLogModel,
            JobModel,
            SchedulerPauseModel,
            SchemaVersion,
            ExclusionModel,
        ]
    )

    # Delete old log entries after 6 months.
    # The last `create` command of each profile must not be deleted
    # since the scheduler uses it to determine the last backup time.
    last_backups_per_profile = (
        EventLogModel.select(EventLogModel.profile, fn.MAX(EventLogModel.start_time))
        .where(EventLogModel.subcommand == 'create')
        .group_by(EventLogModel.profile)
    )
    last_scheduled_backups_per_profile = (
        EventLogModel.select(EventLogModel.profile, fn.MAX(EventLogModel.start_time))
        .where(EventLogModel.subcommand == 'create', EventLogModel.category == 'scheduled')
        .group_by(EventLogModel.profile)
    )

    six_months_ago = datetime.now() - timedelta(days=6 * 30)
    entry = Tuple(EventLogModel.profile, EventLogModel.start_time)
    EventLogModel.delete().where(
        EventLogModel.start_time < six_months_ago,
        entry.not_in(last_backups_per_profile),
        entry.not_in(last_scheduled_backups_per_profile),
    ).execute()

    # Delete old job records after 6 months. Nothing derives scheduling state from them.
    JobModel.delete().where(JobModel.created_at < six_months_ago).execute()

    recover_interrupted_jobs()

    # Migrations
    current_schema, created = SchemaVersion.get_or_create(id=1, defaults={'version': SCHEMA_VERSION})
    current_schema.save()
    if created or current_schema.version == SCHEMA_VERSION:
        pass
    elif con is not None:
        backup_current_db(current_schema.version)
        run_migrations(current_schema, con)

    # Create missing settings and update labels.
    # Leave only setting values untouched.
    for setting in get_misc_settings():
        s, created = SettingsModel.get_or_create(key=setting['key'], defaults=setting)
        s.label = setting['label']
        s.type = setting['type']

        if 'group' in setting:
            s.group = setting['group']
        if 'tooltip' in setting:
            s.tooltip = setting['tooltip']

        s.save()


def backup_current_db(schema_version: int) -> None:
    """
    Creates a backup copy of settings.db
    """

    assert config.SETTINGS_DIR is not None
    timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
    backup_file_name = f'settings_v{schema_version}_{timestamp}.db'
    shutil.copy(config.SETTINGS_DIR / 'settings.db', config.SETTINGS_DIR / backup_file_name)
