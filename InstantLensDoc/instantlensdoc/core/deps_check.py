"""Startup-Check für Laufzeit-Abhängigkeiten (pypdfium2 / Tesseract)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class DepStatus:
    """Ergebnis einer einzelnen Abhängigkeitsprüfung."""

    key: str
    label: str
    ok: bool
    critical: bool
    message: str


def check_pypdfium2() -> DepStatus:
    try:
        import pypdfium2 as pdfium  # noqa: F401

        ver = getattr(pdfium, "__version__", None) or ""
        detail = f"pypdfium2 {ver}".strip() if ver else "pypdfium2 verfügbar"
        return DepStatus(
            key="pypdfium2",
            label="PDF-Engine (pypdfium2)",
            ok=True,
            critical=True,
            message=detail,
        )
    except Exception as e:
        return DepStatus(
            key="pypdfium2",
            label="PDF-Engine (pypdfium2)",
            ok=False,
            critical=True,
            message=(
                "pypdfium2 fehlt oder ist fehlerhaft.\n"
                "Installieren: pip install pypdfium2\n\n"
                f"Technik: {e}"
            ),
        )


def check_tesseract() -> DepStatus:
    try:
        from instantlensdoc.core.ocr import tesseract_available
    except Exception as e:
        return DepStatus(
            key="tesseract",
            label="OCR (Tesseract)",
            ok=False,
            critical=False,
            message=f"OCR-Modul nicht ladbar: {e}",
        )
    ok, msg = tesseract_available()
    return DepStatus(
        key="tesseract",
        label="OCR (Tesseract)",
        ok=bool(ok),
        critical=False,
        message=msg if msg else ("Tesseract verfügbar" if ok else "Tesseract fehlt"),
    )


def check_runtime_dependencies() -> List[DepStatus]:
    """Prüft kritische und optionale Laufzeit-Abhängigkeiten."""
    return [check_pypdfium2(), check_tesseract()]


def format_deps_summary(statuses: List[DepStatus] | None = None) -> str:
    """Klartext für Dialog/Status."""
    items = statuses if statuses is not None else check_runtime_dependencies()
    out: list[str] = []
    for s in items:
        if s.ok:
            first = (s.message or "").strip().splitlines()[0]
            out.append(f"• {s.label}: OK — {first}")
        else:
            level = "kritisch" if s.critical else "optional"
            out.append(f"• {s.label}: FEHLT ({level})")
            out.append((s.message or "").strip())
            out.append("")
    return "\n".join(out).rstrip()


def has_critical_failure(statuses: List[DepStatus] | None = None) -> bool:
    items = statuses if statuses is not None else check_runtime_dependencies()
    return any((not s.ok) and s.critical for s in items)


def has_any_failure(statuses: List[DepStatus] | None = None) -> bool:
    items = statuses if statuses is not None else check_runtime_dependencies()
    return any(not s.ok for s in items)
