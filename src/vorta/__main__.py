import os
import signal
import sys

import peewee
from vorta._version import __version__
from vorta.i18n import trans_late, translate
from vorta.config import SETTINGS_DIR
from vorta.log import init_logger, logger
from vorta.models import init_db
from vorta.updater import get_updater
from vorta.utils import parse_args


def main():
    def exception_handler(type, value, tb):
        from traceback import format_exception
        from PyQt5.QtWidgets import QMessageBox
        logger.critical("Uncaught exception, file a report at https://github.com/borgbase/vorta/issues/new",
                        exc_info=(type, value, tb))
        full_exception = ''.join(format_exception(type, value, tb))
        title = trans_late('app', 'Fatal Error')
        error_message = trans_late('app', 'Uncaught exception, please file a report with this text at\n'
                                   'https://github.com/borgbase/vorta/issues/new\n')
        if app:
            QMessageBox.critical(None,
                                 translate('app', title),
                                 translate('app', error_message) + full_exception)
        else:
            # Crashed before app startup, cannot translate
            sys.exit(1)

    sys.excepthook = exception_handler
    app = None

    args = parse_args()
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # catch ctrl-c and exit

    want_version = getattr(args, 'version', False)
    want_background = getattr(args, 'daemonize', False)

    if want_version:
        print(f"Vorta {__version__}")
        sys.exit()

    if want_background:
        if os.fork():
            sys.exit()

    init_logger(background=want_background)

    # Init database
    sqlite_db = peewee.SqliteDatabase(os.path.join(SETTINGS_DIR, 'settings.db'), pragmas={'journal_mode': 'wal', })
    init_db(sqlite_db)

    # Init app after database is available
    from vorta.application import VortaApp
    app = VortaApp(sys.argv, single_app=args.profile is None)
    app.updater = get_updater()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
