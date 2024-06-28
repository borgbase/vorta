import argparse
import errno
import getpass
import math
import os
import re
import socket
import sys
from datetime import datetime as dt
from functools import reduce
from typing import Any, Callable, Iterable, List, Optional, Tuple, TypeVar

from PyQt6 import QtCore
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QSystemTrayIcon,
)

from vorta.borg._compatibility import BorgCompatibility
from vorta.log import logger
from vorta.network_status.abc import NetworkStatusMonitor

# Used to store whether a user wanted to override the
# default directory for the --development flag
DEFAULT_DIR_FLAG = object()
METRIC_UNITS = ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
NONMETRIC_UNITS = ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi']
_network_status_monitor = None

borg_compat = BorgCompatibility()


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


Number = TypeVar("Number", int, float)


def clamp(n: Number, min_: Number, max_: Number) -> Number:
    """Restrict the number n inside a range"""
    return min(max_, max(n, min_))


def get_network_status_monitor():
    global _network_status_monitor
    if _network_status_monitor is None:
        _network_status_monitor = NetworkStatusMonitor.get_network_status_monitor()
        logger.info(
            'Using %s NetworkStatusMonitor implementation.',
            _network_status_monitor.__class__.__name__,
        )
    return _network_status_monitor


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
