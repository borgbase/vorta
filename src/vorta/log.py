"""
Set up logging to user log dir. Uses the platform's default location:

- linux: $HOME/.cache/Vorta/log
- macOS: $HOME/Library/Logs/Vorta

"""

import logging
from logging.handlers import TimedRotatingFileHandler

from vorta import config

logger = logging.getLogger()

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

fh = TimedRotatingFileHandler(config.LOG_DIR / 'vorta.log', when='d', interval=1, backupCount=5)
fh.namer = lambda log_name: log_name.replace(".log", "") + ".log"
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)


def init_logger(background=False):
    logger.setLevel(logging.DEBUG)
    logging.getLogger('peewee').setLevel(logging.INFO)
    logging.getLogger('PyQt6').setLevel(logging.INFO)

    # Enable file logging by default at the start, since SettingsModel isn't initialised
    toggle_file_logging(True)

    if background:
        pass
    else:  # log to console, when running in foreground
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        logger.addHandler(ch)


def init_file_logging():
    """
    Decides file logging based on the user's preference
    """
    from vorta.store.models import SettingsModel

    toggle_file_logging(SettingsModel.get(key='enable_logging_to_file').value)


def toggle_file_logging(should_log_to_file):
    """
    Enables file logging according to the input
    """

    if should_log_to_file:
        logger.addHandler(fh)
    else:
        logger.removeHandler(fh)
