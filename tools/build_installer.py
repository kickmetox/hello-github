"""Baut den Windows-Installer. NSIS und pynsist müssen installiert sein.

Das Skript lädt den offiziellen Python-Installer, entnimmt daraus Tcl/Tk in
derselben Version wie das eingebettete Python und lässt pynsist das Setup erzeugen.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
CACHE = BUILD / "cache"
STAGING = BUILD / "staging"
PYTHON_VERSION = "3.12.10"

INSTALLER_URL = (
    f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-amd64.exe"
)


def main() -> int:
    _require("makensis")
    _require_module("nsist")
    version = _read_version()
    installer_name = f"SphereDrive-Setup-{version}.exe"
    cache_exe = CACHE / f"python-{PYTHON_VERSION}-amd64.exe"
    tk_root = CACHE / f"tk-{PYTHON_VERSION}"
    CACHE.mkdir(parents=True, exist_ok=True)
    if not cache_exe.is_file():
        print(f"Lade {INSTALLER_URL}")
        urllib.request.urlretrieve(INSTALLER_URL, cache_exe)
    if not (tk_root / "DLLs" / "_tkinter.pyd").is_file():
        print("Entpacke Tcl/Tk aus dem Python-Installer")
        _extract_tk(cache_exe, tk_root)
    _stage(tk_root)
    _write_config(version, installer_name)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.run(
        [sys.executable, "-m", "nsist", str(STAGING / "installer.cfg")],
        cwd=STAGING,
        check=True,
        env=env,
    )
    produced = BUILD / "nsis" / installer_name
    if not produced.is_file():
        raise SystemExit(f"Installer fehlt: {produced}")
    print(f"Installer: {produced} ({produced.stat().st_size} Bytes)")
    return 0


def _read_version() -> str:
    text = (ROOT / "spheredrive" / "__init__.py").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "1.0.0"


def _stage(tk_root: Path) -> None:
    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)
    pkgs = STAGING / "pynsist_pkgs"
    pkgs.mkdir()
    for name in ("_tkinter.pyd", "tcl86t.dll", "tk86t.dll", "zlib1.dll"):
        shutil.copy2(tk_root / "DLLs" / name, pkgs / name)
    lib_file = tk_root / "libs" / "_tkinter.lib"
    if lib_file.is_file():
        shutil.copy2(lib_file, pkgs / "_tkinter.lib")
    shutil.copytree(tk_root / "Lib" / "tkinter", pkgs / "tkinter")
    library = STAGING / "lib"
    library.mkdir()
    for name in ("tcl8", "tcl8.6", "tk8.6"):
        shutil.copytree(tk_root / "tcl" / name, library / name)
    shutil.copytree(ROOT / "assets", STAGING / "assets")


def _write_config(version: str, installer_name: str) -> None:
    icon = (ROOT / "assets" / "SphereDrive.ico").resolve()
    preamble = (ROOT / "tools" / "windows_preamble.py").resolve()
    template_name = "pyapp-de.nsi"
    shutil.copy2(ROOT / "tools" / "pyapp-de.nsi", STAGING / template_name)
    output = (BUILD / "nsis").resolve()
    text = f"""[Application]
name=SphereDrive
version={version}
publisher=SphereDrive
entry_point=spheredrive.__main__:main
icon={icon}
console=false
extra_preamble={preamble}

[Command SphereDrive]
entry_point=spheredrive.__main__:main
console=false
extra_preamble={preamble}

[Python]
version={PYTHON_VERSION}
bitness=64

[Include]
packages=spheredrive
    tkinter
    _tkinter
files=assets > $INSTDIR
    lib > $INSTDIR
exclude=*/__pycache__/*
    *.pyc

[Build]
directory={output}
installer_name={installer_name}
nsi_template={template_name}
"""
    (STAGING / "installer.cfg").write_text(text, encoding="utf-8")


def _extract_tk(installer: Path, dest: Path) -> None:
    data = installer.read_bytes()
    offsets = []
    start = 0
    while True:
        found = data.find(b"MSCF", start)
        if found < 0:
            break
        offsets.append(found)
        start = found + 4
    scratch = CACHE / "python-cab"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir()
    msi_path = None
    for offset in offsets:
        cab = scratch / f"{offset}.cab"
        cab.write_bytes(data[offset:])
        listing = subprocess.run(["7z", "l", str(cab)], capture_output=True, text=True)
        if "Tcl/Tk" in listing.stdout:
            continue
        extracted = scratch / f"out-{offset}"
        result = subprocess.run(["7z", "x", "-y", f"-o{extracted}", str(cab)], capture_output=True, text=True)
        if result.returncode not in {0, 1} or not extracted.exists():
            continue
        for candidate in extracted.rglob("*"):
            if not candidate.is_file():
                continue
            described = subprocess.run(["file", "-b", str(candidate)], capture_output=True, text=True)
            if "Tcl/Tk" in described.stdout:
                msi_path = candidate
                break
        if msi_path is not None:
            break
    if msi_path is None:
        raise SystemExit("Die Tcl/Tk-MSI wurde im Python-Installer nicht gefunden.")
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    subprocess.run(
        ["msiextract", str(msi_path)],
        cwd=dest,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    if not (dest / "DLLs" / "_tkinter.pyd").is_file():
        raise SystemExit("msiextract hat _tkinter.pyd nicht erzeugt.")


def _require(command: str) -> None:
    if shutil.which(command) is None:
        raise SystemExit(f"{command} fehlt. Unter Debian/Ubuntu: sudo apt-get install nsis p7zip-full msitools")


def _require_module(name: str) -> None:
    try:
        __import__(name)
    except ImportError as exc:
        raise SystemExit("pynsist fehlt. Installation: python3 -m pip install pynsist") from exc


if __name__ == "__main__":
    raise SystemExit(main())
