"""Automatische Formatierung, Inhaltsverzeichnis, Systemfonts, Find/Replace — 2.6.10.

Heuristiken für Überschriften/Fließtext (Schriftgröße, Markdown-Präfixe, ALL CAPS)
plus Style-Presets. TOC → PDF-Outline (Sidebar „Inhaltsverzeichnis“) bzw. Markdown.
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence

from .outline import OutlineItem, extract_outline, write_outline
from .overlay import extract_text_blocks
from .pages import page_count as pdf_page_count


STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "heading1": {
        "name": "Überschrift 1",
        "markdown_prefix": "# ",
        "font_family": "Helvetica",
        "font_size": 22.0,
        "bold": True,
        "italic": False,
        "level": 1,
        "alignment": "left",
        "line_spacing": 1.15,
        "space_before_pt": 14.0,
        "space_after_pt": 8.0,
        "first_line_indent_pt": 0.0,
    },
    "heading2": {
        "name": "Überschrift 2",
        "markdown_prefix": "## ",
        "font_family": "Helvetica",
        "font_size": 16.0,
        "bold": True,
        "italic": False,
        "level": 2,
        "alignment": "left",
        "line_spacing": 1.15,
        "space_before_pt": 12.0,
        "space_after_pt": 6.0,
        "first_line_indent_pt": 0.0,
    },
    "heading3": {
        "name": "Überschrift 3",
        "markdown_prefix": "### ",
        "font_family": "Helvetica",
        "font_size": 13.0,
        "bold": True,
        "italic": False,
        "level": 3,
        "alignment": "left",
        "line_spacing": 1.15,
        "space_before_pt": 10.0,
        "space_after_pt": 4.0,
        "first_line_indent_pt": 0.0,
    },
    "body": {
        "name": "Fließtext",
        "markdown_prefix": "",
        "font_family": "Helvetica",
        "font_size": 11.0,
        "bold": False,
        "italic": False,
        "level": 0,
        "alignment": "justify",
        "line_spacing": 1.15,
        "space_before_pt": 0.0,
        "space_after_pt": 6.0,
        "first_line_indent_pt": 0.0,
    },
    "quote": {
        "name": "Zitat",
        "markdown_prefix": "> ",
        "font_family": "Times-Roman",
        "font_size": 11.0,
        "bold": False,
        "italic": True,
        "level": 0,
        "alignment": "left",
        "line_spacing": 1.5,
        "space_before_pt": 8.0,
        "space_after_pt": 8.0,
        "first_line_indent_pt": 0.0,
    },
}

_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_NUM_HEADING_RE = re.compile(r"^(\d{1,3}(?:\.\d{1,3}){0,3})\.?\s+(.{2,120})$")
_ALL_CAPS_RE = re.compile(r"^[A-ZÄÖÜ0-9][A-ZÄÖÜ0-9\s\-–—:.,!?]{1,79}$")


@dataclass
class HeadingCandidate:
    """Erkannte Überschrift (Text oder PDF)."""

    title: str
    level: int
    page_index: Optional[int] = None
    style_id: str = "heading1"
    source: str = "heuristic"  # markdown | font_size | all_caps | numbered | preset
    font_size: float = 0.0
    line_index: int = -1
    x: float = 0.0
    y: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AutoFormatResult:
    """Ergebnis von auto_format_text / auto_format_pdf."""

    text: str = ""
    headings: List[HeadingCandidate] = field(default_factory=list)
    changed_lines: int = 0
    outline_written: bool = False
    outline_count: int = 0
    path: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "headings": [h.to_dict() for h in self.headings],
            "changed_lines": self.changed_lines,
            "outline_written": self.outline_written,
            "outline_count": self.outline_count,
            "path": self.path,
        }


def list_style_presets() -> list[dict[str, Any]]:
    """Alle Style-Presets als Liste von Dicts."""
    out: list[dict[str, Any]] = []
    for sid, preset in STYLE_PRESETS.items():
        row = dict(preset)
        row["id"] = sid
        out.append(row)
    return out


def get_style_preset(style_id: str) -> dict[str, Any]:
    key = (style_id or "body").strip().lower()
    aliases = {
        "h1": "heading1",
        "h2": "heading2",
        "h3": "heading3",
        "title": "heading1",
        "heading": "heading1",
        "fließtext": "body",
        "fliessetext": "body",
        "normal": "body",
        "zitat": "quote",
    }
    key = aliases.get(key, key)
    if key not in STYLE_PRESETS:
        raise ValueError(f"Unbekanntes Style-Preset: {style_id!r}")
    row = dict(STYLE_PRESETS[key])
    row["id"] = key
    return row


def _strip_md_prefix(line: str) -> tuple[int, str]:
    m = _MD_HEADING_RE.match(line.rstrip())
    if m:
        return len(m.group(1)), (m.group(2) or "").strip()
    if line.startswith("> "):
        return 0, line[2:].strip()
    return 0, line.strip()


def classify_line_style(line: str, *, median_font: float = 11.0, font_size: float = 0.0) -> str:
    """Heuristik: Style-ID für eine Textzeile."""
    raw = (line or "").rstrip()
    if not raw.strip():
        return "body"
    md_level, title = _strip_md_prefix(raw)
    if md_level >= 1:
        return f"heading{min(md_level, 3)}"
    if raw.startswith("> ") or (raw.startswith(">") and not raw.startswith(">>")):
        return "quote"
    text = title or raw.strip()
    if font_size > 0 and median_font > 0:
        if font_size >= median_font * 1.55:
            return "heading1"
        if font_size >= median_font * 1.28:
            return "heading2"
        if font_size >= median_font * 1.12 and len(text) <= 80:
            return "heading3"
    if _NUM_HEADING_RE.match(text) and len(text) <= 100:
        return "heading2"
    letters = [c for c in text if c.isalpha()]
    if (
        letters
        and len(text) <= 72
        and sum(1 for c in letters if c.isupper()) / len(letters) >= 0.85
        and _ALL_CAPS_RE.match(text)
    ):
        return "heading1"
    if len(text) <= 60 and text.endswith(":") and not text.endswith("::"):
        return "heading3"
    return "body"


def detect_headings_in_text(text: str) -> list[HeadingCandidate]:
    """Überschriften in Plain-/Markdown-Text erkennen."""
    headings: list[HeadingCandidate] = []
    for i, line in enumerate((text or "").splitlines()):
        style_id = classify_line_style(line)
        if not style_id.startswith("heading"):
            continue
        level = int(style_id[-1]) if style_id[-1].isdigit() else 1
        _, title = _strip_md_prefix(line)
        if not title:
            continue
        md_level, _ = _strip_md_prefix(line)
        source = "markdown" if md_level else "heuristic"
        headings.append(
            HeadingCandidate(
                title=title,
                level=level,
                style_id=style_id,
                source=source,
                line_index=i,
            )
        )
    return headings


def apply_style_to_line(line: str, style_id: str) -> str:
    """Zeile auf Style-Preset (Markdown-Präfix) normalisieren."""
    preset = get_style_preset(style_id)
    _, title = _strip_md_prefix(line)
    if not title and not (line or "").strip():
        return line
    prefix = str(preset.get("markdown_prefix") or "")
    if style_id == "body":
        return title
    return f"{prefix}{title}"


def auto_format_text(text: str, *, preset: str = "default") -> AutoFormatResult:
    """Konsistente Heading/Body/Quote-Styles auf Text anwenden (Markdown-Heuristik)."""
    _ = preset  # reserved for future named packs
    lines = (text or "").splitlines()
    out_lines: list[str] = []
    headings: list[HeadingCandidate] = []
    changed = 0
    for i, line in enumerate(lines):
        if not line.strip():
            out_lines.append(line)
            continue
        style_id = classify_line_style(line)
        new_line = apply_style_to_line(line, style_id)
        if new_line != line:
            changed += 1
        out_lines.append(new_line)
        if style_id.startswith("heading"):
            level = int(style_id[-1])
            _, title = _strip_md_prefix(new_line)
            headings.append(
                HeadingCandidate(
                    title=title,
                    level=level,
                    style_id=style_id,
                    source="auto_format",
                    line_index=i,
                )
            )
    body = "\n".join(out_lines)
    if text.endswith("\n") and not body.endswith("\n"):
        body += "\n"
    return AutoFormatResult(text=body, headings=headings, changed_lines=changed)


def generate_toc_markdown(
    text: str,
    *,
    max_level: int = 3,
    title: str = "Inhaltsverzeichnis",
) -> str:
    """Markdown-TOC aus erkannten Überschriften."""
    heads = detect_headings_in_text(text)
    lines = [f"# {title}", ""]
    for h in heads:
        if h.level > max_level:
            continue
        indent = "  " * (h.level - 1)
        # Anker-ähnlich: Titel als Link-Text (ohne echte URL — lokal nutzbar)
        lines.append(f"{indent}- {h.title}")
    if len(lines) <= 2:
        lines.append("_Keine Überschriften gefunden._")
    return "\n".join(lines) + "\n"


def insert_toc_into_text(
    text: str,
    *,
    max_level: int = 3,
    replace_existing: bool = True,
) -> str:
    """TOC am Dokumentanfang einfügen/aktualisieren (zwischen Markern)."""
    begin = "<!-- ILD-TOC-BEGIN -->"
    end = "<!-- ILD-TOC-END -->"
    toc = generate_toc_markdown(text, max_level=max_level).rstrip()
    block = f"{begin}\n{toc}\n{end}"
    if begin in text and end in text and replace_existing:
        pre, rest = text.split(begin, 1)
        _, post = rest.split(end, 1)
        return pre.rstrip() + "\n\n" + block + "\n" + post.lstrip("\n")
    if text.lstrip().startswith("# Inhaltsverzeichnis") or begin in text:
        return text
    if not text.strip():
        return block + "\n"
    return block + "\n\n" + text.lstrip()


def detect_headings_in_pdf(
    pdf_path: str | Path,
    *,
    max_level: int = 3,
    password: str | None = None,
) -> list[HeadingCandidate]:
    """Überschriften im PDF per Fontgröße + Text-Heuristik."""
    _ = password
    pdf_path = Path(pdf_path)
    n = int(pdf_page_count(pdf_path))
    sizes: list[float] = []
    raw_blocks: list[tuple[int, Any]] = []
    for page in range(n):
        try:
            blocks = extract_text_blocks(pdf_path, page)
        except Exception:
            continue
        for b in blocks:
            fs = float(getattr(b, "font_size", 0) or 0)
            if fs > 0:
                sizes.append(fs)
            raw_blocks.append((page, b))
    median = 11.0
    if sizes:
        sizes_sorted = sorted(sizes)
        median = sizes_sorted[len(sizes_sorted) // 2]
    headings: list[HeadingCandidate] = []
    seen: set[tuple[int, str]] = set()
    for page, b in raw_blocks:
        text = (getattr(b, "text", "") or "").strip()
        if not text or len(text) > 160:
            continue
        fs = float(getattr(b, "font_size", 0) or 0)
        style_id = classify_line_style(text, median_font=median, font_size=fs)
        if not style_id.startswith("heading"):
            continue
        level = int(style_id[-1])
        if level > max_level:
            continue
        _, title = _strip_md_prefix(text)
        key = (page, title.lower())
        if not title or key in seen:
            continue
        seen.add(key)
        source = "font_size" if fs >= median * 1.12 else "heuristic"
        headings.append(
            HeadingCandidate(
                title=title,
                level=level,
                page_index=page,
                style_id=style_id,
                source=source,
                font_size=fs,
                x=float(getattr(b, "x", 0) or 0),
                y=float(getattr(b, "y", 0) or 0),
            )
        )
    return headings


def headings_to_outline(headings: Sequence[HeadingCandidate]) -> list[OutlineItem]:
    """Heading-Liste → verschachtelter Outline-Baum."""
    root: list[OutlineItem] = []
    stack: list[tuple[int, OutlineItem]] = []
    for h in headings:
        if h.page_index is None or h.page_index < 0:
            continue
        item = OutlineItem(title=h.title, page_index=int(h.page_index))
        level = max(1, min(6, int(h.level or 1)))
        while stack and stack[-1][0] >= level:
            stack.pop()
        if not stack:
            root.append(item)
        else:
            stack[-1][1].children.append(item)
        stack.append((level, item))
    return root


def generate_toc_for_pdf(
    pdf_path: str | Path,
    *,
    out_path: str | Path | None = None,
    max_level: int = 3,
    write: bool = True,
    password: str | None = None,
) -> AutoFormatResult:
    """TOC aus PDF-Überschriften erzeugen und optional als Outline speichern."""
    pdf_path = Path(pdf_path)
    heads = detect_headings_in_pdf(pdf_path, max_level=max_level, password=password)
    outline = headings_to_outline(heads)
    written = False
    dest = Path(out_path) if out_path else pdf_path
    if write:
        write_outline(pdf_path, outline, out_path=dest)
        written = True
    return AutoFormatResult(
        headings=heads,
        outline_written=written,
        outline_count=len(heads),
        path=str(dest),
    )


def auto_format_pdf(
    pdf_path: str | Path,
    *,
    out_path: str | Path | None = None,
    max_level: int = 3,
    update_toc: bool = True,
    password: str | None = None,
) -> AutoFormatResult:
    """PDF: Überschriften erkennen, Styles zuweisen, TOC/Outline aktualisieren."""
    pdf_path = Path(pdf_path)
    result = generate_toc_for_pdf(
        pdf_path,
        out_path=out_path,
        max_level=max_level,
        write=update_toc,
        password=password,
    )
    # Style-Zuweisung ist heuristisch (Presets); Outline = klickbares TOC
    result.changed_lines = len(result.headings)
    return result


def find_replace_text(
    text: str,
    find: str,
    replace: str,
    *,
    case_sensitive: bool = False,
    count: int = 0,
) -> tuple[str, int]:
    """Suchen/Ersetzen in Plaintext. count=0 → alle."""
    if not find:
        return text or "", 0
    if case_sensitive:
        if count and count > 0:
            n = (text or "").count(find)
            limited = min(n, count)
            out = text or ""
            for _ in range(limited):
                out = out.replace(find, replace, 1)
            return out, limited
        n = (text or "").count(find)
        return (text or "").replace(find, replace), n
    pattern = re.compile(re.escape(find), re.IGNORECASE)
    matches = list(pattern.finditer(text or ""))
    if not matches:
        return text or "", 0
    limit = len(matches) if not count or count <= 0 else min(len(matches), count)
    out = text or ""
    # von hinten ersetzen, Indizes bleiben stabil
    for m in reversed(matches[:limit]):
        out = out[: m.start()] + replace + out[m.end() :]
    return out, limit


def find_replace_in_pdf_text(
    pdf_path: str | Path,
    find: str,
    replace: str,
    *,
    case_sensitive: bool = False,
    max_replacements: int = 50,
    password: str | None = None,
) -> dict[str, Any]:
    """PDF-Text suchen und per Inline-Edit ersetzen (praktisch, Cover+Rewrite)."""
    from .text_edit import EditableTextSpan, TextStyle, apply_inline_text_edit, hit_test_text
    from .overlay import find_text_rects

    pdf_path = Path(pdf_path)
    if not find:
        return {"count": 0, "path": str(pdf_path), "replacements": []}
    n_pages = int(pdf_page_count(pdf_path))
    rects: list[tuple[int, Any]] = []
    for page_i in range(n_pages):
        try:
            hits = find_text_rects(
                pdf_path,
                page_i,
                find,
                case_sensitive=case_sensitive,
                password=password,
                max_hits=max(1, int(max_replacements or 50)),
            )
        except Exception:
            continue
        for r in hits:
            rects.append((page_i, r))
    replacements: list[dict[str, Any]] = []
    current = pdf_path
    limit = max(0, int(max_replacements or 50))
    for page, r in rects[:limit]:
        x = float(getattr(r, "x", 0) or 0)
        y = float(getattr(r, "y", 0) or 0)
        w = float(getattr(r, "width", 40) or 40)
        h = float(getattr(r, "height", 12) or 12)
        span = hit_test_text(current, page, x + w * 0.1, y + h * 0.5, scale=1.0)
        style = span.style if span else TextStyle()
        edit_span = EditableTextSpan(
            page=page,
            x=x,
            y=y,
            width=max(w, 8.0),
            height=max(h, 8.0),
            text=str(getattr(r, "text", "") or find),
            style=style,
        )
        try:
            result = apply_inline_text_edit(
                current,
                edit_span,
                replace,
                style=style,
                scale=1.0,
                out_path=current,
            )
            current = Path(result.out_path)
            replacements.append({"page": page + 1, "old": find, "new": replace})
        except Exception as e:
            replacements.append({"page": page + 1, "error": str(e)})
    return {
        "count": len([x for x in replacements if "error" not in x]),
        "path": str(current),
        "replacements": replacements,
        "matches_found": len(rects),
    }


def list_system_fonts(*, include_files: bool = False) -> list[str]:
    """Lokal installierte Schriften (Windows Fonts + Qt-Families + Linux-Pfade)."""
    names: set[str] = set()
    # Qt (wenn App/Event-Loop vorhanden oder offscreen)
    try:
        from PySide6.QtGui import QFontDatabase
        from PySide6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if app is None:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            app = QApplication(sys.argv[:1] or ["ild-fonts"])
        try:
            # Qt6: QFontDatabase.families() ist statisch
            families = QFontDatabase.families()
        except TypeError:
            db = QFontDatabase()
            families = db.families()
        for fam in families or []:
            if fam:
                names.add(str(fam))
    except Exception:
        pass

    font_dirs: list[Path] = []
    windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot")
    if windir:
        font_dirs.append(Path(windir) / "Fonts")
    font_dirs.append(Path("C:/Windows/Fonts"))
    font_dirs.extend(
        [
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
            Path.home() / ".fonts",
            Path.home() / ".local/share/fonts",
        ]
    )
    exts = {".ttf", ".otf", ".ttc", ".otc"}
    for d in font_dirs:
        try:
            if not d.is_dir():
                continue
            for p in d.rglob("*"):
                if p.suffix.lower() not in exts:
                    continue
                stem = p.stem.replace("-", " ").replace("_", " ")
                # Dateiname → lesbarer Familienname (grob)
                clean = re.sub(r"(?i)\b(regular|bold|italic|light|medium|black|thin)\b", "", stem)
                clean = re.sub(r"\s+", " ", clean).strip()
                if clean:
                    names.add(clean)
                if include_files:
                    names.add(p.name)
        except Exception:
            continue

    # Standard-14 immer anbieten
    for std in (
        "Helvetica",
        "Times New Roman",
        "Courier New",
        "Arial",
        "Calibri",
        "Segoe UI",
        "Consolas",
        "Georgia",
        "Verdana",
        "Tahoma",
    ):
        names.add(std)
    return sorted(names, key=lambda s: s.lower())


def outline_summary(pdf_path: str | Path) -> list[dict[str, Any]]:
    """Aktuelles PDF-Outline flach als Dict-Liste."""
    items = extract_outline(pdf_path)
    out: list[dict[str, Any]] = []

    def walk(nodes: Iterable[OutlineItem], level: int = 1) -> None:
        for n in nodes or []:
            out.append(
                {
                    "title": n.title,
                    "page": (int(n.page_index) + 1) if n.page_index is not None else None,
                    "level": level,
                }
            )
            if n.children:
                walk(n.children, level + 1)

    walk(items)
    return out
