"""DTP-Preflight: fehlende Schriften, Low-Res-Bilder, vor dem Export."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PreflightIssue:
    kind: str  # font | image | color | other
    message: str
    frame_id: str = ""
    severity: str = "warning"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "message": self.message,
            "frame_id": self.frame_id,
            "severity": self.severity,
        }


@dataclass
class PreflightReport:
    ok: bool = True
    issues: list[PreflightIssue] = field(default_factory=list)
    min_dpi: float = 150.0

    def to_text(self) -> str:
        if not self.issues:
            return "Preflight: keine Beanstandungen."
        lines = [f"Preflight: {len(self.issues)} Hinweis(e)"]
        for i in self.issues:
            lines.append(f"- [{i.severity}] {i.kind}: {i.message}")
        return "\n".join(lines)


def run_dtp_preflight(doc: Any, *, min_dpi: float = 150.0) -> PreflightReport:
    report = PreflightReport(min_dpi=float(min_dpi))
    known = _font_families()
    for fr in getattr(doc, "frames", []):
        if fr.kind == "text":
            fam = (fr.font_family or "").strip()
            style = (doc.styles.get(fr.style_id) if getattr(doc, "styles", None) else None)
            if not fam and style is not None:
                fam = style.font_family or ""
            if fam and fam.lower() not in ("serif", "sans", "monospace") and known and fam not in known:
                report.issues.append(
                    PreflightIssue("font", f"Schrift fehlt: {fam}", fr.id, "error")
                )
        if fr.kind in ("image", "render") and fr.image_path:
            dpi = _effective_dpi(fr)
            if dpi is not None and dpi < min_dpi:
                report.issues.append(
                    PreflightIssue(
                        "image",
                        f"Auflösung {dpi:.0f} ppi < {min_dpi:.0f} ppi ({Path(fr.image_path).name})",
                        fr.id,
                        "warning",
                    )
                )
            if fr.image_path and not Path(fr.image_path).is_file():
                report.issues.append(
                    PreflightIssue("image", f"Bilddatei fehlt: {fr.image_path}", fr.id, "error")
                )
    report.ok = not any(i.severity == "error" for i in report.issues)
    return report


def _font_families() -> set[str]:
    try:
        from PySide6.QtGui import QFontDatabase

        return set(str(f) for f in QFontDatabase.families())
    except Exception:
        return set()


def _effective_dpi(fr: Any) -> float | None:
    path = Path(getattr(fr, "image_path", "") or "")
    if not path.is_file():
        return None
    try:
        from PIL import Image

        with Image.open(path) as im:
            w_px, h_px = im.size
    except Exception:
        try:
            from PySide6.QtGui import QImage

            im = QImage(str(path))
            if im.isNull():
                return None
            w_px, h_px = im.width(), im.height()
        except Exception:
            return None
    w_in = max(0.01, float(fr.width) / 72.0)
    return float(w_px) / w_in
