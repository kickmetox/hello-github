"""Ribbon-Chrome analog Word/SoftMaker — Overflow klickbar, Tabellentools kontextuell.

Tabs: Datei, Start, Einfügen, Layout, Verweise, Sendungen, Überprüfen, Ansicht
plus InstantLens: Bearbeiten, Fenster, PDF, Geräte, DTP und kontextuell Tabellentools.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc.ui.chrome import wrap_hscroll
from instantlensdoc.ui.menu_click import show_scrollable_menu
from instantlensdoc.ui.styles import StyleGallery
from instantlensdoc.ui.word_ribbon import WORD_TAB_GROUPS


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

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        h = super().minimumSizeHint().height()
        w = self._overflow.sizeHint().width() + 20
        if self._items:
            w += max(24, self._items[0].sizeHint().width())
        return QSize(w, h)

    def sizeHint(self) -> QSize:  # noqa: N802
        h = super().sizeHint().height()
        w = self._overflow.sizeHint().width() + 12
        for item in self._items:
            w += item.sizeHint().width() + 4
        return QSize(max(w, 80), h)

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
            qactions=getattr(ribbon, "_qactions", None) if ribbon is not None else None,
        )


class _RibbonGroup(QWidget):
    """Beschriftete Word-Gruppe (Seite einrichten / Absatz / Anordnen)."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ribbonGroup")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setStyleSheet(
            "QWidget#ribbonGroup { border-right: 1px solid #C5CCD6; }"
            "QLabel#ribbonGroupTitle { color: #5A6A7A; font-size: 10px; }"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 0, 6, 0)
        lay.setSpacing(0)
        self.panel = _OverflowPanel(self)
        lab = QLabel(title)
        lab.setObjectName("ribbonGroupTitle")
        lab.setAlignment(Qt.AlignHCenter)
        lay.addWidget(self.panel, 1)
        lay.addWidget(lab)


class RibbonBar(QWidget):
    """
    Ribbon-Chrome: Word-Tabs + InstantLens (Geräte/PDF/DTP).
    Overflow: scrollbares Einspalten-Menü (menu_click) — keine toten Hits.
    Alt+1…8 wählt die ersten Word-Kategorien.
    """

    action_triggered = Signal(str)
    categorySelected = Signal(str)

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

        cat_strip = QWidget()
        cat_strip.setObjectName("ildRibbonTabStrip")
        cats = QHBoxLayout(cat_strip)
        cats.setContentsMargins(0, 0, 0, 0)
        cats.setSpacing(0)
        self._cat_buttons: list[QPushButton] = []
        self._stack = QStackedWidget()
        self._actions: dict[str, QToolButton] = {}
        self._action_buttons: dict[str, list[QToolButton]] = {}
        self._tab_index: dict[str, int] = {}
        self._table_tab_index = -1
        self._arrange_group: QWidget | None = None
        self._prev_index = 0
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
            "line_numbers",
            "dtp_layout",
            "toggle_rulers",
            "toggle_grid",
            "toggle_navigation",
            "format_painter",
            "view_print",
            "view_draft",
            "view_web",
            "view_outline",
            "show_special_chars",
            "toggle_minimap",
            "ink_input",
            "width_marks",
            "print_marks",
            "header_footer_marks",
            "ink_pen_ballpoint",
            "ink_pen_felt",
            "ink_pen_highlighter",
            "ink_brush",
            "ink_fill_none",
            "ink_fill_closed",
            "ink_fill_flood",
            "right_toolbox",
            "write_protect",
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

        def _add_menu_button(
            panel: _OverflowPanel,
            aid: str,
            label: str,
            items: tuple[tuple[str, str], ...],
        ) -> QToolButton:
            tb = QToolButton()
            tb.setText(label)
            tb.setObjectName(f"ribbonAction_{aid}")
            tb.setProperty("ribbonActionId", aid)
            tb.setToolTip(label)
            tb.setAutoRaise(False)
            tb.setPopupMode(QToolButton.InstantPopup)
            menu = QMenu(tb)
            menu.setObjectName(f"ribbonMenu_{aid}")
            for item_aid, item_label in items:
                act = QAction(item_label, tb)
                act.setObjectName(f"ribbonMenuAction_{item_aid}")
                act.triggered.connect(
                    lambda _checked=False, a=item_aid: self.action_triggered.emit(a)
                )
                menu.addAction(act)
            tb.setMenu(menu)
            self._actions.setdefault(aid, tb)
            self._action_buttons.setdefault(aid, []).append(tb)
            panel.add_item(tb)
            return tb

        def _add_disabled_button(
            panel: _OverflowPanel, aid: str, label: str, reason: str
        ) -> QToolButton:
            tb = _add_button(panel, aid, label)
            tb.setEnabled(False)
            tb.setProperty("ribbonUnavailable", True)
            tip = f"{label}: {reason}"
            tb.setToolTip(tip)
            return tb

        def _fill_group_items(panel: _OverflowPanel, items: tuple) -> None:
            for spec in items:
                aid = spec[0]
                label = spec[1]
                kind = spec[2] if len(spec) > 2 else ""
                extra = spec[3] if len(spec) > 3 else None
                if kind == "off":
                    _add_disabled_button(panel, aid, label, str(extra or ""))
                elif kind == "menu" and extra:
                    _add_menu_button(panel, aid, label, tuple(extra))
                else:
                    _add_button(panel, aid, label)

        def _build_grouped_tab(
            title: str,
            groups: tuple,
            *,
            with_gallery: bool = False,
        ) -> QWidget:
            wrap = QWidget()
            wrap.setObjectName(f"ribbon{title}Tab")
            row = QHBoxLayout(wrap)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0)
            for gtitle, items in groups:
                grp = _RibbonGroup(gtitle, wrap)
                grp.panel.overflow_picked.connect(self.action_triggered.emit)
                if with_gallery and gtitle == "Formatvorlagen" and self.style_gallery is None:
                    self.style_gallery = StyleGallery(grp.panel)
                    self.style_gallery.setProperty("ribbonActionId", "styles_pane")
                    self.style_gallery.style_chosen.connect(
                        lambda sid: self.action_triggered.emit(f"style:{sid}")
                    )
                    self.style_gallery.pane_requested.connect(
                        lambda: self.action_triggered.emit("styles_pane")
                    )
                    grp.panel.add_item(self.style_gallery)
                _fill_group_items(grp.panel, items)
                row.addWidget(grp)
            row.addStretch(1)
            return wrap

        def _build_layout_tab() -> QWidget:
            wrap = QWidget()
            wrap.setObjectName("ribbonLayoutTab")
            row = QHBoxLayout(wrap)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0)
            g_page = _RibbonGroup("Seite einrichten", wrap)
            g_page.panel.overflow_picked.connect(self.action_triggered.emit)
            _add_menu_button(
                g_page.panel,
                "page_margins",
                "Seitenränder",
                (
                    ("page_margins_normal", "Normal"),
                    ("page_margins_narrow", "Schmal"),
                    ("page_margins_wide", "Breit"),
                    ("page_margins_custom", "Benutzerdefiniert…"),
                ),
            )
            _add_menu_button(
                g_page.panel,
                "page_orientation",
                "Ausrichtung",
                (
                    ("page_portrait", "Hochformat"),
                    ("page_landscape", "Querformat"),
                ),
            )
            _add_menu_button(
                g_page.panel,
                "page_size",
                "Format",
                (
                    ("page_size_a4", "A4"),
                    ("page_size_letter", "Letter"),
                    ("page_size_legal", "Legal"),
                    ("page_layout", "Benutzerdefiniert…"),
                ),
            )
            _add_menu_button(
                g_page.panel,
                "page_columns",
                "Spalten",
                (
                    ("page_columns_1", "1 Spalte"),
                    ("page_columns_2", "2 Spalten"),
                    ("page_columns_3", "3 Spalten"),
                ),
            )
            _add_menu_button(
                g_page.panel,
                "page_breaks",
                "Umbrüche",
                (
                    ("insert_break", "Seitenumbruch"),
                    ("section_break", "Abschnittsumbruch"),
                ),
            )
            _add_button(g_page.panel, "line_numbers", "Zeilennummern")
            _add_menu_button(
                g_page.panel,
                "hyphenate",
                "Silbentrennung",
                (
                    ("hyphenate_de", "Deutsch"),
                    ("hyphenate_en", "English"),
                    ("hyphenate_fr", "Français"),
                    ("hyphenate_es", "Español"),
                    ("hyphenate_it", "Italiano"),
                ),
            )
            _add_button(g_page.panel, "page_layout", "Seitenlayout…")
            row.addWidget(g_page, 1)

            g_para = _RibbonGroup("Absatz", wrap)
            g_para.panel.overflow_picked.connect(self.action_triggered.emit)
            _add_button(g_para.panel, "outdent", "Einzug −")
            _add_button(g_para.panel, "indent", "Einzug +")
            _add_button(g_para.panel, "paragraph", "Abstand…")
            row.addWidget(g_para)

            g_arr = _RibbonGroup("Anordnen", wrap)
            g_arr.setObjectName("ribbonArrangeGroup")
            g_arr.panel.overflow_picked.connect(self.action_triggered.emit)
            _add_button(g_arr.panel, "bring_forward", "Vorwärts")
            _add_button(g_arr.panel, "send_backward", "Rückwärts")
            row.addWidget(g_arr)
            self._arrange_group = g_arr

            g_dtp = _RibbonGroup("DTP-Werkzeuge", wrap)
            g_dtp.setObjectName("ribbonDtpToolsGroup")
            g_dtp.panel.overflow_picked.connect(self.action_triggered.emit)
            _add_button(g_dtp.panel, "dtp_layout", "DTP-Werkzeuge")
            _add_button(g_dtp.panel, "dtp_text_frame", "Textrahmen")
            _add_button(g_dtp.panel, "dtp_link", "Verketten")
            _add_button(g_dtp.panel, "dtp_grid", "Raster")
            _add_button(g_dtp.panel, "dtp_wrap", "Umfluss")
            row.addWidget(g_dtp)
            self._dtp_tools_group = g_dtp
            row.addStretch(1)
            return wrap

        panels: list[tuple[str, tuple[tuple[str, str], ...], bool, bool]] = [
            (
                "Datei",
                (
                    ("open", "Öffnen"),
                    ("save", "Speichern"),
                    ("save_as", "Speichern unter"),
                    ("print", "Drucken"),
                    ("doc_info", "Informationen"),
                    ("write_protect", "Schreibschutz"),
                    ("settings", "Einstellungen"),
                ),
                False,
                False,
            ),
            (
                "Start",
                (),
                True,
                False,
            ),
            (
                "Einfügen",
                (),
                False,
                False,
            ),
            (
                "Layout",
                (),
                False,
                False,
            ),
            (
                "Verweise",
                (),
                False,
                False,
            ),
            (
                "Sendungen",
                (),
                False,
                False,
            ),
            (
                "Überprüfen",
                (),
                False,
                False,
            ),
            (
                "Ansicht",
                (),
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
                    ("dtp_layout", "DTP-Werkzeuge"),
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
                    ("dtp_font_color", "Schriftfarbe"),
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

            if title == "Layout":
                self._stack.addWidget(_build_layout_tab())
                continue
            if title in WORD_TAB_GROUPS:
                self._stack.addWidget(
                    _build_grouped_tab(
                        title,
                        WORD_TAB_GROUPS[title],
                        with_gallery=(title == "Start"),
                    )
                )
                continue

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
        root.addWidget(wrap_hscroll(cat_strip, object_name="ildRibbonTabScroll"))
        root.addWidget(
            wrap_hscroll(
                self._stack,
                object_name="ildRibbonBodyScroll",
                widget_resizable=True,
            ),
            1,
        )
        # Chrome-Tab „Seitenlayout“ = bestehendes Ribbon-Tab „Layout“ (kein zweites Ribbon).
        if "Layout" in self._tab_index:
            self._tab_index["Seitenlayout"] = self._tab_index["Layout"]
        self._select_cat(1 if self.category_count() > 1 else 0)
        self._install_alt_shortcuts()
        self.set_table_tools_visible(False)
        self.set_arrange_visible(False)
        self.set_dtp_tools_visible(True)

    def _install_alt_shortcuts(self) -> None:
        """Alt+1…8 → Ribbon-Kategorie (praktische Alt-Parity)."""
        self._alt_shortcuts: list[QShortcut] = []
        for i, key in enumerate(self.ALT_CATEGORY_KEYS):
            sc = QShortcut(QKeySequence(f"Alt+{key}"), self)
            sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
            sc.activated.connect(lambda idx=i: self.select_category(idx))
            self._alt_shortcuts.append(sc)

    def _select_cat(self, index: int, *, notify: bool = True) -> None:
        if index < 0 or index >= self._stack.count():
            return
        btn = self._cat_buttons[index]
        if not btn.isVisible() and index == self._table_tab_index:
            return
        current = self._stack.currentIndex()
        if notify and current != index:
            self._prev_index = current
        self._stack.setCurrentIndex(index)
        for i, b in enumerate(self._cat_buttons):
            b.blockSignals(True)
            b.setChecked(i == index)
            b.blockSignals(False)
        if notify:
            self.categorySelected.emit((btn.text() or "").strip())

    def restore_previous_category(self) -> None:
        """Nach Abbruch (Speichern-Dialog) den vorherigen Ribbon-Tab wiederherstellen."""
        prev = int(getattr(self, "_prev_index", 0) or 0)
        self._select_cat(prev, notify=False)

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
        """Tabellentools bleiben sichtbar; Anwendbarkeit über Enablement, nicht Hide."""
        if self._table_tab_index < 0:
            return
        btn = self._cat_buttons[self._table_tab_index]
        btn.setVisible(True)

    def set_arrange_visible(self, visible: bool) -> None:
        """Anordnen bleibt sichtbar; ausgegraut wenn kein Rahmen gewählt."""
        g = getattr(self, "_arrange_group", None)
        if g is not None:
            g.setVisible(True)

    def set_dtp_tools_visible(self, visible: bool) -> None:
        """DTP-Gruppen bleiben in der Word-Leiste sichtbar (keine zweite Ansicht)."""
        g = getattr(self, "_dtp_tools_group", None)
        if g is not None:
            g.setVisible(True)

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

    def set_available(self, action_id: str, enabled: bool, reason: str = "") -> None:
        """Ausgrauen mit deutschem Grund; Cloud-Buttons (ribbonUnavailable) unangetastet."""
        extra = str(reason or "").strip()
        for tb in self._action_buttons.get(action_id, ()) or ():
            try:
                if tb.property("ribbonUnavailable"):
                    continue
                src = tb.property("ildAvailTip")
                if not src:
                    src = tb.toolTip() or tb.text() or ""
                    tb.setProperty("ildAvailTip", src)
                tb.setEnabled(bool(enabled))
                base = str(src).strip()
                if enabled or not extra:
                    tb.setToolTip(base)
                else:
                    tb.setToolTip(f"{base} — {extra}".strip(" —") if base else extra)
            except Exception:
                try:
                    tb.setEnabled(bool(enabled))
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
                if tb.menu() is not None:
                    continue
                if tb.property("ribbonUnavailable"):
                    continue
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
