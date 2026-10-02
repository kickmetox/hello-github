"""Tastaturhilfe-Dialog."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTextBrowser, QVBoxLayout

SHORTCUTS_HTML = """
<h2>Tastaturhilfe — InstantLens Doc</h2>
<table cellpadding="4" cellspacing="0">
<tr><th align="left">Aktion</th><th align="left">Kürzel</th></tr>
<tr><td>Neu</td><td><code>Ctrl+N</code></td></tr>
<tr><td>Öffnen</td><td><code>Ctrl+O</code></td></tr>
<tr><td>Speichern</td><td><code>Ctrl+S</code></td></tr>
<tr><td>Drucken</td><td><code>Ctrl+P</code></td></tr>
<tr><td>Beenden</td><td><code>Ctrl+Q</code></td></tr>
<tr><td>Rückgängig</td><td><code>Ctrl+Z</code></td></tr>
<tr><td>Wiederholen</td><td><code>Ctrl+Y</code> / <code>Ctrl+Shift+Z</code></td></tr>
<tr><td>Suchen</td><td><code>Ctrl+F</code></td></tr>
<tr><td>Auswahl markieren</td><td><code>Ctrl+H</code></td></tr>
<tr><td>Bild aus Zwischenablage</td><td><code>Ctrl+Shift+V</code></td></tr>
<tr><td>PDF: Bild einfügen (Viewer)</td><td><code>Ctrl+V</code></td></tr>
<tr><td>Zoom +</td><td><code>Ctrl++</code></td></tr>
<tr><td>Zoom −</td><td><code>Ctrl+-</code></td></tr>
<tr><td>Seite einpassen</td><td><code>Ctrl+0</code></td></tr>
<tr><td>Breite einpassen</td><td><code>Ctrl+9</code></td></tr>
<tr><td>Zoom 100&nbsp;%</td><td><code>Ctrl+1</code></td></tr>
<tr><td>Overlay bearbeiten</td><td>Doppelklick / <code>Ctrl</code>+Klick</td></tr>
<tr><td>Diese Hilfe</td><td><code>F1</code> (Hilfe-Menü)</td></tr>
</table>
<p><b>PDF-Werkzeuge</b> (Toolbar): Highlight, Schwärzen (REDACT-Preview), Formen per Drag;
Notiz/Stempel/Callout/Overlay per Klick.</p>
<p><b>Schwärzung:</b> Rechteck ziehen → PDF → Schwärzung einbrennen… (Sidecar optional leeren)
bzw. Schwärzungs-Annotationen löschen…</p>
<p>Vollständige Bedienung: Hilfe → Hilfe…</p>
"""


class KeyboardHelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tastaturhilfe")
        self.resize(520, 480)
        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setHtml(SHORTCUTS_HTML)
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.clicked.connect(self.accept)
        layout.addWidget(buttons)
