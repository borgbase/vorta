import os
from datetime import datetime, timedelta

from playhouse import signals

from vorta.autostart import open_app_at_startup

from .migrations import run_migrations
from .models import (DB, ArchiveModel, BackupProfileModel, EventLogModel,
                     RepoModel, RepoPassword, SchemaVersion, SettingsModel,
                     SourceFileModel, WifiSettingModel)
from .settings import get_misc_settings

SCHEMA_VERSION = 19


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
    DB.create_tables([RepoModel, RepoPassword, BackupProfileModel, SourceFileModel, SettingsModel,
                      ArchiveModel, WifiSettingModel, EventLogModel, SchemaVersion])

    # Delete old log entries after 3 months.
    three_months_ago = datetime.now() - timedelta(days=180)
    EventLogModel.delete().where(EventLogModel.start_time < three_months_ago)

    # Migrations
    current_schema, created = SchemaVersion.get_or_create(id=1, defaults={'version': SCHEMA_VERSION})
    current_schema.save()
    if created or current_schema.version == SCHEMA_VERSION:
        pass
    else:
        run_migrations(current_schema, con)

    # Create missing settings and update labels.
    # Leave only setting values untouched.
    for setting in get_misc_settings():
        s, created = SettingsModel.get_or_create(key=setting['key'], defaults=setting)
        s.label = setting['label']
        s.type = setting['type']

        if 'group' in setting:
            s.group = setting['group']

        s.save()

    # Delete old log entries after 3 months.
    three_months_ago = datetime.now() - timedelta(days=3)
    EventLogModel.delete().where(EventLogModel.start_time < three_months_ago).execute()
