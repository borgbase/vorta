import sys
import os
import peewee

import vorta.models
from vorta.application import VortaApp
from vorta.config import SETTINGS_DIR
import vorta.updater


def main():
    # Send crashes to Sentry.
    if not os.environ.get('NO_SENTRY', False):
        import vorta.sentry

    # Init database
    sqlite_db = peewee.SqliteDatabase(os.path.join(SETTINGS_DIR, 'settings.db'))
    vorta.models.init_db(sqlite_db)

    app = VortaApp(sys.argv, single_app=True)
    app.updater = vorta.updater.get_updater()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
