"""Update-Hinweis: lokaler Versionsvergleich (docs/VERSION / VERSION.txt); Online optional."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from instantlensdoc import __version__
from instantlensdoc.config import ROOT

# Öffentliche Version-Datei auf dem Feature-Branch (optional; Ausfall = offline OK)
DEFAULT_VERSION_URL = (
    "https://raw.githubusercontent.com/kickmetox/hello-github/"
    "cursor/instantlensdoc-2108/InstantLensDoc/docs/VERSION"
)


@dataclass
class UpdateResult:
    local_version: str
    remote_version: Optional[str]
    online: bool
    newer_available: bool
    message_de: str
    message_en: str
    reference_source: str = ""  # docs/VERSION | VERSION.txt | remote | none

    def message(self, lang: str = "de") -> str:
        return self.message_en if str(lang).startswith("en") else self.message_de


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


def check_local_version() -> UpdateResult:
    """
    Lokaler Versionsvergleich gegen docs/VERSION oder eingebettete VERSION.txt.
    Nur Hinweis — kein Download.
    """
    local = __version__
    ref, source = read_reference_version()
    if not ref:
        return UpdateResult(
            local_version=local,
            remote_version=None,
            online=False,
            newer_available=False,
            message_de=(
                f"Lokal: {local} — keine Referenzdatei "
                f"(docs/VERSION / VERSION.txt) gefunden (nur Hinweis, kein Download)."
            ),
            message_en=(
                f"Local: {local} — no reference file "
                f"(docs/VERSION / VERSION.txt) found (hint only, no download)."
            ),
            reference_source="none",
        )
    newer = _cmp_tuple(ref) > _cmp_tuple(local)
    older = _cmp_tuple(ref) < _cmp_tuple(local)
    if newer:
        msg_de = (
            f"Update-Hinweis: installiert {local}, Referenz {ref} ({source}). "
            f"Kein Auto-Download."
        )
        msg_en = (
            f"Update notice: installed {local}, reference {ref} ({source}). "
            f"No auto-download."
        )
    elif older:
        msg_de = (
            f"Lokal {local} ist neuer als Referenz {ref} ({source}) — nur Hinweis."
        )
        msg_en = (
            f"Local {local} is newer than reference {ref} ({source}) — hint only."
        )
    else:
        msg_de = f"Aktuell: {local} (entspricht {source})."
        msg_en = f"Up to date: {local} (matches {source})."
    return UpdateResult(
        local_version=local,
        remote_version=ref,
        online=False,
        newer_available=newer,
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
    """
    local_result = check_local_version()
    if not allow_network:
        return local_result

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
                message_de=local_result.message_de + " Online: Version nicht lesbar.",
                message_en=local_result.message_en + " Online: could not parse version.",
                reference_source=local_result.reference_source,
            )
        newer = _cmp_tuple(remote) > _cmp_tuple(local)
        if newer:
            msg_de = (
                f"Update-Hinweis: lokal {local} → remote {remote} "
                f"(kein Auto-Download)."
            )
            msg_en = (
                f"Update notice: local {local} → remote {remote} "
                f"(no auto-download)."
            )
        elif remote == local:
            msg_de = f"Aktuell: {local} (entspricht Remote; lokal {local_result.reference_source or '—'})."
            msg_en = f"Up to date: {local} (matches remote; local {local_result.reference_source or '—'})."
        else:
            msg_de = f"Lokal {local} ist neuer/anders als Remote {remote} (nur Hinweis)."
            msg_en = f"Local {local} is newer/different than remote {remote} (hint only)."
        return UpdateResult(
            local_version=local,
            remote_version=remote,
            online=True,
            newer_available=newer,
            message_de=msg_de,
            message_en=msg_en,
            reference_source="remote",
        )
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        # Offline OK — lokaler Hinweis bleibt
        return local_result
