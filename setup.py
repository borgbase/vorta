from setuptools import setup, find_packages
import os
import sys

DATA_FILES = []
CURRENT_DIR = os.getcwd()

# Install icons and desktop files, not sure if /usr/local/share is constant
if sys.platform == 'linux':
    if 'bdist_wheel' in sys.argv:
        sys.exit("Building wheels is disabled")

    if os.geteuid() == 0:
        xdg_data_dir = '/usr/local/share'
    else:
        xdg_data_dir = os.environ['XDG_DATA_HOME'] if os.environ.get(
            'XDG_DATA_HOME') else os.path.join(os.environ['HOME'], '.local/share')
    application_dir = os.path.join(xdg_data_dir, "applications")
    icon_dir = os.path.join(xdg_data_dir, "icons", "hicolor", "scalable", "apps")

    if not os.path.exists(application_dir):
        os.makedirs(application_dir)
    if not os.path.exists(icon_dir):
        os.makedirs(icon_dir)

    # Rename files to appropriate names
    os.rename(os.path.join(CURRENT_DIR, 'package/icon.svg'),
              os.path.join(CURRENT_DIR, 'package/com.borgbase.Vorta.svg'))

    DATA_FILES = [(application_dir, ['src/vorta/assets/metadata/com.borgbase.Vorta.desktop']),
                  (icon_dir, ['package/com.borgbase.Vorta.svg'])]

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
