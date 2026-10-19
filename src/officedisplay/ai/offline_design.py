from __future__ import annotations

import re
from typing import Any

from officedisplay.model.presentation import (
    Background,
    Presentation,
    Slide,
    SlideObject,
    blank_presentation,
    new_id,
)


_WORD = re.compile(r"[A-Za-zÄÖÜäöüß0-9%]+", re.UNICODE)


def _has(text: str, words: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(word in low for word in words)


def features(text: str) -> list[float]:
    tokens = _WORD.findall(text or "")
    length = min(len(text or "") / 200.0, 1.0)
    return [
        length,
        1.0 if re.search(r"\d", text or "") else 0.0,
        1.0 if _has(text, ("vergleich", "versus", "gegenüber", " vs ", "compare")) else 0.0,
        1.0 if _has(text, ("zeit", "ablauf", "schritt", "timeline", "prozess", "roadmap", "plan")) else 0.0,
        1.0 if _has(text, ("zitat", "sagte", "quote", "»", "«")) else 0.0,
        1.0 if _has(text, ("team", "personen", "vorstellung", "mitarbeit")) else 0.0,
        1.0 if _has(text, ("agenda", "inhalt", "gliederung", "overview")) else 0.0,
        1.0 if _has(text, ("kpi", "kennzahl", "umsatz", "prozent", "%", "diagramm", "chart")) else 0.0,
    ]


def softmax(values: list[float]) -> list[float]:
    peak = max(values) if values else 0.0
    exps = [pow(2.718281828, item - peak) for item in values]
    total = sum(exps) or 1.0
    return [item / total for item in exps]


# Klassen: title, bullets, two_col, chart, timeline, quote
WEIGHTS: list[list[float]] = [
    [-1.2, -0.4, -0.2, -0.3, -0.2, -0.2, 0.2, -0.6],
    [0.4, 0.1, 0.2, 0.1, -0.4, 0.3, 0.8, -0.2],
    [0.1, 0.2, 2.4, -0.2, -0.3, 0.4, 0.1, -0.4],
    [0.0, 1.6, 0.4, -0.2, -0.5, -0.2, -0.2, 2.6],
    [0.0, 0.1, -0.2, 2.8, -0.3, 0.1, 0.2, -0.2],
    [-0.2, -0.3, -0.2, -0.2, 3.2, 0.1, -0.2, -0.4],
]
BIAS = [0.15, 0.55, 0.05, 0.05, 0.05, 0.05]
CLASSES = ["title", "bullets", "two_col", "chart", "timeline", "quote"]


def logits(vector: list[float]) -> list[float]:
    out = []
    for row, bias in zip(WEIGHTS, BIAS):
        out.append(sum(value * weight for value, weight in zip(vector, row)) + bias)
    return out


def predict_layout(text: str) -> str:
    vector = features(text)
    scores = softmax(logits(vector))
    return CLASSES[max(range(len(scores)), key=scores.__getitem__)]


def _clauses(prompt: str) -> list[str]:
    parts = re.split(r"[\n.;]|(?:,\s+)|(?:\s+und\s+)", prompt)
    cleaned = []
    for part in parts:
        text = " ".join(part.split()).strip(" -–•")
        if len(text) >= 3:
            cleaned.append(text)
    return cleaned or [" ".join(prompt.split())]


def _text(
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    size: int,
    color: str,
    bold: bool = False,
    align: str = "left",
    name: str = "",
) -> SlideObject:
    return SlideObject(
        id=new_id(),
        kind="text",
        x=x,
        y=y,
        w=w,
        h=h,
        name=name,
        props={
            "text": text,
            "font_family": "Segoe UI",
            "font_size": size,
            "bold": bold,
            "italic": False,
            "underline": False,
            "color": color,
            "align": align,
        },
    )


def _shape(x, y, w, h, shape, fill, name="") -> SlideObject:
    return SlideObject(
        id=new_id(),
        kind="shape",
        x=x,
        y=y,
        w=w,
        h=h,
        name=name,
        props={"shape": shape, "fill": fill, "stroke": "#00000000", "stroke_width": 0},
    )


def generate_deck(prompt: str) -> Presentation:
    """Ein Satz wird zu einem abgestimmten Foliensatz.

    Es werden nur Formulierungen und Zahlen aus dem Satz verwendet. Fehlen
    Zahlen, bleibt das Diagramm leer und der Text nennt die fehlende Quelle.
    """
    prompt = " ".join((prompt or "").split())
    if not prompt:
        prompt = "Neue Präsentation"
    clauses = _clauses(prompt)
    title = clauses[0][:120]
    layout = predict_layout(prompt)
    presentation = blank_presentation()
    presentation.title = title[:80]
    presentation.slides = []

    cover = Slide(
        id=new_id(),
        name="Titel",
        background=Background(mode="gradient", color="#0B63E5", color2="#08357A", angle=140),
        notes=prompt,
    )
    cover.objects.append(_shape(0.08, 0.18, 0.12, 0.015, "rect", "#F28C28", "akzent"))
    cover.objects.append(_text(0.08, 0.28, 0.84, 0.28, title, 54, "#FFFFFF", True, "left", "titel"))
    cover.objects.append(_text(0.08, 0.62, 0.7, 0.12, "Office Display", 22, "#D6E4FF", False, "left", "untertitel"))
    presentation.slides.append(cover)

    agenda = Slide(
        id=new_id(),
        name="Agenda",
        background=Background(mode="solid", color="#F7F8FB"),
        notes="Gliederung aus dem Ausgangssatz.",
    )
    agenda.objects.append(_text(0.07, 0.08, 0.8, 0.12, "Ablauf", 36, "#1B1F2A", True, "left", "titel"))
    points = clauses[:6]
    agenda.objects.append(
        _text(0.08, 0.26, 0.8, 0.6, "\n".join(f"• {item}" for item in points), 26, "#243044", name="inhalt")
    )
    presentation.slides.append(agenda)

    body = Slide(
        id=new_id(),
        name="Inhalt",
        background=Background(mode="solid", color="#FFFFFF"),
        notes=prompt,
    )
    body.objects.append(_text(0.07, 0.07, 0.86, 0.12, title, 32, "#0B63E5", True, "left", "titel"))
    low = prompt.lower()
    numbers = [float(item.replace(",", ".")) for item in re.findall(r"\d+(?:[.,]\d+)?", prompt)]
    if any(word in low for word in ("kpi", "kennzahl")) and "diagramm" not in low and "chart" not in low:
        if numbers:
            for index, value in enumerate(numbers[:4]):
                label = clauses[min(index, len(clauses) - 1)][:42]
                body.objects.append(
                    SlideObject(
                        id=new_id(),
                        kind="kpi",
                        x=0.06 + index * 0.23,
                        y=0.28,
                        w=0.21,
                        h=0.28,
                        name=f"kpi{index}",
                        props={"value": str(value), "label": label, "color": "#0B63E5"},
                    )
                )
        else:
            body.objects.append(
                _text(0.08, 0.3, 0.8, 0.2, "Keine Kennzahl im Ausgangstext.", 24, "#1B1F2A", name="inhalt")
            )
    elif layout == "two_col":
        mid = max(1, len(clauses) // 2)
        left, right = clauses[:mid], clauses[mid:] or clauses[:1]
        body.objects.append(_shape(0.06, 0.24, 0.42, 0.62, "roundrect", "#F3F6FC"))
        body.objects.append(_shape(0.52, 0.24, 0.42, 0.62, "roundrect", "#FFF6EC"))
        body.objects.append(_text(0.08, 0.28, 0.38, 0.54, "\n".join(left), 22, "#1B1F2A", name="links"))
        body.objects.append(_text(0.54, 0.28, 0.38, 0.54, "\n".join(right), 22, "#1B1F2A", name="rechts"))
    elif layout == "quote":
        body.objects.append(_text(0.1, 0.28, 0.8, 0.4, clauses[0], 36, "#1B1F2A", False, "left", "zitat"))
        body.objects[-1].props["italic"] = True
    elif layout == "timeline":
        body.objects.append(_shape(0.08, 0.48, 0.84, 0.012, "rect", "#0B63E5", "linie"))
        for index, clause in enumerate(clauses[:4]):
            x = 0.08 + index * 0.22
            body.objects.append(_shape(x, 0.45, 0.04, 0.07, "ellipse", "#F28C28", f"punkt{index}"))
            body.objects.append(_text(x - 0.02, 0.56, 0.2, 0.22, clause, 16, "#1B1F2A", name=f"schritt{index}"))
    elif layout == "chart":
        if numbers:
            body.objects.append(
                SlideObject(
                    id=new_id(),
                    kind="chart",
                    x=0.08,
                    y=0.24,
                    w=0.84,
                    h=0.62,
                    name="diagramm",
                    props={
                        "chart_type": "bar",
                        "categories": [f"Wert {i + 1}" for i in range(len(numbers[:6]))],
                        "series": [{"name": "Quelle", "values": numbers[:6]}],
                        "example": False,
                    },
                )
            )
        else:
            body.objects.append(
                _text(0.08, 0.32, 0.8, 0.2, "Keine Zahlen im Ausgangstext.", 24, "#1B1F2A", name="inhalt")
            )
    else:
        bullets = clauses if len(clauses) > 1 else [prompt]
        body.objects.append(
            _text(0.08, 0.24, 0.84, 0.62, "\n".join(f"• {item}" for item in bullets[:6]), 26, "#1B1F2A", name="inhalt")
        )
    presentation.slides.append(body)

    close = Slide(
        id=new_id(),
        name="Abschluss",
        background=Background(mode="gradient", color="#1B1F2A", color2="#0B63E5"),
        notes="Abschluss ohne zusätzliche Behauptungen.",
    )
    close.objects.append(_text(0.08, 0.32, 0.84, 0.16, "Abschluss", 40, "#FFFFFF", True, "left", "titel"))
    close.objects.append(_text(0.08, 0.52, 0.8, 0.16, clauses[-1], 24, "#D6E4FF", name="inhalt"))
    presentation.slides.append(close)
    _apply_guardrails(presentation)
    return presentation


def estimate_font(text: str, box_w: float, box_h: float, slide_h: int, current: int) -> int:
    """Schrift verkleinern, bis der Text grob in den Rahmen passt."""
    size = max(10, int(current))
    chars_per_line = max(8, int(box_w * slide_h * 0.055 * (28 / size)))
    lines = 0
    for paragraph in (text or "").splitlines() or [""]:
        lines += max(1, (len(paragraph) + chars_per_line - 1) // chars_per_line)
    line_px = size * 1.35
    while lines * line_px > box_h * slide_h and size > 12:
        size -= 1
        chars_per_line = max(8, int(box_w * slide_h * 0.055 * (28 / size)))
        lines = 0
        for paragraph in (text or "").splitlines() or [""]:
            lines += max(1, (len(paragraph) + chars_per_line - 1) // chars_per_line)
        line_px = size * 1.35
    return size


def _apply_guardrails(presentation: Presentation) -> None:
    for slide in presentation.slides:
        for obj in slide.objects:
            if obj.kind != "text":
                continue
            text = str(obj.props.get("text") or "")
            bullets = [line for line in text.splitlines() if line.strip()]
            if len(bullets) > 6:
                obj.props["text"] = "\n".join(bullets[:6])
                text = obj.props["text"]
            obj.props["font_size"] = estimate_font(
                text, obj.w, obj.h, presentation.height, int(obj.props.get("font_size") or 24)
            )


def deck_from_outline(slides: list[dict[str, Any]], title: str) -> Presentation:
    presentation = blank_presentation()
    presentation.title = title or "Dokument"
    presentation.slides = []
    for index, item in enumerate(slides):
        slide = Slide(
            id=new_id(),
            name=item.get("title") or f"Folie {index + 1}",
            background=Background(mode="solid", color="#FFFFFF" if index else "#0B63E5"),
            notes=item.get("notes") or "",
        )
        color = "#FFFFFF" if index == 0 else "#1B1F2A"
        title_color = "#FFFFFF" if index == 0 else "#0B63E5"
        slide.objects.append(
            _text(0.07, 0.08, 0.86, 0.14, item.get("title") or "", 34, title_color, True, name="titel")
        )
        bullets = item.get("bullets") or []
        if bullets:
            slide.objects.append(
                _text(
                    0.08,
                    0.28,
                    0.84,
                    0.6,
                    "\n".join(f"• {line}" for line in bullets),
                    24,
                    color if index == 0 else "#243044",
                    name="inhalt",
                )
            )
        presentation.slides.append(slide)
    if not presentation.slides:
        presentation.slides.append(Slide(id=new_id(), name="Leer"))
    _apply_guardrails(presentation)
    return presentation
