"""
Set up logging to user log dir. Uses the platform's default location:

- linux: $HOME/.cache/Vorta/log
- macOS: $HOME/Library/Logs/Vorta

"""

import os
import logging
from logging.handlers import TimedRotatingFileHandler
from .config import LOG_DIR

logger = logging.getLogger()


def init_logger(background=False):
    logger.setLevel(logging.DEBUG)
    logging.getLogger('peewee').setLevel(logging.INFO)
    logging.getLogger('apscheduler').setLevel(logging.INFO)
    logging.getLogger('PyQt5').setLevel(logging.INFO)

    # create logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # create handlers
    fh = TimedRotatingFileHandler(os.path.join(LOG_DIR, 'vorta.log'),
                                  when='d',
                                  interval=1,
                                  backupCount=5)
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
