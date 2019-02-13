import sys
from pathlib import Path
from PyQt5 import QtCore
from setuptools import Distribution
from setuptools.command.install import install


GNOME_STARTUP_FILE = """[Desktop Entry]
Name=Vorta
GenericName=Backup Software
"Exec={}/vorta
Terminal=false
Icon=vorta
Categories=Utility
Type=Application
StartupNotify=false
X-GNOME-Autostart-enabled=true
"""


def open_app_at_startup(enabled=True):
    """
    This function adds/removes the current app bundle from Login items in macOS or Linux (Gnome desktop)
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
            dir_entry_point = get_setuptools_script_dir()
            autostart_file_path.write_text(GNOME_STARTUP_FILE.format(dir_entry_point))
        else:
            if autostart_file_path.exists():
                autostart_file_path.unlink()


# Get entry point of vorta
# From https://stackoverflow.com/questions/
#      25066084/get-entry-point-script-file-location-in-setuputils-package
class OnlyGetScriptPath(install):
    def run(self):
        # does not call install.run() by design
        self.distribution.install_scripts = self.install_scripts


def get_setuptools_script_dir():
    dist = Distribution({'cmdclass': {'install': OnlyGetScriptPath}})
    dist.dry_run = True  # not sure if necessary, but to be safe
    dist.parse_config_files()
    command = dist.get_command_obj('install')
    command.ensure_finalized()
    command.run()
    return dist.install_scripts
