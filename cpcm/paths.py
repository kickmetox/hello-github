"""Pfadabbildung zwischen Linux- und Windows-Welt."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class World(str, Enum):
    LINUX = "linux"
    WINDOWS = "windows"


KNOWN_FOLDERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("desktop", ("Desktop",)),
    ("documents", ("Documents", "Dokumente")),
    ("downloads", ("Downloads",)),
    ("pictures", ("Pictures", "Bilder")),
    ("music", ("Music", "Musik")),
    ("videos", ("Videos",)),
)

_KNOWN_BY_NAME: dict[str, str] = {}
for _canonical, _names in KNOWN_FOLDERS:
    for _name in _names:
        _KNOWN_BY_NAME[_name.casefold()] = _canonical


@dataclass(frozen=True)
class Identity:
    world: World
    home: Path
    appdata: Path
    localappdata: Path
    user: str

    def native_external(self) -> bool:
        if self.world == World.WINDOWS:
            return os.name == "nt"
        return os.name != "nt"


def host_world() -> World:
    return World.WINDOWS if os.name == "nt" else World.LINUX


def host_identity() -> Identity:
    home = Path.home()
    user = home.name or os.environ.get("USER") or os.environ.get("USERNAME") or "user"
    if host_world() == World.WINDOWS:
        home = Path(os.environ.get("USERPROFILE", str(home)))
        appdata = Path(os.environ.get("APPDATA", str(home / "AppData" / "Roaming")))
        localappdata = Path(os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local")))
        user = os.environ.get("USERNAME") or home.name or user
        return Identity(World.WINDOWS, home, appdata, localappdata, user)
    return Identity(World.LINUX, home, home / ".config", home / ".local" / "share", user)


def _windows_syntax(root: str) -> bool:
    return root.startswith("\\\\") or (len(root) >= 2 and root[0].isalpha() and root[1] == ":")


def join_root(root: str, *parts: str) -> str:
    sep = "\\" if _windows_syntax(root) else "/"
    current = root.rstrip("\\/")
    for part in parts:
        piece = str(part).strip("\\/")
        if piece:
            current = f"{current}{sep}{piece}"
    return current


def identity_for_home(world: World, home: Path, user: str | None = None) -> Identity:
    home = Path(home)
    name = user or home.name or "user"
    home_str = str(home)
    if world == World.WINDOWS and _windows_syntax(home_str):
        return Identity(
            world,
            home,
            Path(join_root(home_str, "AppData", "Roaming")),
            Path(join_root(home_str, "AppData", "Local")),
            name,
        )
    if world == World.WINDOWS:
        return Identity(
            world,
            home,
            home / "AppData" / "Roaming",
            home / "AppData" / "Local",
            name,
        )
    return Identity(world, home, home / ".config", home / ".local" / "share", name)


def _abspath(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def relative_if_inside(path: Path, root: Path) -> str | None:
    child = _abspath(path)
    base = _abspath(root)
    try:
        rel = child.relative_to(base)
    except ValueError:
        if os.name != "nt":
            return None
        child_c = os.path.normcase(str(child))
        base_c = os.path.normcase(str(base))
        if child_c == base_c:
            return ""
        prefix = base_c if base_c.endswith("\\") else base_c + "\\"
        if not child_c.startswith(prefix):
            return None
        rel = Path(str(child)[len(str(base)) :].lstrip("\\/"))
    if any(part in ("", ".", "..") for part in rel.parts):
        return None
    return rel.as_posix()


def _clean_parts(canonical: str) -> list[str] | None:
    if not canonical or "\\" in canonical or canonical.startswith("/"):
        return None
    parts = canonical.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return None
    return parts


def to_external(path: Path, world: World) -> str:
    absolute = _abspath(path)
    text = str(absolute)
    if world == World.WINDOWS:
        drive, rest = os.path.splitdrive(text)
        if drive:
            letter = drive[0].lower()
            tail = rest.replace("\\", "/").lstrip("/")
            return "external/" + letter + ("/" + tail if tail else "")
        if text.startswith("\\\\"):
            unc = text[2:].replace("\\", "/").strip("/")
            return "external/unc/" + unc
    tail = text.replace("\\", "/").lstrip("/")
    return "external/" + tail if tail else "external"


def to_canonical(path: Path, identity: Identity) -> str:
    path = Path(path)
    specials: list[tuple[int, str, str]] = []
    for label, root in (("config", identity.appdata), ("local", identity.localappdata)):
        rel = relative_if_inside(path, root)
        if rel is not None:
            specials.append((len(_abspath(root).parts), label, rel))
    if specials:
        _, label, rel = max(specials, key=lambda item: item[0])
        return label if not rel else f"{label}/{rel}"
    rel_home = relative_if_inside(path, identity.home)
    if rel_home is not None:
        if not rel_home:
            return "home"
        parts = rel_home.split("/")
        known = _KNOWN_BY_NAME.get(parts[0].casefold())
        if known:
            rest = "/".join(parts[1:])
            return known if not rest else f"{known}/{rest}"
        return f"home/{rel_home}"
    return to_external(path, identity.world)


def preferred_folder_name(home: Path, names: tuple[str, ...]) -> str:
    text = str(home)
    if not (_windows_syntax(text) and os.name != "nt"):
        for name in names:
            if (home / name).is_dir():
                return name
    return names[0]


def preferred_subdir(home: Path, names: tuple[str, ...]) -> Path:
    return Path(join_root(str(home), preferred_folder_name(home, names)))


def from_canonical(canonical: str, identity: Identity, *, allow_external: bool | None = None) -> str | None:
    parts = _clean_parts(canonical)
    if parts is None:
        return None
    head, rest = parts[0], parts[1:]
    if head == "config":
        return join_root(str(identity.appdata), *rest)
    if head == "local":
        return join_root(str(identity.localappdata), *rest)
    if head == "home":
        return join_root(str(identity.home), *rest)
    for canonical_name, names in KNOWN_FOLDERS:
        if head == canonical_name:
            return join_root(str(identity.home), preferred_folder_name(identity.home, names), *rest)
    if head != "external":
        return None
    if allow_external is None:
        allow_external = identity.native_external()
    if not allow_external:
        return None
    external = _external_to_path(parts[1:], identity.world)
    return None if external is None else str(external)


def _external_to_path(parts: list[str], world: World) -> Path | None:
    if not parts:
        return None
    if world == World.WINDOWS:
        if parts[0] == "unc" and len(parts) >= 3:
            return Path("\\\\" + "\\".join(parts[1:]))
        if len(parts[0]) == 1 and parts[0].isalpha():
            drive = parts[0].upper() + ":\\"
            tail = "\\".join(parts[1:])
            return Path(drive + tail) if tail else Path(drive)
        return None
    if parts[0] == "unc":
        return None
    return Path("/" + "/".join(parts))


def path_pairs(source: Identity, target: Identity) -> list[tuple[str, str]]:
    roots: list[tuple[str, str]] = [
        (str(source.appdata), str(target.appdata)),
        (str(source.localappdata), str(target.localappdata)),
        (str(source.home), str(target.home)),
    ]
    for _name, names in KNOWN_FOLDERS:
        destination = join_root(str(target.home), preferred_folder_name(target.home, names))
        for name in names:
            roots.append((join_root(str(source.home), name), destination))
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for src, dst_text in roots:
        for variant in _variants(src):
            if variant and variant not in seen:
                seen.add(variant)
                pairs.append((variant, dst_text))
    pairs.sort(key=lambda item: len(item[0]), reverse=True)
    return pairs


def _variants(text: str) -> list[str]:
    values = [text, text.replace("\\", "/"), text.replace("/", "\\")]
    unique: list[str] = []
    for value in values:
        if value and value not in unique:
            unique.append(value)
    return unique


def rewrite_text(text: str, source: Identity, target: Identity) -> str:
    updated = text
    for src, dst in path_pairs(source, target):
        if not src or src not in updated:
            continue
        pattern = re.escape(src) + r"(?:[/\\][^\s\"']*)?"
        separator = "\\" if _windows_syntax(dst) else "/"

        def replace(match: re.Match, destination: str = dst, sep: str = separator, origin: str = src) -> str:
            extra = match.group(0)[len(origin) :]
            return destination + extra.replace("\\", sep).replace("/", sep)

        updated = re.sub(pattern, replace, updated)
    return updated


def looks_like_foreign_path(raw: str) -> bool:
    if not raw:
        return False
    if os.name == "nt":
        return raw.startswith("/") and len(raw) > 1 and not raw.startswith("//")
    return len(raw) >= 3 and raw[0].isalpha() and raw[1] == ":" and raw[2] in "\\/"
