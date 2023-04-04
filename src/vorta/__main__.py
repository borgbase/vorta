import os
import signal
import sys
from pathlib import Path
from peewee import SqliteDatabase

# Need to import config as a whole module instead of individual variables
# because we will be overriding the modules variables
import vorta.config as config
from vorta._version import __version__
from vorta.i18n import trans_late, translate
from vorta.log import init_logger, logger
from vorta.store.connection import init_db
from vorta.updater import get_updater
from vorta.utils import DEFAULT_DIR_FLAG, parse_args


def main():
    def exception_handler(type, value, tb):
        from traceback import format_exception
        from PyQt5.QtWidgets import QMessageBox

        logger.critical(
            "Uncaught exception, file a report at https://github.com/borgbase/vorta/issues/new/choose",
            exc_info=(type, value, tb),
        )
        full_exception = ''.join(format_exception(type, value, tb))
        title = trans_late('app', 'Fatal Error')
        error_message = trans_late(
            'app',
            'Uncaught exception, please file a report with this text at\n'
            'https://github.com/borgbase/vorta/issues/new\n',
        )
        if app:
            QMessageBox.critical(
                None,
                translate('app', title),
                translate('app', error_message) + full_exception,
            )
        else:
            # Crashed before app startup, cannot translate
            sys.exit(1)

    sys.excepthook = exception_handler
    app = None

    args = parse_args()
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # catch ctrl-c and exit

    want_version = getattr(args, 'version', False)
    want_background = getattr(args, 'daemonize', False)
    want_development = getattr(args, 'development')

    if want_version:
        print(f"Vorta {__version__}")
        sys.exit()

    if want_background:
        if os.fork():
            sys.exit()

    # want_development is None when flag is not called
    # it's set to the default directory when flag is called without an argument
    # and it's set to the flag's argument if the flag has one
    if want_development:
        if want_development == DEFAULT_DIR_FLAG:
            pass
        else:
            config.DEV_MODE_DIR = Path(want_development)

        if not os.path.exists(config.DEV_MODE_DIR):
            os.makedirs(config.DEV_MODE_DIR)

        config.SETTINGS_DIR = config.DEV_MODE_DIR / 'settings'
        if not os.path.exists(config.SETTINGS_DIR):
            os.makedirs(config.SETTINGS_DIR)

        config.LOG_DIR = config.DEV_MODE_DIR / 'logs'
        if not os.path.exists(config.LOG_DIR):
            os.makedirs(config.LOG_DIR)

        config.CACHE_DIR = config.DEV_MODE_DIR / 'cache'
        if not os.path.exists(config.CACHE_DIR):
            os.makedirs(config.CACHE_DIR)

        config.TEMP_DIR = config.CACHE_DIR / 'tmp'
        if not os.path.exists(config.TEMP_DIR):
            os.makedirs(config.TEMP_DIR)

        config.PROFILE_BOOTSTRAP_FILE = config.DEV_MODE_DIR / '.vorta-init.json'

    # except Exception as exception:
    #     print("That's an invalid path for a dir \n", exception)

    init_logger(background=want_background)

    # Init database
    sqlite_db = SqliteDatabase(
        config.SETTINGS_DIR / 'settings.db',
        pragmas={
            'journal_mode': 'wal',
        },
    )
    init_db(sqlite_db)

    # Init app after database is available
    from vorta.application import VortaApp

    app = VortaApp(sys.argv, single_app=args.profile is None)
    app.updater = get_updater()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
