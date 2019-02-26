import sys
import os
import peewee
import signal

from vorta.models import init_db
from vorta.config import SETTINGS_DIR
from vorta.updater import get_updater
from vorta.utils import parse_args
from vorta.log import init_logger


def main():
    args = parse_args()
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # catch ctrl-c and exit

    frozen_binary = getattr(sys, 'frozen', False)
    want_foreground = getattr(args, 'foreground', False)
    # We assume that a frozen binary is a fat single-file binary made with
    # PyInstaller. These are not compatible with forking into background here:
    if not (want_foreground or frozen_binary):
        print('Forking to background (see system tray).')
        if os.fork():
            sys.exit()

    init_logger(foreground=want_foreground)

    # Init database
    sqlite_db = peewee.SqliteDatabase(os.path.join(SETTINGS_DIR, 'settings.db'))
    init_db(sqlite_db)

    # Init app after database is available
    from vorta.application import VortaApp
    app = VortaApp(sys.argv, single_app=True)
    app.updater = get_updater()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
