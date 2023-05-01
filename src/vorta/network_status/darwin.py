import subprocess
from datetime import datetime as dt
from typing import Iterator, Optional

from vorta.log import logger
from vorta.network_status.abc import NetworkStatusMonitor, SystemWifiInfo


class DarwinNetworkStatus(NetworkStatusMonitor):
    def is_network_metered(self) -> bool:
        return any(is_network_metered(d) for d in get_network_devices())

    def get_current_wifi(self) -> Optional[str]:
        """
        Get current SSID or None if Wifi is off.

        From https://gist.github.com/keithweaver/00edf356e8194b89ed8d3b7bbead000c
        """
        cmd = [
            '/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport',
            '-I',
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        out, err = process.communicate()
        process.wait()
        for line in out.decode(errors='ignore').split('\n'):
            split_line = line.strip().split(':')
            if split_line[0] == 'SSID':
                return split_line[1].strip()

    def get_known_wifis(self):
        """
        Listing all known Wifi networks isn't possible any more from macOS 11. Instead we
        just return the current Wifi.
        """
        wifis = []
        current_wifi = self.get_current_wifi()
        if current_wifi is not None:
            wifis.append(SystemWifiInfo(ssid=current_wifi, last_connected=dt.now()))

        return wifis


def get_network_devices() -> Iterator[str]:
    for line in call_networksetup_listallhardwareports().splitlines():
        if line.startswith(b'Device: '):
            yield line.split()[1].strip().decode('ascii')


def is_network_metered(bsd_device) -> bool:
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
