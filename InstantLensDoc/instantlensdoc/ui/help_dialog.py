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
<li><b>Seitenleiste</b>: Suche (Enter/Suchen), Weiter, Dokumente, Annotationen/Markierungen</li>
<li><b>Bearbeiten → Auswahl markieren</b> (Ctrl+H): Markierung im Editor + Eintrag in der Seitenleiste</li>
<li><b>PDF</b>: Blättern, Zoom, 90°-Drehen, Seite löschen, Seiten neu anordnen;
    Annotationen per Klick (Highlight, Unterstreichen, Notiz, Textfeld, <b>Stempel</b>, <b>Callout</b>) —
    Sidecar <code>*.ildann.json</code> (v2, Auto-Save); Menü PDF → speichern/laden;
    Seite als Bild / Bild als neue Seite</li>
<li><b>Einfügen → Verketteter Textrahmen</b>: Overflow fließt in den Folgeahmen</li>
<li><b>OCR</b>: Extras → OCR — Sprach-Presets + Modus „editierbarer Text“ oder
    „durchsuchbares Bild“ (PDF + <code>*.ildocr.txt</code>). Ohne Tesseract: Install-Hinweis
    (<code>winget install UB-Mannheim.TesseractOCR</code>)</li>
<li><b>Formulare</b>: Extras → Formulargenerator — mehr Feldtypen, Definition speichern/laden
    (<code>*.ildform.json</code>), Live-Vorschau, Export HTML/PDF</li>
<li><b>Build (Windows)</b>: <code>build-windows.ps1</code> — PyInstaller App + Keygen</li>
<li><b>Lizenz</b>: Hilfe → Lizenz — Trial 4 Wochen, Keys 30+2 Tage</li>
<li><b>Keygen</b>: <code>run-keygen.bat</code> bzw. <code>python -m keygen --gui</code></li>
</ul>
<h3>PDF-Modul</h3>
<p>Das Paket <code>ild_pdf</code> kann von anderen Programmen genutzt werden (pypdfium2, kein Poppler).
Bild-Hooks: <code>extract_page_image</code>, <code>insert_image_as_page</code>.</p>
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
