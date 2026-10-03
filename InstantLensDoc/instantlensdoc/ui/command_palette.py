"""Schnellaktionen-Palette (Ctrl+K Command Palette) — 2.3.0/2.3.1.

2.3.1: Fuzzy-Filter, letzte Befehle, Esc schließt, Kategorien gruppiert.
"""

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
    """Häufige Befehle (öffnen, suchen, OCR, export, …) — Kategorien — 2.3.1."""
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
            "kompression optimize downsample jpeg preset dpi",
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


def fuzzy_score(query: str, text: str) -> int | None:
    """
    Fuzzy-Score: Teilstring > Subsequenz (Zeichen in Reihenfolge).
    None = kein Treffer. Höher = besser — 2.3.1.
    """
    q = (query or "").strip().lower()
    t = (text or "").lower()
    if not q:
        return 0
    if q in t:
        # Früher Treffer und kürzerer Text belohnen
        pos = t.find(q)
        return 1000 - pos - max(0, len(t) - len(q)) // 4
    # Subsequenz: alle Query-Zeichen in Reihenfolge
    ti = 0
    gaps = 0
    last = -1
    for ch in q:
        found = t.find(ch, ti)
        if found < 0:
            return None
        if last >= 0:
            gaps += found - last - 1
        last = found
        ti = found + 1
    return 500 - gaps - max(0, len(t) - len(q)) // 8


def match_command(query: str, cmd: PaletteCommand) -> int | None:
    """Bester Fuzzy-Score über Title/Keywords/Category/Id — 2.3.1."""
    q = (query or "").strip().lower()
    if not q:
        return 0
    best: int | None = None
    for field in (cmd.title, cmd.keywords, cmd.category, cmd.id, cmd.shortcut, cmd.haystack()):
        sc = fuzzy_score(q, field)
        if sc is None:
            continue
        if best is None or sc > best:
            best = sc
    return best


class CommandPaletteDialog(QDialog):
    """Filterbare Schnellaktionen-Palette — Ctrl+K; Fuzzy · Recent · Kategorien · Esc — 2.3.1."""

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
        self.resize(560, 420)
        self.setModal(True)
        self._commands = list(commands or default_palette_commands())
        self._runner = runner
        self._chosen_id: str | None = None
        self._by_id = {c.id: c for c in self._commands}

        layout = QVBoxLayout(self)
        hint = QLabel(
            "Tipp: tippen = Fuzzy-Filter · Enter ausführen · Esc schließen · "
            "Kategorien · letzte Befehle oben — 2.3.1"
        )
        hint.setObjectName("commandPaletteHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.filter_edit = QLineEdit()
        self.filter_edit.setObjectName("commandPaletteFilter")
        self.filter_edit.setPlaceholderText("Befehl suchen (Fuzzy)…")
        self.filter_edit.setClearButtonEnabled(True)
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

        # Esc schließt (explizit; zusätzlich Dialog-Standard) — 2.3.1
        esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc.setContext(Qt.WidgetWithChildrenShortcut)
        esc.activated.connect(self.reject)
        enter = QShortcut(QKeySequence(Qt.Key_Return), self)
        enter.activated.connect(self._activate_current)
        enter2 = QShortcut(QKeySequence(Qt.Key_Enter), self)
        enter2.activated.connect(self._activate_current)

        self._refilter()
        self.filter_edit.setFocus()

    def chosen_id(self) -> str | None:
        return self._chosen_id

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)

    def _recent_ids(self) -> list[str]:
        try:
            from instantlensdoc.core.app_settings import get_command_palette_recent

            return list(get_command_palette_recent())
        except Exception:
            return []

    def _remember(self, cmd_id: str) -> None:
        try:
            from instantlensdoc.core.app_settings import push_command_palette_recent

            push_command_palette_recent(cmd_id)
        except Exception:
            pass

    def _refilter(self, _text: str = "") -> None:
        q = (self.filter_edit.text() or "").strip()
        self.list.clear()
        recent = self._recent_ids()
        scored: list[tuple[int, PaletteCommand]] = []
        for cmd in self._commands:
            sc = match_command(q, cmd)
            if sc is None:
                continue
            scored.append((sc, cmd))

        # Ohne Query: Recent zuerst, dann nach Kategorie — 2.3.1
        if not q:
            recent_cmds = [self._by_id[i] for i in recent if i in self._by_id]
            rest = [c for c in self._commands if c.id not in {x.id for x in recent_cmds}]
            # Rest nach Kategorie, dann Titel
            cat_order = ["Datei", "Bearbeiten", "PDF", "OCR", "Ansicht", "App", "Hilfe"]
            cat_rank = {c: i for i, c in enumerate(cat_order)}

            def _sort_key(c: PaletteCommand):
                return (cat_rank.get(c.category, 99), c.category, c.title.lower())

            rest.sort(key=_sort_key)
            shown = 0
            if recent_cmds:
                hdr = QListWidgetItem("—— Letzte Befehle ——")
                hdr.setFlags(Qt.NoItemFlags)
                hdr.setData(Qt.UserRole, "")
                self.list.addItem(hdr)
                for cmd in recent_cmds:
                    self._add_cmd_item(cmd, recent_mark=True)
                    shown += 1
            # Nach Kategorie gruppieren
            last_cat = None
            for cmd in rest:
                if cmd.category != last_cat:
                    last_cat = cmd.category
                    hdr = QListWidgetItem(f"—— {cmd.category or 'Sonstiges'} ——")
                    hdr.setFlags(Qt.NoItemFlags)
                    hdr.setData(Qt.UserRole, "")
                    self.list.addItem(hdr)
                self._add_cmd_item(cmd)
                shown += 1
            self.count_label.setText(f"{shown} / {len(self._commands)}")
        else:
            scored.sort(key=lambda x: (-x[0], x[1].category, x[1].title.lower()))
            # Kategorie-Header bei Filter nur wenn gemischt
            last_cat = object()
            shown = 0
            for _sc, cmd in scored:
                if cmd.category != last_cat:
                    last_cat = cmd.category
                    hdr = QListWidgetItem(f"—— {cmd.category or 'Sonstiges'} ——")
                    hdr.setFlags(Qt.NoItemFlags)
                    hdr.setData(Qt.UserRole, "")
                    self.list.addItem(hdr)
                self._add_cmd_item(cmd)
                shown += 1
            self.count_label.setText(f"{shown} Treffer (Fuzzy)")

        # Ersten echten Befehl selektieren
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item and item.data(Qt.UserRole):
                self.list.setCurrentRow(i)
                break

    def _add_cmd_item(self, cmd: PaletteCommand, *, recent_mark: bool = False) -> None:
        label = cmd.title
        if cmd.shortcut:
            label = f"{cmd.title}  ·  {cmd.shortcut}"
        prefix = "★ " if recent_mark else ""
        if cmd.category:
            label = f"{prefix}[{cmd.category}] {label}"
        else:
            label = f"{prefix}{label}"
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, cmd.id)
        tip = f"{cmd.title}"
        if cmd.category:
            tip += f"\nKategorie: {cmd.category}"
        if cmd.shortcut:
            tip += f"\nShortcut: {cmd.shortcut}"
        if cmd.keywords:
            tip += f"\n{cmd.keywords}"
        item.setToolTip(tip.strip())
        self.list.addItem(item)

    def _activate_current(self) -> None:
        item = self.list.currentItem()
        if item is not None:
            self._activate_item(item)

    def _activate_item(self, item: QListWidgetItem) -> None:
        cid = str(item.data(Qt.UserRole) or "").strip()
        if not cid:
            return
        self._chosen_id = cid
        self._remember(cid)
        if callable(self._runner):
            try:
                self._runner(cid)
            except Exception:
                pass
        self.accept()
