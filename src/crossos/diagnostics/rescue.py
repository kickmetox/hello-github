"""Rettungspläne für NTFS, ext4 und btrfs. Nichts wird ausgeführt.

Windows kann ext4 und btrfs nicht nativ mit fsck prüfen. Der Plan sagt das
und schlägt höchstens ``fsck -n`` in WSL oder das besitzende Linux vor.
"""

from __future__ import annotations

import re

from crossos.safety import SafetyError

_LINUX_DEVICE = re.compile(r"^/dev/(sd[a-z]\d*|nvme\d+n\d+(p\d+)?|mmcblk\d+(p\d+)?|vd[a-z]\d*)$")
_WIN_DRIVE = re.compile(r"^[A-Z]:$")
_FILESYSTEMS = {"ntfs", "ext4", "btrfs", "exfat", "vfat"}


def rescue_plan(*, host_os: str, filesystem: str, device: str) -> dict:
    host = host_os.lower().strip()
    fs = filesystem.lower().strip()
    if host not in {"linux", "windows"}:
        raise SafetyError("host_os muss linux oder windows sein.")
    if fs not in _FILESYSTEMS:
        raise SafetyError("Dateisystem ist nicht in ntfs, ext4, btrfs, exfat, vfat.")
    if not isinstance(device, str):
        raise SafetyError("Gerät fehlt.")
    common = {
        "executed": False,
        "auto_apply": False,
        "host_os": host,
        "filesystem": fs,
        "device": device,
    }
    if host == "linux":
        if not _LINUX_DEVICE.fullmatch(device):
            raise SafetyError("Linux-Gerät muss wie /dev/sda1, /dev/nvme0n1p2 oder /dev/vda aussehen.")
        return common | _linux(fs, device)
    if not _WIN_DRIVE.fullmatch(device):
        raise SafetyError("Unter Windows wird nur ein Laufwerksbuchstabe wie E: angenommen, kein /dev-Knoten.")
    return common | _windows(fs, device)


def _linux(fs: str, device: str) -> dict:
    if fs == "ntfs":
        return {
            "native": True,
            "destructive_default": False,
            "plan_de": (
                "NTFS wird von Linux aus nur gelesen und geplant. ntfsfix ohne --no-action "
                "schreibt Metadaten und wird nicht erzeugt als Apply. Zuerst Gerät mit lsblk prüfen."
            ),
            "steps": [
                {"argv": ["lsblk", "-f"], "read_only": True},
                {"argv": ["ntfsinfo", "-m", device], "read_only": True},
                {
                    "argv": ["ntfsfix", "--no-action", device],
                    "read_only": True,
                    "note_de": "Nur anzeigen. Ein ntfsfix ohne --no-action ist hier kein Schritt.",
                },
            ],
            "do_not_run": [
                ["ntfsfix", device],
                ["ntfsfix", "-d", device],
                ["mkfs.ntfs", device],
            ],
        }
    if fs in {"ext4", "btrfs"}:
        return {
            "native": True,
            "plan_de": (
                f"{fs} gehört auf diesem Linux geprüft, und nur wenn es nicht gemountet ist. "
                "Der Plan enthält fsck -n. Eine Reparatur ohne -n wird nicht angesetzt."
            ),
            "steps": [
                {"argv": ["lsblk", "-f"], "read_only": True},
                {"argv": ["findmnt", device], "read_only": True, "note_de": "Wenn hier eine Mountzeile steht, kein fsck."},
                {"argv": ["fsck", "-n", device], "read_only": True},
            ],
            "do_not_run": [["fsck", "-y", device], ["fsck", "-fy", device]],
        }
    return {
        "native": True,
        "plan_de": f"{fs} wird nur benannt. Es wird kein Reparaturbefehl erzeugt.",
        "steps": [{"argv": ["lsblk", "-f"], "read_only": True}],
        "do_not_run": [["mkfs", device]],
    }


def _windows(fs: str, device: str) -> dict:
    if fs in {"ext4", "btrfs"}:
        return {
            "native": False,
            "native_fsck": False,
            "plan_de": (
                f"Windows kann {fs} nicht nativ mit fsck prüfen oder reparieren. "
                "Eine Prüfung ist entweder das Linux, dem das Dateisystem gehört, "
                "oder in WSL ausdrücklich nur lesend mit fsck -n. CrossOS tut so, "
                "als gäbe es keinen Windows-fsck für dieses Dateisystem, weil es ihn nicht gibt."
            ),
            "owning_os_de": "Reparatur auf dem Linux ausführen, das das Dateisystem eingehängt hat oder besitzen soll.",
            "wsl_plan": {
                "argv": ["wsl", "-d", "DISTRO", "--", "fsck", "-n", "/dev/sdX"],
                "note_de": "DISTRO und das Gerätefile in WSL nicht raten. -n ändert nichts. Ohne -n nicht ausführen.",
            },
            "do_not_run": [
                ["fsck", device],
                ["chkdsk", device, "/f"],
            ],
        }
    if fs == "ntfs":
        return {
            "native": True,
            "plan_de": "NTFS gehört unter Windows zu chkdsk. CrossOS setzt nur einen Scan-Plan, kein /f.",
            "steps": [
                {"argv": ["chkdsk", device, "/scan"], "read_only": True, "note_de": "Scan ist der Plan. /f ist nicht enthalten."},
            ],
            "do_not_run": [["chkdsk", device, "/f"], ["format", device]],
        }
    return {
        "native": True,
        "plan_de": f"{fs} unter Windows wird nur benannt.",
        "steps": [],
        "do_not_run": [["format", device]],
    }
