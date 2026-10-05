"""Import AI/IDML/EPS/SVG/PSD/TIFF/Krita in DTP-Rahmen (Layout vs. Inhalt)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


class ImportResult(dict):
    """status, kind, frames, notes."""


def import_graphic(doc: Any, path: str | Path, *, page: int | None = None) -> ImportResult:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(str(p))
    pg = int(doc.current_page if page is None else page)
    suf = p.suffix.lower()
    dispatch = {
        ".svg": _import_svg,
        ".tif": _import_raster,
        ".tiff": _import_raster,
        ".png": _import_raster,
        ".jpg": _import_raster,
        ".jpeg": _import_raster,
        ".webp": _import_raster,
        ".psd": _import_psd,
        ".kra": _import_kra,
        ".ai": _import_ai_eps,
        ".eps": _import_ai_eps,
        ".idml": _import_idml,
        ".pdf": _import_ai_eps,
    }
    fn = dispatch.get(suf)
    if fn is None:
        raise ValueError(f"Unbekanntes Grafikformat: {suf}")
    return fn(doc, p, pg)


def _import_raster(doc: Any, path: Path, page: int) -> ImportResult:
    fr = doc.add_image_frame(str(path), page=page)
    return ImportResult(status="ok", kind="image", frames=[fr.id], notes=[])


def _import_svg(doc: Any, path: Path, page: int) -> ImportResult:
    notes: list[str] = []
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except Exception as exc:
        notes.append(f"SVG parse: {exc}")
        fr = doc.add_image_frame(str(path), page=page)
        return ImportResult(status="ok", kind="image", frames=[fr.id], notes=notes)
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"
    texts = []
    for el in root.iter(f"{ns}text"):
        t = "".join(el.itertext()).strip()
        if t:
            texts.append(t)
    frames = []
    if texts:
        fr = doc.add_text_frame("\n".join(texts), page=page)
        frames.append(fr.id)
    fr_img = doc.add_image_frame(str(path), page=page, y=220)
    frames.append(fr_img.id)
    return ImportResult(status="ok", kind="svg", frames=frames, notes=notes)


def _import_psd(doc: Any, path: Path, page: int) -> ImportResult:
    notes: list[str] = []
    preview = path
    try:
        from PIL import Image

        im = Image.open(path)
        im = im.convert("RGB")
        dest = path.with_suffix(".ild-psd.png")
        im.save(dest)
        preview = dest
        notes.append("PSD über Pillow-Composite")
    except Exception as exc:
        notes.append(f"PSD ohne Pillow ({exc}) — Pfad als Bildrahmen")
    fr = doc.add_image_frame(str(preview), page=page)
    return ImportResult(status="ok", kind="image", frames=[fr.id], notes=notes)


def _import_kra(doc: Any, path: Path, page: int) -> ImportResult:
    notes: list[str] = []
    preview = path
    try:
        with zipfile.ZipFile(path) as zf:
            name = "mergedimage.png" if "mergedimage.png" in zf.namelist() else None
            if name:
                dest = path.with_suffix(".ild-kra.png")
                dest.write_bytes(zf.read(name))
                preview = dest
                notes.append("Krita mergedimage.png")
    except Exception as exc:
        notes.append(f"KRA: {exc}")
    fr = doc.add_image_frame(str(preview), page=page)
    return ImportResult(status="ok", kind="image", frames=[fr.id], notes=notes)


def _import_ai_eps(doc: Any, path: Path, page: int) -> ImportResult:
    notes: list[str] = []
    raw = path.read_bytes()[:16]
    kind = "render"
    if raw.startswith(b"%PDF"):
        notes.append("AI/PDF als Render-Rahmen (platziert)")
    elif raw.startswith(b"%!PS") or raw.startswith(b"\xc5\xd0\xd3\xc6"):
        notes.append("EPS/AI-PostScript platziert (Bounding-Box, kein Live-Edit)")
    fr = doc.add_render_frame(str(path), page=page)
    return ImportResult(status="ok", kind=kind, frames=[fr.id], notes=notes)


def _import_idml(doc: Any, path: Path, page: int) -> ImportResult:
    notes: list[str] = []
    texts: list[str] = []
    try:
        with zipfile.ZipFile(path) as zf:
            stories = [
                n
                for n in zf.namelist()
                if n.endswith(".xml") and "Stories/" in n.replace("\\", "/")
            ]
            for n in stories[:12]:
                xml = zf.read(n).decode("utf-8", "ignore")
                try:
                    root = ET.fromstring(xml)
                except Exception:
                    continue
                chunks = [el.text or "" for el in root.iter() if (el.text or "").strip()]
                if chunks:
                    texts.append(" ".join(c.strip() for c in chunks if c.strip()))
    except Exception as exc:
        notes.append(f"IDML: {exc}")
        raise
    if not texts:
        notes.append("IDML ohne Story-Text")
        fr = doc.add_text_frame("", page=page)
        return ImportResult(status="ok", kind="text", frames=[fr.id], notes=notes)
    fr = doc.add_text_frame("\n\n".join(texts), page=page)
    return ImportResult(status="ok", kind="text", frames=[fr.id], notes=notes)
