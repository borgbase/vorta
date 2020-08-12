import plistlib
import subprocess
import xml
from typing import Optional

from peewee import format_date_time

from vorta.log import logger
from vorta.network_status.abc import NetworkStatusMonitor, SystemWifiInfo


class DarwinNetworkStatus(NetworkStatusMonitor):
    def is_network_metered(self) -> bool:
        return False  # TODO: implement guessing if current network is metered for OSX

    def get_current_wifi(self) -> Optional[str]:
        """
        Get current SSID or None if Wifi is off.

        From https://gist.github.com/keithweaver/00edf356e8194b89ed8d3b7bbead000c
        """
        cmd = ['/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport', '-I']
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        out, err = process.communicate()
        process.wait()
        for line in out.decode("utf-8").split('\n'):
            split_line = line.strip().split(':')
            if split_line[0] == 'SSID':
                return split_line[1].strip()

    def get_known_wifis(self):
        from vorta.models import WifiSettingModel
        plist_path = '/Library/Preferences/SystemConfiguration/com.apple.airport.preferences.plist'

        try:
            plist_file = open(plist_path, 'rb')
            wifis = plistlib.load(plist_file).get('KnownNetworks')
        except xml.parsers.expat.ExpatError:
            logger.error('Unable to parse list of Wifi networks.')
            return None

        result = []
        if wifis is not None:
            for wifi in wifis.values():
                raw_last_connected = wifi.get('LastConnected', None)
                last_connected = None if not raw_last_connected \
                    else format_date_time(raw_last_connected, WifiSettingModel.last_connected.formats)
                ssid = wifi.get('SSIDString', None)

                if ssid is None:
                    continue

                result.append(SystemWifiInfo(ssid=ssid, last_connected=last_connected))

        return result
