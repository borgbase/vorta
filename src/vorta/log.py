"""
Set up logging to user log dir. Uses the platform's default location:

- linux: $HOME/.cache/Vorta/log
- macOS: $HOME/Library/Logs/Vorta

"""

import logging
from logging.handlers import TimedRotatingFileHandler

from .config import LOG_DIR

logger = logging.getLogger()


class LogTimedRotatingFileHandler(TimedRotatingFileHandler):
    """Create subclass of TimedRotatingFileHandler that always appends '.log' to log files."""

    def __init__(self, filename, when='d', interval=1, backupCount=5, encoding=None, delay=False, utc=False):
        super().__init__(
            filename, when=when, interval=interval, backupCount=backupCount, encoding=encoding, delay=delay, utc=utc
        )
        self.suffix += '.log'


def init_logger(background=False):
    logger.setLevel(logging.DEBUG)
    logging.getLogger('peewee').setLevel(logging.INFO)
    logging.getLogger('PyQt6').setLevel(logging.INFO)

    # create logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # create handlers
    fh = LogTimedRotatingFileHandler(LOG_DIR / 'vorta.log', when='d', interval=1, backupCount=5)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    if background:
        pass
    else:  # log to console, when running in foreground
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
