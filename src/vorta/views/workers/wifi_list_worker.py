import logging

from PyQt6.QtCore import QThread, pyqtSignal

from vorta.store.models import WifiSettingModel
from vorta.utils import get_network_status_monitor

logger = logging.getLogger(__name__)


class WifiListWorker(QThread):
    signal = pyqtSignal(list)

    def __init__(self, profile_id):
        QThread.__init__(self)
        self.profile_id = profile_id

    def run(self):
        """
        Get Wifi networks known to the OS (only current one on macOS) and
        merge with networks from other profiles. Update last connected time.
        """

        # Pull networks known to OS and all other backup profiles
        system_wifis = get_network_status_monitor().get_known_wifis()
        from_other_profiles = WifiSettingModel.select().where(WifiSettingModel.profile != self.profile_id).execute()

        for wifi in list(from_other_profiles) + system_wifis:
            db_wifi, created = WifiSettingModel.get_or_create(
                ssid=wifi.ssid,
                profile=self.profile_id,
                defaults={'last_connected': wifi.last_connected, 'allowed': True},
            )

            # Update last connected time
            if not created and db_wifi.last_connected != wifi.last_connected:
                db_wifi.last_connected = wifi.last_connected
                db_wifi.save()

        # Finally return list of networks and settings for that profile
        self.signal.emit(
            WifiSettingModel.select()
            .where(WifiSettingModel.profile == self.profile_id)
            .order_by(-WifiSettingModel.last_connected)
        )
