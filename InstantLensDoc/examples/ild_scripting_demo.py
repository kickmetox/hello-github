"""Beispiel: InstantLens Doc Scripting (Python) — 2.6.13.

Aufruf aus dem App-Root:
  python examples/ild_scripting_demo.py [pdf]
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ild
from ild_pdf.text_pdf import text_to_pdf


def main() -> int:
    print("InstantLens Doc", ild.version)
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        src = Path(sys.argv[1]) if len(sys.argv) > 1 else td_p / "demo.pdf"
        if not src.is_file():
            text_to_pdf("Scripting-Demo InstantLens Doc", src)
        info = ild.open_info(src)
        print("info:", info)
        print("pages:", ild.page_count(src))
        png = td_p / "p1.png"
        ild.export_page(src, 1, png, dpi=72)
        print("export:", png.exists(), png)
        key = ild.generate_key("demo@example.com", days=10)
        print("key:", key[:20] + "…")
        print("verify:", ild.verify_key(key)["ok"])
        print("license:", ild.license_status()["mode"])
        shape = ild.add_shape(
            src, page=1, kind="ellipse", x=20, y=20, width=80, height=40, filled=True
        )
        print("shape:", shape.get("type"), shape.get("id"))
        stamp = ild.add_stamp(src, page=1, text="Paid")
        print("stamp:", stamp.get("text"))
        hl = ild.highlight_paragraphs(src, page=1, x=0, y=0, width=400, height=200)
        print("paragraph highlights:", hl.get("count"))
        print("stamps:", [s.get("label") for s in ild.list_stamps()][:8])
        fmt = ild.auto_format_text("EINLEITUNG\n\nFließtext Demo.\n")
        print("auto_format headings:", len(fmt.get("headings") or []))
        toc = ild.generate_toc(path=src)
        print("toc outline_count:", toc.get("outline_count"))
        fonts = ild.list_system_fonts()
        print("fonts sample:", fonts[:5])
        fr = ild.find_replace(text="a b a", find="a", replace="X")
        print("find_replace:", fr.get("count"), fr.get("text"))
        print("page formats:", [f["name"] for f in ild.list_page_formats()][:6])
        para = ild.apply_paragraph_format(text="Demo Absatz", alignment="center")
        print("paragraph:", "ild-align" in para.get("text", ""))
        print("satzspiegel", ild.satzspiegel("A4")["format_name"])
        print("masters", [m["id"] for m in ild.list_master_pages()])
        flow = ild.layout_flow_text("Demo " * 40, columns=2)
        print("layout chain", flow["chain"])
        typo = ild.apply_typography(text="Typo Demo", tracking=40, leading=1.5)
        print("typography:", "ild-typo" in typo.get("text", ""))
        hy = ild.hyphenate("Silbentrennung", lang="de")
        print("hyphenate count:", hy.get("count"))
        dc = ild.apply_drop_cap("Kapitelstart mit Initial.", lines=3)
        print("drop_cap:", "ild-dropcap" in dc.get("text", ""))
        img_add = ild.layout_add_image_frame(layout=flow["layout"], image="x.png")
        wrap = ild.layout_set_text_wrap(
            img_add["frame"]["id"], "bounding_box", layout=img_add["layout"]
        )
        print("text_wrap:", wrap["frame"].get("text_wrap"))
        hf = ild.apply_header_footer(
            src, out=td_p / "hf.pdf", header="{title}", footer="{author}", title="Demo", author="ILD"
        )
        print("header_footer:", Path(hf["path"]).exists())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
