# -*- mode: python -*-

import os
import sys

CREATE_VORTA_DIR = False  # create dist/vorta-dir/ output?
BLOCK_CIPHER = None

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
                 'vorta.views.collection_rc',
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
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name=f"vorta-{sys.platform}",
          debug=False,
          bootloader_ignore_signals=True,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True)

app = BUNDLE(exe,
             name='Vorta.app',
             icon='src/vorta/assets/icons/app-icon.icns',
             bundle_identifier='com.borgbase.client.macos',
             info_plist={
                 'NSHighResolutionCapable': 'True',
                 'LSUIElement': '1',
                 'CFBundleShortVersionString': '0.6.15',
                 'CFBundleVersion': '0.6.15',
                 'NSAppleEventsUsageDescription': 'Please allow',
                 'SUFeedURL': 'https://borgbase.github.io/vorta/appcast.xml',
             })

if CREATE_VORTA_DIR:
    coll = COLLECT(exe,
                   a.binaries,
                   a.zipfiles,
                   a.datas,
                   strip=False,
                   name='vorta-dir')
