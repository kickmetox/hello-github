"""Hilfe- und About-Dialoge."""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
)

from instantlensdoc import __version__
from instantlensdoc.config import CONTACT_EMAIL, DISPLAY_NAME, ROOT, VENDOR, icon_paths_for_qt
from instantlensdoc.core.logging_setup import log_dir


HELP_HTML = f"""
<h2>InstantLens Doc — Hilfe</h2>
<p>Moderne Textverarbeitung mit PDF-Annotator, OCR-Bridge und Formulargenerator.</p>
<h3>Erste Schritte</h3>
<ul>
<li><b>Datei → Öffnen</b>: TXT, MD, HTML, DOCX, PDF, Bilder</li>
<li><b>Extras → Einstellungen</b>: Theme, <b>UI-Sprache DE/EN</b>, OCR, Export-Qualität,
    <b>Standard-Zoom</b>, <b>Autosave-Intervall</b>, Soft-Wrap, optional <b>Minimieren in System-Tray</b>,
    optional <b>Backup .bak beim Speichern</b>, <b>Seitengröße-Einheit mm/inch</b>,
    Update-Hinweis, Pfade</li>
<li><b>Datei → Zuletzt geöffnet</b>: Menü + Seitenleiste (persistiert)</li>
<li><b>Datei → Speichern unter</b> (Ctrl+Shift+S): Text → Dokument; PDF → Annotation-Sidecar wählen (PDF unverändert)</li>
<li><b>Datei → Alles speichern</b> (Ctrl+Alt+Shift+S): aktuelles Doc + PDF-Sidecars offener Tabs</li>
<li><b>Datei → Als Kopie speichern</b> (Ctrl+Alt+S): PDF + Sidecar kopieren (Doc bleibt offen); Editor → Speichern unter</li>
<li><b>Datei → Exportieren</b>: Editor-Inhalt als HTML, DOCX oder PDF (zuletzt genutzter Ordner wird gemerkt)</li>
<li><b>Datei → Drucken</b> (Ctrl+P): Editor oder aktuelle PDF-Seite (Qt Print)</li>
<li><b>Seitenleiste</b>: Suche (inkl. letzte Suchbegriffe), „Alle Docs“-Volltext, Zuletzt geöffnet, Dokumente,
    Lesezeichen/Outline (+/− hinzufügen/löschen), <b>Annotationen</b> (klickbar, <b>nach Seite gruppiert</b>,
    <b>Filter nach Typ</b>, <b>Textsuche in der Liste</b>), Markierungen/Treffer</li>
<li><b>Bearbeiten → Rückgängig/Wiederholen</b>: Editor-Text <i>oder</i> PDF-Annotationen/Overlay-Text (Ctrl+Z / Ctrl+Y)</li>
<li><b>Bearbeiten → Suchen und Ersetzen</b> (Ctrl+R): Find/Replace im Texteditor</li>
<li><b>Bearbeiten → Gehe zu Zeile</b> (Ctrl+G): Sprung zur Zeilennummer</li>
<li><b>Bearbeiten → Zeile duplizieren</b> (Ctrl+D): aktuelle Zeile / Auswahl darunter kopieren</li>
<li><b>Bearbeiten → Auswahl markieren</b> (Ctrl+H): Markierung im Editor + Eintrag in der Seitenleiste</li>
<li><b>Bearbeiten → Groß-/Kleinschreibung umschalten</b> (Ctrl+Shift+U): Auswahl GROSS → klein → Titel</li>
<li><b>Bearbeiten → Einrückung erhöhen/verringern</b> (Ctrl+] / Ctrl+[; Tab / Shift+Tab bei Auswahl)</li>
<li><b>Ansicht</b>: Zoom +/−, Seite einpassen (Ctrl+0), Breite (Ctrl+9), 100&nbsp;% (Ctrl+1);
    <b>Hell/Dunkel</b>-Design umschalten; optionale <b>Zeilennummern</b>; <b>Markdown-Vorschau</b> (Split, Ctrl+Shift+M);
    <b>PDF Graustufen</b>; <b>PDF Nachtmodus</b> (Invert-Ansicht, nur Darstellung);
    <b>Annotation-Layer</b> ein/aus (Ctrl+Shift+A)</li>
<li><b>Drag &amp; Drop</b>: Dateien auf das Fenster ziehen zum Öffnen</li>
<li><b>Autosave</b>: Textdokumente (mit Pfad) und PDF-Annotationen — Intervall in Einstellungen</li>
<li><b>PDF</b>: Blättern, Zoom/Fit (debounced + Cache), <b>⟲/⟳ drehen</b> / <b>↔/↕ spiegeln</b> (speichert),
    <b>Graustufen</b> (Ansicht + Bild-Export), <b>Nachtmodus</b> (nur Ansicht, nicht speichern),
    <b>leere Seite / duplizieren</b>, Seite löschen, Seiten neu anordnen;
    Annotationen: Highlight (Drag) + <b>Farben-Picker HL/Stift</b> + <b>Deckkraft α</b>, <b>Schwärzen/Redaction</b> (Drag + Preview „REDACT“ + Einbrennen-Dialog), Unterstreichen, Notiz, <b>Text-Overlay</b>,
    <b>Stempel-Bibliothek</b> (GENEHMIGT/ENTWURF/VERTRAULICH + Datum), Callout,
    <b>Rechteck / Linie / Pfeil / Lineal</b> —
    Sidecar <code>*.ildann.json</code> (v3, Auto-Save, Undo/Redo); JSON Export/Import;
    <b>Textsuche</b> highlightet Treffer auf der aktuellen Seite;
    Doppelklick / Strg+Klick / <b>Ctrl+E</b> auf Notiz/Overlay zum Bearbeiten;
    <b>Ctrl+Shift+D</b> Auswahl duplizieren;
    PDF → Text→Overlay / Overlay einbrennen / <b>Text Seite/alles → Editor</b>;
    <b>Signaturfeld</b> (Platzhalter) und <b>Signatur (Bild)</b> einfügen;
    <b>PDFs zusammenführen / teilen / Seitenbereich</b>;
    <b>Wasserzeichen / Seitennummern</b>;
    <b>Zwei PDFs vergleichen</b> (Seite neben Seite);
    <b>Passwort setzen/öffnen</b>; <b>Bildkompression</b> (Seiten neu als JPEG);
    <b>Metadaten bearbeiten</b>; <b>AcroForm-Formularfelder ausfüllen</b>; <b>Anhänge</b> auflisten/extrahieren;
    <b>Seitengröße / Zuschneiden</b> (Anzeige mm/inch, Statusleiste klickbar / Ctrl+Alt+U);
    Seite/Seiten als PNG/JPEG exportieren / Bild als neue Seite / Seite drucken; Annotation löschen (Auswahl/letzte, Entf); Statusleiste Seite/Größe/Zoom/Dateiname/Wörter; Thumbnails per Drag neu ordnen (<b>Lazy-Load</b>);
    PDF als Kopie speichern; <b>Seitenbereich extrahieren</b> (von–bis → neues PDF);
    große PDFs: Warnung / Limits;
    <b>Seiten-Thumbnails</b> in der Sidebar</li>
<li><b>Datei → Schließen</b>: Speichern-Dialog bei ungespeicherten Änderungen</li>
<li><b>Hilfe → Auf Updates prüfen</b>: lokal immer; Online optional (offline OK)</li>
<li><b>Hilfe → Logordner öffnen</b>: Crash-/App-Logs im Dateimanager</li>
<li><b>Zwischenablage</b>: Bild einfügen (Editor Ctrl+Shift+V / PDF Strg+V) — Stempel oder neue Seite</li>
<li><b>Session</b>: Offene Dokumente (Sidebar-Liste) werden beim Beenden gespeichert und beim Start wiederhergestellt</li>
<li><b>Logging</b>: Datei unter <code>%APPDATA%/InstantLensDoc/logs/</code> (Windows) bzw. <code>~/.config/InstantLensDoc/logs/</code></li>
<li><b>Tastaturhilfe</b>: Hilfe → Tastaturhilfe (F1)</li>
<li><b>Extras → Batch-Konvertierung</b>: Ordner → PDF oder OCR</li>
<li><b>Einfügen → Verketteter Textrahmen</b>: Overflow fließt in den Folgeahmen</li>
<li><b>OCR</b>: Extras → OCR — Sprach-Presets + Modus „editierbarer Text“ oder
    „durchsuchbares Bild“ (PDF + <code>*.ildocr.txt</code>); Tabellen-Heuristik als Markdown wo möglich.
    Ohne Tesseract: Install-Hinweis mit Link
    (<a href="https://github.com/UB-Mannheim/tesseract/wiki">UB-Mannheim Wiki</a>,
    <code>winget install UB-Mannheim.TesseractOCR</code>)</li>
<li><b>Formulare</b>: Extras → Formulargenerator — mehr Feldtypen, Definition speichern/laden
    (<code>*.ildform.json</code>), Live-Vorschau, Export HTML/PDF</li>
<li><b>Build (Windows)</b>: <code>build-windows.ps1</code> — PyInstaller App + Keygen</li>
<li><b>Installer</b>: Desktop-Verknüpfung + Startmenü-Gruppe (siehe Inno-Hinweis)</li>
<li><b>Lizenz</b>: Statusleiste (farbig; bei &lt;7 Tagen Restlaufzeit prominent) + Hilfe → Lizenz — Trial 4 Wochen, Keys 30+2 Tage</li>
<li><b>Keygen</b>: <code>run-keygen.bat</code> / <code>python -m keygen --gui</code>;
    Installer-EXE: <code>{{app}}/InstantLensKeygen.exe</code> (siehe <code>keygen/README.md</code>)</li>
</ul>
<h3>PDF-Modul</h3>
<p>Das Paket <code>ild_pdf</code> kann von anderen Programmen genutzt werden (pypdfium2, kein Poppler).
Beispiel: <code>examples/ild_pdf_demo.py</code>. API: <code>ild_pdf/README.md</code>.</p>
<h3>Sync / Update</h3>
<p>Windows: Repo-Skript <code>scripts/sync-ild.ps1</code> bzw. Store <code>docs/sync-ild.ps1</code> — Branch oder Zip nach
<code>D:\\AI_Temp\\InstantLensDoc</code>, pip, optional Start. Eigenes Icon in <code>assets</code> bleibt erhalten.</p>
<h3>Geplante Features</h3>
<p>KI-Assistent, Cloud-Sync, Stylus/Palm Rejection, 3D u. a. sind im Menü als „Geplant“ markiert
(Stub {__version__}) — siehe FEATURES.md.</p>
"""


def open_log_folder(parent=None) -> bool:
    """Logordner im Dateimanager öffnen; True bei Erfolg."""
    path = log_dir()
    ok = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    if not ok and parent is not None:
        QMessageBox.information(
            parent,
            "Logordner",
            f"Logordner konnte nicht geöffnet werden.\nPfad:\n{path}",
        )
    return bool(ok)


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hilfe")
        self.resize(580, 480)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        browser = QTextBrowser()
        browser.setHtml(HELP_HTML)
        tabs.addTab(browser, "Bedienung")

        features_path = ROOT / "FEATURES.md"
        feat = QTextBrowser()
        if features_path.exists():
            feat.setPlainText(features_path.read_text(encoding="utf-8"))
        else:
            feat.setPlainText("FEATURES.md nicht gefunden.")
        tabs.addTab(feat, "Features")
        layout.addWidget(tabs)

        btn_row = QHBoxLayout()
        btn_logs = QPushButton("Logordner öffnen")
        btn_logs.setToolTip("Crash-/App-Logordner im Dateimanager öffnen")
        btn_logs.clicked.connect(lambda: open_log_folder(self))
        btn_row.addWidget(btn_logs)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.clicked.connect(self.accept)
        layout.addWidget(buttons)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{DISPLAY_NAME} {__version__}")
        icon = QIcon()
        for p in icon_paths_for_qt():
            icon.addFile(str(p))
        if not icon.isNull():
            self.setWindowIcon(icon)
        layout = QVBoxLayout(self)
        icon_lbl = QLabel()
        if not icon.isNull():
            icon_lbl.setPixmap(icon.pixmap(64, 64))
            layout.addWidget(icon_lbl)
        layout.addWidget(
            QLabel(
                f"<h2>{DISPLAY_NAME} {__version__}</h2>"
                f"<p>Version {__version__}<br>"
                f"Hersteller: {VENDOR}<br>"
                f"Kontakt: {CONTACT_EMAIL}</p>"
                f"<p>PDF-Engine: pypdfium2 / PDFium (lizenzfreundlich)</p>"
                f"<p>Icon: assets/app.ico · assets/icon.png</p>"
            )
        )
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
