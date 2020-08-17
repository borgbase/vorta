# -*- mode: python -*-

import os
import sys
from pathlib import Path

from vorta.config import (
    APP_NAME,
    APP_ID_DARWIN
)
from vorta._version import __version__ as APP_VERSION

BLOCK_CIPHER = None
APP_APPCAST_URL = 'https://borgbase.github.io/vorta/appcast.xml'


# it is assumed that the cwd is the git repo dir:
SRC_DIR = os.path.join(os.getcwd(), 'src', 'vorta')

a = Analysis([os.path.join(SRC_DIR, '__main__.py')],
             pathex=[SRC_DIR],
             binaries=[],
             datas=[
                (os.path.join(SRC_DIR, 'assets/UI/*'), 'assets/UI'),
                (os.path.join(SRC_DIR, 'assets/icons/*'), 'assets/icons'),
                (os.path.join(SRC_DIR, 'i18n/qm/*'), 'vorta/i18n/qm'),
             ],
             hiddenimports=[
                 'vorta.views.dark.collection_rc',
                 'vorta.views.light.collection_rc',
                 'pkg_resources.py2_warn',
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=BLOCK_CIPHER,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data, cipher=BLOCK_CIPHER)

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name=f"vorta-{sys.platform}",
          bootloader_ignore_signals=True,
          console=False,
          debug=False,
          strip=False,
          upx=True)

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               debug=False,
               strip=False,
               upx=False,
               name='vorta')

app = BUNDLE(coll,
             name='Vorta.app',
             icon='icon.icns',
             bundle_identifier=None,
             info_plist={
                 'CFBundleName': APP_NAME,
                 'CFBundleDisplayName': APP_NAME,
                 'CFBundleIdentifier': APP_ID_DARWIN,
                 'NSHighResolutionCapable': 'True',
                 'NSRequiresAquaSystemAppearance': 'False',
                 'LSUIElement': '1',
                 'LSMinimumSystemVersion': '10.14',
                 'CFBundleShortVersionString': APP_VERSION,
                 'CFBundleVersion': APP_VERSION,
                 'SUFeedURL': APP_APPCAST_URL,
                 'LSEnvironment': {
                             'LC_CTYPE': 'en_US.UTF-8',
                             'PATH': '/usr/local/bin:/usr/local/sbin:/usr/bin:/bin:/usr/sbin:/sbin'
                         }
             })

