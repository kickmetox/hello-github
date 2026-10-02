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
<tr><td>Speichern unter…</td><td><code>Ctrl+Shift+S</code></td></tr>
<tr><td>Als Kopie speichern…</td><td><code>Ctrl+Alt+S</code></td></tr>
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
<tr><td>Annotation auswählen</td><td>Werkzeug Auswahl / Shift+Klick / Rechtsklick</td></tr>
<tr><td>Annotation löschen</td><td><code>Entf</code> / <code>Backspace</code> (Auswahl oder letzte)</td></tr>
<tr><td>Diese Hilfe</td><td><code>F1</code></td></tr>
</table>
<p><b>Speichern unter (PDF):</b> speichert die Annotationen als Sidecar
<code>*.ildann.json</code> (PDF-Datei bleibt unverändert). Auch unter
PDF → Annotationen speichern unter…</p>
<p><b>Als Kopie speichern (PDF):</b> schreibt PDF + Sidecar an neuen Pfad;
aktuelles Dokument bleibt geöffnet (<code>Ctrl+Alt+S</code> / Datei / PDF).</p>
<p><b>Lesezeichen:</b> Sidebar +/− oder PDF → Lesezeichen hinzufügen/löschen.</p>
<p><b>Annotationen JSON:</b> PDF → exportieren / importieren (ersetzen oder anhängen).</p>
<p><b>PDF-Werkzeuge</b> (Toolbar): Auswahl, Highlight, Schwärzen (REDACT-Preview), Formen per Drag;
Notiz/Stempel/Callout/Overlay per Klick; <b>HL</b>/<b>Stift</b>-Farben-Picker; Ann. löschen;
Seite <b>⟲/⟳ drehen</b>, <b>leere Seite</b>, <b>duplizieren</b>.</p>
<p><b>PDF-Suche:</b> Sidebar-Suche highlightet Treffer auf der aktuellen Seite;
„Weiter“ springt zum nächsten Treffer; <b>letzte Suchbegriffe</b> im Dropdown.</p>
<p><b>Annotationen:</b> eigene Liste in der Sidebar — Klick springt zur Annotation.</p>
<p><b>Seiten als Bilder:</b> PDF → Seite/Seiten als PNG/JPEG exportieren (aktuell oder alle).</p>
<p><b>Thumbnails:</b> in der Sidebar ziehen zum Neuordnen der Seiten.</p>
<p><b>Statusleiste:</b> Dateiname · Seite x/y · Zoom % · Wörter/Ann. · Version · Lizenz.</p>
<p><b>Schwärzung:</b> Rechteck ziehen → PDF → Schwärzung einbrennen… (Sidecar optional leeren)
bzw. Schwärzungs-Annotationen löschen…</p>
<p><b>Extras:</b> Einstellungen (Standard-Zoom, Autosave-Intervall), Batch (Fortschrittsbalken), OCR (Fortschrittsdialog).</p>
<p>Vollständige Bedienung: Hilfe → Hilfe…</p>
"""


class KeyboardHelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tastaturhilfe")
        self.resize(520, 520)
        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setHtml(SHORTCUTS_HTML)
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.clicked.connect(self.accept)
        layout.addWidget(buttons)
