from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QLabel, QListWidget, QListWidgetItem

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

        self.populate_wifi()
        self.setup_connections()

    def setup_connections(self):
        self.meteredNetworksCheckBox.stateChanged.connect(self.on_metered_networks_state_changed)
        self.wifiListWidget.itemChanged.connect(self.save_wifi_item)

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
