"""Gemeinsamer Sicherungsspeicher für Linux und Windows."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from cpcm.paths import Identity, from_canonical, rewrite_text, to_canonical
from cpcm.selection import Selection, SelectionItem, local_path_for

TEXT_SUFFIXES = {
    ".txt", ".json", ".ini", ".conf", ".cfg", ".xml", ".yml", ".yaml", ".toml",
    ".md", ".css", ".js", ".py", ".sh", ".ps1", ".bat", ".cmd", ".reg",
    ".desktop", ".service", ".bashrc", ".profile", ".zshrc", ".gitconfig",
    ".vimrc", ".npmrc",
}
MAX_TEXT_REWRITE = 2 * 1024 * 1024


@dataclass
class Entry:
    canonical: str
    kind: str
    source_path: str
    payload: str = ""
    sha256: str = ""
    size: int = 0
    mode: int = 0o644
    mtime: float = 0.0
    link_target: str = ""

    def to_json(self) -> dict:
        return {
            "canonical": self.canonical,
            "kind": self.kind,
            "source_path": self.source_path,
            "payload": self.payload,
            "sha256": self.sha256,
            "size": self.size,
            "mode": self.mode,
            "mtime": self.mtime,
            "link_target": self.link_target,
        }

    @classmethod
    def from_json(cls, raw: dict) -> "Entry":
        return cls(
            canonical=str(raw["canonical"]),
            kind=str(raw["kind"]),
            source_path=str(raw.get("source_path") or ""),
            payload=str(raw.get("payload") or ""),
            sha256=str(raw.get("sha256") or ""),
            size=int(raw.get("size") or 0),
            mode=int(raw.get("mode") or 0o644),
            mtime=float(raw.get("mtime") or 0),
            link_target=str(raw.get("link_target") or ""),
        )


@dataclass
class Snapshot:
    id: str
    created: str
    source_world: str
    source_user: str
    source_home: str
    entries: list[Entry] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "version": 1,
            "id": self.id,
            "created": self.created,
            "source_world": self.source_world,
            "source_user": self.source_user,
            "source_home": self.source_home,
            "entries": [entry.to_json() for entry in self.entries],
            "skipped": self.skipped,
        }

    @classmethod
    def from_json(cls, raw: dict) -> "Snapshot":
        return cls(
            id=str(raw["id"]),
            created=str(raw["created"]),
            source_world=str(raw.get("source_world") or ""),
            source_user=str(raw.get("source_user") or ""),
            source_home=str(raw.get("source_home") or ""),
            entries=[Entry.from_json(item) for item in raw.get("entries") or []],
            skipped=list(raw.get("skipped") or []),
        )


def snapshots_root(vault: Path) -> Path:
    return vault / "snapshots"


def _reject_id(snapshot_id: str) -> None:
    if not snapshot_id or snapshot_id in (".", "..") or "/" in snapshot_id or "\\" in snapshot_id:
        raise ValueError("Ungültige Sicherungs-ID")


def snapshot_dir(vault: Path, snapshot_id: str) -> Path:
    _reject_id(snapshot_id)
    return snapshots_root(vault) / snapshot_id


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_payload(root: Path, relative: str) -> Path:
    if not relative or relative.startswith(("/", "\\")) or "\\" in relative:
        raise ValueError(f"Unsicherer Speicherpfad: {relative}")
    parts = Path(relative).parts
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"Unsicherer Speicherpfad: {relative}")
    target = root.joinpath(*parts)
    resolved_root = root.resolve()
    resolved = target.resolve() if target.exists() else Path(os.path.abspath(target))
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"Speicherpfad verlässt den Vault: {relative}") from exc
    return target


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def _mode_of(path: Path) -> int:
    try:
        return path.lstat().st_mode & 0o777
    except OSError:
        return 0o644


def _new_id(vault: Path) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = stamp
    index = 2
    while snapshot_dir(vault, candidate).exists():
        candidate = f"{stamp}-{index}"
        index += 1
    return candidate


def _payload_parts_ok(canonical: str) -> bool:
    if not canonical or "\\" in canonical or canonical.startswith("/"):
        return False
    return all(part not in ("", ".", "..") for part in canonical.split("/"))


def to_canonical_safe(path: Path, host: Identity) -> str | None:
    canonical = to_canonical(path, host)
    return canonical if _payload_parts_ok(canonical) else None


def create_snapshot(vault: Path, selection: Selection, host: Identity) -> Snapshot:
    if not selection.items:
        raise ValueError("Keine Dateien oder Verzeichnisse ausgewählt")
    vault.mkdir(parents=True, exist_ok=True)
    snap_id = _new_id(vault)
    root = snapshot_dir(vault, snap_id)
    payload_root = root / "payload"
    payload_root.mkdir(parents=True)
    snapshot = Snapshot(
        id=snap_id,
        created=datetime.now().isoformat(timespec="seconds"),
        source_world=host.world.value,
        source_user=host.user,
        source_home=str(host.home),
    )
    seen: dict[str, Entry] = {}
    for item in selection.items:
        _collect_item(item, host, vault, payload_root, seen, snapshot.skipped)
    snapshot.entries = list(seen.values())
    (root / "manifest.json").write_text(
        json.dumps(snapshot.to_json(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return snapshot


def _collect_item(item, host, vault, payload_root, seen, skipped) -> None:
    local = local_path_for(item, host)
    if local is None:
        skipped.append({"canonical": item.canonical, "reason": "kein lokaler Pfad"})
        return
    if not local.exists() and not local.is_symlink():
        skipped.append({"path": str(local), "reason": "nicht vorhanden"})
        return
    if _inside(local, vault):
        skipped.append({"path": str(local), "reason": "liegt im Vault"})
        return
    if item.kind == "file" or local.is_file() or local.is_symlink():
        _store_path(local, host, payload_root, vault, seen, skipped)
        return
    if not local.is_dir():
        skipped.append({"path": str(local), "reason": "weder Datei noch Verzeichnis"})
        return
    _store_dir_entry(local, host, seen)
    for current, dirnames, filenames in os.walk(local, followlinks=False):
        current_path = Path(current)
        kept: list[str] = []
        for name in dirnames:
            child = current_path / name
            if _inside(child, vault):
                continue
            if child.is_symlink():
                _store_path(child, host, payload_root, vault, seen, skipped)
                continue
            kept.append(name)
            _store_dir_entry(child, host, seen)
        dirnames[:] = kept
        for name in filenames:
            child = current_path / name
            if not _inside(child, vault):
                _store_path(child, host, payload_root, vault, seen, skipped)


def _store_dir_entry(path: Path, host: Identity, seen: dict[str, Entry]) -> None:
    canonical = to_canonical_safe(path, host)
    if canonical is None or canonical in seen:
        return
    seen[canonical] = Entry(
        canonical=canonical,
        kind="dir",
        source_path=str(path),
        mode=_mode_of(path),
        mtime=path.lstat().st_mtime if path.exists() else 0,
    )


def _store_path(path, host, payload_root, vault, seen, skipped) -> None:
    if _inside(path, vault):
        skipped.append({"path": str(path), "reason": "liegt im Vault"})
        return
    canonical = to_canonical_safe(path, host)
    if canonical is None:
        skipped.append({"path": str(path), "reason": "Pfad nicht abbildbar"})
        return
    if path.is_symlink():
        seen[canonical] = Entry(
            canonical=canonical,
            kind="symlink",
            source_path=str(path),
            link_target=os.readlink(path),
            mode=_mode_of(path),
            mtime=path.lstat().st_mtime,
        )
        return
    if not path.is_file():
        skipped.append({"path": str(path), "reason": "übersprungen"})
        return
    payload = _safe_payload(payload_root, canonical)
    payload.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, payload)
    seen[canonical] = Entry(
        canonical=canonical,
        kind="file",
        source_path=str(path),
        payload=canonical,
        sha256=_sha256(payload),
        size=payload.stat().st_size,
        mode=_mode_of(path),
        mtime=path.stat().st_mtime,
    )


def list_snapshots(vault: Path) -> list[dict]:
    root = snapshots_root(vault)
    if not root.is_dir():
        return []
    found = []
    for child in root.iterdir():
        manifest = child / "manifest.json"
        if not manifest.is_file():
            continue
        try:
            raw = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        files = [entry for entry in raw.get("entries") or [] if entry.get("kind") == "file"]
        found.append(
            {
                "id": raw.get("id") or child.name,
                "created": raw.get("created"),
                "source_world": raw.get("source_world"),
                "source_user": raw.get("source_user"),
                "files": len(files),
                "entries": len(raw.get("entries") or []),
            }
        )
    found.sort(key=lambda item: item.get("created") or "", reverse=True)
    return found


def load_snapshot(vault: Path, snapshot_id: str) -> Snapshot:
    manifest = snapshot_dir(vault, snapshot_id) / "manifest.json"
    if not manifest.is_file():
        raise FileNotFoundError(f"Sicherung nicht gefunden: {snapshot_id}")
    return Snapshot.from_json(json.loads(manifest.read_text(encoding="utf-8")))


def _is_text_candidate(path: Path, size: int) -> bool:
    if size > MAX_TEXT_REWRITE:
        return False
    return path.suffix.lower() in TEXT_SUFFIXES or path.name.startswith(".") or (path.suffix == "" and size <= 256 * 1024)


@dataclass
class RestoreReport:
    restored: list[str] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    rewritten: list[str] = field(default_factory=list)
    pre_restore: str = ""

    def to_json(self) -> dict:
        return {
            "restored": self.restored,
            "skipped": self.skipped,
            "conflicts": self.conflicts,
            "rewritten": self.rewritten,
            "pre_restore": self.pre_restore,
        }


def restore_snapshot(
    vault: Path,
    snapshot_id: str,
    target: Identity,
    *,
    source: Identity | None = None,
    overwrite: bool = False,
    translate_paths: bool = False,
    destination: Path | None = None,
    allow_external: bool | None = None,
) -> RestoreReport:
    snapshot = load_snapshot(vault, snapshot_id)
    payload_root = snapshot_dir(vault, snapshot_id) / "payload"
    report = RestoreReport()
    pre_holder: dict = {}
    dirs = [entry for entry in snapshot.entries if entry.kind == "dir"]
    files = [entry for entry in snapshot.entries if entry.kind == "file"]
    links = [entry for entry in snapshot.entries if entry.kind == "symlink"]
    for entry in sorted(dirs, key=lambda item: item.canonical.count("/")):
        try:
            dest = _destination_for(entry.canonical, target, destination, allow_external)
        except ValueError as exc:
            report.skipped.append({"canonical": entry.canonical, "reason": str(exc)})
            continue
        if dest is None:
            report.skipped.append({"canonical": entry.canonical, "reason": "keine Abbildung in dieser Welt"})
            continue
        dest.mkdir(parents=True, exist_ok=True)
        report.restored.append(str(dest))
    for entry in files:
        try:
            _restore_file(
                entry, payload_root, target, source, destination, allow_external,
                overwrite, translate_paths, vault, report, pre_holder,
            )
        except ValueError as exc:
            report.skipped.append({"canonical": entry.canonical, "reason": str(exc)})
    for entry in links:
        try:
            _restore_link(entry, target, destination, allow_external, overwrite, vault, report, pre_holder)
        except ValueError as exc:
            report.skipped.append({"canonical": entry.canonical, "reason": str(exc)})
    if pre_holder.get("path") is not None:
        report.pre_restore = str(pre_holder["path"])
    return report


def _destination_for(canonical, target, destination, allow_external) -> Path | None:
    if destination is not None:
        dest_root = Path(destination)
        dest_root.mkdir(parents=True, exist_ok=True)
        return _safe_payload(dest_root, canonical)
    mapped = from_canonical(canonical, target, allow_external=allow_external)
    return None if mapped is None else Path(mapped)


def _ensure_pre_restore(vault: Path, holder: dict) -> Path:
    if "path" not in holder:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        root = vault / "pre-restore" / stamp
        index = 2
        while root.exists():
            root = vault / "pre-restore" / f"{stamp}-{index}"
            index += 1
        root.mkdir(parents=True)
        holder["path"] = root
    return holder["path"]


def _restore_file(entry, payload_root, target, source, destination, allow_external, overwrite, translate_paths, vault, report, pre_holder) -> None:
    dest = _destination_for(entry.canonical, target, destination, allow_external)
    if dest is None:
        report.skipped.append({"canonical": entry.canonical, "reason": "keine Abbildung in dieser Welt"})
        return
    try:
        payload = _safe_payload(payload_root, entry.payload or entry.canonical)
    except ValueError as exc:
        report.skipped.append({"canonical": entry.canonical, "reason": str(exc)})
        return
    if not payload.is_file():
        report.skipped.append({"canonical": entry.canonical, "reason": "Nutzlast fehlt"})
        return
    digest = _sha256(payload)
    if entry.sha256 and digest != entry.sha256:
        report.skipped.append({"canonical": entry.canonical, "reason": "Prüfsumme stimmt nicht"})
        return
    data = payload.read_bytes()
    rewritten = False
    if translate_paths and source is not None and _is_text_candidate(payload, len(data)):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = ""
        if text and "\x00" not in text:
            updated = rewrite_text(text, source, target)
            if updated != text:
                data = updated.encode("utf-8")
                rewritten = True
    if dest.exists() or dest.is_symlink():
        try:
            same = dest.is_file() and not dest.is_symlink() and hashlib.sha256(dest.read_bytes()).hexdigest() == hashlib.sha256(data).hexdigest()
        except OSError:
            same = False
        if same:
            report.skipped.append({"canonical": entry.canonical, "reason": "bereits identisch"})
            return
        if not overwrite:
            report.conflicts.append(str(dest))
            return
        if dest.is_dir() and not dest.is_symlink():
            report.conflicts.append(str(dest))
            return
        backup_to = _safe_payload(_ensure_pre_restore(vault, pre_holder), entry.canonical)
        backup_to.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_symlink():
            backup_to.write_text(os.readlink(dest), encoding="utf-8")
            dest.unlink()
        elif dest.is_file():
            shutil.copyfile(dest, backup_to)
            dest.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    try:
        os.chmod(dest, entry.mode & 0o777)
    except OSError:
        pass
    report.restored.append(str(dest))
    if rewritten:
        report.rewritten.append(str(dest))


def _restore_link(entry, target, destination, allow_external, overwrite, vault, report, pre_holder) -> None:
    dest = _destination_for(entry.canonical, target, destination, allow_external)
    if dest is None:
        report.skipped.append({"canonical": entry.canonical, "reason": "keine Abbildung in dieser Welt"})
        return
    if dest.exists() or dest.is_symlink():
        if not overwrite:
            report.conflicts.append(str(dest))
            return
        if dest.is_dir() and not dest.is_symlink():
            report.conflicts.append(str(dest))
            return
        backup_to = _safe_payload(_ensure_pre_restore(vault, pre_holder), entry.canonical)
        backup_to.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_symlink():
            backup_to.write_text(os.readlink(dest), encoding="utf-8")
        elif dest.is_file():
            shutil.copyfile(dest, backup_to)
        dest.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        dest.symlink_to(entry.link_target)
    except OSError as exc:
        report.skipped.append({"canonical": entry.canonical, "reason": str(exc)})
        return
    report.restored.append(str(dest))


def export_snapshot(vault: Path, snapshot_id: str, dest_zip: Path) -> Path:
    root = snapshot_dir(vault, snapshot_id)
    if not (root / "manifest.json").is_file():
        raise FileNotFoundError(snapshot_id)
    dest_zip = Path(dest_zip)
    dest_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for current, _dirs, files in os.walk(root):
            for name in files:
                full = Path(current) / name
                archive.write(full, full.relative_to(root).as_posix())
    return dest_zip


def import_snapshot(vault: Path, archive_path: Path) -> str:
    vault.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if "manifest.json" not in names:
            raise ValueError("Archiv enthält kein manifest.json")
        for name in names:
            if name.startswith("/") or "\\" in name or ".." in Path(name).parts:
                raise ValueError(f"Unsicherer Archiveintrag: {name}")
        raw = json.loads(archive.read("manifest.json").decode("utf-8"))
        snap_id = str(raw.get("id") or "")
        _reject_id(snap_id)
        target = snapshot_dir(vault, snap_id)
        if target.exists():
            raise FileExistsError(f"Sicherung existiert bereits: {snap_id}")
        target.mkdir(parents=True)
        for name in names:
            if archive.getinfo(name).is_dir():
                continue
            dest = target / "manifest.json" if name == "manifest.json" else _safe_payload(target, name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(archive.read(name))
    return snap_id


def delete_snapshot(vault: Path, snapshot_id: str) -> None:
    root = snapshot_dir(vault, snapshot_id)
    if not root.is_dir():
        raise FileNotFoundError(snapshot_id)
    shutil.rmtree(root)
