import sys
import os
import peewee

import vorta.models
from vorta.application import VortaApp
from vorta.config import SETTINGS_DIR

# Send crashes to Sentry
if getattr(sys, 'frozen', False):
    import sentry_sdk
    sentry_sdk.init("https://a4a23df3e44743d5b5c5f06417a9a809@sentry.io/1311799")

# Init database
sqlite_db = peewee.SqliteDatabase(os.path.join(SETTINGS_DIR, 'settings.db'))
vorta.models.init_db(sqlite_db)

app = VortaApp(sys.argv)
sys.exit(app.exec_())
