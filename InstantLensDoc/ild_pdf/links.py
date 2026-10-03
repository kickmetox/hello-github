"""Native PDF-Link-Annotationen (externe URI) lesen und Sidecar-Links backen — 2.3.0."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence
from urllib.parse import urlparse


@dataclass(frozen=True)
class UriLink:
    """Klickbarer URI-Link auf einer PDF-Seite (Render-Pixel, Y von oben)."""

    page: int
    x: float
    y: float
    width: float
    height: float
    uri: str

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height


def is_external_http_uri(uri: str) -> bool:
    """Nur http(s)-URLs als externe Links zulassen."""
    raw = (uri or "").strip()
    if not raw:
        return False
    try:
        parsed = urlparse(raw)
    except Exception:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def list_page_uri_links(
    pdf_path: str | Path,
    page_index: int = 0,
    *,
    scale: float = 1.0,
    password: str | None = None,
) -> List[UriLink]:
    """
    Liest Link-Annotationen mit URI-Action auf einer Seite.

    Koordinaten: Render-Pixel bei ``scale``, Ursprung oben links
    (wie Annotationen / Textsuche).
    """
    import pikepdf
    from pikepdf import Name

    path = Path(pdf_path)
    links: List[UriLink] = []
    open_kw: dict = {}
    if password:
        open_kw["password"] = password
    try:
        with pikepdf.open(path, **open_kw) as doc:
            if page_index < 0 or page_index >= len(doc.pages):
                return []
            page = doc.pages[page_index]
            mediabox = page.mediabox
            page_h = float(mediabox[3] - mediabox[1])
            annots = page.get("/Annots")
            if annots is None:
                return []
            for annot in annots:
                try:
                    obj = annot.get_object() if hasattr(annot, "get_object") else annot
                    if obj.get("/Subtype") != Name.Link:
                        continue
                    action = obj.get("/A")
                    if action is None:
                        continue
                    aobj = action.get_object() if hasattr(action, "get_object") else action
                    if aobj.get("/S") != Name.URI:
                        continue
                    uri_val = aobj.get("/URI")
                    if uri_val is None:
                        continue
                    uri = str(uri_val).strip()
                    if not is_external_http_uri(uri):
                        continue
                    rect = obj.get("/Rect")
                    if rect is None or len(rect) < 4:
                        continue
                    left = float(rect[0])
                    bottom = float(rect[1])
                    right = float(rect[2])
                    top = float(rect[3])
                    x0 = min(left, right) * scale
                    x1 = max(left, right) * scale
                    # PDF Y unten → Render Y oben
                    y0 = (page_h - max(bottom, top)) * scale
                    y1 = (page_h - min(bottom, top)) * scale
                    links.append(
                        UriLink(
                            page=page_index,
                            x=x0,
                            y=y0,
                            width=max(x1 - x0, 1.0),
                            height=max(y1 - y0, 1.0),
                            uri=uri,
                        )
                    )
                except Exception:
                    continue
    except Exception:
        return []
    return links


def uri_link_at(
    pdf_path: str | Path,
    page_index: int,
    x: float,
    y: float,
    *,
    scale: float = 1.0,
    password: str | None = None,
) -> Optional[UriLink]:
    """Ersten Treffer an Pixel (x,y) liefern — oberste Annotation zuerst (rückwärts)."""
    links = list_page_uri_links(
        pdf_path, page_index, scale=scale, password=password
    )
    for link in reversed(links):
        if link.contains(x, y):
            return link
    return None


@dataclass(frozen=True)
class SidecarUriLink:
    """Sidecar-Link (Rechteck + URI) in Render-Pixeln, Y von oben — 2.3.0."""

    page: int
    x: float
    y: float
    width: float
    height: float
    uri: str


def sidecar_links_from_annotations(
    annotations: Iterable[object],
) -> List[SidecarUriLink]:
    """Extrahiert LINK-Annotationen (type=link, text=URI) aus Sidecar-Objekten."""
    out: List[SidecarUriLink] = []
    for ann in annotations or []:
        try:
            t = getattr(ann, "type", None)
            t_val = getattr(t, "value", t)
            if str(t_val or "").lower() != "link":
                continue
            uri = str(getattr(ann, "text", "") or "").strip()
            if not is_external_http_uri(uri):
                continue
            out.append(
                SidecarUriLink(
                    page=int(getattr(ann, "page", 0) or 0),
                    x=float(getattr(ann, "x", 0) or 0),
                    y=float(getattr(ann, "y", 0) or 0),
                    width=max(1.0, float(getattr(ann, "width", 1) or 1)),
                    height=max(1.0, float(getattr(ann, "height", 1) or 1)),
                    uri=uri,
                )
            )
        except Exception:
            continue
    return out


def bake_uri_links_to_pdf(
    pdf_path: str | Path,
    links: Sequence[SidecarUriLink | UriLink],
    *,
    out_path: str | Path | None = None,
    scale: float = 1.0,
    password: str | None = None,
) -> Path:
    """
    Schreibt Sidecar-/URI-Links als native PDF Link-Annotationen (pikepdf).
    Ausgabe neues File (Default ``*_links.pdf``). Koordinaten: Render-Pixel bei ``scale``.
    """
    import pikepdf
    from pikepdf import Dictionary, Name

    src = Path(pdf_path)
    dst = Path(out_path) if out_path else src.with_name(f"{src.stem}_links.pdf")
    scale = max(float(scale or 1.0), 1e-6)
    open_kw: dict = {}
    if password:
        open_kw["password"] = password

    with pikepdf.open(src, **open_kw) as doc:
        by_page: dict[int, list] = {}
        for link in links or []:
            uri = str(getattr(link, "uri", "") or "").strip()
            if not is_external_http_uri(uri):
                continue
            page_i = int(getattr(link, "page", 0) or 0)
            if page_i < 0 or page_i >= len(doc.pages):
                continue
            by_page.setdefault(page_i, []).append(link)

        for page_i, page_links in by_page.items():
            page = doc.pages[page_i]
            mediabox = page.mediabox
            page_h = float(mediabox[3] - mediabox[1])
            annots = page.get("/Annots")
            if annots is None:
                annots = doc.make_indirect(pikepdf.Array())
                page["/Annots"] = annots
            for link in page_links:
                x = float(link.x) / scale
                y_top = float(link.y) / scale
                w = max(1.0, float(link.width) / scale)
                h = max(1.0, float(link.height) / scale)
                # Render Y oben → PDF Y unten
                left = x
                right = x + w
                top = page_h - y_top
                bottom = page_h - (y_top + h)
                rect = [min(left, right), min(bottom, top), max(left, right), max(bottom, top)]
                annot = Dictionary(
                    Type=Name.Annot,
                    Subtype=Name.Link,
                    Rect=rect,
                    Border=[0, 0, 1],
                    C=[0.0, 0.0, 1.0],
                    A=Dictionary(Type=Name.Action, S=Name.URI, URI=str(link.uri)),
                )
                annots.append(doc.make_indirect(annot))
        doc.save(dst)
    return dst
