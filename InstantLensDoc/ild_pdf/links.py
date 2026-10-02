"""Native PDF-Link-Annotationen (externe URI) lesen."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
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
