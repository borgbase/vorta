import sys
import os
import peewee

from vorta.models import init_db
from vorta.application import VortaApp
from vorta.config import SETTINGS_DIR
from vorta.updater import get_updater
from vorta.utils import parse_args
from vorta.log import init_logger


def main():
    args = parse_args()

    frozen_binary = getattr(sys, 'frozen', False)
    need_foreground = frozen_binary and sys.platform in ('darwin', 'linux')
    want_foreground = getattr(args, 'foreground', False)
    if not (want_foreground or need_foreground):
        print('Forking to background (see system tray).')
        if os.fork():
            sys.exit()

    init_logger(foreground=want_foreground)

    # Init database
    sqlite_db = peewee.SqliteDatabase(os.path.join(SETTINGS_DIR, 'settings.db'))
    init_db(sqlite_db)

    app = VortaApp(sys.argv, single_app=True)
    app.updater = get_updater()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
