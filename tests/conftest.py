import os
import sys

import pytest
from peewee import SqliteDatabase

import vorta
import vorta.application
import vorta.borg.jobs_manager


def pytest_configure(config):
    sys._called_from_test = True
    pytest._wait_defaults = {'timeout': 20000}
    os.environ['LANG'] = 'en'  # Ensure we test an English UI

    # Patch _getfqdn to avoid slow DNS lookups on CI.
    # This is more targeted than mocking socket.getaddrinfo globally.
    import vorta.utils

    vorta.utils._getfqdn = lambda name="": name.strip() or 'localhost'


@pytest.fixture(scope='session')
def qapp(tmpdir_factory):
    # DB is required to init QApplication. New DB used for every test.
    tmp_db = tmpdir_factory.mktemp('Vorta').join('settings.sqlite')
    mock_db = SqliteDatabase(str(tmp_db))
    vorta.store.connection.init_db(mock_db)

    # Needs to be disabled before calling VortaApp()
    if sys.platform == 'darwin':
        cfg = vorta.store.models.SettingsModel.get(key='check_full_disk_access')
        cfg.value = False
        cfg.save()

    # Force use of DB keyring instead of system keyring to avoid keychain prompts during tests
    keyring_setting = vorta.store.models.SettingsModel.get(key='use_system_keyring')
    keyring_setting.value = False
    keyring_setting.save()

    from vorta.application import VortaApp

    qapp = VortaApp([])  # Only init QApplication once to avoid segfaults while testing.

    yield qapp
    mock_db.close()
    qapp.quit()
