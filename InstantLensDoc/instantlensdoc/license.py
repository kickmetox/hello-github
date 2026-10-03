"""Lizenzierung: Trial 28 Tage, Keys 32 Tage (30+2), HMAC-verifizierbar."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Gemeinsames Geheimnis für lokal verifizierbare Keys (nicht kryptografisch „stark“ gegen Reverse Engineering —
# Zweck: Offline-Aktivierung ohne Server). Keygen und App nutzen denselben Wert.
_SECRET = b"InstantLensDoc-ILD-2026-ame@sellerbach.de-v1"

TRIAL_DAYS = 28
KEY_DAYS = 32  # 30 + 2


def _app_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    d = base / "InstantLensDoc"
    d.mkdir(parents=True, exist_ok=True)
    return d


def license_state_path() -> Path:
    return _app_data_dir() / "license.json"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def generate_key(email: str, issued_at: Optional[int] = None) -> str:
    """Key erzeugen: ILD1.<payload_b64>.<sig_b64>"""
    issued = int(issued_at if issued_at is not None else time.time())
    payload = json.dumps(
        {"e": email.strip().lower(), "i": issued, "d": KEY_DAYS, "v": 1},
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    sig = hmac.new(_SECRET, payload, hashlib.sha256).digest()
    return f"ILD1.{_b64url(payload)}.{_b64url(sig)}"


def verify_key(key: str) -> tuple[bool, str, Optional[dict]]:
    """Key prüfen. Rückgabe: (ok, meldung, payload|None)."""
    key = (key or "").strip()
    parts = key.split(".")
    if len(parts) != 3 or parts[0] != "ILD1":
        return False, "Ungültiges Key-Format", None
    try:
        payload = _b64url_decode(parts[1])
        sig = _b64url_decode(parts[2])
    except Exception:
        return False, "Key konnte nicht dekodiert werden", None
    expected = hmac.new(_SECRET, payload, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        return False, "Schlüssel ungültig (Signatur)", None
    try:
        data = json.loads(payload.decode("utf-8"))
    except Exception:
        return False, "Payload ungültig", None
    issued = int(data.get("i", 0))
    days = int(data.get("d", KEY_DAYS))
    expires = issued + days * 86400
    now = int(time.time())
    if now > expires:
        return False, "Schlüssel abgelaufen — bitte neuen Key per Mail anfordern (ame@sellerbach.de)", data
    return True, "Schlüssel gültig", data


def format_resttage(days: int) -> str:
    """Einheitliche Resttage-Formulierung für Statusleiste / About / Dialog — 1.0.2."""
    d = max(0, int(days))
    if d == 1:
        return "1 Tag"
    return f"{d} Tage"


def resttage_phrase(days: int, *, prefix: str = "noch") -> str:
    """z. B. ``noch 12 Tage`` / ``noch 1 Tag`` — konsistent Status + About."""
    return f"{prefix} {format_resttage(days)}"


def format_ablaufdatum(dt: Optional[datetime], *, empty: str = "—") -> str:
    """Ablaufdatum als TT.MM.JJJJ für About / Status / Dialog — 1.0.3."""
    if dt is None:
        return empty
    try:
        if dt.tzinfo is not None:
            local = dt.astimezone()
        else:
            local = dt.replace(tzinfo=timezone.utc).astimezone()
        return local.strftime("%d.%m.%Y")
    except Exception:
        raw = str(dt)
        return raw[:10] if raw else empty


# Warnung ab diesem Resttage-Wert (inkl.), einmalig pro Kalendertag — 1.0.4
EXPIRY_WARN_DAYS = 3


def _today_iso() -> str:
    return datetime.now().astimezone().date().isoformat()


@dataclass
class LicenseStatus:
    mode: str  # "trial" | "licensed" | "expired"
    message: str
    days_remaining: int
    email: Optional[str] = None
    expires_at: Optional[datetime] = None

    @property
    def allowed(self) -> bool:
        return self.mode in ("trial", "licensed")

    def resttage_text(self, *, prefix: str = "noch") -> str:
        """Konsistente Resttage-Phrase aus dem Statusobjekt."""
        return resttage_phrase(self.days_remaining, prefix=prefix)


class LicenseManager:
    def __init__(self, path: Optional[Path] = None):
        self.path = path or license_state_path()
        self.state = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def ensure_trial_started(self) -> None:
        if "first_run" not in self.state:
            self.state["first_run"] = int(time.time())
            self._save()

    def activate(self, key: str) -> tuple[bool, str]:
        ok, msg, data = verify_key(key)
        if not ok:
            return False, msg
        self.state["key"] = key.strip()
        self.state["email"] = (data or {}).get("e")
        self.state["activated_at"] = int(time.time())
        self._save()
        return True, msg

    def clear_key(self) -> None:
        self.state.pop("key", None)
        self.state.pop("email", None)
        self.state.pop("activated_at", None)
        self._save()

    def should_show_expiry_warning(self, st: Optional[LicenseStatus] = None) -> bool:
        """True wenn Resttage ≤3, noch gültig, und heute noch nicht gewarnt — 1.0.4."""
        status = st if st is not None else self.status()
        if not status.allowed:
            return False
        if int(status.days_remaining) > EXPIRY_WARN_DAYS:
            return False
        last = str(self.state.get("expiry_warn_day") or "")
        return last != _today_iso()

    def mark_expiry_warning_shown(self) -> None:
        """Merkt den heutigen Kalendertag als „Warnung gezeigt“ — 1.0.4."""
        self.state["expiry_warn_day"] = _today_iso()
        self._save()

    def status(self) -> LicenseStatus:
        self.ensure_trial_started()
        key = self.state.get("key")
        if key:
            ok, msg, data = verify_key(key)
            if ok and data:
                issued = int(data["i"])
                days = int(data.get("d", KEY_DAYS))
                expires = issued + days * 86400
                rem = max(0, (expires - int(time.time()) + 86399) // 86400)
                return LicenseStatus(
                    mode="licensed",
                    message=msg,
                    days_remaining=rem,
                    email=data.get("e"),
                    expires_at=datetime.fromtimestamp(expires, tz=timezone.utc),
                )
            # Abgelaufener/ungültiger Key → Trial prüfen
            first = int(self.state.get("first_run", time.time()))
            trial_end = first + TRIAL_DAYS * 86400
            rem = max(0, (trial_end - int(time.time()) + 86399) // 86400)
            if int(time.time()) <= trial_end:
                return LicenseStatus(
                    mode="trial",
                    message=f"Key ungültig/abgelaufen — Trial noch aktiv. {msg}",
                    days_remaining=rem,
                )
            return LicenseStatus(mode="expired", message=msg, days_remaining=0)

        first = int(self.state.get("first_run", time.time()))
        trial_end = first + TRIAL_DAYS * 86400
        rem = max(0, (trial_end - int(time.time()) + 86399) // 86400)
        if int(time.time()) <= trial_end:
            return LicenseStatus(
                mode="trial",
                message=f"Testversion — noch {rem} Tag(e)",
                days_remaining=rem,
                expires_at=datetime.fromtimestamp(trial_end, tz=timezone.utc),
            )
        return LicenseStatus(
            mode="expired",
            message="Testzeit abgelaufen. Key anfordern: ame@sellerbach.de",
            days_remaining=0,
            expires_at=datetime.fromtimestamp(trial_end, tz=timezone.utc),
        )
