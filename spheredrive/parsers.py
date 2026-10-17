"""Parser für die Textausgaben von subst, net und mountvol."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass


@dataclass
class LiveSubst:
    letter: str
    path: str


@dataclass
class LiveNet:
    status: str
    letter: str
    remote: str
    network: str


@dataclass
class LiveShare:
    name: str
    path: str
    remark: str


@dataclass
class LiveVolume:
    id: str
    mounts: list[str]


_SUBST = re.compile(r"^([A-Za-z]):\\?:?\s*=>\s*(.+?)\s*$")
_NET = re.compile(
    r"^(?P<status>.*?)\s+(?P<local>[A-Za-z]:)\s+(?P<remote>\\\\[^\s]+)\s+(?P<network>\S.*)$"
)
_VOLUME = re.compile(r"\\\\\?\\Volume\{([0-9A-Fa-f-]{36})\}\\")
_NO_MOUNT = ("NO MOUNT POINTS", "KEINE BEREITSTELLUNGSPUNKTE")


def parse_subst(text: str) -> list[LiveSubst]:
    found: list[LiveSubst] = []
    for raw in text.splitlines():
        match = _SUBST.match(raw.strip())
        if not match:
            continue
        found.append(LiveSubst(match.group(1).upper(), match.group(2).strip()))
    return found


def format_subst(drives: dict[str, str]) -> str:
    lines = [f"{letter}:\\: => {path}" for letter, path in sorted(drives.items())]
    return "\n".join(lines)


def parse_net_use(text: str) -> list[LiveNet]:
    found: list[LiveNet] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if "\\\\" not in line:
            continue
        match = _NET.match(line.strip())
        if not match:
            continue
        found.append(
            LiveNet(
                status=match.group("status").strip() or "OK",
                letter=match.group("local").rstrip(":").upper(),
                remote=match.group("remote").strip(),
                network=match.group("network").strip(),
            )
        )
    return found


def format_net_use(drives: list[LiveNet]) -> str:
    lines = [
        "Neue Verbindungen werden gespeichert.",
        "",
        "Status       Lokal     Remote                    Netzwerk",
        "-------------------------------------------------------------------------------",
    ]
    for item in drives:
        lines.append(f"{item.status:<12} {item.letter}:        {item.remote:<26} {item.network}")
    lines.append("Der Befehl wurde erfolgreich ausgeführt.")
    return "\n".join(lines)


def parse_net_share(text: str) -> list[LiveShare]:
    found: list[LiveShare] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("-") or stripped.lower().startswith("share name"):
            continue
        if stripped.lower().startswith("freigabename"):
            continue
        if "Befehl wurde" in stripped or "command completed" in stripped.lower():
            continue
        match = re.match(r"^(\S+)\s+((?:[A-Za-z]:\\|\\\\).+)$", stripped)
        if not match:
            continue
        name, rest = match.group(1), match.group(2).strip()
        parts = re.split(r"\s{2,}", rest, maxsplit=1)
        path = parts[0].strip()
        remark = parts[1].strip() if len(parts) > 1 else ""
        found.append(LiveShare(name, path, remark))
    return found


def format_net_share(shares: list[LiveShare]) -> str:
    lines = [
        "Freigabename   Ressource                       Bemerkung",
        "-------------------------------------------------------------------------------",
    ]
    for item in shares:
        lines.append(f"{item.name:<14} {item.path:<32} {item.remark}".rstrip())
    lines.append("Der Befehl wurde erfolgreich ausgeführt.")
    return "\n".join(lines)


def parse_mountvol(text: str) -> list[LiveVolume]:
    current: LiveVolume | None = None
    found: list[LiveVolume] = []
    for raw in text.splitlines():
        match = _VOLUME.search(raw)
        if match and "Volume{" in raw:
            current = LiveVolume(id=f"\\\\?\\Volume{{{match.group(1)}}}\\", mounts=[])
            found.append(current)
            continue
        if current is None:
            continue
        stripped = raw.strip()
        if not stripped:
            continue
        upper = stripped.upper()
        if any(marker in upper for marker in _NO_MOUNT):
            continue
        current.mounts.append(stripped)
    return found


def format_mountvol(volumes: list[LiveVolume]) -> str:
    lines: list[str] = []
    for volume in volumes:
        lines.append(f"    {volume.id}")
        if volume.mounts:
            for mount in volume.mounts:
                lines.append(f"        {mount}")
        else:
            lines.append("        *** NO MOUNT POINTS ***")
        lines.append("")
    return "\n".join(lines)


def parse_json_list(text: str) -> list:
    raw = text.strip()
    if not raw:
        return []
    # PowerShell schreibt manchmal Warnungen vor das JSON.
    start_obj = raw.find("{")
    start_arr = raw.find("[")
    starts = [index for index in (start_obj, start_arr) if index >= 0]
    if not starts:
        raise json.JSONDecodeError("kein JSON", raw, 0)
    data = json.loads(raw[min(starts):])
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    return []


def tokenize_cmd(line: str) -> list[str]:
    tokens: list[str] = []
    index = 0
    while index < len(line):
        char = line[index]
        if char == '"':
            end = line.find('"', index + 1)
            if end < 0:
                tokens.append(line[index + 1:])
                break
            tokens.append(line[index + 1:end])
            index = end + 1
        elif char.isspace():
            index += 1
        else:
            end = index
            while end < len(line) and not line[end].isspace():
                end += 1
            tokens.append(line[index:end])
            index = end
    return tokens


def as_int(value: object) -> int:
    if value is None or value == "":
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(str(value)))
        except (TypeError, ValueError):
            return 0
