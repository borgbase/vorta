import os
import socket
import sys

import pytest
from peewee import SqliteDatabase

import vorta
import vorta.application
import vorta.borg.jobs_manager

# Store original getaddrinfo before any mocking
_original_getaddrinfo = socket.getaddrinfo


def pytest_configure(config):
    sys._called_from_test = True
    pytest._wait_defaults = {'timeout': 20000}
    os.environ['LANG'] = 'en'  # Ensure we test an English UI

    # Mock socket.getaddrinfo globally to avoid slow DNS lookups on CI.
    # The _getfqdn() function in utils.py uses this for archive name templates,
    # and DNS lookups can timeout (10s each) on macOS CI runners.
    def fast_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        # For AI_CANONNAME requests (used by _getfqdn), return hostname as canonical name
        if flags & socket.AI_CANONNAME:
            return [(socket.AF_INET, socket.SOCK_DGRAM, 0, host, ('127.0.0.1', 0))]
        return _original_getaddrinfo(host, port, family, type, proto, flags)

    socket.getaddrinfo = fast_getaddrinfo


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
