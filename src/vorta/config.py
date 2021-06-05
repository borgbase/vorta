import os
from pathlib import Path
import appdirs

APP_NAME = 'Vorta'
APP_AUTHOR = 'BorgBase'
APP_ID_DARWIN = 'com.borgbase.client.macos'
dirs = appdirs.AppDirs(APP_NAME, APP_AUTHOR)
SETTINGS_DIR = dirs.user_data_dir
LOG_DIR = dirs.user_log_dir
CACHE_DIR = dirs.user_cache_dir
TEMP_DIR = os.path.join(CACHE_DIR, "tmp")
PROFILE_BOOTSTRAP_FILE = Path.home() / '.vorta-init.json'

if not os.path.exists(SETTINGS_DIR):
    os.makedirs(SETTINGS_DIR)

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)
