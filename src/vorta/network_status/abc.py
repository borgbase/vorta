import sys
from datetime import datetime
from typing import Optional, NamedTuple, List


class NetworkStatusMonitor:
    @classmethod
    def get_network_status_monitor(cls) -> 'NetworkStatusMonitor':
        if sys.platform == 'darwin':
            from .darwin import DarwinNetworkStatus
            return DarwinNetworkStatus()
        else:
            from .network_manager import NetworkManagerMonitor, UnsupportedException, DBusException
            try:
                return NetworkManagerMonitor()
            except (UnsupportedException, DBusException):
                return NullNetworkStatusMonitor()

    def is_network_status_available(self):
        """Is the network status really available, and not just a dummy implementation?"""
        return type(self) != NetworkStatusMonitor

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

    def is_network_status_available(self):
        return False

    def is_network_metered(self) -> bool:
        return False

    def get_current_wifi(self) -> Optional[str]:
        pass

    def get_known_wifis(self) -> List['SystemWifiInfo']:
        return []
