import sys
from pathlib import Path
from PyQt5 import QtCore

LINUX_STARTUP_FILE = """\
[Desktop Entry]
Name=Vorta
GenericName=Backup Software
Exec=vorta
Terminal=false
Icon=vorta
Categories=Utility
Type=Application
StartupNotify=false
X-GNOME-Autostart-enabled=true
"""


def open_app_at_startup(enabled=True):
    """
    This function adds/removes the current app bundle from Login items in macOS or most Linux desktops
    """
    if sys.platform == 'darwin':
        from Foundation import NSDictionary

        from Cocoa import NSBundle, NSURL
        from CoreFoundation import kCFAllocatorDefault
        # CF = CDLL(find_library('CoreFoundation'))
        from LaunchServices import (LSSharedFileListCreate, kLSSharedFileListSessionLoginItems,
                                    LSSharedFileListInsertItemURL, kLSSharedFileListItemHidden,
                                    kLSSharedFileListItemLast, LSSharedFileListItemRemove)

        app_path = NSBundle.mainBundle().bundlePath()
        url = NSURL.alloc().initFileURLWithPath_(app_path)
        login_items = LSSharedFileListCreate(kCFAllocatorDefault, kLSSharedFileListSessionLoginItems, None)
        props = NSDictionary.dictionaryWithObject_forKey_(True, kLSSharedFileListItemHidden)

        new_item = LSSharedFileListInsertItemURL(login_items, kLSSharedFileListItemLast,
                                                 None, None, url, props, None)
        if not enabled:
            LSSharedFileListItemRemove(login_items, new_item)

    elif sys.platform.startswith('linux'):
        config_path = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.ConfigLocation)
        autostart_file_path = Path(config_path) / 'autostart' / 'vorta.desktop'
        if enabled:
            autostart_file_path.write_text(LINUX_STARTUP_FILE)
        else:
            if autostart_file_path.exists():
                autostart_file_path.unlink()
