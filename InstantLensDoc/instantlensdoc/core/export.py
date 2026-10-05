"""Export/Import: Editor-Inhalt → HTML / DOCX / PDF / TXT / RTF / XLSX / JPG / EPUB / PPTX. — 2.6.28."""

from __future__ import annotations

import html
import logging
import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4
from xml.etree import ElementTree as ET

SUPPORTED_EXPORT_FORMATS: tuple[str, ...] = (
    "docx",
    "xlsx",
    "pdf",
    "txt",
    "rtf",
    "html",
    "jpg",
    "jpeg",
    "epub",
    "pptx",
)
SUPPORTED_IMPORT_FORMATS: tuple[str, ...] = (
    "docx",
    "xlsx",
    "pdf",
    "txt",
    "rtf",
    "html",
    "htm",
    "csv",
    "md",
    "markdown",
    "jpg",
    "jpeg",
    "png",
    "epub",
    "pptx",
)


def _lines(text: str) -> list[str]:
    return (text or "").replace("\r\n", "\n").split("\n")


def list_export_formats() -> list[dict[str, str]]:
    return [
        {"id": "docx", "ext": ".docx", "name": "Microsoft Word"},
        {"id": "xlsx", "ext": ".xlsx", "name": "Microsoft Excel (Tabellen)"},
        {"id": "pdf", "ext": ".pdf", "name": "PDF"},
        {"id": "txt", "ext": ".txt", "name": "Plain Text"},
        {"id": "rtf", "ext": ".rtf", "name": "Rich Text Format"},
        {"id": "html", "ext": ".html", "name": "HTML"},
        {"id": "jpg", "ext": ".jpg", "name": "JPEG-Bild"},
        {"id": "epub", "ext": ".epub", "name": "EPUB (E-Book)"},
        {"id": "pptx", "ext": ".pptx", "name": "Microsoft PowerPoint"},
    ]


def list_import_formats() -> list[dict[str, str]]:
    return [
        {"id": "docx", "ext": ".docx", "name": "Microsoft Word"},
        {"id": "xlsx", "ext": ".xlsx", "name": "Microsoft Excel"},
        {"id": "csv", "ext": ".csv", "name": "CSV (Tabellen)"},
        {"id": "pdf", "ext": ".pdf", "name": "PDF"},
        {"id": "txt", "ext": ".txt", "name": "Plain Text"},
        {"id": "rtf", "ext": ".rtf", "name": "Rich Text Format"},
        {"id": "html", "ext": ".html", "name": "HTML"},
        {"id": "md", "ext": ".md", "name": "Markdown"},
        {"id": "jpg", "ext": ".jpg", "name": "JPEG/PNG Bild"},
        {"id": "epub", "ext": ".epub", "name": "EPUB (E-Book Text)"},
        {"id": "pptx", "ext": ".pptx", "name": "Microsoft PowerPoint"},
    ]

def _inline_md_to_html(fragment: str) -> str:
    """Escape + Markdown-Links → <a>."""
    from instantlensdoc.core.hyperlinks import _MD_LINK_RE, validate_hyperlink

    parts: list[str] = []
    pos = 0
    for m in _MD_LINK_RE.finditer(fragment or ""):
        parts.append(html.escape((fragment or "")[pos : m.start()]))
        label, tgt = m.group(1), m.group(2)
        ok, norm, _k, _e = validate_hyperlink(label, tgt)
        if ok:
            parts.append(
                f'<a href="{html.escape(norm, quote=True)}">{html.escape(label)}</a>'
            )
        else:
            parts.append(html.escape(m.group(0)))
        pos = m.end()
    parts.append(html.escape((fragment or "")[pos:]))
    return "".join(parts)


def _markdownish_body_parts(text: str) -> list[str]:
    """Markdownish → HTML-Fragmente; Markdown-Links → <a> — 2.6.26."""
    paras: list[str] = []
    buf: list[str] = []

    def flush():
        nonlocal buf
        if not buf:
            return
        joined = " ".join(buf).strip()
        buf = []
        if not joined:
            return
        if joined.startswith("### "):
            paras.append(f"<h3>{_inline_md_to_html(joined[4:])}</h3>")
        elif joined.startswith("## "):
            paras.append(f"<h2>{_inline_md_to_html(joined[3:])}</h2>")
        elif joined.startswith("# "):
            paras.append(f"<h1>{_inline_md_to_html(joined[2:])}</h1>")
        elif joined.startswith("- "):
            paras.append(f"<li>{_inline_md_to_html(joined[2:])}</li>")
        else:
            paras.append(f"<p>{_inline_md_to_html(joined)}</p>")

    for line in _lines(text):
        if not line.strip():
            flush()
        else:
            if line.strip().startswith("- ") and buf:
                flush()
            buf.append(line.strip())
    flush()
    out: list[str] = []
    in_ul = False
    for p in paras:
        if p.startswith("<li>"):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(p)
        else:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(p)
    if in_ul:
        out.append("</ul>")
    return out


def export_html(
    text: str,
    path: str | Path,
    *,
    title: str = "InstantLens Doc",
    as_markdownish: bool = True,
) -> Path:
    """
    Schreibt UTF-8-HTML. Bei as_markdownish: #/## Überschriften, leere Zeile = Absatz.
    Markdown-Hyperlinks werden zu <a href> — 2.6.26.
    """
    path = Path(path)
    if as_markdownish:
        body_parts = _markdownish_body_parts(text)
    else:
        body_parts = [f"<pre>{html.escape(text)}</pre>"]

    doc = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8"/>
<meta name="generator" content="InstantLens Doc"/>
<title>{html.escape(title)}</title>
<style>
body {{ font-family: Georgia, 'Times New Roman', serif; max-width: 42rem;
       margin: 2rem auto; padding: 0 1rem; line-height: 1.55; color: #1a1a1a; }}
h1,h2,h3 {{ font-family: 'Segoe UI', system-ui, sans-serif; }}
pre {{ white-space: pre-wrap; font-family: Consolas, monospace; }}
a {{ color: #0b5cab; }}
</style>
</head>
<body>
{"".join(body_parts)}
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")
    return path


def export_epub(
    text: str,
    path: str | Path,
    *,
    title: str = "InstantLens Doc",
    author: str = "InstantLens Doc",
    language: str = "de",
) -> Path:
    """
    EPUB 2.0.1 (ohne externe Abhängigkeit) — Kapitel aus Markdownish-Text — 2.6.26.
    Struktur: mimetype + META-INF/container.xml + OEBPS/{content.opf,toc.ncx,chapter*.xhtml}.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    book_id = f"urn:uuid:{uuid4()}"
    # Kapitel an H1 splitten, sonst ein Kapitel
    raw = (text or "").replace("\r\n", "\n")
    chunks: list[tuple[str, str]] = []
    current_title = title or "Kapitel 1"
    current_lines: list[str] = []
    for line in raw.split("\n"):
        if line.startswith("# ") and not line.startswith("## "):
            if current_lines and any(x.strip() for x in current_lines):
                chunks.append((current_title, "\n".join(current_lines).strip()))
            current_title = line[2:].strip() or f"Kapitel {len(chunks) + 1}"
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines and any(x.strip() for x in current_lines):
        chunks.append((current_title, "\n".join(current_lines).strip()))
    if not chunks:
        chunks = [(title or "Inhalt", raw or "")]

    chapters: list[tuple[str, str, str]] = []  # id, title, xhtml_body
    for i, (ch_title, ch_text) in enumerate(chunks, start=1):
        cid = f"chap{i:02d}"
        body = "".join(_markdownish_body_parts(ch_text if ch_text.strip() else ch_title))
        xhtml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" '
            '"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="'
            + html.escape(language)
            + '">\n<head><title>'
            + html.escape(ch_title)
            + "</title>"
            "<style type=\"text/css\">body{font-family:serif;line-height:1.5;margin:1em;}"
            "a{color:#0b5cab;}</style></head>\n<body>\n"
            f"<h1 id=\"{cid}\">{html.escape(ch_title)}</h1>\n"
            f"{body}\n</body></html>\n"
        )
        chapters.append((cid, ch_title, xhtml))

    manifest_items = []
    spine_items = []
    nav_points = []
    for i, (cid, ch_title, _x) in enumerate(chapters, start=1):
        href = f"{cid}.xhtml"
        manifest_items.append(
            f'<item id="{cid}" href="{href}" media-type="application/xhtml+xml"/>'
        )
        spine_items.append(f'<itemref idref="{cid}"/>')
        nav_points.append(
            f'<navPoint id="nav{i}" playOrder="{i}">'
            f"<navLabel><text>{html.escape(ch_title)}</text></navLabel>"
            f'<content src="{href}"/>'
            f"</navPoint>"
        )

    opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:title>{html.escape(title)}</dc:title>
    <dc:creator opf:role="aut">{html.escape(author or "InstantLens Doc")}</dc:creator>
    <dc:language>{html.escape(language)}</dc:language>
    <dc:identifier id="BookId">{html.escape(book_id)}</dc:identifier>
    <meta name="generator" content="InstantLens Doc"/>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    {"".join(manifest_items)}
  </manifest>
  <spine toc="ncx">
    {"".join(spine_items)}
  </spine>
</package>
"""
    ncx = f"""<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{html.escape(book_id)}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{html.escape(title)}</text></docTitle>
  <navMap>
    {"".join(nav_points)}
  </navMap>
</ncx>
"""
    container = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # mimetype muss unkomprimiert und erstes Entry sein
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", container, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/content.opf", opf, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/toc.ncx", ncx, compress_type=zipfile.ZIP_DEFLATED)
        for cid, _t, xhtml in chapters:
            zf.writestr(
                f"OEBPS/{cid}.xhtml",
                xhtml.encode("utf-8"),
                compress_type=zipfile.ZIP_DEFLATED,
            )
    path.write_bytes(buf.getvalue())
    return path


def import_epub(path: str | Path) -> str:
    """EPUB → Plaintext (Kapitel-Titel + Body) — 2.6.26."""
    path = Path(path)
    parts: list[str] = []
    with zipfile.ZipFile(path, "r") as zf:
        names = [
            n
            for n in zf.namelist()
            if n.lower().endswith((".xhtml", ".html", ".htm"))
            and "meta-inf" not in n.lower()
        ]
        names.sort()
        for name in names:
            raw = zf.read(name).decode("utf-8", errors="replace")
            # Tags grob entfernen
            t = re.sub(r"(?is)<script[^>]*>.*?</script>", "", raw)
            t = re.sub(r"(?is)<style[^>]*>.*?</style>", "", t)
            t = re.sub(r"(?i)<br\s*/?>", "\n", t)
            t = re.sub(r"(?i)</p>", "\n\n", t)
            t = re.sub(r"(?i)</h[1-6]>", "\n\n", t)
            t = re.sub(r"(?i)<h1[^>]*>", "# ", t)
            t = re.sub(r"(?i)<h2[^>]*>", "## ", t)
            t = re.sub(r"(?i)<h3[^>]*>", "### ", t)
            t = re.sub(r"<[^>]+>", "", t)
            t = html.unescape(t)
            t = re.sub(r"\n{3,}", "\n\n", t).strip()
            if t:
                parts.append(t)
    return "\n\n".join(parts).strip() + ("\n" if parts else "")


def _split_pptx_slides(text: str, *, default_title: str = "Folie") -> list[tuple[str, list[str]]]:
    """Text → Folien: Split an Markdown-H1 oder ``---``; Body → Bullet-Zeilen."""
    raw = (text or "").replace("\r\n", "\n").strip()
    if not raw:
        return [(default_title, [])]

    chunks: list[str] = []
    buf: list[str] = []
    for line in raw.split("\n"):
        if line.strip() == "---":
            chunks.append("\n".join(buf).strip())
            buf = []
            continue
        if line.startswith("# ") and not line.startswith("## "):
            if buf and any(x.strip() for x in buf):
                chunks.append("\n".join(buf).strip())
            buf = [line]
            continue
        buf.append(line)
    if buf and any(x.strip() for x in buf):
        chunks.append("\n".join(buf).strip())
    if not chunks:
        chunks = [raw]

    slides: list[tuple[str, list[str]]] = []
    for i, chunk in enumerate(chunks):
        lines = chunk.split("\n")
        title = f"{default_title} {i + 1}"
        body_lines = lines
        if lines and lines[0].startswith("# ") and not lines[0].startswith("## "):
            title = lines[0][2:].strip() or title
            body_lines = lines[1:]
        bullets: list[str] = []
        para_buf: list[str] = []

        def flush_para() -> None:
            nonlocal para_buf
            joined = " ".join(para_buf).strip()
            para_buf = []
            if joined:
                bullets.append(joined)

        for ln in body_lines:
            s = ln.strip()
            if not s:
                flush_para()
                continue
            if s.startswith("## "):
                flush_para()
                bullets.append(s[3:].strip())
                continue
            if s.startswith("### "):
                flush_para()
                bullets.append(s[4:].strip())
                continue
            m = re.match(r"^[-*+]\s+(.+)$", s) or re.match(r"^\d+\.\s+(.+)$", s)
            if m:
                flush_para()
                bullets.append(m.group(1).strip())
            else:
                para_buf.append(s)
        flush_para()
        slides.append((title, bullets))
    return slides


def _pptx_escape(s: str) -> str:
    return html.escape(s or "", quote=False)


def _pptx_text_runs_xml(lines: list[str], *, font_size_hundredths: int = 1800) -> str:
    """a:p Blöcke für Folienkörper."""
    if not lines:
        return (
            '<a:p><a:pPr marL="0"/><a:r><a:rPr lang="de-DE" dirty="0" sz="1400"/>'
            "<a:t> </a:t></a:r></a:p>"
        )
    parts: list[str] = []
    for line in lines:
        parts.append(
            "<a:p>"
            '<a:pPr marL="342900" indent="-342900">'
            '<a:buFont typeface="Arial"/><a:buChar char="•"/>'
            "</a:pPr>"
            f'<a:r><a:rPr lang="de-DE" dirty="0" sz="{font_size_hundredths}"/>'
            f"<a:t>{_pptx_escape(line)}</a:t></a:r></a:p>"
        )
    return "".join(parts)


def _pptx_slide_xml(title: str, bullets: list[str]) -> str:
    title_xml = (
        "<a:p><a:r>"
        '<a:rPr lang="de-DE" dirty="0" sz="3200" b="1"/>'
        f"<a:t>{_pptx_escape(title)}</a:t></a:r></a:p>"
    )
    body_xml = _pptx_text_runs_xml(bullets)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>
        <a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="2" name="Title 1"/><p:cNvSpPr><a:spLocks noGrp="1"/>
          </p:cNvSpPr><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>
        <p:spPr/>
        <p:txBody><a:bodyPr/><a:lstStyle/>{title_xml}</p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="3" name="Content 2"/><p:cNvSpPr><a:spLocks noGrp="1"/>
          </p:cNvSpPr><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr>
        <p:spPr/>
        <p:txBody><a:bodyPr/><a:lstStyle/>{body_xml}</p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>
"""


_PPTX_THEME = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="InstantLens">
  <a:themeElements>
    <a:clrScheme name="Office">
      <a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>
      <a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>
      <a:dk2><a:srgbClr val="1F497D"/></a:dk2>
      <a:lt2><a:srgbClr val="EEECE1"/></a:lt2>
      <a:accent1><a:srgbClr val="4F81BD"/></a:accent1>
      <a:accent2><a:srgbClr val="C0504D"/></a:accent2>
      <a:accent3><a:srgbClr val="9BBB59"/></a:accent3>
      <a:accent4><a:srgbClr val="8064A2"/></a:accent4>
      <a:accent5><a:srgbClr val="4BACC6"/></a:accent5>
      <a:accent6><a:srgbClr val="F79646"/></a:accent6>
      <a:hlink><a:srgbClr val="0000FF"/></a:hlink>
      <a:folHlink><a:srgbClr val="800080"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="Office">
      <a:majorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>
      <a:minorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>
    </a:fontScheme>
    <a:fmtScheme name="Office">
      <a:fillStyleLst>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
      </a:fillStyleLst>
      <a:lnStyleLst>
        <a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln>
        <a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln>
        <a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln>
      </a:lnStyleLst>
      <a:effectStyleLst>
        <a:effectStyle><a:effectLst/></a:effectStyle>
        <a:effectStyle><a:effectLst/></a:effectStyle>
        <a:effectStyle><a:effectLst/></a:effectStyle>
      </a:effectStyleLst>
      <a:bgFillStyleLst>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
      </a:bgFillStyleLst>
    </a:fmtScheme>
  </a:themeElements>
</a:theme>
"""

_PPTX_SLIDE_MASTER = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg><p:bgRef idx="1001"><a:schemeClr val="bg1"/></p:bgRef></p:bg>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>
        <a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="2" name="Title Placeholder"/><p:cNvSpPr><a:spLocks noGrp="1"/>
          </p:cNvSpPr><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="457200" y="274638"/><a:ext cx="8229600" cy="1143000"/>
          </a:xfrm></p:spPr>
        <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>Title</a:t></a:r></a:p></p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="3" name="Body Placeholder"/><p:cNvSpPr><a:spLocks noGrp="1"/>
          </p:cNvSpPr><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="457200" y="1600200"/><a:ext cx="8229600" cy="4525963"/>
          </a:xfrm></p:spPr>
        <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t></a:t></a:r></a:p></p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2"
    accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6"
    hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
</p:sldMaster>
"""

_PPTX_SLIDE_LAYOUT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="titleAndContent" preserve="1">
  <p:cSld name="Title and Content">
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>
        <a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="2" name="Title 1"/><p:cNvSpPr><a:spLocks noGrp="1"/>
          </p:cNvSpPr><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="457200" y="274638"/><a:ext cx="8229600" cy="1143000"/>
          </a:xfrm></p:spPr>
        <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t></a:t></a:r></a:p></p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="3" name="Content Placeholder 2"/><p:cNvSpPr><a:spLocks noGrp="1"/>
          </p:cNvSpPr><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="457200" y="1600200"/><a:ext cx="8229600" cy="4525963"/>
          </a:xfrm></p:spPr>
        <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:pPr lvl="0"/><a:r><a:t></a:t></a:r></a:p></p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>
"""


def export_pptx(
    text: str,
    path: str | Path,
    *,
    title: str = "InstantLens Doc",
) -> Path:
    """
    PowerPoint OOXML (.pptx) ohne python-pptx — Folien aus H1/``---``.

    Praktische Treue: Titel + Bullet-Body; Stdlib zipfile+XML.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    slides = _split_pptx_slides(text, default_title=title or "Folie")

    slide_overrides = []
    sld_id_lst = []
    pres_rels = [
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" '
        'Target="slideMasters/slideMaster1.xml"/>'
    ]
    for i in range(len(slides)):
        sid = i + 2  # rId2+ for slides
        rid = f"rId{sid}"
        slide_overrides.append(
            f'<Override PartName="/ppt/slides/slide{i + 1}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.'
            'presentationml.slide+xml"/>'
        )
        sld_id_lst.append(f'<p:sldId id="{256 + i}" r:id="{rid}"/>')
        pres_rels.append(
            f'<Relationship Id="{rid}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            f'Target="slides/slide{i + 1}.xml"/>'
        )

    content_types = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml"
    ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml"
    ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml"
    ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
  <Override PartName="/ppt/theme/theme1.xml"
    ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
  <Override PartName="/docProps/core.xml"
    ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml"
    ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  {"".join(slide_overrides)}
</Types>
"""
    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
    Target="ppt/presentation.xml"/>
  <Relationship Id="rId2"
    Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties"
    Target="docProps/core.xml"/>
  <Relationship Id="rId3"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties"
    Target="docProps/app.xml"/>
</Relationships>
"""
    presentation = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst>
    <p:sldMasterId id="2147483648" r:id="rId1"/>
  </p:sldMasterIdLst>
  <p:sldIdLst>
    {"".join(sld_id_lst)}
  </p:sldIdLst>
  <p:sldSz cx="9144000" cy="6858000" type="screen4x3"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>
"""
    pres_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        + "\n".join(f"  {r}" for r in pres_rels)
        + "\n</Relationships>\n"
    )
    master_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout"
    Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme"
    Target="../theme/theme1.xml"/>
</Relationships>
"""
    layout_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster"
    Target="../slideMasters/slideMaster1.xml"/>
</Relationships>
"""
    slide_rel = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout"
    Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>
"""
    core = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{_pptx_escape(title)}</dc:title>
  <dc:creator>InstantLens Doc</dc:creator>
  <cp:lastModifiedBy>InstantLens Doc</cp:lastModifiedBy>
</cp:coreProperties>
"""
    app = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>InstantLens Doc</Application>
  <Slides>{len(slides)}</Slides>
  <PresentationFormat>On-screen Show (4:3)</PresentationFormat>
</Properties>
"""

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("ppt/presentation.xml", presentation)
        zf.writestr("ppt/_rels/presentation.xml.rels", pres_rels_xml)
        zf.writestr("ppt/slideMasters/slideMaster1.xml", _PPTX_SLIDE_MASTER)
        zf.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", master_rels)
        zf.writestr("ppt/slideLayouts/slideLayout1.xml", _PPTX_SLIDE_LAYOUT)
        zf.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", layout_rels)
        zf.writestr("ppt/theme/theme1.xml", _PPTX_THEME)
        zf.writestr("docProps/core.xml", core)
        zf.writestr("docProps/app.xml", app)
        for i, (slide_title, bullets) in enumerate(slides, start=1):
            zf.writestr(f"ppt/slides/slide{i}.xml", _pptx_slide_xml(slide_title, bullets))
            zf.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", slide_rel)
    path.write_bytes(buf.getvalue())
    return path


def import_pptx(path: str | Path) -> str:
    """PowerPoint .pptx → Markdown (``# Titel`` + Body) — praktische Treue."""
    path = Path(path)
    ns = {
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    parts: list[str] = []
    with zipfile.ZipFile(path, "r") as zf:
        # Folienreihenfolge aus presentation.xml
        slide_targets: list[str] = []
        try:
            pres = zf.read("ppt/presentation.xml")
            root = ET.fromstring(pres)
            rels_root = ET.fromstring(zf.read("ppt/_rels/presentation.xml.rels"))
            rid_to_target = {
                rel.get("Id"): rel.get("Target")
                for rel in rels_root
                if rel.get("Id") and rel.get("Target")
            }
            for sld in root.findall(".//p:sldId", ns):
                rid = sld.get(
                    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                )
                tgt = rid_to_target.get(rid or "")
                if tgt:
                    if tgt.startswith("/"):
                        slide_targets.append(tgt.lstrip("/"))
                    elif tgt.startswith("ppt/"):
                        slide_targets.append(tgt)
                    else:
                        slide_targets.append("ppt/" + tgt.lstrip("./"))
        except Exception:
            slide_targets = []
        if not slide_targets:
            slide_targets = sorted(
                n for n in zf.namelist() if re.search(r"ppt/slides/slide\d+\.xml$", n, re.I)
            )

        for name in slide_targets:
            try:
                raw = zf.read(name)
            except KeyError:
                continue
            try:
                sroot = ET.fromstring(raw)
            except ET.ParseError:
                continue
            texts: list[str] = []
            for t_el in sroot.findall(".//a:t", ns):
                if t_el.text and t_el.text.strip():
                    texts.append(t_el.text.strip())
            if not texts:
                # Fallback: Regex
                decoded = raw.decode("utf-8", errors="replace")
                texts = [
                    html.unescape(m)
                    for m in re.findall(r"<a:t[^>]*>(.*?)</a:t>", decoded)
                    if m.strip()
                ]
            if not texts:
                continue
            title = texts[0]
            body = texts[1:]
            block = f"# {title}"
            if body:
                block += "\n\n" + "\n".join(
                    (f"- {b}" if not b.startswith("- ") else b) for b in body
                )
            parts.append(block)
    return "\n\n".join(parts).strip() + ("\n" if parts else "")


def export_docx(text: str, path: str | Path, *, title: Optional[str] = None, html: Optional[str] = None) -> Path:
    """DOCX mit Absätzen; optional HTML mit Bold/Italic/Underline — 2.6.49."""
    if html:
        from instantlensdoc.core.richtext_docx import html_to_docx

        return html_to_docx(html, path, title=title)

    # Markdown-ähnliche Marker im Plaintext → echte Runs
    stripped = (text or "").lstrip().lower()
    if "<b>" in stripped or "<i>" in stripped or "<u>" in stripped or "<p" in stripped:
        from instantlensdoc.core.richtext_docx import html_to_docx

        return html_to_docx(text, path, title=title)

    try:
        from docx import Document as DocxDocument
        from docx.shared import Pt
    except ImportError as e:
        raise RuntimeError("python-docx fehlt zum DOCX-Export") from e

    path = Path(path)
    d = DocxDocument()
    if title:
        d.core_properties.title = title
    style = d.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    for line in _lines(text):
        raw = line.rstrip()
        if not raw:
            d.add_paragraph("")
            continue
        if raw.startswith("### "):
            d.add_heading(raw[4:], level=3)
        elif raw.startswith("## "):
            d.add_heading(raw[3:], level=2)
        elif raw.startswith("# "):
            d.add_heading(raw[2:], level=1)
        elif re.match(r"^[-*]\s+", raw):
            d.add_paragraph(re.sub(r"^[-*]\s+", "", raw), style="List Bullet")
        else:
            # Inline **bold** / *italic* / __underline__ → echte Runs
            _add_paragraph_with_md_runs(d, raw)
    d.save(str(path))
    return path


def _add_paragraph_with_md_runs(doc: Any, raw: str) -> None:
    """Konvertiert einfache Markdown-Inline-Marker in DOCX-Runs (Export-Hilfe)."""
    para = doc.add_paragraph("")
    # **bold** | __underline__ | *italic* (nicht gierig)
    pattern = re.compile(r"(\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*)")
    pos = 0
    for m in pattern.finditer(raw or ""):
        if m.start() > pos:
            para.add_run(raw[pos : m.start()])
        token = m.group(0)
        if token.startswith("**") and token.endswith("**"):
            run = para.add_run(token[2:-2])
            run.bold = True
        elif token.startswith("__") and token.endswith("__"):
            run = para.add_run(token[2:-2])
            run.underline = True
        elif token.startswith("*") and token.endswith("*"):
            run = para.add_run(token[1:-1])
            run.italic = True
        else:
            para.add_run(token)
        pos = m.end()
    if pos < len(raw or ""):
        para.add_run(raw[pos:])
    if pos == 0 and not (raw or ""):
        para.add_run("")


def resolve_page_size(name_or_size: str | tuple[float, float] | None = None) -> tuple[float, float]:
    """Seitenformat aus Preset-Name oder Tupel; Default aus Einstellungen."""
    if isinstance(name_or_size, tuple) and len(name_or_size) == 2:
        return float(name_or_size[0]), float(name_or_size[1])
    from ild_pdf.pages import PAGE_SIZE_PRESETS

    name = name_or_size
    if not name:
        try:
            from instantlensdoc.core.app_settings import get_export_pdf_page

            name = get_export_pdf_page()
        except Exception:
            name = "A4"
    return PAGE_SIZE_PRESETS.get(str(name), PAGE_SIZE_PRESETS["A4"])


PDF_RICH_CREATOR = "InstantLens Doc (QTextDocument → QPdfWriter)"


def _export_pdf_rich_qt(
    html: str,
    dest: Path,
    *,
    title: str,
    page_size_pt: tuple[float, float],
) -> Path | None:
    """Formatiertes HTML (DOCX/HTML-Editor) über Qt als PDF setzen — 2.6.54.

    Liefert ``None``, wenn keine ``QGuiApplication`` läuft (CLI/Tests ohne Qt) —
    der Aufrufer fällt dann auf ``text_to_pdf`` zurück. Schreibt in eine Temp-Datei,
    validiert (Header/EOF/pikepdf) und ersetzt erst dann das Ziel.
    """
    import os

    try:
        from PySide6.QtCore import QMarginsF, QSizeF
        from PySide6.QtGui import (
            QFont,
            QGuiApplication,
            QPageLayout,
            QPageSize,
            QPdfWriter,
            QTextDocument,
        )
    except Exception:
        return None
    if QGuiApplication.instance() is None:
        return None
    from ild_pdf.pdf_sniff import assert_valid_pdf

    tmp = dest.with_name(f".{dest.name}.ild-tmp{os.getpid()}")
    try:
        writer = QPdfWriter(str(tmp))
        writer.setTitle(str(title or "InstantLens Doc"))
        writer.setCreator(PDF_RICH_CREATOR)
        writer.setPageSize(QPageSize(QSizeF(float(page_size_pt[0]), float(page_size_pt[1])), QPageSize.Point))
        writer.setPageMargins(QMarginsF(20.0, 20.0, 20.0, 20.0), QPageLayout.Millimeter)
        doc = QTextDocument()
        base = QFont("Calibri", 11)
        base.setStyleHint(QFont.SansSerif)
        doc.setDefaultFont(base)
        doc.setHtml(html or "")
        if not doc.toPlainText().strip():
            # Leeres HTML → leere Seite wäre ok, aber Plaintext-Pfad ist klarer
            return None
        doc.print_(writer)
        # QPdfWriter schreibt beim Painter-Ende; Objekt freigeben, bevor gelesen wird
        del doc
        del writer
        assert_valid_pdf(tmp, remove_invalid=True)
        os.replace(tmp, dest)
        return dest
    except Exception as e:
        logging.getLogger("instantlensdoc.export").warning(
            "Rich-PDF über QPdfWriter fehlgeschlagen (%s) — Fallback Text→PDF", e
        )
        return None
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def export_pdf(
    text: str,
    path: str | Path,
    *,
    title: str = "InstantLens Doc",
    page_size: tuple[float, float] | str | None = None,
    html: Optional[str] = None,
) -> Path:
    """
    Mehrseiten-PDF aus dem Editor-Inhalt — 1.7.0 / 2.6.54.

    ``html`` (DOCX/HTML-Dokument mit Zeichenformaten) wird — wenn eine Qt-GUI läuft —
    über ``QTextDocument`` + ``QPdfWriter`` gesetzt (Fett/Kursiv/Überschriften/
    Schriften erhalten). Sonst bzw. als Fallback: Plaintext via
    ``ild_pdf.text_pdf.text_to_pdf`` (Helvetica/pikepdf).
    Jede Ausgabe wird nach dem Schreiben validiert (``%PDF-``, ``%%EOF``, pikepdf) —
    es bleibt nie eine Datei mit .pdf-Endung und fremdem Inhalt zurück.
    page_size: Tupel, Preset-Name oder None (= Einstellung/A4).
    """
    from ild_pdf.pdf_sniff import assert_valid_pdf
    from ild_pdf.text_pdf import text_to_pdf

    dest = Path(path)
    size_pt = resolve_page_size(page_size)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if html and str(html).strip():
        out = _export_pdf_rich_qt(str(html), dest, title=title, page_size_pt=size_pt)
        if out is not None:
            return out
    out = text_to_pdf(text or "", dest, title=title, page_size=size_pt)
    assert_valid_pdf(out)
    return out


def export_txt(text: str, path: str | Path, *, encoding: str = "utf-8") -> Path:
    """Plaintext speichern — 2.6.14."""
    path = Path(path)
    path.write_text(text or "", encoding=encoding, errors="replace")
    return path


def _rtf_escape(s: str) -> str:
    out: list[str] = []
    for ch in s or "":
        o = ord(ch)
        if ch in {"\\", "{", "}"}:
            out.append("\\" + ch)
        elif ch == "\n":
            out.append("\\par\n")
        elif ch == "\t":
            out.append("\\tab ")
        elif o < 128:
            out.append(ch)
        else:
            out.append(f"\\u{o}?")
    return "".join(out)


def export_rtf(text: str, path: str | Path, *, title: Optional[str] = None, html: Optional[str] = None) -> Path:
    """Einfaches RTF (Absätze, Überschriften #/##); optional HTML mit Formaten — 2.6.49."""
    if html:
        from instantlensdoc.core.richtext_docx import html_to_rtf

        return html_to_rtf(html, path, title=title)
    stripped = (text or "").lstrip().lower()
    if "<b>" in stripped or "<i>" in stripped or "<u>" in stripped or "font-weight" in stripped:
        from instantlensdoc.core.richtext_docx import html_to_rtf

        return html_to_rtf(text, path, title=title)

    path = Path(path)
    parts = [
        r"{\rtf1\ansi\deff0",
        r"{\fonttbl{\f0 Times New Roman;}{\f1 Segoe UI;}}",
    ]
    if title:
        parts.append(r"{\info{\title " + _rtf_escape(title) + "}}")
    parts.append(r"\f0\fs22 ")
    for line in _lines(text):
        raw = line.rstrip()
        if not raw:
            parts.append(r"\par")
            continue
        if raw.startswith("### "):
            parts.append(r"\f1\fs24\b " + _rtf_escape(raw[4:]) + r"\b0\f0\fs22\par")
        elif raw.startswith("## "):
            parts.append(r"\f1\fs28\b " + _rtf_escape(raw[3:]) + r"\b0\f0\fs22\par")
        elif raw.startswith("# "):
            parts.append(r"\f1\fs32\b " + _rtf_escape(raw[2:]) + r"\b0\f0\fs22\par")
        else:
            parts.append(_rtf_escape(raw) + r"\par")
    parts.append("}")
    path.write_text("".join(parts), encoding="utf-8", errors="replace")
    return path


def import_rtf(path: str | Path) -> str:
    """Grober RTF→Text-Import (Steuerworte entfernen) — 2.6.14."""
    raw = Path(path).read_text(encoding="utf-8", errors="replace")
    # Unicode escapes \uN?
    def _u_repl(m: re.Match[str]) -> str:
        try:
            return chr(int(m.group(1)))
        except ValueError:
            return ""

    raw = re.sub(r"\\u(-?\d+)\??", _u_repl, raw)
    raw = raw.replace("\\par", "\n").replace("\\tab", "\t").replace("\\line", "\n")
    # Drop groups like {\*\…} roughly
    raw = re.sub(r"\{\\\*[^}]*\}", "", raw)
    raw = re.sub(r"\\[a-zA-Z]+\d* ?", "", raw)
    raw = raw.replace("{", "").replace("}", "").replace("\\\\", "\\")
    return raw.strip() + ("\n" if raw.strip() else "")


def export_xlsx_from_text(
    text: str,
    path: str | Path,
    *,
    sheet_name: str = "Tabelle1",
) -> Path:
    """Tabellen aus Text (Markdown/ild-table) oder Zeilen→XLSX — 2.6.14."""
    from ild_pdf.tables import (
        create_table,
        export_table_xlsx,
        find_tables_in_text,
        parse_table,
    )

    path = Path(path)
    found = find_tables_in_text(text or "")
    if found:
        return export_table_xlsx(found[0][2], path, sheet_name=sheet_name)
    # Fallback: Zeilen als einspaltige Tabelle / TSV
    rows: list[list[str]] = []
    for line in _lines(text):
        if "\t" in line:
            rows.append(line.split("\t"))
        elif ";" in line and line.count(";") >= 1:
            rows.append([c.strip() for c in line.split(";")])
        else:
            rows.append([line])
    if not rows:
        rows = [[""]]
    return export_table_xlsx(create_table(data=rows, header=False), path, sheet_name=sheet_name)


def export_jpg(
    text: str,
    path: str | Path,
    *,
    title: str = "InstantLens Doc",
    width: int = 1200,
    margin: int = 40,
    bg: str = "#FFFFFF",
    fg: str = "#1A1A1A",
) -> Path:
    """Text als JPEG-Bild (Pillow) — 2.6.14."""
    from PIL import Image, ImageDraw, ImageFont

    path = Path(path)
    lines = _lines(text)
    if not lines:
        lines = [title or " "]
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 18)
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
        title_font = font
    line_h = 24
    height = margin * 2 + line_h * (len(lines) + 2)
    height = max(height, 200)
    img = Image.new("RGB", (int(width), int(height)), bg)
    draw = ImageDraw.Draw(img)
    y = margin
    if title:
        draw.text((margin, y), title, fill=fg, font=title_font)
        y += line_h + 8
    for line in lines[:200]:
        draw.text((margin, y), line[:200], fill=fg, font=font)
        y += line_h
        if y > height - margin:
            break
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path), format="JPEG", quality=90)
    return path


def export_document(
    text: str,
    path: str | Path,
    *,
    fmt: str | None = None,
    title: str = "InstantLens Doc",
    page_size: tuple[float, float] | str | None = None,
    author: str = "InstantLens Doc",
    html: Optional[str] = None,
) -> Path:
    """Unified Export nach Erweiterung/Format — 2.6.14 / EPUB 2.6.26 / Rich-PDF 2.6.54.

    ``html``: formatierter Editor-Inhalt (DOCX/HTML) — PDF/DOCX/RTF nutzen ihn,
    um Zeichenformate zu erhalten; andere Formate ignorieren ihn.
    """
    path = Path(path)
    f = (fmt or path.suffix.lstrip(".")).lower().lstrip(".")
    if f == "jpeg":
        f = "jpg"
    if f == "htm":
        f = "html"
    if f == "html":
        return export_html(text, path, title=title)
    if f == "docx":
        return export_docx(text, path, title=title, html=html)
    if f == "pdf":
        return export_pdf(text, path, title=title, page_size=page_size, html=html)
    if f == "txt":
        return export_txt(text, path)
    if f == "rtf":
        return export_rtf(text, path, title=title, html=html)
    if f == "xlsx":
        return export_xlsx_from_text(text, path)
    if f == "jpg":
        return export_jpg(text, path, title=title)
    if f == "epub":
        return export_epub(text, path, title=title, author=author)
    if f == "pptx":
        return export_pptx(text, path, title=title)
    raise ValueError(f"Unbekanntes Export-Format: {f}")


def import_document_text(path: str | Path) -> dict[str, Any]:
    """Unified Import → Plaintext (+ Meta) — 2.6.14."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    ext = path.suffix.lower().lstrip(".")
    meta: dict[str, Any] = {"path": str(path), "format": ext}
    if ext == "epub":
        return {"text": import_epub(path), "meta": meta}
    if ext == "pptx":
        return {"text": import_pptx(path), "meta": meta}
    if ext in ("txt", "log", "md", "markdown", "html", "htm", "csv"):
        if ext == "csv":
            from ild_pdf.tables import import_csv, table_to_markdown

            table = import_csv(path)
            return {"text": table_to_markdown(table), "meta": {**meta, "table": table.to_dict()}}
        text = path.read_text(encoding="utf-8", errors="replace")
        return {"text": text, "meta": meta}
    if ext == "rtf":
        return {"text": import_rtf(path), "meta": meta}
    if ext == "docx":
        try:
            from instantlensdoc.core.richtext_docx import docx_plain_and_html

            plain, html = docx_plain_and_html(path)
            return {
                "text": plain,
                "meta": {**meta, "html": html, "rich_text": True},
            }
        except Exception:
            try:
                from docx import Document as DocxDocument

                from ild_pdf.tables import create_table, table_to_markdown

                d = DocxDocument(str(path))
                parts: list[str] = [p.text for p in d.paragraphs]
                for ti, tbl in enumerate(d.tables):
                    cells = [[(c.text or "") for c in row.cells] for row in tbl.rows]
                    parts.append(
                        table_to_markdown(create_table(data=cells, table_id=f"docx{ti + 1}"))
                    )
                return {"text": "\n".join(parts), "meta": meta}
            except ImportError as e:
                raise RuntimeError("python-docx fehlt zum DOCX-Import") from e
    if ext == "xlsx":
        from ild_pdf.tables import import_xlsx, table_to_markdown

        table = import_xlsx(path)
        return {"text": table_to_markdown(table), "meta": {**meta, "table": table.to_dict()}}
    if ext == "pdf":
        try:

            from ild_pdf.pdfium_open import open_pdfium

            doc = open_pdfium(path)
            try:
                chunks: list[str] = []
                for i in range(len(doc)):
                    page = doc[i]
                    try:
                        textpage = page.get_textpage()
                        try:
                            chunks.append(textpage.get_text_bounded() or "")
                        finally:
                            textpage.close()
                    except Exception:
                        chunks.append("")
                return {
                    "text": "\n\n".join(chunks).strip() + ("\n" if chunks else ""),
                    "meta": {**meta, "pages": len(doc)},
                }
            finally:
                doc.close()
        except Exception:
            return {"text": "", "meta": {**meta, "note": "PDF ohne Textlayer"}}
    if ext in ("jpg", "jpeg", "png", "bmp", "gif", "webp"):
        return {"text": f"[Bild: {path.name}]\n", "meta": {**meta, "image": str(path)}}
    # Fallback plaintext
    return {"text": path.read_text(encoding="utf-8", errors="replace"), "meta": meta}
