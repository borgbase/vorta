import sys
import os
import peewee

import vorta.models
import vorta.migrations
from vorta.application import VortaApp
from vorta.config import SETTINGS_DIR

# Send crashes to Sentry
if getattr(sys, 'frozen', False):
    import sentry_sdk
    sentry_sdk.init("https://a4a23df3e44743d5b5c5f06417a9a809@sentry.io/1311799")

# Init database
sqlite_db = peewee.SqliteDatabase(os.path.join(SETTINGS_DIR, 'settings.db'))
vorta.models.init_db(sqlite_db)

# Run migrations
from peewee_migrate.cli import get_router
router = get_router(os.path.dirname(vorta.migrations.__file__), sqlite_db, True)
router.run()

app = VortaApp(sys.argv)
sys.exit(app.exec_())
