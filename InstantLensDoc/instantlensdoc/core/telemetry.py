"""Telemetrie-Stub — klar markiert, Toggle disabled, immer no-op — 2.3.2.

Auch bei gespeichertem Opt-in-Flag wird **nichts** gesendet und nichts geloggt.
Kein Netzwerk, keine Queue, kein Fingerprinting.
Ab 2.3.2: Settings-Toggle bleibt disabled (aus); Info-Dialog erklärt warum.
"""

from __future__ import annotations

from typing import Any


def is_telemetry_opt_in() -> bool:
    """Liest Settings — ab 2.3.2 immer False (Toggle disabled)."""
    try:
        from instantlensdoc.core.app_settings import get_telemetry_opt_in

        return bool(get_telemetry_opt_in())
    except Exception:
        return False


def report_anonymous_usage(event: str = "", **_kwargs: Any) -> None:
    """
    No-op Stub: sendet nichts.

    ``event`` / kwargs werden ignoriert — absichtlich ohne Side-Effects.
    """
    return None


def telemetry_stub_info() -> dict[str, Any]:
    """Status für Settings/About/Stubs-Seite — 2.3.2."""
    from instantlensdoc import __version__

    return {
        "name": "Telemetrie",
        "stub": True,
        "opt_in": False,
        "enabled": False,  # nie aktiv — Stub; Toggle disabled
        "toggle_disabled": True,
        "noop": True,
        "message": (
            f"Telemetrie-Stub {__version__}: Toggle disabled (bleibt aus), "
            "immer no-op — keine Datenübertragung (kein Netzwerk). "
            "Info-Dialog erklärt warum Stub."
        ),
        "version_marker": __version__,
        "not_production_ready": True,
    }
