"""Optionale, privacy-respektierende Diagnostik — 2.6.27.

- **Default aus** (Opt-in)
- Settings-Toggle aktivierbar
- **Kein PII**: keine Dateipfade, keine Dateinamen, keine Texte, keine IPs
- **Kein Netzwerk**: nur lokales Zähler-Log unter ``config_dir()/diagnostics.jsonl``
- Bei Opt-out: kompletter No-op (wie früher)
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from instantlensdoc import __version__

# Erlaubte Event-Namen (Whitelist) — alles andere wird verworfen
_ALLOWED_EVENTS = re.compile(
    r"^(app|doc|ann|ocr|export|hook|settings|ui|smoke)\.[a-z0-9_.]+$"
)
_ALLOWED_KEYS = frozenset(
    {
        "event",
        "ts",
        "version",
        "count",
        "ok",
        "kind",
        "fmt",
        "enabled",
        "requested",
        "level",
        "code",
    }
)


def is_telemetry_opt_in() -> bool:
    """Liest Settings — Default False."""
    try:
        from instantlensdoc.core.app_settings import get_telemetry_opt_in

        return bool(get_telemetry_opt_in())
    except Exception:
        return False


def _diagnostics_path() -> Path:
    from instantlensdoc.config import config_dir

    return config_dir() / "diagnostics.jsonl"


def _sanitize_payload(event: str, kwargs: dict[str, Any]) -> dict[str, Any] | None:
    """Nur Whitelist-Events + skalare Nicht-PII-Felder."""
    ev = str(event or "").strip().lower()
    if not ev or not _ALLOWED_EVENTS.match(ev):
        return None
    out: dict[str, Any] = {
        "event": ev,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "version": __version__,
    }
    for key, val in (kwargs or {}).items():
        k = str(key).strip().lower()
        if k not in _ALLOWED_KEYS or k in ("event", "ts", "version"):
            continue
        if isinstance(val, bool):
            out[k] = val
        elif isinstance(val, int) and not isinstance(val, bool):
            out[k] = int(val)
        elif isinstance(val, float):
            out[k] = float(val)
        elif isinstance(val, str):
            # kurze Codes, keine Pfade
            s = val.strip()
            if not s or len(s) > 32:
                continue
            if "/" in s or "\\" in s or "@" in s or ":" in s:
                continue
            out[k] = s
    return out


def report_anonymous_usage(event: str = "", **kwargs: Any) -> None:
    """
    Schreibt bei Opt-in einen anonymen Diagnostik-Eintrag lokal.

    Ohne Opt-in: no-op. Niemals Netzwerk.
    """
    if not is_telemetry_opt_in():
        return
    payload = _sanitize_payload(event, kwargs)
    if not payload:
        return
    try:
        path = _diagnostics_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        # Datei begrenzen (~500 KB)
        if path.stat().st_size > 500_000:
            lines = path.read_text(encoding="utf-8").splitlines()
            path.write_text("\n".join(lines[-200:]) + "\n", encoding="utf-8")
    except Exception:
        return None


def diagnostics_summary(*, limit: int = 50) -> dict[str, Any]:
    """Lokale Diagnostik-Zusammenfassung (keine Roh-PII)."""
    path = _diagnostics_path()
    counts: dict[str, int] = {}
    recent: list[dict[str, Any]] = []
    if path.is_file():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                ev = str(row.get("event") or "")
                if ev:
                    counts[ev] = counts.get(ev, 0) + 1
            for line in lines[-max(1, int(limit)) :]:
                try:
                    recent.append(json.loads(line))
                except Exception:
                    continue
        except Exception:
            pass
    return {
        "opt_in": is_telemetry_opt_in(),
        "path": str(path) if is_telemetry_opt_in() else "",
        "counts": counts,
        "recent": recent if is_telemetry_opt_in() else [],
        "network": False,
        "pii": False,
        "version": __version__,
    }


def clear_diagnostics() -> bool:
    """Lokales Diagnostik-Log löschen."""
    try:
        path = _diagnostics_path()
        if path.is_file():
            path.unlink()
        return True
    except Exception:
        return False


def telemetry_stub_info() -> dict[str, Any]:
    """Status für Settings/About — Name beibehalten für Kompatibilität."""
    opt = is_telemetry_opt_in()
    why = (
        "Warum lokal: nur Diagnostik-Log bei Opt-in; keine Dateipfade/Texte/IPs; "
        "kein Netzwerk — keine Datenübertragung. Default aus. Privacy first."
    )
    return {
        "name": "Telemetrie",
        "stub": False,
        "live": True,
        "opt_in": opt,
        "enabled": opt,
        "toggle_disabled": False,
        "noop": not opt,
        "network": False,
        "pii": False,
        "why": why,
        "stubs_tab_hint": (
            "Details und Status: Einstellungen → Tab „Stubs“ "
            "(Button „Stubs öffnen“) → Fokus erste Stub-Zeile · "
            "Eintrag Telemetrie. Esc schließt den Info-Dialog. "
            "Lokales Log: diagnostics.jsonl"
        ),
        "message": (
            f"Telemetrie {__version__}: Opt-in "
            f"{'an' if opt else 'aus (Default)'} — lokal, kein Netzwerk, kein PII — "
            f"keine Datenübertragung. {why}"
        ),
        "version_marker": __version__,
        "not_production_ready": False,
    }


# Klarer Alias
telemetry_info = telemetry_stub_info
