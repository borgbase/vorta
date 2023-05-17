import os
import tempfile
import time
from logging.handlers import TimedRotatingFileHandler

from vorta.log import log_namer


def test_log_namer():
    """Tests log_namer to ensure adding '.log' to end of filename did not break
    any other functionality, such as creating and rotating/deleting backups"""

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        log_dir = os.path.join(temp_dir, 'logs')
        os.makedirs(log_dir)

        # Create a handler and set its namer to the function we are testing
        # 'when' and 'backupCount' set to speed up test execution time
        handler = TimedRotatingFileHandler(os.path.join(log_dir, 'vorta.log'), when='s', interval=1, backupCount=3)
        handler.namer = log_namer

        # Test doRollover() which calls getFilesToDelete()
        # Both of these functions rely on 'namer' working as intended
        if handler.backupCount > 0:
            for i in range(handler.backupCount + 2):  # Run extra times to ensure proper rotation of excess backups
                handler.doRollover()
                if i == 0:
                    assert len(os.listdir(log_dir)) == 2  # Should keep initial backup + current log
                else:
                    if i < handler.backupCount:
                        assert len(os.listdir(log_dir)) == i + 1  # Should keep i backups + current log
                    else:
                        assert len(os.listdir(log_dir)) == handler.backupCount + 1  # Keeps backupCount backups + log

                for file in os.listdir(log_dir):
                    assert file.endswith('.log')  # Checks that 'namer' is working as intended

                time.sleep(1)  # Need 1s between logs or they are overwritten
