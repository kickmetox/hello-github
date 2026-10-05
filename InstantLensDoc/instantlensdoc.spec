# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller-Spec InstantLens Doc (Alternative zu build-windows.ps1 CLI)."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None
root = Path(SPECPATH)

# PDFium-Binary + Datenpakete mitpacken (sonst EXE öffnet PDF, Canvas bleibt weiß) — 2.6.49
_pdfium_datas, _pdfium_binaries, _pdfium_hidden = collect_all("pypdfium2")

a = Analysis(
    # Thin absolute-import entry (not instantlensdoc/__main__.py) — frozen scripts
    # have no package parent, so relative imports fail at runtime.
    [str(root / "run_instantlensdoc.py")],
    pathex=[str(root)],
    binaries=list(_pdfium_binaries),
    datas=[
        (str(root / "assets"), "assets"),
        (str(root / "FEATURES.md"), "."),
        (str(root / "INFO.md"), "."),
        (str(root / "README.md"), "."),
        (str(root / "CHANGELOG.md"), "."),
    ]
    + list(_pdfium_datas),
    hiddenimports=[
        "pypdfium2",
        "pypdfium2.raw",
        "pypdfium2._helpers",
        "pikepdf",
        "PIL",
        "pytesseract",
        "PySide6.QtPrintSupport",
        "instantlensdoc",
        "instantlensdoc.app",
        "instantlensdoc.core.devices",
        "instantlensdoc.core.scan",
        "instantlensdoc.core.ocr",
        "instantlensdoc.core.scantuxio_ui",
        "instantlensdoc.core.scantuxio",
        "instantlensdoc.core.scantuxio.scanner",
        "instantlensdoc.core.scantuxio.scanner_naps2",
        "instantlensdoc.core.scantuxio.scanner_escl",
        "instantlensdoc.core.scantuxio.discovery",
        "instantlensdoc.core.scantuxio.printing",
        "instantlensdoc.core.scantuxio.printing_windows",
        "instantlensdoc.ui.scan_dialog",
        "ild_pdf",
        "ild",
        "keygen",
    ]
    + list(_pdfium_hidden),
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

_icon_candidates = [
    root / "assets" / "app.ico",
    root / "assets" / "icon.ico",
    root / "assets" / "icon.png",
    root / "assets" / "app.png",
]
icon = next((p for p in _icon_candidates if p.is_file()), None)

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
    icon=str(icon) if icon is not None else None,
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
