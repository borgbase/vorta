import logging
from enum import Enum

from PyQt5 import QtDBus
from PyQt5.QtCore import QObject, QVersionNumber

logger = logging.getLogger(__name__)


def is_current_network_metered():
    nm = get_network_manager()
    return nm and nm.is_current_network_metered


def is_network_metered_status_supported():
    nm = get_network_manager()
    return bool(nm)


def get_network_manager():
    global _network_manager
    if _network_manager:
        return _network_manager

    bus = QtDBus.QDBusConnection.systemBus()
    if bus.isConnected():
        nm = NetworkManagerNetworkStatusAdapter(parent=None, bus=bus)
        if nm.isValid():
            _network_manager = nm
            return _network_manager


_network_manager = None


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

    def is_current_network_metered(self):
        nm_metered = NMMetered(read_dbus_property(self._nm, 'Metered'))
        return nm_metered in (NMMetered.YES, NMMetered.GUESS_YES)

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
