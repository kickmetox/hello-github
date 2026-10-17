"""Interpreter finden, virtuelle Umgebungen anlegen, Pakete und CPython laden."""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path

PACKAGE_RE = re.compile(r"^[A-Za-z0-9_\-\.\[\],<>=!~]+$")
RELEASE_API = "https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"
VERSION_RE = re.compile(r"cpython-(\d+)\.(\d+)\.(\d+)(?:([abrc])(\d+)|\+)")

TOOL_GROUPS = {
    "qualitaet": ["black", "ruff"],
    "tests": ["pytest", "coverage"],
    "editor": ["jedi"],
    "build": ["pyinstaller"],
    "data": ["pandas", "matplotlib"],
    "web": ["flask", "fastapi", "uvicorn"],
    "db": ["pymysql", "psycopg", "pymongo"],
    "notebook": ["ipython"],
}


def _run(args: list[str], timeout: int = 120, cwd: str | None = None) -> dict:
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Zeitlimit erreicht.", "stdout": "", "stderr": ""}
    except OSError as exc:
        return {"ok": False, "error": str(exc), "stdout": "", "stderr": ""}
    return {
        "ok": proc.returncode == 0,
        "code": proc.returncode,
        "stdout": proc.stdout[-30000:],
        "stderr": proc.stderr[-12000:],
        "error": (proc.stderr or proc.stdout or "").strip()[-1000:] if proc.returncode else "",
    }


def interpreter_version(python: str) -> str:
    result = _run([python, "-c", "import sys; print(sys.version.split()[0])"], timeout=15)
    if result.get("ok"):
        return result["stdout"].strip().splitlines()[-1].strip()
    return ""


def _add(found: list[dict], path: str, source: str) -> None:
    if not path:
        return
    resolved = str(Path(path).resolve()) if Path(path).is_file() else path
    if any(item["path"] == resolved for item in found):
        return
    if Path(resolved).is_file() or shutil.which(path):
        exe = resolved if Path(resolved).is_file() else shutil.which(path) or path
        if any(item["path"] == exe for item in found):
            return
        found.append({"path": exe, "source": source, "version": interpreter_version(exe)})


def discover_interpreters(workspace: Path) -> list[dict]:
    found: list[dict] = []
    import sys

    _add(found, sys.executable, "laufende IDE")
    for name in ("python3", "python"):
        which = shutil.which(name)
        if which:
            _add(found, which, "PATH")
    if os.name == "nt":
        which = shutil.which("py")
        if which:
            _add(found, which, "Python-Launcher")
    for folder in (".venv", "venv", "env"):
        for relative in (
            Path(folder) / "bin" / "python",
            Path(folder) / "bin" / "python3",
            Path(folder) / "Scripts" / "python.exe",
        ):
            candidate = workspace / relative
            if candidate.is_file():
                _add(found, str(candidate), f"Projekt {folder}")
    runtime = workspace / ".shatuide" / "runtime"
    if runtime.is_dir():
        for candidate in runtime.rglob("python.exe"):
            _add(found, str(candidate), "heruntergeladen")
        for candidate in list(runtime.rglob("python3"))[:8]:
            if candidate.is_file() and "site-packages" not in candidate.parts:
                _add(found, str(candidate), "heruntergeladen")
    conda = shutil.which("conda")
    if conda:
        result = _run([conda, "env", "list", "--json"], timeout=30)
        if result.get("ok"):
            try:
                data = json.loads(result["stdout"])
            except json.JSONDecodeError:
                data = {}
            for env_path in data.get("envs", []):
                for name in ("python.exe", "bin/python"):
                    candidate = Path(env_path) / name
                    if candidate.is_file():
                        _add(found, str(candidate), "conda")
    return found


def create_venv(base_python: str, destination: Path) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = _run([base_python, "-m", "venv", str(destination)], timeout=180)
    if not result.get("ok"):
        return result
    exe = destination / "Scripts" / "python.exe"
    if not exe.is_file():
        exe = destination / "bin" / "python"
    return {**result, "python": str(exe) if exe.is_file() else ""}


def validate_package(package: str) -> str | None:
    package = package.strip()
    if not package or not PACKAGE_RE.match(package) or package.startswith("-"):
        return None
    return package


def pip_install(python: str, packages: list[str]) -> dict:
    clean = []
    for package in packages:
        valid = validate_package(package)
        if not valid:
            return {"ok": False, "error": f"Ungültiger Paketname: {package}"}
        clean.append(valid)
    if not clean:
        return {"ok": False, "error": "Kein Paket angegeben."}
    _run([python, "-m", "ensurepip", "--upgrade"], timeout=120)
    return _run([python, "-m", "pip", "install", "--disable-pip-version-check", *clean], timeout=300)


def pip_list(python: str) -> dict:
    result = _run([python, "-m", "pip", "list", "--format", "json"], timeout=40)
    if not result.get("ok"):
        return result
    try:
        packages = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return {"ok": False, "error": "pip-Liste nicht lesbar.", "stdout": result.get("stdout", "")}
    return {"ok": True, "packages": packages}


def pip_search_pypi(query: str) -> dict:
    query = query.strip()
    if not query:
        return {"ok": False, "error": "Suchbegriff fehlt."}
    url = "https://pypi.org/pypi/" + urllib.request.quote(query) + "/json"
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    info = data.get("info", {})
    return {
        "ok": True,
        "name": info.get("name", query),
        "version": info.get("version", ""),
        "summary": info.get("summary", ""),
        "home": info.get("home_page") or info.get("project_url") or "",
    }


def tool_status(python: str) -> dict:
    modules = {
        "black": "black",
        "ruff": "ruff",
        "pytest": "pytest",
        "coverage": "coverage",
        "jedi": "jedi",
        "IPython": "IPython",
        "pandas": "pandas",
        "matplotlib": "matplotlib",
        "PyInstaller": "PyInstaller",
        "flask": "flask",
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "pymysql": "pymysql",
        "psycopg": "psycopg",
        "pymongo": "pymongo",
    }
    code = "import importlib.util, json, sys\n" + (
        "mods = " + json.dumps(modules) + "\n"
        "print(json.dumps({name: importlib.util.find_spec(mod) is not None for name, mod in mods.items()}))\n"
    )
    result = _run([python, "-c", code], timeout=30)
    available = {}
    if result.get("ok"):
        try:
            available = json.loads(result["stdout"].strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            available = {}
    commands = {
        "git": shutil.which("git"),
        "conda": shutil.which("conda"),
        "poetry": shutil.which("poetry"),
        "pipenv": shutil.which("pipenv"),
        "docker": shutil.which("docker"),
        "ssh": shutil.which("ssh"),
    }
    return {"ok": True, "modules": available, "commands": {key: bool(value) for key, value in commands.items()}, "paths": commands}


def conda_create(name: str, python_version: str = "3.12") -> dict:
    if not re.match(r"^[A-Za-z0-9_\-]+$", name):
        return {"ok": False, "error": "Ungültiger Umgebungsname."}
    if not re.match(r"^\d+\.\d+$", python_version):
        return {"ok": False, "error": "Ungültige Python-Version."}
    conda = shutil.which("conda")
    if not conda:
        return {"ok": False, "error": "conda ist nicht installiert."}
    return _run([conda, "create", "-y", "-n", name, f"python={python_version}"], timeout=600)


def poetry_install(workspace: Path) -> dict:
    poetry = shutil.which("poetry")
    if not poetry:
        return {"ok": False, "error": "poetry ist nicht installiert."}
    return _run([poetry, "install"], timeout=300, cwd=str(workspace))


def pipenv_install(workspace: Path) -> dict:
    pipenv = shutil.which("pipenv")
    if not pipenv:
        return {"ok": False, "error": "pipenv ist nicht installiert."}
    return _run([pipenv, "install"], timeout=300, cwd=str(workspace))


def platform_tag() -> str | None:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if machine in {"amd64", "x86_64"}:
        arch = "x86_64"
    elif machine in {"arm64", "aarch64"}:
        arch = "aarch64"
    else:
        return None
    if system == "windows":
        return f"{arch}-pc-windows-msvc"
    if system == "linux":
        return f"{arch}-unknown-linux-gnu"
    if system == "darwin":
        return f"{arch}-apple-darwin"
    return None


def _version_key(name: str) -> tuple | None:
    match = re.search(r"cpython-(\d+)\.(\d+)\.(\d+)([a-z]\d+)?\+", name)
    if not match:
        return None
    major, minor, patch, pre = match.groups()
    if pre:
        return None
    return (int(major), int(minor), int(patch))


def pick_asset(assets: list[dict], tag: str | None = None) -> dict | None:
    """Wählt das neueste stabile install_only-Archiv für diese Plattform."""
    target = tag or platform_tag()
    if not target:
        return None
    best = None
    best_key = None
    for asset in assets:
        name = asset.get("name", "")
        if "freethreaded" in name or name.endswith("_stripped.tar.gz"):
            continue
        if not name.endswith("-install_only.tar.gz"):
            continue
        marker = f"-{target}-install_only.tar.gz"
        if marker not in name:
            continue
        # x86_64 soll nicht x86_64_v2 treffen: der Marker beginnt direkt nach der Version.
        if f"-{target}" not in name.split("+", 1)[-1]:
            continue
        key = _version_key(name)
        if key is None:
            continue
        if best_key is None or key > best_key:
            best_key = key
            best = asset
    return best


def download_python(workspace: Path, log=None) -> dict:
    def say(message: str) -> None:
        if log:
            log(message)

    tag = platform_tag()
    if not tag:
        return {"ok": False, "error": f"Plattform {platform.system()} {platform.machine()} wird nicht unterstützt."}
    say("Suche aktuelle CPython-Version …")
    request = urllib.request.Request(RELEASE_API, headers={"User-Agent": "ShatuIDE", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            release = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"ok": False, "error": f"Download-Index nicht erreichbar: {exc}"}
    asset = pick_asset(release.get("assets", []), tag)
    if not asset:
        return {"ok": False, "error": "Kein passendes CPython-Archiv gefunden."}
    url = asset["browser_download_url"]
    runtime = workspace / ".shatuide" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    archive = runtime / asset["name"]
    say(f"Lade {asset['name']} …")
    try:
        urllib.request.urlretrieve(url, archive)
    except Exception as exc:
        return {"ok": False, "error": f"Download fehlgeschlagen: {exc}"}
    say("Entpacke …")
    try:
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(runtime)
    except (tarfile.TarError, OSError) as exc:
        return {"ok": False, "error": f"Entpacken fehlgeschlagen: {exc}"}
    python = _find_downloaded_python(runtime)
    if not python:
        return {"ok": False, "error": "Archiv entpackt, Python-Binary aber nicht gefunden."}
    say(f"Python bereit: {python}")
    return {"ok": True, "python": str(python), "archive": asset["name"]}


def _find_downloaded_python(runtime: Path) -> Path | None:
    names = ["python.exe", "python3", "python"]
    candidates = []
    for name in names:
        candidates.extend(runtime.rglob(name))
    for candidate in candidates:
        if not candidate.is_file():
            continue
        if "site-packages" in candidate.parts:
            continue
        if candidate.name == "python.exe" or candidate.parent.name in {"bin", "Scripts"}:
            return candidate
    return candidates[0] if candidates else None
