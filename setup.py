from setuptools import setup, find_packages
import os
import sys

DATA_FILES = []
CURRENT_DIR = os.getcwd()

# Install icons and desktop files, not sure if /usr/local/share is constant
if sys.platform == 'linux':
    if 'bdist_wheel' in sys.argv:
        raise RuntimeError("This setup.py does not support wheels")

    if os.geteuid() == 0:
        XDG_DATA_DIR = '/usr/local/share'
    else:
        XDG_DATA_DIR = os.environ['XDG_DATA_HOME'] if os.environ.get(
            'XDG_DATA_HOME') else os.path.join(os.environ['HOME'], '.local/share')
    APPLICATION_DIR = os.path.join(XDG_DATA_DIR, "applications")
    ICON_DIR = os.path.join(XDG_DATA_DIR, "icons", "hicolor", "scalable", "apps")

    if not os.path.exists(APPLICATION_DIR):
        os.makedirs(APPLICATION_DIR)
    if not os.path.exists(ICON_DIR):
        os.makedirs(ICON_DIR)

    # Rename files to appropriate names
    os.rename(os.path.join(CURRENT_DIR, 'package/icon.svg'),
              os.path.join(CURRENT_DIR, 'package/com.borgbase.Vorta.svg'))

    DATA_FILES = [(APPLICATION_DIR, ['src/vorta/assets/metadata/com.borgbase.Vorta.desktop']),
                  (ICON_DIR, ['package/com.borgbase.Vorta.svg'])]

setup(
    include_package_data=True,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    data_files=DATA_FILES,
    package_data={'vorta.i18n': ['qm/*.qm']}
)

if sys.platform == 'linux':
    # Unrename files
    os.rename(os.path.join(CURRENT_DIR, 'package/com.borgbase.Vorta.svg'),
              os.path.join(CURRENT_DIR, 'package/icon.svg'))
