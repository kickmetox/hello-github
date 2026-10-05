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
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class RibbonBar(QWidget):
    """
    Ribbon-Chrome: Kategorie-Tabs + Button-Zeile.
    Tabs: Start / Bearbeiten / Review / Ansicht / Fenster / PDF / Geräte — 2.6.51.
    Alt+1…7 wählt Kategorien (Office-ähnliche Alt-Parity, vereinfacht).
    """

    action_triggered = Signal(str)  # action id

    # Alt-Mnemonic → Kategorie-Index (Smoke/Alt-Ribbon) — Geräte = 7 — 2.6.51
    ALT_CATEGORY_KEYS = ("1", "2", "3", "4", "5", "6", "7")

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

        panels = (
            (
                "Start",
                (
                    ("open", "Öffnen"),
                    ("save", "Speichern"),
                    ("save_as", "Speichern unter"),
                    ("compare_pdfs", "Vergleichen"),
                    ("find_replace", "Suchen"),
                    ("spellcheck", "Rechtschreibung"),
                ),
            ),
            (
                "Bearbeiten",
                (
                    ("undo", "Rückgängig"),
                    ("redo", "Wiederholen"),
                    ("spellcheck", "Rechtschreibung"),
                    ("autocorrect_toggle", "Autokorrektur"),
                    ("insert_snippet", "Baustein"),
                    ("find_replace", "Suchen/Ersetzen"),
                    ("auto_toc", "Inhaltsverz."),
                    ("auto_lof", "Abbildungsverz."),
                    ("auto_index", "Stichwortverz."),
                    ("insert_hyperlink", "Hyperlink"),
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
                    ("book_layout", "Buch-Layout"),
                    ("page_by_page", "Seite-für-Seite"),
                    ("continuous_scroll", "Continuous"),
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
                    ("apply_bleed", "Bleed"),
                    ("export_pdfx", "PDF/X"),
                    ("scan_import", "Scannen…"),
                    ("devices_discover", "Geräte erkennen"),
                ),
            ),
            (
                "Geräte",
                (
                    ("scan_import", "Scanner / Scannen…"),
                    ("devices_printers", "Drucker…"),
                    ("devices_discover", "Geräte erkennen…"),
                    ("devices_refresh", "Neu suchen"),
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
            tip = f"{title} — Ribbon 2.6.52"
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
                tb.setToolTip(f"{label} — Ribbon 2.6.52")
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
                tb.clicked.connect(
                    lambda _checked=False, a=aid: self.action_triggered.emit(a)
                )
                self._actions.setdefault(aid, tb)
                row.addWidget(tb)
            row.addStretch(1)
            self._stack.addWidget(panel)

        cats.addStretch(1)
        root.addLayout(cats)
        root.addWidget(self._stack)
        self._select_cat(0)
        self._install_alt_shortcuts()

    def _install_alt_shortcuts(self) -> None:
        """Alt+1…7 → Ribbon-Kategorie (praktische Alt-Parity) — 2.6.51."""
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

    def bind(self, handlers: dict[str, Callable[[], None]]) -> None:
        """Optional: direkte Handler statt Signal (Smoke/Tests)."""
        self._handlers = handlers

        def _dispatch(aid: str) -> None:
            fn = (getattr(self, "_handlers", None) or {}).get(aid)
            if callable(fn):
                fn()

        self.action_triggered.connect(_dispatch)
