import argparse
import errno
import getpass
import operator
import os
import platform
import plistlib
import re
import subprocess
import sys
import unicodedata
import xml
from collections import defaultdict
from datetime import datetime as dt
from functools import reduce

import psutil
from paramiko import SSHException
from paramiko.ecdsakey import ECDSAKey
from paramiko.ed25519key import Ed25519Key
from paramiko.rsakey import RSAKey
from PyQt5 import QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QFileDialog, QSystemTrayIcon

from vorta.borg._compatibility import BorgCompatibility
from vorta.keyring.abc import VortaKeyring
from vorta.log import logger

keyring = VortaKeyring.get_keyring()
logger.info('Using %s Keyring implementation.', keyring.__class__.__name__)

borg_compat = BorgCompatibility()


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
            key_file = os.path.join(ssh_folder, key)
            if not os.path.isfile(key_file):
                continue
            for key_format in key_formats:
                try:
                    parsed_key = key_format.from_private_key_file(key_file)
                    key_details = {
                        'filename': key,
                        'format': parsed_key.get_name(),
                        'bits': parsed_key.get_bits(),
                        'fingerprint': parsed_key.get_fingerprint().hex()
                    }
                    available_private_keys.append(key_details)
                except (SSHException, UnicodeDecodeError, IsADirectoryError):
                    continue
                except OSError as e:
                    if e.errno == errno.ENXIO:
                        # when key_file is a (ControlPath) socket
                        continue
                    else:
                        raise

    return available_private_keys


def pretty_bytes(size):
    """from https://stackoverflow.com/questions/12523586/
            python-format-size-application-converting-b-to-kb-mb-gb-tb/37423778"""
    if type(size) != int:
        return ''
    power = 1000  # GiB is base 2**10, GB is base 10**3.
    n = 0
    Dic_powerN = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size >= power:
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

        try:
            plist_file = open(plist_path, 'rb')
            wifis = plistlib.load(plist_file).get('KnownNetworks')
        except xml.parsers.expat.ExpatError:
            logger.error('Unable to parse list of Wifi networks.')
            return

        if wifis is not None:
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
    parser.add_argument('--version', '-V',
                        action='store_true',
                        help="Show version and exit.")
    parser.add_argument('--foreground', '-f',
                        action='store_true',
                        help="Don't fork into background and open main window on startup.")
    if sys.platform.startswith("linux"):
        parser.add_argument('--daemonize', '-d',
                            action='store_true',
                            help="Daemonize and don't open window on startup.")

    return parser.parse_known_args()[0]


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


def uses_dark_mode():
    """
    This function detects if we are running in dark mode (e.g. macOS dark mode).

    Returns None if the interface style cannot be determined, otherwise a boolean.
    """
    if sys.platform == 'darwin':
        from Foundation import NSUserDefaults
        stdud = NSUserDefaults.standardUserDefaults()
        return stdud.stringForKey_("AppleInterfaceStyle") == "Dark"
    return None


def format_archive_name(profile, archive_name_tpl):
    """
    Generate an archive name. Default:
    {hostname}-{profile_slug}-{now:%Y-%m-%dT%H:%M:%S}
    """
    available_vars = {
        'hostname': platform.node(),
        'profile_id': profile.id,
        'profile_slug': profile.slug(),
        'now': dt.now(),
        'utc_now': dt.utcnow(),
        'user': getpass.getuser()
    }
    return archive_name_tpl.format(**available_vars)


def get_mount_points(repo_url):
    mount_points = {}
    for proc in psutil.process_iter():
        try:
            name = proc.name()
            if name == 'borg' or name.startswith('python'):
                if 'mount' not in proc.cmdline():
                    continue

                for idx, parameter in enumerate(proc.cmdline()):
                    if parameter.startswith(repo_url + '::'):
                        archive_name = parameter[len(repo_url) + 2:]

                        # The borg mount command specifies that the mount_point
                        # parameter comes after the archive name
                        if len(proc.cmdline()) > idx + 1:
                            mount_point = proc.cmdline()[idx + 1]
                            mount_points[archive_name] = mount_point
                        break
        except (psutil.ZombieProcess, psutil.AccessDenied):
            # Getting process details may fail (e.g. zombie process on macOS)
            # or because the process is owned by another user.
            # Also see https://github.com/giampaolo/psutil/issues/783
            continue

    return mount_points


def is_system_tray_available():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        tray = QSystemTrayIcon()
        is_available = tray.isSystemTrayAvailable()
        app.quit()
    else:
        tray = QSystemTrayIcon()
        is_available = tray.isSystemTrayAvailable()

    return is_available
