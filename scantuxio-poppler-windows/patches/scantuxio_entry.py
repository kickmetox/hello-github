"""
Drop-in / Patch-Vorlage für scantuxio_entry.py — pypdfium2-Backend.

Ohne Original-Quellbaum: bootstrap früh aufrufen; PDF-Aufrufe auf
pdf_render.convert_from_path umbiegen (statt pdf2image/Poppler).
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _p in (_HERE, _HERE / "python", _HERE.parent / "python"):
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from pdf_render import bootstrap_for_entry  # noqa: E402


def main() -> int:
    info = bootstrap_for_entry()
    if not info.ok:
        sys.stderr.write(
            "[ScanTuxio] PDF-Rasterung nicht bereit. "
            "pip install pypdfium2 pillow  bzw. Frozen-Build mit --collect-all pypdfium2.\n"
        )

    for mod_name in ("scantuxio", "scantuxio_app", "main", "app"):
        try:
            mod = __import__(mod_name)
        except ImportError:
            continue
        for attr in ("main", "run"):
            if hasattr(mod, attr):
                result = getattr(mod, attr)()
                return int(result or 0)

    sys.stderr.write(
        "[ScanTuxio] Kein App-Hauptmodul gefunden. "
        "bootstrap_for_entry() ist aktiv — Original-Start hinter dem Aufruf einfügen "
        "und PDF-Code auf pdf_render umstellen.\n"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
