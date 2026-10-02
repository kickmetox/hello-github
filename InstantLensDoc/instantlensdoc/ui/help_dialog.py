"""Hilfe- und About-Dialoge."""

from __future__ import annotations

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTabWidget, QTextBrowser, QVBoxLayout

from instantlensdoc import __version__
from instantlensdoc.config import CONTACT_EMAIL, DISPLAY_NAME, ROOT, VENDOR, icon_paths_for_qt


HELP_HTML = """
<h2>InstantLens Doc — Hilfe</h2>
<p>Moderne Textverarbeitung mit PDF-Annotator, OCR-Bridge und Formulargenerator.</p>
<h3>Erste Schritte</h3>
<ul>
<li><b>Datei → Öffnen</b>: TXT, MD, HTML, DOCX, PDF, Bilder</li>
<li><b>Datei → Einstellungen</b>: OCR-Standardsprache, Theme, Batch-/Öffnen-Pfade</li>
<li><b>Datei → Zuletzt geöffnet</b>: Menü + Seitenleiste (persistiert)</li>
<li><b>Datei → Exportieren</b>: Editor-Inhalt als HTML, DOCX oder PDF</li>
<li><b>Datei → Drucken</b> (Ctrl+P): Editor oder aktuelle PDF-Seite (Qt Print)</li>
<li><b>Seitenleiste</b>: Suche, „Alle Docs“-Volltext, Zuletzt geöffnet, Dokumente,
    Lesezeichen/Outline, Annotationen/Markierungen</li>
<li><b>Bearbeiten → Rückgängig/Wiederholen</b>: Editor-Text <i>oder</i> PDF-Annotationen/Overlay-Text (Ctrl+Z / Ctrl+Y)</li>
<li><b>Bearbeiten → Auswahl markieren</b> (Ctrl+H): Markierung im Editor + Eintrag in der Seitenleiste</li>
<li><b>Ansicht</b>: Zoom +/−, Seite einpassen (Ctrl+0), Breite (Ctrl+9), 100&nbsp;% (Ctrl+1);
    <b>Hell/Dunkel</b>-Design umschalten</li>
<li><b>Drag &amp; Drop</b>: Dateien auf das Fenster ziehen zum Öffnen</li>
<li><b>Autosave</b>: Textdokumente (mit Pfad) und PDF-Annotationen ca. jede Minute</li>
<li><b>PDF</b>: Blättern, Zoom/Fit, 90°-Drehen, Seite löschen, Seiten neu anordnen;
    Annotationen: Highlight (Drag), Unterstreichen, Notiz, <b>Text-Overlay</b>, Stempel, Callout,
    <b>Rechteck / Linie / Pfeil / Lineal</b> —
    Sidecar <code>*.ildann.json</code> (v3, Auto-Save, Undo/Redo);
    Doppelklick oder Strg+Klick auf Overlay zum Bearbeiten;
    PDF → Text→Overlay / Overlay einbrennen;
    <b>Signaturfeld</b> (Platzhalter) und <b>Signatur (Bild)</b> einfügen;
    <b>PDFs zusammenführen / teilen</b>;
    Seite als Bild / Bild als neue Seite / Seite drucken</li>
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
<li><b>Lizenz</b>: Statusleiste (farbig) + Hilfe → Lizenz — Trial 4 Wochen, Keys 30+2 Tage</li>
<li><b>Keygen</b>: <code>run-keygen.bat</code> bzw. <code>python -m keygen --gui</code></li>
</ul>
<h3>PDF-Modul</h3>
<p>Das Paket <code>ild_pdf</code> kann von anderen Programmen genutzt werden (pypdfium2, kein Poppler).
Beispiel: <code>examples/ild_pdf_demo.py</code>. API: <code>ild_pdf/README.md</code>.</p>
<h3>Sync / Update</h3>
<p>Windows: Store-Skript <code>docs/sync-ild.ps1</code> — Branch oder Zip nach
<code>D:\\AI_Temp\\InstantLensDoc</code>, pip, optional Start. Eigenes Icon in <code>assets</code> bleibt erhalten.</p>
<h3>Geplante Features</h3>
<p>KI-Assistent, Cloud-Sync, Stylus/Palm Rejection, 3D u. a. sind im Menü als „Geplant“ markiert —
siehe FEATURES.md.</p>
"""


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

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.clicked.connect(self.accept)
        layout.addWidget(buttons)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Info")
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
                f"<h2>{DISPLAY_NAME}</h2>"
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
