import sys
from datetime import datetime
from typing import List, NamedTuple, Optional

from PyQt6.QtCore import QObject, pyqtSignal


class NetworkStatusMonitor(QObject):
    @classmethod
    def get_network_status_monitor(cls) -> 'NetworkStatusMonitor':
        if sys.platform == 'darwin':
            from .darwin import DarwinNetworkStatus

            return DarwinNetworkStatus()
        else:
            from .network_manager import (
                DBusException,
                NetworkManagerMonitor,
                UnsupportedException,
            )

            try:
                return NetworkManagerMonitor()
            except (UnsupportedException, DBusException):
                return NullNetworkStatusMonitor()

    network_status_changed = pyqtSignal(bool, name="networkStatusChanged")

    def __init__(self, parent=None):
        super().__init__(parent)

    def is_network_status_available(self):
        """Is the network status really available, and not just a dummy implementation?"""
        return type(self) is not NetworkStatusMonitor

    def is_network_active(self) -> bool:
        """Is there an active network connection.

        True signals that the network is up. The internet may still not be reachable though.
        """
        raise NotImplementedError()

    def is_network_metered(self) -> bool:
        """Is the currently connected network a metered connection?"""
        raise NotImplementedError()

    def get_current_wifi(self) -> Optional[str]:
        """Get current SSID or None if Wifi is off."""
        raise NotImplementedError()

    def get_known_wifis(self) -> List['SystemWifiInfo']:
        """Get WiFi networks known to system."""
        raise NotImplementedError()


class SystemWifiInfo(NamedTuple):
    ssid: str
    last_connected: Optional[datetime]


class NullNetworkStatusMonitor(NetworkStatusMonitor):
    """Dummy implementation, in case we don't have one for current platform."""

    def __init__(self):
        super().__init__()

    def is_network_active(self):
        return True

    def is_network_status_available(self):
        return False

    def is_network_metered(self) -> bool:
        return False

    def get_current_wifi(self) -> Optional[str]:
        pass

    def get_known_wifis(self) -> List['SystemWifiInfo']:
        return []
