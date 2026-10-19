"""Prüfpläne für Dateisysteme der anderen Welt. Es wird nichts geschrieben."""

from __future__ import annotations

import re

_DEVICE = re.compile(r"^(?:/dev/[\w/-]+|[A-Za-z]:)$")


def repair_plan(source_world: str, filesystem: str, device: str) -> dict:
    filesystem = filesystem.casefold().strip()
    device = device.strip()
    if device and not _DEVICE.match(device):
        raise ValueError("Gerät muss wie /dev/nvme0n1p3 oder C: aussehen")
    placeholder = device or "<GERAET>"
    if filesystem == "ntfs" and source_world == "linux":
        return {
            "summary": "NTFS lässt sich unter Linux prüfen. Eine echte Reparatur macht Windows mit chkdsk, besonders wenn Schnellstart aktiv war.",
            "commands": [f"sudo ntfsfix -n {placeholder}"],
            "writes": False,
        }
    if filesystem in ("ext4", "btrfs") and source_world == "windows":
        if filesystem == "ext4":
            command = f"wsl -d <DISTRO> -- sudo fsck.ext4 -n {placeholder}"
        else:
            command = f"wsl -d <DISTRO> -- sudo btrfs check --readonly {placeholder}"
        return {
            "summary": "Windows prüft ext4 und Btrfs nicht selbst. Der sichere Weg ist eine Prüfung ohne Schreiben aus WSL oder von einem Linux-Medium.",
            "commands": [command],
            "writes": False,
        }
    if filesystem == "ntfs" and source_world == "windows":
        return {"summary": "Unter Windows prüft chkdsk NTFS.", "commands": [f"chkdsk {device or 'C:'} /scan"], "writes": False}
    if filesystem == "ext4" and source_world == "linux":
        return {"summary": "Prüfung ohne Schreiben. Das Gerät darf nicht eingehängt sein.", "commands": [f"sudo fsck.ext4 -n {placeholder}"], "writes": False}
    if filesystem == "btrfs" and source_world == "linux":
        return {"summary": "Prüfung ohne Schreiben.", "commands": [f"sudo btrfs check --readonly {placeholder}"], "writes": False}
    raise ValueError("Unterstützt werden ntfs, ext4 und btrfs")
