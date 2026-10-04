"""Hyperlinks: Text → URL oder Dokumentziel — 2.6.27.

Markdown-Syntax ``[Text](Ziel)`` und HTML ``<a href>``.
Ziele: ``https://…`` / ``http://…`` (extern) oder ``#anker`` / ``ild://line/N`` /
``ild://heading/Name`` / ``ild://bookmark/Label`` (intern).
Optional Sidecar ``*.ildlinks.json`` (ildlinks-v1).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence
from urllib.parse import urlparse
from uuid import uuid4

from instantlensdoc import __version__

LINK_SCHEMA_ID = "ildlinks-v1"
LINK_VERSION = 1
SIDECAR_SUFFIX = ".ildlinks.json"

_MD_LINK_RE = re.compile(
    r"\[([^\]]+)\]\(([^)]+)\)",
    re.MULTILINE,
)
_HTML_A_RE = re.compile(
    r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


@dataclass
class Hyperlink:
    """Ein Hyperlink im Text (Markdown/HTML/Sidecar)."""

    text: str
    target: str
    kind: str = "url"  # url | anchor | line | heading | bookmark
    start: int = -1
    end: int = -1
    id: str = field(default_factory=lambda: uuid4().hex[:10])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Hyperlink":
        return cls(
            text=str(data.get("text") or ""),
            target=str(data.get("target") or ""),
            kind=str(data.get("kind") or "url"),
            start=int(data.get("start", -1)),
            end=int(data.get("end", -1)),
            id=str(data.get("id") or uuid4().hex[:10]),
        )


def classify_target(target: str) -> str:
    """Zieltyp: url | anchor | line | heading | bookmark."""
    raw = (target or "").strip()
    if not raw:
        return "url"
    low = raw.lower()
    if low.startswith("ild://line/"):
        return "line"
    if low.startswith("ild://heading/"):
        return "heading"
    if low.startswith("ild://bookmark/"):
        return "bookmark"
    if raw.startswith("#"):
        return "anchor"
    parsed = urlparse(raw)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return "url"
    if "://" not in raw and "." in raw and " " not in raw:
        return "url"
    if raw.startswith("/") or raw.startswith("./"):
        return "anchor"
    return "url"


def normalize_target(target: str, *, kind: str | None = None) -> str:
    """Ziel normalisieren (http→https-Vorschlag, #anker trimmen)."""
    raw = (target or "").strip()
    if not raw:
        return ""
    k = kind or classify_target(raw)
    if k == "url":
        if "://" not in raw and "." in raw and " " not in raw:
            return "https://" + raw
        return raw
    if k == "anchor":
        if not raw.startswith("#"):
            return "#" + raw.lstrip("#")
        return raw
    return raw


def validate_hyperlink(text: str, target: str) -> tuple[bool, str, str, str]:
    """
    Returns: (ok, normalized_target, kind, de_fehler).
    """
    label = (text or "").strip()
    if not label:
        return False, "", "url", "Linktext darf nicht leer sein."
    kind = classify_target(target)
    norm = normalize_target(target, kind=kind)
    if not norm:
        return False, "", kind, "Ziel darf nicht leer sein."
    if kind == "url":
        parsed = urlparse(norm)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return False, norm, kind, "Nur gültige http(s)-URLs oder Dokumentziele (#anker)."
    if kind == "line":
        try:
            n = int(norm.split("/")[-1])
            if n < 1:
                raise ValueError
        except ValueError:
            return False, norm, kind, "Zeilenziel muss ild://line/N mit N≥1 sein."
    return True, norm, kind, ""


def make_markdown_link(text: str, target: str) -> str:
    ok, norm, _kind, err = validate_hyperlink(text, target)
    if not ok:
        raise ValueError(err)
    safe_text = (text or "").replace("]", "\\]")
    return f"[{safe_text}]({norm})"


def make_html_link(text: str, target: str) -> str:
    import html as html_mod

    ok, norm, _kind, err = validate_hyperlink(text, target)
    if not ok:
        raise ValueError(err)
    return f'<a href="{html_mod.escape(norm, quote=True)}">{html_mod.escape(text)}</a>'


def extract_links_from_text(text: str) -> list[Hyperlink]:
    """Markdown- und HTML-Links aus Text extrahieren (Positionen)."""
    out: list[Hyperlink] = []
    seen: set[tuple[int, int, str]] = set()
    for m in _MD_LINK_RE.finditer(text or ""):
        label, tgt = m.group(1), m.group(2)
        kind = classify_target(tgt)
        key = (m.start(), m.end(), tgt)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            Hyperlink(
                text=label,
                target=normalize_target(tgt, kind=kind),
                kind=kind,
                start=m.start(),
                end=m.end(),
            )
        )
    for m in _HTML_A_RE.finditer(text or ""):
        tgt, label = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        kind = classify_target(tgt)
        key = (m.start(), m.end(), tgt)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            Hyperlink(
                text=label or tgt,
                target=normalize_target(tgt, kind=kind),
                kind=kind,
                start=m.start(),
                end=m.end(),
            )
        )
    return out


def insert_link_in_text(
    text: str,
    link_text: str,
    target: str,
    *,
    start: int | None = None,
    end: int | None = None,
    as_html: bool = False,
) -> dict[str, Any]:
    """
    Link in Text einfügen bzw. Auswahl ersetzen.
    Ohne start/end: ans Ende anhängen (mit Leerzeichen).
    """
    ok, norm, kind, err = validate_hyperlink(link_text, target)
    if not ok:
        raise ValueError(err)
    snippet = make_html_link(link_text, norm) if as_html else make_markdown_link(link_text, norm)
    body = text or ""
    if start is not None and end is not None and 0 <= start <= end <= len(body):
        new_text = body[:start] + snippet + body[end:]
        pos = start
    else:
        sep = "" if (not body or body.endswith(("\n", " ", "\t"))) else " "
        pos = len(body) + len(sep)
        new_text = body + sep + snippet
    link = Hyperlink(
        text=link_text,
        target=norm,
        kind=kind,
        start=pos,
        end=pos + len(snippet),
    )
    return {
        "text": new_text,
        "link": link.to_dict(),
        "snippet": snippet,
        "version": __version__,
    }


def list_heading_anchors(text: str) -> list[dict[str, Any]]:
    """Überschriften → Anker-IDs (slug) für In-Dokument-Ziele."""
    out: list[dict[str, Any]] = []
    for m in _HEADING_RE.finditer(text or ""):
        level = len(m.group(1))
        title = m.group(2).strip()
        slug = slugify_anchor(title)
        out.append(
            {
                "level": level,
                "title": title,
                "anchor": f"#{slug}",
                "target": f"ild://heading/{title}",
                "start": m.start(),
                "end": m.end(),
            }
        )
    return out


def slugify_anchor(title: str) -> str:
    s = (title or "").strip().lower()
    s = re.sub(r"[^\w\s\-äöüÄÖÜß]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s or "section"


def resolve_internal_target(
    text: str,
    target: str,
    *,
    bookmarks: Sequence[tuple[int, str]] | None = None,
) -> dict[str, Any]:
    """
    Internes Ziel auflösen → Zeile (1-basiert) / Zeichenoffset.
    bookmarks: Liste (line_1based, label).
    """
    kind = classify_target(target)
    norm = normalize_target(target, kind=kind)
    lines = (text or "").replace("\r\n", "\n").split("\n")
    if kind == "line":
        n = int(norm.split("/")[-1])
        if n < 1 or n > len(lines):
            return {"ok": False, "error": f"Zeile {n} außerhalb des Dokuments", "target": norm}
        offset = sum(len(l) + 1 for l in lines[: n - 1])
        return {
            "ok": True,
            "kind": "line",
            "line": n,
            "offset": offset,
            "target": norm,
            "snippet": lines[n - 1][:120],
        }
    if kind in ("anchor", "heading"):
        want = norm[1:] if norm.startswith("#") else norm
        if kind == "heading" and norm.lower().startswith("ild://heading/"):
            want = slugify_anchor(norm.split("/", 3)[-1])
        for h in list_heading_anchors(text or ""):
            if h["anchor"].lstrip("#") == want.lstrip("#") or slugify_anchor(h["title"]) == want:
                line = (text or "")[: h["start"]].count("\n") + 1
                return {
                    "ok": True,
                    "kind": kind,
                    "line": line,
                    "offset": h["start"],
                    "target": norm,
                    "title": h["title"],
                    "anchor": h["anchor"],
                }
        return {"ok": False, "error": f"Anker/Überschrift nicht gefunden: {want}", "target": norm}
    if kind == "bookmark":
        label = norm.split("/", 3)[-1] if "/" in norm else norm
        for line_n, lbl in bookmarks or []:
            if (lbl or "").strip().lower() == label.strip().lower():
                n = int(line_n)
                offset = sum(len(l) + 1 for l in lines[: max(0, n - 1)])
                return {
                    "ok": True,
                    "kind": "bookmark",
                    "line": n,
                    "offset": offset,
                    "target": norm,
                    "label": lbl,
                }
        return {"ok": False, "error": f"Lesezeichen nicht gefunden: {label}", "target": norm}
    return {"ok": False, "error": "Kein internes Ziel", "kind": kind, "target": norm}


def links_to_html_fragment(links: Iterable[Hyperlink]) -> str:
    parts = [make_html_link(lk.text, lk.target) for lk in links]
    return "<br/>\n".join(parts)


def apply_links_markdown_to_html(text: str) -> str:
    """Markdown-Links im Fließtext zu HTML-<a> umschreiben (Export-Hilfe)."""
    import html as html_mod

    def _repl(m: re.Match[str]) -> str:
        label, tgt = m.group(1), m.group(2)
        ok, norm, _k, _e = validate_hyperlink(label, tgt)
        if not ok:
            return m.group(0)
        return (
            f'<a href="{html_mod.escape(norm, quote=True)}">'
            f"{html_mod.escape(label)}</a>"
        )

    return _MD_LINK_RE.sub(_repl, text or "")


def sidecar_path_for(doc_path: str | Path) -> Path:
    p = Path(doc_path)
    return p.with_suffix(p.suffix + SIDECAR_SUFFIX.replace(".ildlinks.json", "") + ".ildlinks.json")


def save_links_sidecar(
    doc_path: str | Path,
    links: Sequence[Hyperlink | dict[str, Any]],
    *,
    source: str = "",
) -> Path:
    path = sidecar_path_for(doc_path)
    rows = [
        (lk.to_dict() if isinstance(lk, Hyperlink) else Hyperlink.from_dict(lk).to_dict())
        for lk in links
    ]
    data = {
        "schema": LINK_SCHEMA_ID,
        "version": LINK_VERSION,
        "app_version": __version__,
        "source": source or Path(doc_path).name,
        "links": rows,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_links_sidecar(doc_path: str | Path) -> list[Hyperlink]:
    path = sidecar_path_for(doc_path)
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != LINK_SCHEMA_ID:
        raise ValueError(f"Unbekanntes Link-Schema: {data.get('schema')}")
    return [Hyperlink.from_dict(x) for x in data.get("links") or []]


def hyperlink_info() -> dict[str, Any]:
    return {
        "schema": LINK_SCHEMA_ID,
        "version": LINK_VERSION,
        "app_version": __version__,
        "kinds": ["url", "anchor", "line", "heading", "bookmark"],
        "markdown": "[Text](https://example.com) · [Text](#anker) · [Text](ild://line/12)",
        "html": '<a href="https://example.com">Text</a>',
    }
