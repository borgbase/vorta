import subprocess
from datetime import datetime as dt
from typing import Iterator, List, Optional

from CoreWLAN import CWInterface, CWNetwork, CWWiFiClient

from vorta.log import logger
from vorta.network_status.abc import NetworkStatusMonitor, SystemWifiInfo


class DarwinNetworkStatus(NetworkStatusMonitor):
    def is_network_metered(self) -> bool:
        interface: CWInterface = self._get_wifi_interface()
        network: Optional[CWNetwork] = interface.lastNetworkJoined()

        if network:
            is_ios_hotspot = network.isPersonalHotspot()
        else:
            is_ios_hotspot = False

        return is_ios_hotspot or any(is_network_metered_with_android(d) for d in get_network_devices())

    def get_current_wifi(self) -> Optional[str]:
        """
        Get current SSID or None if Wi-Fi is off.
        """
        interface: Optional[CWInterface] = self._get_wifi_interface()
        if not interface:
            return None

        # If the user has Wi-Fi turned off lastNetworkJoined will return None.
        network: Optional[CWNetwork] = interface.lastNetworkJoined()

        if network:
            network_name = network.ssid()
            return network_name
        else:
            return None

    def get_known_wifis(self) -> List[SystemWifiInfo]:
        """
        Use the program, "networksetup", to get the list of know Wi-Fi networks.
        """

        wifis = []
        interface: Optional[CWInterface] = self._get_wifi_interface()
        if not interface:
            return []

        interface_name = interface.name()
        output = call_networksetup_listpreferredwirelessnetworks(interface_name)

        result = []
        for line in output.strip().splitlines():
            if line.strip().startswith("Preferred networks"):
                continue
            elif not line.strip():
                continue
            else:
                result.append(line.strip())

        for wifi_network_name in result:
            wifis.append(SystemWifiInfo(ssid=wifi_network_name, last_connected=dt.now()))

        return wifis

    def _get_wifi_interface(self) -> Optional[CWInterface]:
        wifi_client: CWWiFiClient = CWWiFiClient.sharedWiFiClient()
        interface: Optional[CWInterface] = wifi_client.interface()
        return interface


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


def call_networksetup_listpreferredwirelessnetworks(interface) -> str:
    command = ['/usr/sbin/networksetup', '-listpreferredwirelessnetworks', interface]
    try:
        return subprocess.check_output(command).decode(encoding='utf-8')
    except subprocess.CalledProcessError:
        logger.debug("Command %s failed", " ".join(command))
