# -*- mode: python -*-
# this pyinstaller spec file is used to build borg binaries on posix platforms
# adapted from Borg project to package noatrized folder-style app

import os, sys

## Pass borg source dir as last argument
basepath = os.path.abspath(os.path.join(sys.argv[-1]))

block_cipher = None

a = Analysis([os.path.join(basepath, 'src', 'borg', '__main__.py'), ],
             pathex=[basepath, ],
             binaries=[],
             datas=[
                (os.path.join(basepath, 'src', 'borg', 'paperkey.html'), 'borg'),
             ],
             hiddenimports=[
                'borg.platform.posix',
                'borg.platform.darwin',
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[
                '_ssl', 'ssl',
             ],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

if sys.platform == 'darwin':
    # do not bundle the osxfuse libraries, so we do not get a version
    # mismatch to the installed kernel driver of osxfuse.
    a.binaries = [b for b in a.binaries if 'libosxfuse' not in b[0]]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='borg.exe',
          debug=False,
          strip=False,
          upx=False,
          console=True)

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name='borg-dir')
