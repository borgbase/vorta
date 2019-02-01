"""
Set up logging to user log dir. Uses the platform's default location:

- linux: $HOME/.cache/Vorta/log
- macOS: $HOME/Library/Logs/Vorta

"""

import os
import logging
from .config import LOG_DIR

logger = logging.getLogger()


def init_logger(foreground=False):
    logger.setLevel(logging.DEBUG)
    logging.getLogger('peewee').setLevel(logging.INFO)
    logging.getLogger('apscheduler').setLevel(logging.INFO)
    logging.getLogger('PyQt5').setLevel(logging.INFO)

    # create logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # create handlers
    fh = logging.FileHandler(os.path.join(LOG_DIR, 'vorta.log'))
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    if foreground:  # log to console, when running in foreground
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
