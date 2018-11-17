import os
import sys
import plistlib
from paramiko.rsakey import RSAKey
from paramiko.ecdsakey import ECDSAKey
from paramiko.ed25519key import Ed25519Key
from paramiko import SSHException
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QFileDialog
import subprocess

"""Workaround for pyinstaller+keyring issue."""
import keyring
if sys.platform == 'darwin':
    from keyring.backends import OS_X
    keyring.set_keyring(OS_X.Keyring())
elif sys.platform == 'win32':
    from keyring.backends import Windows
    keyring.set_keyring(Windows.WinVaultKeyring())
else:
    from keyring.backends import SecretService
    keyring.set_keyring(SecretService.Keyring())


from .models import WifiSettingModel

def choose_folder_dialog(parent, title):
    options = QFileDialog.Options()
    options |= QFileDialog.ShowDirsOnly
    options |= QFileDialog.DontUseNativeDialog
    return QFileDialog.getExistingDirectory(parent, title, "", options=options)

def get_private_keys():
    """Find SSH keys in standard folder."""
    key_formats = [RSAKey, ECDSAKey, Ed25519Key]

    ssh_folder = os.path.expanduser('~/.ssh')

    available_private_keys = []
    if os.path.isdir(ssh_folder):
        for key in os.listdir(ssh_folder):
            for key_format in key_formats:
                try:
                    parsed_key = key_format.from_private_key_file(os.path.join(ssh_folder, key))
                    key_details = {
                        'filename': key,
                        'format': parsed_key.get_name(),
                        'bits': parsed_key.get_bits(),
                        'fingerprint': parsed_key.get_fingerprint().hex()
                    }
                    available_private_keys.append(key_details)
                except (SSHException, UnicodeDecodeError, IsADirectoryError):
                    continue

    return available_private_keys


def pretty_bytes(size):
    """from https://stackoverflow.com/questions/12523586/
            python-format-size-application-converting-b-to-kb-mb-gb-tb/37423778"""
    if type(size) != int:
        return ''
    power = 2**10
    n = 0
    Dic_powerN = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return str(round(size))+Dic_powerN[n]+'B'


def get_asset(path):
    if getattr(sys, 'frozen', False):
        # we are running in a bundle
        bundle_dir = os.path.join(sys._MEIPASS, 'assets')
    else:
        # we are running in a normal Python environment
        bundle_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
    return os.path.join(bundle_dir, path)


def get_sorted_wifis(profile):
    """Get SSIDs from OS and merge with settings in DB."""
    app = QApplication.instance()

    if sys.platform == 'darwin':
        plist_file = open('/Library/Preferences/SystemConfiguration/com.apple.airport.preferences.plist', 'rb')
        wifis = plistlib.load(plist_file)['KnownNetworks']
        if wifis:
            for wifi in wifis.values():
                timestamp = wifi.get('LastConnected', None)
                ssid = wifi['SSIDString']
                WifiSettingModel.get_or_create(ssid=ssid, profile=profile.id,
                                               defaults={'last_connected': timestamp,
                                                        'allowed': True})

    return WifiSettingModel.select().where(WifiSettingModel.profile == profile.id).order_by(-WifiSettingModel.last_connected)


def get_current_wifi():
    """
    Get current SSID or None if Wifi is off.

    From https://gist.github.com/keithweaver/00edf356e8194b89ed8d3b7bbead000c
    """

    if sys.platform == 'darwin':
        cmd = ['/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport','-I']
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        out, err = process.communicate()
        process.wait()
        for line in out.decode("utf-8").split('\n'):
            split_line = line.strip().split(':')
            if split_line[0] == 'SSID':
                return split_line[1].strip()
