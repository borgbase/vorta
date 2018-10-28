# -*- mode: python -*-

block_cipher = None

a = Analysis(['vorta/__main__.py'],
             pathex=['/Users/manu/Workspace/vorta'],
             binaries=[
                ('bin/macosx64/borg', 'bin')
             ],
             datas=[
                ('vorta/UI/*.ui', 'UI'),
                ('vorta/UI/icons/*', 'UI/icons'),
             ],
             hiddenimports=[],
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
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=False )

app = BUNDLE(exe,
             name='Vorta.app',
             icon='vorta/UI/icons/app-icon.icns',
             bundle_identifier='com.borgbase.client.macos',
             info_plist={
                     'NSHighResolutionCapable': 'True',
                     'LSUIElement': '1',
                     'CFBundleShortVersionString': '0.0.3'
                     },
             )

# Debug package. (inspired from borg)
if False:
    coll = COLLECT(exe,
                   a.binaries,
                   a.zipfiles,
                   a.datas,
                   strip=False,
                   upx=True,
                   name='vorta-dir')
