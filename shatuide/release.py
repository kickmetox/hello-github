"""Baut ShatuIDE.exe und den Windows-Installer."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path

from shatuide import __version__
from shatuide.studio import build_msi
from shatuide.tools import RELEASE_API, pick_asset

ROOT = Path(__file__).resolve().parent.parent
PACKAGING = ROOT / "packaging"
SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "ausgabe",
    "dist",
    "build",
    ".shatuide",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "tests",
}


def project_files(source: Path) -> list[Path]:
    files: list[Path] = []
    root = Path(source).resolve()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS or part.startswith(".") for part in relative.parts):
            continue
        if path.suffix.lower() in {".pyc", ".msi", ".exe"}:
            continue
        files.append(path)
    return files


def compile_launcher(kind: str, dest: Path) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if kind == "windows":
        compiler = shutil.which("x86_64-w64-mingw32-gcc")
        source = PACKAGING / "launcher_win.c"
        if not compiler:
            return {"ok": False, "error": "Windows-Compiler fehlt (x86_64-w64-mingw32-gcc)."}
        argv = [compiler, "-O2", "-s", "-o", str(dest), str(source), "-lshell32"]
    else:
        compiler = shutil.which("gcc")
        source = PACKAGING / "launcher_posix.c"
        if not compiler:
            return {"ok": False, "error": "Linux-Compiler fehlt (gcc)."}
        argv = [compiler, "-O2", "-s", "-o", str(dest), str(source)]
    if not source.is_file():
        return {"ok": False, "error": f"Startquelle fehlt: {source.name}"}
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        return {"ok": False, "error": (proc.stderr or proc.stdout or "Compiler fehlgeschlagen.").strip()}
    if kind != "windows":
        dest.chmod(0o755)
    return {"ok": True, "path": str(dest)}


def _bundle_windows_python(stage: Path, cache: Path) -> dict:
    cache.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        RELEASE_API,
        headers={"User-Agent": "ShatuIDE", "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            import json
            release = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"ok": False, "error": f"Download-Index nicht erreichbar: {exc}"}
    asset = pick_asset(release.get("assets", []), "x86_64-pc-windows-msvc")
    if not asset:
        return {"ok": False, "error": "Kein Windows-CPython-Archiv gefunden."}
    archive = cache / asset["name"]
    if not archive.is_file() or archive.stat().st_size != int(asset.get("size") or 0):
        try:
            urllib.request.urlretrieve(asset["browser_download_url"], archive)
        except Exception as exc:
            return {"ok": False, "error": f"Python-Download fehlgeschlagen: {exc}"}
    unpacked = cache / "windows-python"
    if unpacked.exists():
        shutil.rmtree(unpacked)
    unpacked.mkdir()
    try:
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(unpacked, filter="data")
    except (tarfile.TarError, OSError, TypeError) as exc:
        return {"ok": False, "error": f"Python-Archiv defekt: {exc}"}
    found = [
        path for path in unpacked.rglob("python.exe")
        if path.is_file() and "site-packages" not in path.parts
    ]
    if not found:
        return {"ok": False, "error": "python.exe fehlt im Windows-Archiv."}
    runtime = found[0].parent
    target = stage / "python"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(runtime, target)
    if not (target / "python.exe").is_file():
        return {"ok": False, "error": "python.exe liegt nach dem Kopieren nicht unter python\\."}
    return {"ok": True, "python": str(target / "python.exe"), "archive": asset["name"]}


def build_release(source: Path, dest: Path | None = None, bundle_python: bool = False) -> dict:
    source = Path(source).resolve()
    dest = Path(dest or (source / "ausgabe")).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    stage = dest / "inhalt"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()
    for path in project_files(source):
        relative = path.relative_to(source)
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    windows = compile_launcher("windows", stage / "ShatuIDE.exe")
    if not windows["ok"]:
        return windows
    linux_path = dest / "ShatuIDE"
    linux = compile_launcher("native", linux_path)
    if not linux["ok"]:
        return linux
    probe = stage / "ShatuIDE"
    shutil.copy2(linux_path, probe)
    probe.chmod(0o755)
    help_run = subprocess.run([str(probe), "--help"], cwd=str(stage), capture_output=True, text=True, timeout=20)
    probe.unlink(missing_ok=True)
    if help_run.returncode != 0 or "ShatuIDE" not in (help_run.stdout or ""):
        detail = (help_run.stderr or help_run.stdout or "Startprogramm antwortet nicht auf --help.").strip()
        return {"ok": False, "error": detail}
    bundled = False
    if bundle_python:
        placed = _bundle_windows_python(stage, dest / "cache")
        if not placed["ok"]:
            return placed
        bundled = True
    files = [path for path in stage.rglob("*") if path.is_file()]
    package = build_msi(stage, "ShatuIDE", __version__, "Andreas Meyer", files)
    if not package["ok"]:
        return package
    msi = dest / "ShatuIDE.msi"
    exe = dest / "ShatuIDE.exe"
    shutil.copy2(package["path"], msi)
    shutil.copy2(stage / "ShatuIDE.exe", exe)
    if bundled:
        hint = "Python liegt im Installer unter python\\python.exe."
    else:
        hint = "Python 3 muss installiert sein, oder python\\python.exe liegt neben der EXE."
    return {
        "ok": True,
        "msi": str(msi),
        "exe": str(exe),
        "linux": str(linux_path),
        "files": len(files),
        "message": f"Installer {msi.name} und {exe.name} erzeugt. Unter Windows: msiexec /i {msi.name}. Danach startet ShatuIDE.exe die IDE. {hint}",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="ShatuIDE als EXE und MSI bauen")
    parser.add_argument("--dest", default="", help="Zielordner, sonst ausgabe/")
    parser.add_argument("--with-python", action="store_true", help="Windows-CPython in den Installer packen")
    args = parser.parse_args()
    result = build_release(ROOT, Path(args.dest) if args.dest else None, bundle_python=args.with_python)
    print(result.get("message") or result.get("error"))
    raise SystemExit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
