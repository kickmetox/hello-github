"""Offscreen-Menüinventar und Smoke-Trigger für InstantLens Doc 2.6.54."""

from __future__ import annotations

import os
import sys
import tempfile
import time
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STUB_MARKERS = (
    "noch nicht implementiert",
    "coming soon",
    "not yet implemented",
    "stub ",
    "(geplant)",
    "geplant)",
    "planned",
)

SKIP_TRIGGER_TEXTS = frozenset(
    {
        "beenden",
        "quit",
        "exit",
    }
)

# Aktionen, die ein echtes Dialogfenster brauchen (QTimer auto-close / Monkeypatch).
DIALOG_ALLOWLIST_IDS = frozenset(
    {
        "open",
        "save_as",
        "find_replace",
        "settings",
        "page_layout",
        "scan_import",
        "devices_discover",
        "devices_printers",
        "devices_refresh",
        "compare_pdfs",
        "mail_merge",
        "review_mode",
        "doc_comments",
        "shared_review",
        "version_history",
        "spellcheck",
        "preflight",
        "export_pdfx",
        "apply_bleed",
        "esign",
        "batch_pdf",
        "insert_hyperlink",
        "insert_shape",
        "keyboard_help",
        "about",
    }
)


def install_headless_env(config_home: str | None = None) -> str:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ["ILD_SMOKE_QT"] = "1"
    os.environ.setdefault("ILD_SKIP_DEPS_CHECK", "1")
    os.environ.setdefault("ILD_NO_SESSION", "1")
    os.environ.setdefault("ILD_NO_SPLASH", "1")
    if not config_home:
        config_home = tempfile.mkdtemp(prefix="ild-menu-smoke-cfg-")
    os.environ["XDG_CONFIG_HOME"] = config_home
    os.environ.setdefault("HOME", tempfile.mkdtemp(prefix="ild-menu-smoke-home-"))
    return config_home


def pump(app, seconds: float = 0.2, until=None) -> None:
    t0 = time.time()
    while time.time() - t0 < seconds:
        app.processEvents()
        if until is not None and until():
            return
        time.sleep(0.008)


def make_multipage_pdf(path: Path, pages: list[str]) -> None:
    page_ids = [3 + i * 2 for i in range(len(pages))]
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    font_id = 3 + len(pages) * 2
    objs: list[bytes] = []
    objs.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objs.append(
        f"2 0 obj<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>endobj\n".encode()
    )
    for i, text in enumerate(pages):
        page_id = page_ids[i]
        content_id = page_id + 1
        safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 18 Tf 36 200 Td ({safe}) Tj ET\n".encode()
        objs.append(
            (
                f"{page_id} 0 obj<< /Type /Page /Parent 2 0 R "
                f"/MediaBox [0 0 300 400] /Contents {content_id} 0 R "
                f"/Resources<< /Font<< /F1 {font_id} 0 R >> >> >>endobj\n"
            ).encode()
        )
        objs.append(
            f"{content_id} 0 obj<< /Length {len(stream)} >>stream\n".encode()
            + stream
            + b"endstream\nendobj\n"
        )
    objs.append(
        f"{font_id} 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n".encode()
    )
    parts = [b"%PDF-1.4\n"]
    offsets = [0]
    pos = len(parts[0])
    for o in objs:
        offsets.append(pos)
        parts.append(o)
        pos += len(o)
    xref_pos = pos
    xref = [f"xref\n0 {len(offsets)}\n".encode(), b"0000000000 65535 f \n"]
    for off in offsets[1:]:
        xref.append(f"{off:010d} 00000 n \n".encode())
    trailer = (
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode()
    path.write_bytes(b"".join(parts) + b"".join(xref) + trailer)


def make_n_page_pdf(path: Path, n: int) -> None:
    if n <= 40:
        make_multipage_pdf(path, [f"Seite{i + 1:03d}" for i in range(n)])
        return
    one = path.with_name(path.stem + "-one.pdf")
    make_multipage_pdf(one, ["Seite001"])
    import pikepdf

    src = pikepdf.open(one)
    out = pikepdf.Pdf.new()
    for _ in range(n):
        out.pages.append(src.pages[0])
    out.save(str(path))
    src.close()
    out.close()


def make_docx(path: Path) -> None:
    from docx import Document

    d = Document()
    d.add_heading("Menü-Audit DOCX", level=1)
    p = d.add_paragraph()
    r = p.add_run("Absatz mit etwas Text zum Formatieren. ")
    r.bold = True
    p.add_run("Normaler Rest.")
    d.save(str(path))


def _n_receivers(act) -> int:
    """PySide6: QObject.receivers braucht SIGNAL/Klassensignal, nicht die Instanz."""
    if act is None or not hasattr(act, "triggered"):
        return 0
    try:
        from PySide6.QtCore import SIGNAL

        return int(act.receivers(SIGNAL("triggered()")))
    except Exception:
        pass
    try:
        return int(act.receivers(type(act).triggered))
    except Exception:
        return -1


def _slot_name(act) -> str:
    try:
        slots = []
        obj = act.objectName() or ""
        if obj:
            slots.append(obj)
        n = _n_receivers(act)
        if n > 0:
            slots.append(f"triggered×{n}")
        tip = (act.toolTip() or "").strip()
        if tip and len(tip) < 80 and tip not in slots:
            slots.append(tip.replace("|", "/"))
        return "; ".join(slots) if slots else ""
    except Exception as e:
        return f"? {e}"


def _shortcut_str(act) -> str:
    try:
        seqs = []
        if hasattr(act, "shortcuts"):
            for s in act.shortcuts() or []:
                t = s.toString() if hasattr(s, "toString") else str(s)
                if t:
                    seqs.append(t)
        if not seqs and hasattr(act, "shortcut"):
            s = act.shortcut()
            t = s.toString() if hasattr(s, "toString") else str(s)
            if t:
                seqs.append(t)
        return ", ".join(seqs)
    except Exception:
        return ""


def _is_stub_text(*parts: str) -> bool:
    blob = " ".join(parts).lower()
    return any(m in blob for m in STUB_MARKERS)


EDITOR_ONLY_STATUS = "editor-only · bei PDF deaktiviert"

# Line spacing / Absatz / Stile / Einrückung / Seitenlayout (+ übrige Editor-Typografie).
EDITOR_ONLY_NEEDLES = (
    "zeilenabstand",
    "absatz links",
    "absatz zentriert",
    "absatz rechts",
    "absatz blocksatz",
    "laufweite",
    "durchschuss",
    "tracking",
    "leading",
    "silbentrennung",
    "einrückung",
    "seitenlayout",
    "automatische formatierung",
    "formatvorlage",
    "absatzstil",
    "zeichenstil",
    "stil-preset",
    "inhaltsverzeichnis",
    "abbildungsverzeichnis",
    "stichwortverzeichnis",
    "initial / drop",
    "drop cap",
    "textbaustein",
    "sonderzeichen einfügen",
    "markdown-vorschau",
    "wortumbruch",
    "zeilennummern",
    "editor-minimap",
    "einrückungs-guides",
    "sonderzeichen anzeigen",
    "fett",
    "kursiv",
    "unterstrichen",
    "groß-/klein",
    "alles groß",
    "alles klein",
)

# Ribbon-/Palette-IDs, die nur im Text/DOCX-Editor gelten (PDF-disabled).
EDITOR_ONLY_IDS = frozenset(
    {
        "page_layout",
        "insert_hyperlink",
        "insert_shape",
        "insert_snippet",
        "insert_table",
        "format_table",
        "sort_table",
        "import_table_data",
        "export_epub",
        "export_pptx",
        "auto_toc",
        "auto_lof",
        "auto_index",
        "auto_format",
        "toggle_bold",
        "toggle_italic",
        "toggle_underline",
        "para_align_left",
        "para_align_center",
        "para_align_right",
        "para_align_justify",
        "typo_tracking",
        "typo_leading",
        "drop_cap",
        "hyphenate_de",
        "hyphenate_en",
        "hyphenate_fr",
        "hyphenate_ru",
        "hyphenate_es",
        "hyphenate_zh",
        "hyphenate_pt",
        "hyphenate_ar",
        "hyphenate_it",
        "bold",
        "italic",
        "underline",
        "mark",
        "clear_marks",
        "edit",
        "select",
        "find",
    }
)


def editor_only_reason(path: str, text: str, extra_id: str = "") -> str:
    blob = f"{path} {text}".lower()
    eid = (extra_id or "").strip().lower()
    if eid in EDITOR_ONLY_IDS:
        return EDITOR_ONLY_STATUS
    if any(x in blob for x in EDITOR_ONLY_NEEDLES):
        return EDITOR_ONLY_STATUS
    if "einfügen ▸" in blob and "gerät" not in blob:
        return EDITOR_ONLY_STATUS
    if blob.startswith("editor-leiste ▸"):
        return EDITOR_ONLY_STATUS
    return ""


def _win_is_pdf(win) -> bool:
    try:
        return (
            win.stack.currentWidget() is win.pdf_view
            and bool(getattr(win.pdf_view, "pdf_path", None))
        )
    except Exception:
        return False


def apply_editor_only_pdf_disabled(rows: list[dict[str, Any]], win) -> None:
    """Inventar: Editor-only (Zeilenabstand/Absatz/Stile/Einrückung/Seitenlayout) bei PDF = aus."""
    is_pdf = _win_is_pdf(win)
    for r in rows:
        eid = (
            r.get("ribbon_id")
            or r.get("palette_id")
            or r.get("editor_id")
            or r.get("object_name")
            or ""
        )
        reason = editor_only_reason(r.get("path") or "", r.get("text") or "", eid)
        r["editor_only"] = bool(reason)
        if r["editor_only"] and is_pdf:
            r["enabled"] = False
        r["status"] = _row_status(r)


def _row_status(r: dict[str, Any]) -> str:
    if r.get("stub"):
        return "stub"
    if r.get("editor_only"):
        return EDITOR_ONLY_STATUS
    nrecv = int(r.get("receivers") or 0)
    if r.get("kind") == "menu" and nrecv == 0:
        return "kein Slot"
    if not r.get("enabled"):
        return "aus"
    area = r.get("area") or ""
    return f"ok · {area}" if area else "ok"


def classify_area(path: str, text: str, kind: str) -> str:
    p = f"{path} {text}".lower()
    if any(
        x in p
        for x in (
            "scan",
            "gerät",
            "drucker",
            "scanner",
            "devices_",
            "scan_import",
        )
    ):
        return "B"
    if any(
        x in p
        for x in (
            "minimap",
            "als pdf",
            "pdf/x",
            "text → pdf",
            "export_pdfx",
            "save_as",
            "speichern unter",
        )
    ):
        return "A"
    if any(
        x in p
        for x in (
            "zuletzt geöffnet",
            "schließen",
            "tab ",
            "tabs ",
            "öffnen",
            "seite ◀",
            "seite ▶",
            "gehe zu seite",
            "nächste seite",
            "vorherige seite",
        )
    ) and kind in ("menu", "toolbar", "ribbon"):
        if "annotation" in p or "markier" in p:
            return "D"
        if any(x in p for x in ("zuletzt", "tab", "schließen", "öffnen…", "öffnen mit")):
            return "C"
    if any(
        x in p
        for x in (
            "annotation",
            "annot.",
            "highlight",
            "stempel",
            "schwärz",
            "objekt",
            "inline",
            "freihand",
            "notiz",
            "text bearbeiten",
            "undo_annotation",
            "rückgängig",
        )
    ) and ("pdf" in p or kind in ("pdf-toolbar", "context")):
        return "D"
    if kind == "pdf-toolbar" and any(
        x in p for x in ("◀", "▶", "seite", "zoom", "fit")
    ):
        return "C"
    if kind == "pdf-toolbar":
        return "D"
    return ""


def walk_menu(menu, prefix: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if menu is None:
        return rows
    for act in menu.actions():
        if act.isSeparator():
            continue
        text = (act.text() or "").replace("&", "").strip()
        sub = act.menu() if hasattr(act, "menu") else None
        path = f"{prefix} ▸ {text}" if text else prefix
        if sub is not None:
            rows.extend(walk_menu(sub, path))
            continue
        nrecv = _n_receivers(act)
        eo = editor_only_reason(path, text, act.objectName() or "")
        row = {
            "kind": "menu",
            "path": path,
            "text": text,
            "shortcut": _shortcut_str(act),
            "slot": _slot_name(act),
            "object_name": act.objectName() or "",
            "enabled": bool(act.isEnabled()),
            "checkable": bool(act.isCheckable()),
            "receivers": nrecv,
            "stub": _is_stub_text(text, act.toolTip() or "", act.statusTip() or ""),
            "tooltip": (act.toolTip() or "").replace("\n", " "),
            "area": classify_area(path, text, "menu"),
            "editor_only": bool(eo),
            "action": act,
        }
        row["status"] = _row_status(row)
        rows.append(row)
    return rows


def inventory_window(win) -> list[dict[str, Any]]:
    from PySide6.QtGui import QAction, QShortcut
    from PySide6.QtWidgets import QMenuBar, QPushButton, QToolButton

    rows: list[dict[str, Any]] = []
    mb = win.menuBar()
    for top in mb.actions():
        menu = top.menu()
        title = (top.text() or "").replace("&", "").strip()
        if menu is not None:
            rows.extend(walk_menu(menu, title))
        elif (top.text() or "").strip():
            rows.append(
                {
                    "kind": "menu",
                    "path": title,
                    "text": title,
                    "shortcut": _shortcut_str(top),
                    "slot": _slot_name(top),
                    "object_name": top.objectName() or "",
                    "enabled": bool(top.isEnabled()),
                    "checkable": bool(top.isCheckable()),
                    "receivers": _n_receivers(top),
                    "stub": _is_stub_text(title),
                    "tooltip": (top.toolTip() or "").replace("\n", " "),
                    "area": "",
                    "action": top,
                }
            )

    rb = getattr(win, "ribbon_bar", None)
    if rb is not None:
        for i, btn in enumerate(getattr(rb, "_cat_buttons", []) or []):
            rows.append(
                {
                    "kind": "ribbon-tab",
                    "path": f"Ribbon ▸ Tab:{btn.text()}",
                    "text": btn.text(),
                    "shortcut": f"Alt+{i + 1}" if i < 7 else "",
                    "slot": "_select_cat",
                    "object_name": btn.objectName() or "",
                    "enabled": bool(btn.isEnabled()),
                    "checkable": True,
                    "receivers": 1,
                    "stub": False,
                    "tooltip": (btn.toolTip() or "").replace("\n", " "),
                    "area": "B" if "gerät" in (btn.text() or "").lower() else "",
                    "action": None,
                    "ribbon_id": None,
                    "widget": btn,
                }
            )
        seen_ids = set()
        for aid, tb in (getattr(rb, "_actions", {}) or {}).items():
            if aid in seen_ids:
                continue
            seen_ids.add(aid)
            rows.append(
                {
                    "kind": "ribbon",
                    "path": f"Ribbon ▸ {tb.text()}",
                    "text": tb.text(),
                    "shortcut": "",
                    "slot": f"_on_ribbon_action({aid})",
                    "object_name": aid,
                    "enabled": bool(tb.isEnabled()),
                    "checkable": bool(tb.isCheckable()),
                    "receivers": 1,
                    "stub": _is_stub_text(tb.text(), tb.toolTip() or ""),
                    "tooltip": (tb.toolTip() or "").replace("\n", " "),
                    "area": classify_area("Ribbon", f"{aid} {tb.text()}", "ribbon"),
                    "action": None,
                    "ribbon_id": aid,
                    "widget": tb,
                }
            )

    pane = getattr(win, "editor_pane", None)
    if pane is not None:
        for aid, tb in (getattr(pane, "_tool_buttons", {}) or {}).items():
            rows.append(
                {
                    "kind": "editor-toolbar",
                    "path": f"Editor-Leiste ▸ {tb.text()}",
                    "text": tb.text(),
                    "shortcut": "",
                    "slot": f"_on_editor_toolbar_action({aid})",
                    "object_name": tb.objectName() or aid,
                    "enabled": bool(tb.isEnabled()),
                    "checkable": bool(tb.isCheckable()),
                    "receivers": 1,
                    "stub": False,
                    "tooltip": (tb.toolTip() or "").replace("\n", " "),
                    "area": "A" if aid in ("select",) else "",
                    "action": None,
                    "editor_id": aid,
                    "widget": tb,
                }
            )

    pv = getattr(win, "pdf_view", None)
    host = getattr(pv, "_toolbar_host", None) if pv is not None else None
    if host is not None:
        for w in list(host.findChildren(QPushButton)) + list(host.findChildren(QToolButton)):
            text = (w.text() or w.objectName() or "").strip() or "?"
            rows.append(
                {
                    "kind": "pdf-toolbar",
                    "path": f"PDF-Leiste ▸ {text}",
                    "text": text,
                    "shortcut": "",
                    "slot": (w.toolTip() or "")[:80],
                    "object_name": w.objectName() or "",
                    "enabled": bool(w.isEnabled()),
                    "checkable": bool(getattr(w, "isCheckable", lambda: False)()),
                    "receivers": 1,
                    "stub": False,
                    "tooltip": (w.toolTip() or "").replace("\n", " "),
                    "area": classify_area("PDF-Leiste", text, "pdf-toolbar"),
                    "action": None,
                    "widget": w,
                }
            )

    # Globale Shortcuts am Fenster
    for sc in win.findChildren(QShortcut):
        try:
            seq = sc.key().toString() if sc.key() else ""
        except Exception:
            seq = ""
        if not seq:
            continue
        rows.append(
            {
                "kind": "shortcut",
                "path": f"Shortcut ▸ {seq}",
                "text": seq,
                "shortcut": seq,
                "slot": sc.objectName() or "QShortcut",
                "object_name": sc.objectName() or "",
                "enabled": bool(sc.isEnabled()),
                "checkable": False,
                "receivers": 1,
                "stub": False,
                "tooltip": "",
                "area": "",
                "action": None,
                "widget": sc,
            }
        )

    # Command palette ids (kein Widget-Trigger hier)
    try:
        from instantlensdoc.ui.command_palette import default_palette_commands

        for cmd in default_palette_commands():
            rows.append(
                {
                    "kind": "palette",
                    "path": f"Palette ▸ {cmd.category} ▸ {cmd.title}",
                    "text": cmd.title,
                    "shortcut": cmd.shortcut or "",
                    "slot": cmd.id,
                    "object_name": cmd.id,
                    "enabled": True,
                    "checkable": False,
                    "receivers": 1,
                    "stub": _is_stub_text(cmd.title),
                    "tooltip": cmd.keywords,
                    "area": classify_area("Palette", f"{cmd.id} {cmd.title}", "ribbon"),
                    "action": None,
                    "palette_id": cmd.id,
                }
            )
    except Exception:
        pass

    apply_editor_only_pdf_disabled(rows, win)
    return rows


def shortcut_collisions(rows: Iterable[dict]) -> list[tuple[str, list[str]]]:
    by: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        sc = (r.get("shortcut") or "").strip()
        if not sc or r.get("kind") == "shortcut":
            continue
        for part in sc.split(","):
            key = part.strip()
            if key:
                by[key].append(r.get("path") or r.get("text") or "")
    return sorted((k, v) for k, v in by.items() if len(v) > 1)


def english_in_de_ui(rows: Iterable[dict]) -> list[str]:
    needles = (
        "continuous scroll",
        "book layout",
        "high-contrast",
        "coming soon",
        "fit-page",
        "fit-width",
        "workspace-layouts",
        "quick-apply",
        "markdown preview",
        "shared review",
    )
    hits = []
    for r in rows:
        blob = f"{r.get('text','')} {r.get('path','')}".lower()
        for n in needles:
            if n in blob:
                hits.append(r.get("path") or r.get("text") or n)
                break
    return hits


def install_qt_hooks(records: list[dict]) -> Callable[[], None]:
    import sys as _sys

    from PySide6.QtCore import QtMsgType, qInstallMessageHandler
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import (
        QColorDialog,
        QFileDialog,
        QInputDialog,
        QMessageBox,
    )

    orig_excepthook = _sys.excepthook

    def _hook(exctype, value, tb):
        try:
            records.append(
                {"type": "unhandled", "exc": f"{getattr(exctype, '__name__', exctype)}: {value}"}
            )
        except Exception:
            pass
        try:
            if orig_excepthook is not _hook:
                orig_excepthook(exctype, value, tb)
        except Exception:
            pass

    _sys.excepthook = _hook

    def _qt_msg(mode, ctx, msg):
        if mode in (QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg, QtMsgType.QtWarningMsg):
            if "libpng" in (msg or "") or "QFont" in (msg or ""):
                return
            records.append({"type": "qt", "mode": str(mode), "msg": str(msg)})

    qInstallMessageHandler(_qt_msg)

    tmp = Path(tempfile.mkdtemp(prefix="ild-menu-dlg-"))

    def _save(*_a, **_k):
        p = tmp / f"out-{len(list(tmp.iterdir()))}.bin"
        return str(p), "All (*)"

    def _open(*_a, **_k):
        return "", ""

    def _dir(*_a, **_k):
        return str(tmp)

    QFileDialog.getSaveFileName = staticmethod(_save)
    QFileDialog.getOpenFileName = staticmethod(_open)
    QFileDialog.getOpenFileNames = staticmethod(lambda *_a, **_k: ([], ""))
    QFileDialog.getExistingDirectory = staticmethod(_dir)

    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.Ok)
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.Ok)
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.No)

    QInputDialog.getText = staticmethod(lambda *a, **k: ("audit", True))
    QInputDialog.getInt = staticmethod(lambda *a, **k: (1, True))
    QInputDialog.getDouble = staticmethod(lambda *a, **k: (1.0, True))

    def _get_item(*a, **k):
        items = []
        if len(a) >= 4 and isinstance(a[3], (list, tuple)):
            items = list(a[3])
        elif isinstance(k.get("items"), (list, tuple)):
            items = list(k["items"])
        if not items:
            return "", False
        return str(items[0]), True

    QInputDialog.getItem = staticmethod(_get_item)
    QInputDialog.getMultiLineText = staticmethod(lambda *a, **k: ("audit", True))

    from PySide6.QtGui import QColor

    QColorDialog.getColor = staticmethod(lambda *a, **k: QColor("#ffcc00"))
    QDesktopServices.openUrl = staticmethod(lambda *_a, **_k: True)

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QDialog, QMenu

    _orig_dlg_exec = QDialog.exec

    def _auto_reject_exec(self, *args, **kwargs):
        try:
            QTimer.singleShot(30, self.reject)
        except Exception:
            pass
        try:
            return _orig_dlg_exec(self, *args, **kwargs)
        except Exception:
            return int(QDialog.Rejected)

    QDialog.exec = _auto_reject_exec  # type: ignore[method-assign]

    def _menu_exec(self, *args, **kwargs):
        try:
            self.hide()
        except Exception:
            pass
        return None

    QMenu.exec = _menu_exec  # type: ignore[method-assign]

    try:
        from PySide6.QtPrintSupport import QPrintDialog

        QPrintDialog.exec = lambda self, *a, **k: QPrintDialog.Rejected  # type: ignore[method-assign]
    except Exception:
        pass

    try:
        import urllib.request as ur

        def _no_net(*_a, **_k):
            raise OSError("menu-smoke: network disabled")

        ur.urlopen = _no_net  # type: ignore[assignment]
    except Exception:
        pass

    def restore() -> None:
        _sys.excepthook = orig_excepthook
        qInstallMessageHandler(None)

    return restore


def dismiss_modals(app) -> int:
    from PySide6.QtWidgets import QApplication, QDialog, QMenu

    n = 0
    app = app or QApplication.instance()
    if app is None:
        return 0
    w = app.activeModalWidget()
    if w is not None:
        try:
            if isinstance(w, QDialog):
                w.reject()
            elif isinstance(w, QMenu):
                w.hide()
                w.close()
            else:
                w.close()
            n += 1
        except Exception:
            try:
                w.hide()
            except Exception:
                pass
    for d in list(app.topLevelWidgets()):
        try:
            if isinstance(d, QDialog) and d.isVisible() and d.isModal():
                d.reject()
                n += 1
            elif isinstance(d, QMenu) and d.isVisible():
                d.hide()
                n += 1
        except Exception:
            pass
    app.processEvents()
    return n


def trigger_callable(app, fn: Callable[[], None], timeout: float = 4.0) -> dict:
    from PySide6.QtCore import QTimer

    result = {
        "exc": None,
        "dialogs": 0,
        "hang": False,
        "silent": False,
        "status_before": "",
        "status_after": "",
    }
    t0 = time.time()
    closer = QTimer()
    closer.setInterval(60)

    def _tick():
        result["dialogs"] += dismiss_modals(app)
        if time.time() - t0 > timeout:
            still_modal = False
            try:
                from PySide6.QtWidgets import QApplication, QDialog

                inst = app or QApplication.instance()
                w = inst.activeModalWidget() if inst is not None else None
                still_modal = w is not None and (
                    not isinstance(w, QDialog) or w.isVisible()
                )
            except Exception:
                still_modal = False
            if still_modal:
                result["hang"] = True
            closer.stop()
            dismiss_modals(app)

    closer.timeout.connect(_tick)
    closer.start()
    try:
        fn()
    except Exception:
        result["exc"] = traceback.format_exc()
    pump(app, min(0.16, timeout), until=lambda: result["hang"])
    closer.stop()
    result["dialogs"] += dismiss_modals(app)
    pump(app, 0.05)
    return result


def ribbon_handler_ids(win) -> set[str]:
    """IDs, die _on_ribbon_action kennt — per Source-Probe der gebundenen Buttons."""
    rb = getattr(win, "ribbon_bar", None)
    if rb is None:
        return set()
    return set((getattr(rb, "_actions", {}) or {}).keys())


def missing_ribbon_handlers(win) -> list[str]:
    ids = ribbon_handler_ids(win)
    # Probe: rufe Handler-Map indirekt nicht auf; parse Quelle der Methode
    import inspect

    src = inspect.getsource(win._on_ribbon_action)
    missing = []
    for aid in sorted(ids):
        if f'"{aid}"' not in src and f"'{aid}'" not in src:
            missing.append(aid)
    return missing


SKIP_PATH_SUBSTR = (
    "beenden",
)


HEAVY_ON_LARGE_PDF = (
    "ocr",
    "→bilder",
    "einbrennen",
    "gesamten pdf-text",
    "alle seitenbilder",
    "komprimier",
    "preflight",
    "stapelverarbeitung",
    "handschriften",
    "redactions anwenden",
    "echt schwärzen",
    "theme",
    "dunkles design",
    "hoher kontrast",
)


def should_skip_trigger(row: dict, state: str | None = None) -> bool:
    text = (row.get("text") or "").replace("&", "").strip().lower()
    path = (row.get("path") or "").lower()
    if text in SKIP_TRIGGER_TEXTS:
        return True
    if any(s in path for s in SKIP_PATH_SUBSTR) and row.get("kind") == "menu":
        if path.endswith("beenden") or path.endswith(" ▸ beenden"):
            return True
    if row.get("kind") in ("shortcut", "ribbon-tab"):
        return True
    if state == "pdf500":
        blob = f"{path} {text}"
        if any(h in blob for h in HEAVY_ON_LARGE_PDF):
            return True
        if row.get("kind") == "palette":
            return True
    return False


def trigger_row(app, win, row: dict, state: str | None = None) -> dict:
    kind = row.get("kind")
    if should_skip_trigger(row, state):
        return {"skipped": True}

    def _fn():
        if kind == "menu" and row.get("action") is not None:
            row["action"].trigger()
            return
        if kind == "ribbon" and row.get("ribbon_id"):
            win._on_ribbon_action(row["ribbon_id"])
            return
        if kind == "editor-toolbar" and row.get("editor_id"):
            win._on_editor_toolbar_action(row["editor_id"])
            return
        if kind == "pdf-toolbar" and row.get("widget") is not None:
            w = row["widget"]
            w.click()
            return
        if kind == "palette" and row.get("palette_id"):
            win._run_palette_command(row["palette_id"])
            return
        if row.get("action") is not None:
            row["action"].trigger()

    before = ""
    try:
        before = win.statusBar().currentMessage() if win.statusBar() else ""
    except Exception:
        before = ""
    out = trigger_callable(app, _fn)
    try:
        after = win.statusBar().currentMessage() if win.statusBar() else ""
    except Exception:
        after = ""
    out["status_before"] = before
    out["status_after"] = after
    if (
        not out.get("exc")
        and not out.get("dialogs")
        and not out.get("hang")
        and before == after
        and kind in ("menu", "ribbon", "palette")
        and int(row.get("receivers") or 0) == 0
    ):
        out["silent"] = True
        out["no_slot"] = True
    if int(row.get("receivers") or 0) == 0 and kind == "menu":
        out["no_slot"] = True
    if row.get("stub"):
        out["stub"] = True
    return out


def current_state_tag(win, fixtures: dict[str, Path] | None = None) -> str:
    try:
        pv = getattr(win, "pdf_view", None)
        path = str(getattr(pv, "pdf_path", "") or "")
        if path:
            if fixtures and path == str(fixtures.get("pdf500") or ""):
                return "pdf500"
            if fixtures and path == str(fixtures.get("pdf20") or ""):
                return "pdf20"
            if "audit-500" in path:
                return "pdf500"
            if "audit-20" in path:
                return "pdf20"
            return "pdf"
        stack_w = win.stack.currentWidget() if getattr(win, "stack", None) else None
        if stack_w is getattr(win, "editor_pane", None):
            doc = getattr(win, "doc", None)
            dp = str(getattr(doc, "path", "") or "") if doc else ""
            if dp.lower().endswith(".docx"):
                return "docx"
            return "empty"
        return "none"
    except Exception:
        return "?"


def load_state(win, app, state: str, fixtures: dict[str, Path]) -> None:
    if current_state_tag(win, fixtures) == state:
        return
    try:
        if getattr(win, "doc", None) is not None:
            win.doc.dirty = False
        store = getattr(getattr(win, "pdf_view", None), "store", None)
        if store is not None:
            store.dirty = False
    except Exception:
        pass
    if state == "none":
        try:
            if hasattr(win, "close_all_tabs"):
                win.close_all_tabs()
        except Exception:
            pass
        pump(app, 0.15)
        return
    if state == "empty":
        win.new_doc("empty")
        pump(app, 0.2)
        return
    if state == "docx":
        win.open_path(str(fixtures["docx"]))
        pump(app, 0.35)
        return
    if state in ("pdf20", "pdf500"):
        key = "pdf20" if state == "pdf20" else "pdf500"
        p = fixtures[key]
        if key == "pdf500" and not p.is_file():
            make_n_page_pdf(p, 500)
        win.open_path(str(p))
        pump(app, 0.9 if state == "pdf20" else 2.0)
        return


def build_fixtures(td: Path, *, with_pdf500: bool = False) -> dict[str, Path]:
    pdf20 = td / "audit-20.pdf"
    pdf500 = td / "audit-500.pdf"
    docx = td / "audit.docx"
    make_n_page_pdf(pdf20, 20)
    if with_pdf500:
        make_n_page_pdf(pdf500, 500)
    make_docx(docx)
    return {"pdf20": pdf20, "pdf500": pdf500, "docx": docx}


def create_main_window():
    from PySide6.QtWidgets import QApplication

    from instantlensdoc.license import LicenseManager
    from instantlensdoc.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    lm = LicenseManager()
    lm.ensure_trial_started()
    win = MainWindow(lm)
    win.resize(1400, 900)
    win.show()
    pump(app, 0.25)
    return app, win


def format_inventory_markdown(rows: list[dict[str, Any]], *, state_note: str) -> str:
    from collections import Counter

    kinds = Counter(r.get("kind") or "?" for r in rows)
    n_eo = sum(1 for r in rows if r.get("editor_only"))
    n_dis = sum(1 for r in rows if r.get("kind") == "menu" and not r.get("enabled"))
    lines = [
        "---",
        "cursor:",
        '  subagentId: "bc-03419908-ec29-523f-9ae4-eb21b9e2c1c1"',
        "---",
        "",
        "# InstantLens Doc 2.6.54 — Menü-Inventar",
        "",
        f"Offscreen-Walk (`QT_QPA_PLATFORM=offscreen`) über QMenuBar, Ribbon-Tabs, "
        f"Editor-Leiste, PDF-Leiste, Command-Palette und QShortcut. {state_note}",
        "",
        "## Zählung",
        "",
        "| Art | Anzahl |",
        "|---|---|",
    ]
    for k in sorted(kinds):
        lines.append(f"| {k} | {kinds[k]} |")
    lines.append(f"| **Summe** | **{len(rows)}** |")
    lines.append(f"| Editor-only (bei PDF deaktiviert) | {n_eo} |")
    lines.append(f"| Menüeinträge disabled (PDF-Zustand) | {n_dis} |")
    lines.extend(
        [
            "",
            "## Tabelle",
            "",
            "| Menüpfad | Text | Kürzel | Slot | Status |",
            "|---|---|---|---|---|",
        ]
    )
    for r in rows:
        path = str(r.get("path") or "").replace("|", "/")
        text = str(r.get("text") or "").replace("|", "/")
        sc = str(r.get("shortcut") or "").replace("|", "/")
        slot = str(r.get("slot") or "").replace("|", "/")[:80]
        st = str(r.get("status") or "").replace("|", "/")
        lines.append(f"| {path} | {text} | {sc} | {slot} | {st} |")
    lines.append("")
    return "\n".join(lines)
