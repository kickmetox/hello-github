from __future__ import annotations

from officedisplay.model.presentation import Background, Slide, SlideObject, new_id


def _text(x, y, w, h, text, size, color, bold=False, name="") -> SlideObject:
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
            "align": "left",
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


TEMPLATES = {
    "Pitch": "pitch",
    "Unterricht": "lesson",
    "Kennzahlen": "kpi",
    "Zitat": "quote",
    "Vergleich": "compare",
    "Team": "team",
    "Titel mit Fläche": "cover",
}


def apply_template(presentation, key: str) -> None:
    kind = TEMPLATES.get(key, key)
    presentation.slides = []
    builders = {
        "pitch": _pitch,
        "lesson": _lesson,
        "kpi": _kpi,
        "quote": _quote,
        "compare": _compare,
        "team": _team,
        "cover": _cover,
    }
    builders.get(kind, _cover)(presentation)


def _cover(presentation) -> None:
    slide = Slide(id=new_id(), name="Titel", background=Background(mode="gradient", color="#0B63E5", color2="#F28C28"))
    slide.objects.append(_text(0.08, 0.34, 0.8, 0.2, presentation.title or "Titel", 60, "#FFFFFF", True, "titel"))
    slide.objects.append(_text(0.08, 0.58, 0.6, 0.1, "Untertitel", 24, "#FFF6EC", name="untertitel"))
    presentation.slides.append(slide)


def _pitch(presentation) -> None:
    _cover(presentation)
    problem = Slide(id=new_id(), name="Problem", background=Background(color="#FFFFFF"))
    problem.objects += [
        _text(0.07, 0.08, 0.8, 0.12, "Problem", 36, "#0B63E5", True, "titel"),
        _text(0.08, 0.28, 0.8, 0.5, "• Ausgangslage\n• Reibung\n• Folge", 28, "#1B1F2A", name="inhalt"),
    ]
    solution = Slide(id=new_id(), name="Ansatz", background=Background(color="#F7F8FB"))
    solution.objects += [
        _text(0.07, 0.08, 0.8, 0.12, "Ansatz", 36, "#0B63E5", True, "titel"),
        _shape(0.08, 0.3, 0.25, 0.4, "roundrect", "#0B63E5"),
        _shape(0.37, 0.3, 0.25, 0.4, "roundrect", "#F28C28"),
        _shape(0.66, 0.3, 0.25, 0.4, "roundrect", "#3CB44B"),
    ]
    presentation.slides += [problem, solution]


def _lesson(presentation) -> None:
    slide = Slide(id=new_id(), name="Lernziel", background=Background(color="#FFFFFF"))
    slide.objects += [
        _shape(0, 0, 1, 0.08, "rect", "#0B63E5"),
        _text(0.07, 0.16, 0.8, 0.12, "Lernziel", 36, "#1B1F2A", True, "titel"),
        _text(0.08, 0.34, 0.84, 0.5, "• Begriff\n• Beispiel\n• Übung", 28, "#243044", name="inhalt"),
    ]
    presentation.slides.append(slide)


def _kpi(presentation) -> None:
    slide = Slide(id=new_id(), name="Kennzahlen", background=Background(color="#F4F6FB"))
    slide.objects.append(_text(0.06, 0.06, 0.8, 0.1, "Kennzahlen", 34, "#1B1F2A", True, "titel"))
    colors = ["#0B63E5", "#F28C28", "#3CB44B"]
    for index, color in enumerate(colors):
        x = 0.06 + index * 0.31
        slide.objects.append(_shape(x, 0.24, 0.28, 0.28, "roundrect", color, f"kpi{index}"))
        slide.objects.append(_text(x + 0.02, 0.3, 0.24, 0.12, "–", 36, "#FFFFFF", True, f"wert{index}"))
    slide.objects.append(
        SlideObject(
            id=new_id(),
            kind="chart",
            x=0.06,
            y=0.58,
            w=0.88,
            h=0.34,
            name="diagramm",
            props={
                "chart_type": "bar",
                "categories": ["A", "B", "C"],
                "series": [{"name": "Beispielwerte – ersetzen", "values": [3, 5, 4]}],
                "example": True,
            },
        )
    )
    presentation.slides.append(slide)


def _quote(presentation) -> None:
    slide = Slide(id=new_id(), name="Zitat", background=Background(mode="solid", color="#1B1F2A"))
    slide.objects.append(_text(0.1, 0.28, 0.8, 0.3, "Zitat einsetzen", 40, "#FFFFFF", False, "zitat"))
    slide.objects[-1].props["italic"] = True
    slide.objects.append(_text(0.1, 0.64, 0.6, 0.1, "Quelle", 20, "#F28C28", name="quelle"))
    presentation.slides.append(slide)


def _compare(presentation) -> None:
    slide = Slide(id=new_id(), name="Vergleich", background=Background(color="#FFFFFF"))
    slide.objects += [
        _text(0.06, 0.06, 0.8, 0.1, "Vergleich", 34, "#1B1F2A", True, "titel"),
        _shape(0.06, 0.22, 0.42, 0.68, "roundrect", "#E8F0FF"),
        _shape(0.52, 0.22, 0.42, 0.68, "roundrect", "#FFF1E4"),
        _text(0.08, 0.26, 0.38, 0.1, "Option A", 24, "#0B63E5", True, "links"),
        _text(0.54, 0.26, 0.38, 0.1, "Option B", 24, "#C46A10", True, "rechts"),
    ]
    presentation.slides.append(slide)


def _team(presentation) -> None:
    slide = Slide(id=new_id(), name="Team", background=Background(color="#FFFFFF"))
    slide.objects.append(_text(0.06, 0.06, 0.8, 0.1, "Team", 34, "#1B1F2A", True, "titel"))
    for index in range(3):
        x = 0.08 + index * 0.3
        slide.objects.append(_shape(x + 0.06, 0.24, 0.14, 0.2, "ellipse", "#0B63E5", f"person{index}"))
        slide.objects.append(_text(x, 0.48, 0.26, 0.12, "Name", 20, "#1B1F2A", True, f"name{index}"))
    presentation.slides.append(slide)


def element(kind: str) -> SlideObject:
    catalog = {
        "Rahmen": _shape(0.08, 0.08, 0.3, 0.3, "roundrect", "#00000000"),
        "Fläche": _shape(0.1, 0.1, 0.28, 0.18, "roundrect", "#0B63E5"),
        "Kreis": _shape(0.12, 0.12, 0.18, 0.18, "ellipse", "#F28C28"),
        "Raute": _shape(0.12, 0.12, 0.18, 0.18, "diamond", "#3CB44B"),
        "Stern": _shape(0.12, 0.12, 0.18, 0.18, "star", "#E23B3B"),
        "Pfeil": _shape(0.1, 0.2, 0.4, 0.12, "arrow", "#0B63E5"),
        "Badge": _shape(0.1, 0.1, 0.22, 0.08, "roundrect", "#1B1F2A"),
    }
    obj = catalog.get(kind, catalog["Fläche"]).clone()
    if kind == "Rahmen":
        obj.props["fill"] = "#00000000"
        obj.props["stroke"] = "#0B63E5"
        obj.props["stroke_width"] = 4
    if kind == "Badge":
        obj.children = []
        obj.name = "badge"
    obj.name = obj.name or kind.lower()
    return obj
