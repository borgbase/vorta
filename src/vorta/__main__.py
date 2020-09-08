import os
import signal
import sys

import peewee
from vorta._version import __version__
from vorta.config import SETTINGS_DIR, LOG_DIR
from vorta.i18n import translate
from vorta.log import init_logger, logger
from vorta.models import init_db
from vorta.updater import get_updater
from vorta.utils import parse_args


def main():
    def exception_handler(type, value, tb):
        # https://stackoverflow.com/questions/49065371/why-does-sys-excepthook-behave-differently-when-wrapped
        # This double prints the exception, want to only print the log entry
        logger.critical("Uncaught exception, file a report at https://github.com/borgbase/vorta/issues/new:",
                        exc_info=(type, value, tb))
        sys.__excepthook__(type, value, tb)
        if app:
            from vorta.notifications import VortaNotifications
            notifier = VortaNotifications.pick()
            notifier.deliver(translate('messages', 'Application Error'),
                             translate('messages', "Uncaught exception, see log in {} for details".format(LOG_DIR)),
                             level='exception')

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
