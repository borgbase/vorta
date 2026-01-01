from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QCheckBox, QLabel, QListWidget, QListWidgetItem

from vorta.store.models import BackupProfileMixin, WifiSettingModel
from vorta.utils import get_asset, get_sorted_wifis

uifile = get_asset('UI/networks_page.ui')
NetworksUI, NetworksBase = uic.loadUiType(uifile)


class NetworksPage(NetworksBase, NetworksUI, BackupProfileMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.wifiListLabel: QLabel = self.findChild(QLabel, 'wifiListLabel')
        self.meteredNetworksCheckBox: QCheckBox = self.findChild(QCheckBox, 'meteredNetworksCheckBox')
        self.wifiListWidget: QListWidget = self.findChild(QListWidget, 'wifiListWidget')

        # Connect signals
        self.meteredNetworksCheckBox.stateChanged.connect(self.on_metered_networks_state_changed)
        self.wifiListWidget.itemChanged.connect(self.save_wifi_item)
        self._profile_changed_connection = QApplication.instance().profile_changed_event.connect(self.populate_wifi)
        self.destroyed.connect(self._on_destroyed)

        self.populate_wifi()

    def on_metered_networks_state_changed(self, state):
        profile = self.profile()
        attr = 'dont_run_on_metered_networks'
        new_value = state != Qt.CheckState.Checked
        self.save_profile_attr(attr, new_value)
        self.meteredNetworksCheckBox.setChecked(False if profile.dont_run_on_metered_networks else True)

    def populate_wifi(self):
        self.wifiListWidget.clear()
        profile = self.profile()
        if profile:
            for wifi in get_sorted_wifis(profile):
                item = QListWidgetItem()
                item.setText(wifi.ssid)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                if wifi.allowed:
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
                self.wifiListWidget.addItem(item)

    def save_wifi_item(self, item):
        profile = self.profile()
        if profile:
            db_item = WifiSettingModel.get(ssid=item.text(), profile=profile.id)
            db_item.allowed = item.checkState() == Qt.CheckState.Checked
            db_item.save()

    def save_profile_attr(self, attr, new_value):
        profile = self.profile()
        if profile:
            setattr(profile, attr, new_value)
            profile.save()

    def _on_destroyed(self):
        try:
            QApplication.instance().profile_changed_event.disconnect(self._profile_changed_connection)
        except (TypeError, RuntimeError):
            pass
