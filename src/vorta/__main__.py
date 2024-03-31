import os
import signal
import sys

from peewee import SqliteDatabase

# Need to import config as a whole module instead of individual variables
# because we will be overriding the modules variables
from vorta import config
from vorta._version import __version__
from vorta.log import init_logger, logger
from vorta.store.connection import init_db
from vorta.updater import get_updater
from vorta.utils import DEFAULT_DIR_FLAG, parse_args
from vorta.views.exception_dialog import ExceptionDialog


def main():
    def exception_handler(type, value, tb):
        from traceback import format_exception

        logger.critical(
            "Uncaught exception, file a report at https://github.com/borgbase/vorta/issues/new/choose",
            exc_info=(type, value, tb),
        )
        full_exception = ''.join(format_exception(type, value, tb))

        if app:
            exception_dialog = ExceptionDialog(full_exception)
            exception_dialog.show()
            exception_dialog.raise_()
            exception_dialog.activateWindow()
            exception_dialog.exec()
        else:
            # Crashed before app startup, cannot translate
            sys.exit(1)

    sys.excepthook = exception_handler
    app = None

    args = parse_args()
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # catch ctrl-c and exit

    want_version = getattr(args, 'version', False)
    want_background = getattr(args, 'daemonize', False)
    want_development = getattr(args, 'development', False)

    if want_version:
        print(f"Vorta {__version__}")  # noqa: T201
        sys.exit()

    if want_background:
        if os.fork():
            sys.exit()

    if want_development:
        # if we're using the default dev dir
        if want_development is DEFAULT_DIR_FLAG:
            config.init_dev_mode(config.default_dev_dir())
        else:
            # if we're not using the default dev dir and
            # instead we're using whatever dir is passed as an argument
            config.init_dev_mode(want_development)

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
