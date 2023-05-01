from pathlib import Path

import platformdirs

APP_NAME = 'Vorta'
APP_AUTHOR = 'BorgBase'
APP_ID_DARWIN = 'com.borgbase.client.macos'
dirs = platformdirs.PlatformDirs(APP_NAME, APP_AUTHOR)
SETTINGS_DIR = dirs.user_data_path
LOG_DIR = dirs.user_log_path
CACHE_DIR = dirs.user_cache_path
TEMP_DIR = CACHE_DIR / "tmp"
PROFILE_BOOTSTRAP_FILE = Path.home() / '.vorta-init.json'


# ensure directories exist
for dir in (SETTINGS_DIR, LOG_DIR, CACHE_DIR, TEMP_DIR):
    dir.mkdir(parents=True, exist_ok=True)
