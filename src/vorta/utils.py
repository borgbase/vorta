import os
import sys
import plistlib
import argparse
import unicodedata
import re

from collections import defaultdict
from functools import reduce
import operator

from paramiko.rsakey import RSAKey
from paramiko.ecdsakey import ECDSAKey
from paramiko.ed25519key import Ed25519Key
from paramiko import SSHException
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5 import QtCore
import subprocess
import keyring


class VortaKeyring(keyring.backend.KeyringBackend):
    """Fallback keyring service."""
    @classmethod
    def priority(cls):
        return 5

    def set_password(self, service, repo_url, password):
        from .models import RepoPassword
        keyring_entry, created = RepoPassword.get_or_create(
            url=repo_url,
            defaults={'password': password}
        )
        keyring_entry.password = password
        keyring_entry.save()

    def get_password(self, service, repo_url):
        from .models import RepoPassword
        try:
            keyring_entry = RepoPassword.get(url=repo_url)
            return keyring_entry.password
        except Exception:
            return None

    def delete_password(self, service, repo_url):
        pass


# Select keyring/Workaround for pyinstaller+keyring issue.
if sys.platform == 'darwin':
    from keyring.backends import OS_X
    keyring.set_keyring(OS_X.Keyring())
elif sys.platform == 'win32':
    from keyring.backends import Windows
    keyring.set_keyring(Windows.WinVaultKeyring())
elif sys.platform == 'linux':
    from keyring.backends import SecretService
    try:
        SecretService.Keyring.priority()  # Test if keyring works.
        keyring.set_keyring(SecretService.Keyring())
    except Exception:
        keyring.set_keyring(VortaKeyring())
else:  # Fall back to saving password to database.
    keyring.set_keyring(VortaKeyring())


def nested_dict():
    """
    Combination of two idioms to quickly build dicts from lists of keys:

    - https://stackoverflow.com/a/16724937/3983708
    - https://stackoverflow.com/a/14692747/3983708
    """
    return defaultdict(nested_dict)


def get_dict_from_list(dataDict, mapList):
    return reduce(operator.getitem, mapList, dataDict)


def choose_file_dialog(parent, title, want_folder=True):
    options = QFileDialog.Options()
    if want_folder:
        options |= QFileDialog.ShowDirsOnly
    dialog = QFileDialog(parent, title, os.path.expanduser('~'), options=options)
    dialog.setFileMode(QFileDialog.Directory if want_folder else QFileDialog.AnyFile)
    dialog.setParent(parent, QtCore.Qt.Sheet)
    return dialog


def get_private_keys():
    """Find SSH keys in standard folder."""
    key_formats = [RSAKey, ECDSAKey, Ed25519Key]

    ssh_folder = os.path.expanduser('~/.ssh')

    available_private_keys = []
    if os.path.isdir(ssh_folder):
        for key in os.listdir(ssh_folder):
            for key_format in key_formats:
                try:
                    parsed_key = key_format.from_private_key_file(
                        os.path.join(ssh_folder, key)
                    )
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
    power = 1000  # GiB is base 2**10, GB is base 10**3.
    n = 0
    Dic_powerN = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f'{round(size, 1)} {Dic_powerN[n]}B'


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

    from vorta.models import WifiSettingModel

    if sys.platform == 'darwin':
        plist_path = '/Library/Preferences/SystemConfiguration/com.apple.airport.preferences.plist'
        plist_file = open(plist_path, 'rb')
        wifis = plistlib.load(plist_file)['KnownNetworks']
        if wifis:
            for wifi in wifis.values():
                timestamp = wifi.get('LastConnected', None)
                ssid = wifi['SSIDString']
                db_wifi, created = WifiSettingModel.get_or_create(
                    ssid=ssid,
                    profile=profile.id,
                    defaults={'last_connected': timestamp, 'allowed': True}
                )

                # update last connected time
                if not created and db_wifi.last_connected != timestamp:
                    db_wifi.last_connected = timestamp
                    db_wifi.save()

        # remove Wifis that were deleted in the system.
        deleted_wifis = WifiSettingModel.select() \
            .where(WifiSettingModel.ssid.not_in([w['SSIDString'] for w in wifis.values()]))
        for wifi in deleted_wifis:
            wifi.delete_instance()

    return WifiSettingModel.select() \
        .where(WifiSettingModel.profile == profile.id).order_by(-WifiSettingModel.last_connected)


def get_current_wifi():
    """
    Get current SSID or None if Wifi is off.

    From https://gist.github.com/keithweaver/00edf356e8194b89ed8d3b7bbead000c
    """

    if sys.platform == 'darwin':
        cmd = ['/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport', '-I']
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        out, err = process.communicate()
        process.wait()
        for line in out.decode("utf-8").split('\n'):
            split_line = line.strip().split(':')
            if split_line[0] == 'SSID':
                return split_line[1].strip()


def parse_args():
    parser = argparse.ArgumentParser(description='Vorta Backup GUI for Borg.')
    parser.add_argument('--foreground', '-f',
                        action='store_true',
                        help="Don't fork into background and open main window on startup.")
    return parser.parse_args()


def slugify(value):
    """
    Converts to lowercase, removes non-word characters (alphanumerics and
    underscores) and converts spaces to hyphens. Also strips leading and
    trailing whitespace.

    Copied from Django.
    """
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(r'[-\s]+', '-', value)


def set_tray_icon(tray, active=False):
    from vorta.models import SettingsModel
    use_light_style = SettingsModel.get(key='use_light_icon').value
    icon_name = f"icons/hdd-o{'-active' if active else ''}-{'light' if use_light_style else 'dark'}.png"
    icon = QIcon(get_asset(icon_name))
    tray.setIcon(icon)


def open_app_at_startup(enabled=True):
    if sys.platform == 'darwin':
        print('Not implemented due to conflict with keyring package.')
        # From https://stackoverflow.com/questions/26213884/cocoa-add-app-to-startup-in-sandbox-using-pyobjc
        # from Foundation import NSDictionary
        # from Cocoa import NSBundle, NSURL
        # from CoreFoundation import kCFAllocatorDefault
        # from LaunchServices import (LSSharedFileListCreate, kLSSharedFileListSessionLoginItems,
        #                             LSSharedFileListInsertItemURL, kLSSharedFileListItemHidden,
        #                             kLSSharedFileListItemLast, LSSharedFileListItemRemove)
        #
        # app_path = NSBundle.mainBundle().bundlePath()
        # url = NSURL.alloc().initFileURLWithPath_(app_path)
        # login_items = LSSharedFileListCreate(kCFAllocatorDefault, kLSSharedFileListSessionLoginItems, None)
        # props = NSDictionary.dictionaryWithObject_forKey_(True, kLSSharedFileListItemHidden)
        #
        # new_item = LSSharedFileListInsertItemURL(login_items, kLSSharedFileListItemLast,
        #                                          None, None, url, props, None)
        # if not enabled:
        #     LSSharedFileListItemRemove(login_items, new_item)
