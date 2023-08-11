import argparse
import errno
import fnmatch
import getpass
import math
import os
import re
import socket
import sys
import unicodedata
from datetime import datetime as dt
from functools import reduce
from typing import Any, Callable, Iterable, List, Optional, Tuple, TypeVar

import psutil
from PyQt6 import QtCore
from PyQt6.QtCore import QFileInfo, QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QFileDialog, QSystemTrayIcon

from vorta.borg._compatibility import BorgCompatibility
from vorta.log import logger
from vorta.network_status.abc import NetworkStatusMonitor

# Used to store whether a user wanted to override the
# default directory for the --development flag
DEFAULT_DIR_FLAG = object()
METRIC_UNITS = ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
NONMETRIC_UNITS = ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi']

borg_compat = BorgCompatibility()
_network_status_monitor = None


class FilePathInfoAsync(QThread):
    signal = pyqtSignal(str, str, str)

    def __init__(self, path, exclude_patterns_str):
        self.path = path
        QThread.__init__(self)
        self.exiting = False
        self.exclude_patterns = []
        for _line in (exclude_patterns_str or '').splitlines():
            line = _line.strip()
            if line != '':
                self.exclude_patterns.append(line)

    def run(self):
        # logger.info("running thread to get path=%s...", self.path)
        self.size, self.files_count = get_path_datasize(self.path, self.exclude_patterns)
        self.signal.emit(self.path, str(self.size), str(self.files_count))


def normalize_path(path):
    """normalize paths for MacOS (but do nothing on other platforms)"""
    # HFS+ converts paths to a canonical form, so users shouldn't be required to enter an exact match.
    # Windows and Unix filesystems allow different forms, so users always have to enter an exact match.
    return unicodedata.normalize('NFD', path) if sys.platform == 'darwin' else path


# prepare patterns as borg does
# see `FnmatchPattern._prepare` at
# https://github.com/borgbackup/borg/blob/master//src/borg/patterns.py
def prepare_pattern(pattern):
    """Prepare and process fnmatch patterns as borg does"""
    if pattern.endswith(os.path.sep):
        # trailing sep indicates that the contents should be excluded
        # but not the directory it self.
        pattern = os.path.normpath(pattern).rstrip(os.path.sep)
        pattern += os.path.sep + '*' + os.path.sep
    else:
        pattern = os.path.normpath(pattern) + os.path.sep + '*'

    pattern = pattern.lstrip(os.path.sep)  # sep at beginning is removed
    return re.compile(fnmatch.translate(pattern))


def match(pattern: re.Pattern, path: str):
    """Check whether a path matches the given pattern."""
    path = path.lstrip(os.path.sep) + os.path.sep
    return pattern.match(path) is not None


def get_directory_size(dir_path, exclude_patterns):
    '''Get number of files only and total size in bytes from a path.
    Based off https://stackoverflow.com/a/17936789'''
    exclude_patterns = [prepare_pattern(p) for p in exclude_patterns]

    data_size_filtered = 0
    seen = set()
    seen_filtered = set()

    for dir_path, subdirectories, file_names in os.walk(dir_path, topdown=True):
        is_excluded = False
        for pattern in exclude_patterns:
            if match(pattern, dir_path):
                is_excluded = True
                break

        if is_excluded:
            subdirectories.clear()  # so that os.walk won't walk them
            continue

        for file_name in file_names:
            file_path = os.path.join(dir_path, file_name)

            # Ignore symbolic links, since borg doesn't follow them
            if os.path.islink(file_path):
                continue

            is_excluded = False
            for pattern in exclude_patterns:
                if match(pattern, file_path):
                    is_excluded = True
                    break

            try:
                stat = os.stat(file_path)
                if stat.st_ino not in seen:  # Visit each file only once
                    # this won't add the size of a hardlinked file
                    seen.add(stat.st_ino)
                    if not is_excluded:
                        data_size_filtered += stat.st_size
                        seen_filtered.add(stat.st_ino)
            except (FileNotFoundError, PermissionError):
                continue

    files_count_filtered = len(seen_filtered)

    return data_size_filtered, files_count_filtered


def get_network_status_monitor():
    global _network_status_monitor
    if _network_status_monitor is None:
        _network_status_monitor = NetworkStatusMonitor.get_network_status_monitor()
        logger.info(
            'Using %s NetworkStatusMonitor implementation.',
            _network_status_monitor.__class__.__name__,
        )
    return _network_status_monitor


def get_path_datasize(path, exclude_patterns):
    file_info = QFileInfo(path)

    if file_info.isDir():
        data_size, files_count = get_directory_size(file_info.absoluteFilePath(), exclude_patterns)
    else:
        data_size = file_info.size()
        files_count = 1

    return data_size, files_count


def nested_dict():
    """
    Combination of two idioms to quickly build dicts from lists of keys:

    - https://stackoverflow.com/a/16724937/3983708
    - https://stackoverflow.com/a/14692747/3983708
    """
    return dict()


def get_dict_from_list(dataDict, mapList):
    return reduce(lambda d, k: d.setdefault(k, {}), mapList, dataDict)


def choose_file_dialog(parent, title, want_folder=True):
    dialog = QFileDialog(parent, title, os.path.expanduser('~'))
    dialog.setFileMode(QFileDialog.FileMode.Directory if want_folder else QFileDialog.FileMode.ExistingFiles)
    dialog.setParent(parent, QtCore.Qt.WindowType.Sheet)
    if want_folder:
        dialog.setOption(QFileDialog.Option.ShowDirsOnly)
    return dialog


def is_ssh_private_key_file(filepath: str) -> bool:
    """Check if the file is a SSH key."""
    try:
        with open(filepath, 'r') as f:
            first_line = f.readline()
        pattern = r'^-----BEGIN(\s\w+)? PRIVATE KEY-----'
        return re.match(pattern, first_line) is not None
    except UnicodeDecodeError:
        return False


def get_private_keys() -> List[str]:
    """Find SSH keys in standard folder."""

    ssh_folder = os.path.expanduser('~/.ssh')

    available_private_keys = []
    if os.path.isdir(ssh_folder):
        for key in os.listdir(ssh_folder):
            key_file = os.path.join(ssh_folder, key)
            if not os.path.isfile(key_file):
                continue
            # ignore config, known_hosts*, *.pub, etc.
            if key.endswith('.pub') or key.startswith('known_hosts') or key == 'config':
                continue
            try:
                if is_ssh_private_key_file(key_file):
                    if os.stat(key_file).st_mode & 0o077 == 0:
                        available_private_keys.append(key)
                    else:
                        logger.warning(f'Permissions for {key_file} are too open.')
                else:
                    logger.debug(f'Not a private SSH key file: {key}')
            except PermissionError:
                logger.warning(f'Permission error while opening file: {key_file}', exc_info=True)
                continue
            except OSError as e:
                if e.errno == errno.ENXIO:
                    # when key_file is a (ControlPath) socket
                    continue
                raise

    return available_private_keys


def sort_sizes(size_list):
    """Sorts sizes with extensions. Assumes that size is already in largest unit possible"""
    final_list = []
    for suffix in [" B", " KB", " MB", " GB", " TB", " PB", " EB", " ZB", " YB"]:
        sub_list = [
            float(size[: -len(suffix)])
            for size in size_list
            if size.endswith(suffix) and size[: -len(suffix)][-1].isnumeric()
        ]
        sub_list.sort()
        final_list += [(str(size) + suffix) for size in sub_list]
        # Skip additional loops
        if len(final_list) == len(size_list):
            break
    return final_list


Number = TypeVar("Number", int, float)


def clamp(n: Number, min_: Number, max_: Number) -> Number:
    """Restrict the number n inside a range"""
    return min(max_, max(n, min_))


def find_best_unit_for_sizes(sizes: Iterable[int], metric: bool = True, precision: int = 1) -> int:
    """
    Selects the index of the biggest unit (see the lists in the pretty_bytes function) capable of
    representing the smallest size in the sizes iterable.
    """
    min_size = min((s for s in sizes if isinstance(s, int)), default=None)
    return find_best_unit_for_size(min_size, metric=metric, precision=precision)


def find_best_unit_for_size(size: Optional[int], metric: bool = True, precision: int = 1) -> int:
    """
    Selects the index of the biggest unit (see the lists in the pretty_bytes function) capable of
    representing the passed size.
    """
    if not isinstance(size, int) or size == 0:  # this will also take care of the None case
        return 0
    power = 10**3 if metric else 2**10
    n = math.floor(math.log(abs(size) * 10**precision, power))
    return n


def pretty_bytes(
    size: int, metric: bool = True, sign: bool = False, precision: int = 1, fixed_unit: Optional[int] = None
) -> str:
    """
    Formats the size with the requested unit and precision. The find_best_size_unit function
    can be used to find the correct unit for a list of sizes. If no fixed_unit is passed it will
    find the biggest unit to represent the size
    """
    if not isinstance(size, int):
        return ''
    prefix = '+' if sign and size > 0 else ''
    power, units = (10**3, METRIC_UNITS) if metric else (2**10, NONMETRIC_UNITS)
    if fixed_unit is None:
        n = find_best_unit_for_size(size, metric=metric, precision=precision)
    else:
        n = fixed_unit
    n = clamp(n, 0, len(units) - 1)
    size /= power**n
    try:
        unit = units[n]
        digits = f'%.{precision}f' % (round(size, precision))
        return f'{prefix}{digits} {unit}B'
    except KeyError as error:
        logger.error(error)
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
    """
    Get Wifi networks known to the OS (only current one on macOS) and
    merge with networks from other profiles. Update last connected time.
    """

    from vorta.store.models import WifiSettingModel

    # Pull networks known to OS and all other backup profiles
    system_wifis = get_network_status_monitor().get_known_wifis()
    from_other_profiles = WifiSettingModel.select().where(WifiSettingModel.profile != profile.id).execute()

    for wifi in list(from_other_profiles) + system_wifis:
        db_wifi, created = WifiSettingModel.get_or_create(
            ssid=wifi.ssid,
            profile=profile.id,
            defaults={'last_connected': wifi.last_connected, 'allowed': True},
        )

        # Update last connected time
        if not created and db_wifi.last_connected != wifi.last_connected:
            db_wifi.last_connected = wifi.last_connected
            db_wifi.save()

    # Finally return list of networks and settings for that profile
    return (
        WifiSettingModel.select()
        .where(WifiSettingModel.profile == profile.id)
        .order_by(-WifiSettingModel.last_connected)
    )


def parse_args():
    parser = argparse.ArgumentParser(description='Vorta Backup GUI for Borg.')
    parser.add_argument('--version', '-V', action='store_true', help="Show version and exit.")
    parser.add_argument(
        '--daemonize',
        '-d',
        action='store_true',
        help="Fork to background and don't open window on startup.",
    )
    parser.add_argument(
        '--create',
        dest='profile',
        help='Create a backup in the background using the given profile. '
        'Vorta must already be running for this to work.',
    )
    # the "development" attribute will be None if the flag is not called
    # if the flag is called without an extra argument, the "development" attribute
    # will be set to the value of DEFAULT_DIR_FLAG.
    # if the flag is called with an extra argument, the "development" attribute
    # will be set to that argument
    parser.add_argument(
        '--development',
        '-D',
        nargs='?',
        const=DEFAULT_DIR_FLAG,
        metavar="CONFIG_DIRECTORY",
        help='Start vorta in a local development environment. '
        'All log, config, cache, and temp files will be stored within the project tree. '
        'You can follow this flag with an optional path and it will store the files in the provided location.',
    )
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


# patched socket.getfqdn() - see https://bugs.python.org/issue5004
# Reused with permission from https://github.com/borgbackup/borg/blob/master/src/borg/platform/base.py (BSD-3-Clause)
def _getfqdn(name=""):
    """Get fully qualified domain name from name.
    An empty argument is interpreted as meaning the local host.
    """
    name = name.strip()
    if not name or name == "0.0.0.0":
        name = socket.gethostname()
    try:
        addrs = socket.getaddrinfo(name, None, 0, socket.SOCK_DGRAM, 0, socket.AI_CANONNAME)
    except OSError:
        pass
    else:
        for addr in addrs:
            if addr[3]:
                name = addr[3]
                break
    return name


def format_archive_name(profile, archive_name_tpl):
    """
    Generate an archive name. Default set in models.BackupProfileModel
    """
    hostname = socket.gethostname()
    hostname = hostname.split(".")[0]
    available_vars = {
        'hostname': hostname,
        'fqdn': _getfqdn(hostname),
        'profile_id': profile.id,
        'profile_slug': profile.slug(),
        'now': dt.now(),
        'utc_now': dt.utcnow(),
        'user': getpass.getuser(),
    }
    return archive_name_tpl.format(**available_vars)


SHELL_PATTERN_ELEMENT = re.compile(r'([?\[\]*])')


def get_mount_points(repo_url):
    mount_points = {}
    repo_mounts = []
    for proc in psutil.process_iter():
        try:
            name = proc.name()
            if name == 'borg' or name.startswith('python'):
                if 'mount' not in proc.cmdline():
                    continue

                if borg_compat.check('V2'):
                    # command line syntax:
                    # `borg mount -r <repo> <mountpoint> <path> (-a <archive_pattern>)`
                    cmd = proc.cmdline()
                    if repo_url in cmd:
                        i = cmd.index(repo_url)
                        if len(cmd) > i + 1:
                            mount_point = cmd[i + 1]

                            # Archive mount?
                            ao = '-a' in cmd
                            if ao or '--match-archives' in cmd:
                                i = cmd.index('-a' if ao else '--match-archives')
                                if len(cmd) >= i + 1 and not SHELL_PATTERN_ELEMENT.search(cmd[i + 1]):
                                    mount_points[mount_point] = cmd[i + 1]
                            else:
                                repo_mounts.append(mount_point)
                else:
                    for idx, parameter in enumerate(proc.cmdline()):
                        if parameter.startswith(repo_url):
                            # mount from this repo

                            # The borg mount command specifies that the mount_point
                            # parameter comes after the archive name
                            if len(proc.cmdline()) > idx + 1:
                                mount_point = proc.cmdline()[idx + 1]

                                # archive or full mount?
                                if parameter[len(repo_url) :].startswith('::'):
                                    archive_name = parameter[len(repo_url) + 2 :]
                                    mount_points[archive_name] = mount_point
                                    break
                                else:
                                    # repo mount point
                                    repo_mounts.append(mount_point)

        except (psutil.ZombieProcess, psutil.AccessDenied, psutil.NoSuchProcess):
            # Getting process details may fail (e.g. zombie process on macOS)
            # or because the process is owned by another user.
            # Also see https://github.com/giampaolo/psutil/issues/783
            continue

    return mount_points, repo_mounts


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


def search(key, iterable: Iterable, func: Callable = None) -> Tuple[int, Any]:
    """
    Search for a key in an iterable.

    Before comparing an item with the key `func` is called on the item.

    Parameters
    ----------
    key : Any
        The key to search for.
    iterable : Iterable
        The iterable to search in.
    func : Callable, optional
        The function to apply, by default None

    Returns
    -------
    Tuple[int, Any] or None
        The index and the item in case of a match else `None`.
    """
    if not func:

        def func(x):
            return x

    for i, item in enumerate(iterable):
        if func(item) == key:
            return i, item

    return None
