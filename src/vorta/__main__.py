import sys
import os
import peewee

import vorta.models
from vorta.application import VortaApp
from vorta.config import SETTINGS_DIR
from vorta._version import __version__


def main():
    # Send crashes to Sentry
    if not os.environ.get('NO_SENTRY', False):
        import sentry_sdk
        sentry_sdk.init("https://a4a23df3e44743d5b5c5f06417a9a809@sentry.io/1311799",
                        release=__version__)

    # Init database
    sqlite_db = peewee.SqliteDatabase(os.path.join(SETTINGS_DIR, 'settings.db'))
    vorta.models.init_db(sqlite_db)

    app = VortaApp(sys.argv)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
