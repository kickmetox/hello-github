"""Navigation des Präsentations- und Slideshow-Players, ohne Anzeige."""

from __future__ import annotations


def navigate_player(index: int, count: int, blank: str, key: str) -> dict:
    """Nächster und vorheriger Index, Blende, Notizleiste, Ende.

    `blank` ist "", "black" oder "white".
    `key` ist ein Befehl oder eine Taste: next/right/space/pagedown, prev/left/pageup,
    home, end, escape, b/period, w, n, click.

    Rückgabe: index, blank, exit, toggle_notes, run_click.
    Ein Klick führt Objektaktionen nur aus, wenn keine Blende aktiv ist.
    """
    name = (key or "").strip().lower().replace(" ", "")
    current = blank if blank in {"black", "white"} else ""
    result = {
        "index": index if count <= 0 else max(0, min(count - 1, index)),
        "blank": current,
        "exit": False,
        "toggle_notes": False,
        "run_click": False,
    }
    if name in {"escape", "esc"}:
        result["exit"] = True
        return result
    if count <= 0:
        result["index"] = 0
        return result
    if name in {"b", "black", "schwarz", "period", ".", "punkt"}:
        result["blank"] = "" if current == "black" else "black"
        return result
    if name in {"w", "white", "weiss", "weiß"}:
        result["blank"] = "" if current == "white" else "white"
        return result
    if name in {"n", "notes", "notiz", "notizen"}:
        result["toggle_notes"] = True
        return result
    if name in {"home", "pos1", "first", "anfang"}:
        result["index"] = 0
        return result
    if name in {"end", "ende", "last"}:
        result["index"] = count - 1
        return result
    if name in {"prev", "previous", "left", "arrowleft", "pageup", "bildauf", "zurück", "zurueck"}:
        result["index"] = max(0, index - 1)
        return result
    if name in {"click", "klick"}:
        if current:
            result["index"] = min(count - 1, index + 1)
        else:
            result["run_click"] = True
        return result
    if name in {"next", "right", "arrowright", "space", "leertaste", "pagedown", "bildab", "weiter"}:
        result["index"] = min(count - 1, index + 1)
        return result
    return result
