#!/usr/bin/env python3
"""Packt ein startbares Windows-Python-Layout (run.bat + Deps-Hinweis + Keygen).

Nutzung (Linux/Windows):
  python scripts/pack-windows-runnable.py
  python scripts/pack-windows-runnable.py --out /path/to/out.zip

Erzeugt InstantLensDoc-VERSION-windows-runnable.zip mit klaren DE-Startskripten.
PyInstaller-EXE entsteht separat via build-windows.ps1 auf einem 64-Bit-Windows-Host.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INCLUDE_TOP = [
    "instantlensdoc",
    "ild_pdf",
    "ild",
    "keygen",
    "assets",
    "docs",
    "examples",
    "installer",
    "scripts",
    "run.bat",
    "run.ps1",
    "run-keygen.bat",
    "run-keygen.ps1",
    "run-ild.bat",
    "run_instantlensdoc.py",  # PyInstaller entry (ohne Relative-Import) — 2.6.36/2.6.40
    "build-windows.ps1",
    "instantlensdoc.spec",
    "requirements.txt",
    "VERSION.txt",
    "README.md",
    "INFO.md",
    "FEATURES.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "vendor",  # Tesseract-Runtime Layout / README (Binaries optional) — 2.6.42
]

SKIP_DIR_NAMES = {
    "__pycache__",
    ".venv",
    ".git",
    "build",
    "dist",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
}


def _version() -> str:
    return (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip().split()[0]


def _should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_DIR_NAMES:
        return True
    if path.name.endswith((".pyc", ".pyo", ".zip")):
        return True
    if path.name.startswith(".smoke"):
        return True
    return False


def collect_files() -> list[Path]:
    files: list[Path] = []
    for name in INCLUDE_TOP:
        src = ROOT / name
        if not src.exists():
            continue
        if src.is_file():
            files.append(src)
            continue
        for p in src.rglob("*"):
            if p.is_file() and not _should_skip(p.relative_to(ROOT)):
                files.append(p)
    return files


def write_start_hinweis(dest_dir: Path, version: str) -> None:
    text = f"""# InstantLens Doc {version} — Windows startbar (Python-Layout)

## Schnellstart (64-Bit empfohlen)

1. Python **3.10+ 64-Bit** installieren (python.org oder Microsoft Store).
2. Dieses Paket nach z. B. `D:\\AI_Temp\\InstantLensDoc-2661` entpacken
   (nested: innerer Ordner `InstantLensDoc\\`).
3. Abhängigkeiten (gleicher Rebuild wie 2.6.59):

```bat
cd /d D:\\AI_Temp\\InstantLensDoc-2661
python -m pip install -r requirements.txt
run.bat
```

Oder Sync + Swap wie 2.6.59:

```powershell
powershell -ExecutionPolicy Bypass -File "D:\\AI_Temp\\sync-ild.ps1" -LocalPack D:\\AI_Temp\\InstantLensDoc-2.6.61-pack.zip -Dest D:\\AI_Temp\\InstantLensDoc-2661 -Swap -SkipStart
cd /d D:\\AI_Temp\\InstantLensDoc
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\\build-windows.ps1
powershell -ExecutionPolicy Bypass -File .\\scripts\\install-ild.ps1
```

Oder non-interactive: `run.bat --yes`

## Keygenerator

```bat
run-keygen.bat
```

CLI: `python -m keygen kunde@example.com`  
Prüfen: `python -m keygen --verify "ILD1...."`

Keys: Trial 28 Tage · Lizenzkeys 32 Tage (30+2), Format `ILD1.<payload>.<sig>` (HMAC).  
Kontakt: ame@sellerbach.de

## EXE-Build (optional, auf Windows x64)

```powershell
powershell -ExecutionPolicy Bypass -File .\\build-windows.ps1
```

Ergebnis: `dist\\InstantLensDoc\\InstantLensDoc.exe` (+ `InstantLensKeygen.exe`).  
Installer-Einzeiler: `powershell -ExecutionPolicy Bypass -File .\\scripts\\build-windows-installer.ps1`  
→ `dist\\InstantLensDoc-Setup-<VERSION>.exe`

## Desktop-/Startmenü-Shortcuts

```powershell
powershell -ExecutionPolicy Bypass -File .\\scripts\\install-ild.ps1
```

Keygen-Shortcut wird angelegt, wenn `run-keygen.bat` vorhanden ist.

## Nach Sync (empfohlen)

```powershell
powershell -ExecutionPolicy Bypass -File "D:\\AI_Temp\\sync-ild.ps1" -SkipStart
cd /d D:\\AI_Temp\\InstantLensDoc
powershell -ExecutionPolicy Bypass -File .\\scripts\\install-ild.ps1
powershell -ExecutionPolicy Bypass -File .\\scripts\\build-windows-installer.ps1
```

Oder Sync inkl. optionalem Installer-Build (Inno Setup 6):

```powershell
powershell -ExecutionPolicy Bypass -File "D:\\AI_Temp\\sync-ild.ps1" -BuildInstaller -SkipStart
```

## Scripting (Python / PowerShell)

```bat
python -m ild --help
run-ild.bat pages dokument.pdf
powershell -ExecutionPolicy Bypass -File .\\scripts\\ild.ps1 license generate kunde@example.com
```

Anleitung: siehe Store-Doc ``instantlensdoc-scripting.md`` bzw. In-App-Hilfe „Scripting“.

"""
    (dest_dir / "WINDOWS-START.md").write_text(text, encoding="utf-8")


def pack(out_zip: Path) -> tuple[Path, str]:
    version = _version()
    staging = out_zip.parent / f"_stage-ild-{version}-runnable"
    if staging.exists():
        shutil.rmtree(staging)
    app_dir = staging / "InstantLensDoc"
    app_dir.mkdir(parents=True)

    for src in collect_files():
        rel = src.relative_to(ROOT)
        dst = app_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    write_start_hinweis(app_dir, version)

    out_zip.parent.mkdir(parents=True, exist_ok=True)
    if out_zip.exists():
        out_zip.unlink()
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(app_dir.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(staging).as_posix())

    h = hashlib.sha256(out_zip.read_bytes()).hexdigest()
    try:
        shutil.rmtree(staging, ignore_errors=True)
    except OSError:
        pass
    return out_zip, h


def main(argv: list[str] | None = None) -> int:
    version = _version()
    p = argparse.ArgumentParser(description="InstantLens Doc Windows-Runnable Pack")
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "dist" / f"InstantLensDoc-{version}-windows-runnable.zip",
        help="Ziel-Zip",
    )
    args = p.parse_args(argv)
    path, digest = pack(args.out.resolve())
    print(f"OK: {path}")
    print(f"SHA256: {digest}")
    print(f"Version: {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
