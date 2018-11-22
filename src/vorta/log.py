"""
Set up logging to user log dir. Uses the platform's default location:

- linux: $HOME/.cache/Vorta/log
- macOS: $HOME/Library/Logs/Vorta

"""

import os
import logging
from .config import LOG_DIR

logger = logging.getLogger('vorta')
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler(os.path.join(LOG_DIR, 'vorta.log'))
# fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
