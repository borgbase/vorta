# -*- mode: python -*-

block_cipher = None


a = Analysis(['vorta/__main__.py'],
             pathex=['/Users/manu/Workspace/vorta'],
             binaries=[
                ('bin/macosx64/borg', 'bin')
             ],
             datas=[
                ('vorta/UI/*.ui', 'vorta/UI'),
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
             icon=None,
             bundle_identifier=None,
             info_plist={
                     'NSHighResolutionCapable': 'True'
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
