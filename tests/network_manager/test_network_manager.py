from datetime import datetime
from unittest.mock import MagicMock

import pytest
from vorta.network_status.abc import SystemWifiInfo
from vorta.network_status.network_manager import (
    ActiveConnectionInfo,
    DBusException,
    NetworkManagerDBusAdapter,
    NetworkManagerMonitor,
    NMMetered,
    decode_ssid,
)


@pytest.fixture
def mock_adapter():
    return MagicMock(spec_set=NetworkManagerDBusAdapter, wraps=UncallableNetworkManagerDBusAdapter())


@pytest.fixture
def nm_monitor(mock_adapter):
    return NetworkManagerMonitor(nm_adapter=mock_adapter)


def test_is_network_status_available(nm_monitor):
    assert nm_monitor.is_network_status_available() is True


@pytest.mark.parametrize(
    'global_metered_status, expected',
    [
        (NMMetered.UNKNOWN, False),
        (NMMetered.YES, True),
        (NMMetered.NO, False),
        (NMMetered.GUESS_YES, True),
        (NMMetered.GUESS_NO, False),
    ],
)
def test_is_network_metered(global_metered_status, expected, nm_monitor):
    nm_monitor._nm.get_global_metered_status.return_value = global_metered_status

    result = nm_monitor.is_network_metered()

    assert result == expected


@pytest.mark.parametrize(
    'connection_path, connection_type, type_settings, expected',
    [
        (
            '/org/freedesktop/NetworkManager/ActiveConnection/1',
            '802-11-wireless',
            {'ssid': bytes([84, 69, 83, 84])},
            'TEST',
        ),
        ('/org/freedesktop/NetworkManager/ActiveConnection/2', '802-11-ethernet', {}, None),
    ],
)
def test_get_current_wifi(connection_path, connection_type, type_settings, expected, nm_monitor):
    nm_monitor._nm.get_primary_connection_path.return_value = connection_path
    nm_monitor._nm.get_active_connection_info.return_value = ActiveConnectionInfo(
        connection='/org/freedesktop/NetworkManager/Settings/12', type=connection_type
    )
    nm_monitor._nm.get_settings.side_effect = [{connection_type: type_settings}]

    result = nm_monitor.get_current_wifi()

    assert result == expected


def test_get_current_wifi_with_no_connection(nm_monitor):
    nm_monitor._nm.get_primary_connection_path.return_value = None

    assert nm_monitor.get_current_wifi() is None


def test_get_known_wifis(nm_monitor):
    nm_monitor._nm.get_connections_paths.return_value = ['/org/freedesktop/NetworkManager/Settings/12']
    nm_monitor._nm.get_settings.return_value = {
        'connection': {'timestamp': 1597303736},
        '802-11-wireless': {'ssid': [84, 69, 83, 84]},
    }

    result = nm_monitor.get_known_wifis()

    assert result == [
        SystemWifiInfo(
            ssid='TEST',
            last_connected=datetime(2020, 8, 13, 7, 28, 56),
        )
    ]


def test_get_known_wifis_with_never_used_connection(nm_monitor):
    nm_monitor._nm.get_connections_paths.return_value = ['/org/freedesktop/NetworkManager/Settings/12']
    nm_monitor._nm.get_settings.return_value = {
        'connection': {},
        '802-11-wireless': {'ssid': [84, 69, 83, 84]},
    }

    result = nm_monitor.get_known_wifis()

    assert result == [
        SystemWifiInfo(
            ssid='TEST',
            last_connected=None,
        )
    ]


def test_get_known_wifis_partial_failure(nm_monitor):
    nm_monitor._nm.get_connections_paths.return_value = [
        '/org/freedesktop/NetworkManager/Settings/12',
        '/org/freedesktop/NetworkManager/Settings/42',
    ]
    nm_monitor._nm.get_settings.side_effect = [
        DBusException("Test"),
        {
            'connection': {},
            '802-11-wireless': {'ssid': [84, 69, 83, 84]},
        },
    ]

    result = nm_monitor.get_known_wifis()

    assert result == [
        SystemWifiInfo(
            ssid='TEST',
            last_connected=None,
        )
    ]


def test_get_known_wifis_with_no_wifi_connections(nm_monitor):
    nm_monitor._nm.get_connections_paths.return_value = ['/org/freedesktop/NetworkManager/Settings/12']
    nm_monitor._nm.get_settings.return_value = {
        'connection': {},
        '802-11-ethernet': {},
    }

    result = nm_monitor.get_known_wifis()

    assert result == []


@pytest.mark.parametrize(
    'ssid_bytes, expected',
    [
        ([84, 69, 83, 84], 'TEST'),
        ([240, 159, 150, 150], '🖖'),
        ([0, 1, 2, 10, 34, 39], '\\x00\\x01\\x02\\n"\''),
    ],
)
def test_decode_ssid(ssid_bytes, expected):
    result = decode_ssid(ssid_bytes)
    assert result == expected


class UncallableNetworkManagerDBusAdapter(NetworkManagerDBusAdapter):
    def __init__(self):
        # Skip parent setup, this way none of the DBus calls can happen in tests
        super(NetworkManagerDBusAdapter, self).__init__(parent=None)
