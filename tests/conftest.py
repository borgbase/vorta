import os
import socket
import sys
from unittest.mock import Mock

import pytest
from peewee import SqliteDatabase

import vorta
import vorta.application
import vorta.borg.jobs_manager


def pytest_configure(config):
    pytest._wait_defaults = {'timeout': 20000}
    os.environ['LANG'] = 'en'  # Ensure we test an English UI

    # Disable pytest-qt's processEvents() calls on macOS to prevent hangs.
    # See: https://github.com/pytest-dev/pytest-qt/issues/223
    if sys.platform == 'darwin':
        try:
            import pytestqt.plugin

            pytestqt.plugin._process_events = lambda: None
        except (ImportError, AttributeError):
            pass

    # Mock D-Bus system bus to prevent hangs in CI (scheduler.py, network_manager.py)
    try:
        from PyQt6 import QtDBus

        _original_system_bus = QtDBus.QDBusConnection.systemBus

        def _mock_system_bus():
            mock_bus = Mock()
            mock_bus.isConnected.return_value = False
            return mock_bus

        QtDBus.QDBusConnection.systemBus = staticmethod(_mock_system_bus)
    except ImportError:
        pass

    # Mock DNS lookups to prevent timeouts in CI (utils._getfqdn)
    _original_getaddrinfo = socket.getaddrinfo
    socket.getaddrinfo = lambda *args, **kwargs: []

    # Mock WiFi enumeration to prevent hangs on headless CI (utils.get_sorted_wifis)
    import vorta.utils

    _original_get_network_status_monitor = vorta.utils.get_network_status_monitor

    def _mock_get_network_status_monitor():
        mock_monitor = Mock()
        mock_monitor.get_known_wifis.return_value = []
        return mock_monitor

    vorta.utils.get_network_status_monitor = _mock_get_network_status_monitor


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
