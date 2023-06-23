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


def default_dev_dir() -> Path:
    """Returns a default dir for config files in the project's main folder"""
    return Path(__file__).parent.parent.parent / '.dev_config'


def init_from_platformdirs():
    """Initializes config dirs for system-wide use"""
    dirs = platformdirs.PlatformDirs(APP_NAME, APP_AUTHOR)
    init(dirs.user_data_path, dirs.user_log_path, dirs.user_cache_path, dirs.user_cache_path / 'tmp', Path.home())


def init_dev_mode(dir: Path):
    """Initializes config dirs for local use inside provided dir"""
    dir_full_path = Path(dir).resolve()
    init(
        dir_full_path / 'settings',
        dir_full_path / 'logs',
        dir_full_path / 'cache',
        dir_full_path / 'tmp',
        dir_full_path,
    )


def init(settings: Path, logs: Path, cache: Path, tmp: Path, bootstrap: Path):
    """Initializes config directories with provided paths"""
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
    """Creates config dirs and parent dirs if they don't exist"""
    # ensure directories exist
    for dir in (SETTINGS_DIR, LOG_DIR, CACHE_DIR, TEMP_DIR):
        dir.mkdir(parents=True, exist_ok=True)


# Make sure that the config values are valid
init_from_platformdirs()
