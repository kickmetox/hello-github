"""Beispiel: InstantLens Doc Scripting (Python) — 2.6.8.

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
