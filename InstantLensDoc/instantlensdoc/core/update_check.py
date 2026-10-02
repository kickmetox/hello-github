"""Update-Hinweis: lokal immer, Online optional (offline-fähig)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

from instantlensdoc import __version__

# Öffentliche Version-Datei auf dem Feature-Branch (optional; Ausfall = offline OK)
DEFAULT_VERSION_URL = (
    "https://raw.githubusercontent.com/kickmetox/hello-github/"
    "cursor/instantlensdoc-2108/InstantLensDoc/instantlensdoc/__init__.py"
)


@dataclass
class UpdateResult:
    local_version: str
    remote_version: Optional[str]
    online: bool
    newer_available: bool
    message_de: str
    message_en: str

    def message(self, lang: str = "de") -> str:
        return self.message_en if str(lang).startswith("en") else self.message_de


def _parse_version_from_init(text: str) -> Optional[str]:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("__version__"):
            # __version__ = "0.3.1"
            parts = line.split("=", 1)
            if len(parts) == 2:
                return parts[1].strip().strip("\"'")
    return None


def _cmp_tuple(v: str) -> tuple:
    nums = []
    for part in v.replace("-", ".").split("."):
        try:
            nums.append(int(part))
        except ValueError:
            nums.append(0)
    return tuple(nums)


def check_for_updates(
    *,
    url: str = DEFAULT_VERSION_URL,
    timeout: float = 3.0,
    allow_network: bool = True,
) -> UpdateResult:
    """
    Vergleicht lokale Version mit Remote-`__init__.py`.
    Bei Netzwerkfehler/Timeout: online=False, klarer Offline-Hinweis.
    """
    local = __version__
    if not allow_network:
        return UpdateResult(
            local_version=local,
            remote_version=None,
            online=False,
            newer_available=False,
            message_de=f"Lokal: {local} — Online-Check deaktiviert (offline OK).",
            message_en=f"Local: {local} — online check disabled (offline OK).",
        )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": f"InstantLensDoc/{local}"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        remote = _parse_version_from_init(raw)
        if not remote:
            return UpdateResult(
                local_version=local,
                remote_version=None,
                online=True,
                newer_available=False,
                message_de=f"Lokal: {local} — Remote-Version nicht lesbar.",
                message_en=f"Local: {local} — could not parse remote version.",
            )
        newer = _cmp_tuple(remote) > _cmp_tuple(local)
        if newer:
            msg_de = f"Update verfügbar: lokal {local} → remote {remote}."
            msg_en = f"Update available: local {local} → remote {remote}."
        elif remote == local:
            msg_de = f"Aktuell: {local} (entspricht Remote)."
            msg_en = f"Up to date: {local} (matches remote)."
        else:
            msg_de = f"Lokal {local} ist neuer/anders als Remote {remote}."
            msg_en = f"Local {local} is newer/different than remote {remote}."
        return UpdateResult(
            local_version=local,
            remote_version=remote,
            online=True,
            newer_available=newer,
            message_de=msg_de,
            message_en=msg_en,
        )
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        return UpdateResult(
            local_version=local,
            remote_version=None,
            online=False,
            newer_available=False,
            message_de=f"Lokal: {local} — Online-Check nicht möglich (offline OK). ({e.__class__.__name__})",
            message_en=f"Local: {local} — online check unavailable (offline OK). ({e.__class__.__name__})",
        )
