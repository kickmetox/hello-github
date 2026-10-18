"""Fachlogik. Die Oberfläche ruft nur diese Schicht auf."""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from spheredrive.commands import (
    APPMODEL_UNLOCK,
    BITBUCKET,
    BITBUCKET_WOW,
    DOS_DEVICES,
    FOLDER_DESC,
    FOLDER_DESC_WOW,
    POLICIES_SYSTEM,
    RUN_KEY,
    build_unc,
    del_command,
    dos_device_value,
    drive_icon_key,
    icon_registry_value,
    mklink_command,
    mountpoints2_key,
    mountvol_assign,
    mountvol_list,
    mountvol_remove,
    net_share_create,
    parent_dir,
    net_share_delete,
    net_share_list,
    net_use_connect,
    net_use_delete,
    net_use_list,
    network_key,
    norm_path,
    normalize_letter,
    normalize_mount_target,
    normalize_volume_id,
    ps_list_drives_script,
    ps_list_volumes_script,
    ps_name_ok,
    ps_new_drive_script,
    ps_remove_drive_script,
    ps_scan_reparse_script,
    render_profile_block,
    replace_marked_block,
    rmdir_command,
    share_name_ok,
    subst_create,
    subst_delete,
    subst_list,
)
from spheredrive.host import PreviewHost, RunResult, WindowsHost, make_host
from spheredrive.i18n import t
from spheredrive.models import (
    DriveCard,
    LinkEntry,
    LinkSpec,
    MountSpec,
    NetEntry,
    NetSpec,
    OpResult,
    PsEntry,
    PsSpec,
    ShareEntry,
    ShareSpec,
    Snapshot,
    SubstEntry,
    SubstSpec,
    VolumeEntry,
)
from spheredrive.parsers import as_int, parse_json_list, parse_mountvol, parse_net_share, parse_net_use, parse_subst
from spheredrive.paths import default_store_path, format_launch, restore_launch
from spheredrive.store import Store

log = logging.getLogger("spheredrive")

DIR_KINDS = {"junction", "symlink_dir"}
FILE_KINDS = {"symlink_file", "hardlink"}
AUTOSTART_NAME = "SphereDrive"

_KIND_LABEL = {
    "fixed": t("Lokaler Datenträger"),
    "removable": t("Wechselmedium"),
    "remote": t("Netzlaufwerk"),
    "cdrom": t("CD-Laufwerk"),
    "ramdisk": t("RAM-Datenträger"),
    "subst": t("Virtuelles Laufwerk"),
    "unknown": t("Laufwerk"),
    "disconnected": t("Nicht verbunden"),
}

_KIND_FALLBACK = {
    "fixed": t("Lokaler Datenträger"),
    "removable": t("USB-Laufwerk"),
    "remote": t("Netzlaufwerk"),
    "cdrom": t("CD-Laufwerk"),
    "ramdisk": t("RAM-Datenträger"),
    "subst": t("Subst"),
    "unknown": t("Laufwerk"),
    "disconnected": t("Laufwerk"),
}


class SphereService:
    def __init__(self, host: PreviewHost | WindowsHost | None = None, store_path: Path | None = None) -> None:
        self.host = host if host is not None else make_host()
        self.store = Store(Path(store_path) if store_path is not None else default_store_path())
        self.synchronous = bool(getattr(self.host, "preview", False))

    # --- Momentaufnahme -------------------------------------------------

    def snapshot(self) -> Snapshot:
        return Snapshot(
            subst=self._collect_subst(),
            net=self._collect_net(),
            shares=self._collect_shares(),
            links=self._collect_links(),
            psdrives=self._collect_ps(),
            volumes=self.list_volumes(),
            admin=self.host.is_admin(),
            linked_connections=self.linked_connections_enabled(),
            autostart=self.autostart_enabled(),
            elevated_task=self.host.task_exists(),
            preview=bool(self.host.preview),
        )

    def restore_persistent(self) -> list[OpResult]:
        """Wird beim Anmelden ohne Oberfläche ausgeführt."""
        results: list[OpResult] = []
        live = {item.letter: item.path for item in parse_subst(self.host.run(subst_list()).stdout)}
        for item in self.store.data["subst"]:
            if not item.get("persistent"):
                continue
            letter = item["letter"]
            path = item["path"]
            if letter in live and norm_path(live[letter]) == norm_path(path):
                results.append(OpResult(True, f"{letter}: ist bereits verbunden."))
                continue
            if letter in self.host.logical_drives() and letter not in live:
                results.append(OpResult(False, f"{letter}: ist belegt und wurde nicht ersetzt."))
                continue
            if not self.host.path_isdir(path):
                results.append(OpResult(False, t("Ordner für {letter}: fehlt: {path}", letter=letter, path=path)))
                continue
            result = self.host.run(subst_create(letter, path))
            results.append(self._from_run(result, t("{letter}: wurde wiederhergestellt.", letter=letter), t("subst fehlgeschlagen")))
        connected = {item.letter for item in parse_net_use(self.host.run(net_use_list()).stdout)}
        for item in self.store.data["net"]:
            if not item.get("persistent"):
                continue
            letter = item["letter"]
            if letter in connected:
                results.append(OpResult(True, f"{letter}: (Netz) ist bereits verbunden."))
                continue
            result = self.host.run(
                net_use_connect(letter, item["remote"], item.get("user") or "", "", True)
            )
            results.append(self._from_run(result, t("{letter}: wurde erneut verbunden.", letter=letter), t("net use fehlgeschlagen")))
        for item in self.store.data["psdrives"]:
            if not item.get("profile"):
                continue
            # Profil-Laufwerke entstehen in PowerShell-Sitzungen, nicht in diesem Prozess.
        return results or [OpResult(True, t("Keine dauerhaften Zuordnungen gespeichert."))]

    # --- Subst ----------------------------------------------------------

    def apply_subst(self, spec: SubstSpec, *, replace: bool = False) -> OpResult:
        letter = normalize_letter(spec.letter)
        path = (spec.path or "").strip().strip('"')
        if letter is None:
            return OpResult(False, t("Der Laufwerksbuchstabe ist ungültig."))
        if not path:
            return OpResult(False, t("Der Ordner fehlt."))
        warnings: list[str] = []
        live = {item.letter: item.path for item in parse_subst(self.host.run(subst_list()).stdout)}
        if letter in live:
            if norm_path(live[letter]) != norm_path(path):
                if not replace:
                    return OpResult(
                        False,
                        t("{letter}: ist bereits mit {path} verbunden.", letter=letter, path=live[letter]),
                        code="conflict",
                    )
                removed = self.remove_subst(letter)
                if not removed.ok:
                    return removed
                live.pop(letter, None)
        elif letter in self.host.logical_drives():
            return OpResult(False, t("{letter}: wird bereits von einem anderen Laufwerk verwendet.", letter=letter), code="occupied")
        if letter not in live:
            if not self.host.path_isdir(path):
                return OpResult(False, t("Der Zielordner existiert nicht."))
            created = self.host.run(subst_create(letter, path))
            if not created.ok:
                return self._from_run(created, "", t("subst konnte das Laufwerk nicht verbinden."))
        if spec.persistent:
            warning = self._write_dos_device(letter, path)
            if warning:
                warnings.append(warning)
            if self.store.data["settings"].get("autostart", True):
                self.write_autostart(True)
            else:
                warnings.append(
                    t("Autostart ist aus. Ohne DOS-Devices-Eintrag verschwindet das Laufwerk beim Neustart.")
                )
        else:
            self._delete_dos_device(letter)
        self._write_appearance(letter, spec.label, spec.icon, warnings)
        guid = self._existing_subst(letter).get("recycle_guid", "")
        if spec.recycle:
            guid, recycle_warning = self._enable_recycle(letter, spec.label or f"{letter}_Drive", spec.recycle_mb, guid)
            if recycle_warning:
                warnings.append(recycle_warning)
        elif guid:
            warning = self._disable_recycle(letter, guid)
            if warning:
                warnings.append(warning)
            guid = ""
        if spec.uac:
            warning = self._enable_uac_mapping()
            if warning:
                warnings.append(warning)
        self._upsert(
            "subst",
            "letter",
            {
                "letter": letter,
                "path": path,
                "label": spec.label.strip(),
                "icon": spec.icon.strip(),
                "persistent": bool(spec.persistent),
                "uac": bool(spec.uac),
                "recycle": bool(spec.recycle) and bool(guid),
                "recycle_guid": guid,
                "recycle_mb": int(spec.recycle_mb or 10240),
            },
        )
        self.host.notify_shell()
        message = t("{letter}: ist mit {path} verbunden.", letter=letter, path=path)
        return OpResult(True, message, warnings)

    def remove_subst(self, letter: str) -> OpResult:
        normalized = normalize_letter(letter)
        if normalized is None:
            return OpResult(False, t("Der Laufwerksbuchstabe ist ungültig."))
        warnings: list[str] = []
        stored = self._existing_subst(normalized)
        result = self.host.run(subst_delete(normalized))
        if not result.ok and "nicht verbunden" not in result.text.lower() and "invalid" not in result.text.lower():
            # Ein bereits fehlendes Laufwerk ist kein Fehler, wenn wir nur die Konfiguration lösen.
            if normalized in {item.letter for item in parse_subst(self.host.run(subst_list()).stdout)}:
                return self._from_run(result, "", t("Das Laufwerk konnte nicht getrennt werden."))
        warning = self._delete_dos_device(normalized)
        if warning:
            warnings.append(warning)
        if stored.get("recycle_guid"):
            warning = self._disable_recycle(normalized, stored["recycle_guid"])
            if warning:
                warnings.append(warning)
        self._delete_appearance(normalized)
        self._drop("subst", "letter", normalized)
        self.host.notify_shell()
        return OpResult(True, t("{letter}: wurde getrennt.", letter=normalized), warnings)

    # --- net use --------------------------------------------------------

    def connect_net(self, spec: NetSpec) -> OpResult:
        letter = normalize_letter(spec.letter)
        remote = (spec.remote or "").strip()
        if letter is None:
            return OpResult(False, t("Der Laufwerksbuchstabe ist ungültig."))
        if not remote.startswith("\\\\"):
            return OpResult(False, t("Die Freigabe muss ein UNC-Pfad sein, zum Beispiel \\\\server\\freigabe."))
        current = {item.letter: item.remote for item in parse_net_use(self.host.run(net_use_list()).stdout)}
        same = letter in current and current[letter].rstrip("\\").lower() == remote.rstrip("\\").lower()
        if letter in self.host.logical_drives() and not same:
            return OpResult(False, t("{letter}: ist bereits belegt.", letter=letter))
        if not same:
            result = self.host.run(
                net_use_connect(letter, remote, spec.user.strip(), spec.password, spec.persistent),
                input_text="Y\n",
                timeout=45,
            )
            if not result.ok:
                return self._from_run(result, "", t("net use konnte die Freigabe nicht verbinden."))
        warnings: list[str] = []
        self._write_appearance(letter, spec.label, spec.icon, warnings)
        if spec.label.strip():
            try:
                self.host.registry.set_sz("HKCU", mountpoints2_key(remote), "_LabelFromReg", spec.label.strip())
            except PermissionError:
                warnings.append(t("Die Netzwerkbezeichnung konnte nicht geschrieben werden."))
        self._upsert(
            "net",
            "letter",
            {
                "letter": letter,
                "remote": remote,
                "user": spec.user.strip(),
                "persistent": bool(spec.persistent),
                "label": spec.label.strip(),
                "icon": spec.icon.strip(),
            },
        )
        if spec.persistent and self.store.data["settings"].get("autostart", True):
            self.write_autostart(True)
        self.host.notify_shell()
        if spec.password:
            warnings.append(t("Das Kennwort wurde nicht gespeichert."))
        return OpResult(True, t("{letter}: ist mit {remote} verbunden.", letter=letter, remote=remote), warnings)

    def disconnect_net(self, letter: str) -> OpResult:
        normalized = normalize_letter(letter)
        if normalized is None:
            return OpResult(False, t("Der Laufwerksbuchstabe ist ungültig."))
        result = self.host.run(net_use_delete(normalized), input_text="Y\n", timeout=30)
        if not result.ok:
            return self._from_run(result, "", t("Die Netzwerkverbindung konnte nicht getrennt werden."))
        try:
            self.host.registry.delete_value("HKCU", network_key(normalized), "RemotePath")
        except PermissionError:
            pass
        self._drop("net", "letter", normalized)
        self._delete_appearance(normalized)
        self.host.notify_shell()
        return OpResult(True, t("{letter}: wurde getrennt.", letter=normalized))

    def create_share(self, spec: ShareSpec) -> OpResult:
        name = spec.name.strip()
        path = spec.path.strip().strip('"')
        if not share_name_ok(name):
            return OpResult(False, t("Der Freigabename ist ungültig. $ am Ende ist administrativen Freigaben vorbehalten."))
        if not self.host.path_isdir(path):
            return OpResult(False, t("Der freizugebende Ordner existiert nicht."))
        principal = spec.principal.strip() or os.environ.get("USERNAME") or os.environ.get("USER") or ""
        result = self.host.run(net_share_create(name, path, spec.permission, principal), timeout=30)
        if not result.ok:
            return self._from_run(result, "", t("Die Freigabe konnte nicht erstellt werden."))
        self._upsert("shares", "name", {"name": name, "path": path, "permission": spec.permission, "principal": principal})
        return OpResult(
            True,
            t("Freigabe {name} zeigt auf {path}.", name=name, path=path),
            [t("Der Ordner ist damit im Netzwerk erreichbar. Verbinde ihn anschließend mit net use.")],
        )

    def delete_share(self, name: str) -> OpResult:
        cleaned = name.strip()
        if not cleaned:
            return OpResult(False, t("Der Freigabename fehlt."))
        result = self.host.run(net_share_delete(cleaned), timeout=30)
        if not result.ok:
            return self._from_run(result, "", t("Die Freigabe konnte nicht entfernt werden."))
        self._drop("shares", "name", cleaned)
        return OpResult(True, t("Freigabe {cleaned} wurde entfernt. Die Dateien bleiben am Ort.", cleaned=cleaned))

    # --- mklink ---------------------------------------------------------

    def create_link(self, spec: LinkSpec) -> OpResult:
        kind = spec.kind
        link = spec.link.strip().strip('"')
        target = spec.target.strip().strip('"')
        if kind not in DIR_KINDS | FILE_KINDS:
            return OpResult(False, t("Die Verknüpfungsart ist unbekannt."))
        if not link or not target:
            return OpResult(False, t("Link-Pfad und Ziel werden beide benötigt."))
        if norm_path(link) == norm_path(target):
            return OpResult(False, t("Link und Ziel dürfen nicht identisch sein."))
        parent = parent_dir(link)
        if parent and not self.host.path_isdir(parent):
            return OpResult(False, t("Der übergeordnete Ordner des Links existiert nicht."))
        if self.host.path_occupied(link):
            return OpResult(False, t("Am Link-Pfad liegt bereits eine Datei oder ein Ordner."))
        if kind in DIR_KINDS and not self.host.path_isdir(target):
            return OpResult(False, t("Das Ziel einer Junction oder eines Ordnerlinks muss ein Ordner sein."))
        if kind in FILE_KINDS and not self.host.path_isfile(target):
            return OpResult(False, t("Das Ziel dieser Verknüpfung muss eine Datei sein."))
        result = self.host.run(mklink_command(kind, link, target))
        if not result.ok:
            warnings = []
            if kind in {"symlink_dir", "symlink_file"}:
                warnings.append(
                    t("Symbolische Links brauchen Administratorrechte oder den Windows-Entwicklermodus.")
                )
            failure = self._from_run(result, "", t("mklink ist fehlgeschlagen."))
            failure.warnings.extend(warnings)
            return failure
        self._upsert("links", "link", {"kind": kind, "link": link, "target": target})
        return OpResult(True, t("Verknüpfung angelegt: {link}", link=link))

    def remove_link(self, link: str) -> OpResult:
        path = link.strip().strip('"')
        if not path:
            return OpResult(False, t("Der Link-Pfad fehlt."))
        stored = self._find("links", "link", path)
        kind = (stored or {}).get("kind", "")
        if kind == "hardlink":
            result = self.host.run(del_command(path))
        else:
            if not self.host.is_reparse(path):
                return OpResult(
                    False,
                    t("Der Pfad ist kein symbolischer Link und keine Junction. Es wurde nichts gelöscht."),
                )
            if kind == "symlink_file" or (not kind and self.host.path_isfile(path)):
                result = self.host.run(del_command(path))
            else:
                result = self.host.run(rmdir_command(path))
        if not result.ok:
            return self._from_run(result, "", t("Die Verknüpfung konnte nicht entfernt werden."))
        self._drop_path("links", "link", path)
        return OpResult(True, t("Die Verknüpfung wurde entfernt. Das Ziel bleibt unverändert."))

    def scan_links(self, folder: str) -> OpResult:
        path = folder.strip().strip('"')
        if not self.host.path_isdir(path):
            return OpResult(False, t("Der Ordner existiert nicht."))
        result = self.host.run_powershell(ps_scan_reparse_script(path))
        if not result.ok and not result.stdout.strip():
            return self._from_run(result, "", t("Die Verknüpfungen konnten nicht gelesen werden."))
        try:
            rows = parse_json_list(result.stdout) if result.stdout.strip() else []
        except Exception:
            return OpResult(False, t("Die Antwort von PowerShell konnte nicht gelesen werden."))
        added = 0
        for row in rows:
            link = str(row.get("Link") or "")
            if not link:
                continue
            kind = _kind_from_scan(str(row.get("LinkType") or ""), as_int(row.get("Attributes")))
            target = str(row.get("Target") or "")
            if self._find("links", "link", link) is None:
                self.store.data["links"].append({"kind": kind, "link": link, "target": target})
                added += 1
        self.store.save()
        return OpResult(True, t("{count} Verknüpfungen im Ordner, {added} neu in die Liste übernommen.", count=len(rows), added=added))

    # --- New-PSDrive ----------------------------------------------------

    def create_psdrive(self, spec: PsSpec) -> OpResult:
        name = spec.name.strip()
        provider = spec.provider.strip()
        root = spec.root.strip().strip('"')
        if not ps_name_ok(name):
            return OpResult(False, t("Der Laufwerksname muss mit einem Buchstaben beginnen und darf nur Buchstaben, Ziffern und _ enthalten."))
        if not provider:
            return OpResult(False, t("Der Anbieter fehlt."))
        if provider == "FileSystem" and not root.startswith("\\\\") and not self.host.path_isdir(root):
            return OpResult(False, t("Der Stammordner existiert nicht."))
        if spec.persist_windows and not (provider == "FileSystem" and root.startswith("\\\\")):
            return OpResult(False, t("-Persist gilt nur für UNC-Pfade des FileSystem-Anbieters."))
        script = ps_new_drive_script(name, provider, root, spec.persist_windows)
        result = self.host.run_powershell(script)
        if not result.ok:
            return self._from_run(result, "", t("New-PSDrive ist fehlgeschlagen."))
        self._upsert(
            "psdrives",
            "name",
            {
                "name": name,
                "provider": provider,
                "root": root,
                "profile": bool(spec.profile),
                "persist_windows": bool(spec.persist_windows),
            },
        )
        warnings: list[str] = []
        if spec.profile:
            self._rewrite_profiles()
            warnings.append(t("Neue PowerShell-Fenster legen das Laufwerk über das Profil an."))
        else:
            self._rewrite_profiles()
            warnings.append(t("Das Laufwerk gilt nur in der PowerShell-Sitzung, die es angelegt hat."))
        return OpResult(True, t("PowerShell-Laufwerk {name}: wurde angelegt.", name=name), warnings)

    def remove_psdrive(self, name: str) -> OpResult:
        cleaned = name.strip()
        if not cleaned:
            return OpResult(False, t("Der Laufwerksname fehlt."))
        result = self.host.run_powershell(ps_remove_drive_script(cleaned))
        stored = self._find("psdrives", "name", cleaned)
        if not result.ok and stored is None:
            return self._from_run(result, "", t("Remove-PSDrive ist fehlgeschlagen."))
        self._drop("psdrives", "name", cleaned)
        self._rewrite_profiles()
        message = t("PowerShell-Laufwerk {name}: wurde entfernt.", name=cleaned)
        if not result.ok:
            return OpResult(True, message, [t("In dieser Sitzung war es nicht mehr vorhanden. Der Profileintrag ist gelöscht.")])
        return OpResult(True, message)

    def open_powershell(self, spec: PsSpec) -> OpResult:
        script = ps_new_drive_script(spec.name.strip(), spec.provider.strip(), spec.root.strip(), spec.persist_windows)
        script += "; Write-Host 'SphereDrive: Laufwerk ist in dieser Sitzung bereit.'"
        self.host.spawn(
            ["powershell.exe", "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", script]
        )
        if self.host.preview:
            return OpResult(True, t("Vorschau: Eine PowerShell-Sitzung würde jetzt offen bleiben."))
        return OpResult(True, t("PowerShell wurde geöffnet. Das Laufwerk lebt in diesem Fenster."))

    # --- Bereitstellungspunkte ------------------------------------------

    def list_volumes(self) -> list[VolumeEntry]:
        listed = parse_mountvol(self.host.run(mountvol_list()).stdout)
        meta: dict[str, dict] = {}
        info = self.host.run_powershell(ps_list_volumes_script(), timeout=40)
        if info.stdout.strip():
            try:
                for row in parse_json_list(info.stdout):
                    volume = normalize_volume_id(str(row.get("DeviceID") or ""))
                    if volume:
                        meta[volume.lower()] = row
            except Exception:
                log.warning("Volumedaten von PowerShell konnten nicht gelesen werden.", exc_info=True)
        entries: list[VolumeEntry] = []
        seen: set[str] = set()
        for volume in listed:
            seen.add(volume.id.lower())
            entries.append(_volume_from(volume.id, volume.mounts, meta.get(volume.id.lower(), {})))
        for key, row in meta.items():
            if key in seen:
                continue
            volume = normalize_volume_id(str(row.get("DeviceID") or ""))
            if volume:
                entries.append(_volume_from(volume, [], row))
        return entries

    def mount_volume(self, spec: MountSpec) -> OpResult:
        volume = normalize_volume_id(spec.volume)
        target = normalize_mount_target(spec.target)
        if volume is None:
            return OpResult(False, t("Die Volume-GUID ist ungültig."))
        if target is None:
            return OpResult(False, t("Das Bereitstellungsziel fehlt."))
        known = {item.id.lower() for item in self.list_volumes()}
        if known and volume.lower() not in known:
            return OpResult(False, t("Dieses Volume ist nicht in der Liste."))
        if target.endswith(":") and len(target) == 2:
            letter = target[0]
            if letter in self.host.logical_drives():
                return OpResult(False, t("{letter}: ist bereits belegt.", letter=letter))
        else:
            if not self.host.path_isdir(target):
                return OpResult(False, t("Der NTFS-Ordner existiert nicht."))
            if not self.host.dir_is_empty(target):
                return OpResult(False, t("Der Ordner muss leer sein. mountvol lehnt einen gefüllten Ordner ab."))
        result = self.host.run(mountvol_assign(target, volume))
        if not result.ok:
            return self._from_run(result, "", t("mountvol konnte das Volume nicht bereitstellen."))
        self._upsert("mounts", "target", {"volume": volume, "target": target})
        return OpResult(
            True,
            t("{volume} ist unter {target} bereitgestellt.", volume=volume, target=target),
            [t("Das übersteht einen Neustart. Zum Anlegen einer VHD weiter die Datenträgerverwaltung verwenden.")],
        )

    def unmount_volume(self, target: str) -> OpResult:
        normalized = normalize_mount_target(target)
        if normalized is None:
            return OpResult(False, t("Das Bereitstellungsziel fehlt."))
        result = self.host.run(mountvol_remove(normalized))
        if not result.ok:
            return self._from_run(result, "", t("Die Bereitstellung konnte nicht aufgehoben werden."))
        self._drop_mount(normalized)
        return OpResult(True, t("Die Bereitstellung {target} wurde aufgehoben. Das Volume selbst bleibt erhalten.", target=normalized))

    def open_diskmgmt(self) -> OpResult:
        self.host.open_msc("diskmgmt.msc")
        if self.host.preview:
            return OpResult(True, t("Vorschau: diskmgmt.msc würde jetzt geöffnet."))
        return OpResult(True, t("Datenträgerverwaltung wird geöffnet."))

    def open_share_manager(self) -> OpResult:
        self.host.open_msc("fsmgmt.msc")
        if self.host.preview:
            return OpResult(True, t("Vorschau: die Freigabeverwaltung würde jetzt geöffnet."))
        return OpResult(True, t("Freigabeverwaltung wird geöffnet."))

    def list_folders(self, path: str) -> list[str]:
        return self.host.list_folders(path)

    def drive_letters(self) -> list[str]:
        return sorted(self.host.logical_drives())

    def open_in_explorer(self, path: str) -> OpResult:
        target = path.strip()
        if not target:
            return OpResult(False, t("Es ist nichts zum Öffnen ausgewählt."))
        if not self.host.preview and not self.host.path_exists(target):
            return OpResult(False, t("Der Pfad kann nicht geöffnet werden: {target}", target=target))
        self.host.open_path(target)
        return OpResult(True, t("Explorer: {target}", target=target))

    def apply_appearance(self, letter: str, label: str, icon: str) -> OpResult:
        """Nur Bezeichnung und Symbol. Legt kein subst und kein net use an."""
        normalized = normalize_letter(letter)
        if normalized is None:
            return OpResult(False, t("Der Laufwerksbuchstabe ist ungültig."))
        known = normalized in self.host.logical_drives()
        known = known or self._find("subst", "letter", normalized) is not None
        known = known or self._find("net", "letter", normalized) is not None
        if not known:
            return OpResult(False, t("{letter}: ist nicht vorhanden.", letter=normalized))
        if not label.strip() and not icon.strip():
            return OpResult(False, t("Bezeichnung oder Symbol angeben."))
        warnings: list[str] = []
        self._write_appearance(normalized, label, icon, warnings)
        for section in ("subst", "net"):
            current = self._find(section, "letter", normalized)
            if current is not None:
                current["label"] = label.strip()
                current["icon"] = icon.strip()
                self.store.save()
        self.host.notify_shell()
        return OpResult(True, t("Bezeichnung und Symbol für {letter}: wurden gespeichert.", letter=normalized), warnings)

    def drive_cards(self, include_all: bool = True, snap: Snapshot | None = None) -> list[DriveCard]:
        """Laufwerkskacheln. Ohne include_all nur Subst, net use und von SphereDrive bereitgestellte Buchstaben."""
        if snap is None:
            snap = self.snapshot()
        subst = {item.letter: item for item in snap.subst}
        net = {item.letter: item for item in snap.net}
        volumes: dict[str, VolumeEntry] = {}
        for volume in snap.volumes:
            for mount in volume.mounts:
                letter = _mount_letter(mount)
                if letter and letter not in volumes:
                    volumes[letter] = volume
        managed = set()
        for item in self.store.data.get("mounts", []):
            letter = normalize_letter(str(item.get("target", "")))
            if letter:
                managed.add(letter)
        online = self.host.logical_drives()
        letters: set[str] = set(subst) | set(net) | set(managed)
        if include_all:
            letters |= set(online) | set(volumes)
        cards: list[DriveCard] = []
        for letter in sorted(letters):
            card = self._drive_card(
                letter,
                subst.get(letter),
                net.get(letter),
                volumes.get(letter),
                letter in managed,
                letter in online,
            )
            if include_all or card.origin in {"subst", "net", "mount"}:
                cards.append(card)
        return cards

    # --- Einstellungen --------------------------------------------------

    def linked_connections_enabled(self) -> bool:
        return self.host.registry.get_dword("HKLM", POLICIES_SYSTEM, "EnableLinkedConnections") == 1

    def autostart_enabled(self) -> bool:
        value = self.host.registry.get_sz("HKCU", RUN_KEY, AUTOSTART_NAME)
        return bool(value and "SphereDrive" in value)

    def developer_mode(self) -> bool:
        return self.host.registry.get_dword("HKLM", APPMODEL_UNLOCK, "AllowDevelopmentWithoutDevLicense") == 1

    def apply_settings(self, *, linked: bool, autostart: bool, elevated_task: bool) -> OpResult:
        warnings: list[str] = []
        if linked != self.linked_connections_enabled():
            try:
                if linked:
                    self.host.registry.set_dword("HKLM", POLICIES_SYSTEM, "EnableLinkedConnections", 1)
                    warnings.append(t("EnableLinkedConnections wird erst nach einem Neustart wirksam."))
                else:
                    self.host.registry.delete_value("HKLM", POLICIES_SYSTEM, "EnableLinkedConnections")
            except PermissionError:
                return OpResult(False, t("EnableLinkedConnections braucht Administratorrechte."))
        self.write_autostart(autostart)
        if elevated_task != self.host.task_exists():
            if elevated_task:
                command, arguments = restore_launch()
                created = self.host.create_logon_task(command, arguments)
                if not created.ok:
                    return self._from_run(
                        created,
                        "",
                        t("Die Anmeldungsaufgabe konnte nicht erstellt werden. Dafür sind Administratorrechte nötig."),
                    )
                warnings.append(
                    t("Die Aufgabe läuft bei der Anmeldung mit höchsten Rechten und ruft SphereDrive --restore auf.")
                )
            else:
                deleted = self.host.delete_logon_task()
                if not deleted.ok:
                    return self._from_run(deleted, "", t("Die Anmeldungsaufgabe konnte nicht gelöscht werden."))
        self.store.data["settings"]["linked_connections"] = linked
        self.store.data["settings"]["autostart"] = autostart
        self.store.data["settings"]["elevated_task"] = elevated_task
        self.store.save()
        return OpResult(True, t("Einstellungen wurden übernommen."), warnings)

    def write_autostart(self, enabled: bool) -> None:
        if enabled:
            command, arguments = restore_launch()
            self.host.registry.set_sz("HKCU", RUN_KEY, AUTOSTART_NAME, format_launch(command, arguments))
        else:
            try:
                self.host.registry.delete_value("HKCU", RUN_KEY, AUTOSTART_NAME)
            except PermissionError:
                return
        self.store.data["settings"]["autostart"] = enabled
        self.store.save()

    def elevate(self) -> OpResult:
        if self.host.is_admin():
            return OpResult(True, t("SphereDrive läuft bereits mit Administratorrechten."))
        if self.host.preview:
            self.host.elevate()
            return OpResult(True, t("Vorschau: Administratorrechte sind jetzt simuliert."))
        self.host.elevate()
        return OpResult(True, t("Die Instanz mit Administratorrechten wird gestartet."), relaunch=True)

    def refresh_shell(self) -> OpResult:
        self.host.notify_shell()
        return OpResult(True, t("Der Explorer wurde zum Neulesen von Bezeichnung und Symbol aufgefordert."))

    def restart_explorer(self) -> OpResult:
        if self.host.preview:
            return OpResult(True, t("Vorschau: Der Explorer wird hier nicht neu gestartet."))
        self.host.run(["taskkill", "/F", "/IM", "explorer.exe"], timeout=20)
        self.host.spawn(["explorer.exe"])
        return OpResult(True, t("Der Explorer wurde neu gestartet."))

    def open_config_dir(self) -> OpResult:
        self.host.open_path(str(self.store.path.parent))
        return OpResult(True, str(self.store.path))

    # --- intern ---------------------------------------------------------

    def _drive_card(
        self,
        letter: str,
        subst: SubstEntry | None,
        net: NetEntry | None,
        volume: VolumeEntry | None,
        managed_mount: bool,
        online: bool,
    ) -> DriveCard:
        reported = self.host.drive_type(letter)
        if subst is not None:
            origin = "subst"
            kind = "subst"
            label = subst.label
            icon = subst.icon
            target = subst.path
            status = subst.status
            persistent = subst.persistent
            uac = subst.uac
            recycle = subst.recycle
            recycle_mb = subst.recycle_mb
            user = ""
            real_fixed = False
            can_disconnect = True
            fallback = t(_win_basename(target) or _KIND_FALLBACK["subst"])
            capacity = 0
            free = 0
            filesystem = ""
        elif net is not None:
            origin = "net"
            kind = "remote"
            label = net.label
            icon = net.icon
            target = net.remote
            status = net.status
            persistent = net.persistent
            uac = False
            recycle = False
            recycle_mb = 10240
            user = net.user
            real_fixed = False
            can_disconnect = True
            fallback = t(_win_basename(target) or _KIND_FALLBACK["remote"])
            capacity = 0
            free = 0
            filesystem = ""
        else:
            kind = reported if reported not in {"unknown", "subst"} else "fixed"
            if not online and managed_mount:
                kind = "disconnected"
            origin = "mount" if managed_mount else "volume"
            label = self._read_label(letter) or (volume.label if volume else "")
            icon = self._read_icon(letter)
            target = f"{letter}:\\"
            status = "bereit" if online else "getrennt"
            persistent = bool(managed_mount)
            uac = False
            recycle = False
            recycle_mb = 10240
            user = ""
            real_fixed = kind in {"fixed", "removable", "cdrom", "ramdisk"} or (
                managed_mount and kind != "remote"
            )
            can_disconnect = bool(managed_mount) or kind == "remote"
            fallback = t(_KIND_FALLBACK.get(kind, "Laufwerk"))
            capacity = volume.capacity if volume else 0
            free = volume.free if volume else 0
            filesystem = volume.filesystem if volume else ""
        display = (label or "").strip() or fallback
        raw_kind = _KIND_LABEL["disconnected"] if status == "getrennt" else _KIND_LABEL.get(kind, "Laufwerk")
        kind_label = t(raw_kind)
        return DriveCard(
            letter=letter,
            title=f"{display} ({letter}:)",
            kind=kind,
            kind_label=kind_label,
            target=target,
            label=label or "",
            icon=icon or "",
            persistent=persistent,
            uac=uac,
            recycle=recycle,
            recycle_mb=recycle_mb,
            capacity=capacity,
            free=free,
            filesystem=filesystem,
            status=status,
            origin=origin,
            managed=managed_mount or origin in {"subst", "net"},
            real_fixed=real_fixed,
            can_disconnect=can_disconnect,
            user=user,
        )

    def _collect_subst(self) -> list[SubstEntry]:
        live = {item.letter: item.path for item in parse_subst(self.host.run(subst_list()).stdout)}
        configured = {item["letter"]: item for item in self.store.data["subst"]}
        letters = list(dict.fromkeys([*configured.keys(), *live.keys()]))
        entries: list[SubstEntry] = []
        for letter in letters:
            stored = configured.get(letter, {})
            path = live.get(letter) or stored.get("path", "")
            if letter in live and letter in configured:
                status = "aktiv" if norm_path(live[letter]) == norm_path(stored.get("path", live[letter])) else "Pfad weicht ab"
            elif letter in live:
                status = "nicht verwaltet"
            else:
                status = "getrennt"
            guid = stored.get("recycle_guid") or self._find_recycle_guid(letter) or ""
            entries.append(
                SubstEntry(
                    letter=letter,
                    path=path,
                    label=stored.get("label") or self._read_label(letter),
                    icon=stored.get("icon") or self._read_icon(letter),
                    persistent=bool(stored.get("persistent") or self._dos_device_present(letter)),
                    uac=bool(stored.get("uac")),
                    recycle=bool(stored.get("recycle") or guid),
                    recycle_guid=guid,
                    recycle_mb=int(stored.get("recycle_mb") or 10240),
                    status=status,
                    managed=letter in configured,
                )
            )
        return entries

    def _collect_net(self) -> list[NetEntry]:
        live = parse_net_use(self.host.run(net_use_list()).stdout)
        live_map = {item.letter: item for item in live}
        configured = {item["letter"]: item for item in self.store.data["net"]}
        letters = list(dict.fromkeys([*configured.keys(), *live_map.keys()]))
        entries: list[NetEntry] = []
        for letter in letters:
            stored = configured.get(letter, {})
            current = live_map.get(letter)
            remote = current.remote if current else stored.get("remote", "")
            persistent = bool(stored.get("persistent")) or self.host.registry.get_sz(
                "HKCU", network_key(letter), "RemotePath"
            ) not in (None, "")
            if current and letter in configured:
                status = current.status or "aktiv"
            elif current:
                status = "nicht verwaltet"
            else:
                status = "getrennt"
            entries.append(
                NetEntry(
                    letter=letter,
                    remote=remote,
                    status=status,
                    persistent=persistent,
                    user=stored.get("user", ""),
                    label=stored.get("label") or self._read_label(letter),
                    icon=stored.get("icon") or self._read_icon(letter),
                    managed=letter in configured,
                )
            )
        return entries

    def _collect_shares(self) -> list[ShareEntry]:
        result = self.host.run(net_share_list())
        return [ShareEntry(item.name, item.path, item.remark) for item in parse_net_share(result.stdout)]

    def _collect_links(self) -> list[LinkEntry]:
        entries: list[LinkEntry] = []
        for item in self.store.data["links"]:
            path = item.get("link", "")
            if self.host.preview:
                exists = self.host.is_reparse(path)
            elif item.get("kind") == "hardlink":
                exists = self.host.path_isfile(path)
            else:
                exists = self.host.is_reparse(path)
            entries.append(
                LinkEntry(
                    kind=item.get("kind", ""),
                    link=path,
                    target=item.get("target", ""),
                    status="aktiv" if exists else "fehlend",
                    managed=True,
                )
            )
        return entries

    def _collect_ps(self) -> list[PsEntry]:
        live: dict[str, dict] = {}
        result = self.host.run_powershell(ps_list_drives_script())
        if result.stdout.strip():
            try:
                for row in parse_json_list(result.stdout):
                    name = str(row.get("Name") or "")
                    if name:
                        live[name] = row
            except Exception:
                log.warning("Get-PSDrive konnte nicht gelesen werden.", exc_info=True)
        configured = {item["name"]: item for item in self.store.data["psdrives"]}
        # Nur verwaltete und in dieser Vorschau/Sitzung eben angelegte Namen anzeigen,
        # nicht jedes eingebaute Laufwerk wie C, HKLM oder Env.
        if self.host.preview:
            # Die Vorschau kennt nur Laufwerke, die SphereDrive selbst angelegt hat.
            names = list(dict.fromkeys([*configured.keys(), *live.keys()]))
        else:
            # Get-PSDrive liefert auch C:, HKLM: und Env:. Angezeigt werden die gespeicherten.
            names = list(configured.keys())
        entries: list[PsEntry] = []
        for name in names:
            stored = configured.get(name, {})
            current = live.get(name, {})
            root = str(current.get("Root") or stored.get("root") or "")
            provider = str(current.get("Provider") or stored.get("provider") or "")
            if name in configured and name in live:
                status = "aktiv"
            elif name in live:
                status = "nicht verwaltet"
            elif stored.get("profile"):
                status = "im Profil"
            else:
                status = "nur Sitzung"
            entries.append(
                PsEntry(
                    name=name,
                    provider=provider,
                    root=root,
                    profile=bool(stored.get("profile")),
                    persist_windows=bool(stored.get("persist_windows")),
                    status=status,
                    managed=name in configured,
                )
            )
        return entries

    def _write_dos_device(self, letter: str, path: str) -> str | None:
        try:
            self.host.registry.set_sz("HKLM", DOS_DEVICES, f"{letter}:", dos_device_value(path))
        except PermissionError:
            return (
                "Der dauerhafte DOS-Devices-Eintrag braucht Administratorrechte. "
                "Bis dahin stellt der Autostart das Laufwerk nach der Anmeldung wieder her."
            )
        return t("DOS Devices übernimmt das Laufwerk beim nächsten Systemstart, auch für Administratoren.")

    def _delete_dos_device(self, letter: str) -> str | None:
        try:
            self.host.registry.delete_value("HKLM", DOS_DEVICES, f"{letter}:")
        except PermissionError:
            return t("Der DOS-Devices-Eintrag konnte ohne Administratorrechte nicht entfernt werden.")
        return None

    def _dos_device_present(self, letter: str) -> bool:
        return self.host.registry.get_sz("HKLM", DOS_DEVICES, f"{letter}:") not in (None, "")

    def _write_appearance(self, letter: str, label: str, icon: str, warnings: list[str]) -> None:
        label = label.strip()
        icon = icon.strip()
        for hive in ("HKCU", "HKLM"):
            try:
                if label:
                    self.host.registry.set_sz(hive, drive_icon_key(letter, "DefaultLabel"), "", label)
                if icon:
                    self.host.registry.set_sz(
                        hive, drive_icon_key(letter, "DefaultIcon"), "", icon_registry_value(icon)
                    )
            except PermissionError:
                if hive == "HKLM":
                    continue
                warnings.append(t("Bezeichnung oder Symbol konnten nicht gespeichert werden."))

    def _delete_appearance(self, letter: str) -> None:
        for hive in ("HKCU", "HKLM"):
            try:
                self.host.registry.delete_tree(hive, rf"Software\Microsoft\Windows\CurrentVersion\Explorer\DriveIcons\{letter}")
            except PermissionError:
                continue

    def _read_label(self, letter: str) -> str:
        for hive in ("HKCU", "HKLM"):
            value = self.host.registry.get_sz(hive, drive_icon_key(letter, "DefaultLabel"), "")
            if value:
                return value
        return ""

    def _read_icon(self, letter: str) -> str:
        for hive in ("HKCU", "HKLM"):
            value = self.host.registry.get_sz(hive, drive_icon_key(letter, "DefaultIcon"), "")
            if value:
                return value
        return ""

    def _enable_recycle(self, letter: str, name: str, capacity_mb: int, guid: str) -> tuple[str, str | None]:
        try:
            capacity = int(capacity_mb)
        except (TypeError, ValueError):
            capacity = 10240
        capacity = min(max(capacity, 1), 999999)
        existing = guid or self._find_recycle_guid(letter) or ""
        if existing and not existing.startswith("{"):
            existing = "{" + existing + "}"
        token = existing or "{" + str(uuid.uuid4()).upper() + "}"
        try:
            for base in (FOLDER_DESC, FOLDER_DESC_WOW):
                key = base + "\\" + token
                self.host.registry.set_sz("HKLM", key, "RelativePath", f"{letter}:\\")
                self.host.registry.set_sz("HKLM", key, "Name", name[:64] or f"{letter}_Drive")
                self.host.registry.set_dword("HKLM", key, "Category", 4)
            for base in (BITBUCKET, BITBUCKET_WOW):
                key = base + "\\" + token
                self.host.registry.set_dword("HKCU", key, "NukeOnDelete", 0)
                self.host.registry.set_dword("HKCU", key, "MaxCapacity", capacity)
        except PermissionError:
            return "", t("Der Papierkorb für virtuelle Laufwerke braucht Administratorrechte (Known-Folder-Registrierung).")
        return token, t(
            "Papierkorb für {letter}: ist registriert ({capacity} MB). "
            "Falls der Explorer ihn noch nicht anbietet, einmal ab- und wieder anmelden. "
            "Die Dateien bleiben auf dem Datenträger des Zielordners.",
            letter=letter,
            capacity=capacity,
        )

    def _disable_recycle(self, letter: str, guid: str) -> str | None:
        del letter
        token = guid if guid.startswith("{") else "{" + guid + "}"
        try:
            for base in (FOLDER_DESC, FOLDER_DESC_WOW):
                self.host.registry.delete_tree("HKLM", base + "\\" + token)
            for base in (BITBUCKET, BITBUCKET_WOW):
                self.host.registry.delete_tree("HKCU", base + "\\" + token)
        except PermissionError:
            return t("Die Papierkorb-Registrierung konnte ohne Administratorrechte nicht entfernt werden.")
        return None

    def _find_recycle_guid(self, letter: str) -> str | None:
        try:
            for name in self.host.registry.subkeys("HKLM", FOLDER_DESC):
                relative = self.host.registry.get_sz("HKLM", FOLDER_DESC + "\\" + name, "RelativePath")
                if relative and relative.rstrip("\\").upper() == f"{letter}:":
                    return name if name.startswith("{") else "{" + name + "}"
        except PermissionError:
            return None
        return None

    def _enable_uac_mapping(self) -> str | None:
        changed = not self.linked_connections_enabled()
        try:
            self.host.registry.set_dword("HKLM", POLICIES_SYSTEM, "EnableLinkedConnections", 1)
        except PermissionError:
            return (
                "Damit auch Programme mit Administratorrechten das Laufwerk sehen, "
                "EnableLinkedConnections und die erhöhte Anmeldungsaufgabe einschalten. Das braucht Administratorrechte."
            )
        task_note = ""
        if not self.host.task_exists() and self.host.is_admin():
            command, arguments = restore_launch()
            created = self.host.create_logon_task(command, arguments)
            if created.ok:
                self.store.data["settings"]["elevated_task"] = True
                task_note = t(" Die Anmeldungsaufgabe mit höchsten Rechten wurde eingerichtet.")
        if changed:
            return t("EnableLinkedConnections ist gesetzt und wirkt nach einem Neustart.") + task_note
        return task_note.strip() or None

    def _rewrite_profiles(self) -> None:
        block = render_profile_block(self.store.data["psdrives"])
        for path in self.host.profile_paths():
            current = self.host.read_text(path)
            updated = replace_marked_block(current, block)
            if updated != current:
                self.host.write_text(path, updated)

    def _existing_subst(self, letter: str) -> dict:
        return self._find("subst", "letter", letter) or {}

    def _find(self, section: str, key: str, value: str) -> dict | None:
        wanted = value.casefold()
        for item in self.store.data[section]:
            current = str(item.get(key, ""))
            if key in {"link", "path", "target"}:
                if norm_path(current) == norm_path(value):
                    return item
            elif current.casefold() == wanted:
                return item
        return None

    def _upsert(self, section: str, key: str, item: dict) -> None:
        rows = self.store.data[section]
        for index, current in enumerate(rows):
            if key in {"link", "target"} and norm_path(str(current.get(key, ""))) == norm_path(str(item.get(key, ""))):
                rows[index] = item
                break
            if str(current.get(key, "")).casefold() == str(item.get(key, "")).casefold():
                rows[index] = item
                break
        else:
            rows.append(item)
        self.store.save()

    def _drop(self, section: str, key: str, value: str) -> None:
        wanted = value.casefold()
        self.store.data[section] = [
            item for item in self.store.data[section] if str(item.get(key, "")).casefold() != wanted
        ]
        self.store.save()

    def _drop_path(self, section: str, key: str, value: str) -> None:
        wanted = norm_path(value)
        self.store.data[section] = [
            item for item in self.store.data[section] if norm_path(str(item.get(key, ""))) != wanted
        ]
        self.store.save()

    def _drop_mount(self, target: str) -> None:
        wanted = target.rstrip("\\").casefold()
        self.store.data["mounts"] = [
            item
            for item in self.store.data["mounts"]
            if str(item.get("target", "")).rstrip("\\").casefold() != wanted
        ]
        self.store.save()

    def _from_run(self, result: RunResult, success: str, fallback: str) -> OpResult:
        if result.ok:
            return OpResult(True, success or result.stdout.strip() or t("Erledigt."))
        text = result.text or f"{fallback} (Code {result.code})."
        return OpResult(False, text)


def _mount_letter(mount: str) -> str | None:
    text = (mount or "").strip()
    if len(text) >= 2 and text[0].isalpha() and text[1] == ":":
        return text[0].upper()
    return None


def _win_basename(path: str) -> str:
    text = (path or "").replace("/", "\\").rstrip("\\")
    if not text:
        return ""
    return text.rsplit("\\", 1)[-1]


def _volume_from(volume_id: str, mounts: list[str], row: dict) -> VolumeEntry:
    letter = str(row.get("DriveLetter") or "")
    if letter.endswith(":"):
        letter = letter[:-1]
    return VolumeEntry(
        id=volume_id,
        label=str(row.get("Label") or ""),
        filesystem=str(row.get("FileSystem") or ""),
        capacity=as_int(row.get("Capacity")),
        free=as_int(row.get("FreeSpace")),
        mounts=list(mounts),
    )


def _kind_from_scan(link_type: str, attributes: int) -> str:
    directory = bool(attributes & 0x10)
    if link_type.lower() == "junction":
        return "junction"
    if directory:
        return "symlink_dir"
    return "symlink_file"
