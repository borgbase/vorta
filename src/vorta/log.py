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

# create handlers
fh = logging.FileHandler(os.path.join(LOG_DIR, 'vorta.log'))
# fh.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)

# create logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# apply formatter
fh.setFormatter(formatter)
ch.setFormatter(formatter)

# add handlers
logger.addHandler(fh)
logger.addHandler(ch)
