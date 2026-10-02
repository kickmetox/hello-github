# Einfügen ganz oben in die bestehende scantuxio_entry.py (nach imports).

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
for _p in (_root / "python", _root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from pdf_render import bootstrap_for_entry, convert_from_path, ensure_pdf_backend

_pdf = bootstrap_for_entry()
# Optional hart: ensure_pdf_backend(required=True)

# PDF-Stellen im restlichen Code ersetzen:
#   alt: from pdf2image import convert_from_path
#   neu: from pdf_render import convert_from_path
# (Signatur: convert_from_path(path, dpi=200, first_page=…, last_page=…))
