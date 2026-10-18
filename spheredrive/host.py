"""Ausführungsschicht. WindowsHost spricht mit dem System, PreviewHost simuliert es."""

from __future__ import annotations

import ctypes
import json
import locale
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from spheredrive.commands import TASK_NAME, map_through_subst, norm_path, normalize_letter, parent_dir, task_xml
from spheredrive.parsers import (
    LiveNet,
    LiveShare,
    LiveVolume,
    format_mountvol,
    format_net_share,
    format_net_use,
    format_subst,
    tokenize_cmd,
)
from spheredrive.paths import entry_script, gui_launch, pythonw_executable
from spheredrive.registry import MemoryRegistry, WindowsRegistry

CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_CONSOLE = 0x00000010
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF


@dataclass
class RunResult:
    ok: bool
    stdout: str
    stderr: str
    code: int = 0

    @property
    def text(self) -> str:
        return (self.stderr or self.stdout or "").strip()


def _result(ok: bool, stdout: str = "", stderr: str = "", code: int | None = None) -> RunResult:
    return RunResult(ok, stdout, stderr, 0 if code is None and ok else (code if code is not None else 1))


class PreviewHost:
    """Simuliert subst, net, mklink, mountvol und PowerShell, ohne das System zu verändern."""

    preview = True

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else Path.home() / ".config" / "SphereDrive" / "preview"
        self.registry = MemoryRegistry(admin=False)
        self.admin = False
        self.strict_paths = False
        self.subst: dict[str, str] = {}
        self.net: dict[str, LiveNet] = {}
        self.shares: dict[str, LiveShare] = {}
        self.links: dict[str, dict[str, str]] = {}
        self.psdrives: dict[str, dict[str, str]] = {}
        self.files: set[str] = set()
        self.dirs: set[str] = set()
        self.nonempty: set[str] = set()
        self.volumes: list[dict] = [
            {
                "id": "\\\\?\\Volume{11111111-1111-1111-1111-111111111111}\\",
                "label": "System",
                "filesystem": "NTFS",
                "capacity": 512 * 1024**3,
                "free": 180 * 1024**3,
                "mounts": ["C:\\"],
            },
            {
                "id": "\\\\?\\Volume{22222222-2222-2222-2222-222222222222}\\",
                "label": "Daten",
                "filesystem": "NTFS",
                "capacity": 1024 * 1024**3,
                "free": 640 * 1024**3,
                "mounts": [],
            },
        ]
        self.task = False
        self.calls: list[list[str]] = []
        self.spawned: list[list[str]] = []

    def set_admin(self, admin: bool) -> None:
        self.admin = admin
        self.registry.set_admin(admin)

    def is_admin(self) -> bool:
        return self.admin

    def run(self, args: list[str], *, input_text: str | None = None, timeout: int = 30) -> RunResult:
        del input_text, timeout
        self.calls.append(list(args))
        if not args:
            return _result(False, stderr="Leerer Befehl")
        name = Path(args[0]).name.lower()
        if name == "subst":
            return self._subst(args)
        if name == "net":
            return self._net(args)
        if name == "cmd":
            return self._cmd(args)
        if name == "mountvol":
            return self._mountvol(args)
        if name in {"explorer", "explorer.exe", "mmc", "mmc.exe"}:
            return _result(True)
        if name == "schtasks":
            return self._schtasks(args)
        if name == "taskkill":
            return _result(True, stdout="Vorschau")
        return _result(False, stderr=f"Unbekannter Befehl: {args[0]}")

    def run_powershell(self, script: str, *, timeout: int = 40) -> RunResult:
        del timeout
        self.calls.append(["powershell", script])
        if "Win32_Volume" in script:
            payload = []
            for volume in self.volumes:
                letter = ""
                for mount in volume["mounts"]:
                    if re.fullmatch(r"[A-Za-z]:\\?", mount):
                        letter = mount[0].upper() + ":"
                        break
                payload.append(
                    {
                        "DeviceID": volume["id"],
                        "DriveLetter": letter,
                        "Label": volume["label"],
                        "FileSystem": volume["filesystem"],
                        "Capacity": volume["capacity"],
                        "FreeSpace": volume["free"],
                    }
                )
            return _result(True, stdout=json.dumps(payload))
        if "Get-PSDrive" in script and "New-PSDrive" not in script and "ReparsePoint" not in script:
            payload = [
                {"Name": name, "Provider": item["provider"], "Root": item["root"]}
                for name, item in self.psdrives.items()
            ]
            return _result(True, stdout=json.dumps(payload))
        if script.startswith("New-PSDrive") or "\nNew-PSDrive" in script:
            match = re.search(
                r"-Name '([^']*)' -PSProvider '([^']*)' -Root '([^']*)'( -Persist)?",
                script,
            )
            if not match:
                return _result(False, stderr="New-PSDrive konnte nicht gelesen werden")
            root = match.group(3).replace("''", "'")
            self.psdrives[match.group(1)] = {"provider": match.group(2), "root": root}
            return _result(True)
        if "Remove-PSDrive" in script:
            match = re.search(r"-Name '([^']*)'", script)
            if not match or match.group(1) not in self.psdrives:
                return _result(False, stderr="Das PowerShell-Laufwerk ist nicht vorhanden.")
            del self.psdrives[match.group(1)]
            return _result(True)
        if "ReparsePoint" in script:
            match = re.search(r"\$root = '([^']*)'", script)
            folder = (match.group(1) if match else "").replace("''", "'")
            return _result(True, stdout=json.dumps(self._reparse_payload(folder)))
        return _result(False, stderr="Dieses PowerShell-Skript ist in der Vorschau nicht hinterlegt.")

    def spawn(self, args: list[str]) -> None:
        self.spawned.append(list(args))
        if args and args[0].lower().startswith("powershell") and len(args) >= 1:
            command = args[-1]
            if "New-PSDrive" in command:
                self.run_powershell(command)

    def path_isdir(self, path: str) -> bool:
        return self._kind(path) == "dir"

    def path_isfile(self, path: str) -> bool:
        return self._kind(path) == "file"

    def path_exists(self, path: str) -> bool:
        return self.path_occupied(path) or self._kind(path) in {"dir", "file"}

    def path_occupied(self, path: str) -> bool:
        """True nur für Pfade, die die Vorschau wirklich angelegt oder registriert hat."""
        key = self._key(path)
        return key in self.files or key in self.dirs or key in self.links

    def dir_is_empty(self, path: str) -> bool:
        if not self.path_isdir(path):
            return False
        if not self.strict_paths:
            return True
        key = self._key(path)
        if key in self.nonempty:
            return False
        for link in self.links:
            parent = self._key(str(Path(link).parent))
            if parent == key:
                return False
        return True

    def is_reparse(self, path: str) -> bool:
        return self._key(path) in self.links

    def list_folders(self, path: str) -> list[str]:
        """Unterordner eines Laufwerks oder Ordners. Die Vorschau kennt einen festen Baum unter C:."""
        resolved = map_through_subst(path, self.subst)
        return list(_PREVIEW_FOLDERS.get(norm_path(resolved), []))

    def logical_drives(self) -> set[str]:
        letters = set(self.subst) | set(self.net)
        for volume in self.volumes:
            for mount in volume["mounts"]:
                if re.fullmatch(r"[A-Za-z]:\\?", mount):
                    letters.add(mount[0].upper())
        return letters

    def drive_type(self, letter: str) -> str:
        """subst, remote, fixed oder unknown. Echte Wechselmedien gibt die Vorschau nicht vor."""
        normalized = normalize_letter(letter)
        if normalized is None:
            return "unknown"
        if normalized in self.subst:
            return "subst"
        if normalized in self.net:
            return "remote"
        for volume in self.volumes:
            for mount in volume["mounts"]:
                if mount[:1].upper() == normalized and (len(mount) < 2 or mount[1] == ":"):
                    return "fixed"
        return "unknown"

    def notify_shell(self) -> None:
        return None

    def elevate(self) -> None:
        self.set_admin(True)

    def documents_dir(self) -> Path:
        return self.root / "Documents"

    def profile_paths(self) -> list[Path]:
        documents = self.documents_dir()
        return [
            documents / "WindowsPowerShell" / "profile.ps1",
            documents / "PowerShell" / "profile.ps1",
        ]

    def read_text(self, path: Path) -> str:
        file_path = Path(path)
        if not file_path.is_file():
            return ""
        return file_path.read_text(encoding="utf-8")

    def write_text(self, path: Path, text: str) -> None:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(text, encoding="utf-8")

    def open_path(self, path: str) -> None:
        self.spawned.append(["explorer", path])

    def open_msc(self, name: str) -> None:
        self.spawned.append(["mmc", name])

    def task_exists(self) -> bool:
        return self.task

    def create_logon_task(self, command: str, arguments: str) -> RunResult:
        if not self.admin:
            return _result(False, stderr="Zugriff verweigert")
        # Die XML wird erzeugt, damit fehlerhafte Escape-Logik auch in der Vorschau auffällt.
        xml = task_xml(command, arguments)
        if command not in xml or "--restore" not in xml:
            return _result(False, stderr="Aufgabendefinition unvollständig")
        self.task = True
        return _result(True, stdout="Erfolg: Die geplante Aufgabe wurde erstellt.")

    def delete_logon_task(self) -> RunResult:
        if not self.admin:
            return _result(False, stderr="Zugriff verweigert")
        self.task = False
        return _result(True)

    def pythonw(self) -> str:
        return pythonw_executable()

    def script_path(self) -> str:
        return str(entry_script())

    def _subst(self, args: list[str]) -> RunResult:
        if len(args) == 1:
            return _result(True, stdout=format_subst(self.subst))
        if len(args) >= 3 and args[2].upper() == "/D":
            letter = args[1].rstrip(":").upper()
            if letter not in self.subst:
                return _result(False, stderr="Ungültiger Parameter: Laufwerk nicht verbunden.", code=1)
            del self.subst[letter]
            return _result(True)
        if len(args) >= 3:
            letter = args[1].rstrip(":").upper()
            path = args[2]
            if letter in self.logical_drives() and self.subst.get(letter) != path:
                return _result(False, stderr="Laufwerk bereits belegt.", code=1)
            self.subst[letter] = path
            self.dirs.add(self._key(path))
            return _result(True)
        return _result(False, stderr="Syntaxfehler bei subst")

    def _net(self, args: list[str]) -> RunResult:
        if len(args) >= 2 and args[1].lower() == "use":
            return self._net_use(args)
        if len(args) >= 2 and args[1].lower() == "share":
            return self._net_share(args)
        return _result(False, stderr="Unbekannter net-Befehl")

    def _net_use(self, args: list[str]) -> RunResult:
        if len(args) == 2:
            return _result(True, stdout=format_net_use(list(self.net.values())))
        if "/delete" in [item.lower() for item in args]:
            letter = args[2].rstrip(":").upper()
            if letter not in self.net:
                return _result(False, stderr="Netzwerkverbindung nicht gefunden.", code=2)
            del self.net[letter]
            self.registry.delete_value("HKCU", rf"Network\{letter}", "RemotePath")
            return _result(True, stdout="Der Befehl wurde erfolgreich ausgeführt.")
        letter = args[2].rstrip(":").upper()
        remote = args[3]
        persistent = any(item.lower() == "/persistent:yes" for item in args)
        if letter in self.logical_drives() and letter not in self.net:
            return _result(False, stderr="Laufwerk bereits belegt.", code=1)
        self.net[letter] = LiveNet("OK", letter, remote, "Microsoft Windows Network")
        if persistent:
            self.registry.set_sz("HKCU", rf"Network\{letter}", "RemotePath", remote)
        return _result(True, stdout="Der Befehl wurde erfolgreich ausgeführt.")

    def _net_share(self, args: list[str]) -> RunResult:
        if len(args) == 2:
            return _result(True, stdout=format_net_share(list(self.shares.values())))
        if "/delete" in [item.lower() for item in args]:
            name = args[2]
            if name not in self.shares:
                return _result(False, stderr="Freigabe nicht gefunden.", code=2)
            del self.shares[name]
            return _result(True, stdout="Freigabe wurde gelöscht.")
        if not self.admin:
            return _result(False, stderr="Zugriff verweigert", code=5)
        assignment = args[2]
        if "=" not in assignment:
            return _result(False, stderr="Syntaxfehler bei net share")
        name, path = assignment.split("=", 1)
        self.shares[name] = LiveShare(name, path, "")
        return _result(True, stdout="Freigabe wurde erstellt.")

    def _cmd(self, args: list[str]) -> RunResult:
        if len(args) < 3 or args[1].lower() != "/c":
            return _result(False, stderr="cmd ohne /c")
        tokens = tokenize_cmd(args[2])
        if not tokens:
            return _result(False, stderr="Leeres cmd")
        head = tokens[0].lower()
        if head == "mklink":
            return self._mklink(tokens)
        if head == "rmdir":
            link = tokens[-1]
            key = self._key(link)
            if key not in self.links:
                return _result(False, stderr="Das System kann die angegebene Datei nicht finden.", code=2)
            if self.links[key].get("kind") == "symlink_file":
                return _result(False, stderr="rmdir erwartet einen Ordnerlink.")
            del self.links[key]
            return _result(True)
        if head == "del":
            link = tokens[-1]
            key = self._key(link)
            item = self.links.get(key)
            if item is None:
                return _result(False, stderr="Datei nicht gefunden.", code=2)
            if item.get("kind") not in {"symlink_file", "hardlink"}:
                return _result(False, stderr="del entfernt keinen Ordnerlink.")
            del self.links[key]
            return _result(True)
        return _result(False, stderr=f"Unbekannter cmd-Befehl: {tokens[0]}")

    def _mklink(self, tokens: list[str]) -> RunResult:
        kind = "symlink_file"
        rest = tokens[1:]
        if rest and rest[0].upper() == "/J":
            kind = "junction"
            rest = rest[1:]
        elif rest and rest[0].upper() == "/D":
            kind = "symlink_dir"
            rest = rest[1:]
        elif rest and rest[0].upper() == "/H":
            kind = "hardlink"
            rest = rest[1:]
        if len(rest) < 2:
            return _result(False, stderr="Syntaxfehler bei mklink")
        link, target = rest[0], rest[1]
        key = self._key(link)
        if key in self.links or (self.strict_paths and self._kind(link) != "missing"):
            return _result(False, stderr="Die Datei existiert bereits.", code=1)
        if kind in {"symlink_dir", "symlink_file"} and not self.admin and self.registry.get_dword(
            "HKLM",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock",
            "AllowDevelopmentWithoutDevLicense",
        ) != 1:
            return _result(False, stderr="Sie verfügen nicht über ausreichende Berechtigungen für symbolische Links.", code=1)
        self.links[key] = {"kind": kind, "link": link, "target": target}
        return _result(True, stdout=f"Verknüpfung erstellt für {link}")

    def _mountvol(self, args: list[str]) -> RunResult:
        if len(args) == 1:
            volumes = [LiveVolume(item["id"], list(item["mounts"])) for item in self.volumes]
            return _result(True, stdout=format_mountvol(volumes))
        if len(args) >= 3 and args[2].upper() == "/D":
            target = args[1]
            for volume in self.volumes:
                before = list(volume["mounts"])
                volume["mounts"] = [mount for mount in volume["mounts"] if not self._same_mount(mount, target)]
                if volume["mounts"] != before:
                    return _result(True)
            return _result(False, stderr="Das System kann den angegebenen Pfad nicht finden.", code=2)
        if len(args) >= 3:
            target, volume_id = args[1], args[2]
            for volume in self.volumes:
                if volume["id"].lower() == volume_id.lower():
                    if any(self._same_mount(mount, target) for mount in volume["mounts"]):
                        return _result(True)
                    shown = target + "\\" if re.fullmatch(r"[A-Za-z]:", target) else target
                    volume["mounts"].append(shown)
                    return _result(True)
            return _result(False, stderr="Das angegebene Volume wurde nicht gefunden.", code=2)
        return _result(False, stderr="Syntaxfehler bei mountvol")

    def _schtasks(self, args: list[str]) -> RunResult:
        lowered = [item.lower() for item in args]
        if "/query" in lowered:
            if self.task:
                return _result(True, stdout=TASK_NAME)
            return _result(False, stderr="FEHLER: Das System kann die angegebene Datei nicht finden.", code=1)
        if "/create" in lowered:
            return self.create_logon_task("pythonw", "--restore")
        if "/delete" in lowered:
            return self.delete_logon_task()
        return _result(False, stderr="Unbekannter schtasks-Aufruf")

    def _reparse_payload(self, folder: str) -> list[dict]:
        parent = self._key(folder)
        rows = []
        for _key, item in self.links.items():
            if self._key(parent_dir(item["link"])) != parent:
                continue
            kind = item["kind"]
            link_type = "Junction" if kind == "junction" else "SymbolicLink"
            attributes = 16 if kind in {"junction", "symlink_dir"} else 0
            rows.append(
                {
                    "Link": item["link"],
                    "LinkType": link_type,
                    "Attributes": attributes,
                    "Target": item["target"],
                }
            )
        return rows

    def _kind(self, path: str) -> str:
        key = self._key(path)
        if key in self.files:
            return "file"
        if key in self.dirs:
            return "dir"
        if self.strict_paths:
            return "missing"
        return _permissive_kind(path)

    def _key(self, path: str) -> str:
        return norm_path(path)

    def _same_mount(self, left: str, right: str) -> bool:
        return left.rstrip("\\").lower() == right.rstrip("\\").lower()


def _preview_tree() -> dict[str, list[str]]:
    raw = {
        "C:\\": ["Benutzer", "Programme", "Projekte", "Windows"],
        "C:\\Benutzer": ["Öffentlich"],
        "C:\\Benutzer\\Öffentlich": ["Dokumente"],
        "C:\\Programme": ["SphereDrive"],
        "C:\\Projekte": ["Archiv", "SphereDrive"],
        "C:\\Projekte\\Archiv": ["2024", "2026"],
        "C:\\Projekte\\Archiv\\2024": [],
        "C:\\Projekte\\Archiv\\2026": [],
        "C:\\Projekte\\SphereDrive": ["assets"],
        "C:\\Projekte\\SphereDrive\\assets": [],
        "C:\\Programme\\SphereDrive": [],
        "C:\\Windows": ["System32"],
        "C:\\Windows\\System32": [],
    }
    return {norm_path(path): names for path, names in raw.items()}


_PREVIEW_FOLDERS = _preview_tree()


def _permissive_kind(path: str) -> str:
    text = path.strip().strip('"')
    if not text:
        return "missing"
    if text.startswith("\\\\"):
        return "dir"
    name = os.path.basename(text.rstrip("\\/"))
    looks_file = "." in name and not name.startswith(".")
    if len(text) >= 3 and text[1] == ":":
        return "file" if looks_file else "dir"
    if text.startswith("/"):
        return "file" if looks_file else "dir"
    return "missing"


class WindowsHost:
    preview = False

    def __init__(self) -> None:
        self.registry = WindowsRegistry()
        self.calls: list[list[str]] = []

    def is_admin(self) -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except (AttributeError, OSError):
            return False

    def run(self, args: list[str], *, input_text: str | None = None, timeout: int = 30) -> RunResult:
        self.calls.append(list(args))
        encoding = locale.getpreferredencoding(False)
        flags = CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            completed = subprocess.run(
                args,
                input=input_text,
                capture_output=True,
                text=True,
                encoding=encoding,
                errors="replace",
                timeout=timeout,
                creationflags=flags,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return _result(False, stderr="Zeitüberschreitung beim Ausführen des Befehls.")
        except FileNotFoundError:
            return _result(False, stderr=f"Befehl nicht gefunden: {args[0]}")
        except OSError as exc:
            return _result(False, stderr=str(exc))
        return RunResult(
            completed.returncode == 0,
            completed.stdout or "",
            completed.stderr or "",
            completed.returncode,
        )

    def run_powershell(self, script: str, *, timeout: int = 45) -> RunResult:
        return self.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            timeout=timeout,
        )

    def spawn(self, args: list[str]) -> None:
        flags = CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
        subprocess.Popen(args, creationflags=flags)

    def path_isdir(self, path: str) -> bool:
        return os.path.isdir(path)

    def path_isfile(self, path: str) -> bool:
        return os.path.isfile(path)

    def path_exists(self, path: str) -> bool:
        return os.path.exists(path)

    def path_occupied(self, path: str) -> bool:
        return os.path.exists(path)

    def dir_is_empty(self, path: str) -> bool:
        if not os.path.isdir(path):
            return False
        try:
            return next(os.scandir(path), None) is None
        except OSError:
            return False

    def is_reparse(self, path: str) -> bool:
        kernel = ctypes.windll.kernel32
        kernel.GetFileAttributesW.argtypes = [ctypes.c_wchar_p]
        kernel.GetFileAttributesW.restype = ctypes.c_uint32
        attrs = kernel.GetFileAttributesW(path)
        if attrs == INVALID_FILE_ATTRIBUTES:
            return False
        return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)

    def list_folders(self, path: str) -> list[str]:
        names: list[str] = []
        try:
            with os.scandir(path) as scan:
                for entry in scan:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            names.append(entry.name)
                    except OSError:
                        continue
        except OSError:
            return []
        return sorted(names, key=str.casefold)

    def logical_drives(self) -> set[str]:
        try:
            mask = ctypes.windll.kernel32.GetLogicalDrives()
        except (AttributeError, OSError):
            return set()
        letters = set()
        for index in range(26):
            if mask & (1 << index):
                letters.add(chr(ord("A") + index))
        return letters

    def drive_type(self, letter: str) -> str:
        """GetDriveTypeW: removable, fixed, remote, cdrom, ramdisk oder unknown."""
        normalized = normalize_letter(letter)
        if normalized is None:
            return "unknown"
        try:
            kernel = ctypes.windll.kernel32
            kernel.GetDriveTypeW.argtypes = [ctypes.c_wchar_p]
            kernel.GetDriveTypeW.restype = ctypes.c_uint32
            code = int(kernel.GetDriveTypeW(f"{normalized}:\\"))
        except (AttributeError, OSError, ValueError):
            return "unknown"
        return {2: "removable", 3: "fixed", 4: "remote", 5: "cdrom", 6: "ramdisk"}.get(code, "unknown")

    def notify_shell(self) -> None:
        # SHCNE_ASSOCCHANGED | SHCNF_FLUSH, damit Explorer Bezeichnung und Symbol neu liest.
        try:
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x1000, None, None)
        except (AttributeError, OSError):
            return

    def elevate(self) -> None:
        executable, arguments = gui_launch()
        ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, arguments, None, 1)

    def documents_dir(self) -> Path:
        result = self.run_powershell("[Environment]::GetFolderPath('MyDocuments')", timeout=20)
        if result.ok and result.stdout.strip():
            return Path(result.stdout.strip().splitlines()[-1])
        return Path.home() / "Documents"

    def profile_paths(self) -> list[Path]:
        documents = self.documents_dir()
        return [
            documents / "WindowsPowerShell" / "profile.ps1",
            documents / "PowerShell" / "profile.ps1",
        ]

    def read_text(self, path: Path) -> str:
        file_path = Path(path)
        if not file_path.is_file():
            return ""
        return file_path.read_text(encoding="utf-8")

    def write_text(self, path: Path, text: str) -> None:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(text, encoding="utf-8")

    def open_path(self, path: str) -> None:
        os.startfile(path)  # noqa: S606  Windows-Shell öffnet den Ordner.

    def open_msc(self, name: str) -> None:
        subprocess.Popen(["cmd", "/c", "start", "", name], creationflags=CREATE_NO_WINDOW)

    def task_exists(self) -> bool:
        result = self.run(["schtasks", "/Query", "/TN", TASK_NAME], timeout=20)
        return result.ok

    def create_logon_task(self, command: str, arguments: str) -> RunResult:
        import tempfile

        xml = task_xml(command, arguments)
        handle = tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-16")
        try:
            handle.write(xml)
            handle.close()
            return self.run(["schtasks", "/Create", "/TN", TASK_NAME, "/XML", handle.name, "/F"], timeout=30)
        finally:
            try:
                os.remove(handle.name)
            except OSError:
                pass

    def delete_logon_task(self) -> RunResult:
        return self.run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"], timeout=20)

    def pythonw(self) -> str:
        return pythonw_executable()

    def script_path(self) -> str:
        return str(entry_script())


def system_caption(build: int | None = None) -> str:
    """Name des laufenden Systems. Windows 11 beginnt bei Build 22000."""
    if build is None:
        if sys.platform != "win32":
            from spheredrive.i18n import t

            return t("Vorschau")
        try:
            build = int(sys.getwindowsversion().build)
        except (AttributeError, OSError, ValueError):
            return "Windows"
    if build >= 22000:
        return "Windows 11"
    if build >= 10240:
        return "Windows 10"
    return "Windows"


def make_host() -> PreviewHost | WindowsHost:
    if sys.platform == "win32":
        return WindowsHost()
    return PreviewHost()


