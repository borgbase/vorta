"""
Set up logging to user log dir. Uses the platform's default location:

- linux: $HOME/.cache/Vorta/log
- macOS: $HOME/Library/Logs/Vorta

"""

import logging
from logging.handlers import TimedRotatingFileHandler

from vorta import config

logger = logging.getLogger()


def init_logger(background=False):
    logger.setLevel(logging.DEBUG)
    logging.getLogger('peewee').setLevel(logging.INFO)
    logging.getLogger('PyQt6').setLevel(logging.INFO)

    # create logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # create handlers
    fh = TimedRotatingFileHandler(config.LOG_DIR / 'vorta.log', when='d', interval=1, backupCount=5)
    # ensure ".log" suffix
    fh.namer = lambda log_name: log_name.replace(".log", "") + ".log"
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
