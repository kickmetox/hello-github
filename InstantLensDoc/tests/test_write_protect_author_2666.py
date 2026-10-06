"""Schreibschutz und Textersteller wie Word Datei/Überprüfen ▸ Schützen / Info."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["ILD_SMOKE_QT"] = "1"
os.environ.setdefault("ILD_SKIP_DEPS_CHECK", "1")
os.environ.setdefault("ILD_NO_SESSION", "1")
os.environ.setdefault("ILD_NO_SPLASH", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from instantlensdoc.core.document_author import (  # noqa: E402
    default_author,
    load_author,
    persist_author,
)
from instantlensdoc.core.documents import open_document, save_document  # noqa: E402
from instantlensdoc.core.write_protect import (  # noqa: E402
    REASON_WRITE_PROTECT,
    detect_docx_protection,
    detect_protection,
    persist_protection,
    verify_password,
)
from instantlensdoc.ui.word_ribbon import REASON_WRITE_PROTECT as RIBBON_REASON  # noqa: E402
from menu_smoke_lib import (  # noqa: E402
    build_fixtures,
    create_main_window,
    install_headless_env,
    load_state,
    pump,
)
from instantlensdoc.ui.menu_click import find_menubar_menu, iter_leaf_actions  # noqa: E402


_APP = None
_WIN = None
_TD = None
_FIXTURES = None


def setup_module() -> None:
    global _APP, _WIN, _FIXTURES, _TD
    install_headless_env()
    _TD = tempfile.TemporaryDirectory(prefix="ild-protect-author-2666-")
    _FIXTURES = build_fixtures(Path(_TD.name))
    _APP, _WIN = create_main_window()


def teardown_module() -> None:
    global _WIN, _TD
    try:
        if _WIN is not None:
            _WIN.hide()
    except Exception:
        pass
    _WIN = None
    if _TD is not None:
        _TD.cleanup()


def _leaf(title: str, label: str):
    menu = find_menubar_menu(_WIN, title)
    assert menu is not None, f"Menü {title} fehlt"
    for path, host, act in iter_leaf_actions(menu, title):
        text = (act.text() or "").replace("&", "").strip()
        if text == label:
            return path, host, act
    raise AssertionError(f"{title}: {label} nicht gefunden")


def test_reason_string_matches_word() -> None:
    assert REASON_WRITE_PROTECT == "Dokument ist schreibgeschützt"
    assert RIBBON_REASON == "Dokument ist schreibgeschützt"


def test_txt_sidecar_protect_and_author_roundtrip() -> None:
    td = Path(_TD.name)
    path = td / "brief.txt"
    path.write_text("Hallo", encoding="utf-8")
    persist_author(path, "Ada Lovelace", kind="TEXT")
    persist_protection(path, kind="TEXT", protected=True, password_hash_value="")
    info = detect_protection(path)
    assert info.protected is True
    assert info.source == "sidecar"
    author = load_author(path, kind="TEXT")
    assert author == "Ada Lovelace"
    persist_protection(path, kind="TEXT", protected=False)
    assert detect_protection(path).protected is False


def test_docx_document_protection_and_dc_creator() -> None:
    from instantlensdoc.core.documents import Document, DocKind

    td = Path(_TD.name)
    path = td / "schutz.docx"
    doc = Document(kind=DocKind.DOCX, title="schutz.docx", text="Absatz")
    doc.meta["html"] = "<p>Absatz</p>"
    doc.meta["author"] = "Clara Schumann"
    doc.meta["write_protect"] = True
    save_document(doc, path)
    assert detect_docx_protection(path) is True
    opened = open_document(path)
    assert opened.meta.get("author") == "Clara Schumann"
    assert opened.meta.get("write_protect") is True


def test_password_hash_empty_ok() -> None:
    path = Path(_TD.name) / "pw.txt"
    path.write_text("x", encoding="utf-8")
    persist_protection(path, kind="TEXT", protected=True, password_hash_value="")
    info = detect_protection(path)
    assert info.protected is True
    assert info.password_hash == ""
    assert verify_password("", "") is True
    assert verify_password("", "x") is False


def test_new_doc_defaults_os_user_author() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.05)
    want = default_author()
    assert _WIN._current_author() == want
    assert want
    assert "Autor:" in (_WIN.author_status_label.text() or "")
    assert want in (_WIN.author_status_label.text() or "")


def test_write_protect_grays_mutating_keeps_copy_print_view() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.1)
    assert _WIN._set_write_protect(True, interactive=False, password="") is True
    pump(_APP, 0.05)
    _WIN._sync_menu_enablement()
    caps = _WIN._view_capability_state()
    assert caps["write_protect"] is True
    assert caps["font"] is False
    assert caps["font_reason"] == "Dokument ist schreibgeschützt"
    _p, _h, fett = _leaf("Bearbeiten", "Fett")
    assert not fett.isEnabled()
    assert "Dokument ist schreibgeschützt" in (fett.toolTip() or "")
    _p, _h, copy = _leaf("Bearbeiten", "Kopieren")
    assert copy.isEnabled()
    _p, _h, cut = _leaf("Bearbeiten", "Ausschneiden")
    assert not cut.isEnabled()
    assert "Dokument ist schreibgeschützt" in (cut.toolTip() or "")
    _p, _h, printer = _leaf("Datei", "Drucken…")
    assert printer.isEnabled()
    _p, _h, info = _leaf("Datei", "Informationen…")
    assert info.isEnabled()
    _p, _h, schutz = _leaf("Datei", "Dokument schützen")
    assert schutz.isEnabled()
    assert schutz.isChecked()
    _p, _h, klassisch = _leaf("Ansicht", "Klassisch (Pull-down)")
    assert klassisch.isEnabled()
    assert not _WIN.ribbon_bar.is_enabled("bold")
    assert not _WIN.ribbon_bar.is_enabled("font")
    assert not _WIN.ribbon_bar.is_enabled("dtp_text_frame")
    assert not _WIN.ribbon_bar.is_enabled("page_layout")
    assert not _WIN.ribbon_bar.is_enabled("ink_input")
    assert _WIN.ribbon_bar.is_enabled("print")
    assert _WIN.ribbon_bar.is_enabled("write_protect")
    assert _WIN.ribbon_bar.is_enabled("doc_info")
    assert _WIN.ribbon_bar.is_enabled("chrome_klassisch")
    assert _WIN.ribbon_bar.is_enabled("dtp_layout")
    assert _WIN.editor.isReadOnly()
    assert _WIN._set_write_protect(False, interactive=False, password="") is True
    pump(_APP, 0.05)
    _WIN._sync_menu_enablement()
    assert _WIN._view_capability_state()["font"] is True
    assert _leaf("Bearbeiten", "Fett")[2].isEnabled()
    assert not _WIN.editor.isReadOnly()


def test_write_protect_password_blocks_wrong() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.05)
    assert _WIN._set_write_protect(True, interactive=False, password="geheim") is True
    assert _WIN._document_is_write_protected()
    assert _WIN._set_write_protect(False, interactive=False, password="falsch") is False
    assert _WIN._document_is_write_protected()
    assert _WIN._set_write_protect(False, interactive=False, password="geheim") is True
    assert not _WIN._document_is_write_protected()


def test_write_protect_grays_dtp_and_annotate_on_pdf() -> None:
    load_state(_WIN, _APP, "pdf20", _FIXTURES)
    pump(_APP, 0.2)
    assert _WIN._set_write_protect(True, interactive=False, password="") is True
    pump(_APP, 0.05)
    _WIN._sync_menu_enablement()
    caps = _WIN._view_capability_state()
    assert caps["write_protect"] is True
    assert caps["font"] is False
    assert not _WIN.ribbon_bar.is_enabled("dtp_text_frame")
    assert not _WIN.ribbon_bar.is_enabled("ink_input")
    assert not _WIN.ribbon_bar.is_enabled("stamp_place")
    assert _WIN.ribbon_bar.is_enabled("print")
    assert _WIN.ribbon_bar.is_enabled("chrome_ribbon")
    rtip = _WIN.ribbon_bar._actions["bold"].toolTip() or ""
    assert "Dokument ist schreibgeschützt" in rtip
    _WIN._set_write_protect(False, interactive=False, password="")


def test_author_field_token_uses_doc_meta() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    pump(_APP, 0.05)
    _WIN.doc.meta["author"] = "Testautorin"
    ctx = _WIN._field_resolve_context()
    assert ctx.author == "Testautorin"
    assert _WIN.editor.insert_field_token("author", target="body") is True
    assert "{author}" in _WIN.editor.toPlainText()


def test_menus_have_protect_and_info() -> None:
    load_state(_WIN, _APP, "empty", _FIXTURES)
    _leaf("Datei", "Dokument schützen")
    _leaf("Datei", "Informationen…")
    _leaf("Bearbeiten", "Dokument schützen")
    assert "write_protect" in _WIN.ribbon_bar._actions
    assert "doc_info" in _WIN.ribbon_bar._actions
