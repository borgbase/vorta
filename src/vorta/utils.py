import argparse
import errno
import getpass
import operator
import os
import platform
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime as dt
from functools import reduce

import psutil
from paramiko import SSHException
from paramiko.ecdsakey import ECDSAKey
from paramiko.ed25519key import Ed25519Key
from paramiko.rsakey import RSAKey
from PyQt5 import QtCore
from PyQt5.QtCore import QFileInfo, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QFileDialog, QSystemTrayIcon

from vorta.borg._compatibility import BorgCompatibility
from vorta.i18n import trans_late
from vorta.keyring.abc import VortaKeyring
from vorta.log import logger
from vorta.network_status.abc import NetworkStatusMonitor

QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)  # enable highdpi scaling
QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)  # use highdpi icons

borg_compat = BorgCompatibility()
_network_status_monitor = None


class FilePathInfoAsync(QThread):
    signal = pyqtSignal(str, str, str)

    def __init__(self, path):
        self.path = path
        QThread.__init__(self)
        self.exiting = False

    def run(self):
        # logger.info("running thread to get path=%s...", self.path)
        self.files_count = 0
        self.size, self.files_count = get_path_datasize(self.path)
        self.signal.emit(self.path, str(self.size), str(self.files_count))


def get_directory_size(dir_path):
    ''' Get number of files only and total size in bytes from a path.
        Based off https://stackoverflow.com/a/17936789 '''
    data_size = 0
    seen = set()

    for curr_path, _, file_names in os.walk(dir_path):
        for file_name in file_names:
            file_path = os.path.join(curr_path, file_name)

            # Ignore symbolic links, since borg doesn't follow them
            if os.path.islink(file_path):
                continue

            stat = os.stat(file_path)

            # Visit each file once
            if stat.st_ino not in seen:
                seen.add(stat.st_ino)
                data_size += stat.st_size

    files_count = len(seen)

    return data_size, files_count


def get_network_status_monitor():
    global _network_status_monitor
    if _network_status_monitor is None:
        _network_status_monitor = NetworkStatusMonitor.get_network_status_monitor()
        logger.info('Using %s NetworkStatusMonitor implementation.', _network_status_monitor.__class__.__name__)
    return _network_status_monitor


def get_path_datasize(path):
    file_info = QFileInfo(path)
    data_size = 0

    if file_info.isDir():
        data_size, files_count = get_directory_size(file_info.absoluteFilePath())
        # logger.info("path (folder) %s %u elements size now=%u (%s)",
        #            file_info.absoluteFilePath(), files_count, data_size, pretty_bytes(data_size))
    else:
        # logger.info("path (file) %s size=%u", file_info.path(), file_info.size())
        data_size = file_info.size()
        files_count = 1

    return data_size, files_count


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
    dialog = QFileDialog(parent, title, os.path.expanduser('~'))
    dialog.setFileMode(QFileDialog.Directory if want_folder else QFileDialog.ExistingFiles)
    dialog.setParent(parent, QtCore.Qt.Sheet)
    if want_folder:
        dialog.setOption(QFileDialog.ShowDirsOnly)
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
                except (SSHException, UnicodeDecodeError, IsADirectoryError, IndexError):
                    continue
                except OSError as e:
                    if e.errno == errno.ENXIO:
                        # when key_file is a (ControlPath) socket
                        continue
                    else:
                        raise

    return available_private_keys


def sort_sizes(size_list):
    """ Sorts sizes with extensions. Assumes that size is already in largest unit possible """
    final_list = []
    for suffix in [" B", " KB", " MB", " GB", " TB"]:
        sub_list = [float(size[:-len(suffix)])
                    for size in size_list if size.endswith(suffix) and size[:-len(suffix)][-1].isnumeric()]
        sub_list.sort()
        final_list += [(str(size) + suffix) for size in sub_list]
        # Skip additional loops
        if len(final_list) == len(size_list):
            break
    return final_list


def pretty_bytes(size):
    """from https://stackoverflow.com/questions/12523586/
            python-format-size-application-converting-b-to-kb-mb-gb-tb/37423778"""
    if not isinstance(size, int):
        return ''
    power = 1000  # GiB is base 2**10, GB is base 10**3.
    n = 0
    Dic_powerN = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size >= power:
        size /= power
        n += 1
    try:
        unit = Dic_powerN[n]
        return f'{round(size, 1)} {unit}B'
    except KeyError as e:
        logger.error(e)
        return "NaN"


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

    system_wifis = get_network_status_monitor().get_known_wifis()
    if system_wifis is None:
        # Don't show any networks if we can't get the current list
        return []

    for wifi in system_wifis:
        db_wifi, created = WifiSettingModel.get_or_create(
            ssid=wifi.ssid,
            profile=profile.id,
            defaults={'last_connected': wifi.last_connected, 'allowed': True}
        )

        # update last connected time
        if not created and db_wifi.last_connected != wifi.last_connected:
            db_wifi.last_connected = wifi.last_connected
            db_wifi.save()

    # remove Wifis that were deleted in the system.
    deleted_wifis = WifiSettingModel.select() \
        .where(WifiSettingModel.ssid.not_in([wifi.ssid for wifi in system_wifis]))
    for wifi in deleted_wifis:
        wifi.delete_instance()

    return WifiSettingModel.select() \
        .where(WifiSettingModel.profile == profile.id).order_by(-WifiSettingModel.last_connected)


def parse_args():
    parser = argparse.ArgumentParser(description='Vorta Backup GUI for Borg.')
    parser.add_argument('--version', '-V',
                        action='store_true',
                        help="Show version and exit.")
    parser.add_argument('--daemonize', '-d',
                        action='store_true',
                        help="Fork to background and don't open window on startup.")
    parser.add_argument(
        '--create',
        dest='profile',
        help='Create a backup in the background using the given profile. '
        'Vorta must already be running for this to work.')

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


def uses_dark_mode():
    """
    This function detects if we are running in dark mode (e.g. macOS dark mode).
    """
    palette = QApplication.instance().palette()
    return palette.windowText().color().lightness() > palette.window().color().lightness()


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
        except (psutil.ZombieProcess, psutil.AccessDenied, psutil.NoSuchProcess):
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


def validate_passwords(first_pass, second_pass):
    ''' Validates the password for borg, do not use on single fields '''
    pass_equal = first_pass == second_pass
    pass_long = len(first_pass) > 8

    if not pass_long and not pass_equal:
        return trans_late('utils', "Passwords must be identical and greater than 8 characters long.")
    if not pass_equal:
        return trans_late('utils', "Passwords must be identical.")
    if not pass_long:
        return trans_late('utils', "Passwords must be greater than 8 characters long.")

    return ""


def display_password_backend(encryption):
    ''' Display password backend message based off current keyring '''
    # flake8: noqa E501
    if encryption != 'none':
        keyring = VortaKeyring.get_keyring()
        return trans_late('utils', "Storing the password in your password manager.") if keyring.is_primary else trans_late(
            'utils', 'Saving the password to disk. To store password more securely install a supported secret store such as KeepassXC')
    else:
        return ""
