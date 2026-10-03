"""Telemetrie-Stub — klar opt-in, Default aus, immer no-op — 2.3.0.

Auch bei aktivierter Einstellung wird **nichts** gesendet und nichts geloggt.
Kein Netzwerk, keine Queue, kein Fingerprinting.
"""

from __future__ import annotations

from typing import Any


def is_telemetry_opt_in() -> bool:
    """Liest Settings „anonym Nutzung melden“ (Default False)."""
    try:
        from instantlensdoc.core.app_settings import get_telemetry_opt_in

        return bool(get_telemetry_opt_in())
    except Exception:
        return False


def report_anonymous_usage(event: str = "", **_kwargs: Any) -> None:
    """
    No-op Stub: auch bei Opt-in sendet nichts.

    ``event`` / kwargs werden ignoriert — absichtlich ohne Side-Effects.
    """
    return None


def telemetry_stub_info() -> dict[str, Any]:
    """Status für Settings/About/Stubs-Seite."""
    from instantlensdoc import __version__

    opt_in = is_telemetry_opt_in()
    return {
        "name": "Telemetrie",
        "stub": True,
        "opt_in": opt_in,
        "enabled": False,  # nie aktiv — Stub
        "noop": True,
        "message": (
            f"Telemetrie-Stub {__version__}: opt-in „anonym Nutzung melden“ "
            f"{'an' if opt_in else 'aus'}, immer no-op — keine Datenübertragung"
        ),
        "version_marker": __version__,
        "not_production_ready": True,
    }
