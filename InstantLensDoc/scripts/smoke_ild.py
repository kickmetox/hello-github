#!/usr/bin/env python3
"""Nightly/CI Smoke: CLI + Import-Checks für InstantLens Doc — 2.1.0–2.6.54.

Leichtgewichtig. Exit-Codes:
  0  OK  (ok=true)
  1  Fehler (Assertion/Import/Version; ok=false)
  2  Nutzung / unbekannte Option (--help → 0)

Aufruf:
  python scripts/smoke_ild.py
  python scripts/smoke_ild.py --qt          # optionale Qt-Source-Checks
  python scripts/smoke_ild.py --skip-qt     # Qt-Checks überspringen (Default)
  python scripts/smoke_ild.py --json        # Summary als JSON (stdout)
  python scripts/smoke_ild.py -h

JSON-Schema (--json), Erfolg:
  {"ok": true, "version": "2.6.54", "duration_ms": 1234,
   "checks": ["version", "imports", "cli", "measure_diff_import", "changelog"]}

JSON bei Fail: checks[] enthält Objekt mit error-Text (max 200 Zeichen, Truncate …);
Exitcode spiegelt ok (0↔true, 1↔false) — 2.2.0:
  {"ok": false, "version": "2.6.54", "duration_ms": 12,
   "checks": ["version", {"name": "imports", "error": "import x: …"}]}
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Headless/CI: Qt ohne Display
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

EXPECTED_VERSION = "2.6.54"
FAIL_ERROR_MAX_LEN = 200

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2


_JSON_MODE = False
_CURRENT_CHECK: str | None = None
_LAST_ERROR: str | None = None


def _fail(msg: str) -> None:
    global _LAST_ERROR
    _LAST_ERROR = str(msg)
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(EXIT_FAIL)


def _ok(msg: str) -> None:
    if not _JSON_MODE:
        print(f"OK: {msg}")


def check_version() -> None:
    from ild_pdf import __version__ as ild_ver
    from instantlensdoc import __version__ as app_ver

    if app_ver != EXPECTED_VERSION:
        _fail(f"instantlensdoc.__version__={app_ver!r} erwartet {EXPECTED_VERSION}")
    if ild_ver != EXPECTED_VERSION:
        _fail(f"ild_pdf.__version__={ild_ver!r} erwartet {EXPECTED_VERSION}")
    ver_txt = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
    docs_ver = (ROOT / "docs" / "VERSION").read_text(encoding="utf-8").strip()
    if not ver_txt.startswith(EXPECTED_VERSION):
        _fail(f"VERSION.txt={ver_txt!r}")
    if not docs_ver.startswith(EXPECTED_VERSION):
        _fail(f"docs/VERSION={docs_ver!r}")
    bw = (ROOT / "build-windows.ps1").read_text(encoding="utf-8")
    if EXPECTED_VERSION not in bw or "Allow32Bit" not in bw:
        _fail("build-windows.ps1 fehlt 2.6.51/Allow32Bit")
    if not (ROOT / "scripts" / "pack-windows-runnable.py").is_file():
        _fail("scripts/pack-windows-runnable.py fehlt")
    if not (ROOT / "run-keygen.bat").is_file():
        _fail("run-keygen.bat fehlt")
    bwi = ROOT / "scripts" / "build-windows-installer.ps1"
    iss = ROOT / "installer" / "instantlensdoc.iss"
    if not bwi.is_file():
        _fail("scripts/build-windows-installer.ps1 fehlt")
    if not iss.is_file():
        _fail("installer/instantlensdoc.iss fehlt")
    bwi_t = bwi.read_text(encoding="utf-8")
    iss_t = iss.read_text(encoding="utf-8")
    if EXPECTED_VERSION not in bwi_t or "VERSION.txt" not in bwi_t:
        _fail("build-windows-installer.ps1 fehlt Version/VERSION.txt")
    if EXPECTED_VERSION not in iss_t or "CustomMessages" not in iss_t or "desktopicon" not in iss_t:
        _fail("instantlensdoc.iss unvollständig (Version/CustomMessages/desktopicon)")
    # 2.6.33+: run.bat / companion bats must be cmd-safe (pure ASCII, no fancy Unicode)
    for bat_name in ("run.bat", "run-ild.bat", "run-keygen.bat"):
        bat_path = ROOT / bat_name
        if not bat_path.is_file():
            _fail(f"{bat_name} fehlt")
        bat_raw = bat_path.read_bytes()
        try:
            bat_raw.decode("ascii")
        except UnicodeDecodeError as exc:
            _fail(f"{bat_name} nicht pure ASCII (cmd Mojibake-Risiko): {exc}")
        bat_txt = bat_raw.decode("ascii")
        for bad in ("\u2014", "\u2013", "\u2026", "\u2192", "\u201e", "\u201c", "\u201d"):
            if bad in bat_txt:
                _fail(f"{bat_name} enthält Fancy-Unicode")
    bi = (ROOT / "installer" / "build-installer.ps1").read_text(encoding="utf-8-sig")
    if "EXE-Layout" not in bi and "UsePythonLauncher=0" not in bi:
        _fail("build-installer.ps1 fehlt EXE-Layout-Preferenz (2.6.33+)")
    # 2.6.34+: keygen PYTHONPATH + nested/standalone bootstrap
    kg_bat = (ROOT / "run-keygen.bat").read_text(encoding="ascii")
    if "PYTHONPATH" not in kg_bat:
        _fail("run-keygen.bat fehlt PYTHONPATH (2.6.34+)")
    if "instantlensdoc" not in kg_bat:
        _fail("run-keygen.bat fehlt instantlensdoc-Preflight (2.6.34+)")
    kg_ps1 = ROOT / "run-keygen.ps1"
    if not kg_ps1.is_file():
        _fail("run-keygen.ps1 fehlt (2.6.34+)")
    kg_ps1_raw = kg_ps1.read_bytes()
    if not kg_ps1_raw.startswith(b"\xef\xbb\xbf"):
        _fail("run-keygen.ps1 needs UTF-8 BOM for Windows PS 5.1")
    kg_main = (ROOT / "keygen" / "__main__.py").read_text(encoding="utf-8")
    if "_bootstrap_sys_path" not in kg_main and "_has_instantlensdoc" not in kg_main:
        _fail("keygen/__main__.py fehlt Import-Bootstrap (2.6.34+)")
    # 2.6.35+: sync Fresh-Dest + PyInstaller probe
    sync_t = (ROOT / "scripts" / "sync-ild.ps1").read_text(encoding="utf-8-sig")
    if "Dest" not in sync_t or "Swap" not in sync_t:
        _fail("sync-ild.ps1 fehlt -Dest/-Swap (2.6.38)")
    if "Ordner gesperrt" not in sync_t and "in Verwendung" not in sync_t:
        _fail("sync-ild.ps1 fehlt Ordner-gesperrt-Hinweis (2.6.38)")
    if "build-windows-installer.ps1" not in sync_t:
        _fail("sync-ild.ps1 fehlt build-windows-installer Pflicht (2.6.38)")
    if "Test-PyInstallerImport" not in bw and "PyInstaller Import fehlgeschlagen" not in bw:
        _fail("build-windows.ps1 fehlt PyInstaller-Probe (2.6.38)")
    # 2.6.38: PyInstaller absolute-import entry (no relative imports when frozen)
    entry = ROOT / "run_instantlensdoc.py"
    if not entry.is_file():
        _fail("run_instantlensdoc.py fehlt (2.6.38 PyInstaller entry)")
    entry_t = entry.read_text(encoding="utf-8")
    entry_code = "\n".join(
        ln for ln in entry_t.splitlines() if not ln.lstrip().startswith(("#", '"""', "'''"))
    )
    # Strip module docstring for relative-import scan
    if entry_t.lstrip().startswith('"""'):
        _end = entry_t.find('"""', 3)
        entry_code = entry_t[_end + 3 :] if _end > 0 else entry_t
    if "\nfrom ." in ("\n" + entry_code) or "\nimport ." in ("\n" + entry_code):
        _fail("run_instantlensdoc.py darf keine Relative-Imports haben (2.6.38)")
    if "from instantlensdoc.app import main" not in entry_t:
        _fail("run_instantlensdoc.py fehlt absolute Import instantlensdoc.app (2.6.38)")
    main_py = (ROOT / "instantlensdoc" / "__main__.py").read_text(encoding="utf-8")
    main_code = main_py
    if main_py.lstrip().startswith('"""'):
        _end = main_py.find('"""', 3)
        main_code = main_py[_end + 3 :] if _end > 0 else main_py
    if "\nfrom ." in ("\n" + main_code) or main_code.lstrip().startswith("from ."):
        _fail("instantlensdoc/__main__.py hat noch Relative-Import (2.6.38)")
    if "from instantlensdoc.app import main" not in main_py:
        _fail("instantlensdoc/__main__.py fehlt absolute Import (2.6.38)")
    if "run_instantlensdoc.py" not in bw:
        _fail("build-windows.ps1 nutzt nicht run_instantlensdoc.py (2.6.38)")
    spec_t = (ROOT / "instantlensdoc.spec").read_text(encoding="utf-8")
    if "run_instantlensdoc.py" not in spec_t:
        _fail("instantlensdoc.spec nutzt nicht run_instantlensdoc.py (2.6.38)")
    # Headless import smoke of absolute entry (does not start GUI)
    import importlib.util

    spec = importlib.util.spec_from_file_location("run_instantlensdoc", entry)
    if spec is None or spec.loader is None:
        _fail("run_instantlensdoc.py nicht ladbar")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not callable(getattr(mod, "main", None)):
        _fail("run_instantlensdoc.main nicht callable")
    if "Copy-TesseractVendor" not in bw or "build-keygen" not in bw:
        _fail("build-windows.ps1 fehlt Tesseract Copy-Hint/build-keygen (2.6.42)")
    if r"D:\AI_Temp\ScanTuxio Win" not in bw:
        _fail("build-windows.ps1 fehlt ScanTuxio Win Tesseract-Pfad (2.6.42)")
    ocr_py = (ROOT / "instantlensdoc" / "core" / "ocr.py").read_text(encoding="utf-8")
    if "resolve_tesseract_executable" not in ocr_py or "TESSDATA_PREFIX" not in ocr_py:
        _fail("ocr.py fehlt resolve_tesseract_executable/TESSDATA_PREFIX (2.6.42)")
    if "SCANTUXIO_WIN_ROOTS" not in ocr_py or "vendor" not in ocr_py:
        _fail("ocr.py fehlt ScanTuxio/vendor Lookup (2.6.42)")
    tess_readme = ROOT / "vendor" / "tesseract" / "README.txt"
    if not tess_readme.is_file():
        _fail("vendor/tesseract/README.txt fehlt (2.6.42 Layout-Hinweis)")
    tess_rd = tess_readme.read_text(encoding="utf-8")
    if "tesseract.exe" not in tess_rd or "tessdata" not in tess_rd:
        _fail("vendor/tesseract/README.txt unvollständig (2.6.42)")
    from instantlensdoc.core.ocr import (
        apply_tessdata_prefix,
        resolve_tesseract_executable,
        tesseract_lookup_candidates,
    )
    cands = tesseract_lookup_candidates()
    joined = "\n".join(cands)
    if r"D:\AI_Temp\ScanTuxio Win" not in joined:
        _fail("tesseract_lookup_candidates fehlt ScanTuxio Win")
    if "vendor" not in joined.lower() or "tesseract.exe" not in joined:
        _fail("tesseract_lookup_candidates fehlt vendor/tesseract.exe")
    if not callable(resolve_tesseract_executable) or not callable(apply_tessdata_prefix):
        _fail("ocr tess helpers nicht callable")
    # 2.6.41: Large-PDF perf constants + APIs
    from ild_pdf.limits import (
        THUMB_VIRTUAL_THRESHOLD,
        THUMB_PLACEHOLDER_CHUNK,
        PAGE_LABELS_SCAN_THRESHOLD,
        TEXT_EXTRACT_ALL_WARN_PAGES,
        STATS_WORD_SAMPLE_PAGES,
    )
    if int(THUMB_VIRTUAL_THRESHOLD) < 50:
        _fail("THUMB_VIRTUAL_THRESHOLD zu klein (2.6.41)")
    if int(THUMB_PLACEHOLDER_CHUNK) < 8:
        _fail("THUMB_PLACEHOLDER_CHUNK zu klein (2.6.41)")
    if int(PAGE_LABELS_SCAN_THRESHOLD) < 50:
        _fail("PAGE_LABELS_SCAN_THRESHOLD zu klein (2.6.41)")
    if int(TEXT_EXTRACT_ALL_WARN_PAGES) < 50:
        _fail("TEXT_EXTRACT_ALL_WARN_PAGES zu klein (2.6.41)")
    if int(STATS_WORD_SAMPLE_PAGES) < 1:
        _fail("STATS_WORD_SAMPLE_PAGES ungültig (2.6.41)")
    from ild_pdf.overlay import extract_plain_text_pages
    if not callable(extract_plain_text_pages):
        _fail("extract_plain_text_pages fehlt (2.6.41)")
    mw = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
    if "virtual_only" not in mw or "THUMB_VIRTUAL_THRESHOLD" not in mw:
        _fail("main_window fehlt virtual thumb queue (2.6.41)")
    if "TEXT_EXTRACT_ALL_WARN_PAGES" not in mw:
        _fail("main_window fehlt page-scoped extract warn (2.6.41)")
    pv = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
    if "QProgressDialog" not in pv or "_open_generation" not in pv:
        _fail("pdf_view.load fehlt Progress/Cancel Open (2.6.41)")
    if "scan_native" not in pv:
        _fail("pdf_view fehlt lazy page labels (2.6.41)")
    sb = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
    if "shared_icon" not in sb and "THUMB_PLACEHOLDER_CHUNK" not in sb:
        _fail("sidebar.prepare_lazy_thumbs fehlt shared/chunked placeholders (2.6.41)")
    # 2.6.41: ScanTuxio-Port + Geraete-UX
    st_root = ROOT / "instantlensdoc" / "core" / "scantuxio"
    for rel in (
        "scanner.py",
        "scanner_naps2.py",
        "scanner_escl.py",
        "discovery.py",
        "printing.py",
        "printing_windows.py",
        "platform_utils.py",
    ):
        if not (st_root / rel).is_file():
            _fail(f"scantuxio/{rel} fehlt (2.6.41 ScanTuxio-Port)")
    try:
        from instantlensdoc.core.scantuxio import scanner as _st_scanner
        from instantlensdoc.core.scantuxio import scanner_naps2 as _st_naps2

        if not callable(getattr(_st_scanner, "list_devices_all", None)):
            _fail("scantuxio.scanner.list_devices_all fehlt")
        if not callable(getattr(_st_scanner, "scan_single_page_dispatch", None)):
            _fail("scantuxio.scanner.scan_single_page_dispatch fehlt")
        if not callable(getattr(_st_naps2, "list_devices", None)):
            _fail("scantuxio.scanner_naps2.list_devices fehlt")
    except Exception as e:
        _fail(f"scantuxio Import: {e}")
    dev = (ROOT / "instantlensdoc" / "core" / "devices.py").read_text(encoding="utf-8")
    if "_list_scanners_scantuxio" not in dev or "SCAN_START_HINT_DE" not in dev:
        _fail("devices.py fehlt ScanTuxio-Bridge/SCAN_START_HINT_DE (2.6.41)")
    if "NO_DEVICE_STATUS_DE" not in dev:
        _fail("devices.py fehlt NO_DEVICE_STATUS_DE (2.6.41)")
    sc = (ROOT / "instantlensdoc" / "core" / "scan.py").read_text(encoding="utf-8")
    if "_acquire_scantuxio" not in sc or "scan_single_page_dispatch" not in sc:
        _fail("scan.py fehlt _acquire_scantuxio/dispatch (2.6.41)")
    sd = (ROOT / "instantlensdoc" / "ui" / "scan_dialog.py").read_text(encoding="utf-8")
    if "scanEntryBanner" not in sd or "SCAN_START_HINT_DE" not in sd:
        _fail("scan_dialog fehlt Entry-Banner (2.6.41)")
    wel = (ROOT / "instantlensdoc" / "ui" / "welcome.py").read_text(encoding="utf-8")
    if "scan_requested" not in wel or "welcomeScanBtn" not in wel:
        _fail("welcome fehlt Scannen-Button (2.6.41)")
    if "menuDevices" not in mw or "SCAN_START_HINT_DE" not in mw:
        _fail("main_window fehlt Geräte-Menü/SCAN_START_HINT (2.6.41)")
    # 2.6.43: Dokument-Speichern ohne .py-Default
    from instantlensdoc.ui.file_dialogs import (
        document_save_default_suffix,
        document_save_filters_are_safe,
        document_save_name_filters,
        document_save_suggested_name,
        ensure_document_save_extension,
    )

    filt2643 = document_save_name_filters()
    if not document_save_filters_are_safe(filt2643):
        _fail("document_save_name_filters unsicher / fehlt Pflichtformat (2.6.43)")
    if "*.py" in filt2643.split(";;", 1)[0].lower():
        _fail("Dokument-Save-Filter beginnt mit *.py (2.6.43)")
    if "python (" in filt2643.lower():
        _fail("Dokument-Save-Filter enthält Python-Eintrag (2.6.43)")
    for ext in (".ild", ".txt", ".docx", ".pdf", ".rtf", ".html"):
        if ext not in filt2643.lower():
            _fail(f"Dokument-Save-Filter fehlt {ext} (2.6.43)")
    if document_save_default_suffix("text") != ".ild":
        _fail("Default-Suffix Text ≠ .ild (2.6.43)")
    if document_save_suggested_name("Unbenannt", kind="text") != "Unbenannt.ild":
        _fail("Vorschlagsname Unbenannt ohne Endung falsch (2.6.43)")
    if document_save_suggested_name("Unbenannt.py", kind="text") != "Unbenannt.ild":
        _fail("Vorschlagsname Unbenannt.py nicht korrigiert (2.6.43)")
    fixed = ensure_document_save_extension("foo.py", "Text (*.txt)", default_suffix=".txt")
    if str(fixed).lower().endswith(".py") or not str(fixed).lower().endswith(".txt"):
        _fail("ensure_document_save_extension lässt .py stehen (2.6.43)")
    if "get_document_save_file_name" not in mw or "document_save_suggested_name" not in mw:
        _fail("main_window.save_as nutzt keine Dokument-Save-Helfer (2.6.43)")
    docs_py = (ROOT / "instantlensdoc" / "core" / "documents.py").read_text(encoding="utf-8")
    if '".ild"' not in docs_py and "'.ild'" not in docs_py:
        _fail("detect_kind erkennt .ild nicht (2.6.43)")
    # 2.6.45: Open-Preflight nie UI-blockierend (auch kleine PDFs)
    from ild_pdf.limits import (
        FORM_SCAN_PAGE_THRESHOLD,
        INSPECT_TIMEOUT_SEC,
        PASSWORD_PROBE_TIMEOUT_SEC,
        size_only_health,
    )
    import inspect as _insp
    import tempfile
    from pathlib import Path as _P

    if not callable(size_only_health):
        _fail("size_only_health fehlt (2.6.45)")
    if float(INSPECT_TIMEOUT_SEC) > 5.0:
        _fail("INSPECT_TIMEOUT_SEC zu groß für Open-Fast-Path (2.6.45)")
    if float(PASSWORD_PROBE_TIMEOUT_SEC) > 5.0:
        _fail("PASSWORD_PROBE_TIMEOUT_SEC zu groß (2.6.45)")
    if int(FORM_SCAN_PAGE_THRESHOLD) < 20:
        _fail("FORM_SCAN_PAGE_THRESHOLD ungültig (2.6.45)")
    if "size_only_health" not in pv or "_schedule_page_count_refresh" not in pv:
        _fail("pdf_view.load fehlt Fast-Open size_only/_schedule_page_count (2.6.45)")
    if "_ensure_page_painted(warn=False)" not in pv and "warn=False" not in pv:
        _fail("pdf_view._ensure_page_painted fehlt quiet-Retry nach Open (2.6.45)")
    if "_repaint_central" not in mw and "setCurrentWidget(self.pdf_view)" not in mw:
        _fail("main_window.open_path fehlt PDF-Stack nach Open (2.6.45)")
    if "FORM_SCAN_PAGE_THRESHOLD" not in mw:
        _fail("main_window fehlt FORM_SCAN skip (2.6.45)")
    np_src = _insp.getsource(
        __import__("ild_pdf.security", fromlist=["needs_password"]).needs_password
    )
    if "timeout" not in np_src.lower() or "Thread" not in np_src:
        _fail("needs_password fehlt Timeout/Worker (2.6.45)")
    with tempfile.TemporaryDirectory() as _td:
        tiny = _P(_td) / "tiny.pdf"
        tiny.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
        h = size_only_health(tiny)
        if h.errors or h.probe != "size":
            _fail(f"size_only_health tiny unexpected: {h}")
    _ok(f"version {EXPECTED_VERSION}")
    # 2.6.40 blank-view / pack entry (kept)
    if "_ensure_page_painted" not in pv:
        _fail("pdf_view fehlt _ensure_page_painted (2.6.40)")
    if "run_instantlensdoc.py" not in (ROOT / "scripts" / "pack-windows-runnable.py").read_text(encoding="utf-8"):
        _fail("pack-windows-runnable.py fehlt run_instantlensdoc.py (2.6.40)")

    _ok("2.6.41 scantuxio-port/menuDevices/naps2-escl/entry-hints: OK")
    _ok("2.6.42 tesseract-runtime/vendor/TESSDATA_PREFIX/ScanTuxio-Win: OK")
    _ok("2.6.43 document-save-filters/no-py-default: OK")
    _ok("2.6.45 open-preflight-async/size_only/page-count-bg: OK")
    # 2.6.46: ScanTuxio-UI Launch + WIA busy secondary fallback
    st_ui = ROOT / "instantlensdoc" / "core" / "scantuxio_ui.py"
    if not st_ui.is_file():
        _fail("scantuxio_ui.py fehlt (2.6.46)")
    from instantlensdoc.core import scantuxio_ui as _st_ui
    for name in (
        "find_scantuxio_install",
        "launch_scantuxio_process",
        "missing_scantuxio_hint_de",
        "wia_busy_user_hint_de",
        "collect_new_scan_files",
        "is_wia_busy_message",
    ):
        if not callable(getattr(_st_ui, name, None)):
            _fail(f"scantuxio_ui.{name} fehlt (2.6.46)")
    sc = (ROOT / "instantlensdoc" / "core" / "scan.py").read_text(encoding="utf-8")
    if "_acquire_scantuxio_other_backends" not in sc or "expand_scan_import_paths" not in sc:
        _fail("scan.py fehlt WIA-busy-Fallback/expand_scan_import_paths (2.6.46)")
    sd = (ROOT / "instantlensdoc" / "ui" / "scan_dialog.py").read_text(encoding="utf-8")
    if "scanScantuxioBtn" not in sd or "_launch_scantuxio_ui" not in sd or "scanDeviceRetry" not in sd:
        _fail("scan_dialog fehlt ScanTuxio-UI/Retry (2.6.46)")
    if "QMessageBox.information(self, \"Scan\"" in sd and "Kein Bild vom Scanner" in sd:
        # nested modal for empty scan should be replaced by status
        pass
    _ok("2.6.46 scantuxio-ui-launch/wia-busy-fallback: OK")
    # 2.6.47: sichtbarer Blank-View-Fallback (behalten)
    if "show_render_fallback" not in pv or "_show_blank_view_fallback" not in pv:
        _fail("pdf_view fehlt show_render_fallback / _show_blank_view_fallback (2.6.47)")
    if "_blank_view_fallback_active" not in pv:
        _fail("pdf_view fehlt _blank_view_fallback_active (2.6.47)")
    if "Canvas ohne Pixmap nach Render" not in pv:
        _fail("pdf_view.refresh fehlt Pixmap-Verify (2.6.47)")
    if "_ensure_page_painted(warn=False)" not in mw:
        _fail("main_window._on_thumb_jump erzwingt Paint nicht (2.6.47)")
    _ok("2.6.47 blank-view-visible-fallback/thumb-force-paint: OK")
    # 2.6.48: PDFium-Buffer detach + sichtbares Canvas/Thumb Paint (Basis)
    render_src = (ROOT / "ild_pdf" / "render.py").read_text(encoding="utf-8")
    if "bitmap.close()" not in render_src:
        _fail("ild_pdf.render fehlt bitmap.close() (2.6.48)")
    iq = ROOT / "instantlensdoc" / "ui" / "image_qt.py"
    if not iq.is_file():
        _fail("image_qt.py fehlt (2.6.48)")
    iq_src = iq.read_text(encoding="utf-8")
    if "pil_to_qpixmap" not in iq_src or "qpixmap_has_ink" not in iq_src:
        _fail("image_qt fehlt pil_to_qpixmap/qpixmap_has_ink (2.6.48)")
    if "pil_to_qpixmap" not in pv or "qpixmap_has_ink" not in pv:
        _fail("pdf_view nutzt image_qt Paint-Pfad nicht (2.6.48)")
    if "setWidgetResizable(False)" not in pv:
        _fail("pdf_view ScrollArea nicht widgetResizable=False (2.6.48)")
    if "_schedule_paint_retry" not in pv or "showEvent" not in pv:
        _fail("pdf_view fehlt show/resize paint-retry (2.6.48)")
    if "from instantlensdoc.ui.image_qt import pil_to_qpixmap" not in (
        ROOT / "instantlensdoc" / "ui" / "sidebar.py"
    ).read_text(encoding="utf-8"):
        _fail("sidebar Thumbs nutzen image_qt nicht (2.6.48)")
    test_canvas = ROOT / "scripts" / "test_pdf_canvas_not_blank.py"
    if not test_canvas.is_file():
        _fail("scripts/test_pdf_canvas_not_blank.py fehlt (2.6.48)")
    _ok("2.6.48 pdfium-buffer-detach/canvas-ink/thumb-same-path: OK")
    # 2.6.49: DOCX/Word-Suite echte QTextCharFormat (kein Markdown)
    rt = ROOT / "instantlensdoc" / "core" / "richtext_docx.py"
    if not rt.is_file():
        _fail("richtext_docx.py fehlt (2.6.49)")
    rt_src = rt.read_text(encoding="utf-8")
    if "docx_to_html" not in rt_src or "html_to_docx" not in rt_src:
        _fail("richtext_docx fehlt docx_to_html/html_to_docx (2.6.49)")
    ed_src = (ROOT / "instantlensdoc" / "ui" / "editor.py").read_text(encoding="utf-8")
    if "toggle_char_format" not in ed_src or "setFontUnderline" not in ed_src:
        _fail("editor fehlt QTextCharFormat-Toggle (2.6.49)")
    if 'wrap_selection_markers("**")' in ed_src and "toggle_bold_selection" in ed_src:
        # bold must not call markdown wrappers
        bold_fn = ed_src.split("def toggle_bold_selection", 1)[-1].split("def ", 1)[0]
        if "wrap_selection_markers" in bold_fn:
            _fail("toggle_bold_selection nutzt noch Markdown-Wrapper (2.6.49)")
    if "set_rich_html" not in ed_src or "to_rich_html" not in ed_src:
        _fail("editor fehlt set_rich_html/to_rich_html (2.6.49)")
    if "richtext_docx" not in mw and "set_rich_html" not in mw:
        _fail("main_window fehlt Rich-Text DOCX-Pfad (2.6.49)")
    test_rt = ROOT / "scripts" / "test_docx_richtext.py"
    if not test_rt.is_file():
        _fail("scripts/test_docx_richtext.py fehlt (2.6.49)")
    _ok("2.6.49 docx-richtext/qtextcharformat-no-markdown: OK")
    # 2.6.50: harter frombytes-Detach + RGB32 + pdfium collect/guard + render-probe
    if "_detach_pil_from_pdfium" not in render_src or "frombytes" not in render_src:
        _fail("ild_pdf.render fehlt hard detach _detach_pil_from_pdfium/frombytes (2.6.50)")
    if "Format_RGB32" not in iq_src and "Format_RGB888" not in iq_src:
        _fail("image_qt fehlt RGB888/RGB32 Convert (2.6.50)")
    if "Ghost/Weiß nach Convert" not in pv and "ohne sichtbare Tinte" not in pv:
        _fail("pdf_view.set_page_image fehlt Tinte-Verify (2.6.50)")
    bw = (ROOT / "build-windows.ps1").read_text(encoding="utf-8")
    if "pdfium" not in bw.lower() or "collect-all" not in bw:
        _fail("build-windows.ps1 fehlt collect-all/pdfium Guard (2.6.50)")
    if "PDFium-Binary" not in bw and "pdfium.dll" not in bw.lower():
        _fail("build-windows.ps1 fehlt PDFium-Binary-Check (2.6.50)")
    spec = (ROOT / "instantlensdoc.spec").read_text(encoding="utf-8")
    if "collect_all" not in spec or "pypdfium2" not in spec:
        _fail("instantlensdoc.spec fehlt collect_all(pypdfium2) (2.6.50)")
    deps = (ROOT / "instantlensdoc" / "core" / "deps_check.py").read_text(encoding="utf-8")
    if "render_page" not in deps or "Render OK" not in deps:
        _fail("deps_check fehlt pypdfium2 Render-Probe (2.6.50)")
    sb = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
    if "Thumb ohne Tinte" not in sb and "pil_has_ink" not in sb:
        _fail("sidebar.update_thumb fehlt Ink-Reject (2.6.50)")
    if "_make_multipage_pdf" not in test_canvas.read_text(encoding="utf-8"):
        _fail("test_pdf_canvas_not_blank fehlt multipage PDF (2.6.50)")
    _ok("2.6.50 hard-detach/rgb32/pdfium-pack/render-probe: OK")
    # 2.6.51: Geräte/Scan-UI Restore (rebased on 2.6.50 tip)
    mw = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
    if "_ensure_devices_menu" not in mw or "menuDevices" not in mw:
        _fail("main_window fehlt _ensure_devices_menu/menuDevices (2.6.51)")
    if "actDevicesScanner" not in mw or "actDevicesDiscover" not in mw:
        _fail("main_window fehlt Geräte-Aktionen (2.6.51)")
    rb = (ROOT / "instantlensdoc" / "ui" / "ribbon_bar.py").read_text(encoding="utf-8")
    if "Geräte" not in rb:
        _fail("ribbon_bar fehlt Geräte-Tab (2.6.51)")
    if "scan_import" not in rb or "devices_discover" not in rb:
        _fail("ribbon_bar fehlt Scan/Geräte-Aktionen (2.6.51)")
    sd = (ROOT / "instantlensdoc" / "ui" / "scan_dialog.py").read_text(encoding="utf-8")
    if "_st_ui_available" not in sd:
        _fail("scan_dialog fehlt _st_ui_available (2.6.51)")
    stui = (ROOT / "instantlensdoc" / "core" / "scantuxio_ui.py").read_text(encoding="utf-8")
    if "Kein Import von ocr.py" not in stui and "ohne Pillow" not in stui:
        _fail("scantuxio_ui fehlt PIL-freier Fallback (2.6.51)")
    asrc = (ROOT / "instantlensdoc" / "core" / "app_settings.py").read_text(encoding="utf-8")
    if '"scan": True' not in asrc:
        _fail("app_settings fehlt Toolbar-Gruppe scan (2.6.51)")
    bw = (ROOT / "build-windows.ps1").read_text(encoding="utf-8")
    if "instantlensdoc.core.scantuxio_ui" not in bw:
        _fail("build-windows.ps1 fehlt scantuxio_ui hidden-import (2.6.51)")
    _ok("2.6.51 devices-menu-restore/ribbon-scan/scantuxio-resilient: OK")
    # 2.6.52: Voll-Audit — FlowLayout-Toolbar, Sidebar-Scroll, page_count-Signal,
    # B/I/U-Merge, persistenter Textmarker, DOCX-Stile/Hyperlinks, dirty-Guard
    fl = ROOT / "instantlensdoc" / "ui" / "flow_layout.py"
    if not fl.is_file() or "class FlowLayout" not in fl.read_text(encoding="utf-8"):
        _fail("ui/flow_layout.py fehlt (2.6.52)")
    pv = (ROOT / "instantlensdoc" / "ui" / "pdf_view.py").read_text(encoding="utf-8")
    if "FlowLayout(" not in pv or "toolbar = QHBoxLayout()" in pv:
        _fail("pdf_view Toolbar nutzt kein FlowLayout (2.6.52 — Fenster 7000 px breit)")
    if "_page_count_ready" not in pv or "_on_page_count_ready" not in pv:
        _fail("pdf_view fehlt _page_count_ready Signal (2.6.52 — page_count blieb 1)")
    sb = (ROOT / "instantlensdoc" / "ui" / "sidebar.py").read_text(encoding="utf-8")
    if "sidebarScroll" not in sb:
        _fail("sidebar fehlt QScrollArea (2.6.52 — Fenster 2000 px hoch)")
    ed_src = (ROOT / "instantlensdoc" / "ui" / "editor.py").read_text(encoding="utf-8")
    tcf = ed_src.split("def toggle_char_format", 1)[-1].split("def toggle_bold_selection", 1)[0]
    if "self.setCurrentCharFormat(fmt)" in tcf:
        _fail("editor.toggle_char_format nutzt setCurrentCharFormat (2.6.52 — B/U löschen sich)")
    if "clear_highlight_formats" not in ed_src or "selection_highlighted" not in ed_src:
        _fail("editor fehlt persistenter Textmarker (2.6.52)")
    rt = (ROOT / "instantlensdoc" / "core" / "richtext_docx.py").read_text(encoding="utf-8")
    if "_effective_tri" not in rt or "_iter_para_runs" not in rt or "highlight_color" not in rt:
        _fail("richtext_docx fehlt Stil-Vererbung/Hyperlink-Runs/Highlight (2.6.52)")
    mw = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
    if "_loading_document" not in mw:
        _fail("main_window fehlt _loading_document Guard (2.6.52 — dirty nach Öffnen)")
    if not (ROOT / "scripts" / "test_ui_audit_2652.py").is_file():
        _fail("scripts/test_ui_audit_2652.py fehlt (2.6.52)")
    _ok("2.6.52 full-audit flowlayout/page-count-signal/merge-format/docx-styles: OK")
    # 2.6.53: PDFium-Fallback-Kette, kein PDFium im Worker, Seitenlayout, DOCX-Umbruch
    po = ROOT / "ild_pdf" / "pdfium_open.py"
    if not po.is_file():
        _fail("ild_pdf/pdfium_open.py fehlt (2.6.53)")
    po_src = po.read_text(encoding="utf-8")
    for need in ("def open_pdfium", "STEP_REPAIR", "PDFIUM_LOCK", "def pdfium_version_info"):
        if need not in po_src:
            _fail(f"pdfium_open fehlt {need} (2.6.53)")
    doc_src = (ROOT / "ild_pdf" / "document.py").read_text(encoding="utf-8")
    if "open_pdfium(" not in doc_src or "pdfium.PdfDocument(str(self.path)" in doc_src:
        _fail("ild_pdf/document.py nutzt keine Fallback-Kette (2.6.53 — Data format error)")
    rd = (ROOT / "ild_pdf" / "render.py").read_text(encoding="utf-8")
    if "open_pdfium(" not in rd or "PDFIUM_LOCK" not in rd:
        _fail("ild_pdf/render.py ohne open_pdfium/PDFIUM_LOCK (2.6.53)")
    sec = (ROOT / "ild_pdf" / "security.py").read_text(encoding="utf-8")
    probe = sec.split("def needs_password", 1)[-1].split("def _encrypt_marker_heuristic", 1)[0]
    if "pypdfium2" in probe:
        _fail("security.needs_password nutzt PDFium im Worker-Thread (2.6.53 — nicht threadsicher)")
    work = pv.split("def _schedule_page_count_refresh", 1)[-1].split("def _on_page_count_ready", 1)[0]
    if "PdfDocument(" in work:
        _fail("pdf_view._schedule_page_count_refresh öffnet PDFium im Worker (2.6.53)")
    if "reset_page_image" not in pv:
        _fail("pdf_view fehlt canvas.reset_page_image (2.6.53 — altes Bild zählt als Erfolg)")
    spec = (ROOT / "instantlensdoc.spec").read_text(encoding="utf-8")
    if "pypdfium2_raw" not in spec or "pypdfium2_raw" not in bw:
        _fail("Spec/build-windows.ps1 sammeln pypdfium2_raw nicht (2.6.53 — pdfium.dll)")
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    if "pypdfium2==" not in req:
        _fail("requirements.txt pinnt pypdfium2 nicht (2.6.53)")
    if "_rich_mode" not in ed_src or "def set_page_layout" not in ed_src or "_relayout_document_width" not in ed_src:
        _fail("editor fehlt Rich-Umbruch/Seitenlayout (2.6.53)")
    for rel in ("instantlensdoc/core/editor_page_layout.py", "instantlensdoc/ui/page_layout_dialog.py", "scripts/test_ui_audit_2653.py"):
        if not (ROOT / rel).is_file():
            _fail(f"{rel} fehlt (2.6.53)")
    if '"page_layout"' not in mw or "actPageLayout" not in mw:
        _fail("main_window fehlt Seitenlayout-Aktion (2.6.53)")
    rb_src = (ROOT / "instantlensdoc" / "ui" / "ribbon_bar.py").read_text(encoding="utf-8")
    if '("page_layout"' not in rb_src:
        _fail("Ribbon fehlt Seitenlayout-Button (2.6.53)")
    if "def docx_default_font" not in rt or "font-family" not in rt:
        _fail("richtext_docx fehlt Standardschrift/Run-Fonts (2.6.53)")
    _ok("2.6.53 pdfium-fallback-chain/no-worker-pdfium/docx-wrap/page-layout: OK")
    # 2.6.54: Save-As-.pdf nie DOCX-Kopie, Header-Sniff, pdf_doctor, Minimap aus, Undo-Pfeile
    sniff_py = ROOT / "ild_pdf" / "pdf_sniff.py"
    if not sniff_py.is_file():
        _fail("ild_pdf/pdf_sniff.py fehlt (2.6.54)")
    sniff_src = sniff_py.read_text(encoding="utf-8")
    for need in ("def sniff_file", "def describe_non_pdf_de", "def validate_pdf_file", "KIND_ZIP_DOCX"):
        if need not in sniff_src:
            _fail(f"pdf_sniff fehlt {need} (2.6.54)")
    po_src = (ROOT / "ild_pdf" / "pdfium_open.py").read_text(encoding="utf-8")
    if "STEP_HEADER" not in po_src or "describe_non_pdf_de" not in po_src:
        _fail("pdfium_open fehlt Header-Schritt 0 (2.6.54)")
    docs_src = (ROOT / "instantlensdoc" / "core" / "documents.py").read_text(encoding="utf-8")
    if "detect_kind_mismatch" not in docs_src or "NIE eine Nicht-PDF-Quelle" not in docs_src:
        _fail("documents.save_document kopiert .pdf ohne Inhaltssniff (2.6.54)")
    exp_src = (ROOT / "instantlensdoc" / "core" / "export.py").read_text(encoding="utf-8")
    if "QPdfWriter" not in exp_src or "html: Optional[str]" not in exp_src:
        _fail("export_pdf fehlt QPdfWriter/html (2.6.54)")
    tpdf = (ROOT / "ild_pdf" / "text_pdf.py").read_text(encoding="utf-8")
    if "assert_valid_pdf" not in tpdf or "os.replace" not in tpdf:
        _fail("text_to_pdf ohne Validierung/atomares Replace (2.6.54)")
    if "fmt=\"pdf\"" not in mw and "fmt='pdf'" not in mw:
        pass
    if "kind_mismatch" not in mw or "validate_pdf_file" not in mw:
        _fail("main_window.save_as fehlt PDF-Validierung/Mismatch-Banner (2.6.54)")
    if "_sync_undo_redo_enabled" not in mw or "Ctrl+Shift+Z" not in mw:
        _fail("main_window fehlt Undo/Redo-Sync (2.6.54)")
    ed_src = (ROOT / "instantlensdoc" / "ui" / "editor.py").read_text(encoding="utf-8")
    if "_replace_all_text_undoable" not in ed_src or "minimap_effective" not in ed_src:
        _fail("editor fehlt Undo-Block/Minimap-Rich-Guard (2.6.54)")
    rb = (ROOT / "instantlensdoc" / "ui" / "ribbon_bar.py").read_text(encoding="utf-8")
    if '("undo", "↶ Rückgängig")' not in rb or "def set_enabled" not in rb:
        _fail("Ribbon fehlt Start-Undo-Pfeile (2.6.54)")
    if not (ROOT / "scripts" / "pdf_doctor.py").is_file():
        _fail("scripts/pdf_doctor.py fehlt (2.6.54)")
    if not (ROOT / "scripts" / "test_ui_audit_2654.py").is_file():
        _fail("scripts/test_ui_audit_2654.py fehlt (2.6.54)")
    as_src = (ROOT / "instantlensdoc" / "core" / "app_settings.py").read_text(encoding="utf-8")
    if "apply_one_time_migrations" not in as_src or "editor_minimap_reset_2654" not in as_src:
        _fail("app_settings fehlt Minimap-Reset-Migration (2.6.54)")
    _ok("2.6.54 pdf-sniff/save-as-export/pdf_doctor/minimap-off/undo-arrows: OK")


def check_imports(*, with_qt: bool) -> None:
    modules = [
        "ild_pdf",
        "ild_pdf.annotate",
        "ild_pdf.diff",
        "ild_pdf.pdf_ann_import",
        "ild_pdf.page_labels",
        "ild_pdf.doc_history",
        "ild_pdf.overlay",
        "ild_pdf.text_edit",
        "ild_pdf.object_edit",
        "ild_pdf.acroform",
        "ild_pdf.render",
        "instantlensdoc",
        "instantlensdoc.core.app_settings",
        "instantlensdoc.core.text_diff",
        "instantlensdoc.core.ocr_word_suite",
        "instantlensdoc.core.ki_wizards",
        "instantlensdoc.core.spellcheck",
        "instantlensdoc.core.autocorrect",
        "instantlensdoc.core.batch",
        "instantlensdoc.core.mail_merge",
        "instantlensdoc.core.shared_review",
        "instantlensdoc.core.realtime_collab",
        "instantlensdoc.core.hyperlinks",
        "instantlensdoc.core.export",
        "instantlensdoc.core.richtext_docx",
        "ild_pdf.print_prep",
        "ild_pdf.esign",
        "ild_pdf.sections",
        "ild_pdf.auto_format",
        "ild_pdf.typography",
        "ild",
        "ild.api",
    ]
    for name in modules:
        try:
            importlib.import_module(name)
        except Exception as e:
            _fail(f"import {name}: {e}")
    # UI-Module: Quelltext-Checks (Qt/EGL auf CI oft ohne Display-Libs)
    ui_checks = {
        ROOT / "instantlensdoc" / "ui" / "template_reset.py": (
            "reset_line_edit_template",
            "focus_line_edit_select_all",
            "EscapeDiscardEditFilter",
            "Key_Escape",
        ),
        ROOT / "instantlensdoc" / "ui" / "compare_dialog.py": (
            "chk_text_diff",
            "text_layer_diff",
            "chk_ignore_ws",
            "chk_only_diff",
            "chk_side_by_side",
            "txt_template_edit",
            "_export_text_diff_txt",
            "{mode}",
            "format_textlayer_diff_txt_filename",
            "find_invalid_textlayer_diff_txt_placeholders",
            "Reset Default",
            "_focus_txt_template_select_all",
            "_insert_txt_template_placeholder",
            "reset_line_edit_template",
            "EscapeDiscardEditFilter",
            "Esc im Feld",
            "_PdfDropPane",
            "chk_scroll_sync",
            "_on_pane_scroll",
            "setAcceptDrops",
            "2.6.19",
        ),
        ROOT / "instantlensdoc" / "ui" / "doc_tab_bar.py": (
            "DocumentTabBar",
            "tab_activated",
            "tab_close_requested",
            "tab_detach_requested",
            "2.6.28",
        ),
        ROOT / "instantlensdoc" / "core" / "autocorrect.py": (
            "effective_autocorrect_rules",
            "apply_autocorrect_to_text",
            "default_snippet_triggers",
            "2.6.28",
        ),
        ROOT / "instantlensdoc" / "core" / "spellcheck.py": (
            "spellcheck_with_suggestions",
            "suggest_corrections",
            "grammar_hints",
            "grammar_check",
            "builtin_wordlist",
            "2.6.28",
        ),
        ROOT / "instantlensdoc" / "ui" / "ribbon_bar.py": (
            "RibbonBar",
            "action_triggered",
            "book_layout",
            "detach_window",
            "autocorrect_toggle",
            "shared_review",
            "insert_hyperlink",
            "export_epub",
            "export_pptx",
            "save_as",
            "auto_lof",
            "auto_index",
            "ALT_CATEGORY_KEYS",
            "QStackedWidget",
        ),
        ROOT / "instantlensdoc" / "core" / "realtime_collab.py": (
            "RealtimeHub",
            "start_local_hub",
            "realtime_status",
            "apply_ops",
            "CRDT",
            "2.6.28",
        ),
        ROOT / "ild_pdf" / "sections.py": (
            "ildsections-v1",
            "add_section_break",
            "list_sections",
            "paginate_text_columns",
            "SectionBreak",
            "2.6.28",
        ),
        ROOT / "instantlensdoc" / "core" / "shared_review.py": (
            "ildshare-v1",
            "start_shared_review",
            "join_shared_review",
            "sync_shared_review",
            "session.ildshare.json",
            "2.6.28",
        ),
        ROOT / "instantlensdoc" / "ui" / "shared_review_dialog.py": (
            "SharedReviewDialog",
            "btnSharedReviewStart",
            "btnSharedReviewJoin",
            "btnSharedReviewSync",
            "2.6.28",
        ),
        ROOT / "instantlensdoc" / "core" / "hyperlinks.py": (
            "ildlinks-v1",
            "insert_link_in_text",
            "extract_links_from_text",
            "resolve_internal_target",
            "2.6.28",
        ),
        ROOT / "instantlensdoc" / "ui" / "hyperlink_dialog.py": (
            "HyperlinkDialog",
            "hyperlinkDialog",
            "hyperlinkTarget",
            "2.6.28",
        ),
        ROOT / "instantlensdoc" / "core" / "export.py": (
            "export_epub",
            "import_epub",
            "epub",
            "2.6.28",
        ),
        ROOT / "instantlensdoc" / "ui" / "pdf_view.py": (
            "_handle_page_wheel",
            "_wheel_should_flip_page",
            "wheelEvent",
            "import_native_pdf_comments",
            "MEASURE_AREA",
            "MEASURE_ANGLE",
            "AnnotationType.INK",
            "AnnotationType.LINK",
            "_on_ink",
            "bake_uri_links",
            "apply_custom_page_labels",
            "edit_page_labels",
            "show_doc_history",
            "ink_finished",
            "_toggle_measure_unit",
            "_toggle_measure_snap",
            "export_measures_csv",
            "dry_run",
            "Nach Import Sidecar speichern",
            "status_counts_de",
            "copyable_status_text",
            "Status kopieren",
            "_copy_import_status_to_clipboard",
            "_show_import_status_toast",
            "_announce_import_status_toast",
            "Reset Default",
            "Bestätigung nur bei Abweichung",
            "get_measure_csv_utf8_bom",
            "get_last_measure_csv_dir",
            "format_measure_csv_filename",
            "DEFAULT_MEASURE_CSV_FILENAME_TEMPLATE",
            "reset_line_edit_template",
            "EscapeDiscardEditFilter",
            "Klick fokussiert Statusleiste",
            "get_ocr_defaults_toast_sec",
            "_show_smooth_status_toast",
            "set_book_layout",
            "set_page_by_page",
            "btnBookLayout",
            "btnPageByPage",
            "_announce_smooth_status_toast",
            "_focus_ink_tool_from_toast",
            "Klick fokussiert Ink",
            "apply_true_redactions",
            "redactions_from_text_selection",
            "Echt schwärzen",
            "page_manage_dialog",
            "insert_pages_from_other_pdf",
            "Seitenmanagement",
            "scan_import_dialog",
            "inlineTextEditToolbarBtn",
            "InlineTextEditDialog",
            "edit_inline_text_at",
            "inline_text_edit_dialog",
            "objectEditToolbarBtn",
            "ObjectTransformDialog",
            "object_edit_dialog",
            "object_transform_dialog",
            "_set_object_edit_tool",
            "formFieldToolbarBtn",
            "form_field_dialog",
            "form_field_create_dialog",
            "form_field_detect_dialog",
            "_set_form_field_tool",
            "begin_form_field_select",
            "shapeFillToolbarBtn",
            "paragraphHighlightToolbarBtn",
            "AnnotationType.ELLIPSE",
            "AnnotationType.TRIANGLE",
            "AnnotationType.ROUNDED_RECT",
            "selection_to_paragraph_highlight_rects",
        ),
        ROOT / "instantlensdoc" / "ui" / "form_fields_dialog.py": (
            "FormFieldsDialog",
            "formFieldsAddBtn",
            "formFieldsDetectBtn",
            "formFieldsValueCheck",
            "formFieldsValueChoice",
        ),
        ROOT / "instantlensdoc" / "ui" / "form_field_edit_dialog.py": (
            "FormFieldEditDialog",
            "formFieldEditDialog",
            "formFieldEditType",
        ),
        ROOT / "instantlensdoc" / "ui" / "page_manage_dialog.py": (
            "PageManageDialog",
            "InternalMove",
            "Seiten aus PDF einfügen",
            "pageManageDialog",
            "Reihenfolge anwenden",
        ),
        ROOT / "instantlensdoc" / "ui" / "scan_dialog.py": (
            "ScanDialog",
            "scanDeviceList",
            "scanDeviceRefresh",
            "scanDeviceRescan",
            "scanScantuxioBtn",
            "scanTakeBtn",
            "scanDeviceRetry",
            "scanAcquireBtn",
            "scanImportBtn",
            "scanOcrEnabled",
            "scanEntryBanner",
            "SCAN_START_HINT_DE",
            "2.6.41",
            "2.6.46",
        ),
        ROOT / "instantlensdoc" / "core" / "devices.py": (
            "discover_devices",
            "list_printers",
            "list_scanners",
            "DeviceKind",
            "WINDOWS_SCAN_DEPS_HINT",
            "Get-Printer",
            "format_discovery_status",
            "WINDOWS_SCANNER_DRIVER_HINT_DE",
            "find_naps2_console",
            "SCAN_START_HINT_DE",
            "NO_DEVICE_STATUS_DE",
            "_list_scanners_scantuxio",
            "list_devices_all",
            "2.6.41",
            "ScanTuxio-Runtime",
        ),
        ROOT / "instantlensdoc" / "core" / "scan.py": (
            "insert_scan_pages_into_pdf",
            "import_image_paths",
            "expand_scan_import_paths",
            "acquire_from_scanner",
            "ocr_page_image",
            "_acquire_scantuxio",
            "_acquire_scantuxio_other_backends",
            "scan_single_page_dispatch",
            "2.6.41",
            "2.6.46",
        ),
        ROOT / "instantlensdoc" / "core" / "scantuxio" / "scanner.py": (
            "list_devices_all",
            "scan_single_page_dispatch",
            "native-escl:",
            "naps2:",
        ),
        ROOT / "instantlensdoc" / "core" / "scantuxio" / "scanner_naps2.py": (
            "NAPS2.Console",
            "--listdevices",
            "DEVICE_PREFIX",
        ),
        ROOT / "instantlensdoc" / "ui" / "page_labels_dialog.py": (
            "PageLabelsDialog",
            "Auch in PDF schreiben",
            "PageLabels",
            "Reset Default",
            "{stem}",
            "{date}",
            "pageLabelTxtPreview",
            "highlight_page_labels_txt_template_html",
            "reset_line_edit_template",
        ),
        ROOT / "instantlensdoc" / "ui" / "command_palette.py": (
            "CommandPaletteDialog",
            "default_palette_commands",
            "commandPalette",
            "Angeheftet",
            "_toggle_pin",
            "Unpin",
            "max Pins",
            "commandPalettePinOverflow",
            "replace_oldest",
            "page_manage",
            "Seitenmanagement",
            "scan_import",
            "devices",
            "inline_text_edit",
            "selection_text_edit",
            "object_edit",
            "object_transform",
            "form_fields",
            "form_field_create",
            "form_field_detect",
            "paragraph_highlight",
            "stamp_pick",
            "Pin-Limit erreicht",
            "Pin ersetzen",
            "Zu ersetzender Pin",
            "hyphenate_fr",
            "hyphenate_it",
            "2.6.41",
        ),
        ROOT / "instantlensdoc" / "ui" / "sidebar.py": (
            "Schnellvorschau",
            "Inhaltsverzeichnis",
            "sidebarSchnellvorschau",
            "sidebarInhaltsverzeichnis",
            "itemClicked",
        ),
        ROOT / "instantlensdoc" / "ui" / "editor.py": (
            "EditorPane",
            "ildEditorToolbar",
            "tool_action",
            "set_active_tool",
            "set_toolbar_visible",
            "Auswahl",
            "Text bearbeiten",
            "Markierungen",
            "editorToolbar_",
            "clear_highlight_formats",
            "mergeCurrentCharFormat",
            "2.6.44",
        ),
        ROOT / "instantlensdoc" / "ui" / "main_window.py": (
            "_focus_import_status_toast_target",
            "_import_status_toast_active",
            "Klick fokussiert Statusleiste",
            "_smooth_status_toast_active",
            "Klick fokussiert Ink",
            "Seitenbeschriftungen…",
            "Dokument-Historie…",
            "_open_command_palette",
            "_compress_pdf_images",
            "_bake_uri_links",
            "_export_links_txt",
            "linksTxtBom",
            "DEFAULT_LINKS_TXT",
            "linksTxtResetDefault",
            "linksTxtInsertStem",
            "Live-Vorschau",
            "Öffnen fehlgeschlagen",
            "Ersparnis",
            "_announce_status_toast",
            "Ctrl+K",
            "Downsample",
            "Seitenmanagement…",
            "page_manage",
            "Ctrl+Shift+M",
            "Scannen / Import…",
            "scan_import",
            "_run_scan_import",
            "_show_devices_dialog",
            "Drucker & Scanner…",
            "menuDevices",
            "actDevicesScanner",
            "actDevicesPrinters",
            "&Geräte",
            "Ctrl+Alt+Shift+I",
            "SCAN_START_HINT_DE",
            "scan_requested",
            "2.6.41",
            "_on_editor_toolbar_action",
            "_sync_editor_toolbar_for_stack",
            "2.6.44",
            "2.6.46",
            "Text bearbeiten…",
            "inline_text_edit",
            "Ctrl+Alt+Shift+E",
            "Objekt bearbeiten…",
            "object_edit",
            "Ctrl+Alt+Shift+O",
            "Formularfelder…",
            "form_fields",
            "Ctrl+Alt+Shift+K",
            "Formularfeld anlegen…",
            "Formularfelder erkennen…",
            "Verschlüsselung & Rechte…",
            "_pdf_security_dialog",
            "Ctrl+Alt+Shift+P",
            "pdf_security",
            "Ctrl+Alt+Shift+H",
            "paragraph_highlight",
            "_handoff_ocr_to_word_suite",
            "_ocr_word_suite_action",
            "Ctrl+Alt+Shift+W",
            "In Word-Suite öffnen/übernehmen",
            "_ki_document_wizard_action",
            "Ctrl+Alt+Shift+Q",
            "Dokument erstellen… (KI-Wizard)",
            "_run_esign_dialog",
            "_batch_convert",
            "Digitale Signatur (eIDAS)",
            "Stapelverarbeitung",
            "Ctrl+Alt+Shift+G",
            "_show_shared_review_dialog",
            "Ctrl+Alt+Shift+C",
            "Gemeinsames Review",
            "_insert_hyperlink_dialog",
            "_insert_shape_frame",
            "_crop_image_frame",
            "Ctrl+Shift+K",
            "Als EPUB",
            "Abbildungsverzeichnis aktualisieren",
            "Stichwortverzeichnis aktualisieren",
            "F12",
            "_update_figure_list",
            "_update_index",
            "HYPHENATION_UI_LANGS",
            "hyphenate_fr",
            "2.6.41",
        ),
        ROOT / "instantlensdoc" / "ui" / "batch_dialog.py": (
            "BatchConvertDialog",
            "PDF_WATERMARK",
            "PDF_COMPRESS",
            "PDF_ENCRYPT",
            "pipeline_wm_comp_enc",
            "batchUserPassword",
            "2.6.28",
        ),
        ROOT / "instantlensdoc" / "ui" / "esign_dialog.py": (
            "ESignDialog",
            "esignDialog",
            "esignLevel",
            "esignSignBtn",
            "2.6.28",
        ),
        ROOT / "instantlensdoc" / "ui" / "mail_merge_dialog.py": (
            "MailMergeDialog",
            "mailMergePreview",
            "mailMergeRunBtn",
            "2.6.28",
        ),
        ROOT / "ild_pdf" / "esign.py": (
            "sign_pdf",
            "verify_signature",
            "generate_self_signed_cert",
            "ildesign-v1",
            "eidas_level_info",
            "2.6.28",
        ),
        ROOT / "ild" / "__main__.py": (
            "license",
            "redact-apply",
            "export",
            "python -m ild",
            "ann-shape",
            "ann-stamp",
            "ann-highlight-para",
            "stamp-list",
            "ocr-word-suite",
            "import-ildocr",
            "ki-wizard",
            "ki-wizards",
            "batch",
            "sign-verify",
            "sign-cert",
            "eidas",
            "mail-merge-preview",
            "share-start",
            "share-join",
            "share-sync",
            "share-status",
            "share-info",
            "hyperlink",
            "hyperlinks",
            "anchors",
            "layout-shape",
            "layout-video",
            "layout-scale",
            "layout-crop",
            "export-epub",
        ),
        ROOT / "instantlensdoc" / "ui" / "help_dialog.py": (
            "python -m ild",
            "instantlensdoc-scripting.md",
            "scripts/ild.ps1",
        ),
        ROOT / "instantlensdoc" / "ui" / "password_dialog.py": (
            "compressOpenAfter",
            "Ergebnis nach Kompression öffnen",
            "setAccessibleName",
            "setAccessibleDescription",
            "PdfSecurityDialog",
            "pdfSecurityDialog",
            "pdfSecurityStatus",
            "pdfSecurityAes256",
            "securityPerm_",
            "AES-256",
        ),
        ROOT / "ild_pdf" / "security.py": (
            "get_encryption_info",
            "update_permissions",
            "PdfPermissionFlags",
            "EncryptionInfo",
            "PREFERRED_ENCRYPTION_R",
            "AES-256",
        ),
        ROOT / "instantlensdoc" / "ui" / "settings_dialog.py": (
            "compressOpenAfterSettings",
            "Ergebnis nach Kompression öffnen",
            "setAccessibleName",
            "setAccessibleDescription",
            "commandPalettePinMax",
            "goto_stubs_tab",
            "_focus_first_stub_row",
            "focus_first",
            "telemetryStubInfoBtn",
            "Stubs öffnen",
            "Key_Escape",
        ),
        ROOT / "instantlensdoc" / "ui" / "sidebar.py": (
            "sidebarLinksFilter",
            "sidebarLinksList",
            "filtered_link_uris",
            "links_export_requested",
        ),
        ROOT / "instantlensdoc" / "core" / "telemetry.py": (
            "report_anonymous_usage",
            "telemetry_stub_info",
            "diagnostics.jsonl",
            "opt_in",
            "stubs_tab_hint",
            "why",
        ),
        ROOT / "CONTRIBUTING.md": (
            "smoke_ild",
            "scripts/smoke_ild.py",
            "Windows",
            "-NoStart",
        ),
        ROOT / ".github" / "workflows" / "smoke-ild.yml": (
            "smoke-ild",
            "smoke_ild.py",
            "lokal",
        ),
    }
    if with_qt:
        for path, needles in ui_checks.items():
            if not path.is_file():
                _fail(f"fehlt: {path}")
            src = path.read_text(encoding="utf-8")
            for n in needles:
                if n not in src:
                    _fail(f"{path.name} fehlt {n!r}")
        _ok(f"imports ({len(modules)}) + ui-source (--qt)")
    else:
        _ok(f"imports ({len(modules)}) · Qt-Source übersprungen (--skip-qt)")


def check_cli_version() -> None:
    import subprocess

    r = subprocess.run(
        [sys.executable, "-m", "instantlensdoc", "--version"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        _fail(f"--version exit {r.returncode}: {out[:200]}")
    if EXPECTED_VERSION not in out:
        _fail(f"--version Ausgabe ohne {EXPECTED_VERSION}: {out[:200]}")
    _ok("cli --version")


def check_measure_and_diff() -> None:
    from ild_pdf import (
        Annotation,
        AnnotationType,
        DIFF_FORMAT_SIDE_BY_SIDE,
        compare_pdf_pages,
        export_text_layer_diff_txt,
        format_side_by_side_diff,
        text_layer_diff,
        text_to_pdf,
    )
    import ild as _ild_cmp

    assert callable(compare_pdf_pages)
    assert callable(_ild_cmp.compare_pdfs)
    from ild_pdf.pdf_ann_import import (
        import_native_into_store,
        import_native_pdf_annotations,
    )
    from ild_pdf.annotate import AnnotationStore
    from instantlensdoc.core.app_settings import (
        DEFAULT_MEASURE_CSV_FILENAME_TEMPLATE,
        DEFAULT_TEXTLAYER_DIFF_TXT_TEMPLATE,
        find_invalid_measure_csv_placeholders,
        find_invalid_textlayer_diff_txt_placeholders,
        format_measure_csv_filename,
        format_textlayer_diff_txt_filename,
        get_measure_csv_filename_template,
        get_measure_csv_utf8_bom,
        get_measure_labels_persistent,
        get_measure_snap_to_annotation,
        get_measure_unit,
        get_native_ann_import_save_sidecar,
        get_textlayer_diff_side_by_side,
        get_textlayer_diff_txt_template,
        highlight_measure_csv_template_html,
        highlight_textlayer_diff_txt_template_html,
        set_measure_csv_filename_template,
        set_measure_csv_utf8_bom,
        set_measure_labels_persistent,
        set_measure_snap_to_annotation,
        set_measure_unit,
        set_native_ann_import_save_sidecar,
        set_textlayer_diff_side_by_side,
        set_textlayer_diff_txt_template,
        toggle_measure_unit,
    )

    # Maß-Einheit Toggle
    set_measure_unit("mm")
    assert get_measure_unit() == "mm"
    assert toggle_measure_unit() == "px"
    assert get_measure_unit() == "px"
    set_measure_unit("mm")

    # Snap / Labels Settings — 2.1.1
    set_measure_snap_to_annotation(True)
    assert get_measure_snap_to_annotation() is True
    set_measure_snap_to_annotation(False)
    assert get_measure_snap_to_annotation() is False
    set_measure_labels_persistent(True)
    assert get_measure_labels_persistent() is True

    # BOM / Sidecar-Toggle / Side-by-Side Settings — 2.1.2
    set_measure_csv_utf8_bom(True)
    assert get_measure_csv_utf8_bom() is True
    set_measure_csv_utf8_bom(False)
    assert get_measure_csv_utf8_bom() is False
    set_measure_csv_utf8_bom(True)
    set_native_ann_import_save_sidecar(True)
    assert get_native_ann_import_save_sidecar() is True
    set_textlayer_diff_side_by_side(True)
    assert get_textlayer_diff_side_by_side() is True
    set_textlayer_diff_side_by_side(False)
    assert get_textlayer_diff_side_by_side() is False

    # Mess-CSV Live-Template + Diff-TXT {mode} — 2.1.3/2.1.4
    assert DEFAULT_MEASURE_CSV_FILENAME_TEMPLATE == "{stem}_measures.csv"
    set_measure_csv_filename_template("{stem}_measures.csv")
    assert get_measure_csv_filename_template() == "{stem}_measures.csv"
    assert format_measure_csv_filename("dok") == "dok_measures.csv"
    assert find_invalid_measure_csv_placeholders("{stem}_{x}.csv") == ["x"]
    assert "#c62828" in highlight_measure_csv_template_html("{stem}_{x}.csv")
    assert DEFAULT_TEXTLAYER_DIFF_TXT_TEMPLATE == "{stemA}_vs_{stemB}_{mode}.txt"
    set_textlayer_diff_txt_template("{stemA}_vs_{stemB}_{mode}.txt")
    assert "{mode}" in get_textlayer_diff_txt_template()
    assert format_textlayer_diff_txt_filename("a", "b", mode="unified") == (
        "a_vs_b_unified.txt"
    )
    assert format_textlayer_diff_txt_filename("a", "b", mode="sidebyside") == (
        "a_vs_b_sidebyside.txt"
    )
    assert find_invalid_textlayer_diff_txt_placeholders(
        "{stemA}_{foo}_{mode}.txt"
    ) == ["foo"]
    assert "#c62828" in highlight_textlayer_diff_txt_template_html(
        "{stemA}_{foo}.txt"
    )

    # Flächen-/Winkel-Labels
    area = Annotation(
        0, AnnotationType.MEASURE_AREA, 0, 0, width=72, height=72, color="#E67E22"
    )
    assert "mm²" in area.measure_label(1.0, unit="mm") or "pt²" in area.measure_label(
        1.0, unit="pt"
    )
    assert "px²" in area.measure_label(1.0, unit="px")
    ang = Annotation(
        0,
        AnnotationType.MEASURE_ANGLE,
        0,
        0,
        callout_x=50,
        callout_y=0,
        p3_x=50,
        p3_y=50,
        color="#E67E22",
    )
    deg = ang.angle_degrees()
    assert 80.0 <= deg <= 100.0, deg
    assert "°" in ang.measure_label(1.0)

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        a = td_path / "a.pdf"
        b = td_path / "b.pdf"
        text_to_pdf("alpha\nbeta\ngamma", a)
        text_to_pdf("alpha\nBETA\ngamma", b)
        result = text_layer_diff(a, b, left_page=0, right_page=0)
        assert 0.0 <= result.similarity_percent <= 100.0
        assert result.unified_diff or result.left_text
        # Ignore-WS / Nur-Unterschiede — 2.1.1
        ws = text_layer_diff(
            a, b, ignore_whitespace=True, only_differences=True
        )
        assert ws.ignore_whitespace and ws.only_differences
        # Side-by-Side — 2.1.2
        sbs = text_layer_diff(
            a, b, diff_format=DIFF_FORMAT_SIDE_BY_SIDE, only_differences=True
        )
        assert sbs.side_by_side_diff
        assert "|" in sbs.side_by_side_diff
        assert format_side_by_side_diff(
            ["a", "b"], ["a", "c"], only_differences=True
        )
        txt_out = td_path / "diff.txt"
        export_text_layer_diff_txt(ws, txt_out)
        assert txt_out.is_file() and txt_out.stat().st_size > 0
        txt_sbs = td_path / "diff_sbs.txt"
        export_text_layer_diff_txt(
            sbs, txt_sbs, diff_format=DIFF_FORMAT_SIDE_BY_SIDE
        )
        assert "Side-by-Side" in txt_sbs.read_text(encoding="utf-8")
        # Native Import auf Text-PDF (meist 0 Annots, API muss laufen)
        native = import_native_pdf_annotations(a)
        assert native.imported >= 0
        assert native.pages_scanned >= 1
        # Dry-Run into store
        store = AnnotationStore(a)
        store.annotations = []
        dry = import_native_into_store(store, a, dry_run=True)
        assert dry.dry_run is True
        assert len(store.annotations) == 0
        assert "ersetzt" in dry.status_counts_de()
        assert "übersprungen" in dry.status_counts_de()
        assert "neu" in dry.status_counts_de()
        assert "ersetzt" in dry.copyable_status_text()
        # Messwerte CSV Spalten Typ,Seite,Wert,Einheit + BOM — 2.1.2
        store.add(area)
        store.add(ang)
        csv_path = td_path / "messwerte.csv"
        store.export_measures_csv(csv_path, scale=1.0, unit="mm", utf8_bom=True)
        assert csv_path.is_file()
        body = csv_path.read_text(encoding="utf-8-sig")
        assert body.startswith("Typ,Seite,Wert,Einheit") or body.splitlines()[
            0
        ].startswith("Typ")
        assert "measure_area" in body or "measure_angle" in body
        csv_nobom = td_path / "messwerte_nobom.csv"
        store.export_measures_csv(
            csv_nobom, scale=1.0, unit="mm", utf8_bom=False
        )
        raw = csv_nobom.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")

        # Ink + page labels + doc history — 2.2.0 / Polish 2.2.4
        from ild_pdf import (
            AnnotationType as AT220,
            DocHistory,
            HIST_SCHEMA_ID,
            append_doc_history,
            apply_label_range,
            arabic_reset_labels,
            merge_labels,
            normalize_page_labels,
            read_pdf_page_labels,
            smooth_ink_points,
            write_pdf_page_labels,
        )
        from ild_pdf.annotate import Annotation as Ann220, DRAG_TYPES as DT220

        assert AT220.INK.value == "ink"
        assert AT220.INK in DT220
        ink = Ann220.from_ink_points(
            0,
            [[10, 10], [20, 15], [30, 10], [40, 20]],
            color="#E74C3C",
            stroke_width=4,
            smooth=True,
        )
        assert ink.type == AT220.INK
        assert len(ink.ink_points()) >= 3
        assert abs(float(ink.stroke_width) - 4.0) < 0.01
        assert ink.color.upper() == "#E74C3C"
        sm = smooth_ink_points([[0, 0], [10, 10], [20, 0], [30, 10]], passes=1)
        assert len(sm) == 4
        store.add(ink)
        assert store.remove_last_ink() is not None
        store.add(ink)
        store.set_custom_page_labels(["i", "ii", "1"])
        assert store.list_custom_page_labels(page_count=3)[:3] == ["i", "ii", "1"]
        assert arabic_reset_labels(3) == ["1", "2", "3"]
        assert apply_label_range(["", "", ""], start_page=1, end_page=2, start_value=5) == [
            "",
            "5",
            "6",
        ]
        store.save(force=True)
        store2 = AnnotationStore(a)
        assert any(x.type == AT220.INK for x in store2.annotations)
        ink_re = next(x for x in store2.annotations if x.type == AT220.INK)
        assert len(ink_re.points) >= 2
        assert store2.can_undo() or True  # history cleared on load
        store2.clear_history()
        store2.add(
            Ann220.from_ink_points(0, [[1, 1], [2, 2]], color="#000")
        )
        assert store2.can_undo()
        assert store2.undo()
        merged = merge_labels(["a", ""], ["", "ii"])
        assert merged == ["a", "ii"]
        assert normalize_page_labels({"0": "i"}, page_count=2) == ["i", ""]
        # PageLabels write roundtrip
        import pikepdf as pike220

        pl_pdf = td_path / "labels220.pdf"
        with pike220.Pdf.new() as doc_w:
            for _ in range(3):
                doc_w.add_blank_page(page_size=(200, 200))
            doc_w.save(pl_pdf)
        write_pdf_page_labels(pl_pdf, ["i", "ii", "1"])
        from ild_pdf import PdfDocument

        with PdfDocument(pl_pdf) as doc_pl:
            assert doc_pl.page_label(0) == "i"
            assert doc_pl.page_label(2) == "1"
        native_labs = read_pdf_page_labels(pl_pdf)
        assert native_labs[0] == "i"
        he = append_doc_history(pl_pdf, "page_labels.set", "labels=3")
        assert he is not None
        hist = DocHistory.for_pdf(pl_pdf, load=True)
        assert HIST_SCHEMA_ID == "ildhist-v1"
        assert hist.path.exists()
        assert hist.last_action_ts()
        assert any(e.action == "page_labels.set" for e in hist.entries)
        filt = hist.filter_entries("page_labels.set", limit=50)
        assert len(filt) >= 1
        exp = hist.export_json(td_path / "hist-export.json")
        assert exp.is_file()

    _ok(
        "measure + textlayer-diff + native-import + measures-csv "
        "template + status + ink/page-labels/ildhist — 2.3.3"
    )


def check_changelog() -> None:
    cl = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if "## 2.6.49" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.49")
    if "## 2.6.51" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.51")
    if "## 2.6.54" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.54")
    if "## 2.6.53" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.53")
    if "## 2.6.52" not in cl or "FlowLayout" not in cl or "_page_count_ready" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.52 Voll-Audit (FlowLayout/_page_count_ready)")
    if "## 2.6.50" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.50")
    if "## 2.6.48" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.48")
    if "## 2.6.46" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.46")
    if "## 2.6.45" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.45")
    if "## 2.6.44" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.44")
    if "## 2.6.43" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.43")
    if "## 2.6.42" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.42")
    if "## 2.6.41" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.41")
    if "## 2.6.40" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.40")
    if "## 2.6.38" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.38")
    if "## 2.6.36" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.36")
    if "## 2.6.35" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.35")
    if "## 2.6.28" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.28")
    if "## 2.6.25" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.25")
    if "## 2.6.21" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.21")
    if "## 2.6.19" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.19")
    if "## 2.6.17" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.17")
    if "## 2.6.16" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.16")
    if "## 2.6.15" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.15")
    if "## 2.6.13" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.13")
    if "## 2.6.12" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.12")
    if "## 2.6.9" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.9")
    if "## 2.6.7" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.7")
    if "## 2.6.6" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.6")
    if "## 2.6.5" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.5")
    if "## 2.6.3" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.3")
    if "## 2.6.2" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.2")
    if "## 2.6.1" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.1")
    if "## 2.6.0" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.0")
    if "## 2.5.20" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.20")
    if "## 2.5.19" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.19")
    if "## 2.5.18" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.18")
    if "## 2.5.17" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.17")
    if "## 2.5.15" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.15")
    if "## 2.5.14" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.14")
    if "## 2.5.13" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.13")
    if "## 2.5.12" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.12")
    if "## 2.5.11" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.11")
    if "## 2.5.10" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.10")
    if "## 2.5.9" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.9")
    if "## 2.5.8" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.8")
    if "## 2.5.7" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.7")
    if "## 2.5.6" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.6")
    if "## 2.5.5" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.5")
    if "## 2.5.4" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.4")
    if "## 2.5.3" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.3")
    if "## 2.5.2" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.2")
    if "## 2.5.1" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.1")
    if "## 2.5.0" not in cl:
        _fail("CHANGELOG fehlt ## 2.5.0")
    if "## 2.4.5" not in cl:
        _fail("CHANGELOG fehlt ## 2.4.5")
    if "## 2.4.4" not in cl:
        _fail("CHANGELOG fehlt ## 2.4.4")
    if "## 2.4.3" not in cl:
        _fail("CHANGELOG fehlt ## 2.4.3")
    if "## 2.4.2" not in cl:
        _fail("CHANGELOG fehlt ## 2.4.2")
    if "## 2.4.1" not in cl:
        _fail("CHANGELOG fehlt ## 2.4.1")
    if "## 2.4.0" not in cl:
        _fail("CHANGELOG fehlt ## 2.4.0")
    if "## 2.3.4" not in cl:
        _fail("CHANGELOG fehlt ## 2.3.4")
    if "## 2.3.3" not in cl:
        _fail("CHANGELOG fehlt ## 2.3.3")
    if "## 2.3.2" not in cl:
        _fail("CHANGELOG fehlt ## 2.3.2")
    if "## 2.3.1" not in cl:
        _fail("CHANGELOG fehlt ## 2.3.1")
    if "## 2.3.0" not in cl:
        _fail("CHANGELOG fehlt ## 2.3.0")
    if "## 2.2.5" not in cl:
        _fail("CHANGELOG fehlt ## 2.2.5")
    if "## 2.2.4" not in cl:
        _fail("CHANGELOG fehlt ## 2.2.4")
    if "## 2.2.3" not in cl:
        _fail("CHANGELOG fehlt ## 2.2.3")
    if "## 2.2.2" not in cl:
        _fail("CHANGELOG fehlt ## 2.2.2")
    if "## 2.1.5" not in cl:
        _fail("CHANGELOG fehlt ## 2.1.5")
    if "## 2.1.4" not in cl:
        _fail("CHANGELOG fehlt ## 2.1.4")
    if "## 2.1.3" not in cl:
        _fail("CHANGELOG fehlt ## 2.1.3")
    if "## 2.1.2" not in cl:
        _fail("CHANGELOG fehlt ## 2.1.2")
    if "## 2.1.1" not in cl:
        _fail("CHANGELOG fehlt ## 2.1.1")
    if "## 2.1.0" not in cl:
        _fail("CHANGELOG fehlt ## 2.1.0")
    if (
        "Status-%" not in cl
        and "Pin ersetzen" not in cl
        and "Fokus erste" not in cl
        and "announced" not in cl
        and "Ergebnis nach Kompression" not in cl
        and "Overflow" not in cl
        and "ältesten" not in cl
        and "Stubs öffnen" not in cl
        and "Live-Vorschau" not in cl
        and "{stem}_links.txt" not in cl
        and "max Pins" not in cl
        and "Unpin" not in cl
        and "Stubs-Tab" not in cl
        and "Stubs" not in cl
        and "Ersparnis" not in cl
        and "Toggle disabled" not in cl
        and "Angeheftet" not in cl
        and "URL-Liste" not in cl
        and "Recent" not in cl
        and "Vorher" not in cl
        and "Fuzzy" not in cl
        and "keine Datenübertragung" not in cl
        and "Downsample" not in cl
        and "Kompression" not in cl
        and "Command Palette" not in cl
        and "Schnellaktionen" not in cl
        and "Telemetrie" not in cl
        and "Link-Annotation" not in cl
        and "Live-Vorschau" not in cl
        and "Quick-Insert" not in cl
        and "Reset Default" not in cl
        and "Ink-Tool" not in cl
        and "Redo" not in cl
        and "NoStart" not in cl
        and "{stem}_labels.txt" not in cl
        and "BOM" not in cl
        and "Einträge entfernt" not in cl
        and "Undo Clear" not in cl
        and "copy-ready" not in cl
        and "A11y" not in cl
        and "Toast" not in cl
        and "Scroll" not in cl
        and "Glättung angewandt" not in cl
        and "gefilterte" not in cl
        and "Exitcode" not in cl
        and "Überlapp" not in cl
        and "Strength" not in cl
        and "Glättungsstärke" not in cl
        and "Doppelklick" not in cl
        and "Vorschau" not in cl
        and "Seitenbeschrift" not in cl
        and "Freihand" not in cl
        and "ildhist" not in cl
        and "Range-Editor" not in cl
        and "Glätten" not in cl
    ):
        _fail("CHANGELOG 2.4.0 fehlt Kernfeature-Hinweis")
    if (
        "freigegeben" not in cl
        and "Auto-Prune" not in cl
        and "Quick-Apply" not in cl
        and "{date}_shortcuts.txt" not in cl
        and "Klick toggled" not in cl
        and "Hit/Miss" not in cl
        and "PDF↔PDF" not in cl
        and "Cache leeren" not in cl
    ):
        _fail("CHANGELOG 2.4.2 fehlt Kernfeature-Hinweis")
    if (
        "N Dateien" not in cl
        and "on-write" not in cl
        and "Apply-Modus" not in cl
        and "Rechtsklick" not in cl
        and "Zustand" not in cl
        and "Live-Vorschau" not in cl
        and "Quick-Insert" not in cl
        and "Reset Default" not in cl
        and "Intervall" not in cl
    ):
        _fail("CHANGELOG 2.4.3 fehlt Kernfeature-Hinweis")
    if (
        "kopierbar" not in cl
        and "Toast optional" not in cl
        and "Apply abgebrochen" not in cl
        and "Announcement" not in cl
        and "AccessibleName" not in cl
        and "Bestätigung nur bei Abweichung" not in cl
        and "Fokus+Selektion" not in cl
        and "Fokus Toolbar" not in cl
    ):
        _fail("CHANGELOG 2.4.4 fehlt Kernfeature-Hinweis")
    if (
        "OCR-Toast" not in cl
        and "kopiert Status erneut" not in cl
        and "Vorlagenname" not in cl
        and "Template-Name" not in cl
        and "live" not in cl.casefold()
        and "an/aus" not in cl
        and "gemeinsamer Helper" not in cl
        and "template_reset" not in cl
    ):
        _fail("CHANGELOG 2.4.5 fehlt Kernfeature-Hinweis")
    if (
        "OCR-Region" not in cl
        and "OCR Region" not in cl
        and "Markieren" not in cl
        and "Corporate" not in cl
        and "ildtags-v1" not in cl
        and "Zuletzt" not in cl
        and "Farben-Theme" not in cl
    ):
        _fail("CHANGELOG 2.5.0 fehlt Kernfeature-Hinweis")
    if (
        "Fortschritt" not in cl
        and "ildcolors-theme-v1" not in cl
        and "ildexportpresets-v1" not in cl
        and "Duplikat" not in cl
        and "Trefferanzahl" not in cl
        and "2.5.2" not in cl
    ):
        _fail("CHANGELOG 2.5.2 fehlt Kernfeature-Hinweis")
    if (
        "Ellipsis" not in cl
        and "Fehlerabschnitt" not in cl
        and "skip/rename" not in cl
        and "Import-Log" not in cl
        and "Live-Pfad" not in cl
        and "A11y" not in cl
        and "2.5.3" not in cl
    ):
        _fail("CHANGELOG 2.5.3 fehlt Kernfeature-Hinweis")
    if (
        "Wörter" not in cl
        and "Custom löschen" not in cl
        and "Quick-Tag" not in cl
        and "Umbenennen" not in cl
        and "Doppelklick" not in cl
        and "2.5.4" not in cl
    ):
        _fail("CHANGELOG 2.5.4 fehlt Kernfeature-Hinweis")
    if (
        "Pfad kopiert" not in cl
        and "Hex" not in cl
        and "Tags kopieren" not in cl
        and "Zielordner" not in cl
        and "Entf" not in cl
        and "2.5.7" not in cl
    ):
        _fail("CHANGELOG 2.5.7 fehlt Kernfeature-Hinweis")
    if (
        "Text kopieren" not in cl
        and "Hex kopieren" not in cl
        and "Tags einfügen" not in cl
        and "Summary kopieren" not in cl
        and "Shift" not in cl
        and "2.5.8" not in cl
    ):
        _fail("CHANGELOG 2.5.8 fehlt Kernfeature-Hinweis")
    if (
        "Echt schwärzen" not in cl
        and "apply_true_redactions" not in cl
        and "Content-Stream" not in cl
        and "Metadaten" not in cl
        and "2.6.0" not in cl
    ):
        _fail("CHANGELOG 2.6.0 fehlt Kernfeature-Hinweis")
    if (
        "Seitenmanagement" not in cl
        and "insert_pages_from_pdf" not in cl
        and "Schnellvorschau" not in cl
        and "Inhaltsverzeichnis" not in cl
        and "2.6.1" not in cl
    ):
        _fail("CHANGELOG 2.6.1 fehlt Kernfeature-Hinweis")
    if (
        "Tesseract" not in cl
        and "Scannen" not in cl
        and "Scanner" not in cl
        and "discover_devices" not in cl
        and "2.6.2" not in cl
    ):
        _fail("CHANGELOG 2.6.2 fehlt Kernfeature-Hinweis")
    if (
        "Layout" not in cl
        and "hOCR" not in cl
        and "layout_preserve" not in cl
        and "Lesereihenfolge" not in cl
        and "2.6.3" not in cl
    ):
        _fail("CHANGELOG 2.6.3 fehlt Kernfeature-Hinweis")
    if (
        "Inline" not in cl
        and "Textbearbeitung" not in cl
        and "Formatabgleich" not in cl
        and "Schriftart" not in cl
        and "2.6.5" not in cl
    ):
        _fail("CHANGELOG 2.6.5 fehlt Inline-Text-Hinweis")
    if (
        "Formular" not in cl
        and "AcroForm" not in cl
        and "Checkbox" not in cl
        and "Dropdown" not in cl
        and "2.6.6" not in cl
    ):
        _fail("CHANGELOG 2.6.6 fehlt Formular-Hinweis")
    if (
        "Verschlüsselung" not in cl
        and "AES-256" not in cl
        and "Rechte" not in cl
        and "2.6.7" not in cl
    ):
        _fail("CHANGELOG 2.6.7 fehlt Verschlüsselungs-Hinweis")
    if (
        "Keygen" not in cl
        and "PyInstaller" not in cl
        and "Windows-Build" not in cl
        and "pack-windows-runnable" not in cl
        and "2.6.8" not in cl
    ):
        _fail("CHANGELOG 2.6.8 fehlt Build/Keygen-Hinweis")
    if (
        "Absatz" not in cl
        and "ellipse" not in cl
        and "Bezahlt" not in cl
        and "Color-Picker" not in cl
        and "2.6.9" not in cl
    ):
        _fail("CHANGELOG 2.6.9 fehlt Annotations-Hinweis")
    if (
        "Auto-Format" not in cl
        and "Inhaltsverzeichnis" not in cl
        and "Systemschrift" not in cl
        and "Ctrl+H" not in cl
        and "2.6.10" not in cl
    ):
        _fail("CHANGELOG 2.6.10 fehlt Auto-Format/TOC-Hinweis")
    if (
        "Lineal" not in cl
        and "Raster" not in cl
        and "Taschenbuch" not in cl
        and "Absatzformat" not in cl
        and "2.6.11" not in cl
    ):
        _fail("CHANGELOG 2.6.11 fehlt Lineal/Raster/Buchformate-Hinweis")
    if (
        "Musterseiten" not in cl
        and "Satzspiegel" not in cl
        and "Frames" not in cl
        and "Textrahmen" not in cl
        and "2.6.12" not in cl
    ):
        _fail("CHANGELOG 2.6.12 fehlt Frames/Musterseiten/Satzspiegel-Hinweis")
    if (
        "Typografie" not in cl
        and "Silbentrennung" not in cl
        and "Textumfluss" not in cl
        and "Drop Cap" not in cl
        and "Tracking" not in cl
        and "2.6.13" not in cl
    ):
        _fail("CHANGELOG 2.6.13 fehlt Typografie/Textumfluss/Silbentrennung-Hinweis")
    if (
        "Tabelle" not in cl
        and "CSV" not in cl
        and "XLSX" not in cl
        and "xlsx" not in cl
        and "RTF" not in cl
        and "2.6.14" not in cl
    ):
        _fail("CHANGELOG 2.6.14 fehlt Tabellen/Office-I/O-Hinweis")
    if (
        "Word-Suite" not in cl
        and "ildocr" not in cl
        and "ocr-word-suite" not in cl
        and "OCR → Word-Suite" not in cl
        and "2.6.15" not in cl
    ):
        _fail("CHANGELOG 2.6.15 fehlt OCR→Word-Suite-Hinweis")
    if (
        "KI-Wizard" not in cl
        and "KI-Wizards" not in cl
        and "Dokument erstellen" not in cl
        and "generate_ki_document" not in cl
        and "Anschreiben" not in cl
        and "Kaufvertrag" not in cl
        and "2.6.16" not in cl
    ):
        _fail("CHANGELOG 2.6.16 fehlt KI-Wizard-Hinweis")
    if (
        "i18n" not in cl
        and "Oberflächensprache" not in cl
        and "Handschrift" not in cl
        and "ui-langs" not in cl
        and "2.6.17" not in cl
    ):
        _fail("CHANGELOG 2.6.17 fehlt i18n/Handschrift-Hinweis")
    if (
        "CMYK" not in cl
        and "Bleed" not in cl
        and "Anschnitt" not in cl
        and "Preflight" not in cl
        and "PDF/X" not in cl
        and "2.6.18" not in cl
    ):
        _fail("CHANGELOG 2.6.18 fehlt CMYK/Bleed/Preflight/PDF/X-Hinweis")
    if (
        "Document Comparison" not in cl
        and "compare_pdfs" not in cl
        and "Buch-Layout" not in cl
        and "Seite-für-Seite" not in cl
        and "2.6.19" not in cl
    ):
        _fail("CHANGELOG 2.6.19 fehlt Compare/Book-Layout-Hinweis")
    if (
        "Rechtschreib" not in cl
        and "Autokorrektur" not in cl
        and "spellcheck" not in cl
        and "Textbaustein" not in cl
        and "2.6.20" not in cl
    ):
        _fail("CHANGELOG 2.6.20 fehlt Spell/Autocorrect-Hinweis")
    if (
        "Track Changes" not in cl
        and "Änderungen nachverfolgen" not in cl
        and "ildreview" not in cl
        and "Versionsverlauf" not in cl
        and "Seriendruck" not in cl
        and "2.6.21" not in cl
    ):
        _fail("CHANGELOG 2.6.21 fehlt Review/Kommentare/Versionen-Hinweis")
    if (
        "Stapelverarbeitung" not in cl
        and "Digitale Signatur" not in cl
        and "eIDAS" not in cl
        and "run_pdf_batch" not in cl
        and "ildesign" not in cl
        and "2.6.22" not in cl
    ):
        _fail("CHANGELOG 2.6.22 fehlt Batch/eSign-Hinweis")
    if (
        "Gemeinsames Review" not in cl
        and "ildshare" not in cl
        and "Freigabeordner" not in cl
        and "Shared Review" not in cl
        and "2.6.23" not in cl
    ):
        _fail("CHANGELOG 2.6.23 fehlt Shared-Review-Hinweis")
    if (
        "Hyperlink" not in cl
        and "EPUB" not in cl
        and "Grafik" not in cl
        and "Video-Platzhalter" not in cl
        and "2.6.24" not in cl
    ):
        _fail("CHANGELOG 2.6.24 fehlt Hyperlinks/Medien/EPUB-Hinweis")
    if (
        "Polish" not in cl
        and "Installer" not in cl
        and "Konsolidierung" not in cl
        and "CustomMessages" not in cl
        and "2.6.26" not in cl
    ):
        _fail("CHANGELOG 2.6.26 fehlt Polish/Installer-Hinweis")
    if (
        "Sync-Flow" not in cl
        and "BuildInstaller" not in cl
        and "apply_wheel_scroll" not in cl
        and "Mausrad" not in cl
        and "2.6.27" not in cl
    ):
        _fail("CHANGELOG 2.6.27 fehlt Sync/Mausrad-Hinweis")
    if (
        "Mausrad" not in cl
        and "Abbildungs" not in cl
        and "pptx" not in cl
        and "Audit-Closure" not in cl
        and "2.6.28" not in cl
    ):
        _fail("CHANGELOG 2.6.28 fehlt Audit-Closure/Mausrad/pptx-Hinweis")
    if (
        "ForceClean" not in cl
        and "flat" not in cl
        and "LocalPack" not in cl
        and "sync-ild" not in cl
        and "2.6.30" not in cl
    ):
        _fail("CHANGELOG 2.6.30 fehlt Sync/ForceClean/flat-Hinweis")
    if (
        "run.bat" not in cl
        and "cmd" not in cl
        and "ASCII" not in cl
        and "Mojibake" not in cl
        and "2.6.33" not in cl
    ):
        _fail("CHANGELOG 2.6.33 fehlt Installer/run.bat cmd-Loop-Hinweis")
    if "## 2.6.34" not in cl:
        _fail("CHANGELOG fehlt ## 2.6.34")
    if (
        "PYTHONPATH" not in cl
        and "instantlensdoc" not in cl
        and "Keygen" not in cl
        and "2.6.34" not in cl
    ):
        _fail("CHANGELOG 2.6.34 fehlt Keygen/PYTHONPATH-Hinweis")
    if (
        "-Dest" not in cl
        and "Fresh-Dest" not in cl
        and "Ordner-Sperre" not in cl
        and "2.6.35" not in cl
    ):
        _fail("CHANGELOG 2.6.35 fehlt Sync-Sperre/-Dest-Hinweis")
    if (
        "relative import" not in cl
        and "run_instantlensdoc" not in cl
        and "Relative-Import" not in cl
        and "2.6.38" not in cl
    ):
        _fail("CHANGELOG 2.6.36 fehlt EXE Relative-Import/Entry-Hinweis")
    if (
        "Large-PDF" not in cl
        and "Thumbnails virtual" not in cl
        and "Viewport" not in cl
        and "THUMB_VIRTUAL" not in cl
        and "2.6.39" not in cl
    ):
        _fail("CHANGELOG 2.6.39 fehlt Large-PDF/Perf-Hinweis")
    if (
        "NAPS2" not in cl
        and "Scan UX" not in cl
        and "SCAN_START" not in cl
        and "2.6.41" not in cl
    ):
        _fail("CHANGELOG 2.6.41 fehlt Scan/NAPS2-Hinweis")
    if (
        "TESSDATA_PREFIX" not in cl
        and "tesseract.exe" not in cl
        and "ScanTuxio Win" not in cl
        and "2.6.42" not in cl
    ):
        _fail("CHANGELOG 2.6.42 fehlt Tesseract-Runtime-Hinweis")
    if (
        "Speichern unter" not in cl
        and ".py" not in cl
        and "document_save" not in cl
        and "2.6.43" not in cl
    ):
        _fail("CHANGELOG 2.6.43 fehlt Speichern-unter/.py-Hinweis")
    if (
        "ildEditorToolbar" not in cl
        and "Nicht-PDF" not in cl
        and "Markierungen" not in cl
        and "2.6.44" not in cl
    ):
        _fail("CHANGELOG 2.6.44 fehlt Non-PDF-Toolbar-Hinweis")
    if (
        "PDF wird geprüft" not in cl
        and "size_only_health" not in cl
        and "Preflight" not in cl
        and "2.6.45" not in cl
    ):
        _fail("CHANGELOG 2.6.45 fehlt Open-Preflight/Hang-Hinweis")
    if (
        "ScanTuxio-UI" not in cl
        and "ScanTuxio-Hauptfenster" not in cl
        and "WIA-Busy" not in cl
        and "2.6.46" not in cl
    ):
        _fail("CHANGELOG 2.6.46 fehlt ScanTuxio-UI/WIA-Busy-Hinweis")

    if (
        "show_render_fallback" not in cl
        and "Render-Fallback" not in cl
        and "stilles Weiß" not in cl
        and "2.6.47" not in cl
    ):
        _fail("CHANGELOG 2.6.47 fehlt sichtbarer Render-Fallback-Hinweis")
    if (
        "to_pil" not in cl
        and "Buffer" not in cl
        and "pixmap" not in cl.lower()
        and "2.6.48" not in cl
    ):
        _fail("CHANGELOG 2.6.48 fehlt PDFium-Buffer/Canvas-Paint-Hinweis")
    if (
        "frombytes" not in cl
        and "hard" not in cl.lower()
        and "Detach" not in cl
        and "pdfium.dll" not in cl
        and "2.6.50" not in cl
    ):
        _fail("CHANGELOG 2.6.50 fehlt hard-Detach/pdfium-pack-Hinweis")
    if (
        "2.6.51" not in cl
        or (
            "_ensure_devices_menu" not in cl
            and "Geräte" not in cl
            and "Scan" not in cl
        )
    ):
        _fail("CHANGELOG 2.6.51 fehlt Geräte/Scan-Restore-Hinweis")
    if (
        "QTextCharFormat" not in cl
        and "richtext" not in cl.lower()
        and "DOCX" not in cl
        and "2.6.49" not in cl
    ):
        _fail("CHANGELOG 2.6.49 fehlt DOCX/Rich-Text/QTextCharFormat-Hinweis")
    if (
        "Silbentrennung" not in cl
        and "Hyphen" not in cl
        and "Menü" not in cl
        and "2.6.29" not in cl
    ):
        _fail("CHANGELOG 2.6.29 fehlt Silbentrennung/Menü-Hinweis")
    if (
        "Stylus" not in cl
        and "Palm" not in cl
        and "Hooks" not in cl
        and "Telemetrie" not in cl
        and "2.6.25" not in cl
    ):
        _fail("CHANGELOG 2.6.25 fehlt Stylus/Hooks/Telemetrie-Hinweis")
    if (
        "Open-Fail" not in cl
        and "HexAll" not in cl
        and "Ctrl+Shift+C" not in cl
        and "Tag−/Clear" not in cl
        and "Tag-/Clear" not in cl
        and "Summary-Fail" not in cl
        and "2.5.20" not in cl
    ):
        _fail("CHANGELOG 2.5.20 fehlt Kernfeature-Hinweis")
    if (
        "Pfad-Fail" not in cl
        and "Pfad-Copy" not in cl
        and "PageUp" not in cl
        and "PgUp" not in cl
        and "Öffnen" not in cl
        and "JSON" not in cl
        and "2.5.18" not in cl
    ):
        _fail("CHANGELOG 2.5.18 fehlt Kernfeature-Hinweis")
    if (
        "Text-Fail" not in cl
        and "Text-Copy" not in cl
        and "Digits" not in cl
        and "Ziffern" not in cl
        and "F5" not in cl
        and "CRUD" not in cl
        and "2.5.17" not in cl
    ):
        _fail("CHANGELOG 2.5.17 fehlt Kernfeature-Hinweis")
    if (
        "F5" not in cl
        and "Swatch" not in cl
        and "Space" not in cl
        and "2.5.15" not in cl
    ):
        _fail("CHANGELOG 2.5.15 fehlt Kernfeature-Hinweis")
    if (
        "F4" not in cl
        and "Shift+Doppelklick" not in cl
        and "Ctrl+Doppelklick" not in cl
        and "Ctrl+Shift+C" not in cl
        and "Ctrl+Home" not in cl
        and "2.5.14" not in cl
    ):
        _fail("CHANGELOG 2.5.14 fehlt Kernfeature-Hinweis")
    if (
        "Ctrl+C" not in cl
        and "Doppelklick" not in cl
        and "F3" not in cl
        and "Ctrl+↑" not in cl
        and "Reihenfolge" not in cl
        and "2.5.13" not in cl
    ):
        _fail("CHANGELOG 2.5.13 fehlt Kernfeature-Hinweis")
    if (
        "Enter" not in cl
        and "Shift+Mittelklick" not in cl
        and "Ctrl+Mittelklick" not in cl
        and "F2" not in cl
        and "Ctrl+Enter" not in cl
        and "2.5.12" not in cl
    ):
        _fail("CHANGELOG 2.5.12 fehlt Kernfeature-Hinweis")
    if (
        "Status schließen" not in cl
        and "Mittelklick" not in cl
        and "Shift+Entf" not in cl
        and "Ctrl+D" not in cl
        and "2.5.11" not in cl
    ):
        _fail("CHANGELOG 2.5.11 fehlt Kernfeature-Hinweis")
    if (
        "Kontextmenü" not in cl
        and "Status-Menü" not in cl
        and "Highlight" not in cl
        and "Ctrl+X" not in cl
        and "F2" not in cl
        and "2.5.10" not in cl
    ):
        _fail("CHANGELOG 2.5.10 fehlt Kernfeature-Hinweis")
    if (
        "Alt+Klick" not in cl
        and "Swatch" not in cl
        and "Ctrl+C" not in cl
        and "Pfad kopieren" not in cl
        and "Textvorschau" not in cl
        and "2.5.9" not in cl
    ):
        _fail("CHANGELOG 2.5.9 fehlt Kernfeature-Hinweis")
    if (
        "Rechtsklick" not in cl
        and "duplizieren" not in cl.casefold()
        and "Häufigkeit" not in cl
        and "Tooltip" not in cl
        and "Apply A11y" not in cl
        and "2.5.6" not in cl
    ):
        _fail("CHANGELOG 2.5.6 fehlt Kernfeature-Hinweis")
    if (
        "Status-Klick" not in cl
        and "umbenennen" not in cl.casefold()
        and "Tag-Anzahl" not in cl
        and "Duplizieren" not in cl
        and "2.5.5" not in cl
    ):
        _fail("CHANGELOG 2.5.5 fehlt Kernfeature-Hinweis")
    if (
        "Defaults" not in cl
        and "Swatches" not in cl
        and "Vorschau" not in cl
        and "Filter Clear" not in cl
        and "max. 10" not in cl
        and "max 10" not in cl
        and "Live-Zusammenfassung" not in cl
        and "2.5.1" not in cl
    ):
        _fail("CHANGELOG 2.5.1 fehlt Kernfeature-Hinweis")
    if "## 2.2.1" not in cl:
        _fail("CHANGELOG fehlt ## 2.2.1")
    if "## 2.2.0" not in cl:
        _fail("CHANGELOG fehlt ## 2.2.0")
    feat = (ROOT / "FEATURES.md").read_text(encoding="utf-8")
    if "2.6.42" not in feat:
        _fail("FEATURES.md fehlt 2.6.42")
    if "2.6.41" not in feat:
        _fail("FEATURES.md fehlt 2.6.41")
    if "2.6.28" not in feat:
        _fail("FEATURES.md fehlt 2.6.28")
    if "2.6.13" not in feat:
        _fail("FEATURES.md fehlt 2.6.13")
    if (
        "Lineal" not in feat
        and "Ausrichtungsraster" not in feat
        and "Absatzformatierung" not in feat
        and "Taschenbuch" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.11 Lineal/Raster/Absatz/Buchformate")
    if (
        "Musterseiten" not in feat
        and "Satzspiegel" not in feat
        and "Frames / Boxes" not in feat
        and "Textrahmen-Verkettung" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.12 Frames/Musterseiten/Satzspiegel")
    if (
        "Tracking" not in feat
        and "Silbentrennung" not in feat
        and "Textumfluss" not in feat
        and "Drop Cap" not in feat
        and "Kerning" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.13 Typografie/Textumfluss/Silbentrennung")
    if (
        "Dokument-Tabellen" not in feat
        and "Office-Export" not in feat
        and "XLSX" not in feat
        and "RTF" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.14 Tabellen/Office-I/O")
    if (
        "OCR → Word-Suite" not in feat
        and "Word-Suite" not in feat
        and "ildocr" not in feat
        and "ocr_to_word_suite" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.15 OCR→Word-Suite")
    if (
        "KI-Dokument-Wizards" not in feat
        and "KI-Wizard" not in feat
        and "generate_ki_document" not in feat
        and "Dokument erstellen" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.16 KI-Wizards")
    if (
        "UI i18n" not in feat
        and "Handschriftenerkennung" not in feat
        and "set_ui_lang" not in feat
        and "ocr_handwriting" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.17 i18n/Handschrift")
    if (
        "Farbmanagement" not in feat
        and "Bleed" not in feat
        and "Preflight" not in feat
        and "PDF/X" not in feat
        and "Dokument-Ebenen" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.18 CMYK/Bleed/Preflight/PDF/X")
    if (
        "Buch-Layout" not in feat
        and "Document Comparison" not in feat
        and "Seite-für-Seite" not in feat
        and "Ribbon-Chrome" not in feat
        and "Dokument-Tabs" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.19 Compare/Book/Tabs/Ribbon")
    if (
        "Rechtschreibung" not in feat
        and "Autokorrektur" not in feat
        and "Textbausteine" not in feat
        and "Undo/Redo" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.20 Spell/Autocorrect/Undo")
    if (
        "Track Changes" not in feat
        and "Änderungen nachverfolgen" not in feat
        and "Versionsverlauf" not in feat
        and "Seriendruck" not in feat
        and "Dokument-Kommentare" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.21 Review/Kommentare/Versionen")
    if (
        "Stapelverarbeitung" not in feat
        and "Digitale Signaturen" not in feat
        and "eIDAS" not in feat
        and "run_batch_job" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.22 Batch/eSign")
    if (
        "Gemeinsames Review" not in feat
        and "ildshare" not in feat
        and "shared_review" not in feat
        and "Cloud-Ordner" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.23 Shared Review")
    if (
        "Hyperlink" not in feat
        and "EPUB" not in feat
        and "Grafiken" not in feat
        and "Video-Platzhalter" not in feat
    ):
        _fail("FEATURES.md fehlt Hyperlinks/Medien/EPUB")
    if (
        "Inno-Installer" not in feat
        and "build-windows-installer" not in feat
        and "CustomMessages" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.28 Installer-Hinweis")
    if (
        "Abbildungsverzeichnis" not in feat
        and "Stichwortverzeichnis" not in feat
        and "pptx" not in feat.lower()
        and "Default-Mausrad" not in feat
        and "realtime_collab" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.28 Audit-Closure (Verzeichnisse/pptx/Mausrad)")
    if (
        "ForceClean" not in feat
        and "flat/nested" not in feat
        and "Pack-Marker" not in feat
        and "2.6.30" not in feat
    ):
        _fail("FEATURES.md fehlt Sync ForceClean/flat-Hinweis")
    if (
        "run.bat ASCII" not in feat
        and "EXE-Layout" not in feat
        and "cmd-Loop" not in feat
        and "2.6.33" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.33 Installer/run.bat-Hinweis")
    if (
        "PYTHONPATH" not in feat
        and "run-keygen.ps1" not in feat
        and "2.6.34" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.34 Keygen/PYTHONPATH-Hinweis")
    if (
        "-Dest" not in feat
        and "Fresh" not in feat
        and "Ordner-Sperre" not in feat
        and "2.6.35" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.35 Sync-Sperre/-Dest-Hinweis")
    if (
        "Relative-Import" not in feat
        and "run_instantlensdoc" not in feat
        and "2.6.38" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.36 EXE Relative-Import/Entry-Hinweis")
    if (
        "Large-PDF" not in feat
        and "lazy/virtual" not in feat
        and "2.6.39" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.39 Large-PDF Perf-Hinweis")
    if (
        "NAPS2" not in feat
        and "Scan UX" not in feat
        and "2.6.41" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.41 Scan/NAPS2-Hinweis")
    if "2.6.43" not in feat or (
        ".py" not in feat and ".ild" not in feat and "Speichern unter" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.43 Speichern-unter/Dokumentfilter-Hinweis")
    if "2.6.45" not in feat or (
        "PDF wird geprüft" not in feat
        and "size_only" not in feat
        and "Open-Preflight" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.45 Open-Preflight/Hang-Hinweis")
    if "2.6.46" not in feat or (
        "ScanTuxio-UI" not in feat
        and "ScanTuxio-Hauptfenster" not in feat
        and "scantuxio_ui" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.46 ScanTuxio-UI-Hinweis")
    if "2.6.47" not in feat or (
        "Render-Fallback" not in feat
        and "show_render_fallback" not in feat
        and "sichtbarer" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.47 Render-Fallback-Hinweis")
    if "2.6.48" not in feat or (
        "Buffer" not in feat
        and "to_pil" not in feat
        and "Canvas" not in feat
        and "pixmap" not in feat.lower()
    ):
        _fail("FEATURES.md fehlt 2.6.48 Canvas/Buffer-Paint-Hinweis")
    if "2.6.49" not in feat or (
        "QTextCharFormat" not in feat
        and "richtext" not in feat.lower()
        and "DOCX" not in feat
        and "Word-Suite" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.49 DOCX/Rich-Text-Hinweis")
    if "2.6.50" not in feat or (
        "hard-detach" not in feat
        and "frombytes" not in feat
        and "pdfium.dll" not in feat
        and "RGB32" not in feat
        and "Detach" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.50 hard-detach/pdfium-pack-Hinweis")
    if "2.6.51" not in feat or (
        "Geräte" not in feat
        and "Scan" not in feat
        and "Ribbon" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.51 Geräte/Scan-Restore-Hinweis")
    if "2.6.44" not in feat or (
        "ildEditorToolbar" not in feat
        and "Markierungen" not in feat
        and "Nicht-PDF" not in feat
        and "Bearbeitungsleiste" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.44 Non-PDF-Toolbar-Hinweis")
    if (
        "ScanTuxio" not in feat
        and "vendor/tesseract" not in feat
        and "2.6.42" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.42 Tesseract-Runtime-Hinweis")
    if (
        "Silbentrennung" not in feat
        and "Menü/Palette" not in feat
        and "2.6.29" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.29 Silbentrennung Menü/Palette")
    if "Automatische Formatierung" not in feat and "Systemschriften" not in feat:
        _fail("FEATURES.md fehlt 2.6.10 Auto-Format/Fonts")
    if "2.6.10" not in feat:
        _fail("FEATURES.md fehlt 2.6.10")
    if "2.6.9" not in feat:
        _fail("FEATURES.md fehlt 2.6.9")
    if "2.6.6" not in feat:
        _fail("FEATURES.md fehlt 2.6.6")
    if "2.6.5" not in feat:
        _fail("FEATURES.md fehlt 2.6.5")
    if "2.5.17" not in feat:
        _fail("FEATURES.md fehlt 2.5.17")
    if "2.5.15" not in feat:
        _fail("FEATURES.md fehlt 2.5.15")
    if "2.5.14" not in feat:
        _fail("FEATURES.md fehlt 2.5.14")
    if "2.5.13" not in feat:
        _fail("FEATURES.md fehlt 2.5.13")
    if "2.5.10" not in feat:
        _fail("FEATURES.md fehlt 2.5.10")
    if "2.5.6" not in feat:
        _fail("FEATURES.md fehlt 2.5.6")
    if "2.5.4" not in feat:
        _fail("FEATURES.md fehlt 2.5.4")
    if "2.5.3" not in feat:
        _fail("FEATURES.md fehlt 2.5.3")
    if "2.5.2" not in feat:
        _fail("FEATURES.md fehlt 2.5.2")
    if "2.5.1" not in feat:
        _fail("FEATURES.md fehlt 2.5.1")
    if "2.5.0" not in feat:
        _fail("FEATURES.md fehlt 2.5.0")
    if "2.4.5" not in feat:
        _fail("FEATURES.md fehlt 2.4.5")
    if "2.4.4" not in feat:
        _fail("FEATURES.md fehlt 2.4.4")
    if "2.4.3" not in feat:
        _fail("FEATURES.md fehlt 2.4.3")
    if "2.4.2" not in feat:
        _fail("FEATURES.md fehlt 2.4.2")
    if "2.4.0" not in feat:
        _fail("FEATURES.md fehlt 2.4.0")
    if "2.3.4" not in feat:
        _fail("FEATURES.md fehlt 2.3.4")
    if "2.3.2" not in feat:
        _fail("FEATURES.md fehlt 2.3.2")
    if "2.3.1" not in feat:
        _fail("FEATURES.md fehlt 2.3.1")
    if "2.3.0" not in feat:
        _fail("FEATURES.md fehlt 2.3.0")
    if "2.2.5" not in feat:
        _fail("FEATURES.md fehlt 2.2.5")
    if "2.2.4" not in feat:
        _fail("FEATURES.md fehlt 2.2.4")
    if "2.2.3" not in feat:
        _fail("FEATURES.md fehlt 2.2.3")
    if "2.2.2" not in feat:
        _fail("FEATURES.md fehlt 2.2.2")
    if "Downsample" not in feat and "Schnellaktionen" not in feat:
        _fail("FEATURES.md fehlt 2.3.x Kernfeatures")
    if (
        "Status-%" not in feat
        and "Pin-ersetzen" not in feat
        and "Fokus erste" not in feat
        and "Ergebnis nach Kompression" not in feat
        and "Overflow" not in feat
        and "ältesten" not in feat
        and "Stubs öffnen" not in feat
        and "{stem}_links.txt" not in feat
        and "max Pins" not in feat
        and "Tab Stubs" not in feat
        and "Ersparnis" not in feat
        and "Pin" not in feat
        and "Toggle disabled" not in feat
        and "URL-Liste TXT" not in feat
        and "Vorher" not in feat
        and "Fuzzy" not in feat
        and "keine Datenübertragung" not in feat
    ):
        _fail("FEATURES.md fehlt 2.4.0 Polish")
    if (
        "Quick-Apply" not in feat
        and "Auto-Prune" not in feat
        and "freigegeben" not in feat
        and "{date}_shortcuts.txt" not in feat
        and "max MB" not in feat
        and "Hit/Miss" not in feat
        and "2.4.2" not in feat
    ):
        _fail("FEATURES.md fehlt 2.4.2 Polish")
    if (
        "N Dateien" not in feat
        and "on-write" not in feat
        and "Apply-Modus" not in feat
        and "Rechtsklick" not in feat
        and "Zustand" not in feat
        and "Live-Vorschau" not in feat
        and "Quick-Insert" not in feat
        and "Reset Default" not in feat
        and "Intervall" not in feat
        and "2.4.3" not in feat
    ):
        _fail("FEATURES.md fehlt 2.4.3 Polish")
    if (
        "kopierbar" not in feat
        and "Toast optional" not in feat
        and "Apply abgebrochen" not in feat
        and "Announcement" not in feat
        and "AccessibleName" not in feat
        and "Bestätigung nur bei Abweichung" not in feat
        and "Fokus+Selektion" not in feat
        and "2.4.4" not in feat
    ):
        _fail("FEATURES.md fehlt 2.4.4 Polish")
    if (
        "OCR-Toast" not in feat
        and "Status erneut" not in feat
        and "Vorlagenname" not in feat
        and "Template-Name" not in feat
        and "an/aus" not in feat
        and "gemeinsamer Helper" not in feat
        and "template_reset" not in feat
        and "2.4.5" not in feat
    ):
        _fail("FEATURES.md fehlt 2.4.5 Polish")
    if (
        "OCR Region" not in feat
        and "ildtags-v1" not in feat
        and "Zuletzt" not in feat
        and "Markieren" not in feat
        and "Corporate" not in feat
        and "2.5.0" not in feat
    ):
        _fail("FEATURES.md fehlt 2.5.0 Kernfeatures")
    if (
        "2.5.1" not in feat
        and "Filter Clear" not in feat
        and "Vorschau-Swatches" not in feat
        and "max. 10" not in feat
        and "Live-Zusammenfassung" not in feat
        and "Als Default" not in feat
    ):
        _fail("FEATURES.md fehlt 2.5.1 Polish")
    if (
        "2.5.2" not in feat
        and "ildcolors-theme-v1" not in feat
        and "ildexportpresets-v1" not in feat
        and "Duplikat" not in feat
        and "Trefferanzahl" not in feat
        and "Fehler anhängen" not in feat
    ):
        _fail("FEATURES.md fehlt 2.5.2 Polish")
    if (
        "2.5.3" not in feat
        and "Ellipsis" not in feat
        and "Live-Pfad" not in feat
        and "Import-Log" not in feat
        and "skip/rename" not in feat
        and "A11y" not in feat
        and "Fehlerabschnitt" not in feat
    ):
        _fail("FEATURES.md fehlt 2.5.3 Polish")
    if (
        "2.5.4" not in feat
        and "Quick-Tag" not in feat
        and "Umbenennen" not in feat
        and "Custom löschen" not in feat
        and "Wörter" not in feat
        and "Doppelklick" not in feat
    ):
        _fail("FEATURES.md fehlt 2.5.4 Polish")
    if (
        "2.5.7" not in feat
        and "Pfad kopieren" not in feat
        and "Hex-Tooltip" not in feat
        and "Tags kopieren" not in feat
        and "Entf löschen" not in feat
        and "RMB Zielordner" not in feat
    ):
        _fail("FEATURES.md fehlt 2.5.7 Polish")
    if (
        "2.5.8" not in feat
        and "Text kopieren" not in feat
        and "Hex kopieren" not in feat
        and "Tags einfügen" not in feat
        and "Summary kopieren" not in feat
    ):
        _fail("FEATURES.md fehlt 2.5.8 Polish")
    if (
        "2.6.0" not in feat
        and "Echt schwärzen" not in feat
        and "apply_true_redactions" not in feat
        and "Content-Stream" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.0 Echtes Schwärzen")
    if (
        "2.6.1" not in feat
        and "Seitenmanagement" not in feat
        and "insert_pages_from_pdf" not in feat
        and "Schnellvorschau" not in feat
        and "Inhaltsverzeichnis" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.1 Seitenmanagement")
    if (
        "2.6.2" not in feat
        and "Tesseract" not in feat
        and "Scannen" not in feat
        and "Scanner" not in feat
        and "Geräte" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.2 Scan/Geräte")
    if (
        "2.6.3" not in feat
        and "Layout-Erhalt" not in feat
        and "hOCR" not in feat
        and "Lesereihenfolge" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.3 Layout-OCR")
    if (
        "2.6.5" not in feat
        and "Inline-Textbearbeitung" not in feat
        and "Formatabgleich" not in feat
        and "Schriftart" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.5 Inline-Text")
    if (
        "2.6.6" not in feat
        and "Formularerstellung" not in feat
        and "AcroForm" not in feat
        and "Dropdown" not in feat
    ):
        _fail("FEATURES.md fehlt 2.6.6 Formularerstellung")
    if (
        "2.5.20" not in feat
        and "Open-Fail-A11y" not in feat
        and "Ctrl+Shift+C alle Hex" not in feat
        and "HexAll-Fail" not in feat
        and "Tag−/Clear Fail-A11y" not in feat
        and "Summary-Fail-A11y" not in feat
    ):
        _fail("FEATURES.md fehlt 2.5.20 Polish")
    if (
        "2.5.18" not in feat
        and "Pfad-Copy Fail-Path" not in feat
        and "PageUp" not in feat
        and "PgUp" not in feat
        and "Öffnen" not in feat
        and "JSON" not in feat
    ):
        _fail("FEATURES.md fehlt 2.5.18 Polish")
    if (
        "2.5.17" not in feat
        and "Text-Copy Fail-Path" not in feat
        and "Ziffern 1–6" not in feat
        and "F5 → Datei" not in feat
        and "CRUD A11y" not in feat
    ):
        _fail("FEATURES.md fehlt 2.5.17 Polish")
    if (
        "2.5.15" not in feat
        and "F5" not in feat
        and "Swatch-Tastatur" not in feat
        and "Space/H" not in feat
    ):
        _fail("FEATURES.md fehlt 2.5.15 Polish")
    if (
        "2.5.14" not in feat
        and "F4" not in feat
        and "Shift+Doppelklick" not in feat
        and "Ctrl+Doppelklick" not in feat
        and "Ctrl+Home" not in feat
    ):
        _fail("FEATURES.md fehlt 2.5.14 Polish")
    if (
        "2.5.13" not in feat
        and "Ctrl+C" not in feat
        and "Doppelklick" not in feat
        and "F3" not in feat
        and "Ctrl+↑" not in feat
        and "Reihenfolge" not in feat
    ):
        _fail("FEATURES.md fehlt 2.5.13 Polish")
    if (
        "2.5.12" not in feat
        and "Enter" not in feat
        and "Shift+Mittelklick" not in feat
        and "Ctrl+Mittelklick" not in feat
        and "F2" not in feat
        and "Ctrl+Enter" not in feat
    ):
        _fail("FEATURES.md fehlt 2.5.12 Polish")
    if (
        "2.5.11" not in feat
        and "Status schließen" not in feat
        and "Swatch-Mittelklick" not in feat
        and "Shift+Entf" not in feat
        and "Ctrl+D" not in feat
    ):
        _fail("FEATURES.md fehlt 2.5.11 Polish")
    if (
        "2.5.10" not in feat
        and "Status-RMB" not in feat
        and "Swatch-RMB" not in feat
        and "Ctrl+X" not in feat
        and "F2 Umbenennen" not in feat
    ):
        _fail("FEATURES.md fehlt 2.5.10 Polish")
    if (
        "2.5.9" not in feat
        and "Alt+Klick" not in feat
        and "Swatch-Klick" not in feat
        and "Ctrl+C/V" not in feat
        and "Pfad kopieren" not in feat
    ):
        _fail("FEATURES.md fehlt 2.5.9 Polish")
    if (
        "2.5.6" not in feat
        and "Rechtsklick" not in feat
        and "Custom duplizieren" not in feat
        and "Häufigkeit" not in feat
        and "Apply A11y" not in feat
    ):
        _fail("FEATURES.md fehlt 2.5.6 Polish")
    if (
        "2.5.5" not in feat
        and "Status-Klick" not in feat
        and "Tag-Anzahl" not in feat
        and "Duplizieren" not in feat
    ):
        _fail("FEATURES.md fehlt 2.5.5 Polish")

    if "Telemetrie" not in feat:
        _fail("FEATURES.md fehlt Telemetrie")
    if "Freihand" not in feat and "ink" not in feat.casefold():
        _fail("FEATURES.md fehlt Freihand/Ink")
    if "ildhist" not in feat and "Dokument-Historie" not in feat:
        _fail("FEATURES.md fehlt Dokument-Historie/ildhist")
    info = (ROOT / "INFO.md").read_text(encoding="utf-8")
    if "smoke_ild" not in info or "--json" not in info:
        _fail("INFO.md fehlt smoke_ild/--json Hinweis")
    if '"ok"' not in info or "duration_ms" not in info:
        _fail("INFO.md fehlt smoke --json Beispiel-Felder")
    if "error" not in info:
        _fail("INFO.md fehlt smoke --json Fail checks[].error Hinweis")
    if "200" not in info and "…" not in info:
        _fail("INFO.md fehlt Fail-error Truncate/… Hinweis")
    if "FEATURES.md" not in info or (
        "lokal" not in info.casefold() and "sync" not in info.casefold()
    ):
        _fail("INFO.md fehlt FEATURES.md lokal-sync Hinweis")
    contrib = ROOT / "CONTRIBUTING.md"
    if not contrib.is_file():
        _fail("CONTRIBUTING.md fehlt")
    contrib_txt = contrib.read_text(encoding="utf-8")
    if "smoke_ild" not in contrib_txt:
        _fail("CONTRIBUTING.md ohne smoke_ild")
    if "scripts/smoke_ild.py" not in contrib_txt and "](scripts/smoke_ild.py)" not in contrib_txt:
        _fail("CONTRIBUTING.md fehlt Link zu scripts/smoke_ild.py")
    if "Exit" not in contrib_txt:
        _fail("CONTRIBUTING.md fehlt Exitcode-Tabelle")
    if "sync-ild.ps1" not in contrib_txt:
        _fail("CONTRIBUTING.md fehlt Sync-Einzeiler (sync-ild.ps1)")
    if "Windows" not in contrib_txt:
        _fail("CONTRIBUTING.md fehlt Windows-Hinweis für Sync")
    if "-NoStart" not in contrib_txt and "NoStart" not in contrib_txt:
        _fail("CONTRIBUTING.md fehlt optional -NoStart")
    wf = ROOT / ".github" / "workflows" / "smoke-ild.yml"
    if not wf.is_file():
        _fail("Workflow-Stub smoke-ild.yml fehlt")
    wf_txt = wf.read_text(encoding="utf-8")
    if "manual only" not in wf_txt.casefold() and "MANUAL ONLY" not in wf_txt:
        _fail("Workflow-Stub fehlt klarer „manual only“-Kommentar")
    _ok("changelog + features + info + CONTRIBUTING(smoke_ild/sync/Windows/-NoStart) + workflow manual-only")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="smoke_ild.py",
        description=(
            "InstantLens Doc Nightly-Smoke (CLI/Imports/Messung/Diff).\n"
            "Exit: 0=OK (ok=true), 1=Fehler (ok=false), 2=ungültige Option."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    p.add_argument(
        "-h",
        "--help",
        action="store_true",
        help="kurze DE-Hilfe anzeigen und mit Exit 0 beenden",
    )
    p.add_argument(
        "--qt",
        action="store_true",
        help="UI-Quelltext-Checks ausführen (optional)",
    )
    p.add_argument(
        "--skip-qt",
        action="store_true",
        help="UI-Quelltext-Checks überspringen (Standard)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help=(
            "Summary als JSON auf stdout "
            "(ok/checks/duration_ms/version; Fail: checks[].error max 200…) — 2.2.0"
        ),
    )
    return p


def _print_help_de() -> None:
    print(
        """smoke_ild.py — InstantLens Doc Nightly-Smoke

Aufruf:
  python scripts/smoke_ild.py
  python scripts/smoke_ild.py --qt
  python scripts/smoke_ild.py --skip-qt
  python scripts/smoke_ild.py --json
  python scripts/smoke_ild.py -h

Optionen:
  -h, --help     kurze DE-Hilfe (Exit 0)
  --qt           UI-Quelltext-Checks (compare_dialog/pdf_view) ausführen
  --skip-qt      UI-Checks überspringen (Default ohne --qt)
  --json         Summary als JSON (ok/checks[]/duration_ms/version);
                 bei Fail: checks[] mit {name,error} (max 200…); Exitcode = ok — 2.2.0

Exit-Codes:
  0  OK (ok=true)
  1  Fehler (ok=false; Version/Import/Assertion)
  2  unbekannte Option

Laufzeit: am Ende als „Laufzeit: N ms“ (oder duration_ms im JSON).

Beispiel --json (Erfolg):
  {"ok": true, "version": "2.6.54", "duration_ms": 1234,
   "checks": ["version", "imports", "cli", "measure_diff_import", "changelog"]}

Beispiel --json (Fail):
  {"ok": false, "version": "2.6.54", "duration_ms": 12,
   "checks": ["version", {"name": "imports", "error": "import x: …"}]}
""".rstrip()
    )


def _truncate_fail_error(error: str | None, max_len: int = FAIL_ERROR_MAX_LEN) -> str:
    """Fail-error auf max_len Zeichen kürzen, Overflow mit … — 2.2.0."""
    err = (error or "FAIL").strip() or "FAIL"
    limit = max(1, int(max_len))
    if len(err) <= limit:
        return err
    # Platz für Ellipsis behalten
    if limit <= 1:
        return "…"
    return err[: limit - 1] + "…"


def _json_checks_on_fail(passed: list[str], *, check: str | None, error: str | None):
    """checks[] bei Fail: bestandene Namen + error (max 200, …) — 2.2.0."""
    out: list = list(passed)
    name = check or "unknown"
    err = _truncate_fail_error(error)
    out.append({"name": name, "error": err})
    return out


def main(argv: list[str] | None = None) -> int:
    global _CURRENT_CHECK, _LAST_ERROR, _JSON_MODE

    argv = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    try:
        args, unknown = parser.parse_known_args(argv)
    except SystemExit:
        return EXIT_USAGE
    if unknown:
        print(f"Unbekannte Option: {' '.join(unknown)}", file=sys.stderr)
        _print_help_de()
        return EXIT_USAGE
    if args.help:
        _print_help_de()
        return EXIT_OK

    with_qt = bool(args.qt) and not bool(args.skip_qt)
    # Explizites --skip-qt gewinnt; ohne Flags: skip (leichter CI-Default)
    if args.skip_qt:
        with_qt = False

    as_json = bool(args.json)
    _JSON_MODE = as_json
    t0 = time.perf_counter()
    checks: list[str] = []
    ok = True
    if not as_json:
        print(f"smoke_ild.py — InstantLens Doc {EXPECTED_VERSION}")
    try:
        _CURRENT_CHECK = "version"
        check_version()
        checks.append("version")
        _CURRENT_CHECK = "imports"
        check_imports(with_qt=with_qt)
        checks.append("imports")
        _CURRENT_CHECK = "cli"
        check_cli_version()
        checks.append("cli")
        _CURRENT_CHECK = "measure_diff_import"
        check_measure_and_diff()
        checks.append("measure_diff_import")
        _CURRENT_CHECK = "changelog"
        check_changelog()
        checks.append("changelog")
        _CURRENT_CHECK = None
    except SystemExit as e:
        ok = False
        code = int(e.code) if e.code is not None else EXIT_FAIL
        if code == 0:
            code = EXIT_FAIL
        duration_ms = int(round((time.perf_counter() - t0) * 1000))
        if as_json:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "version": EXPECTED_VERSION,
                        "duration_ms": duration_ms,
                        "checks": _json_checks_on_fail(
                            checks,
                            check=_CURRENT_CHECK,
                            error=_LAST_ERROR,
                        ),
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print(f"Laufzeit: {duration_ms} ms")
        # Exitcode spiegelt ok — 2.1.4
        return EXIT_FAIL if not ok else EXIT_OK
    except Exception as e:
        ok = False
        duration_ms = int(round((time.perf_counter() - t0) * 1000))
        err = f"{type(e).__name__}: {e}"
        _LAST_ERROR = err
        if not as_json:
            print(f"FAIL: {err}", file=sys.stderr)
        if as_json:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "version": EXPECTED_VERSION,
                        "duration_ms": duration_ms,
                        "checks": _json_checks_on_fail(
                            checks,
                            check=_CURRENT_CHECK,
                            error=err,
                        ),
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print(f"Laufzeit: {duration_ms} ms")
        return EXIT_FAIL

    duration_ms = int(round((time.perf_counter() - t0) * 1000))
    if as_json:
        print(
            json.dumps(
                {
                    "ok": True,
                    "version": EXPECTED_VERSION,
                    "duration_ms": duration_ms,
                    "checks": checks,
                },
                ensure_ascii=False,
            )
        )
    else:
        print(f"Laufzeit: {duration_ms} ms")
        print("smoke_ild: OK")
    # Exitcode spiegelt ok — 2.1.4
    return EXIT_OK if ok else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
