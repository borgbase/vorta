import logging
from datetime import datetime
from enum import Enum
from typing import Optional, List, Any, NamedTuple, Mapping

from PyQt5 import QtDBus
from PyQt5.QtCore import QObject, QVersionNumber

from vorta.network_status.abc import NetworkStatusMonitor, SystemWifiInfo

logger = logging.getLogger(__name__)


class NetworkManagerMonitor(NetworkStatusMonitor):
    def __init__(self, nm_adapter: 'NetworkManagerDBusAdapter' = None):
        self._nm = nm_adapter or NetworkManagerDBusAdapter.get_system_nm_adapter()

    def is_network_metered(self) -> bool:
        return self._nm.get_global_metered_status() in (NMMetered.YES, NMMetered.GUESS_YES)

    def get_current_wifi(self) -> Optional[str]:
        # Only check the primary connection. VPN over WiFi will still show the WiFi as Primary Connection.
        # We don't check all active connections, as NM won't disable WiFi when connecting a cable.
        active_connection_path = self._nm.get_primary_connection_path()
        if not active_connection_path:
            return
        active_connection = self._nm.get_active_connection_info(active_connection_path)
        if active_connection.type == '802-11-wireless':
            settings = self._nm.get_settings(active_connection.connection)
            ssid = self._get_ssid_from_settings(settings)
            if ssid:
                return ssid

    def get_known_wifis(self) -> Optional[List[SystemWifiInfo]]:
        wifis = []
        for connection_path in self._nm.get_connections_paths():
            settings = self._nm.get_settings(connection_path)
            ssid = self._get_ssid_from_settings(settings)
            if ssid:
                timestamp = settings['connection'].get('timestamp')
                wifis.append(SystemWifiInfo(
                    ssid=ssid,
                    last_connected=timestamp and datetime.utcfromtimestamp(timestamp),
                ))
        return wifis

    def _get_ssid_from_settings(self, settings):
        wireless_settings = settings.get('802-11-wireless') or {}
        raw_ssid = wireless_settings.get('ssid')
        ssid = raw_ssid and decode_ssid(raw_ssid)
        return ssid


def decode_ssid(raw_ssid: List[int]) -> Optional[str]:
    """SSIDs are binary strings, but we need something to show to the user."""
    # Best effort UTF-8 decoding, as most SSIDs are UTF-8 (or even ASCII)
    str_ssid = bytes(raw_ssid).decode('utf-8', 'surrogateescape')
    if str_ssid.isprintable():
        return str_ssid
    else:
        return ''.join(
            c if c.isprintable() else ascii(c)[1:-1]
            for c in str_ssid
        )


class UnsupportedException(Exception):
    """NetworkManager is not available"""


class DBusException(Exception):
    """Failed to call a DBus method"""


class NetworkManagerDBusAdapter(QObject):
    """Simple adapter to NetworkManager's DBus interface.
    This should be the only part of NM support that needs manual testing."""
    BUS_NAME = 'org.freedesktop.NetworkManager'
    NM_PATH = '/org/freedesktop/NetworkManager'

    def __init__(self, parent, bus):
        super().__init__(parent)
        self._bus = bus
        self._nm = self._get_iface(self.NM_PATH, 'org.freedesktop.NetworkManager')

    @classmethod
    def get_system_nm_adapter(cls) -> 'NetworkManagerDBusAdapter':
        bus = QtDBus.QDBusConnection.systemBus()
        if not bus.isConnected():
            raise UnsupportedException("Can't connect to system bus")
        nm_adapter = cls(parent=None, bus=bus)
        if not nm_adapter.isValid():
            raise UnsupportedException("Can't connect to NetworkManager")
        return nm_adapter

    def isValid(self):
        if not self._nm.isValid():
            return False
        nm_version = self._get_nm_version()
        if nm_version < QVersionNumber(1, 2):
            logger.warning('NetworkManager version 1.2 or later required, found %s', nm_version.toString())
            return False
        return True

    def get_primary_connection_path(self) -> Optional[str]:
        return read_dbus_property(self._nm, 'PrimaryConnection')

    def get_active_connection_info(self, active_connection_path) -> 'ActiveConnectionInfo':
        active_connection = self._get_iface(active_connection_path, 'org.freedesktop.NetworkManager.Connection.Active')
        return ActiveConnectionInfo(
            connection=read_dbus_property(active_connection, 'Connection'),
            type=read_dbus_property(active_connection, 'Type'),
        )

    def get_connections_paths(self) -> List[str]:
        settings_manager = self._get_iface(self.NM_PATH + '/Settings', 'org.freedesktop.NetworkManager.Settings')
        return get_result(settings_manager.call('ListConnections'))

    def get_settings(self, connection_path) -> Mapping[str, Mapping[str, Any]]:
        settings = self._get_iface(connection_path, 'org.freedesktop.NetworkManager.Settings.Connection')
        return get_result(settings.call('GetSettings'))

    def get_global_metered_status(self) -> 'NMMetered':
        return NMMetered(read_dbus_property(self._nm, 'Metered'))

    def _get_nm_version(self):
        version, _suffindex = QVersionNumber.fromString(read_dbus_property(self._nm, 'Version'))
        return version

    def _get_iface(self, path, interface) -> QtDBus.QDBusInterface:
        return QtDBus.QDBusInterface(self.BUS_NAME, path, interface, self._bus)


def read_dbus_property(obj, property):
    # QDBusInterface.property() didn't work for some reason
    props = QtDBus.QDBusInterface(obj.service(), obj.path(), 'org.freedesktop.DBus.Properties', obj.connection())
    msg = props.call('Get', obj.interface(), property)
    return get_result(msg)


def get_result(msg: QtDBus.QDBusMessage) -> Any:
    if msg.type() == msg.MessageType.ReplyMessage:
        return msg.arguments()[0]
    else:
        raise DBusException("DBus call failed: {}".format(msg.arguments()))


class ActiveConnectionInfo(NamedTuple):
    connection: str
    type: str


class NMMetered(Enum):
    UNKNOWN = 0
    YES = 1
    NO = 2
    GUESS_YES = 3
    GUESS_NO = 4


class NMDeviceType(Enum):
    # Only the types we care about
    UNKNOWN = 0
    WIFI = 2
