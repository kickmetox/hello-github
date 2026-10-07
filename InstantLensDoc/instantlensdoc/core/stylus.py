"""Stylus / Stift-Eingabe für Annotationen — 2.6.27.

Druckempfindlichkeit wenn Tablet/Stylus Druck liefert; sonst verbesserte
Stift-Integration (gleicher Freihand-Pfad mit optionaler Palm-Rejection).
"""

from __future__ import annotations

from typing import Any, Sequence

from instantlensdoc import __version__

# Basis-Strichstärke-Faktor bei Druck 0…1 → Multiplikator 0.35…1.8
PRESSURE_MIN_FACTOR = 0.35
PRESSURE_MAX_FACTOR = 1.8
DEFAULT_PRESSURE = 0.5


def get_stylus_pressure_enabled() -> bool:
    try:
        from instantlensdoc.core.app_settings import load_settings

        return bool(load_settings().get("stylus_pressure_enabled", True))
    except Exception:
        return True


def set_stylus_pressure_enabled(enabled: bool) -> None:
    from instantlensdoc.core.app_settings import save_settings

    save_settings({"stylus_pressure_enabled": bool(enabled)})


def get_stylus_palm_rejection() -> bool:
    try:
        from instantlensdoc.core.app_settings import load_settings

        return bool(load_settings().get("stylus_palm_rejection", True))
    except Exception:
        return True


def set_stylus_palm_rejection(enabled: bool) -> None:
    from instantlensdoc.core.app_settings import save_settings

    save_settings({"stylus_palm_rejection": bool(enabled)})


def pressure_to_stroke_width(base_width: float, pressure: float) -> float:
    """Mappt Stylus-Druck (0–1) auf Strichstärke um die Basisbreite."""
    p = max(0.0, min(1.0, float(pressure)))
    factor = PRESSURE_MIN_FACTOR + (PRESSURE_MAX_FACTOR - PRESSURE_MIN_FACTOR) * p
    w = float(base_width or 2.0) * factor
    return max(0.5, min(24.0, w))


def normalize_ink_point(pt: Sequence[float]) -> list[float]:
    """Punkt als [x, y] oder [x, y, pressure] normalisieren."""
    x = float(pt[0])
    y = float(pt[1])
    if len(pt) >= 3:
        try:
            pr = float(pt[2])
        except (TypeError, ValueError):
            pr = DEFAULT_PRESSURE
        return [x, y, max(0.0, min(1.0, pr))]
    return [x, y]


def point_pressure(pt: Sequence[float], default: float = DEFAULT_PRESSURE) -> float:
    if len(pt) >= 3:
        try:
            return max(0.0, min(1.0, float(pt[2])))
        except (TypeError, ValueError):
            return float(default)
    return float(default)


def should_reject_palm(
    *,
    pointer_type: str,
    pressure: float | None = None,
    contact_size: float | None = None,
) -> bool:
    """
    Einfache Palm-Rejection-Heuristik.

    - Touch (Finger) wird verworfen wenn Palm-Rejection aktiv
    - Sehr große Kontaktfläche → Handballen
    """
    if not get_stylus_palm_rejection():
        return False
    kind = (pointer_type or "").strip().lower()
    if kind in ("touch", "finger", "touchevent"):
        return True
    if contact_size is not None and float(contact_size) > 40.0:
        return True
    # Druck 0 bei deklariertem Stylus oft Finger-Proxy — nur bei sehr niedrig + Touch
    if kind == "unknown" and pressure is not None and float(pressure) <= 0.0:
        return False
    return False


def stylus_info() -> dict[str, Any]:
    """Status für Settings/About/Stubs — produktiv ab 2.6.27."""
    return {
        "name": "Stylus / Palm Rejection",
        "stub": False,
        "live": True,
        "pressure_enabled": get_stylus_pressure_enabled(),
        "palm_rejection": get_stylus_palm_rejection(),
        "pressure_range": [0.0, 1.0],
        "stroke_factor_range": [PRESSURE_MIN_FACTOR, PRESSURE_MAX_FACTOR],
        "message": (
            f"Stylus {__version__}: Druckempfindlichkeit "
            f"{'an' if get_stylus_pressure_enabled() else 'aus'}, "
            f"Palm-Rejection {'an' if get_stylus_palm_rejection() else 'aus'} — "
            "Tablet/Stift → variable Strichstärke; ohne Druck = Maus-Freihand."
        ),
        "version_marker": __version__,
        "not_production_ready": False,
    }
