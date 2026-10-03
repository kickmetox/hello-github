"""Schnellaktionen-Palette (Ctrl+K Command Palette) — 2.3.0."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)


@dataclass(frozen=True)
class PaletteCommand:
    """Ein Eintrag in der Command Palette."""

    id: str
    title: str
    keywords: str = ""
    category: str = ""
    shortcut: str = ""

    def haystack(self) -> str:
        parts = [self.title, self.keywords, self.category, self.id, self.shortcut]
        return " ".join(p for p in parts if p).lower()


def default_palette_commands() -> list[PaletteCommand]:
    """Häufige Befehle (öffnen, suchen, OCR, export, …)."""
    return [
        PaletteCommand("open", "Dokument öffnen…", "datei open öffnen", "Datei", "Ctrl+O"),
        PaletteCommand("save", "Speichern", "datei save speichern", "Datei", "Ctrl+S"),
        PaletteCommand("save_all", "Alles speichern", "speichern alle", "Datei"),
        PaletteCommand("search", "Suche (Sidebar)", "suchen find textsuche", "Bearbeiten", "Ctrl+F"),
        PaletteCommand(
            "multi_search",
            "Multi-Dokument-Suche…",
            "suchen alle docs pdf",
            "Bearbeiten",
            "Ctrl+Shift+F",
        ),
        PaletteCommand("find_replace", "Suchen/Ersetzen…", "ersetzen replace", "Bearbeiten", "Ctrl+R"),
        PaletteCommand("ocr_page", "OCR aktuelle Seite…", "ocr tesseract seite", "OCR"),
        PaletteCommand("ocr_pdf", "OCR gesamtes PDF…", "ocr batch pdf", "OCR"),
        PaletteCommand("export", "Exportieren…", "export html docx pdf", "Datei"),
        PaletteCommand("export_page_images", "Seiten als Bilder…", "export png jpeg", "PDF"),
        PaletteCommand(
            "compress",
            "PDF komprimieren / Downsample…",
            "kompression optimize downsample jpeg",
            "PDF",
        ),
        PaletteCommand("bake_links", "Link-Annotationen in PDF backen…", "link uri bake", "PDF"),
        PaletteCommand("page_labels", "Seitenbeschriftungen…", "labels pagelabels", "PDF"),
        PaletteCommand("doc_history", "Dokument-Historie…", "historie ildhist", "PDF"),
        PaletteCommand("goto_page", "Gehe zu Seite…", "seite goto", "PDF", "Ctrl+G"),
        PaletteCommand("settings", "Einstellungen…", "settings einstellungen", "App"),
        PaletteCommand("keyboard_help", "Tastaturhilfe", "hilfe shortcuts f1", "Hilfe", "F1"),
        PaletteCommand("about", "Über InstantLens Doc", "about version", "Hilfe"),
        PaletteCommand("theme_cycle", "Theme wechseln", "theme hell dunkel", "Ansicht"),
        PaletteCommand("ann_layer", "Annotation-Layer umschalten", "annotationen layer", "Ansicht"),
    ]


class CommandPaletteDialog(QDialog):
    """Filterbare Schnellaktionen-Palette — Ctrl+K."""

    def __init__(
        self,
        parent=None,
        *,
        commands: Optional[List[PaletteCommand]] = None,
        runner: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Schnellaktionen (Ctrl+K)")
        self.setObjectName("commandPalette")
        self.resize(520, 360)
        self.setModal(True)
        self._commands = list(commands or default_palette_commands())
        self._runner = runner
        self._chosen_id: str | None = None

        layout = QVBoxLayout(self)
        hint = QLabel("Tipp: tippen zum Filtern · Enter ausführen · Esc schließen — 2.3.0")
        hint.setObjectName("commandPaletteHint")
        layout.addWidget(hint)

        self.filter_edit = QLineEdit()
        self.filter_edit.setObjectName("commandPaletteFilter")
        self.filter_edit.setPlaceholderText("Befehl suchen…")
        self.filter_edit.textChanged.connect(self._refilter)
        layout.addWidget(self.filter_edit)

        self.list = QListWidget()
        self.list.setObjectName("commandPaletteList")
        self.list.itemActivated.connect(self._activate_item)
        self.list.itemDoubleClicked.connect(self._activate_item)
        layout.addWidget(self.list)

        foot = QHBoxLayout()
        self.count_label = QLabel("")
        self.count_label.setObjectName("commandPaletteCount")
        foot.addWidget(self.count_label)
        foot.addStretch(1)
        layout.addLayout(foot)

        esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc.activated.connect(self.reject)
        enter = QShortcut(QKeySequence(Qt.Key_Return), self)
        enter.activated.connect(self._activate_current)
        enter2 = QShortcut(QKeySequence(Qt.Key_Enter), self)
        enter2.activated.connect(self._activate_current)

        self._refilter()
        self.filter_edit.setFocus()

    def chosen_id(self) -> str | None:
        return self._chosen_id

    def _refilter(self, _text: str = "") -> None:
        q = (self.filter_edit.text() or "").strip().lower()
        self.list.clear()
        shown = 0
        for cmd in self._commands:
            if q and q not in cmd.haystack():
                continue
            label = cmd.title
            if cmd.shortcut:
                label = f"{cmd.title}  ·  {cmd.shortcut}"
            if cmd.category:
                label = f"[{cmd.category}] {label}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, cmd.id)
            item.setToolTip(f"{cmd.title}\n{cmd.keywords}".strip())
            self.list.addItem(item)
            shown += 1
        self.count_label.setText(f"{shown} / {len(self._commands)}")
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    def _activate_current(self) -> None:
        item = self.list.currentItem()
        if item is not None:
            self._activate_item(item)

    def _activate_item(self, item: QListWidgetItem) -> None:
        cid = str(item.data(Qt.UserRole) or "").strip()
        if not cid:
            return
        self._chosen_id = cid
        if callable(self._runner):
            try:
                self._runner(cid)
            except Exception:
                pass
        self.accept()
