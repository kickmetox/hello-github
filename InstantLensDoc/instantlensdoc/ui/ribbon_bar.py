"""Ribbon-ähnliche Werkzeugleiste — 2.6.52 (Geräte/Scan + F12/Save-as, Alt-Parity)."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
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


class RibbonBar(QWidget):
    """
    Ribbon-Chrome: Kategorie-Tabs + Button-Zeile.
    Tabs: Start / Bearbeiten / Review / Ansicht / Fenster / PDF / Geräte / DTP — 2.6.54.
    Alt+1…8 wählt Kategorien (Office-ähnliche Alt-Parity, vereinfacht).
    """

    action_triggered = Signal(str)  # action id

    # Alt-Mnemonic → Kategorie-Index (Smoke/Alt-Ribbon) — Geräte = 7 — 2.6.51
    ALT_CATEGORY_KEYS = ("1", "2", "3", "4", "5", "6", "7", "8")

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
        # Alle Buttons je Aktion (undo/redo liegen in Start **und** Bearbeiten) — 2.6.54
        self._action_buttons: dict[str, list[QToolButton]] = {}

        panels = (
                (
                    "Start",
                    (
                        ("open", "Öffnen"),
                        ("save", "Speichern"),
                        ("save_as", "Speichern unter"),
                        ("undo", "↶ Rückgängig"),
                        ("redo", "↷ Wiederholen"),
                        ("bold", "Fett"),
                        ("italic", "Kursiv"),
                        ("underline", "Unterstrichen"),
                        ("strike", "Durchgestrichen"),
                        ("highlight", "Textmarker"),
                        ("align_left", "Links"),
                        ("align_center", "Zentriert"),
                        ("align_right", "Rechts"),
                        ("align_justify", "Blocksatz"),
                        ("bullet_list", "Aufzählung"),
                        ("numbered_list", "Nummerierung"),
                        ("paragraph", "Absatz…"),
                        ("clear_formatting", "Format löschen"),
                        ("compare_pdfs", "Vergleichen"),
                        ("find_replace", "Suchen"),
                        ("spellcheck", "Rechtschreibung"),
                    ),
                ),
                (
                    "Bearbeiten",
                    (
                        ("undo", "↶ Rückgängig"),
                        ("redo", "↷ Wiederholen"),
                        ("spellcheck", "Rechtschreibung"),
                        ("find_replace", "Suchen/Ersetzen"),
                        ("insert_hyperlink", "Hyperlink"),
                        ("insert_table", "Tabelle"),
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
                    ),
                ),
            (
                "Review",
                (
                    ("review_mode", "Änderungen"),
                    ("doc_comments", "Kommentare"),
                    ("shared_review", "Gemeinsam"),
                    ("version_history", "Versionen"),
                    ("mail_merge", "Seriendruck"),
                ),
            ),
            (
                "Ansicht",
                (
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
            ),
            (
                "Fenster",
                (
                    ("doc_split", "Teilen"),
                    ("detach_window", "Separates Fenster"),
                    ("toggle_doc_tabs", "Tabs"),
                ),
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
            ),
            (
                "Geräte",
                (
                    ("scan_import", "Scannen…"),
                    ("devices_printers", "Drucker…"),
                    ("devices_discover", "Geräte erkennen…"),
                    ("devices_refresh", "Neu suchen"),
                ),
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
            ),
        )

        for i, (title, buttons) in enumerate(panels):
            # Alt-Parity: sichtbarer Shortcut-Hinweis in Tooltip
            mnemonic = self.ALT_CATEGORY_KEYS[i] if i < len(self.ALT_CATEGORY_KEYS) else ""
            btn = QPushButton(title)
            btn.setObjectName("ribbonCat")
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            tip = f"{title} — Ribbon 2.6.54"
            if mnemonic:
                tip += f" (Alt+{mnemonic})"
            btn.setToolTip(tip)
            btn.setProperty("altMnemonic", mnemonic)
            btn.clicked.connect(lambda _=False, idx=i: self._select_cat(idx))
            cats.addWidget(btn)
            self._cat_buttons.append(btn)

            panel = QFrame()
            # Ribbon darf die Fenster-Mindestbreite nicht diktieren (13 Buttons
            # ≈ 1350 px): rechts überzählige Buttons werden geclippt — 2.6.52
            panel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            row = QHBoxLayout(panel)
            row.setContentsMargins(4, 2, 4, 2)
            row.setSpacing(4)
            for aid, label in buttons:
                tb = QToolButton()
                tb.setText(label)
                tb.setObjectName(f"ribbonAction_{aid}")
                tb.setToolTip(f"{label} — Ribbon 2.6.54")
                tb.setAutoRaise(False)
                if aid in (
                    "book_layout",
                    "page_by_page",
                    "continuous_scroll",
                    "toggle_doc_tabs",
                    "autocorrect_toggle",
                    "doc_split",
                    "toggle_ribbon",
                    "review_mode",
                ):
                    tb.setCheckable(True)
                if aid in ("undo", "redo"):
                    # Sichtbare Pfeile „vor/zurück“; Enabled-Zustand folgt Editor-
                    # bzw. PDF-Undo-Stack (MainWindow._sync_undo_redo_ui) — 2.6.54
                    icon = self.style().standardIcon(
                        QStyle.SP_ArrowBack if aid == "undo" else QStyle.SP_ArrowForward
                    )
                    tb.setIcon(icon)
                    tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
                    tb.setToolTip(
                        "Rückgängig (Ctrl+Z)" if aid == "undo" else "Wiederholen (Ctrl+Y / Ctrl+Shift+Z)"
                    )
                tb.clicked.connect(
                    lambda _checked=False, a=aid: self.action_triggered.emit(a)
                )
                self._actions.setdefault(aid, tb)
                self._action_buttons.setdefault(aid, []).append(tb)
                row.addWidget(tb)
            row.addStretch(1)
            self._stack.addWidget(panel)

        cats.addStretch(1)
        root.addLayout(cats)
        root.addWidget(self._stack)
        self._select_cat(0)
        self._install_alt_shortcuts()

    def _install_alt_shortcuts(self) -> None:
        """Alt+1…8 → Ribbon-Kategorie (praktische Alt-Parity) — 2.6.54."""
        self._alt_shortcuts: list[QShortcut] = []
        for i, key in enumerate(self.ALT_CATEGORY_KEYS):
            sc = QShortcut(QKeySequence(f"Alt+{key}"), self)
            sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
            sc.activated.connect(lambda idx=i: self.select_category(idx))
            self._alt_shortcuts.append(sc)

    def _select_cat(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        for i, b in enumerate(self._cat_buttons):
            b.blockSignals(True)
            b.setChecked(i == index)
            b.blockSignals(False)

    def select_category(self, index: int) -> None:
        """Öffentliche Kategorie-Wahl (Smoke/Alt-Ribbon)."""
        if 0 <= index < self._stack.count():
            self._select_cat(index)

    def category_count(self) -> int:
        return self._stack.count()

    def set_checked(self, action_id: str, checked: bool) -> None:
        btn = self._actions.get(action_id)
        if btn is not None and btn.isCheckable():
            btn.blockSignals(True)
            btn.setChecked(bool(checked))
            btn.blockSignals(False)

    def set_enabled(self, action_id: str, enabled: bool) -> None:
        """Alle Buttons einer Aktion (in allen Tabs) aktivieren/deaktivieren — 2.6.54."""
        for btn in self._action_buttons.get(action_id, ()):
            btn.setEnabled(bool(enabled))

    def is_enabled(self, action_id: str) -> bool:
        btns = self._action_buttons.get(action_id, ())
        return bool(btns) and all(b.isEnabled() for b in btns)

    def buttons(self, action_id: str) -> list[QToolButton]:
        return list(self._action_buttons.get(action_id, ()))

    def set_action_enabled(self, action_id: str, enabled: bool) -> None:
        """Alias für PDF-Undo-Tooltips / Annotation-Tests — 2.6.54."""
        self.set_enabled(action_id, enabled)

    def set_action_tooltip(self, action_id: str, text: str) -> None:
        tip = str(text or "")
        for tb in self._action_buttons.get(action_id, ()) or ():
            try:
                tb.setToolTip(tip)
            except Exception:
                pass

    def bind(self, handlers: dict[str, Callable[[], None]]) -> None:
        """Optional: direkte Handler statt Signal (Smoke/Tests)."""
        self._handlers = handlers

        def _dispatch(aid: str) -> None:
            fn = (getattr(self, "_handlers", None) or {}).get(aid)
            if callable(fn):
                fn()

        self.action_triggered.connect(_dispatch)
