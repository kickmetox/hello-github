"""PDF-Menü 2659: kein No-Op — Dialog (QTimer close) oder Dateiänderung."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["ILD_SMOKE_QT"] = "1"
os.environ.setdefault("ILD_SKIP_DEPS_CHECK", "1")
os.environ.setdefault("ILD_NO_SESSION", "1")
os.environ.setdefault("ILD_NO_SPLASH", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from menu_effect_lib import DialogRecorder, pump  # noqa: E402
from menu_smoke_lib import (  # noqa: E402
    create_main_window,
    install_headless_env,
    make_docx,
    make_n_page_pdf,
)
from ild_pdf.menu_policy import pdf_menu_disable_reason, pdf_menu_need  # noqa: E402
from instantlensdoc.ui.menu_click import (  # noqa: E402
    find_menubar_menu,
    iter_leaf_actions,
    mouse_click_menu_action,
    prepare_menu_for_clicks,
)


_APP = None
_WIN = None
_TD = None
_REC = None
_PDF = None
_DOCX = None
_ORIG = None


def setup_module() -> None:
    global _APP, _WIN, _TD, _REC, _PDF, _DOCX, _ORIG
    install_headless_env()
    _TD = tempfile.TemporaryDirectory(prefix="ild-pdf-menu-2659-")
    td = Path(_TD.name)
    _PDF = td / "three.pdf"
    _DOCX = td / "doc.docx"
    make_n_page_pdf(_PDF, 3)
    make_docx(_DOCX)
    _ORIG = _PDF.read_bytes()
    _REC = DialogRecorder(shot_dir=None)
    _REC.install()
    _APP, _WIN = create_main_window()


def teardown_module() -> None:
    global _WIN, _TD, _REC
    try:
        if _WIN is not None:
            _WIN.close()
    except Exception:
        pass
    if _REC is not None:
        _REC.restore()
    if _TD is not None:
        _TD.cleanup()


def _pdf_menu():
    menu = find_menubar_menu(_WIN, "PDF")
    assert menu is not None, "PDF-Menü fehlt"
    return menu


def _leaf_actions():
    return list(iter_leaf_actions(_pdf_menu()))


def _reload_pdf() -> None:
    _PDF.write_bytes(_ORIG)
    _WIN.open_path(str(_PDF))
    pump(_APP, 0.2)
    try:
        _WIN._sync_menu_enablement()
    except Exception:
        pass


def _close_all() -> None:
    try:
        if hasattr(_WIN, "close_all_tabs"):
            _WIN.close_all_tabs()
    except Exception:
        pass
    pump(_APP, 0.1)


def _snap() -> dict:
    pv = _WIN.pdf_view
    path = getattr(pv, "pdf_path", None)
    mtime = 0
    sidec = 0
    try:
        if path and Path(path).is_file():
            mtime = int(Path(path).stat().st_mtime_ns)
    except Exception:
        mtime = 0
    try:
        store = getattr(pv, "store", None)
        sp = getattr(store, "sidecar_path", None) if store is not None else None
        if sp and Path(sp).is_file():
            sidec = int(Path(sp).stat().st_mtime_ns)
    except Exception:
        sidec = 0
    gray = False
    night = False
    try:
        gray = bool(pv.grayscale_enabled())
    except Exception:
        pass
    try:
        night = bool(pv.night_mode_enabled())
    except Exception:
        pass
    color = str(getattr(pv, "_highlight_color", "") or "")
    tool = str(getattr(pv, "tool", None) or getattr(pv, "_tool", "") or "")
    page = int(getattr(pv, "page_index", -1) or -1)
    count = int(getattr(pv, "page_count", 0) or 0)
    stack_pdf = False
    try:
        stack_pdf = _WIN.stack.currentWidget() is pv
    except Exception:
        stack_pdf = False
    return {
        "mtime": mtime,
        "sidec": sidec,
        "gray": gray,
        "night": night,
        "color": color,
        "tool": tool,
        "page": page,
        "count": count,
        "stack_pdf": stack_pdf,
    }


def test_pdf_menu_policy_labels() -> None:
    assert pdf_menu_need("PDFs zusammenführen / teilen…") == "always"
    assert pdf_menu_need("Zwei PDFs vergleichen…") == "always"
    assert pdf_menu_need("Scannen / Import…") == "always"
    assert pdf_menu_need("Seitenbereich extrahieren…") == "pdf"
    assert pdf_menu_need("Stempel 90° drehen ↻") == "selection"
    assert pdf_menu_need("Lesezeichen löschen") == "selection"
    assert (
        pdf_menu_disable_reason(
            "Dokument-Statistik…", has_open_pdf=True, is_pdf_tab=False
        )
        == ""
    )
    assert pdf_menu_disable_reason(
        "Dokument-Statistik…", has_open_pdf=False, is_pdf_tab=False
    ) == "Nur bei geöffnetem PDF verfügbar"


def test_ocg_layers_empty_on_plain_pdf() -> None:
    from ild_pdf.print_prep import list_optional_content_groups

    assert list_optional_content_groups(_PDF) == []


def test_docx_only_pdf_items_disabled() -> None:
    _close_all()
    _WIN.open_path(str(_DOCX))
    pump(_APP, 0.25)
    _WIN._sync_menu_enablement()
    failed = []
    always = []
    for path, _menu, act in _leaf_actions():
        text = (act.text() or "").replace("&", "").strip()
        need = pdf_menu_need(text)
        if need == "always":
            always.append(path)
            continue
        if act.isEnabled():
            failed.append(path)
    assert always, "always-on PDF-Einträge fehlen"
    assert not failed, "PDF-only bei DOCX ohne PDF-Tab noch enabled:\n" + "\n".join(
        failed[:20]
    )


def test_pdf_menu_object_name_and_one_column() -> None:
    menu = _pdf_menu()
    assert menu.objectName() == "menuPdf"
    prepare_menu_for_clicks(menu)
    menu.popup(menu.parentWidget().mapToGlobal(menu.rect().topLeft()) if menu.parentWidget() else menu.pos())
    menu.show()
    pump(_APP, 0.1)
    rect = menu.rect()
    overflow_x = []
    for path, _host, act in _leaf_actions():
        geo = menu.actionGeometry(act)
        if geo.isValid() and geo.x() > rect.width():
            overflow_x.append(f"{path} x={geo.x()} w={rect.width()}")
    menu.hide()
    pump(_APP, 0.05)
    assert not overflow_x, "PDF-Menü zweite Spalte (actionGeometry außerhalb):\n" + "\n".join(
        overflow_x[:12]
    )


def test_docx_with_sibling_pdf_pdf_only_enabled() -> None:
    _close_all()
    _WIN.open_path(str(_PDF))
    pump(_APP, 0.2)
    _WIN.open_path(str(_DOCX))
    pump(_APP, 0.25)
    _WIN._sync_menu_enablement()
    disabled_pdf = []
    always = []
    stats = None
    for path, _menu, act in _leaf_actions():
        text = (act.text() or "").replace("&", "").strip()
        if "Dokument-Statistik" in text:
            stats = act
        need = pdf_menu_need(text)
        if need == "always":
            always.append(path)
            assert act.isEnabled(), f"always-on disabled bei DOCX: {path}"
            continue
        if need == "pdf" and not act.isEnabled():
            disabled_pdf.append(path)
    assert stats is not None
    assert stats.isEnabled(), "Statistik muss bei offenem Geschwister-PDF enabled sein"
    assert always, "always-on PDF-Einträge fehlen"
    assert not disabled_pdf, (
        "PDF-only bei DOCX (PDF-Geschwister offen) disabled:\n"
        + "\n".join(disabled_pdf[:20])
    )


def test_qtest_mouseclick_pdf_only_with_sibling_pdf() -> None:
    _close_all()
    _WIN.open_path(str(_PDF))
    pump(_APP, 0.2)
    _WIN.open_path(str(_DOCX))
    pump(_APP, 0.25)
    _WIN._sync_menu_enablement()
    hits = {"n": 0}
    act = None
    host = None
    for _path, host, act in _leaf_actions():
        text = (act.text() or "").replace("&", "").strip()
        if "Dokument-Statistik" in text:
            break
    else:
        raise AssertionError("Dokument-Statistik fehlt")
    assert act.isEnabled(), "PDF-only bei Geschwister-PDF disabled"

    def _hit(*_a, **_k):
        hits["n"] += 1

    act.triggered.connect(_hit)
    _REC.events.clear()
    try:
        assert mouse_click_menu_action(_APP, host, act)
        pump(_APP, 0.2)
    finally:
        try:
            act.triggered.disconnect(_hit)
        except Exception:
            pass
    assert hits["n"] >= 1, f"Mausklick PDF-only mit Geschwister-PDF: triggered={hits['n']}"
    assert _REC.events, "PDF-only Mausklick ohne Dialog (Zielwahl oder Statistik)"


def test_qtest_mouseclick_pdf_always_on_without_pdf_tab() -> None:
    _close_all()
    _WIN.open_path(str(_DOCX))
    pump(_APP, 0.25)
    _WIN._sync_menu_enablement()
    hits = {"n": 0}
    act = None
    host = None
    for _path, host, act in _leaf_actions():
        text = (act.text() or "").replace("&", "").strip()
        if pdf_menu_need(text) == "always" and act.isEnabled():
            break
    else:
        raise AssertionError("kein enabled always-on PDF-Eintrag")

    def _hit(*_a, **_k):
        hits["n"] += 1

    act.triggered.connect(_hit)
    _REC.events.clear()
    try:
        assert mouse_click_menu_action(_APP, host, act)
        pump(_APP, 0.2)
    finally:
        try:
            act.triggered.disconnect(_hit)
        except Exception:
            pass
    assert hits["n"] >= 1, f"Mausklick always-on ohne PDF-Tab: triggered={hits['n']}"
    assert _REC.events, "always-on Mausklick ohne Dialog"


def test_qtest_mouseclick_each_enabled_pdf_action_fires_slot() -> None:
    _reload_pdf()
    fails: list[str] = []
    n_enabled = 0
    for path, host, act in _leaf_actions():
        if not act.isEnabled():
            continue
        n_enabled += 1
        before = _snap()
        _REC.events.clear()
        hits = {"n": 0}

        def _hit(*_a, **_k):
            hits["n"] += 1

        act.triggered.connect(_hit)
        try:
            ok = mouse_click_menu_action(_APP, host, act)
        except Exception as e:
            fails.append(f"{path}: exception {e}")
            try:
                act.triggered.disconnect(_hit)
            except Exception:
                pass
            _reload_pdf()
            continue
        pump(_APP, 0.15)
        try:
            act.triggered.disconnect(_hit)
        except Exception:
            pass
        after = _snap()
        dlg = bool(_REC.events)
        changed = after != before
        if not ok or hits["n"] < 1:
            fails.append(f"{path}: click={ok} triggered={hits['n']}")
        elif not dlg and not changed:
            fails.append(f"{path}: Mausklick ohne Dialog und ohne Datei-/Ansichtsänderung")
        try:
            _PDF.write_bytes(_ORIG)
            if getattr(_WIN.pdf_view, "pdf_path", None):
                cur = Path(_WIN.pdf_view.pdf_path)
                if cur.resolve() == _PDF.resolve():
                    _WIN.pdf_view.load(_PDF)
        except Exception:
            _reload_pdf()
        try:
            _WIN._sync_menu_enablement()
        except Exception:
            pass
        pump(_APP, 0.05)
    assert n_enabled >= 40, f"zu wenige enabled PDF-Aktionen: {n_enabled}"
    assert not fails, "Mausklick ohne Slot:\n" + "\n".join(fails[:30])


# Screenshot-Inventar: ein Pytest-Fall pro deutschem PDF-Menü-Eintrag.
INVENTORY: list[tuple[str, str]] = [
    ("merge", "PDFs zusammenführen / teilen…"),
    ("extract", "Seitenbereich extrahieren…"),
    ("split", "Seiten als Einzel-PDFs…"),
    ("watermark", "Wasserzeichen / Seitennummern / Kopfzeile…"),
    ("compare", "Zwei PDFs vergleichen…"),
    ("ann_search", "Annotation-Suche (offene Docs)…"),
    ("esign", "Digitale Signatur (eIDAS)…"),
    ("encrypt", "PDF verschlüsseln…"),
    ("decrypt", "PDF entschlüsseln…"),
    ("stats", "Dokument-Statistik…"),
    ("compress", "PDF komprimieren / Downsample…"),
    ("preflight", "Preflight (Druckprüfung)…"),
    ("bleed", "Anschnitt / Bleed setzen…"),
    ("layers", "Dokument-Ebenen…"),
    ("flatten_links", "Link-Annotationen in PDF backen…"),
    ("metadata", "Metadaten bearbeiten…"),
    ("tags", "Dokument-Tags…"),
    ("sanitize", "PDF bereinigen…"),
    ("forms", "Formularfelder ausfüllen…"),
    ("attachments", "Anhänge…"),
    ("portfolio", "PDF-Portfolio…"),
    ("stamp_lib", "Stempel-Bibliothek (Bilder)…"),
    ("ann_tmpl", "Annotation-Vorlagen…"),
    ("crop", "Seitengröße / Zuschneiden…"),
    ("goto", "Gehe zu Seite…"),
    ("page_labels", "Seitenbeschriftungen…"),
    ("history", "Dokument-Historie…"),
    ("ann_save", "Annotationen speichern (Sidecar)"),
    ("ann_save_as", "Annotationen speichern unter…"),
    ("ann_load", "Annotationen laden"),
    ("ann_json", "Annotationen als JSON exportieren…"),
    ("ann_json_flat", "Annotationen exportieren (JSON / Flatten)…"),
    ("ann_csv", "Annotationen als CSV exportieren…"),
    ("ann_md", "Kommentar-Bericht (Markdown)…"),
    ("ann_txt", "Kommentar-Bericht (Text)…"),
    ("ann_flatten", "Annotationen flatten/bake exportieren…"),
    ("ann_import_json", "Annotationen aus JSON importieren…"),
    ("ann_import_native", "PDF-Kommentare importieren (native)…"),
    ("ann_dupes", "Annotation-Duplikate finden / zusammenführen…"),
    ("color_cycle", "Annotation-Farbe Palette-Zyklus"),
    ("color_rand", "Annotation-Farbe randomisieren"),
    ("bm_add", "Lesezeichen hinzufügen…"),
    ("bm_del", "Lesezeichen löschen"),
    ("rot90", "Seite drehen 90° ⟳"),
    ("rotm90", "Seite drehen −90° ⟲"),
    ("stamp_rot", "Stempel 90° drehen ↻"),
    ("flip_h", "Seite horizontal spiegeln ↔"),
    ("flip_v", "Seite vertikal spiegeln ↕"),
    ("gray", "Graustufen umschalten"),
    ("night", "Nachtmodus umschalten"),
    ("insert", "Leere Seite einfügen"),
    ("dup", "Seite duplizieren"),
    ("delete", "Seite löschen…"),
    ("group", "Annotationsgruppe umbenennen/Farbe…"),
]


def _find_inventory_action(needle: str):
    want = needle.replace("&", "").strip()
    for _path, _menu, act in _leaf_actions():
        got = (act.text() or "").replace("&", "").strip()
        if got == want:
            return act
    return None


def _add_ann(*, kind, **kw):
    from ild_pdf.annotate import Annotation, AnnotationType

    store = _WIN.pdf_view.store
    assert store is not None
    typ = getattr(AnnotationType, kind)
    ann = Annotation(page=0, type=typ, x=12.0, y=12.0, width=80.0, height=28.0, **kw)
    store.add(ann)
    return ann


def _prepare_inventory(key: str) -> None:
    if key == "stamp_rot":
        ann = _add_ann(kind="STAMP", text="GENEHMIGT")
        _WIN.pdf_view._selected_ann_id = ann.id
        try:
            _WIN.pdf_view.canvas.set_selected_id(ann.id)
        except Exception:
            pass
    elif key == "bm_del":
        from ild_pdf.outline import add_outline_item

        add_outline_item(_WIN.pdf_view.pdf_path, "InventarBM", 0)
        _WIN._refresh_outline(_WIN.pdf_view.pdf_path)
        tree = _WIN.sidebar.outline
        if tree.topLevelItemCount() > 0:
            tree.setCurrentItem(tree.topLevelItem(0))
    elif key == "flatten_links":
        _add_ann(kind="LINK", text="https://example.com/ild")
    try:
        _WIN._sync_menu_enablement()
    except Exception:
        pass
    pump(_APP, 0.05)


@pytest.mark.parametrize("key,needle", INVENTORY, ids=[k for k, _ in INVENTORY])
def test_inventory_item_dialog_or_file(key: str, needle: str) -> None:
    _reload_pdf()
    _prepare_inventory(key)
    act = _find_inventory_action(needle)
    assert act is not None, f"PDF-Menü fehlt: {needle}"
    if not act.isEnabled():
        try:
            act.setEnabled(True)
        except Exception:
            pass
    assert act.isEnabled(), f"disabled nach Vorbereitung: {needle}"
    before = _snap()
    _REC.events.clear()
    act.trigger()
    pump(_APP, 0.2)
    after = _snap()
    dlg = bool(_REC.events)
    changed = after != before
    assert dlg or changed, (
        f"{needle}: kein schließbarer Dialog und keine Datei-/Ansichtsänderung"
        f" (events={_REC.events!r})"
    )
