"""Ribbon-Chrome analog Word/SoftMaker — Overflow klickbar, Tabellentools kontextuell.

Tabs: Datei, Start, Einfügen, Layout, Verweise, Sendungen, Überprüfen, Ansicht
plus InstantLens: Bearbeiten, Fenster, PDF, Geräte, DTP und kontextuell Tabellentools.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc.ui.menu_click import show_scrollable_menu
from instantlensdoc.ui.styles import StyleGallery


def _std_icon(widget: QWidget, pix) -> QIcon:
    try:
        return widget.style().standardIcon(pix)
    except Exception:
        return QIcon()


class _OverflowPanel(QWidget):
    """Eine Ribbon-Zeile: sichtbare Buttons + »-Overflow ohne tote Treffer."""

    overflow_picked = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(4, 2, 4, 2)
        self._row.setSpacing(4)
        self._items: list[QWidget] = []
        self._overflow = QToolButton()
        self._overflow.setObjectName("ribbonOverflow")
        self._overflow.setText("»")
        self._overflow.setToolTip("Weitere Befehle (scrollbares Menü)")
        self._overflow.clicked.connect(self._open_overflow)
        self._row.addWidget(self._overflow)
        self._row.addStretch(1)
        self._hidden_specs: list[tuple[str, str]] = []

    def add_item(self, widget: QWidget) -> None:
        idx = self._row.indexOf(self._overflow)
        if idx < 0:
            idx = max(0, self._row.count() - 1)
        self._row.insertWidget(idx, widget)
        self._items.append(widget)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._reflow()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._reflow()

    def _reflow(self) -> None:
        avail = max(40, self.width() - self._overflow.sizeHint().width() - 16)
        used = 0
        hidden: list[QWidget] = []
        shown_any = False
        for w in self._items:
            hint = w.sizeHint().width() + 4
            if shown_any and used + hint > avail:
                w.setVisible(False)
                hidden.append(w)
                continue
            w.setVisible(True)
            used += hint
            shown_any = True
        self._hidden_specs = []
        for w in hidden:
            aid = str(w.property("ribbonActionId") or "")
            label = ""
            if isinstance(w, QToolButton):
                label = w.text()
            self._hidden_specs.append((aid or label, label or aid))
        self._overflow.setVisible(bool(self._hidden_specs))
        self._overflow.setEnabled(bool(self._hidden_specs))

    def _open_overflow(self) -> None:
        if not self._hidden_specs:
            return
        global_pos = self._overflow.mapToGlobal(QPoint(0, self._overflow.height()))
        ribbon = self.parentWidget()
        while ribbon is not None and not hasattr(ribbon, "_pick_overflow"):
            ribbon = ribbon.parentWidget()
        on_pick = ribbon._pick_overflow if ribbon is not None else (
            lambda aid: self.overflow_picked.emit(str(aid))
        )
        show_scrollable_menu(
            self._hidden_specs,
            self,
            pos=global_pos,
            on_pick=on_pick,
        )


class RibbonBar(QWidget):
    """
    Ribbon-Chrome: Word-Tabs + InstantLens (Geräte/PDF/DTP).
    Overflow: scrollbares Einspalten-Menü (menu_click) — keine toten Hits.
    Alt+1…8 wählt die ersten Word-Kategorien.
    """

    action_triggered = Signal(str)

    # Alt-Mnemonic → Kategorie-Index (Smoke/Alt-Ribbon) — Geräte bleibt erreichbar
    ALT_CATEGORY_KEYS = ("1", "2", "3", "4", "5", "6", "7", "8")

    WORD_TAB_TITLES = (
        "Datei",
        "Start",
        "Einfügen",
        "Layout",
        "Verweise",
        "Sendungen",
        "Überprüfen",
        "Ansicht",
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ildRibbonBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            "#ildRibbonBar {"
            " background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            " stop:0 #F8FAFC, stop:1 #E8EEF5);"
            " border-bottom: 1px solid #B8C2D0;"
            "}"
            "QPushButton#ribbonCat {"
            " background: transparent; border: none; padding: 6px 14px;"
            " color: #314055; font-weight: 600;"
            "}"
            "QPushButton#ribbonCat:checked {"
            " background: #FFFFFF; border: 1px solid #B8C2D0;"
            " border-bottom: 1px solid #FFFFFF; color: #0B3D91;"
            "}"
            "QToolButton {"
            " background: #FFFFFF; border: 1px solid #C5CCD6;"
            " border-radius: 3px; padding: 6px 10px; margin: 2px;"
            "}"
            "QToolButton:hover { background: #F0F5FB; border-color: #8FA3C0; }"
            "QToolButton:checked { background: #D9E6F8; border-color: #3B6DB5; }"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 2, 4, 4)
        root.setSpacing(2)

        cats = QHBoxLayout()
        cats.setSpacing(0)
        self._cat_buttons: list[QPushButton] = []
        self._stack = QStackedWidget()
        self._actions: dict[str, QToolButton] = {}
        self._action_buttons: dict[str, list[QToolButton]] = {}
        self._tab_index: dict[str, int] = {}
        self._table_tab_index = -1
        self.style_gallery: StyleGallery | None = None

        checkable = {
            "book_layout",
            "page_by_page",
            "continuous_scroll",
            "toggle_doc_tabs",
            "autocorrect_toggle",
            "doc_split",
            "toggle_ribbon",
            "review_mode",
            "chrome_klassisch",
            "chrome_ribbon",
            "chrome_kombiniert",
            "table_header_row",
            "table_borders",
        }

        def _icon_for(aid: str) -> QIcon | None:
            mapping = {
                "open": QStyle.SP_DialogOpenButton,
                "save": QStyle.SP_DialogSaveButton,
                "undo": QStyle.SP_ArrowBack,
                "redo": QStyle.SP_ArrowForward,
                "mail_merge": QStyle.SP_FileDialogListView,
                "insert_table": QStyle.SP_FileDialogDetailedView,
                "page_layout": QStyle.SP_FileDialogContentsView,
                "spellcheck": QStyle.SP_MessageBoxInformation,
            }
            pix = mapping.get(aid)
            return _std_icon(self, pix) if pix is not None else None

        def _add_button(panel: _OverflowPanel, aid: str, label: str) -> QToolButton:
            tb = QToolButton()
            tb.setText(label)
            tb.setObjectName(f"ribbonAction_{aid}")
            tb.setProperty("ribbonActionId", aid)
            tb.setToolTip(f"{label}")
            tb.setAutoRaise(False)
            if aid in checkable:
                tb.setCheckable(True)
            icon = _icon_for(aid)
            if icon is not None and not icon.isNull():
                tb.setIcon(icon)
                tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            if aid in ("undo", "redo"):
                tb.setToolTip(
                    "Rückgängig (Ctrl+Z)" if aid == "undo" else "Wiederholen (Ctrl+Y / Ctrl+Shift+Z)"
                )
            tb.clicked.connect(lambda _checked=False, a=aid: self.action_triggered.emit(a))
            self._actions.setdefault(aid, tb)
            self._action_buttons.setdefault(aid, []).append(tb)
            panel.add_item(tb)
            return tb

        panels: list[tuple[str, tuple[tuple[str, str], ...], bool, bool]] = [
            (
                "Datei",
                (
                    ("open", "Öffnen"),
                    ("save", "Speichern"),
                    ("save_as", "Speichern unter"),
                    ("print", "Drucken"),
                    ("settings", "Einstellungen"),
                ),
                False,
                False,
            ),
            (
                "Start",
                (
                    ("undo", "↶ Rückgängig"),
                    ("redo", "↷ Wiederholen"),
                    ("bold", "Fett"),
                    ("italic", "Kursiv"),
                    ("underline", "Unterstrichen"),
                    ("strike", "Durchgestrichen"),
                    ("highlight", "Textmarker"),
                    ("highlight_color", "Hintergrundfarbe"),
                    ("font", "Schriftart"),
                    ("font_color", "Farbe"),
                    ("align_left", "Links"),
                    ("align_center", "Zentriert"),
                    ("align_right", "Rechts"),
                    ("align_justify", "Blocksatz"),
                    ("bullet_list", "Aufzählung"),
                    ("numbered_list", "Nummerierung"),
                    ("paragraph", "Absatz…"),
                    ("clear_formatting", "Format löschen"),
                    ("find_replace", "Suchen"),
                    ("spellcheck", "Rechtschreibung"),
                    ("styles_pane", "Formatvorlagen"),
                ),
                True,
                False,
            ),
            (
                "Einfügen",
                (
                    ("insert_table", "Tabelle"),
                    ("insert_hyperlink", "Hyperlink"),
                    ("insert_break", "Seitenumbruch"),
                    ("insert_shape", "Form"),
                    ("header_footer", "Kopf-/Fußzeile"),
                    ("field_token", "Ersatzzeichen"),
                    ("insert_nbsp", "Geschütztes Leerzeichen"),
                    ("insert_shy", "Weiches Trennzeichen"),
                    ("insert_snippet", "Baustein"),
                ),
                False,
                False,
            ),
            (
                "Layout",
                (
                    ("page_layout", "Seitenlayout…"),
                    ("paragraph", "Absatz…"),
                    ("align_left", "Links"),
                    ("align_center", "Zentriert"),
                    ("align_right", "Rechts"),
                    ("align_justify", "Blocksatz"),
                    ("bullet_list", "Aufzählung"),
                    ("numbered_list", "Nummerierung"),
                    ("header_footer", "Kopf-/Fußzeile"),
                ),
                False,
                False,
            ),
            (
                "Verweise",
                (
                    ("auto_toc", "Inhaltsverz."),
                    ("auto_lof", "Abbildungsverz."),
                    ("auto_index", "Stichwortverz."),
                    ("insert_hyperlink", "Hyperlink"),
                ),
                False,
                False,
            ),
            (
                "Sendungen",
                (
                    ("mail_merge", "Seriendruck…"),
                    ("mail_merge_data", "Datenquelle…"),
                    ("mail_merge_field", "Feld einfügen"),
                    ("mail_merge_preview", "Vorschau"),
                    ("mail_merge_finish", "Zusammenführen"),
                ),
                False,
                False,
            ),
            (
                "Überprüfen",
                (
                    ("review_mode", "Änderungen"),
                    ("doc_comments", "Kommentare"),
                    ("shared_review", "Gemeinsam"),
                    ("version_history", "Versionen"),
                    ("spellcheck", "Rechtschreibung"),
                ),
                False,
                False,
            ),
            (
                "Ansicht",
                (
                    ("chrome_klassisch", "Klassisch"),
                    ("chrome_ribbon", "Ribbon"),
                    ("chrome_kombiniert", "Kombiniert"),
                    ("page_layout", "Seitenlayout…"),
                    ("page_size_a4", "A4"),
                    ("page_size_letter", "Letter"),
                    ("page_portrait", "Hochformat"),
                    ("page_landscape", "Querformat"),
                    ("book_layout", "Buch-Layout"),
                    ("page_by_page", "Seite-für-Seite"),
                    ("continuous_scroll", "Fortlaufend"),
                    ("toggle_doc_tabs", "Dokument-Tabs"),
                    ("toggle_ribbon", "Ribbon"),
                ),
                False,
                False,
            ),
            (
                "Bearbeiten",
                (
                    ("undo", "↶ Rückgängig"),
                    ("redo", "↷ Wiederholen"),
                    ("highlight", "Textmarker"),
                    ("highlight_color", "Hintergrundfarbe"),
                    ("spellcheck", "Rechtschreibung"),
                    ("find_replace", "Suchen/Ersetzen"),
                    ("insert_hyperlink", "Hyperlink"),
                    ("insert_table", "Tabelle"),
                    ("style_normal", "Normal"),
                    ("style_h1", "Überschrift 1"),
                    ("insert_break", "Umbruch"),
                    ("clear_formatting", "Format löschen"),
                    ("autocorrect_toggle", "Autokorrektur"),
                    ("insert_snippet", "Baustein"),
                    ("page_layout", "Seitenlayout…"),
                    ("auto_toc", "Inhaltsverz."),
                    ("auto_lof", "Abbildungsverz."),
                    ("auto_index", "Stichwortverz."),
                    ("insert_shape", "Form"),
                    ("export_epub", "EPUB"),
                    ("export_pptx", "PPTX"),
                    ("compare_pdfs", "Vergleichen"),
                ),
                False,
                False,
            ),
            (
                "Fenster",
                (
                    ("doc_split", "Teilen"),
                    ("detach_window", "Separates Fenster"),
                    ("toggle_doc_tabs", "Tabs"),
                ),
                False,
                False,
            ),
            (
                "PDF",
                (
                    ("compare_pdfs", "PDF vergleichen"),
                    ("preflight", "Preflight"),
                    ("apply_bleed", "Anschnitt"),
                    ("export_pdfx", "PDF/X"),
                    ("scan_import", "Scannen…"),
                    ("devices_discover", "Geräte erkennen"),
                ),
                False,
                False,
            ),
            (
                "Geräte",
                (
                    ("scan_import", "Scannen…"),
                    ("devices_printers", "Drucker…"),
                    ("devices_discover", "Geräte erkennen…"),
                    ("devices_refresh", "Neu suchen"),
                ),
                False,
                False,
            ),
            (
                "DTP",
                (
                    ("dtp_layout", "Layout-Modus"),
                    ("dtp_text_frame", "Textrahmen"),
                    ("dtp_link", "Verketten"),
                    ("dtp_grid", "Raster"),
                    ("dtp_export_pdf", "PDF export"),
                    ("dtp_import", "Import"),
                    ("dtp_image", "Bild…"),
                    ("dtp_graphic", "Grafik"),
                    ("dtp_fill", "Füllen"),
                    ("dtp_stroke", "Kontur"),
                    ("dtp_font", "Schrift"),
                    ("dtp_wrap", "Umfluss"),
                    ("dtp_weld", "Schweißen"),
                    ("dtp_symbol", "Symbol"),
                    ("dtp_preflight", "Preflight"),
                    ("dtp_pdfx", "PDF/X"),
                    ("dtp_text_path", "Pfadtext"),
                    ("dtp_glyphs", "Glyphen"),
                    ("ki_assistant", "KI-Assistent"),
                    ("varfonts", "Variable Fonts"),
                    ("pades_sign", "PAdES"),
                ),
                False,
                False,
            ),
            (
                "Tabellentools",
                (
                    ("table_add_row", "Zeile +"),
                    ("table_add_col", "Spalte +"),
                    ("table_del_row", "Zeile −"),
                    ("table_del_col", "Spalte −"),
                    ("table_merge", "Zellen verbinden"),
                    ("table_split", "Zelle teilen"),
                    ("table_borders", "Rahmen"),
                    ("table_header_row", "Kopfzeile"),
                    ("table_align_left", "Zelle links"),
                    ("table_align_center", "Zelle Mitte"),
                    ("table_align_right", "Zelle rechts"),
                ),
                False,
                True,
            ),
        ]

        for i, (title, buttons, with_gallery, contextual) in enumerate(panels):
            mnemonic = self.ALT_CATEGORY_KEYS[i] if i < len(self.ALT_CATEGORY_KEYS) else ""
            btn = QPushButton(title)
            btn.setObjectName("ribbonCat")
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            tip = f"{title} — Ribbon"
            if mnemonic:
                tip += f" (Alt+{mnemonic})"
            btn.setToolTip(tip)
            btn.setProperty("altMnemonic", mnemonic)
            btn.clicked.connect(lambda _=False, idx=i: self._select_cat(idx))
            cats.addWidget(btn)
            self._cat_buttons.append(btn)
            self._tab_index[title] = i
            if contextual:
                self._table_tab_index = i
                btn.hide()

            panel = _OverflowPanel()
            panel.overflow_picked.connect(self.action_triggered.emit)
            if with_gallery:
                self.style_gallery = StyleGallery(panel)
                self.style_gallery.setProperty("ribbonActionId", "styles_pane")
                self.style_gallery.style_chosen.connect(
                    lambda sid: self.action_triggered.emit(f"style:{sid}")
                )
                self.style_gallery.pane_requested.connect(
                    lambda: self.action_triggered.emit("styles_pane")
                )
                panel.add_item(self.style_gallery)
            for aid, label in buttons:
                _add_button(panel, aid, label)
            self._stack.addWidget(panel)

        cats.addStretch(1)
        root.addLayout(cats)
        root.addWidget(self._stack)
        self._select_cat(1 if self.category_count() > 1 else 0)
        self._install_alt_shortcuts()
        self.set_table_tools_visible(False)

    def _install_alt_shortcuts(self) -> None:
        """Alt+1…8 → Ribbon-Kategorie (praktische Alt-Parity)."""
        self._alt_shortcuts: list[QShortcut] = []
        for i, key in enumerate(self.ALT_CATEGORY_KEYS):
            sc = QShortcut(QKeySequence(f"Alt+{key}"), self)
            sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
            sc.activated.connect(lambda idx=i: self.select_category(idx))
            self._alt_shortcuts.append(sc)

    def _select_cat(self, index: int) -> None:
        if index < 0 or index >= self._stack.count():
            return
        btn = self._cat_buttons[index]
        if not btn.isVisible() and index == self._table_tab_index:
            return
        self._stack.setCurrentIndex(index)
        for i, b in enumerate(self._cat_buttons):
            b.blockSignals(True)
            b.setChecked(i == index)
            b.blockSignals(False)

    def select_category(self, index: int) -> None:
        """Öffentliche Kategorie-Wahl (Smoke/Alt-Ribbon)."""
        if 0 <= index < self._stack.count():
            self._select_cat(index)

    def select_tab(self, title: str) -> None:
        idx = self._tab_index.get(title)
        if idx is not None:
            self._select_cat(idx)

    def category_count(self) -> int:
        return self._stack.count()

    def set_table_tools_visible(self, visible: bool) -> None:
        if self._table_tab_index < 0:
            return
        btn = self._cat_buttons[self._table_tab_index]
        btn.setVisible(bool(visible))
        if visible:
            self._select_cat(self._table_tab_index)
        elif self._stack.currentIndex() == self._table_tab_index:
            start = self._tab_index.get("Start", 1)
            self._select_cat(start)

    def set_checked(self, action_id: str, checked: bool) -> None:
        for btn in self._action_buttons.get(action_id, ()) or ():
            if btn is not None and btn.isCheckable():
                btn.blockSignals(True)
                btn.setChecked(bool(checked))
                btn.blockSignals(False)
        btn = self._actions.get(action_id)
        if btn is not None and btn.isCheckable():
            btn.blockSignals(True)
            btn.setChecked(bool(checked))
            btn.blockSignals(False)

    def set_enabled(self, action_id: str, enabled: bool) -> None:
        """Alle Buttons einer Aktion (in allen Tabs) aktivieren/deaktivieren."""
        for btn in self._action_buttons.get(action_id, ()):
            btn.setEnabled(bool(enabled))

    def is_enabled(self, action_id: str) -> bool:
        btns = self._action_buttons.get(action_id, ())
        return bool(btns) and all(b.isEnabled() for b in btns)

    def buttons(self, action_id: str) -> list[QToolButton]:
        return list(self._action_buttons.get(action_id, ()))

    def set_action_enabled(self, action_id: str, enabled: bool) -> None:
        self.set_enabled(action_id, enabled)

    def set_action_tooltip(self, action_id: str, text: str) -> None:
        tip = str(text or "")
        for tb in self._action_buttons.get(action_id, ()) or ():
            try:
                tb.setToolTip(tip)
            except Exception:
                pass

    def bind_qactions(self, mapping: dict[str, QAction]) -> None:
        """Ribbon-Buttons lösen dieselbe QAction aus wie das Pulldown-Menü."""
        self._qactions = {}
        for aid, act in (mapping or {}).items():
            if act is None:
                continue
            self._qactions[str(aid)] = act
            for tb in self._action_buttons.get(aid, ()):
                label = tb.text()
                icon = tb.icon()
                style = tb.toolButtonStyle()
                try:
                    tb.clicked.disconnect()
                except TypeError:
                    pass
                tb.setDefaultAction(act)
                if label:
                    tb.setText(label)
                if not icon.isNull():
                    tb.setIcon(icon)
                tb.setToolButtonStyle(style)

    def qaction(self, action_id: str):
        return (getattr(self, "_qactions", None) or {}).get(action_id)

    def _pick_overflow(self, aid: str) -> None:
        """Overflow-Hit: gebundene Pulldown-QAction, sonst action_triggered."""
        act = self.qaction(str(aid))
        if act is not None:
            try:
                if act.isEnabled():
                    act.trigger()
                return
            except Exception:
                pass
        self.action_triggered.emit(str(aid))

    def bind(self, handlers: dict[str, Callable[[], None]]) -> None:
        """Optional: direkte Handler statt Signal (Smoke/Tests)."""
        self._handlers = handlers

        def _dispatch(aid: str) -> None:
            fn = (getattr(self, "_handlers", None) or {}).get(aid)
            if callable(fn):
                fn()

        self.action_triggered.connect(_dispatch)
