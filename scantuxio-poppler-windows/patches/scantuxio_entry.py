"""
Drop-in / Patch-Vorlage für scantuxio_entry.py

Wenn der Original-Entry nur Bootstrapping macht: diese Datei als
scantuxio_entry.py ersetzen ODER den Block ensure_poppler() ganz oben
in den bestehenden Entry einfügen (siehe patches/ENTRY_SNIPPET.py).

Ohne vollständigen Quellbaum kann die frozen ScanTuxio.exe diesen
Python-Entry nur nutzen, wenn das Build-Layout den Entry noch lädt
(z. B. Dev-Start via run.bat → python scantuxio_entry.py). Für die
fertige EXE muss Poppler über PATH/Bundle + Installer greifen; der
Finder wird erst nach Rebuild mit diesem Modul aktiv.
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

# Sicherstellen, dass python/ neben dem Entry importierbar ist
_HERE = Path(__file__).resolve().parent
for _p in (_HERE, _HERE / "python", _HERE.parent / "python"):
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from poppler_paths import ensure_poppler
except ImportError:
    # Fallback: Modul liegt ggf. im gleichen Ordner wie die EXE
    sys.path.insert(0, str(_HERE))
    from poppler_paths import ensure_poppler  # type: ignore


def _warn(msg: str) -> None:
    # Kein harter Exit: App soll starten; PDF-Raster fehlt dann ggf.
    sys.stderr.write(f"[ScanTuxio] {msg}\n")
    # Optional: Logdatei neben der App
    try:
        log = Path(getattr(sys, "executable", ".")).resolve().parent / "scantuxio-poppler.log"
        if not getattr(sys, "frozen", False):
            log = _HERE / "scantuxio-poppler.log"
        with log.open("a", encoding="utf-8") as fh:
            fh.write(msg + "\n")
    except OSError:
        pass


def bootstrap_poppler() -> bool:
    info = ensure_poppler(required=False)
    if info.ok:
        _warn(info.message)
        return True
    _warn(info.message)
    _warn(
        "PDF→Bild (Poppler) nicht verfügbar. Installer/vendor/poppler prüfen "
        "oder SCANTUXIO_POPPLER auf den bin-Ordner setzen."
    )
    return False


def main() -> int:
    bootstrap_poppler()

    # --- Bestehenden App-Start hier belassen / anbinden ---
    # Ohne Original-Quellcode: versuche gängige Modulnamen.
    for mod_name in ("scantuxio", "scantuxio_app", "main", "app"):
        try:
            mod = __import__(mod_name)
        except ImportError:
            continue
        if hasattr(mod, "main"):
            result = mod.main()
            return int(result or 0)
        if hasattr(mod, "run"):
            result = mod.run()
            return int(result or 0)

    _warn(
        "Kein App-Hauptmodul gefunden (scantuxio/main/app). "
        "Poppler-Bootstrap ist aktiv; Original-Entry-Logik muss manuell "
        "hinter bootstrap_poppler() eingefügt werden."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
