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

# Current schema version. Increment this when making changes to the database schema.
SCHEMA_VERSION = 23

# Event retention period in months
EVENT_LOG_RETENTION_MONTHS = 6

"""
Database Management Module
--------------------------
This module handles database initialization, migrations, and maintenance for the Vorta application.
It manages the SQLite database that stores backup profiles, repositories, settings, and event logs.
"""

@signals.post_save(sender=SettingsModel)
def setup_autostart(model_class, instance, created):
    """
    Signal handler to enable/disable application autostart based on settings changes.
    
    Args:
        model_class: The model class that triggered the signal
        instance: The model instance that was saved
        created: Boolean indicating if this is a new instance
    """
    if instance.key == 'autostart':
        open_app_at_startup(instance.value)


def cleanup_db():
    """
    Perform database cleanup operations.
    
    This function optimizes the database by running VACUUM command and
    ensures connections are properly closed.
    """
    # Clean up database
    DB.execute_sql("VACUUM")
    DB.close()


def backup_current_db(schema_version):
    """
    Creates a backup copy of the settings database before migrations.
    
    Args:
        schema_version (int): The current schema version before migration
    
    Returns:
        str: Path to the backup file
    """
    timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
    backup_file_name = f'settings_v{schema_version}_{timestamp}.db'
    backup_path = config.SETTINGS_DIR / backup_file_name
    shutil.copy(config.SETTINGS_DIR / 'settings.db', backup_path)
    return str(backup_path)


def _purge_old_event_logs():
    """
    Delete old event log entries while preserving important records.
    
    This function removes log entries older than the retention period,
    except for the last backup of each profile which is needed for scheduling.
    """
    # Find the last backup for each profile
    last_backups_per_profile = (
        EventLogModel.select(EventLogModel.profile, fn.MAX(EventLogModel.start_time))
        .where(EventLogModel.subcommand == 'create')
        .group_by(EventLogModel.profile)
    )
    
    # Find the last scheduled backup for each profile
    last_scheduled_backups_per_profile = (
        EventLogModel.select(EventLogModel.profile, fn.MAX(EventLogModel.start_time))
        .where(EventLogModel.subcommand == 'create', EventLogModel.category == 'scheduled')
        .group_by(EventLogModel.profile)
    )
    
    # Calculate cutoff date
    retention_days = EVENT_LOG_RETENTION_MONTHS * 30
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    # Create tuple for comparison
    entry = Tuple(EventLogModel.profile, EventLogModel.start_time)
    
    # Delete old entries except important ones
    deleted_count = EventLogModel.delete().where(
        EventLogModel.start_time < cutoff_date,
        entry.not_in(last_backups_per_profile),
        entry.not_in(last_scheduled_backups_per_profile),
    ).execute()
    
    return deleted_count


def _update_settings():
    """
    Update application settings in the database.
    
    This function creates missing settings and updates labels and metadata
    while preserving user-configured values.
    """
    updated_count = 0
    created_count = 0
    
    for setting in get_misc_settings():
        s, created = SettingsModel.get_or_create(key=setting['key'], defaults=setting)
        
        if created:
            created_count += 1
        else:
            # Update metadata but preserve the value
            s.label = setting['label']
            s.type = setting['type']
            if 'group' in setting:
                s.group = setting['group']
            if 'tooltip' in setting:
                s.tooltip = setting['tooltip']
            s.save()
            updated_count += 1
            
    return created_count, updated_count


def init_db(con=None):
    """
    Initialize the database and perform setup operations.
    
    This function creates necessary tables, runs migrations if needed,
    cleans up old data, and ensures settings are properly initialized.
    
    Args:
        con (SqliteDatabase, optional): Database connection. If None, uses the default connection.
    
    Returns:
        dict: Summary of operations performed
    """
    operations = {
        'tables_created': False,
        'migrations_run': False,
        'db_backed_up': False,
        'logs_purged': 0,
        'settings_created': 0,
        'settings_updated': 0
    }
    
    # Initialize database connection if provided
    if con is not None:
        # Set umask to ensure database file has restricted permissions
        os.umask(0o0077)
        DB.initialize(con)
        DB.connect()
    
    # Create tables if they don't exist
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
    operations['tables_created'] = True
    
    # Handle schema migrations
    current_schema, created = SchemaVersion.get_or_create(id=1, defaults={'version': SCHEMA_VERSION})
    
    if not created and current_schema.version != SCHEMA_VERSION:
        operations['db_backed_up'] = backup_current_db(current_schema.version)
        run_migrations(current_schema, con)
        operations['migrations_run'] = True
    
    # Delete old log entries
    operations['logs_purged'] = _purge_old_event_logs()
    
    # Update settings
    operations['settings_created'], operations['settings_updated'] = _update_settings()
    
    return operations
