import sys
from shutil import copy2
import os
from pathlib import Path

AUTOSTART_DELAY = """StartupNotify=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=20"""
IS_FLATPAK = Path('/.flatpak-info').exists()


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
        with open(os.path.join(os.path.dirname(__file__),
                               "assets/metadata/com.borgbase.Vorta.desktop")) as desktop_file:
            desktop_file_text = desktop_file.read()

            # Find XDG_CONFIG_HOME unless when running in flatpak
            if IS_FLATPAK:
                config_path = Path.home() / '.config'
            else:
                config_path = Path(os.environ.get(
                    "XDG_CONFIG_HOME", os.path.expanduser("~"))) / '.config'

            autostart_path = config_path / "autostart"
            autostart_file_path = autostart_path / 'vorta.desktop'

            if not autostart_path.exists():
                autostart_path.mkdir(parents=True)

            if enabled:
                # Replace to for flatpak if appropriate and start in background
                desktop_file_text = desktop_file_text.replace(
                    "Exec=vorta", "Exec=flatpak run com.borgbase.Vorta --daemonize" if IS_FLATPAK
                    else "Exec=vorta --daemonize")
                # Add autostart delay
                desktop_file_text += (AUTOSTART_DELAY)
                # Write desktop file
                autostart_file_path.write_text(desktop_file_text)
            else:
                if autostart_file_path.exists():
                    autostart_file_path.unlink()


def desktop_application(enabled=True):
    # Find XDG_DATA_HOME unless when running in flatpak
    if IS_FLATPAK:
        data_path = Path.home() / ".local" / "share"
    else:
        data_path = Path(os.environ.get(
            "XDG_DATA_HOME", os.path.expanduser("~"))) / ".local" / "share"

    desktop_path = data_path / "applications"
    icon_path = data_path / "icons" / "hicolor" / "scalable" / "apps"

    if not icon_path.exists():
        icon_path.mkdir(parents=True)
    if not desktop_path.exists():
        desktop_path.mkdir(parents=True)

    if enabled:
        # Copy icons
        main_icon_path = Path(__file__).parent / "assets" / "metadata" / "com.borgbase.Vorta.svg"
        symbolic_icon_path = Path(__file__).parent / "assets" / "metadata" / "com.borgbase.Vorta-symbolic.svg"
        desktop_file_path = Path(__file__).parent / "assets" / "metadata" / "com.borgbase.Vorta.desktop"
        copy2(main_icon_path, icon_path)
        copy2(symbolic_icon_path, icon_path)
        copy2(desktop_file_path, desktop_path)
    else:
        main_icon_path = icon_path / "com.borgbase.Vorta.svg"
        symbolic_icon_path = icon_path / "com.borgbase.Vorta-symbolic.svg"
        desktop_file_path = desktop_path / "com.borgbase.Vorta.desktop"

        if desktop_file_path.exists():
            desktop_file_path.unlink()
        if symbolic_icon_path.exists():
            symbolic_icon_path.unlink()
        if main_icon_path.exists():
            main_icon_path.unlink()
