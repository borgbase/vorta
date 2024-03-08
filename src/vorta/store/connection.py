import os
import shutil
from datetime import datetime, timedelta

from peewee import Tuple, fn
from playhouse import signals

from vorta import config
from vorta.autostart import open_app_at_startup

from .migrations import run_migrations
from .models import (
    DB,
    ArchiveModel,
    BackupProfileModel,
    EventLogModel,
    ExclusionModel,
    RepoModel,
    RepoPassword,
    SchemaVersion,
    SettingsModel,
    SourceFileModel,
    WifiSettingModel,
)
from .settings import get_misc_settings

SCHEMA_VERSION = 22


@signals.post_save(sender=SettingsModel)
def setup_autostart(model_class, instance, created):
    if instance.key == 'autostart':
        open_app_at_startup(instance.value)


def cleanup_db():
    # Clean up database
    DB.execute_sql("VACUUM")
    DB.close()


def init_db(con=None):
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

    three_months_ago = datetime.now() - timedelta(days=6 * 30)
    entry = Tuple(EventLogModel.profile, EventLogModel.start_time)
    EventLogModel.delete().where(
        EventLogModel.start_time < three_months_ago,
        entry.not_in(last_backups_per_profile),
        entry.not_in(last_scheduled_backups_per_profile),
    ).execute()

    # Migrations
    current_schema, created = SchemaVersion.get_or_create(id=1, defaults={'version': SCHEMA_VERSION})
    current_schema.save()
    if created or current_schema.version == SCHEMA_VERSION:
        pass
    else:
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


def backup_current_db(schema_version):
    """
    Creates a backup copy of settings.db
    """

    timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
    backup_file_name = f'settings_v{schema_version}_{timestamp}.db'
    shutil.copy(config.SETTINGS_DIR / 'settings.db', config.SETTINGS_DIR / backup_file_name)
