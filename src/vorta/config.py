import appdirs
import os
import shutil

APP_NAME = 'Vorta'
APP_AUTHOR = 'BorgBase'
SETTINGS_DIR = appdirs.user_data_dir(APP_NAME, APP_AUTHOR)

if not os.path.exists(SETTINGS_DIR):
    os.makedirs(SETTINGS_DIR)

def remove_config():
    shutil.rmtree(SETTINGS_DIR)
