from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QLabel, QListWidget, QListWidgetItem

from vorta.store.models import WifiSettingModel
from vorta.utils import get_asset, get_sorted_wifis
from vorta.views.base_tab import BaseTab

uifile = get_asset('UI/networks_page.ui')
NetworksUI, NetworksBase = uic.loadUiType(uifile)


class NetworksPage(BaseTab, NetworksBase, NetworksUI):
    def __init__(self, parent=None, profile_provider=None):
        super().__init__(parent=parent, profile_provider=profile_provider)
        self.setupUi(self)

        self.wifiListLabel: QLabel = self.findChild(QLabel, 'wifiListLabel')
        self.meteredNetworksCheckBox: QCheckBox = self.findChild(QCheckBox, 'meteredNetworksCheckBox')
        self.wifiListWidget: QListWidget = self.findChild(QListWidget, 'wifiListWidget')

        # Connect signals
        self.meteredNetworksCheckBox.stateChanged.connect(self.on_metered_networks_state_changed)
        self.wifiListWidget.itemChanged.connect(self.save_wifi_item)
        self.track_profile_change(self.populate_wifi, call_now=True)

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
