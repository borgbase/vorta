import sys
from typing import Dict, List
from vorta.i18n import trans_late


def get_misc_settings() -> List[Dict[str, str]]:
    """
    Get the settings structure with default values.

    Returns
    -------
    List[Dict[str, str]]
        The settings in a json-like way.
    """
    # groups
    notifications = trans_late('settings', 'Notifications')
    startup = trans_late('settings', 'Startup')
    information = trans_late('settings', 'Information')
    security = trans_late('settings', 'Security')

    # Default settings for all platforms.
    settings = [
        {
            'key': 'enable_notifications',
            'value': True,
            'type': 'checkbox',
            'group': notifications,
            'label': trans_late('settings', 'Display notifications when background tasks fail'),
        },
        {
            'key': 'enable_notifications_success',
            'value': False,
            'type': 'checkbox',
            'group': notifications,
            'label': trans_late('settings', 'Also notify about successful background tasks'),
        },
        {
            'key': 'autostart',
            'value': False,
            'type': 'checkbox',
            'group': startup,
            'label': trans_late('settings', 'Automatically start Vorta at login'),
        },
        {
            'key': 'foreground',
            'value': True,
            'type': 'checkbox',
            'group': startup,
            'label': trans_late('settings', 'Open main window on startup'),
        },
        {
            'key': 'get_srcpath_datasize',
            'value': True,
            'type': 'checkbox',
            'group': information,
            'label': trans_late('settings', 'Get statistics of file/folder when added'),
        },
        {
            'key': 'use_system_keyring',
            'value': True,
            'type': 'checkbox',
            'group': security,
            'label': trans_late(
                'settings',
                'Store repository passwords in system keychain, if available',
            ),
        },
        {
            'key': 'override_mount_permissions',
            'value': False,
            'type': 'checkbox',
            'group': security,
            'label': trans_late(
                'settings',
                'Try to replace existing permissions when mounting an archive',
            ),
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
    ]
    if sys.platform == 'darwin':
        settings += [
            {
                'key': 'check_for_updates',
                'value': True,
                'type': 'checkbox',
                'label': trans_late('settings', 'Check for updates on startup'),
            },
            {
                'key': 'updates_include_beta',
                'value': False,
                'type': 'checkbox',
                'label': trans_late('settings', 'Include pre-release versions when checking for updates'),
            },
        ]
    else:
        settings += [
            {
                'key': 'enable_background_question',
                'value': True,
                'type': 'checkbox',
                'label': trans_late(
                    'settings',
                    "If the system tray isn't available, " "ask whether to continue in the background " "on exit",
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
