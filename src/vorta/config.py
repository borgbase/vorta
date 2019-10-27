import appdirs
import os

APP_NAME = 'Vorta'
APP_AUTHOR = 'BorgBase'
dirs = appdirs.AppDirs(APP_NAME, APP_AUTHOR)
SETTINGS_DIR = dirs.user_data_dir
LOG_DIR = dirs.user_log_dir
STATE_DIR = dirs.user_state_dir
DB_PATH = os.path.join(SETTINGS_DIR, 'settings.db')

if not os.path.exists(SETTINGS_DIR):
    os.makedirs(SETTINGS_DIR)

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

if not os.path.exists(STATE_DIR):
    os.makedirs(STATE_DIR)
