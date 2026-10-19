from __future__ import annotations

import re

from officedisplay.ai.offline_design import deck_from_outline


def _lines(text: str) -> list[tuple[int, str]]:
    result = []
    for index, raw in enumerate((text or "").splitlines(), start=1):
        line = raw.strip()
        if line:
            result.append((index, line))
    return result


def outline_from_text(text: str) -> list[dict]:
    """Gliederung nur aus dem gelieferten Text, mit Zeilennummer als Quelle."""
    sections: list[dict] = []
    current: dict | None = None
    for line_no, line in _lines(text):
        is_heading = line.startswith("#") or (len(line) < 80 and not line.endswith(".") and len(line.split()) <= 10)
        if is_heading and (line.startswith("#") or current is None or len(current["points"]) >= 6):
            title = line.lstrip("#").strip()
            current = {"title": title, "points": [], "source_line": line_no}
            sections.append(current)
            continue
        if current is None:
            current = {"title": line[:80], "points": [], "source_line": line_no}
            sections.append(current)
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            sentence = sentence.strip()
            if sentence:
                current["points"].append({"text": sentence, "source_line": line_no})
    return sections


def slides_from_text(text: str, title: str = "Dokument"):
    sections = outline_from_text(text)
    payload = []
    for section in sections:
        bullets = [point["text"] for point in section["points"][:8]]
        sources = sorted({point["source_line"] for point in section["points"]})
        notes = "Quelle Zeilen: " + ", ".join(str(item) for item in sources) if sources else f"Quelle Zeile {section['source_line']}"
        if not bullets:
            bullets = [section["title"]]
            notes = f"Quelle Zeile {section['source_line']}"
        payload.append({"title": section["title"], "bullets": bullets, "notes": notes})
    if not payload:
        payload.append({"title": title, "bullets": ["Leeres Dokument"], "notes": "Keine Textquelle"})
    return deck_from_outline(payload, title)


def read_text_file(path: str) -> str:
    suffix = path.lower().rsplit(".", 1)[-1]
    if suffix == "pdf":
        from pypdf import PdfReader

        reader = PdfReader(path)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()
