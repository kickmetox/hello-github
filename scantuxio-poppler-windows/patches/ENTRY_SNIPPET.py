# Einfügen ganz oben in die bestehende scantuxio_entry.py (nach imports).

import sys
from pathlib import Path

# poppler_paths.py nach: <app>/python/ oder <app>/
_root = Path(__file__).resolve().parent
for _p in (_root / "python", _root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from poppler_paths import ensure_poppler

_poppler = ensure_poppler(required=False)
if not _poppler.ok:
    sys.stderr.write(f"[ScanTuxio] {_poppler.message}\n")
# Danach unverändert: restlicher Entry / App-Start
