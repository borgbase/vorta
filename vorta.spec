# -*- mode: python -*-

block_cipher = None

a = Analysis(['src/vorta/__main__.py'],
             pathex=['/Users/manu/Workspace/vorta/src'],
             binaries=[
                ('bin/macosx64/borg', 'bin'),
             ],
             datas=[
                ('src/vorta/assets/UI/*', 'assets/UI'),
                ('src/vorta/assets/icons/*', 'assets/icons'),
             ],
             hiddenimports=['vorta.views.collection_rc',
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='vorta',
          debug=False,
          bootloader_ignore_signals=True,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True )

app = BUNDLE(exe,
             name='Vorta.app',
             icon='src/vorta/assets/icons/app-icon.icns',
             bundle_identifier='com.borgbase.client.macos',
             info_plist={
                     'NSHighResolutionCapable': 'True',
                     'LSUIElement': '1',
                     'CFBundleShortVersionString': '0.6.4',
                     'CFBundleVersion': '0.6.4',
                     'NSAppleEventsUsageDescription': 'Please allow',
                     'SUFeedURL': 'https://borgbase.github.io/vorta/appcast.xml'
                     },
             )
if False:
    coll = COLLECT(exe,
                   a.binaries,
                   a.zipfiles,
                   a.datas,
                   strip=False,
                   name='vorta-dir')
