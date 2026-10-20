from __future__ import annotations

import re

from officedisplay.model.presentation import Presentation, Slide, SlideObject, new_id


def _numbers(text: str) -> list[float]:
    found = []
    for raw in re.findall(r"\d+(?:[.,]\d+)?", text):
        found.append(float(raw.replace(",", ".")))
    return found


def apply_command(presentation: Presentation, slide: Slide, command: str) -> str:
    """Kleine Offline-Grammatik für Gestaltungsbefehle. Kein Netz."""
    text = " ".join((command or "").lower().split())
    if not text:
        return "Kein Befehl."
    if any(word in text for word in ("dunkl", "dark")):
        slide.background.mode = "gradient"
        slide.background.color = "#1B1F2A"
        slide.background.color2 = "#0B63E5"
        return "Hintergrund abgedunkelt."
    if any(word in text for word in ("hell", "light", "weiß", "weiss")):
        slide.background.mode = "solid"
        slide.background.color = "#FFFFFF"
        return "Hintergrund aufgehellt."
    if "zwei spalt" in text or "two col" in text or "2 spalt" in text:
        return _two_columns(slide)
    if "diagramm" in text or "chart" in text:
        return _chart(slide)
    if "zeit" in text or "timeline" in text:
        return _timeline(slide)
    if "größer" in text or "groesser" in text or "larger" in text:
        _scale_fonts(slide, 1.15)
        return "Schrift vergrößert."
    if "kleiner" in text or "smaller" in text:
        _scale_fonts(slide, 0.85)
        return "Schrift verkleinert."
    if "zentrier" in text or "center" in text:
        for obj in slide.objects:
            if obj.kind == "text":
                obj.props["align"] = "center"
        return "Text zentriert."
    if "folie" in text and ("neu" in text or "hinzu" in text or "add" in text):
        presentation.slides.append(Slide(id=new_id(), name=f"Folie {len(presentation.slides) + 1}"))
        return "Folie hinzugefügt."
    return "Befehl nicht erkannt. Beispiele: zwei spalten, diagramm, dunkler hintergrund, größer."


def _scale_fonts(slide: Slide, factor: float) -> None:
    for obj in slide.objects:
        if obj.kind == "text":
            size = int(obj.props.get("font_size") or 24)
            obj.props["font_size"] = max(10, min(96, int(size * factor)))


def _blob(slide: Slide) -> str:
    parts = []
    for obj in slide.objects:
        if obj.kind == "text":
            parts.append(str(obj.props.get("text") or ""))
    return "\n".join(parts)


def _two_columns(slide: Slide) -> str:
    lines = [line.strip("• ").strip() for line in _blob(slide).splitlines() if line.strip()]
    if len(lines) < 2:
        lines = lines + ["Zweiter Punkt"]
    mid = max(1, len(lines) // 2)
    slide.objects = [
        obj
        for obj in slide.objects
        if not (obj.kind == "text" and obj.name in {"inhalt", "links", "rechts"})
    ]
    slide.objects.append(
        SlideObject(
            id=new_id(),
            kind="text",
            x=0.06,
            y=0.28,
            w=0.4,
            h=0.6,
            name="links",
            props={"text": "\n".join(lines[:mid]), "font_size": 22, "color": "#1B1F2A", "font_family": "Segoe UI"},
        )
    )
    slide.objects.append(
        SlideObject(
            id=new_id(),
            kind="text",
            x=0.52,
            y=0.28,
            w=0.4,
            h=0.6,
            name="rechts",
            props={"text": "\n".join(lines[mid:]), "font_size": 22, "color": "#1B1F2A", "font_family": "Segoe UI"},
        )
    )
    return "Zwei Spalten angelegt."


def _chart(slide: Slide) -> str:
    values = _numbers(_blob(slide))
    if not values:
        return "Keine Zahlen auf der Folie. Es wurden keine Beispielwerte eingesetzt."
    slide.objects.append(
        SlideObject(
            id=new_id(),
            kind="chart",
            x=0.1,
            y=0.3,
            w=0.8,
            h=0.55,
            name="diagramm",
            props={
                "chart_type": "bar",
                "categories": [f"P{i + 1}" for i in range(len(values[:8]))],
                "series": [{"name": "Werte", "values": values[:8]}],
                "example": False,
            },
        )
    )
    return "Diagramm eingefügt."


def _timeline(slide: Slide) -> str:
    lines = [line.strip("• ").strip() for line in _blob(slide).splitlines() if line.strip()][:4] or ["Start"]
    slide.objects.append(
        SlideObject(
            id=new_id(),
            kind="shape",
            x=0.08,
            y=0.5,
            w=0.84,
            h=0.01,
            name="linie",
            props={"shape": "rect", "fill": "#0B63E5", "stroke": "#00000000", "stroke_width": 0},
        )
    )
    for index, line in enumerate(lines):
        slide.objects.append(
            SlideObject(
                id=new_id(),
                kind="text",
                x=0.08 + index * 0.22,
                y=0.56,
                w=0.2,
                h=0.2,
                name=f"schritt{index}",
                props={"text": line, "font_size": 16, "color": "#1B1F2A", "font_family": "Segoe UI"},
            )
        )
    return "Zeitstrahl ergänzt."
