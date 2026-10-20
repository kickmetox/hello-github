from __future__ import annotations

"""Reine Zeigerlogik für Maus, Stift, Radierer und Touch.

Qt liefert die Rohereignisse. Diese Funktionen entscheiden, welche Aktion
ausgeführt wird, und bauen druckabhängige Striche. Dadurch ist die Bedienung
ohne Grafiktablet testbar.
"""

from dataclasses import dataclass, field


CREATE_TOOLS = {"text", "chart", "rect", "ellipse", "roundrect", "triangle", "diamond", "star", "arrow", "line"}


def interpret_pointer(tool: str, pointer_kind: str, touch_mode: str) -> str:
    """Aktion: draw, erase, pan, select, create.

    Stift zeichnet im Stiftwerkzeug und radiert, wenn die Radiererseite
    aufliegt. Touch zeichnet nur im Modus „Zeichnen“. Text- und Formwerkzeuge
    legen ein Objekt an, auch mit dem Finger. Die Maus folgt dem aktiven Werkzeug.
    """
    if pointer_kind == "eraser":
        return "erase"
    if pointer_kind == "pen":
        if tool == "eraser":
            return "erase"
        if tool in {"pen", "highlighter"}:
            return "draw"
        if tool in CREATE_TOOLS:
            return "create"
        return "select"
    if pointer_kind == "touch":
        if touch_mode == "draw" and tool == "eraser":
            return "erase"
        if touch_mode == "draw" and tool in {"pen", "highlighter"}:
            return "draw"
        if tool in CREATE_TOOLS:
            return "create"
        if touch_mode == "pan":
            return "pan"
        return "select"
    if tool in {"pen", "highlighter"}:
        return "draw"
    if tool == "eraser":
        return "erase"
    if tool == "pan":
        return "pan"
    if tool in CREATE_TOOLS:
        return "create"
    return "select"


def stroke_width(base: float, pressure: float, curve: float, pointer_kind: str) -> float:
    curve = max(0.2, min(curve, 4.0))
    if pointer_kind == "pen":
        amount = max(0.02, min(float(pressure), 1.0))
    elif pointer_kind == "touch":
        amount = max(0.35, min(float(pressure or 0.55), 1.0))
    else:
        amount = 0.72
    return max(0.4, base * (0.22 + 0.78 * (amount**curve)))


def smooth_points(points: list[tuple[float, float, float]], passes: int = 1) -> list[tuple[float, float, float]]:
    """Gleitender Mittelwert. Endpunkte bleiben stehen, der Druck ebenso."""
    current = list(points)
    passes = max(0, min(int(passes), 6))
    for _ in range(passes):
        if len(current) < 3:
            break
        nxt = [current[0]]
        for index in range(1, len(current) - 1):
            ax, ay, ap = current[index - 1]
            bx, by, bp = current[index]
            cx, cy, cp = current[index + 1]
            nxt.append(((ax + bx + cx) / 3.0, (ay + by + cy) / 3.0, bp))
        nxt.append(current[-1])
        current = nxt
    return current


@dataclass
class StrokeBuilder:
    base_width: float = 6.0
    curve: float = 1.0
    smooth_passes: int = 1
    pointer_kind: str = "pen"
    points: list[tuple[float, float, float]] = field(default_factory=list)

    def add(self, x: float, y: float, pressure: float) -> None:
        if self.points:
            px, py, _pp = self.points[-1]
            if abs(px - x) < 1e-4 and abs(py - y) < 1e-4:
                return
        self.points.append((x, y, max(0.0, min(float(pressure), 1.0))))

    def widths(self) -> list[float]:
        smoothed = smooth_points(self.points, self.smooth_passes)
        return [
            stroke_width(self.base_width, pressure, self.curve, self.pointer_kind)
            for _x, _y, pressure in smoothed
        ]

    def finish(self) -> list[tuple[float, float, float]]:
        return smooth_points(self.points, self.smooth_passes)


def device_kind_from_name(device_name: str, pointer_name: str = "") -> str:
    blob = f"{device_name} {pointer_name}".lower()
    if "eraser" in blob or "radier" in blob:
        return "eraser"
    if "stylus" in blob or "pen" in blob or "tablet" in blob:
        return "pen"
    if "finger" in blob or "touch" in blob:
        return "touch"
    return "mouse"
