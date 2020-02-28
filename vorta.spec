# -*- mode: python -*-

import os
import sys

CREATE_VORTA_DIR = False  # create dist/vorta-dir/ output?
BLOCK_CIPHER = None
APP_NAME = 'Vorta'
APP_VERSION = '0.6.23'

# it is assumed that the cwd is the git repo dir:
REPO_DIR = os.path.abspath('.')
SRC_DIR = os.path.join(REPO_DIR, 'src')

a = Analysis(['src/vorta/__main__.py'],
             pathex=[SRC_DIR],
             binaries=[
                (f"bin/{sys.platform}/borg", 'bin'),  # (<borg fat binary for this platform>, <dest. folder>)
             ],
             datas=[
                ('src/vorta/assets/UI/*', 'assets/UI'),
                ('src/vorta/assets/icons/*', 'assets/icons'),
                ('src/vorta/i18n/qm/*', 'vorta/i18n/qm'),
             ],
             hiddenimports=[
                 'vorta.views.dark.collection_rc',
                 'vorta.views.light.collection_rc',
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
          upx=False)

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
             icon='src/vorta/assets/icons/app-icon.icns',
             bundle_identifier=None,
             info_plist={
                 'CFBundleName': APP_NAME,
                 'CFBundleDisplayName': APP_NAME,
                 'CFBundleIdentifier': 'com.borgbase.client.macos',
                 'NSHighResolutionCapable': 'True',
                 'LSUIElement': '1',
                 'LSMinimumSystemVersion': '10.14',
                 'CFBundleShortVersionString': APP_VERSION,
                 'CFBundleVersion': APP_VERSION,
                 'SUFeedURL': 'https://borgbase.github.io/vorta/appcast.xml',
                 'LSEnvironment': {
                             'LC_CTYPE': 'en_US.UTF-8',
                             'PATH': '/usr/local/bin:/usr/local/sbin:/usr/bin:/bin:/usr/sbin:/sbin'
                         }
             })

