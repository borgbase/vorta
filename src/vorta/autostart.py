import sys

AUTOSTART_DELAY = """StartupNotify=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=20"""


def open_app_at_startup(enabled=True):
    """
    On macOS, this function adds/removes the current app bundle from Login items
    while on Linux it adds a .desktop file at ~/.config/autostart
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
        from appdirs import user_config_dir
        from pathlib import Path

        is_flatpak = Path('/.flatpak-info').exists()

        with open(Path(__file__).parent / "assets/metadata/com.borgbase.Vorta.desktop") as desktop_file:
            desktop_file_text = desktop_file.read()

        # Find XDG_CONFIG_HOME unless when running in flatpak
        if is_flatpak:
            autostart_path = Path.home() / '.config' / 'autostart'
        else:
            autostart_path = Path(user_config_dir("autostart"))

        if not autostart_path.exists():
            autostart_path.mkdir()

        autostart_file_path = autostart_path / 'vorta.desktop'

        if enabled:
            # Replace command for flatpak if appropriate and start in background
            desktop_file_text = desktop_file_text.replace(
                "Exec=vorta", "Exec=flatpak run com.borgbase.Vorta --daemonize" if is_flatpak
                else "Exec=vorta --daemonize")
            # Add autostart delay
            desktop_file_text += (AUTOSTART_DELAY)

            autostart_file_path.write_text(desktop_file_text)
        elif autostart_file_path.exists():
            autostart_file_path.unlink()
