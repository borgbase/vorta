import subprocess
from datetime import datetime as dt
from typing import Iterator, Optional

from CoreWLAN import CWInterface

from vorta.log import logger
from vorta.network_status.abc import NetworkStatusMonitor, SystemWifiInfo


class DarwinNetworkStatus(NetworkStatusMonitor):
    def is_network_metered(self) -> bool:
        return any(is_network_metered_with_android(d) for d in get_network_devices())

    def get_current_wifi(self) -> Optional[str]:
        """
        Get current SSID or None if Wifi is off.
        """
        interface = self._get_wifi_interface()
        network = interface.lastNetworkJoined()
        network_name = network.ssid()

        return network_name

    def _get_wifi_interface(self):
        interface = CWInterface.interface()
        return interface

    def get_known_wifis(self):
        """
        Use the program, "networksetup" to get the list of know Wi-Fi networks.
        """

        wifis = []
        interface = self._get_wifi_interface()
        command = ['/usr/sbin/networksetup', '-listpreferredwirelessnetworks', interface]

        result = subprocess.run(command, capture_output=True, text=True)

        for wifi_network_name in result:
            wifis.append(SystemWifiInfo(ssid=wifi_network_name, last_connected=dt.now()))

        return wifis


def get_network_devices() -> Iterator[str]:
    for line in call_networksetup_listallhardwareports().splitlines():
        if line.startswith(b'Device: '):
            yield line.split()[1].strip().decode('ascii')


def is_network_metered_with_android(bsd_device) -> bool:
    return b'ANDROID_METERED' in call_ipconfig_getpacket(bsd_device)


def call_ipconfig_getpacket(bsd_device):
    cmd = ['ipconfig', 'getpacket', bsd_device]
    try:
        return subprocess.check_output(cmd)
    except subprocess.CalledProcessError:
        logger.debug("Command %s failed", ' '.join(cmd))
        return b''


def call_networksetup_listallhardwareports():
    cmd = ['networksetup', '-listallhardwareports']
    try:
        return subprocess.check_output(cmd)
    except subprocess.CalledProcessError:
        logger.debug("Command %s failed", ' '.join(cmd))
