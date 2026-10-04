"""Schnellaktionen-Palette (Ctrl+K Command Palette) — 2.3.0–2.3.5 / 2.6.29.

2.3.1: Fuzzy-Filter, letzte Befehle, Esc schließt, Kategorien gruppiert.
2.3.2: Pin häufige Befehle · Recent-Anzahl Settings 5/10/20.
2.3.3: Pin-Persistenz · Unpin · max Pins Settings 3/5/10.
2.3.4: Overflow-Hinweis bei Pin-Limit · Option ältesten Pin ersetzen.
2.3.5: Pin-ersetzen-Bestätigung mit Namen des zu ersetzenden Pins.
2.6.29: Silbentrennung-Befehle für alle 9 UI-Sprachen (FR/RU/ES/ZH/PT/AR/IT).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
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
        PaletteCommand(
            "find_replace",
            "Suchen/Ersetzen…",
            "ersetzen replace finden",
            "Bearbeiten",
            "Ctrl+H",
        ),
        PaletteCommand(
            "toggle_bold",
            "Fett",
            "bold fett format",
            "Bearbeiten",
            "Ctrl+B",
        ),
        PaletteCommand(
            "toggle_italic",
            "Kursiv",
            "italic kursiv format",
            "Bearbeiten",
            "Ctrl+I",
        ),
        PaletteCommand(
            "toggle_underline",
            "Unterstrichen",
            "underline unterstrichen format",
            "Bearbeiten",
            "Ctrl+U",
        ),
        PaletteCommand(
            "auto_format",
            "Automatische Formatierung",
            "auto format styles überschrift heading preset",
            "Bearbeiten",
            "Ctrl+Alt+Shift+F",
        ),
        PaletteCommand(
            "auto_toc",
            "Inhaltsverzeichnis aktualisieren",
            "toc inhaltsverzeichnis outline verzeichnis",
            "Bearbeiten",
            "Ctrl+Alt+Shift+T",
        ),
        PaletteCommand(
            "auto_lof",
            "Abbildungsverzeichnis aktualisieren",
            "lof abbildungsverzeichnis figure caption verzeichnis",
            "Bearbeiten",
            "Ctrl+Alt+Shift+A",
        ),
        PaletteCommand(
            "auto_index",
            "Stichwortverzeichnis aktualisieren",
            "index stichwortverzeichnis keywords verzeichnis",
            "Bearbeiten",
            "Ctrl+Alt+Shift+X",
        ),
        PaletteCommand(
            "save_as",
            "Speichern unter…",
            "save as speichern unter f12",
            "Datei",
            "F12",
        ),
        PaletteCommand(
            "para_align_left",
            "Absatz links",
            "absatz align left ausrichtung",
            "Bearbeiten",
            "Ctrl+L",
        ),
        PaletteCommand(
            "para_align_center",
            "Absatz zentriert",
            "absatz align center zentriert",
            "Bearbeiten",
            "Ctrl+E",
        ),
        PaletteCommand(
            "para_align_right",
            "Absatz rechts",
            "absatz align right rechts",
            "Bearbeiten",
            "Ctrl+R",
        ),
        PaletteCommand(
            "para_align_justify",
            "Absatz Blocksatz",
            "absatz align justify blocksatz",
            "Bearbeiten",
            "Ctrl+J",
        ),
        PaletteCommand(
            "toggle_rulers",
            "Lineal ein/aus",
            "lineal ruler horizontal vertikal",
            "Ansicht",
            "Ctrl+Alt+R",
        ),
        PaletteCommand(
            "toggle_grid",
            "Ausrichtungsraster ein/aus",
            "raster grid guides ausrichtung",
            "Ansicht",
            "Ctrl+Alt+G",
        ),
        PaletteCommand(
            "toggle_satzspiegel",
            "Satzspiegel ein/aus",
            "satzspiegel type area margins ränder",
            "Ansicht",
            "Ctrl+Alt+S",
        ),
        PaletteCommand(
            "apply_master_page",
            "Musterseite anwenden…",
            "musterseite master page kopf fuß seitenzahl",
            "Einfügen",
        ),
        PaletteCommand(
            "add_column_frames",
            "Spalten-Rahmen…",
            "spalten rahmen verkettung columns frames",
            "Einfügen",
        ),
        PaletteCommand(
            "move_frame",
            "Rahmen verschieben…",
            "rahmen verschieben move frame box",
            "Einfügen",
        ),
        PaletteCommand(
            "resize_frame",
            "Rahmen skalieren…",
            "rahmen skalieren resize frame box",
            "Einfügen",
        ),
        PaletteCommand(
            "typo_tracking",
            "Laufweite / Tracking +50",
            "tracking laufweite typografie letterspacing",
            "Bearbeiten",
        ),
        PaletteCommand(
            "typo_leading",
            "Durchschuss / Leading 1,5",
            "leading durchschuss zeilenabstand typografie",
            "Bearbeiten",
        ),
        PaletteCommand(
            "drop_cap",
            "Initial / Drop Cap",
            "drop cap initial versalbuchstabe typografie",
            "Bearbeiten",
            "Ctrl+Alt+Shift+D",
        ),
        PaletteCommand(
            "hyphenate_de",
            "Silbentrennung (DE)",
            "silbentrennung hyphenation deutsch de",
            "Bearbeiten",
            "Ctrl+Alt+Shift+H",
        ),
        PaletteCommand(
            "hyphenate_en",
            "Silbentrennung (EN)",
            "hyphenation english silbentrennung en",
            "Bearbeiten",
        ),
        PaletteCommand(
            "hyphenate_fr",
            "Silbentrennung (FR)",
            "hyphenation francais silbentrennung fr",
            "Bearbeiten",
        ),
        PaletteCommand(
            "hyphenate_ru",
            "Silbentrennung (RU)",
            "hyphenation russian silbentrennung ru",
            "Bearbeiten",
        ),
        PaletteCommand(
            "hyphenate_es",
            "Silbentrennung (ES)",
            "hyphenation espanol silbentrennung es",
            "Bearbeiten",
        ),
        PaletteCommand(
            "hyphenate_zh",
            "Silbentrennung (ZH, no-break)",
            "hyphenation chinese silbentrennung zh cjk",
            "Bearbeiten",
        ),
        PaletteCommand(
            "hyphenate_pt",
            "Silbentrennung (PT)",
            "hyphenation portugues silbentrennung pt",
            "Bearbeiten",
        ),
        PaletteCommand(
            "hyphenate_ar",
            "Silbentrennung (AR, no-break)",
            "hyphenation arabic silbentrennung ar",
            "Bearbeiten",
        ),
        PaletteCommand(
            "hyphenate_it",
            "Silbentrennung (IT)",
            "hyphenation italiano silbentrennung it",
            "Bearbeiten",
        ),
        PaletteCommand(
            "text_wrap",
            "Textumfluss um Bildrahmen…",
            "textumfluss wrap image shape contour bounding",
            "Einfügen",
        ),
        PaletteCommand(
            "insert_table",
            "Tabelle einfügen…",
            "tabelle table erstellen grid",
            "Einfügen",
            "Ctrl+Alt+Shift+T",
        ),
        PaletteCommand(
            "format_table",
            "Tabelle formatieren…",
            "tabelle format align stil border",
            "Einfügen",
        ),
        PaletteCommand(
            "sort_table",
            "Tabelle sortieren…",
            "tabelle sortieren sort column",
            "Einfügen",
        ),
        PaletteCommand(
            "import_table_data",
            "Zahlen/Daten importieren (CSV/Excel)…",
            "csv excel xlsx import tabelle daten",
            "Einfügen",
        ),
        PaletteCommand(
            "export_xlsx",
            "Als XLSX exportieren…",
            "export excel xlsx tabelle",
            "Datei",
        ),
        PaletteCommand(
            "export_rtf",
            "Als RTF exportieren…",
            "export rtf rich text",
            "Datei",
        ),
        PaletteCommand(
            "export_epub",
            "Als EPUB exportieren…",
            "export epub ebook e-book hyperlink kapitel",
            "Datei",
        ),
        PaletteCommand(
            "export_pptx",
            "Als PPTX exportieren…",
            "export pptx powerpoint presentation folie slides",
            "Datei",
        ),
        PaletteCommand(
            "insert_hyperlink",
            "Hyperlink einfügen…",
            "hyperlink link url anker bookmark website",
            "Einfügen",
            "Ctrl+Shift+K",
        ),
        PaletteCommand(
            "insert_shape",
            "Form einfügen…",
            "shape form rectangle ellipse dreieck grafik",
            "Einfügen",
        ),
        PaletteCommand(
            "insert_video",
            "Video-Platzhalter (URL)…",
            "video online youtube url placeholder medien",
            "Einfügen",
        ),
        PaletteCommand(
            "scale_image",
            "Bild skalieren…",
            "scale skalieren bild grafik medien",
            "Einfügen",
        ),
        PaletteCommand(
            "crop_image",
            "Bild zuschneiden…",
            "crop zuschneiden bild grafik medien",
            "Einfügen",
        ),
        PaletteCommand(
            "export_pdfx",
            "Als PDF/X (druckreif)…",
            "export pdfx print ready druckreif anschnitt bleed cmyk",
            "Datei",
        ),
        PaletteCommand(
            "preflight",
            "Preflight (Druckprüfung)…",
            "preflight druck prüfung schriften auflösung dpi bleed fehlend",
            "PDF",
        ),
        PaletteCommand(
            "apply_bleed",
            "Anschnitt / Bleed setzen…",
            "bleed anschnitt trimbox bleedbox druck",
            "PDF",
        ),
        PaletteCommand(
            "doc_layers",
            "Dokument-Ebenen…",
            "ebenen layers hintergrund bilder text rahmen",
            "PDF",
        ),
        PaletteCommand(
            "compare_pdfs",
            "Zwei PDFs vergleichen…",
            "compare vergleich diff sync scroll drag drop dokumentvergleich",
            "PDF",
            "Ctrl+Alt+Shift+V",
        ),
        PaletteCommand(
            "book_layout",
            "Buch-Layout (Book Layout)",
            "book layout buch doppelseite cover spread",
            "Ansicht",
            "Ctrl+Alt+2",
        ),
        PaletteCommand(
            "page_by_page",
            "Seite-für-Seite-Scrollen",
            "page scroll blättern einzelseite",
            "Ansicht",
            "Ctrl+Alt+3",
        ),
        PaletteCommand(
            "toggle_doc_tabs",
            "Dokument-Tabs ein/aus",
            "tabs dokumente ribbon workspace",
            "Ansicht",
        ),
        PaletteCommand(
            "toggle_ribbon",
            "Ribbon-Leiste ein/aus",
            "ribbon toolbar chrome workspace",
            "Ansicht",
        ),
        PaletteCommand(
            "spellcheck",
            "Rechtschreibung prüfen…",
            "spellcheck rechtschreibung vorschläge grammar wörterbuch f7",
            "Bearbeiten",
            "F7",
        ),
        PaletteCommand(
            "spell_suggestions",
            "Rechtschreibvorschläge…",
            "spell suggestions korrektur vorschläge shift+f7",
            "Bearbeiten",
            "Shift+F7",
        ),
        PaletteCommand(
            "autocorrect_toggle",
            "Autokorrektur ein/aus",
            "autocorrect autokorrektur tippfehler bausteine kürzel",
            "Bearbeiten",
        ),
        PaletteCommand(
            "detach_window",
            "Dokument in separatem Fenster",
            "detach window separates fenster tabs workspace",
            "Fenster",
        ),
        PaletteCommand(
            "review_mode",
            "Review / Änderungen nachverfolgen…",
            "review track changes änderungen nachverfolgen accept reject",
            "Review",
            "Ctrl+Shift+E",
        ),
        PaletteCommand(
            "doc_comments",
            "Kommentare…",
            "comments kommentare feedback anker textstelle",
            "Review",
            "Ctrl+Alt+M",
        ),
        PaletteCommand(
            "version_history",
            "Versionsverlauf…",
            "version history versionsverlauf snapshot restore wiederherstellen",
            "Review",
            "Ctrl+Alt+Shift+H",
        ),
        PaletteCommand(
            "mail_merge",
            "Seriendruck…",
            "mail merge seriendruck csv excel empfänger briefe vorschau",
            "Review",
        ),
        PaletteCommand(
            "shared_review",
            "Gemeinsames Review / Cloud-Ordner…",
            "shared review cloud sync freigabeordner kollaboration kommentare stempel highlights",
            "Review",
            "Ctrl+Alt+Shift+C",
        ),
        PaletteCommand(
            "batch_pdf",
            "Stapelverarbeitung (Batch)…",
            "batch stapel convert watermark compress encrypt pdf ordner",
            "PDF",
        ),
        PaletteCommand(
            "esign",
            "Digitale Signatur (eIDAS)…",
            "esign signature signatur zertifikat eidas aes qes p12",
            "PDF",
            "Ctrl+Alt+Shift+G",
        ),
        PaletteCommand("ocr_page", "OCR aktuelle Seite…", "ocr tesseract seite", "OCR"),
        PaletteCommand("ocr_pdf", "OCR gesamtes PDF…", "ocr batch pdf", "OCR"),
        PaletteCommand(
            "ocr_region",
            "OCR Region (Rechteck)…",
            "ocr region rechteck crop bereich",
            "OCR",
        ),
        PaletteCommand(
            "ocr_word_suite",
            "In Word-Suite öffnen/übernehmen…",
            "ocr word suite ildocr übernehmen handoff editierbar sidecar",
            "OCR",
            "Ctrl+Alt+Shift+W",
        ),
        PaletteCommand(
            "ocr_handwriting",
            "Handschriftenerkennung…",
            "ocr handwriting handschrift psm tesseract schreiben",
            "OCR",
        ),
        PaletteCommand(
            "ki_document_wizard",
            "Dokument erstellen… (KI-Wizard)",
            "ki wizard formular anschreiben kaufvertrag rechnung dokument erstellen isoliert",
            "KI",
            "Ctrl+Alt+Shift+Q",
        ),
        PaletteCommand(
            "settings_ui_lang",
            "Einstellungen… (Oberflächensprache)",
            "settings sprache language i18n locale ui lang deutsch english français",
            "Extras",
        ),
        PaletteCommand(
            "doc_tags",
            "Dokument-Tags…",
            "tags ildtags dokument label filter",
            "PDF",
        ),
        PaletteCommand(
            "true_redact",
            "Echt schwärzen…",
            "schwärzen redaction redact meta content-stream unwiderruflich",
            "PDF",
        ),
        PaletteCommand(
            "selection_redact",
            "Auswahl → Schwärzung",
            "schwärzen auswahl text redaction",
            "PDF",
        ),
        PaletteCommand(
            "page_manage",
            "Seitenmanagement…",
            "seiten ordnen drag drehen löschen einfügen zusammenfügen merge reorder",
            "PDF",
            "Ctrl+Shift+M",
        ),
        PaletteCommand(
            "scan_import",
            "Scannen / Import…",
            "scan scanner import ocr tesseract wia twain bild foto seite",
            "PDF",
            "Ctrl+Alt+Shift+I",
        ),
        PaletteCommand(
            "devices",
            "Drucker & Scanner…",
            "drucker scanner geräte network wia twain print refresh",
            "PDF",
        ),
        PaletteCommand(
            "inline_text_edit",
            "Text bearbeiten…",
            "inline text edit schrift font reflow formatabgleich bearbeiten",
            "PDF",
            "Ctrl+Alt+Shift+E",
        ),
        PaletteCommand(
            "selection_text_edit",
            "Auswahl → Text bearbeiten",
            "auswahl text edit inline löschen ändern font",
            "PDF",
        ),
        PaletteCommand(
            "object_edit",
            "Objekt bearbeiten…",
            "objekt bild vektor tabelle verschieben skalieren spiegeln ersetzen",
            "PDF",
            "Ctrl+Alt+Shift+O",
        ),
        PaletteCommand(
            "object_transform",
            "Objekt-Dialog…",
            "objekt dialog flip spiegeln ersetzen transform",
            "PDF",
        ),
        PaletteCommand(
            "form_fields",
            "Formularfelder…",
            "formular acroform felder ausfüllen checkbox dropdown create",
            "PDF",
            "Ctrl+Alt+Shift+K",
        ),
        PaletteCommand(
            "form_field_create",
            "Formularfeld anlegen…",
            "formular feld anlegen text checkbox dropdown rechteck",
            "PDF",
        ),
        PaletteCommand(
            "form_field_detect",
            "Formularfelder erkennen…",
            "formular erkennen detect label underscore checkbox",
            "PDF",
        ),
        PaletteCommand(
            "pdf_security",
            "Verschlüsselung & Rechte…",
            "passwort encrypt aes256 rechte druck kopieren security entsperren",
            "PDF",
            "Ctrl+Alt+Shift+P",
        ),
        PaletteCommand(
            "pdf_encrypt",
            "PDF verschlüsseln…",
            "passwort setzen encrypt aes verschlüsseln",
            "PDF",
        ),
        PaletteCommand(
            "pdf_decrypt",
            "PDF entschlüsseln…",
            "passwort entfernen decrypt entsperren unlock",
            "PDF",
        ),
        PaletteCommand(
            "paragraph_highlight",
            "Absatz-Highlight…",
            "annotation highlight absatz paragraph textabschnitt markieren",
            "PDF",
        ),
        PaletteCommand(
            "stamp_pick",
            "Stempel setzen…",
            "stempel paid bezahlt rechnung datum custom stamp",
            "PDF",
        ),
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
        PaletteCommand(
            "ann_templates",
            "Annotation-Vorlagen…",
            "vorlagen templates ildtmpl stempel highlight",
            "PDF",
        ),
        PaletteCommand(
            "keyboard_help",
            "Tastatur-Cheat-Sheet",
            "hilfe shortcuts f1 cheat-sheet tastatur",
            "Hilfe",
            "F1",
        ),
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
    """Filterbare Schnellaktionen — Fuzzy · Pin/Unpin · Overflow · Esc — 2.3.4."""

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
        self.resize(560, 440)
        self.setModal(True)
        self._commands = list(commands or default_palette_commands())
        self._runner = runner
        self._chosen_id: str | None = None
        self._by_id = {c.id: c for c in self._commands}

        layout = QVBoxLayout(self)
        hint = QLabel(
            "Tipp: tippen = Fuzzy · Enter ausführen · Esc schließen · "
            "Rechtsklick = Anheften/Unpin · Pins persistiert · "
            "max Pins 3/5/10 · bei Limit: Overflow-Hinweis + ältesten ersetzen — 2.3.4"
        )
        hint.setObjectName("commandPaletteHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.pin_overflow_hint = QLabel("")
        self.pin_overflow_hint.setObjectName("commandPalettePinOverflow")
        self.pin_overflow_hint.setWordWrap(True)
        self.pin_overflow_hint.setStyleSheet("color: #8a6d00; font-weight: 600;")
        self.pin_overflow_hint.setAccessibleName("Pin-Limit Overflow-Hinweis")
        self.pin_overflow_hint.hide()
        layout.addWidget(self.pin_overflow_hint)

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
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context_menu)
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

    def _pinned_ids(self) -> list[str]:
        try:
            from instantlensdoc.core.app_settings import get_command_palette_pinned

            return list(get_command_palette_pinned())
        except Exception:
            return []

    def _remember(self, cmd_id: str) -> None:
        try:
            from instantlensdoc.core.app_settings import push_command_palette_recent

            push_command_palette_recent(cmd_id)
        except Exception:
            pass

    def _pin_limit(self) -> int:
        try:
            from instantlensdoc.core.app_settings import get_command_palette_pin_max

            return int(get_command_palette_pin_max())
        except Exception:
            return 5

    def _update_pin_overflow_hint(self) -> None:
        """Overflow-Hinweis wenn Pin-Limit erreicht — 2.3.5."""
        try:
            from instantlensdoc.core.app_settings import command_palette_pins_at_limit

            at_limit = bool(command_palette_pins_at_limit())
        except Exception:
            at_limit = False
        if at_limit:
            lim = self._pin_limit()
            msg = (
                f"Pin-Limit erreicht ({lim}). "
                "Neuer Pin: ältesten ersetzen oder zuerst Unpin — 2.3.5"
            )
            self.pin_overflow_hint.setText(msg)
            self.pin_overflow_hint.setToolTip(msg)
            self.pin_overflow_hint.setAccessibleName(msg)
            self.pin_overflow_hint.show()
        else:
            self.pin_overflow_hint.clear()
            self.pin_overflow_hint.setAccessibleName("Pin-Limit Overflow-Hinweis")
            self.pin_overflow_hint.hide()

    def _context_menu(self, pos) -> None:
        item = self.list.itemAt(pos)
        if item is None:
            return
        cid = str(item.data(Qt.UserRole) or "").strip()
        if not cid:
            return
        pinned = set(self._pinned_ids())
        menu = QMenu(self)
        if cid in pinned:
            act = QAction("Unpin (Pin entfernen)", self)
            act.setObjectName("commandPaletteUnpin")
            act.setToolTip("Pin lösen — Persistenz Settings — 2.3.4")
            act.triggered.connect(lambda: self._toggle_pin(cid))
        else:
            at_limit = len(pinned) >= self._pin_limit()
            if at_limit:
                act = QAction("Anheften (ältesten Pin ersetzen)…", self)
                act.setObjectName("commandPalettePinReplaceOldest")
                act.setToolTip(
                    "Pin-Limit erreicht — Bestätigung mit Namen des zu "
                    "ersetzenden Pins — 2.3.5"
                )
            else:
                act = QAction("Anheften (häufiger Befehl)", self)
                act.setObjectName("commandPalettePin")
                act.setToolTip(
                    "Anheften — Persistenz · max Pins Settings — 2.3.4"
                )
            act.triggered.connect(lambda: self._toggle_pin(cid))
        menu.addAction(act)
        menu.exec(self.list.mapToGlobal(pos))

    def _toggle_pin(self, cmd_id: str) -> None:
        """Pin/Unpin; bei Limit Bestätigung mit Namen des zu ersetzenden Pins — 2.3.5."""
        try:
            from instantlensdoc.core.app_settings import (
                get_command_palette_pin_max,
                get_command_palette_pinned,
                toggle_command_palette_pin,
            )

            pinned = list(get_command_palette_pinned())
            if cmd_id in pinned:
                toggle_command_palette_pin(cmd_id)
            else:
                result = toggle_command_palette_pin(cmd_id, replace_oldest=False)
                if result is None:
                    limit = int(get_command_palette_pin_max())
                    oldest = pinned[-1] if pinned else ""
                    oldest_title = (
                        self._by_id[oldest].title
                        if oldest in self._by_id
                        else (oldest or "—")
                    )
                    new_title = (
                        self._by_id[cmd_id].title
                        if cmd_id in self._by_id
                        else (cmd_id or "—")
                    )
                    reply = QMessageBox.question(
                        self,
                        "Pin ersetzen",
                        (
                            f"Pin-Limit ({limit}) erreicht.\n\n"
                            f"Pin „{oldest_title}“ durch „{new_title}“ ersetzen?\n\n"
                            f"Zu ersetzender Pin: {oldest_title}"
                        ),
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes,
                    )
                    if reply == QMessageBox.Yes:
                        toggle_command_palette_pin(cmd_id, replace_oldest=True)
        except Exception:
            pass
        self._update_pin_overflow_hint()
        self._refilter()

    def _refilter(self, _text: str = "") -> None:
        q = (self.filter_edit.text() or "").strip()
        self.list.clear()
        recent = self._recent_ids()
        pinned = self._pinned_ids()
        scored: list[tuple[int, PaletteCommand]] = []
        for cmd in self._commands:
            sc = match_command(q, cmd)
            if sc is None:
                continue
            scored.append((sc, cmd))

        # Ohne Query: Pinned → Recent → Kategorie — 2.3.2
        if not q:
            pinned_cmds = [self._by_id[i] for i in pinned if i in self._by_id]
            pinned_set = {c.id for c in pinned_cmds}
            recent_cmds = [
                self._by_id[i]
                for i in recent
                if i in self._by_id and i not in pinned_set
            ]
            used = pinned_set | {c.id for c in recent_cmds}
            rest = [c for c in self._commands if c.id not in used]
            cat_order = ["Datei", "Bearbeiten", "PDF", "OCR", "Ansicht", "App", "Hilfe"]
            cat_rank = {c: i for i, c in enumerate(cat_order)}

            def _sort_key(c: PaletteCommand):
                return (cat_rank.get(c.category, 99), c.category, c.title.lower())

            rest.sort(key=_sort_key)
            shown = 0
            if pinned_cmds:
                hdr = QListWidgetItem("—— Angeheftet ——")
                hdr.setFlags(Qt.NoItemFlags)
                hdr.setData(Qt.UserRole, "")
                self.list.addItem(hdr)
                for cmd in pinned_cmds:
                    self._add_cmd_item(cmd, pinned_mark=True)
                    shown += 1
            if recent_cmds:
                hdr = QListWidgetItem("—— Letzte Befehle ——")
                hdr.setFlags(Qt.NoItemFlags)
                hdr.setData(Qt.UserRole, "")
                self.list.addItem(hdr)
                for cmd in recent_cmds:
                    self._add_cmd_item(cmd, recent_mark=True)
                    shown += 1
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
            last_cat = object()
            shown = 0
            pinned_set = set(pinned)
            for _sc, cmd in scored:
                if cmd.category != last_cat:
                    last_cat = cmd.category
                    hdr = QListWidgetItem(f"—— {cmd.category or 'Sonstiges'} ——")
                    hdr.setFlags(Qt.NoItemFlags)
                    hdr.setData(Qt.UserRole, "")
                    self.list.addItem(hdr)
                self._add_cmd_item(cmd, pinned_mark=cmd.id in pinned_set)
                shown += 1
            self.count_label.setText(f"{shown} Treffer (Fuzzy)")

        # Ersten echten Befehl selektieren
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item and item.data(Qt.UserRole):
                self.list.setCurrentRow(i)
                break
        self._update_pin_overflow_hint()

    def _add_cmd_item(
        self,
        cmd: PaletteCommand,
        *,
        recent_mark: bool = False,
        pinned_mark: bool = False,
    ) -> None:
        label = cmd.title
        if cmd.shortcut:
            label = f"{cmd.title}  ·  {cmd.shortcut}"
        if pinned_mark:
            prefix = "[Pin] "
        elif recent_mark:
            prefix = "★ "
        else:
            prefix = ""
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
        if pinned_mark:
            tip += "\nAngeheftet (Rechtsklick → Unpin) · Persistenz Settings — 2.3.3"
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
