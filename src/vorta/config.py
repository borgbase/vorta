from pathlib import Path

import platformdirs

APP_NAME = 'Vorta'
APP_AUTHOR = 'BorgBase'
APP_ID_DARWIN = 'com.borgbase.client.macos'
SETTINGS_DIR = None
LOG_DIR = None
CACHE_DIR = None
TEMP_DIR = None
PROFILE_BOOTSTRAP_FILE = None


def default_dev_dir():
    return Path(__file__).parent.parent.parent / '.dev_config'


def init_from_platformdirs():
    dirs = platformdirs.PlatformDirs(APP_NAME, APP_AUTHOR)
    init(dirs.user_data_path, dirs.user_log_path, dirs.user_cache_path, dirs.user_cache_path / 'tmp', Path.home())


def init_dev_mode(dir):
    dir_full_path = Path(dir).resolve()
    init(
        dir_full_path / 'settings',
        dir_full_path / 'logs',
        dir_full_path / 'cache',
        dir_full_path / 'tmp',
        dir_full_path,
    )


def init(settings, logs, cache, tmp, bootstrap):
    global SETTINGS_DIR
    global LOG_DIR
    global CACHE_DIR
    global TEMP_DIR
    global PROFILE_BOOTSTRAP_FILE
    SETTINGS_DIR = settings
    LOG_DIR = logs
    CACHE_DIR = cache
    TEMP_DIR = tmp
    PROFILE_BOOTSTRAP_FILE = bootstrap / '.vorta-init.json'
    ensure_dirs()


def ensure_dirs():
    # ensure directories exist
    for dir in (SETTINGS_DIR, LOG_DIR, CACHE_DIR, TEMP_DIR):
        dir.mkdir(parents=True, exist_ok=True)


# Make sure that the config values are valid
init_from_platformdirs()
