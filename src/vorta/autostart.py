import sys
from pathlib import Path

LINUX_STARTUP_FILE = """\
[Desktop Entry]
Name=Vorta
GenericName=Backup Software
Exec={}
Terminal=false
Icon=vorta
Categories=Utility
Type=Application
StartupNotify=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=20
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
        autostart_path = Path.home() / '.config' / 'autostart'

        if not autostart_path.exists():
            autostart_path.mkdir()

        autostart_file_path = autostart_path / 'vorta.desktop'

        if enabled:
            if Path('/.flatpak-info').exists():
                # Vorta runs as flatpak
                autostart_file_path.write_text(LINUX_STARTUP_FILE.format('flatpak run com.borgbase.vorta'))
            else:
                autostart_file_path.write_text(LINUX_STARTUP_FILE.format('vorta'))

        else:
            if autostart_file_path.exists():
                autostart_file_path.unlink()
