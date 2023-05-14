from vorta.log import LogTimedRotatingFileHandler


def test_log_file_suffix():
    """Ensure log files always have '.log' suffix."""

    handler = LogTimedRotatingFileHandler('mylog.log', when='d', interval=1, backupCount=5)
    assert handler.suffix.endswith('.log')
