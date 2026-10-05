#!/usr/bin/env python3
"""Offscreen-Tests 2.6.54 — Tab schließen, per-Tab-Nav, Recents, Thumb→Next, Mausrad.

Felder:
1. Tab-X auf 500-Seiten-PDF hängt / Tab-Eintrag bleibt stehen.
2. Nach Open von B klebt Nav von A (7/536).
3. Nach Thumb-Klick funktionieren ◀/▶ / Bild-ab nicht.
4. Mausrad blättert nicht.
5. Recent-Liste lässt sich nicht leeren (alle drei Views).

Aufruf:
  QT_QPA_PLATFORM=offscreen python3 scripts/test_ui_audit_2654_tab_close.py
  QT_QPA_PLATFORM=offscreen python3 -m pytest -q scripts/test_ui_audit_2654_tab_close.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["ILD_SMOKE_QT"] = "1"
os.environ.setdefault("ILD_SKIP_DEPS_CHECK", "1")
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="ild-audit-2654-tab-cfg-")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from test_pdf_canvas_not_blank import _make_multipage_pdf  # noqa: E402
from test_ui_audit_2652 import _pump  # noqa: E402

CLOSE_BUDGET_MS = 400.0
N_BIG = 500


def _send_wheel(widget, angle_y: int, *, ctrl: bool = False) -> None:
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtWidgets import QApplication

    w = max(8, int(widget.width() or 64))
    h = max(8, int(widget.height() or 64))
    local = QPointF(w / 2.0, h / 2.0)
    try:
        glob = QPointF(widget.mapToGlobal(local.toPoint()))
    except Exception:
        glob = local
    mods = Qt.ControlModifier if ctrl else Qt.NoModifier
    ev = QWheelEvent(
        local,
        glob,
        QPoint(0, 0),
        QPoint(0, int(angle_y)),
        Qt.NoButton,
        mods,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(widget, ev)


def _recent_paths(widget) -> list[str]:
    out: list[str] = []
    for i in range(widget.count()):
        it = widget.item(i)
        if it is None:
            continue
        raw = it.data(256) if hasattr(it, "data") else None
        if raw is None:
            from PySide6.QtCore import Qt as _Qt

            raw = it.data(_Qt.UserRole)
        if raw:
            out.append(str(raw))
    return out


def _wait_pages(app, pv, n: int, seconds: float = 5.0) -> None:
    _pump(app, seconds, until=lambda: int(pv.page_count or 0) >= int(n))


def _make_window():
    from PySide6.QtWidgets import QApplication

    from instantlensdoc.license import LicenseManager
    from instantlensdoc.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    lm = LicenseManager()
    lm.ensure_trial_started()
    win = MainWindow(lm)
    win.resize(1400, 900)
    win.show()
    _pump(app, 0.2)
    return app, win


def test_close_500_page_tab_under_budget_and_tab_gone():
    from instantlensdoc.core import recent as recent_mod

    app, win = _make_window()
    pv = win.pdf_view
    late: list[str] = []

    def _on_status(msg: str) -> None:
        late.append(str(msg))

    pv.status.connect(_on_status)
    with tempfile.TemporaryDirectory() as td:
        big = Path(td) / "big500.pdf"
        _make_multipage_pdf(big, [f"S{i + 1}" for i in range(N_BIG)])
        win.open_path(str(big))
        _wait_pages(app, pv, N_BIG)
        assert int(pv.page_count) >= N_BIG
        assert win.doc_tab_bar.tabs.count() == 1
        t0 = time.perf_counter()
        win.close_tab_path(str(big))
        dt_ms = (time.perf_counter() - t0) * 1000.0
        assert dt_ms <= CLOSE_BUDGET_MS, f"Tab-Close {dt_ms:.1f} ms > {CLOSE_BUDGET_MS} ms"
        _pump(app, 0.4)
        assert win.doc_tab_bar.tabs.count() == 0, (
            f"Tab-Leiste nach Close nicht leer: {win.doc_tab_bar.tabs.count()}"
        )
        assert not win.sidebar.document_paths()
        assert win.stack.currentWidget() is win.welcome_page
        assert pv.pdf_path is None
        assert int(pv.page_count or 0) == 0
        assert pv.lbl_page.text() in {"—", "-"}
        # Späte Worker dürfen nicht explodieren
        _pump(app, 0.6)
        assert win.doc is None or not win.doc.path
        recent_mod.clear_recent()
        win._stop_thumb_lazy()
        win.close()
    print(f"OK  close 500-page tab {dt_ms:.1f} ms, tabs=0, welcome")


def test_open_two_close_one_remaining_current():
    app, win = _make_window()
    pv = win.pdf_view
    with tempfile.TemporaryDirectory() as td:
        a = Path(td) / "a.pdf"
        b = Path(td) / "b.pdf"
        _make_multipage_pdf(a, ["A1", "A2", "A3"])
        _make_multipage_pdf(b, ["B1", "B2"])
        win.open_path(str(a))
        _wait_pages(app, pv, 3)
        win.open_path(str(b))
        _wait_pages(app, pv, 2)
        assert win.doc_tab_bar.tabs.count() == 2
        win.close_tab_path(str(b))
        _pump(app, 1.5, until=lambda: win.doc is not None and win.doc.path and Path(win.doc.path).name == "a.pdf")
        assert win.doc_tab_bar.tabs.count() == 1
        remaining = [Path(p).name for p in win.sidebar.document_paths()]
        assert remaining == ["a.pdf"]
        assert Path(win.doc.path).name == "a.pdf"
        assert win.doc_tab_bar.tabs.currentIndex() == 0
        win._stop_thumb_lazy()
        win.close()
    print("OK  open 2 close 1 → tab count 1, remaining current")


def test_per_tab_page_count_and_close_a_keeps_b():
    app, win = _make_window()
    pv = win.pdf_view
    with tempfile.TemporaryDirectory() as td:
        a = Path(td) / "A500.pdf"
        b = Path(td) / "B3.pdf"
        _make_multipage_pdf(a, [f"A{i + 1}" for i in range(N_BIG)])
        _make_multipage_pdf(b, ["B1", "B2", "B3"])
        win.open_path(str(a))
        _wait_pages(app, pv, N_BIG)
        assert int(pv.page_count) == N_BIG
        win.open_path(str(b))
        _wait_pages(app, pv, 3)
        _pump(app, 0.4)
        assert int(pv.page_count) == 3, f"B klebt A: page_count={pv.page_count}"
        assert pv.current_page == 0
        assert pv.spin_page.value() == 1
        assert pv.spin_page.maximum() == 3
        assert "/ 3" in pv.lbl_page.text() or pv.lbl_page.text().endswith("3")
        status = win.page_status_label.text()
        assert "3" in status and "500" not in status, status
        win.open_path(str(a))
        _wait_pages(app, pv, N_BIG)
        _pump(app, 0.3)
        assert int(pv.page_count) == N_BIG
        assert pv.spin_page.maximum() == N_BIG
        win.close_tab_path(str(a))
        _pump(app, 2.0, until=lambda: int(pv.page_count or 0) == 3)
        assert int(pv.page_count) == 3
        assert Path(win.doc.path).name == "B3.pdf"
        assert pv.spin_page.maximum() == 3
        assert win.doc_tab_bar.tabs.count() == 1
        win._stop_thumb_lazy()
        win.close()
    print("OK  per-tab nav A=500 B=3, close A keeps B")


def test_thumb_click_then_next_and_spin_sync():
    app, win = _make_window()
    pv = win.pdf_view
    with tempfile.TemporaryDirectory() as td:
        pdf = Path(td) / "nav20.pdf"
        _make_multipage_pdf(pdf, [f"P{i + 1}" for i in range(20)])
        win.open_path(str(pdf))
        _wait_pages(app, pv, 20)
        _pump(app, 1.0, until=lambda: win.sidebar.thumbs.count() >= 20)
        assert win.sidebar.thumbs.count() == 20
        win._on_thumb_jump(9)  # Seite 10
        _pump(app, 0.4)
        assert int(pv.current_page) == 9, pv.current_page
        assert pv.spin_page.value() == 10
        assert win.sidebar.thumbs.currentRow() == 9
        pv.next_page()
        _pump(app, 0.3)
        assert int(pv.current_page) == 10, f"Next nach Thumb blieb {pv.current_page}"
        assert pv.spin_page.value() == 11
        assert win.sidebar.thumbs.currentRow() == 10
        pv.spin_page.setValue(5)
        _pump(app, 0.3)
        assert int(pv.current_page) == 4
        assert win.sidebar.thumbs.currentRow() == 4
        pv.btn_page_prev.click()
        _pump(app, 0.2)
        assert int(pv.current_page) == 3
        win._stop_thumb_lazy()
        win.close()
    print("OK  thumb 10 → next 11, spin/thumbs in sync")


def test_wheel_flips_page_from_1_to_2():
    app, win = _make_window()
    pv = win.pdf_view
    with tempfile.TemporaryDirectory() as td:
        pdf = Path(td) / "wheel.pdf"
        _make_multipage_pdf(pdf, ["W1", "W2", "W3", "W4"])
        win.open_path(str(pdf))
        _wait_pages(app, pv, 4)
        pv.set_current_page(0)
        pv.fit_page()
        _pump(app, 0.3)
        assert pv.current_page == 0
        # Ohne Overflow: Rad = nächste Seite
        _send_wheel(pv.canvas, -120)
        _pump(app, 0.3)
        assert int(pv.current_page) == 1, f"Rad von Seite 1 blieb {pv.current_page}"
        assert win.sidebar.thumbs.currentRow() == 1
        # Overflow: am unteren Rand weiterblättern
        pv.set_scale(2.5, immediate=True)
        _pump(app, 0.3)
        bar = pv.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())
        _pump(app, 0.1)
        _send_wheel(pv.canvas, -120)
        _pump(app, 0.3)
        assert int(pv.current_page) == 2, f"Rad am unteren Rand blieb {pv.current_page}"
        win._stop_thumb_lazy()
        win.close()
    print("OK  wheel page 1→2, edge flip, thumbs follow")


def test_recent_clear_all_three_views():
    from instantlensdoc.core import recent as recent_mod

    app, win = _make_window()
    with tempfile.TemporaryDirectory() as td:
        files = []
        for i in range(3):
            p = Path(td) / f"r{i}.txt"
            p.write_text(f"r{i}", encoding="utf-8")
            files.append(p)
            recent_mod.add_recent(p)
        gone = Path(td) / "missing.txt"
        recent_mod.add_recent(gone)
        win._refresh_recent()
        _pump(app, 0.2)
        stored = recent_mod.load_recent()
        assert str(gone) not in stored, "fehlende Datei blieb in recent.json"
        assert len(_recent_paths(win.sidebar.recent)) == 3
        labels = [a.text() for a in win._recent_menu.actions() if a.text() and a.text() != "Liste leeren"]
        assert any("r0.txt" in t or "r1.txt" in t for t in labels)
        wp = win.welcome_page
        wp.refresh_recent()
        assert len(_recent_paths(wp.recent_list)) == 3
        win._clear_recent(confirm=False)
        _pump(app, 0.2)
        assert recent_mod.load_recent() == []
        assert recent_mod.load_recent_entries() == []
        assert _recent_paths(win.sidebar.recent) == []
        assert _recent_paths(wp.recent_list) == []
        menu_txt = [a.text() for a in win._recent_menu.actions() if a.isEnabled() and a.text()]
        assert "Liste leeren" in [a.text() for a in win._recent_menu.actions()]
        assert not any(t.endswith(".txt") for t in menu_txt)
        win.close()
    print("OK  recent clear: json + welcome + dock + Datei-Menü leer")


def test_close_all_and_app_exit_budget():
    app, win = _make_window()
    pv = win.pdf_view
    with tempfile.TemporaryDirectory() as td:
        big = Path(td) / "exit500.pdf"
        _make_multipage_pdf(big, [f"E{i + 1}" for i in range(N_BIG)])
        small = Path(td) / "exit3.pdf"
        _make_multipage_pdf(small, ["x", "y", "z"])
        win.open_path(str(small))
        _wait_pages(app, pv, 3)
        win.open_path(str(big))
        _wait_pages(app, pv, N_BIG)
        t0 = time.perf_counter()
        win.close_all_tabs()
        dt = (time.perf_counter() - t0) * 1000.0
        assert dt <= CLOSE_BUDGET_MS, f"Alle schließen {dt:.1f} ms"
        _pump(app, 0.5)
        assert win.doc_tab_bar.tabs.count() == 0
        win.open_path(str(big))
        _wait_pages(app, pv, N_BIG)
        t0 = time.perf_counter()
        win.close()
        dt2 = (time.perf_counter() - t0) * 1000.0
        assert dt2 <= CLOSE_BUDGET_MS, f"App-Exit {dt2:.1f} ms"
        print(f"OK  close-all {dt:.1f} ms, exit {dt2:.1f} ms")
        return


def _find_menu_action(win, title: str):
    for top in win.menuBar().actions():
        menu = top.menu()
        if menu is None:
            if top.text() == title:
                return top
            continue
        for act in menu.actions():
            if act.text() == title:
                return act
            sub = act.menu()
            if sub is None:
                continue
            for child in sub.actions():
                if child.text() == title:
                    return child
    return None


def test_pdf_line_spacing_keeps_pdf_tab():
    """PDF-Tab: Zeilenabstand 1,5 darf Editor/Geschwister-DOCX nicht anheben — 2.6.54."""
    from instantlensdoc.core import recent as recent_mod
    from instantlensdoc.core.documents import DocKind

    app, win = _make_window()
    pv = win.pdf_view
    with tempfile.TemporaryDirectory() as td:
        pdf = Path(td) / "report.pdf"
        sibling = Path(td) / "report.docx"
        _make_multipage_pdf(pdf, ["P1", "P2", "P3"])
        sibling.write_text("Geschwister-DOCX", encoding="utf-8")
        recent_mod.add_recent(sibling)
        win._refresh_recent()
        win.open_path(str(pdf))
        _wait_pages(app, pv, 3)
        tabs_before = win.doc_tab_bar.tabs.count()
        assert tabs_before >= 1
        assert win.stack.currentWidget() is pv
        assert win.doc is not None and win.doc.kind == DocKind.PDF
        assert Path(win.doc.path).name == "report.pdf"

        win._set_paragraph_line_spacing(1.5)
        _pump(app, 0.2)
        act = _find_menu_action(win, "Zeilenabstand 1,5")
        assert act is not None
        act.trigger()
        _pump(app, 0.2)
        win._toggle_bold()
        win._indent_selection()
        win._show_page_layout_dialog()
        win._on_editor_toolbar_action("bold")
        win._check_spelling()
        _pump(app, 0.2)

        assert win.stack.currentWidget() is pv, "Stack verließ PDF-Ansicht"
        assert win.stack.currentWidget() is not win.editor_pane
        assert win.doc_tab_bar.tabs.count() == tabs_before
        assert win.doc is not None and win.doc.kind == DocKind.PDF
        assert Path(win.doc.path).name == "report.pdf"
        names = [Path(p).name for p in win.sidebar.document_paths()]
        assert "report.docx" not in names
        assert int(pv.page_count) >= 3
        win._stop_thumb_lazy()
        win.close()
    print("OK  PDF line-spacing 1.5 keeps PDF tab, no sibling/editor raise")


def main() -> int:
    test_close_500_page_tab_under_budget_and_tab_gone()
    test_open_two_close_one_remaining_current()
    test_per_tab_page_count_and_close_a_keeps_b()
    test_thumb_click_then_next_and_spin_sync()
    test_wheel_flips_page_from_1_to_2()
    test_recent_clear_all_three_views()
    test_close_all_and_app_exit_budget()
    test_pdf_line_spacing_keeps_pdf_tab()
    print("OK test_ui_audit_2654_tab_close")
    return 0


if __name__ == "__main__":
    import faulthandler

    faulthandler.dump_traceback_later(240, exit=True)
    raise SystemExit(main())
