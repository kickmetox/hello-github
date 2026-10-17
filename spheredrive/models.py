"""Datenmodelle für Zuordnungen, Momentaufnahmen und Aktionsergebnisse."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OpResult:
    ok: bool
    message: str
    warnings: list[str] = field(default_factory=list)
    relaunch: bool = False
    code: str = ""

    def text(self) -> str:
        return "\n".join(part for part in (self.message, *self.warnings) if part)


@dataclass
class SubstSpec:
    letter: str
    path: str
    label: str = ""
    icon: str = ""
    persistent: bool = True
    uac: bool = False
    recycle: bool = False
    recycle_mb: int = 10240


@dataclass
class NetSpec:
    letter: str
    remote: str
    user: str = ""
    password: str = ""
    persistent: bool = True
    label: str = ""
    icon: str = ""


@dataclass
class ShareSpec:
    name: str
    path: str
    permission: str = "READ"
    principal: str = ""


@dataclass
class LinkSpec:
    kind: str
    link: str
    target: str


@dataclass
class PsSpec:
    name: str
    provider: str
    root: str
    profile: bool = False
    persist_windows: bool = False


@dataclass
class MountSpec:
    volume: str
    target: str


@dataclass
class SubstEntry:
    letter: str
    path: str
    label: str = ""
    icon: str = ""
    persistent: bool = False
    uac: bool = False
    recycle: bool = False
    recycle_guid: str = ""
    recycle_mb: int = 10240
    status: str = ""
    managed: bool = False


@dataclass
class NetEntry:
    letter: str
    remote: str
    status: str = ""
    persistent: bool = False
    user: str = ""
    label: str = ""
    icon: str = ""
    managed: bool = False


@dataclass
class ShareEntry:
    name: str
    path: str
    remark: str = ""


@dataclass
class LinkEntry:
    kind: str
    link: str
    target: str
    status: str = ""
    managed: bool = False


@dataclass
class PsEntry:
    name: str
    provider: str
    root: str
    profile: bool = False
    persist_windows: bool = False
    status: str = ""
    managed: bool = False


@dataclass
class VolumeEntry:
    id: str
    label: str
    filesystem: str
    capacity: int = 0
    free: int = 0
    mounts: list[str] = field(default_factory=list)


@dataclass
class DriveCard:
    """Eine Kachel in der Laufwerksübersicht, unabhängig von der Herkunft des Buchstabens."""

    letter: str
    title: str
    kind: str
    kind_label: str
    target: str
    label: str = ""
    icon: str = ""
    persistent: bool = False
    uac: bool = False
    recycle: bool = False
    recycle_mb: int = 10240
    capacity: int = 0
    free: int = 0
    filesystem: str = ""
    status: str = ""
    origin: str = ""
    managed: bool = False
    real_fixed: bool = False
    can_disconnect: bool = False
    user: str = ""


@dataclass
class Snapshot:
    subst: list[SubstEntry]
    net: list[NetEntry]
    shares: list[ShareEntry]
    links: list[LinkEntry]
    psdrives: list[PsEntry]
    volumes: list[VolumeEntry]
    admin: bool
    linked_connections: bool
    autostart: bool
    elevated_task: bool
    preview: bool
