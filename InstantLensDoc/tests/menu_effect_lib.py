"""Audit 2655: PASS nur bei echtem Dialog oder sichtbarer Dokument-/UI-Änderung."""

from __future__ import annotations

import json
import os
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtGui import QGuiApplication, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QDialog,
    QFileDialog,
    QFontDialog,
    QInputDialog,
    QMenu,
    QMessageBox,
    QWidget,
)

from menu_smoke_lib import (
    SKIP_TRIGGER_TEXTS,
    build_fixtures,
    create_main_window,
    install_headless_env,
    inventory_window,
    load_state,
    pump,
    walk_menu,
)


FAIL_DIALOG_CLASSES = frozenset({"StubInfoDialog", "QMessageBox"})
FAIL_OBJECT_NAMES = frozenset({"stubInfoDialog"})


def make_ocr_text(path: Path) -> None:
    path.write_text(
        "OCR-Import\nAbsatz mit Text zum Formatieren und Suchen.\nDritte Zeile.\n",
        encoding="utf-8",
    )


def build_effect_fixtures(td: Path) -> dict[str, Path]:
    fx = build_fixtures(td, with_pdf500=False)
    ocr = td / "audit-ocr.txt"
    make_ocr_text(ocr)
    fx["ocr"] = ocr
    return fx


def load_effect_state(win, app, state: str, fixtures: dict[str, Path]) -> None:
    if state == "ocr":
        try:
            if getattr(win, "doc", None) is not None:
                win.doc.dirty = False
        except Exception:
            pass
        win.open_path(str(fixtures["ocr"]))
        pump(app, 0.35)
        try:
            win._sync_menu_enablement()
            win._sync_undo_redo_enabled()
        except Exception:
            pass
        return
    if state == "pdf":
        load_state(win, app, "pdf20", fixtures)
    else:
        load_state(win, app, state, fixtures)
    pump(app, 0.2)
    try:
        win._sync_menu_enablement()
        win._sync_undo_redo_enabled()
    except Exception:
        pass


def _clip_text() -> str:
    try:
        cb = QGuiApplication.clipboard()
        return cb.text() if cb is not None else ""
    except Exception:
        return ""


def _clip_token() -> str:
    try:
        cb = QGuiApplication.clipboard()
        if cb is None:
            return ""
        md = cb.mimeData()
        if md is None:
            return ""
        raw = md.data("application/x-ild-copy")
        return bytes(raw).decode("utf-8", errors="replace") if raw else ""
    except Exception:
        return ""


def snapshot_state(win) -> dict[str, Any]:
    ed = getattr(win, "editor", None)
    html = ""
    plain = ""
    cursor = -1
    sel = 0
    if ed is not None:
        try:
            html = ed.document().toHtml()
        except Exception:
            html = ""
        try:
            plain = ed.toPlainText()
        except Exception:
            plain = ""
        try:
            cur = ed.textCursor()
            cursor = int(cur.position())
            sel = int(abs(cur.selectionEnd() - cur.selectionStart()))
        except Exception:
            pass
        try:
            extras = len(ed.extraSelections())
        except Exception:
            extras = 0
        try:
            rev = int(ed.document().revision())
        except Exception:
            rev = 0
        try:
            bms = len(ed.list_line_bookmarks()) if hasattr(ed, "list_line_bookmarks") else 0
        except Exception:
            bms = 0
    else:
        extras = 0
        rev = 0
        bms = 0
    checks = []
    try:
        mb = win.menuBar()
        for top in mb.actions():
            menu = top.menu() if hasattr(top, "menu") else None
            if menu is None:
                continue
            for act in menu.actions():
                if act.isSeparator():
                    continue
                sub = act.menu() if hasattr(act, "menu") else None
                if sub is not None:
                    for sa in sub.actions():
                        if sa.isCheckable():
                            checks.append(f"{sa.text()}={int(sa.isChecked())}")
                    continue
                if act.isCheckable():
                    checks.append(f"{act.text()}={int(act.isChecked())}")
    except Exception:
        pass
    stack = ""
    try:
        w = win.stack.currentWidget()
        stack = w.objectName() or type(w).__name__
    except Exception:
        stack = ""
    pv = getattr(win, "pdf_view", None)
    page = zoom = tool = n_ann = None
    if pv is not None:
        for attr in ("page_index", "current_page", "_page", "page"):
            if hasattr(pv, attr):
                try:
                    page = getattr(pv, attr)
                    if callable(page):
                        page = page()
                    break
                except Exception:
                    pass
        for attr in ("zoom", "_zoom", "scale"):
            if hasattr(pv, attr):
                try:
                    zoom = getattr(pv, attr)
                    if callable(zoom):
                        zoom = zoom()
                    break
                except Exception:
                    pass
        tool = getattr(pv, "tool", None) or getattr(pv, "_tool", None) or getattr(pv, "current_tool", None)
        if hasattr(tool, "value"):
            try:
                tool = tool.value
            except Exception:
                pass
        try:
            store = getattr(pv, "store", None)
            n_ann = len(store.all()) if store is not None and hasattr(store, "all") else None
        except Exception:
            n_ann = None
    sidebar = None
    try:
        sidebar = bool(win.sidebar.isVisible())
    except Exception:
        pass
    split = None
    try:
        sw = getattr(win, "secondary_wrap", None)
        split = bool(sw.isVisible()) if sw is not None else None
    except Exception:
        pass
    status = ""
    try:
        status = win.statusBar().currentMessage() or ""
    except Exception:
        status = ""
    dirty = False
    try:
        dirty = bool(getattr(getattr(win, "doc", None), "dirty", False))
    except Exception:
        dirty = False
    n_tabs = 0
    try:
        n_tabs = len(list(win.sidebar.document_paths() or []))
    except Exception:
        n_tabs = 0
    ribbon_vis = None
    try:
        rb = getattr(win, "ribbon_bar", None)
        ribbon_vis = bool(rb.isVisible()) if rb is not None else None
    except Exception:
        ribbon_vis = None
    tabs_vis = None
    try:
        tb = getattr(win, "doc_tab_bar", None)
        tabs_vis = bool(tb.isVisible()) if tb is not None else None
    except Exception:
        tabs_vis = None
    ed_tool = ""
    try:
        pane = getattr(win, "editor_pane", None)
        ed_tool = pane.active_tool() if pane is not None and hasattr(pane, "active_tool") else ""
        for aid, tbtn in (getattr(pane, "_tool_buttons", {}) or {}).items():
            if tbtn.isCheckable():
                checks.append(f"ed:{aid}={int(tbtn.isChecked())}")
    except Exception:
        pass
    pdf_btns = []
    try:
        host = getattr(pv, "_toolbar_host", None) if pv is not None else None
        if host is not None:
            from PySide6.QtWidgets import QAbstractButton

            for w in host.findChildren(QAbstractButton):
                if w.isCheckable():
                    pdf_btns.append(f"{w.text()}={int(w.isChecked())}")
    except Exception:
        pdf_btns = []
    project = ""
    try:
        from instantlensdoc.core.app_settings import get_active_project_workspace

        wp = get_active_project_workspace()
        project = str(wp) if wp else ""
    except Exception:
        project = ""
    snippets = ""
    try:
        from instantlensdoc.core.app_settings import get_editor_snippets

        snippets = "|".join(get_editor_snippets() or [])
    except Exception:
        snippets = ""
    unit = ""
    try:
        from instantlensdoc.core.app_settings import get_page_size_unit

        unit = str(get_page_size_unit() or "")
    except Exception:
        unit = ""
    checkables = "|".join(checks)
    return {
        "html": html,
        "plain": plain,
        "cursor": cursor,
        "sel": sel,
        "stack": stack,
        "page": page,
        "zoom": zoom,
        "tool": str(tool) if tool is not None else "",
        "n_ann": n_ann,
        "sidebar": sidebar,
        "split": split,
        "clip": _clip_text(),
        "clip_token": _clip_token(),
        "win_w": int(win.width()) if win is not None else 0,
        "win_h": int(win.height()) if win is not None else 0,
        "rev": rev,
        "extras": extras,
        "checkables": checkables,
        "status": status,
        "dirty": dirty,
        "n_tabs": n_tabs,
        "ribbon_vis": ribbon_vis,
        "tabs_vis": tabs_vis,
        "ed_tool": ed_tool,
        "pdf_btns": "|".join(pdf_btns),
        "project": project,
        "snippets": snippets,
        "bookmarks": bms,
        "unit": unit,
    }


def state_changed(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    keys = (
        "html",
        "plain",
        "cursor",
        "sel",
        "stack",
        "page",
        "zoom",
        "tool",
        "n_ann",
        "sidebar",
        "split",
        "clip",
        "clip_token",
        "win_w",
        "win_h",
        "rev",
        "extras",
        "checkables",
        "status",
        "dirty",
        "n_tabs",
        "ribbon_vis",
        "tabs_vis",
        "ed_tool",
        "pdf_btns",
        "project",
        "snippets",
        "bookmarks",
        "unit",
    )
    hits = []
    for k in keys:
        if before.get(k) != after.get(k):
            hits.append(k)
    return hits


class DialogRecorder:
    def __init__(self, shot_dir: Path | None = None) -> None:
        self.events: list[dict[str, Any]] = []
        self.shot_dir = shot_dir
        self.seen_shots: set[str] = set()
        self._restore: list[Callable[[], None]] = []

    def install(self) -> None:
        from instantlensdoc.ui import stubs as stubs_mod

        rec = self
        orig_show = QDialog.show

        def _show(self_dlg, *a, **k):
            info = rec._describe(self_dlg, kind="exec")
            rec.events.append(info)
            rec._grab(self_dlg, info)
            try:
                return orig_show(self_dlg, *a, **k)
            except Exception:
                return None

        QDialog.show = _show  # type: ignore[method-assign]

        orig_exec = QDialog.exec

        def _exec(self_dlg, *a, **k):
            info = rec._describe(self_dlg, kind="exec")
            rec.events.append(info)
            rec._grab(self_dlg, info)
            try:
                QTimer.singleShot(40, self_dlg.reject)
            except Exception:
                pass
            try:
                return orig_exec(self_dlg, *a, **k)
            except Exception:
                return int(QDialog.Rejected)

        QDialog.exec = _exec  # type: ignore[method-assign]

        def _wrap_box(name: str, orig):
            def _fn(*a, **k):
                title = ""
                text = ""
                if len(a) >= 2:
                    title = str(a[1] or "")
                if len(a) >= 3:
                    text = str(a[2] or "")
                rec.events.append(
                    {
                        "kind": "messagebox",
                        "box": name,
                        "cls": "QMessageBox",
                        "title": title,
                        "text": text[:240],
                        "objectName": "",
                    }
                )
                if name == "question":
                    return QMessageBox.No
                return QMessageBox.Ok

            return _fn

        for nm in ("information", "warning", "critical", "question"):
            orig = getattr(QMessageBox, nm)
            setattr(QMessageBox, nm, staticmethod(_wrap_box(nm, orig)))

        orig_planned = stubs_mod.show_planned

        def _planned(parent, key):
            rec.events.append(
                {
                    "kind": "planned",
                    "box": "show_planned",
                    "cls": "show_planned",
                    "title": str(key),
                    "text": str(key),
                    "objectName": "",
                }
            )
            return orig_planned(parent, key)

        stubs_mod.show_planned = _planned

        tmp = Path(tempfile.mkdtemp(prefix="ild-audit-dlg-"))

        def _save(*_a, **_k):
            rec.events.append(
                {
                    "kind": "exec",
                    "cls": "QFileDialog",
                    "title": "Speichern",
                    "text": "",
                    "objectName": "QFileDialog",
                }
            )
            p = tmp / f"out-{len(list(tmp.iterdir()))}.bin"
            return str(p), "All (*)"

        def _open(*_a, **_k):
            rec.events.append(
                {
                    "kind": "exec",
                    "cls": "QFileDialog",
                    "title": "Öffnen",
                    "text": "",
                    "objectName": "QFileDialog",
                }
            )
            return "", ""

        QFileDialog.getSaveFileName = staticmethod(_save)
        QFileDialog.getOpenFileName = staticmethod(_open)
        QFileDialog.getOpenFileNames = staticmethod(lambda *_a, **_k: ([], ""))
        QFileDialog.getExistingDirectory = staticmethod(lambda *_a, **_k: str(tmp))

        def _get_item(*a, **k):
            rec.events.append(
                {
                    "kind": "exec",
                    "cls": "QInputDialog",
                    "title": str(a[1] if len(a) > 1 else k.get("title") or "Eingabe"),
                    "text": "",
                    "objectName": "QInputDialog",
                }
            )
            items = []
            if len(a) >= 4 and isinstance(a[3], (list, tuple)):
                items = list(a[3])
            elif isinstance(k.get("items"), (list, tuple)):
                items = list(k["items"])
            if not items:
                return "", False
            return str(items[0]), True

        def _get_text(*a, **k):
            rec.events.append(
                {
                    "kind": "exec",
                    "cls": "QInputDialog",
                    "title": str(a[1] if len(a) > 1 else "Eingabe"),
                    "text": "",
                    "objectName": "QInputDialog",
                }
            )
            return "audit", True

        QInputDialog.getText = staticmethod(_get_text)

        def _get_int(*a, **k):
            rec.events.append(
                {
                    "kind": "exec",
                    "cls": "QInputDialog",
                    "title": str(a[1] if len(a) > 1 else "Zahl"),
                    "text": "",
                    "objectName": "QInputDialog",
                }
            )
            return 1, True

        QInputDialog.getInt = staticmethod(_get_int)
        QInputDialog.getDouble = staticmethod(lambda *a, **k: (1.0, True))
        QInputDialog.getItem = staticmethod(_get_item)
        QInputDialog.getMultiLineText = staticmethod(lambda *a, **k: ("audit", True))

        from PySide6.QtGui import QColor, QFont

        def _get_color(*a, **k):
            rec.events.append(
                {
                    "kind": "exec",
                    "cls": "QColorDialog",
                    "title": "Farbe",
                    "text": "",
                    "objectName": "QColorDialog",
                }
            )
            return QColor("#cc3300")

        QColorDialog.getColor = staticmethod(_get_color)

        def _get_font(*a, **k):
            rec.events.append(
                {
                    "kind": "exec",
                    "cls": "QFontDialog",
                    "title": "Schrift",
                    "text": "",
                    "objectName": "QFontDialog",
                }
            )
            return QFont("Arial", 12), True

        QFontDialog.getFont = staticmethod(_get_font)

        orig_menu_exec = QMenu.exec

        def _menu_exec(self_m, *a, **k):
            rec.events.append(
                {
                    "kind": "menu",
                    "cls": "QMenu",
                    "title": self_m.title() or self_m.objectName() or "QMenu",
                    "text": "",
                    "objectName": self_m.objectName() or "",
                }
            )
            try:
                self_m.hide()
            except Exception:
                pass
            return None

        QMenu.exec = _menu_exec  # type: ignore[method-assign]

        try:
            from PySide6.QtPrintSupport import QPrintDialog

            def _print_exec(self_d, *a, **k):
                rec.events.append(
                    {
                        "kind": "exec",
                        "cls": "QPrintDialog",
                        "title": "Drucken",
                        "text": "",
                        "objectName": "QPrintDialog",
                    }
                )
                return QPrintDialog.Rejected

            QPrintDialog.exec = _print_exec  # type: ignore[method-assign]
        except Exception:
            pass

        def restore() -> None:
            QDialog.exec = orig_exec  # type: ignore[method-assign]
            QDialog.show = orig_show  # type: ignore[method-assign]
            QMenu.exec = orig_menu_exec  # type: ignore[method-assign]
            stubs_mod.show_planned = orig_planned

        self._restore.append(restore)

    def restore(self) -> None:
        for fn in self._restore:
            try:
                fn()
            except Exception:
                pass
        self._restore.clear()

    def reset(self) -> None:
        self.events = []

    def _describe(self, dlg: QWidget, *, kind: str) -> dict[str, Any]:
        cls = type(dlg).__name__
        title = ""
        try:
            title = dlg.windowTitle() or ""
        except Exception:
            title = ""
        oname = ""
        try:
            oname = dlg.objectName() or ""
        except Exception:
            oname = ""
        return {
            "kind": kind,
            "cls": cls,
            "title": title,
            "text": "",
            "objectName": oname,
        }

    def _grab(self, dlg: QWidget, info: dict[str, Any]) -> None:
        if self.shot_dir is None:
            return
        key = f"{info.get('cls')}-{info.get('title')}-{info.get('objectName')}"
        if key in self.seen_shots:
            return
        self.seen_shots.add(key)
        try:
            self.shot_dir.mkdir(parents=True, exist_ok=True)
            try:
                dlg.show()
                dlg.resize(max(dlg.width(), 420), max(dlg.height(), 200))
                QApplication.processEvents()
            except Exception:
                pass
            pix = dlg.grab()
            safe = "".join(
                c if c.isalnum() or c in "-_." else "_"
                for c in f"{info.get('cls')}_{info.get('title') or 'dialog'}"
            )[:80]
            out = self.shot_dir / f"{safe}.png"
            pix.save(str(out))
            info["screenshot"] = str(out)
        except Exception as e:
            info["screenshot_error"] = str(e)


def classify_events(
    events: list[dict[str, Any]], changes: list[str]
) -> tuple[str, str]:
    planned = [e for e in events if e.get("kind") == "planned" or e.get("cls") == "show_planned"]
    stubs = [
        e
        for e in events
        if (
            e.get("cls") in FAIL_DIALOG_CLASSES
            or e.get("objectName") in FAIL_OBJECT_NAMES
        )
        and e.get("box") != "question"
    ]
    info_boxes = [
        e
        for e in events
        if e.get("kind") == "messagebox" and e.get("box") in ("information", "warning", "critical")
    ]
    questions = [
        e for e in events if e.get("kind") == "messagebox" and e.get("box") == "question"
    ]
    real = [
        e
        for e in events
        if e.get("kind") == "exec"
        and e.get("cls") not in FAIL_DIALOG_CLASSES
        and e.get("objectName") not in FAIL_OBJECT_NAMES
        and e.get("cls") != "QMessageBox"
    ]
    if planned:
        return "fail", "show_planned"
    if real:
        return "open", real[0].get("cls") or "dialog"
    if questions:
        return "open", "QMessageBox.question"
    if stubs and not changes:
        return "fail", "stub-dialog"
    if info_boxes and not changes:
        return "fail", "info-box"
    if changes:
        return "effect", ",".join(changes[:6])
    return "fail", "no-op"


def should_skip(row: dict, state: str) -> bool:
    text = (row.get("text") or "").replace("&", "").strip().lower()
    path = (row.get("path") or "").lower()
    if text in SKIP_TRIGGER_TEXTS:
        return True
    if path.endswith("beenden") or path.endswith(" ▸ beenden"):
        return True
    if row.get("kind") in ("shortcut", "ribbon-tab", "palette"):
        return True
    if not row.get("enabled", True):
        return True
    if row.get("kind") == "pdf-toolbar" and state != "pdf":
        return True
    if row.get("kind") == "pdf-toolbar":
        w = row.get("widget")
        if w is not None:
            try:
                if not w.isVisible():
                    return True
            except Exception:
                pass
            try:
                if w.isCheckable() and w.isChecked():
                    return True
            except Exception:
                pass
    if row.get("kind") == "editor-toolbar" and state == "pdf":
        return True
    return False


def trigger_row_effect(app, win, row: dict) -> None:
    kind = row.get("kind")
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
        row["widget"].click()
        return
    if kind == "context" and row.get("action") is not None:
        row["action"].trigger()
        return
    if row.get("action") is not None:
        row["action"].trigger()


def inventory_context(win) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ed = getattr(win, "editor", None)
    if ed is not None:
        try:
            menu = ed.createStandardContextMenu()
            for act in menu.actions():
                if act.isSeparator():
                    continue
                text = (act.text() or "").replace("&", "").strip()
                if not text:
                    continue
                rows.append(
                    {
                        "kind": "context",
                        "path": f"Kontext Editor ▸ {text}",
                        "text": text,
                        "enabled": bool(act.isEnabled()),
                        "action": act,
                        "receivers": 1,
                        "area": "editor",
                    }
                )
            for label in (
                "Fett",
                "Kursiv",
                "Unterstrichen",
                "Durchgestrichen",
                "Formatierungen löschen",
                "Suchen und Ersetzen…",
            ):
                rows.append(
                    {
                        "kind": "context",
                        "path": f"Kontext Editor ▸ {label}",
                        "text": label,
                        "enabled": True,
                        "action": None,
                        "context_slot": label,
                        "receivers": 1,
                        "area": "editor",
                    }
                )
        except Exception:
            pass
    bar = getattr(win, "doc_tab_bar", None) or getattr(win, "tab_bar", None)
    if bar is not None:
        rows.append(
            {
                "kind": "context",
                "path": "Kontext Tabs ▸ In separatem Fenster öffnen",
                "text": "In separatem Fenster öffnen",
                "enabled": True,
                "action": None,
                "context_slot": "tab-detach",
                "receivers": 1,
                "area": "tabs",
            }
        )
    return rows


def walk_state(
    app, win, state: str, rec: DialogRecorder, fixtures: dict[str, Path]
) -> list[dict[str, Any]]:
    try:
        win._sync_menu_enablement()
    except Exception:
        pass
    inv = inventory_window(win)
    inv.extend(inventory_context(win))
    out: list[dict[str, Any]] = []
    seen_act: set[int] = set()
    for row in inv:
        kind = row.get("kind")
        if kind not in {"menu", "ribbon", "editor-toolbar", "pdf-toolbar", "context"}:
            continue
        path = row.get("path") or row.get("text") or ""
        enabled = bool(row.get("enabled", True))
        act = row.get("action")
        if act is not None:
            aid = id(act)
            if aid in seen_act:
                out.append(
                    {
                        "path": path,
                        "kind": kind,
                        "text": row.get("text") or "",
                        "verdict": "alias",
                        "detail": "same-QAction",
                    }
                )
                continue
            seen_act.add(aid)
        if should_skip(row, state):
            verdict = "skip" if enabled else "disabled"
            if not enabled:
                verdict = "disabled"
            out.append(
                {
                    "path": path,
                    "kind": kind,
                    "text": row.get("text") or "",
                    "verdict": verdict,
                    "detail": "skip" if verdict == "skip" else "disabled",
                }
            )
            continue
        rec.reset()
        before = snapshot_state(win)
        exc = None
        try:
            slot = row.get("context_slot")
            if slot:
                mapping = {
                    "Fett": win._toggle_bold,
                    "Kursiv": win._toggle_italic,
                    "Unterstrichen": win._toggle_underline,
                    "Durchgestrichen": win._toggle_strike,
                    "Formatierungen löschen": win._clear_formatting,
                    "Suchen und Ersetzen…": win._find_replace,
                    "tab-detach": win._detach_current_document,
                }
                fn = mapping.get(slot)
                if fn:
                    fn()
            else:
                trigger_row_effect(app, win, row)
        except Exception:
            exc = traceback.format_exc()
        pump(app, 0.12)
        after = snapshot_state(win)
        changes = state_changed(before, after)
        events = list(rec.events)
        if exc:
            verdict, detail = "fail", f"exc:{exc.splitlines()[-1][:120]}"
        else:
            verdict, detail = classify_events(events, changes)
        shot = next((e.get("screenshot") for e in events if e.get("screenshot")), "")
        out.append(
            {
                "path": path,
                "kind": kind,
                "text": row.get("text") or "",
                "verdict": verdict,
                "detail": detail,
                "changes": changes,
                "dialogs": [
                    {
                        "cls": e.get("cls"),
                        "title": e.get("title"),
                        "box": e.get("box"),
                    }
                    for e in events
                    if e.get("kind") in ("exec", "messagebox", "planned")
                ],
                "screenshot": shot,
            }
        )
        try:
            if after.get("stack") != before.get("stack"):
                load_effect_state(win, app, state, fixtures)
            else:
                from menu_smoke_lib import current_state_tag

                tag = current_state_tag(win, fixtures)
                expect = "pdf20" if state == "pdf" else state
                if state == "ocr":
                    dp = str(getattr(getattr(win, "doc", None), "path", "") or "")
                    if "audit-ocr" not in dp:
                        load_effect_state(win, app, state, fixtures)
                elif tag != expect and not (state == "docx" and tag == "docx"):
                    load_effect_state(win, app, state, fixtures)
        except Exception:
            pass
    return out
