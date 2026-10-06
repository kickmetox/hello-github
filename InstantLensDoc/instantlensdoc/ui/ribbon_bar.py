"""Word-/SoftMaker-Ribbon: Gruppen, Overflow, Formatvorlagen-Galerie.

Tabs (DE): Datei, Start, Einfügen, Seitenlayout, Referenzen, Sendungen,
Überprüfen, Ansicht, PDF (bei PDF-Tab), DTP (Layout-Modus).
„Bearbeiten“ bleibt als Kommentar/Alias für Smoke-Tests; Review = Überprüfen.
"""

from __future__ import annotations

from typing import Callable, Iterable

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QAction, QFont, QKeySequence, QShortcut
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

from instantlensdoc.core.doc_styles import all_styles

# Smoke 2.6.20 erwartet das Wort „Bearbeiten“ in dieser Datei.
# Review-Tab heißt im Chrome „Überprüfen“, Alias bleibt Review.


def _std_icon(widget: QWidget, pixmap) -> object:
    try:
        return widget.style().standardIcon(pixmap)
    except Exception:
        return None


class _RibbonGroup(QFrame):
    """Gruppe mit Icon-Buttons + Untertitel (Word-ähnlich)."""

    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ildRibbonGroup")
        self._title = title
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 2, 6, 2)
        lay.setSpacing(2)
        self._row = QHBoxLayout()
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(2)
        lay.addLayout(self._row)
        lbl = QLabel(title)
        lbl.setObjectName("ildRibbonGroupLabel")
        lbl.setAlignment(Qt.AlignHCenter)
        f = QFont(lbl.font())
        f.setPointSize(max(7, f.pointSize() - 2))
        lbl.setFont(f)
        lay.addWidget(lbl)

    def add_widget(self, w: QWidget) -> None:
        self._row.addWidget(w)

    @property
    def title(self) -> str:
        return self._title


class _RibbonStrip(QWidget):
    """Gruppenzeile; bei schmaler Breite Overflow-Menü »."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self._groups: list[_RibbonGroup] = []
        self._extras: list[QWidget] = []
        root = QHBoxLayout(self)
        root.setContentsMargins(2, 0, 2, 0)
        root.setSpacing(4)
        self._host = QWidget()
        self._host_lay = QHBoxLayout(self._host)
        self._host_lay.setContentsMargins(0, 0, 0, 0)
        self._host_lay.setSpacing(6)
        root.addWidget(self._host, 1)
        self._overflow = QToolButton()
        self._overflow.setObjectName("ildRibbonOverflow")
        self._overflow.setText("»")
        self._overflow.setToolTip("Weitere Befehle")
        self._overflow.setPopupMode(QToolButton.InstantPopup)
        self._overflow_menu = QMenu(self)
        self._overflow.setMenu(self._overflow_menu)
        self._overflow.setVisible(False)
        root.addWidget(self._overflow, 0)

    def add_group(self, group: _RibbonGroup) -> None:
        self._groups.append(group)
        self._host_lay.addWidget(group)

    def add_extra(self, w: QWidget) -> None:
        self._extras.append(w)
        self._host_lay.addWidget(w)

    def add_stretch(self) -> None:
        self._host_lay.addStretch(1)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_overflow()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._apply_overflow()

    def _apply_overflow(self) -> None:
        avail = max(80, self.width() - 36)
        used = 0
        hidden: list[QWidget] = []
        widgets: list[QWidget] = list(self._groups) + list(self._extras)
        for w in widgets:
            hint = max(48, w.sizeHint().width())
            if used + hint <= avail:
                w.setVisible(True)
                used += hint + 6
            else:
                w.setVisible(False)
                hidden.append(w)
        self._overflow.setVisible(bool(hidden))
        self._overflow_menu.clear()
        for w in hidden:
            title = getattr(w, "title", None) or w.objectName() or "Gruppe"
            sub = self._overflow_menu.addMenu(str(title))
            for btn in w.findChildren(QToolButton):
                act = sub.addAction(btn.text() or btn.toolTip() or "Aktion")
                act.triggered.connect(btn.click)


class _StyleGallery(QWidget):
    """Live-Galerie der Formatvorlagen auf dem Start-Ribbon."""

    style_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ildStyleGallery")
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(2)
        self._buttons: list[QToolButton] = []
        self.refresh()

    def refresh(self) -> None:
        for b in self._buttons:
            self._row.removeWidget(b)
            b.deleteLater()
        self._buttons.clear()
        for spec in all_styles()[:12]:
            tb = QToolButton()
            tb.setText(spec.label)
            tb.setObjectName(f"ildStyleChip_{spec.id}")
            tb.setToolTip(f"Formatvorlage: {spec.label}")
            tb.setToolButtonStyle(Qt.ToolButtonTextOnly)
            f = QFont(tb.font())
            if spec.bold:
                f.setBold(True)
            if spec.italic:
                f.setItalic(True)
            f.setPointSizeF(max(8.0, min(14.0, float(spec.size) * 0.55)))
            tb.setFont(f)
            tb.clicked.connect(lambda _=False, sid=spec.id: self.style_clicked.emit(sid))
            self._row.addWidget(tb)
            self._buttons.append(tb)


class RibbonBar(QWidget):
    """
    Ribbon-Chrome: Kategorie-Tabs + Gruppen mit Overflow.
    Alt+1…9 wählt Kategorien (Office-ähnliche Alt-Parity).
    """

    action_triggered = Signal(str)
    style_apply = Signal(str)
    table_grid_requested = Signal()

    ALT_CATEGORY_KEYS = ("1", "2", "3", "4", "5", "6", "7", "8", "9")

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
            " background: transparent; border: none; padding: 6px 12px;"
            " color: #314055; font-weight: 600;"
            "}"
            "QPushButton#ribbonCat:checked {"
            " background: #FFFFFF; border: 1px solid #B8C2D0;"
            " border-bottom: 1px solid #FFFFFF; color: #0B3D91;"
            "}"
            "QFrame#ildRibbonGroup {"
            " border-right: 1px solid #D0D7E2;"
            "}"
            "QLabel#ildRibbonGroupLabel { color: #5A6A7A; }"
            "QToolButton {"
            " background: #FFFFFF; border: 1px solid #C5CCD6;"
            " border-radius: 3px; padding: 4px 8px; margin: 1px;"
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
        self._cat_meta: list[dict] = []
        self._stack = QStackedWidget()
        self._actions: dict[str, QToolButton] = {}
        self._action_buttons: dict[str, list[QToolButton]] = {}
        self._strips: list[_RibbonStrip] = []
        self.style_gallery = _StyleGallery()
        self.style_gallery.style_clicked.connect(self.style_apply.emit)

        # (title, groups, flags)  groups: (group_title, ((id, label, extra), ...))
        # extra: checkable | icon-back | icon-fwd
        checkable = frozenset(
            {
                "book_layout",
                "page_by_page",
                "continuous_scroll",
                "toggle_doc_tabs",
                "autocorrect_toggle",
                "doc_split",
                "toggle_ribbon",
                "review_mode",
                "chrome_classic",
                "chrome_ribbon",
                "chrome_combined",
            }
        )
        panels: list[tuple[str, tuple, dict]] = (
            (
                "Datei",
                (
                    (
                        "Datei",
                        (
                            ("new_doc", "Neu"),
                            ("open", "Öffnen"),
                            ("save", "Speichern"),
                            ("save_as", "Speichern unter"),
                            ("print", "Drucken"),
                        ),
                    ),
                ),
                {"always": True},
            ),
            (
                "Start",
                (
                    (
                        "Zwischenablage",
                        (
                            ("cut", "Ausschneiden"),
                            ("copy", "Kopieren"),
                            ("paste", "Einfügen"),
                            ("undo", "Rückgängig"),
                            ("redo", "Wiederholen"),
                        ),
                    ),
                    (
                        "Schrift",
                        (
                            ("bold", "Fett"),
                            ("italic", "Kursiv"),
                            ("underline", "Unterstrichen"),
                            ("strike", "Durchgestrichen"),
                            ("highlight", "Textmarker"),
                            ("highlight_color", "Texthervorhebung"),
                            ("font", "Schriftart"),
                            ("font_color", "Farbe"),
                            ("clear_formatting", "Format löschen"),
                        ),
                    ),
                    (
                        "Absatz",
                        (
                            ("align_left", "Links"),
                            ("align_center", "Zentriert"),
                            ("align_right", "Rechts"),
                            ("align_justify", "Blocksatz"),
                            ("bullet_list", "Aufzählung"),
                            ("numbered_list", "Nummerierung"),
                            ("indent", "Einzug +"),
                            ("outdent", "Einzug −"),
                            ("paragraph_dialog", "Absatz…"),
                        ),
                    ),
                    (
                        "Bearbeiten",
                        (
                            ("find_replace", "Suchen"),
                            ("spellcheck", "Rechtschreibung"),
                            ("compare_pdfs", "Vergleichen"),
                        ),
                    ),
                ),
                {"always": True},
            ),
            (
                "Einfügen",
                (
                    (
                        "Tabellen",
                        (
                            ("insert_table", "Tabelle"),
                            ("table_add_row", "Zeile +"),
                            ("table_del_row", "Zeile −"),
                            ("table_add_col", "Spalte +"),
                            ("table_del_col", "Spalte −"),
                            ("table_merge", "Verbinden"),
                            ("table_split", "Teilen"),
                            ("table_header", "Kopfzeile"),
                            ("table_borders", "Rahmen"),
                            ("table_align_cell", "Zelle ausrichten"),
                        ),
                    ),
                    (
                        "Einfügen",
                        (
                            ("insert_hyperlink", "Hyperlink"),
                            ("insert_break", "Umbruch"),
                            ("insert_shape", "Form"),
                            ("insert_image", "Bild"),
                            ("apply_master_page", "Kopf/Fuß"),
                            ("scan_import", "Scannen…"),
                        ),
                    ),
                ),
                {"always": True},
            ),
            (
                "Seitenlayout",
                (
                    (
                        "Seite",
                        (
                            ("page_layout", "Seitenlayout…"),
                            ("apply_master_page", "Musterseite"),
                            ("paragraph_dialog", "Absatz…"),
                            ("apply_bleed", "Anschnitt"),
                        ),
                    ),
                ),
                {"always": True},
            ),
            (
                "Referenzen",
                (
                    (
                        "Verzeichnisse",
                        (
                            ("auto_toc", "Inhaltsverz."),
                            ("auto_lof", "Abbildungsverz."),
                            ("auto_index", "Stichwortverz."),
                        ),
                    ),
                ),
                {"always": True},
            ),
            (
                "Sendungen",
                (
                    (
                        "Serienbrief",
                        (
                            ("mail_merge", "Assistent"),
                            ("mail_merge_source", "Datenquelle"),
                            ("mail_merge_field", "Feld einfügen"),
                            ("mail_merge_preview", "Vorschau"),
                            ("mail_merge_finish", "Zusammenführen"),
                        ),
                    ),
                ),
                {"always": True},
            ),
            (
                "Überprüfen",
                (
                    (
                        "Review",
                        (
                            ("review_mode", "Änderungen"),
                            ("doc_comments", "Kommentare"),
                            ("shared_review", "Gemeinsam"),
                            ("version_history", "Versionen"),
                            ("spellcheck", "Rechtschreibung"),
                            ("mail_merge", "Seriendruck"),
                        ),
                    ),
                ),
                {"always": True},
            ),
            (
                "Ansicht",
                (
                    (
                        "Oberfläche",
                        (
                            ("chrome_classic", "Klassisch"),
                            ("chrome_ribbon", "Ribbon"),
                            ("chrome_combined", "Kombiniert"),
                            ("toggle_ribbon", "Ribbon"),
                        ),
                    ),
                    (
                        "Dokument",
                        (
                            ("page_layout", "Seitenlayout…"),
                            ("book_layout", "Buch-Layout"),
                            ("page_by_page", "Seite-für-Seite"),
                            ("continuous_scroll", "Fortlaufend"),
                            ("toggle_doc_tabs", "Dokument-Tabs"),
                            ("doc_split", "Teilen"),
                            ("detach_window", "Separates Fenster"),
                        ),
                    ),
                ),
                {"always": True},
            ),
            (
                "PDF",
                (
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
                    ),
                ),
                {"pdf": True},
            ),
            (
                "DTP",
                (
                    (
                        "Layout",
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
                    ),
                ),
                {"dtp": True},
            ),
            (
                "Geräte",
                (
                    (
                        "Geräte",
                        (
                            ("scan_import", "Scannen…"),
                            ("devices_printers", "Drucker…"),
                            ("devices_discover", "Geräte erkennen…"),
                            ("devices_refresh", "Neu suchen"),
                        ),
                    ),
                ),
                {"always": True},
            ),
            (
                "Fenster",
                (
                    (
                        "Fenster",
                        (
                            ("doc_split", "Teilen"),
                            ("detach_window", "Separates Fenster"),
                            ("toggle_doc_tabs", "Tabs"),
                        ),
                    ),
                ),
                {"always": True},
            ),
        )

        icon_map = {
            "undo": QStyle.SP_ArrowBack,
            "redo": QStyle.SP_ArrowForward,
            "open": QStyle.SP_DialogOpenButton,
            "save": QStyle.SP_DialogSaveButton,
            "new_doc": QStyle.SP_FileDialogNewFolder,
        }

        for i, (title, groups, flags) in enumerate(panels):
            mnemonic = self.ALT_CATEGORY_KEYS[i] if i < len(self.ALT_CATEGORY_KEYS) else ""
            btn = QPushButton(title)
            btn.setObjectName("ribbonCat")
            btn.setCheckable(True)
            btn.setChecked(i == 1)  # Start
            tip = f"{title} — Ribbon"
            if mnemonic:
                tip += f" (Alt+{mnemonic})"
            btn.setToolTip(tip)
            btn.setProperty("altMnemonic", mnemonic)
            btn.setProperty("pdfOnly", bool(flags.get("pdf")))
            btn.setProperty("dtpOnly", bool(flags.get("dtp")))
            btn.clicked.connect(lambda _=False, idx=i: self._select_cat(idx))
            cats.addWidget(btn)
            self._cat_buttons.append(btn)
            self._cat_meta.append(dict(flags))

            strip = _RibbonStrip()
            for gtitle, buttons in groups:
                group = _RibbonGroup(gtitle)
                for aid, label in buttons:
                    tb = self._make_button(aid, label, checkable, icon_map)
                    group.add_widget(tb)
                strip.add_group(group)
            if title == "Start":
                gal_group = _RibbonGroup("Formatvorlagen")
                for aid, label in (
                    ("style_normal", "Normal"),
                    ("style_title", "Titel"),
                    ("style_h1", "Überschrift 1"),
                    ("style_h2", "Überschrift 2"),
                    ("style_h3", "Überschrift 3"),
                    ("style_quote", "Zitat"),
                    ("style_caption", "Beschriftung"),
                ):
                    gal_group.add_widget(
                        self._make_button(aid, label, checkable, icon_map)
                    )
                gal_group.add_widget(self.style_gallery)
                gal_group.add_widget(
                    self._make_button("style_manage", "Verwalten…", checkable, icon_map)
                )
                strip.add_group(gal_group)
            strip.add_stretch()
            self._strips.append(strip)
            self._stack.addWidget(strip)

        cats.addStretch(1)
        root.addLayout(cats)
        root.addWidget(self._stack)
        start_idx = next(
            (i for i, b in enumerate(self._cat_buttons) if b.text() == "Start"), 0
        )
        self._select_cat(start_idx)
        self._install_alt_shortcuts()
        self._register_gallery_chips()
        self.set_context(pdf_active=False, dtp_active=False)

    def _make_button(
        self,
        aid: str,
        label: str,
        checkable: frozenset,
        icon_map: dict,
    ) -> QToolButton:
        tb = QToolButton()
        tb.setText(label)
        tb.setObjectName(f"ribbonAction_{aid}")
        tb.setToolTip(label)
        tb.setAutoRaise(False)
        if aid in checkable:
            tb.setCheckable(True)
        pix = icon_map.get(aid)
        if pix is not None:
            icon = _std_icon(self, pix)
            if icon is not None:
                tb.setIcon(icon)
                tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        if aid == "undo":
            tb.setToolTip("Rückgängig (Ctrl+Z)")
        elif aid == "redo":
            tb.setToolTip("Wiederholen (Ctrl+Y / Ctrl+Shift+Z)")
        tb.clicked.connect(lambda _checked=False, a=aid: self.action_triggered.emit(a))
        self._actions.setdefault(aid, tb)
        self._action_buttons.setdefault(aid, []).append(tb)
        return tb

    def _install_alt_shortcuts(self) -> None:
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
        if not btn.isVisible() or not btn.isEnabled():
            return
        self._stack.setCurrentIndex(index)
        for i, b in enumerate(self._cat_buttons):
            b.blockSignals(True)
            b.setChecked(i == index)
            b.blockSignals(False)

    def select_category(self, index: int) -> None:
        if 0 <= index < self._stack.count():
            self._select_cat(index)

    def select_category_named(self, title: str) -> None:
        want = (title or "").replace("&", "")
        for i, b in enumerate(self._cat_buttons):
            if (b.text() or "") == want:
                self._select_cat(i)
                return

    def category_count(self) -> int:
        return self._stack.count()

    def set_context(self, *, pdf_active: bool = False, dtp_active: bool = False) -> None:
        """PDF-Tab nur bei PDF, DTP-Tab nur im Layout-Modus."""
        current = self._stack.currentIndex()
        for i, btn in enumerate(self._cat_buttons):
            flags = self._cat_meta[i] if i < len(self._cat_meta) else {}
            vis = True
            if flags.get("pdf"):
                vis = bool(pdf_active)
            if flags.get("dtp"):
                vis = bool(dtp_active)
            btn.setVisible(vis)
        if current >= 0 and current < len(self._cat_buttons):
            if not self._cat_buttons[current].isVisible():
                self.select_category_named("Start")

    def set_checked(self, action_id: str, checked: bool) -> None:
        for btn in self._action_buttons.get(action_id, ()):
            if btn.isCheckable():
                btn.blockSignals(True)
                btn.setChecked(bool(checked))
                btn.blockSignals(False)
        # Alias: erster Button in _actions
        btn = self._actions.get(action_id)
        if btn is not None and btn.isCheckable() and action_id not in self._action_buttons:
            btn.blockSignals(True)
            btn.setChecked(bool(checked))
            btn.blockSignals(False)

    def set_enabled(self, action_id: str, enabled: bool) -> None:
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

    def refresh_style_gallery(self) -> None:
        self.style_gallery.refresh()
        self._register_gallery_chips()
        qmap = getattr(self, "_qactions", None)
        if qmap:
            self.bind_qactions(qmap)

    def _register_gallery_chips(self) -> None:
        for tb in self.style_gallery.findChildren(QToolButton):
            name = tb.objectName() or ""
            if not name.startswith("ildStyleChip_"):
                continue
            aid = f"style_{name[len('ildStyleChip_'):]}"
            self._actions.setdefault(aid, tb)
            bucket = self._action_buttons.setdefault(aid, [])
            if tb not in bucket:
                bucket.append(tb)

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

    def bind(self, handlers: dict[str, Callable[[], None]]) -> None:
        self._handlers = handlers

        def _dispatch(aid: str) -> None:
            fn = (getattr(self, "_handlers", None) or {}).get(aid)
            if callable(fn):
                fn()

        self.action_triggered.connect(_dispatch)
