import os
import signal
import sys

import peewee
from vorta._version import __version__
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
        if app and app.main_window:
            full_exception = ''.join(format_exception(type, value, tb))
            try:
                QMessageBox.critical(app.main_window,
                                     app.main_window.tr("Fatal Error"),
                                     app.main_window.tr(
                                         "Uncaught exception, please file a report with this text at\n"
                                         "https://github.com/borgbase/vorta/issues/new\n") + full_exception)
            except RuntimeError:
                # Window is closed, only log is available, exit to prevent freezing
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
    sqlite_db = peewee.SqliteDatabase(os.path.join(SETTINGS_DIR, 'settings.db'))
    init_db(sqlite_db)

    # Init app after database is available
    from vorta.application import VortaApp
    app = VortaApp(sys.argv, single_app=True)
    app.updater = get_updater()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
