"""
Set up logging to user log dir. Uses the platform's default location:

- linux: $HOME/.cache/Vorta/log
- macOS: $HOME/Library/Logs/Vorta

"""

import logging
from logging.handlers import TimedRotatingFileHandler

from vorta import config

logger = logging.getLogger()
file_handler: TimedRotatingFileHandler | None = None
console_handler: logging.StreamHandler | None = None
in_background = False


def init_logger(background=False, log_to_file=True):
    global file_handler, console_handler, in_background
    logger.setLevel(logging.DEBUG)
    logging.getLogger('peewee').setLevel(logging.INFO)
    logging.getLogger('PyQt6').setLevel(logging.INFO)

    # create logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # create handlers
    # delay=True: don't create the file until the first record is written,
    # so no file is left behind if file logging is disabled in the settings.
    fh = TimedRotatingFileHandler(config.LOG_DIR / 'vorta.log', when='d', interval=1, backupCount=5, delay=True)
    # ensure ".log" suffix
    fh.namer = lambda log_name: log_name.replace(".log", "") + ".log"
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    file_handler = fh

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    console_handler = ch
    in_background = background

    if not background:  # log to console, when running in foreground
        logger.addHandler(ch)

    set_file_logging(log_to_file)


def set_file_logging(enabled: bool) -> None:
    """Add or remove the log file handler, depending on the `enable_file_logging` setting.

    In background mode there is no console handler, so it is added while file logging is off.
    Otherwise nothing would be logged at all.
    """
    if file_handler is None:  # logger not initialized, e.g. in tests
        return
    if enabled:
        if file_handler not in logger.handlers:
            logger.addHandler(file_handler)
        if in_background and console_handler is not None:
            logger.removeHandler(console_handler)
    else:
        logger.removeHandler(file_handler)
        file_handler.close()
        if in_background and console_handler is not None and console_handler not in logger.handlers:
            logger.addHandler(console_handler)
