import pytest

from vorta.network_status import darwin


@pytest.mark.parametrize('getpacket_output_name, expected', [
    ('normal_router', False),
    ('phone', True),
])
def test_is_network_metered(getpacket_output_name, expected, monkeypatch):
    def mock_getpacket(device):
        assert device == 'en0'
        return GETPACKET_OUTPUTS[getpacket_output_name]

    monkeypatch.setattr(darwin, 'call_ipconfig_getpacket', mock_getpacket)

    result = darwin.is_network_metered('en0')
    assert result == expected


def test_get_network_devices(monkeypatch):
    monkeypatch.setattr(darwin, 'call_networksetup_listallhardwareports', lambda: NETWORKSETUP_OUTPUT)

    result = list(darwin.get_network_devices())
    assert result == ['Bluetooth-Modem', 'en0', 'en1', 'en2', 'bridge0']


GETPACKET_OUTPUTS = {
    'normal_router': b"""\
op = BOOTREPLY
htype = 1
flags = 0
hlen = 6
hops = 0
xid = 0x8dc8db4d
secs = 0
ciaddr = 0.0.0.0
yiaddr = 172.16.13.237
siaddr = 0.0.0.0
giaddr = 0.0.0.0
chaddr = 8c:85:90:ad:ee:a3
sname =
file =
options:
Options count is 9
dhcp_message_type (uint8): ACK 0x5
subnet_mask (ip): 255.255.252.0
router (ip_mult): {172.16.12.1}
domain_name_server (ip_mult): {172.16.12.1, 8.8.8.8}
domain_name (string): .
lease_time (uint32): 0xe10
interface_mtu (uint16): 0x5dc
server_identifier (ip): 172.16.12.1
end (none):
""",
    'phone': b"""\
op = BOOTREPLY
htype = 1
flags = 0
hlen = 6
hops = 0
xid = 0x8dc8db4e
secs = 0
ciaddr = 0.0.0.0
yiaddr = 192.168.43.223
siaddr = 192.168.43.242
giaddr = 0.0.0.0
chaddr = 8c:85:90:ad:ee:a3
sname =
file =
options:
Options count is 11
dhcp_message_type (uint8): ACK 0x5
server_identifier (ip): 192.168.43.242
lease_time (uint32): 0xe0f
renewal_t1_time_value (uint32): 0x707
rebinding_t2_time_value (uint32): 0xc4d
subnet_mask (ip): 255.255.255.0
broadcast_address (ip): 192.168.43.255
router (ip_mult): {192.168.43.242}
domain_name_server (ip_mult): {192.168.43.242}
vendor_specific (opaque):
0000  41 4e 44 52 4f 49 44 5f  4d 45 54 45 52 45 44     ANDROID_METERED
"""
}

NETWORKSETUP_OUTPUT = b"""\
Hardware Port: Bluetooth DUN
Device: Bluetooth-Modem
Ethernet Address: N/A

Hardware Port: Wi-Fi
Device: en0
Ethernet Address: d7:02:65:7c:1e:14

Hardware Port: Bluetooth PAN
Device: en1
Ethernet Address: N/A

Hardware Port: Thunderbolt 1
Device: en2
Ethernet Address: bb:e8:c3:25:2b:12

Hardware Port: Thunderbolt Bridge
Device: bridge0
Ethernet Address: N/A
"""
