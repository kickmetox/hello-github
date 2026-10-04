"""Update-Hinweis: lokaler Versionsvergleich (docs/VERSION / VERSION.txt); Online optional."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from instantlensdoc import __version__
from instantlensdoc.config import ROOT

_log = logging.getLogger("instantlensdoc.update")

# Öffentliche Version-Datei auf dem Feature-Branch (optional; Ausfall = offline OK)
DEFAULT_VERSION_URL = (
    "https://raw.githubusercontent.com/kickmetox/hello-github/"
    "cursor/instantlensdoc-2108/InstantLensDoc/docs/VERSION"
)

UpdateStatus = Literal["current", "newer", "unknown", "offline"]


@dataclass
class UpdateResult:
    local_version: str
    remote_version: Optional[str]
    online: bool
    newer_available: bool
    message_de: str
    message_en: str
    reference_source: str = ""  # docs/VERSION | VERSION.txt | remote | none
    status: UpdateStatus = "unknown"  # aktuell / neuer Build / offline / unbekannt
    checked_at: str = ""  # ISO-Zeitstempel letzter Check — 1.7.3

    def message(self, lang: str = "de") -> str:
        return self.message_en if str(lang).startswith("en") else self.message_de

    def status_label(self, lang: str = "de") -> str:
        """Kurzstatus inkl. offline / nicht geprüft — 1.7.3."""
        de = {
            "current": "aktuell",
            "newer": "neuer Build Hinweis",
            "unknown": "unbekannt",
            "offline": "offline / nicht geprüft",
        }
        en = {
            "current": "up to date",
            "newer": "newer build notice",
            "unknown": "unknown",
            "offline": "offline / not checked",
        }
        table = en if str(lang).startswith("en") else de
        return table.get(self.status, table["unknown"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


def _record_check_timestamp(iso_ts: str | None = None) -> str:
    """Zeitstempel speichern und zurückgeben — 1.7.3."""
    from instantlensdoc.core.app_settings import set_last_update_check_at

    ts = (iso_ts or _now_iso()).strip()
    try:
        set_last_update_check_at(ts)
    except Exception:
        pass
    return ts


def format_checked_at(iso_ts: str | None, *, lang: str = "de") -> str:
    """Lesbarer Zeitstempel TT.MM.JJJJ HH:MM für Status/Dialog — 1.7.4."""
    raw = str(iso_ts or "").strip()
    if not raw:
        return "nie" if not str(lang).startswith("en") else "never"
    try:
        dt = datetime.fromisoformat(raw)
        return dt.strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return raw


def format_reference_source_tooltip(source: str | None, *, lang: str = "de") -> str:
    """Tooltip-Text mit Versionsquelle (docs/VERSION / VERSION.txt) — 1.7.4/1.7.5."""
    src = str(source or "").strip() or "—"
    if str(lang).startswith("en"):
        return f"Source: {src} (docs/VERSION or VERSION.txt; click opens in editor)"
    return f"Quelle: {src} (docs/VERSION oder VERSION.txt; Klick öffnet im Editor)"


def _parse_version_from_init(text: str) -> Optional[str]:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("__version__"):
            parts = line.split("=", 1)
            if len(parts) == 2:
                return parts[1].strip().strip("\"'")
    return None


def _parse_version_plain(text: str) -> Optional[str]:
    """Erste nicht-leere Zeile als Version (docs/VERSION / VERSION.txt)."""
    for line in (text or "").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        # Nur Versionstoken (z. B. 1.7.0)
        token = s.split()[0].strip().strip("\"'")
        if token and any(c.isdigit() for c in token):
            return token
    return None


def _cmp_tuple(v: str) -> tuple:
    nums = []
    for part in v.replace("-", ".").split("."):
        try:
            nums.append(int(part))
        except ValueError:
            nums.append(0)
    return tuple(nums)


def find_embedded_version_file() -> tuple[Optional[Path], Optional[str]]:
    """
    Lokale Referenzversion suchen:
    1) InstantLensDoc/docs/VERSION
    2) InstantLensDoc/VERSION.txt (eingebettet / Pack)
    3) neben sys._MEIPASS / CWD
    """
    candidates = [
        (ROOT / "docs" / "VERSION", "docs/VERSION"),
        (ROOT / "VERSION.txt", "VERSION.txt"),
        (Path.cwd() / "docs" / "VERSION", "docs/VERSION"),
        (Path.cwd() / "VERSION.txt", "VERSION.txt"),
    ]
    seen: set[str] = set()
    for path, label in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        try:
            if path.is_file():
                ver = _parse_version_plain(path.read_text(encoding="utf-8"))
                if ver:
                    return path, label
        except OSError:
            continue
    return None, None


def read_reference_version() -> tuple[Optional[str], str]:
    """(version, source_label) aus docs/VERSION oder VERSION.txt."""
    path, label = find_embedded_version_file()
    if path is None or label is None:
        return None, "none"
    try:
        ver = _parse_version_plain(path.read_text(encoding="utf-8"))
    except OSError:
        return None, label
    return ver, label


def check_local_version(*, record_timestamp: bool = False) -> UpdateResult:
    """
    Lokaler Versionsvergleich gegen docs/VERSION oder eingebettete VERSION.txt.
    Nur Hinweis — kein Download.
    """
    from instantlensdoc.core.app_settings import get_last_update_check_at

    local = __version__
    checked = _record_check_timestamp() if record_timestamp else get_last_update_check_at()
    checked_fmt_de = format_checked_at(checked, lang="de")
    checked_fmt_en = format_checked_at(checked, lang="en")
    ts_note_de = f" Letzter Check: {checked_fmt_de}."
    ts_note_en = f" Last check: {checked_fmt_en}."

    ref, source = read_reference_version()
    if not ref:
        return UpdateResult(
            local_version=local,
            remote_version=None,
            online=False,
            newer_available=False,
            status="unknown",
            checked_at=checked,
            message_de=(
                f"Status: unbekannt — lokal {local}, keine Referenzdatei "
                f"(docs/VERSION / VERSION.txt) (nur Hinweis, kein Download)."
                f"{ts_note_de}"
            ),
            message_en=(
                f"Status: unknown — local {local}, no reference file "
                f"(docs/VERSION / VERSION.txt) (hint only, no download)."
                f"{ts_note_en}"
            ),
            reference_source="none",
        )
    newer = _cmp_tuple(ref) > _cmp_tuple(local)
    older = _cmp_tuple(ref) < _cmp_tuple(local)
    if newer:
        status: UpdateStatus = "newer"
        msg_de = (
            f"Status: neuer Build Hinweis — installiert {local}, "
            f"Referenz {ref} ({source}). Kein Auto-Download.{ts_note_de}"
        )
        msg_en = (
            f"Status: newer build notice — installed {local}, "
            f"reference {ref} ({source}). No auto-download.{ts_note_en}"
        )
    elif older:
        status = "current"
        msg_de = (
            f"Status: aktuell — lokal {local} ist neuer als Referenz {ref} "
            f"({source}) (nur Hinweis).{ts_note_de}"
        )
        msg_en = (
            f"Status: up to date — local {local} is newer than reference {ref} "
            f"({source}) (hint only).{ts_note_en}"
        )
    else:
        status = "current"
        msg_de = f"Status: aktuell — {local} (entspricht {source}).{ts_note_de}"
        msg_en = f"Status: up to date — {local} (matches {source}).{ts_note_en}"
    return UpdateResult(
        local_version=local,
        remote_version=ref,
        online=False,
        newer_available=newer,
        status=status,
        checked_at=checked,
        message_de=msg_de,
        message_en=msg_en,
        reference_source=source,
    )


def check_for_updates(
    *,
    url: str = DEFAULT_VERSION_URL,
    timeout: float = 3.0,
    allow_network: bool = True,
) -> UpdateResult:
    """
    Primär: lokaler Vergleich gegen docs/VERSION / VERSION.txt (kein Download).
    Optional: Online-Vergleich gegen Remote-VERSION (nur Hinweis).
    Offline → Status „offline / nicht geprüft“ + Zeitstempel — 1.7.3.
    """
    checked = _record_check_timestamp()
    checked_fmt_de = format_checked_at(checked, lang="de")
    checked_fmt_en = format_checked_at(checked, lang="en")
    local_result = check_local_version(record_timestamp=False)
    # Zeitstempel aus diesem Lauf übernehmen
    local_result = UpdateResult(
        local_version=local_result.local_version,
        remote_version=local_result.remote_version,
        online=local_result.online,
        newer_available=local_result.newer_available,
        status=local_result.status,
        checked_at=checked,
        message_de=local_result.message_de,
        message_en=local_result.message_en,
        reference_source=local_result.reference_source,
    )
    if not allow_network:
        # Kein Online-Versuch → offline / nicht geprüft — 1.7.3
        return UpdateResult(
            local_version=local_result.local_version,
            remote_version=local_result.remote_version,
            online=False,
            newer_available=local_result.newer_available,
            status="offline",
            checked_at=checked,
            message_de=(
                f"Status: offline / nicht geprüft — lokal {local_result.local_version} "
                f"({local_result.reference_source or '—'}). "
                f"Online nicht geprüft. Letzter Check: {checked_fmt_de}."
            ),
            message_en=(
                f"Status: offline / not checked — local {local_result.local_version} "
                f"({local_result.reference_source or '—'}). "
                f"Online not checked. Last check: {checked_fmt_en}."
            ),
            reference_source=local_result.reference_source,
        )

    # Online nur ergänzend — bei Erfolg Remote bevorzugen wenn lesbar
    local = __version__
    try:
        req = urllib.request.Request(url, headers={"User-Agent": f"InstantLensDoc/{local}"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        remote = _parse_version_plain(raw) or _parse_version_from_init(raw)
        if not remote:
            # Lokales Ergebnis behalten, aber online=True markieren wenn Request ok
            return UpdateResult(
                local_version=local_result.local_version,
                remote_version=local_result.remote_version,
                online=True,
                newer_available=local_result.newer_available,
                status=local_result.status,
                checked_at=checked,
                message_de=(
                    local_result.message_de
                    + f" Online: Version nicht lesbar. Letzter Check: {checked_fmt_de}."
                ),
                message_en=(
                    local_result.message_en
                    + f" Online: could not parse version. Last check: {checked_fmt_en}."
                ),
                reference_source=local_result.reference_source,
            )
        newer = _cmp_tuple(remote) > _cmp_tuple(local)
        if newer:
            status: UpdateStatus = "newer"
            msg_de = (
                f"Status: neuer Build Hinweis — lokal {local} → remote {remote} "
                f"(kein Auto-Download). Letzter Check: {checked_fmt_de}."
            )
            msg_en = (
                f"Status: newer build notice — local {local} → remote {remote} "
                f"(no auto-download). Last check: {checked_fmt_en}."
            )
        elif remote == local:
            status = "current"
            msg_de = (
                f"Status: aktuell — {local} "
                f"(entspricht Remote; lokal {local_result.reference_source or '—'}). "
                f"Letzter Check: {checked_fmt_de}."
            )
            msg_en = (
                f"Status: up to date — {local} "
                f"(matches remote; local {local_result.reference_source or '—'}). "
                f"Last check: {checked_fmt_en}."
            )
        else:
            status = "current"
            msg_de = (
                f"Status: aktuell — lokal {local} ist neuer/anders als Remote {remote} "
                f"(nur Hinweis). Letzter Check: {checked_fmt_de}."
            )
            msg_en = (
                f"Status: up to date — local {local} is newer/different than remote "
                f"{remote} (hint only). Last check: {checked_fmt_en}."
            )
        return UpdateResult(
            local_version=local,
            remote_version=remote,
            online=True,
            newer_available=newer,
            status=status,
            checked_at=checked,
            message_de=msg_de,
            message_en=msg_en,
            reference_source="remote",
        )
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as e:
        # Offline-Fallback: Status offline / nicht geprüft + Zeitstempel — 1.7.3
        _log.debug("Update online fehlgeschlagen (offline OK): %s", e)
        return UpdateResult(
            local_version=local_result.local_version,
            remote_version=local_result.remote_version,
            online=False,
            newer_available=local_result.newer_available,
            status="offline",
            checked_at=checked,
            message_de=(
                f"Status: offline / nicht geprüft — lokal {local_result.local_version} "
                f"({local_result.reference_source or '—'}). "
                f"Online nicht erreichbar (kein Fehler). Letzter Check: {checked_fmt_de}."
            ),
            message_en=(
                f"Status: offline / not checked — local {local_result.local_version} "
                f"({local_result.reference_source or '—'}). "
                f"Online unreachable (no error). Last check: {checked_fmt_en}."
            ),
            reference_source=local_result.reference_source,
        )
