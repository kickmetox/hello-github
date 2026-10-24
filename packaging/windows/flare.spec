# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller-Spec. Läuft unter Windows-Python (auch via Wine)."""

import os

from PyInstaller.utils.hooks import collect_submodules

root = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
icon = os.path.join(SPECPATH, "flare.ico")
datas = [(os.path.join(root, "flare", "ui.html"), "flare")]
if os.path.exists(icon):
    datas.append((icon, "."))

a = Analysis(
    [os.path.join(root, "flare.py")],
    pathex=[root],
    binaries=[],
    datas=datas,
    hiddenimports=collect_submodules("flare"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Flare",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=icon if os.path.exists(icon) else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Flare",
)
