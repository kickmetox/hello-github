"""Hilfe- und About-Dialoge."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTabWidget, QTextBrowser, QVBoxLayout

from instantlensdoc import __version__
from instantlensdoc.config import CONTACT_EMAIL, DISPLAY_NAME, ROOT, VENDOR


HELP_HTML = """
<h2>InstantLens Doc — Hilfe</h2>
<p>Moderne Textverarbeitung mit PDF-Annotator, OCR-Bridge und Formulargenerator.</p>
<h3>Erste Schritte</h3>
<ul>
<li><b>Datei → Öffnen</b>: TXT, MD, HTML, DOCX, PDF, Bilder</li>
<li><b>PDF</b>: Seiten blättern, zoomen, drehen; Annotationen per Klick (Highlight, Unterstreichen, Notiz, Textfeld)</li>
<li><b>OCR</b>: Extras → OCR — benötigt installiertes Tesseract</li>
<li><b>Formulare</b>: Extras → Formulargenerator</li>
<li><b>Lizenz</b>: Hilfe → Lizenz — Trial 4 Wochen, Keys 30+2 Tage</li>
</ul>
<h3>PDF-Modul</h3>
<p>Das Paket <code>ild_pdf</code> kann von anderen Programmen genutzt werden (pypdfium2, kein Poppler).</p>
<h3>Geplante Features</h3>
<p>KI-Assistent, Cloud-Sync, Stylus/Palm Rejection u. a. sind im Menü als „Geplant“ markiert — siehe FEATURES.md.</p>
"""


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hilfe")
        self.resize(560, 420)
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
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                f"<h2>{DISPLAY_NAME}</h2>"
                f"<p>Version {__version__}<br>"
                f"Hersteller: {VENDOR}<br>"
                f"Kontakt: {CONTACT_EMAIL}</p>"
                f"<p>PDF-Engine: pypdfium2 / PDFium (lizenzfreundlich)</p>"
            )
        )
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
