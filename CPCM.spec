# -*- mode: python ; coding: utf-8 -*-
# Linux-Binary, eine Datei: python3 -m PyInstaller --noconfirm --clean CPCM.spec
# Ausgabe: dist/CPCM. Pillow wird nicht gebraucht. Laufzeit der Quelle bleibt die Standardbibliothek.

a = Analysis(
    ['cpcm.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('web', 'web'),
        ('examples', 'examples'),
        ('icon.png', '.'),
        ('cpcm.ico', '.'),
    ],
    hiddenimports=[
        'cpcm',
        'cpcm.__main__',
        'cpcm.backup',
        'cpcm.catalog',
        'cpcm.cli',
        'cpcm.diagnose',
        'cpcm.filesystems',
        'cpcm.hardware',
        'cpcm.paths',
        'cpcm.selection',
        'cpcm.server',
        'cpcm.settings',
        'cpcm.shortcuts',
        'cpcm.themes',
        'cpcm.translate',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CPCM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
