import os
import signal
import sys

from vorta._version import __version__
from vorta.log import init_logger
from vorta.models import connect_db
from vorta.updater import get_updater
from vorta.utils import parse_args


def main():
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

    connect_db()

    # Init app after database is available
    from vorta.application import VortaApp
    app = VortaApp(sys.argv, single_app=True)
    app.updater = get_updater()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
