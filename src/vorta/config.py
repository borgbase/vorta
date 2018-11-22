import appdirs
import os

APP_NAME = 'Vorta'
APP_AUTHOR = 'BorgBase'
dirs = appdirs.AppDirs(APP_NAME, APP_AUTHOR)
SETTINGS_DIR = dirs.user_data_dir
LOG_DIR = dirs.user_log_dir

if not os.path.exists(SETTINGS_DIR):
    os.makedirs(SETTINGS_DIR)

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
