# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller-Spec InstantLens Doc (Alternative zu build-windows.ps1 CLI)."""

from pathlib import Path

block_cipher = None
root = Path(SPECPATH)

a = Analysis(
    [str(root / "instantlensdoc" / "__main__.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / "assets"), "assets"),
        (str(root / "FEATURES.md"), "."),
        (str(root / "INFO.md"), "."),
    ],
    hiddenimports=["pypdfium2", "pikepdf", "PIL"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

icon = root / "assets" / "app.ico"
if not icon.exists():
    icon = root / "assets" / "icon.png"

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="InstantLensDoc",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(icon) if icon.exists() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="InstantLensDoc",
)
