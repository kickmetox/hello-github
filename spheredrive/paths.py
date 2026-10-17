"""Pfade für Konfiguration, Symbol und Arbeitsordner."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

# Vom Benutzer genannter Arbeitsordner. Liegt dort ein Symbol, hat es Vorrang.
WORK_DIR = Path(r"D:\AI_Temp\SphereDrive")
PREFERRED_ICON_NAMES = ("spheredrive.ico", "app.ico", "icon.ico", "logo.ico")


def package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_store_path() -> Path:
    override = os.environ.get("SPHEREDRIVE_CONFIG")
    if override:
        return Path(override)
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "SphereDrive" / "config.json"
    return Path.home() / ".config" / "SphereDrive" / "config.json"


def default_log_path() -> Path:
    return default_store_path().with_name("spheredrive.log")


def choose_icon(files: list[Path]) -> Path | None:
    """Wählt ein Symbol. Eine fremde .ico-Datei gewinnt vor der mitgelieferten SphereDrive.ico."""
    existing = [path for path in files if path.is_file() and path.suffix.lower() == ".ico"]
    if not existing:
        return None
    custom = [path for path in existing if path.name.lower() != "spheredrive.ico"]
    pool = custom or existing

    def rank(path: Path) -> tuple[int, str]:
        name = path.name.lower()
        if "sphere" in name:
            return (0, name)
        if name in PREFERRED_ICON_NAMES:
            return (1, name)
        return (2, name)

    return sorted(pool, key=rank)[0]


def _icons_in(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return [path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".ico"]


def _icon_directories() -> list[Path]:
    module_assets = Path(__file__).resolve().parent / "assets"
    directories = [WORK_DIR, module_assets, package_root(), package_root() / "assets"]
    installed = install_root()
    if installed is not None:
        directories.extend((installed / "assets", installed))
    return directories


def find_icon() -> Path | None:
    env = os.environ.get("SPHEREDRIVE_ICON")
    if env and Path(env).is_file():
        return Path(env)
    for directory in _icon_directories():
        chosen = choose_icon(_icons_in(directory))
        if chosen is not None:
            return chosen
    return None


def default_drive_icon() -> str:
    """Programmsymbol als Vorgabe für eine neue Laufwerkszuordnung."""
    found = find_icon()
    return str(found) if found is not None else ""


def find_window_png() -> Path | None:
    icon = find_icon()
    if icon is not None:
        sibling = icon.with_suffix(".png")
        if sibling.is_file():
            return sibling
    bundled = package_root() / "assets" / "SphereDrive.png"
    return bundled if bundled.is_file() else None


def program_source() -> Path:
    """Ordner mit assets und, im Quelltext, SphereDrive.pyw."""
    installed = install_root()
    if installed is not None and (installed / "assets").is_dir():
        return installed
    return package_root()


def _same_folder(left: Path, right: Path) -> bool:
    return os.path.normcase(os.path.abspath(left)) == os.path.normcase(os.path.abspath(right))


def _copy_tree(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if item.name == "__pycache__" or item.suffix.lower() == ".pyc":
            continue
        dest = target / item.name
        if item.is_dir():
            _copy_tree(item, dest)
        elif item.is_file():
            shutil.copy2(item, dest)


def publish_to(target: Path, source: Path | None = None) -> list[str]:
    """Kopiert Programmdateien nach target. Ein bereits belegter Ordner wird ergänzt, nicht geleert."""
    origin = source or program_source()
    target.mkdir(parents=True, exist_ok=True)
    if _same_folder(origin, target):
        return []
    copied: list[str] = []
    for name in ("SphereDrive.pyw", "Start-SphereDrive.bat", "README.md", "SphereDrive-Setup-1.0.0.exe"):
        src = origin / name
        if not src.is_file():
            continue
        shutil.copy2(src, target / name)
        copied.append(name)
    for name in ("assets", "spheredrive"):
        src = origin / name
        if not src.is_dir():
            continue
        _copy_tree(src, target / name)
        copied.append(name + "\\")
    return copied


def place_logo(target: Path, source: Path | None = None) -> None:
    """Legt das mitgelieferte Symbol in den Arbeitsordner, solange dort kein eigenes .ico liegt."""
    origin = source or program_source()
    target.mkdir(parents=True, exist_ok=True)
    custom = [path for path in _icons_in(target) if path.name.lower() != "spheredrive.ico"]
    if custom:
        return
    for name in ("SphereDrive.ico", "SphereDrive.png"):
        src = origin / "assets" / name
        if not src.is_file():
            src = origin / name
        if src.is_file() and not (target / name).is_file():
            shutil.copy2(src, target / name)


def ensure_work_dir() -> str | None:
    """Legt D:\\AI_Temp\\SphereDrive an. Unter anderen Systemen passiert nichts."""
    if sys.platform != "win32":
        return None
    try:
        WORK_DIR.mkdir(parents=True, exist_ok=True)
        source = program_source()
        if (source / "SphereDrive.pyw").is_file() or (source / "assets").is_dir():
            publish_to(WORK_DIR, source)
            place_logo(WORK_DIR, source)
    except OSError as exc:
        return f"Der Pfad kann nicht geöffnet werden: {WORK_DIR}. {exc}"
    return None


def browse_directory() -> str:
    """Vorhandener Startordner für Dateidialoge. Fehlt D:, wird das Benutzerverzeichnis genommen."""
    ensure_work_dir()
    if WORK_DIR.is_dir():
        return str(WORK_DIR)
    home = Path.home()
    return str(home) if home.is_dir() else ""


def entry_script() -> Path:
    root = package_root()
    pyw = root / "SphereDrive.pyw"
    if pyw.is_file():
        return pyw
    return Path(__file__).resolve()


def pythonw_executable() -> str:
    executable = Path(sys.executable)
    candidate = executable.with_name("pythonw.exe")
    if candidate.is_file():
        return str(candidate)
    return str(executable)


def install_root() -> Path | None:
    """Installationsordner des Windows-Installers, falls das Programm von dort läuft."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    executable = Path(sys.executable)
    if executable.parent.name.lower() != "python":
        return None
    root = executable.parent.parent
    if (root / "pkgs").is_dir():
        return root
    return None


def bundled_restore(executable: Path) -> tuple[str, str] | None:
    """Startzeile für --restore, wenn SphereDrive aus dem Installer heraus läuft."""
    if executable.parent.name.lower() != "python":
        return None
    root = executable.parent.parent
    launcher = root / "bin" / "SphereDrive.exe"
    if launcher.is_file():
        return str(launcher), "--restore"
    for name in ("SphereDrive.launch.pyw", "SphereDrive.launch.py"):
        script = root / name
        if script.is_file():
            pythonw = executable.parent / "pythonw.exe"
            if not pythonw.is_file():
                pythonw = executable
            return str(pythonw), f'"{script}" --restore'
    return None


def restore_launch() -> tuple[str, str]:
    """Programm und Argumente, mit denen die Anmeldung die Zuordnungen wiederherstellt."""
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable)), "--restore"
    bundled = bundled_restore(Path(sys.executable))
    if bundled is not None:
        return bundled
    return pythonw_executable(), f'"{entry_script()}" --restore'


def gui_launch() -> tuple[str, str]:
    """Dieselbe Zeile ohne --restore, für den normalen Start und die Erhöhung."""
    executable, arguments = restore_launch()
    if arguments == "--restore":
        return executable, ""
    suffix = " --restore"
    if arguments.endswith(suffix):
        return executable, arguments[: -len(suffix)]
    return executable, arguments


def format_launch(executable: str, arguments: str) -> str:
    if arguments:
        return f'"{executable}" {arguments}'
    return f'"{executable}"'
