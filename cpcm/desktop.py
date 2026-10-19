"""Aktionen des Windows-Programms. Kein Fenster, kein Browser."""

from __future__ import annotations

import json
from pathlib import Path

from cpcm import AUTHOR_EMAIL, AUTHOR_NAME, __version__
from cpcm.backup import create_snapshot, delete_snapshot, export_snapshot, import_snapshot, list_snapshots, restore_snapshot
from cpcm.catalog import MANAGERS, detect_installed, plan
from cpcm.diagnose import analyze, script_for
from cpcm.filesystems import repair_plan
from cpcm.hardware import load_profiles, probe, set_active
from cpcm.paths import World, host_identity
from cpcm.personal import AREAS, apply_wallpaper, discover
from cpcm.selection import add_path, load_selection, remove_item, save_selection
from cpcm.server import browse
from cpcm.settings import counterpart_identity, host_home_identity, install_root, load_settings, save_settings, vault_dir
from cpcm.shortcuts import GESTURE_DEFAULTS, gesture_artifacts, translate_shortcut
from cpcm.themes import theme_artifacts
from cpcm.translate import identities_from_request, translate_config


def _text(value) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, indent=2, ensure_ascii=False)


class Session:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or install_root()).resolve()

    def settings(self) -> dict:
        return load_settings(self.root)

    def vault(self) -> Path:
        return vault_dir(self.settings(), self.root)

    def identities(self):
        data = self.settings()
        host = host_home_identity(data, host_identity())
        return host, counterpart_identity(data, host)

    def status_line(self) -> str:
        host, _other = self.identities()
        return f"Vault: {self.vault()}    {AUTHOR_NAME} · {AUTHOR_EMAIL}    {host.world.value}"

    def title(self) -> str:
        return f"CPCM {__version__} – {AUTHOR_NAME}"

    def browse(self, path_text: str) -> dict:
        return browse(path_text)

    def add(self, path_text: str) -> str:
        host, other = self.identities()
        selection = load_selection(self.vault())
        item = add_path(selection, Path(path_text), host, other)
        save_selection(self.vault(), selection)
        windows = item.paths.get("windows", "")
        linux = item.paths.get("linux", "")
        return f"Aufgenommen: {item.label}\nWindows: {windows}\nLinux: {linux}"

    def remove_selected(self, item_id: str) -> str:
        selection = load_selection(self.vault())
        remove_item(selection, item_id)
        save_selection(self.vault(), selection)
        return "Eintrag entfernt."

    def selection_rows(self) -> list[dict]:
        return [item.to_json() for item in load_selection(self.vault()).items]

    def areas(self) -> tuple[tuple[str, str], ...]:
        return AREAS

    def prepare_personal(self, keys: list[str]) -> str:
        host, _other = self.identities()
        found, missing = discover(host, keys)
        if not found:
            raise ValueError("Keiner der gewählten Bereiche ist auf diesem Rechner vorhanden.")
        lines = [self.add(str(path)) for path in found]
        if missing:
            lines.append("Nicht vorhanden: " + ", ".join(missing))
        return "\n".join(lines)

    def backup(self, progress=None) -> str:
        host, _other = self.identities()
        snapshot = create_snapshot(self.vault(), load_selection(self.vault()), host, progress=progress)
        files = sum(1 for entry in snapshot.entries if entry.kind == "file")
        skipped = len(snapshot.skipped)
        return f"Sicherung {snapshot.id}\nDateien: {files}\nÜbersprungen: {skipped}"

    def apply_saved_wallpaper(self) -> str:
        from cpcm.backup import snapshot_dir
        rows = self.snapshots()
        if not rows:
            raise ValueError("Keine Sicherung vorhanden.")
        image = snapshot_dir(self.vault(), rows[0]["id"]) / "payload" / "appearance" / "wallpaper"
        if not image.is_file():
            raise ValueError("Die letzte Sicherung enthält keinen Hintergrund.")
        return apply_wallpaper(image)

    def snapshots(self) -> list[dict]:
        return list_snapshots(self.vault())

    def restore(self, snapshot_id: str, *, overwrite: bool, translate_paths: bool, destination: str) -> str:
        host, _other = self.identities()
        dest = Path(destination) if destination.strip() else None
        report = restore_snapshot(
            self.vault(),
            snapshot_id,
            host,
            source=host,
            overwrite=overwrite,
            translate_paths=translate_paths,
            destination=dest,
        )
        return _text(report.to_json())

    def export(self, snapshot_id: str, dest: str) -> str:
        path = export_snapshot(self.vault(), snapshot_id, Path(dest))
        return f"Export: {path}"

    def import_archive(self, path: str) -> str:
        snapshot_id = import_snapshot(self.vault(), Path(path))
        return f"Importiert: {snapshot_id}"

    def delete(self, snapshot_id: str) -> str:
        delete_snapshot(self.vault(), snapshot_id)
        return f"Gelöscht: {snapshot_id}"

    def save_worlds(self, linux_home: str, windows_home: str, vault_path: str) -> str:
        data = self.settings()
        data["homes"]["linux"] = linux_home.strip()
        data["homes"]["windows"] = windows_home.strip()
        vault_text = vault_path.strip()
        data["vault"] = vault_text or None
        save_settings(data, self.root)
        return "Welten gespeichert.\n" + self.world_lines()

    def world_lines(self) -> str:
        data = self.settings()
        rows = [
            f"Linux-Home: {data['homes'].get('linux', '')}",
            f"Windows-Home: {data['homes'].get('windows', '')}",
            f"Vault: {self.vault()}",
            "",
        ]
        for item in load_selection(self.vault()).items:
            rows.append(f"{item.label}: Windows {item.paths.get('windows', '–')} | Linux {item.paths.get('linux', '–')}")
        return "\n".join(rows)

    def detect_apps(self) -> str:
        found = detect_installed()
        return "\n".join(found) if found else "Keine bekannten Programme gefunden."

    def plan_apps(self, names_text: str, manager: str) -> str:
        host, _other = self.identities()
        target = World.LINUX if host.world == World.WINDOWS else World.WINDOWS
        names = [line.strip() for line in names_text.splitlines() if line.strip()]
        return _text(plan(names, target, manager))

    def managers(self) -> tuple[str, ...]:
        host, _other = self.identities()
        return MANAGERS[host.world]

    def translate(self, text: str, source_name: str, target_name: str) -> str:
        host, _other = self.identities()
        source, target = identities_from_request({"source": source_name, "target": target_name, "homes": self.settings()["homes"]}, host)
        return translate_config(text, source, target)["text"]

    def shortcut(self, text: str) -> str:
        return "\n".join([
            f"Windows: {translate_shortcut(text, World.WINDOWS)}",
            f"Linux: {translate_shortcut(text, World.LINUX)}",
        ])

    def gestures(self) -> str:
        host, _other = self.identities()
        return _text(gesture_artifacts(dict(GESTURE_DEFAULTS), host.world))

    def theme(self) -> str:
        host, _other = self.identities()
        desktop = "windows" if host.world == World.WINDOWS else "gnome"
        return _text(theme_artifacts({"mode": "dark", "accent": "#0078D4"}, host.world, desktop))

    def diagnose(self, text: str) -> str:
        host, _other = self.identities()
        findings = analyze(text)
        lines = []
        for finding in findings:
            lines.append(f"{finding.get('title', '')}: {finding.get('plain', '')}")
            script = script_for(finding, host.world)
            if script:
                lines.append(script)
            lines.append("")
        return "\n".join(lines).strip() or "Keine bekannte Meldung."

    def filesystem(self, world_name: str, filesystem: str, device: str) -> str:
        return _text(repair_plan(world_name, filesystem, device))

    def hardware(self) -> str:
        profiles = load_profiles(self.vault())
        return _text({"probe": probe(), "profile": profiles})

    def activate_profile(self, name: str) -> str:
        return _text(set_active(self.vault(), name))

    def help_text(self) -> str:
        path = self.root / "docs" / "HILFE.txt"
        if path.is_file():
            return path.read_text(encoding="utf-8")
        return "Hilfe liegt unter docs\\HILFE.txt."

    def manual_path(self) -> Path:
        return self.root / "docs" / "BEDIENUNGSANLEITUNG.rtf"

    def features_path(self) -> Path:
        return self.root / "docs" / "FEATURE-LISTE.rtf"
