from __future__ import annotations

import logging
import sys
from typing import Any

from PyQt6.QtCore import QT_TRANSLATE_NOOP

from vorta.store.models import SettingsModel

logger = logging.getLogger(__name__)


def get_misc_settings() -> list[dict[str, Any]]:
    """
    Get the settings structure with default values.

    Returns
    -------
    list[dict[str, Any]]
        The settings in a json-like way.
    """
    # groups
    notifications = QT_TRANSLATE_NOOP('settings', 'Notifications')
    startup = QT_TRANSLATE_NOOP('settings', 'Startup')
    information = QT_TRANSLATE_NOOP('settings', 'Information')
    security = QT_TRANSLATE_NOOP('settings', 'Security')
    updates = QT_TRANSLATE_NOOP('settings', 'Updates')

    # Default settings for all platforms.
    settings = [
        {
            'key': 'enable_notifications',
            'value': True,
            'type': 'checkbox',
            'group': notifications,
            'label': QT_TRANSLATE_NOOP('settings', 'Display notifications when background tasks fail'),
        },
        {
            'key': 'enable_notifications_success',
            'value': False,
            'type': 'checkbox',
            'group': notifications,
            'label': QT_TRANSLATE_NOOP('settings', 'Notify about successful background tasks'),
        },
        {
            'key': 'autostart',
            'value': False,
            'type': 'checkbox',
            'group': startup,
            'label': QT_TRANSLATE_NOOP('settings', 'Automatically start Vorta at login'),
            'tooltip': QT_TRANSLATE_NOOP('settings', 'Add Vorta to the systems autostart list'),
        },
        {
            'key': 'foreground',
            'value': True,
            'type': 'checkbox',
            'group': startup,
            'label': QT_TRANSLATE_NOOP('settings', 'Show main window of Vorta on launch'),
            'tooltip': QT_TRANSLATE_NOOP(
                'settings',
                'Make Vorta appear on screen instead of minimizing to system tray',
            ),
        },
        {
            'key': 'get_srcpath_datasize',
            'value': True,
            'type': 'checkbox',
            'group': information,
            'label': QT_TRANSLATE_NOOP('settings', 'Get statistics of file/folder when added'),
            'tooltip': QT_TRANSLATE_NOOP(
                'settings', 'When adding a new source, calculate its size and the number of files.'
            ),
        },
        {
            'key': 'enable_fixed_units',
            'value': False,
            'type': 'checkbox',
            'group': information,
            'label': QT_TRANSLATE_NOOP('settings', 'Use the same unit of measurement for archive sizes'),
            'tooltip': QT_TRANSLATE_NOOP(
                'settings',
                'When enabled, all archive sizes will use the same unit of measurement, '
                'such as  KB or MB. This can make archive sizes easier to compare.',
            ),
        },
        {
            'key': 'use_system_keyring',
            'value': True,
            'type': 'checkbox',
            'group': security,
            'label': QT_TRANSLATE_NOOP('settings', 'Store repository passwords in system keychain, if available'),
            'tooltip': QT_TRANSLATE_NOOP(
                'settings', "Otherwise Vorta's configuration database stores the password in plaintext."
            ),
        },
        {
            'key': 'override_mount_permissions',
            'value': False,
            'type': 'checkbox',
            'group': security,
            'label': QT_TRANSLATE_NOOP(
                'settings',
                'Try to replace file permissions when mounting an archive',
            ),
            'tooltip': QT_TRANSLATE_NOOP('settings', 'Set owner to current user and umask to 0277'),
        },
        {
            'key': 'previous_profile_id',
            'str_value': '1',
            'type': 'internal',
            'label': 'Previously selected profile',
        },
        {
            'key': 'previous_window_width',
            'str_value': '800',
            'type': 'internal',
            'label': 'Previous window width',
        },
        {
            'key': 'previous_window_height',
            'str_value': '600',
            'type': 'internal',
            'label': 'Previous window height',
        },
        {
            'key': 'diff_files_display_mode',
            'str_value': '0',
            'type': 'internal',
            'label': 'Diff dialog display mode',
        },
        {
            'key': 'extract_files_display_mode',
            'str_value': '0',
            'type': 'internal',
            'label': 'Extract dialog display mode',
        },
        {
            'key': 'sourcetab_sort_column',
            'str_value': '0',
            'type': 'internal',
            'label': 'Source Tab Sort Column',
        },
        {
            'key': 'sourcetab_sort_order',
            'str_value': '0',
            'type': 'internal',
            'label': 'Source Tab Sort Order',
        },
    ]
    if sys.platform == 'darwin':
        settings += [
            {
                'key': 'check_for_updates',
                'value': True,
                'type': 'checkbox',
                'group': updates,
                'label': QT_TRANSLATE_NOOP('settings', 'Check for updates on startup'),
                'tooltip': QT_TRANSLATE_NOOP('settings', 'Uses Sparkle to find new updates published on Github.'),
            },
            {
                'key': 'updates_include_beta',
                'value': False,
                'type': 'checkbox',
                'group': updates,
                'label': QT_TRANSLATE_NOOP('settings', 'Include pre-release versions when checking for updates'),
                'tooltip': QT_TRANSLATE_NOOP('settings', 'Needs Vorta restart to apply.'),
            },
            {
                'key': 'check_full_disk_access',
                'value': True,
                'type': 'checkbox',
                'group': startup,
                'label': QT_TRANSLATE_NOOP(
                    'settings',
                    'Check for Full Disk Access on startup',
                ),
                'tooltip': QT_TRANSLATE_NOOP(
                    'settings', 'Alerts user when full disk access permission has not been provided'
                ),
            },
        ]
    else:
        settings += [
            {
                'key': 'enable_background_question',
                'value': True,
                'type': 'checkbox',
                'label': QT_TRANSLATE_NOOP(
                    'settings',
                    "If the system tray isn't available, ask whether to continue in the background on exit",
                ),
            },
            {
                'key': 'disable_background_state',
                'value': False,
                'type': 'internal',
                'label': 'Previous background exit button state',
            },
        ]
    return settings


def get_grouped_checkbox_settings() -> list[tuple[str, list[SettingsModel]]]:
    """
    Return checkbox settings grouped by their group label, ready for the view to render.

    Filters out:
      - DB rows whose key is not declared in get_misc_settings() — these are legacy /
        deprecated settings left over from previous installs.
      - Groups that become empty after filtering (e.g. the 'Updates' group on non-darwin
        platforms, where none of its keys are declared in get_misc_settings()).

    The returned list preserves the alphabetical group order of the underlying query.
    """
    valid_keys = {entry['key'] for entry in get_misc_settings()}

    rows = (
        SettingsModel.select()
        .where((SettingsModel.type == 'checkbox') & (SettingsModel.group != ''))
        .order_by(SettingsModel.group.asc())
    )

    grouped: dict[str, list[SettingsModel]] = {}
    for row in rows:
        if row.key not in valid_keys:
            logger.warning('Unknown setting %s', row.key)
            continue
        grouped.setdefault(row.group, []).append(row)

    return list(grouped.items())
