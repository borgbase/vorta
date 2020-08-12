import logging
from enum import Enum
from typing import Optional, List

from PyQt5 import QtDBus
from PyQt5.QtCore import QObject, QVersionNumber

from vorta.network_status.abc import NetworkStatusMonitor

logger = logging.getLogger(__name__)


class NetworkManagerMonitor(NetworkStatusMonitor):
    def __init__(self):
        bus = QtDBus.QDBusConnection.systemBus()
        if not bus.isConnected():
            raise UnsupportedException("Can't connect to system bus")
        nm_adapter = NetworkManagerNetworkStatusAdapter(parent=None, bus=bus)
        if not nm_adapter.isValid():
            raise UnsupportedException("Can't connect to NetworkManager")
        self._nm = nm_adapter

    def is_network_metered(self) -> bool:
        return self._nm.get_global_metered_status() in (NMMetered.YES, NMMetered.GUESS_YES)

    def get_current_wifi(self) -> Optional[str]:
        return None  # TODO: get current WiFi SSID

    def get_known_wifis(self) -> List[str]:
        return None  # TODO: list known WiFi SSIDs


class UnsupportedException(Exception):
    """NetworkManager is not available"""


class NetworkManagerNetworkStatusAdapter(QObject):
    def __init__(self, parent, bus):
        super().__init__(parent)
        self._nm = QtDBus.QDBusInterface(
            'org.freedesktop.NetworkManager', '/org/freedesktop/NetworkManager', 'org.freedesktop.NetworkManager',
            bus)

    def isValid(self):
        if not self._nm.isValid():
            return False
        nm_version = self._get_nm_version()
        if nm_version < QVersionNumber(1, 2):
            logger.warning('NetworkManager version 1.2 or later required, found %s', nm_version.toString())
            return False
        return True

    def get_global_metered_status(self):
        return NMMetered(read_dbus_property(self._nm, 'Metered'))

    def _get_nm_version(self):
        version, _suffindex = QVersionNumber.fromString(read_dbus_property(self._nm, 'Version'))
        return version


def read_dbus_property(obj, property):
    # QDBusInterface.property() didn't work for some reason
    props = QtDBus.QDBusInterface(obj.service(), obj.path(), 'org.freedesktop.DBus.Properties', obj.connection())
    msg = props.call('Get', obj.interface(), property)
    if msg.type() == msg.MessageType.ReplyMessage:
        return msg.arguments()[0]


class NMMetered(Enum):
    UNKNOWN = 0
    YES = 1
    NO = 2
    GUESS_YES = 3
    GUESS_NO = 4
