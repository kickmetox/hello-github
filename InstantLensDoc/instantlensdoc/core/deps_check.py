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
        import tempfile
        from pathlib import Path

        import pypdfium2 as pdfium  # noqa: F401

        from ild_pdf.render import render_page

        ver = getattr(pdfium, "__version__", None) or ""
        # Import reicht nicht: Frozen/EXE ohne pdfium.dll importiert oft noch
        # das Python-Paket, rendert aber weiß/leer. Mini-Render prüft Binary — 2.6.49
        mini = (
            b"%PDF-1.4\n"
            b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n"
            b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n"
            b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
            b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n"
            b"4 0 obj<< /Length 44 >>stream\n"
            b"BT /F1 24 Tf 40 100 Td (OK) Tj ET\n"
            b"endstream\nendobj\n"
            b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
            b"xref\n0 6\n0000000000 65535 f \n"
            b"trailer<< /Size 6 /Root 1 0 R >>\nstartxref\n0\n%%EOF\n"
        )
        with tempfile.TemporaryDirectory() as td:
            pdf = Path(td) / "deps_pdfium_probe.pdf"
            pdf.write_bytes(mini)
            img = render_page(pdf, 0, scale=1.0, use_cache=False)
            if img is None or int(getattr(img, "width", 0) or 0) < 8:
                raise RuntimeError("Render lieferte kein Bild (pdfium Binary fehlt?)")
            # Mindestens etwas Nicht-Weiß (Text „OK“)
            rgb = img.convert("RGB")
            ink = 0
            for y in range(0, rgb.height, 6):
                for x in range(0, rgb.width, 6):
                    r, g, b = rgb.getpixel((x, y))
                    if r < 250 or g < 250 or b < 250:
                        ink += 1
                        if ink >= 3:
                            break
                if ink >= 3:
                    break
            if ink < 3:
                raise RuntimeError("Render ohne Tinte (weißes Ghost-Pixmap)")
        detail = f"pypdfium2 {ver} (Render OK)".strip() if ver else "pypdfium2 verfügbar (Render OK)"
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
                "pypdfium2 fehlt, pdfium-Binary fehlt, oder Render fehlgeschlagen.\n"
                "Installieren: pip install pypdfium2\n"
                "Frozen-Build: --collect-all pypdfium2 / Spec collect_all.\n\n"
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
