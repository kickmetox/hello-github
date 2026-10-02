"""Tastaturhilfe-Dialog."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTextBrowser, QVBoxLayout

SHORTCUTS_HTML = """
<h2>Tastaturhilfe — InstantLens Doc</h2>
<table cellpadding="4" cellspacing="0">
<tr><th align="left">Aktion</th><th align="left">Kürzel</th></tr>
<tr><td>Neu (leer)</td><td><code>Ctrl+N</code></td></tr>
<tr><td>Textbaustein 1–3 einfügen</td><td><code>Ctrl+Alt+1</code> … <code>3</code></td></tr>
<tr><td>Annotationen sperren</td><td><code>Ctrl+Shift+L</code></td></tr>
<tr><td>Seitenrahmen / CropBox</td><td><code>Ctrl+Shift+B</code></td></tr>
<tr><td>Druckermarken</td><td><code>Ctrl+Alt+M</code></td></tr>
<tr><td>Zeilen sortieren (A–Z)</td><td><code>Ctrl+Shift+O</code></td></tr>
<tr><td>Öffnen</td><td><code>Ctrl+O</code></td></tr>
<tr><td>Speichern</td><td><code>Ctrl+S</code></td></tr>
<tr><td>Alles speichern</td><td><code>Ctrl+Alt+Shift+S</code></td></tr>
<tr><td>Speichern unter…</td><td><code>Ctrl+Shift+S</code></td></tr>
<tr><td>Als Kopie speichern…</td><td><code>Ctrl+Alt+S</code></td></tr>
<tr><td>Drucken</td><td><code>Ctrl+P</code></td></tr>
<tr><td>Beenden</td><td><code>Ctrl+Q</code></td></tr>
<tr><td>Rückgängig</td><td><code>Ctrl+Z</code></td></tr>
<tr><td>Wiederholen</td><td><code>Ctrl+Y</code> / <code>Ctrl+Shift+Z</code></td></tr>
<tr><td>Suchen</td><td><code>Ctrl+F</code></td></tr>
<tr><td>Suchen und Ersetzen</td><td><code>Ctrl+R</code></td></tr>
<tr><td>Gehe zu Zeile / Seite</td><td><code>Ctrl+G</code> (Editor / PDF)</td></tr>
<tr><td>Gehe zu Seite (PDF-Menü)</td><td><code>Ctrl+Shift+G</code></td></tr>
<tr><td>Tab duplizieren</td><td><code>Ctrl+Shift+T</code></td></tr>
<tr><td>Erneut öffnen</td><td><code>Ctrl+Alt+Shift+O</code></td></tr>
<tr><td>Zeile duplizieren</td><td><code>Ctrl+D</code></td></tr>
<tr><td>Zeile kommentieren/auskommentieren</td><td><code>Ctrl+/</code> (# oder //)</td></tr>
<tr><td>Auswahl markieren</td><td><code>Ctrl+H</code></td></tr>
<tr><td>Groß-/Kleinschreibung umschalten</td><td><code>Ctrl+Shift+U</code></td></tr>
<tr><td>Einrückung erhöhen</td><td><code>Ctrl+]</code> / <code>Tab</code> (Block)</td></tr>
<tr><td>Einrückung verringern</td><td><code>Ctrl+[</code> / <code>Shift+Tab</code></td></tr>
<tr><td>Präsentationsmodus</td><td><code>F5</code> (Vollbild; ←/→ Esc)</td></tr>
<tr><td>Bild aus Zwischenablage</td><td><code>Ctrl+Shift+V</code></td></tr>
<tr><td>PDF: Bild einfügen (Viewer)</td><td><code>Ctrl+V</code></td></tr>
<tr><td>Zoom +</td><td><code>Ctrl++</code></td></tr>
<tr><td>Zoom −</td><td><code>Ctrl+-</code></td></tr>
<tr><td>Seite einpassen</td><td><code>Ctrl+0</code></td></tr>
<tr><td>Breite einpassen</td><td><code>Ctrl+9</code></td></tr>
<tr><td>Höhe einpassen</td><td><code>Ctrl+8</code></td></tr>
<tr><td>Zoom 100&nbsp;%</td><td><code>Ctrl+1</code></td></tr>
<tr><td>Overlay / Notiz bearbeiten</td><td>Doppelklick / <code>Ctrl</code>+Klick / <code>Ctrl+E</code></td></tr>
<tr><td>Annotation auswählen</td><td>Werkzeug Auswahl / Shift+Klick / Rechtsklick</td></tr>
<tr><td>PDF-Link (http/https) öffnen</td><td>Auswahl + Klick / <code>Ctrl</code>+Klick</td></tr>
<tr><td>Stempel drehen 90°</td><td>Toolbar „Stempel ↻“ / PDF-Menü (Auswahl)</td></tr>
<tr><td>Annotation löschen</td><td><code>Entf</code> / <code>Backspace</code> (Auswahl oder letzte)</td></tr>
<tr><td>Annotation duplizieren</td><td><code>Ctrl+Shift+D</code> (Auswahl)</td></tr>
<tr><td>Alle Annotationen auf Seite</td><td><code>Ctrl+A</code> (PDF-Modus)</td></tr>
<tr><td>Seitengröße mm/inch</td><td><code>Ctrl+Alt+U</code> / Klick Status</td></tr>
<tr><td>Diese Hilfe</td><td><code>F1</code></td></tr>
</table>
<p><b>Speichern unter (PDF):</b> speichert die Annotationen als Sidecar
<code>*.ildann.json</code> (PDF-Datei bleibt unverändert). Auch unter
PDF → Annotationen speichern unter…</p>
<p><b>Alles speichern:</b> aktuelles Dokument sowie Annotation-Sidecars der offenen PDF-Tabs
(<code>Ctrl+Alt+Shift+S</code> / Datei).</p>
<p><b>Als Kopie speichern (PDF):</b> schreibt PDF + Sidecar an neuen Pfad;
aktuelles Dokument bleibt geöffnet (<code>Ctrl+Alt+S</code> / Datei / PDF).</p>
<p><b>Lesezeichen:</b> Sidebar +/− oder PDF → Lesezeichen hinzufügen/löschen.</p>
<p><b>Annotationen JSON/CSV:</b> PDF → als JSON oder CSV exportieren / JSON importieren (ersetzen oder anhängen).</p>
<p><b>PDF-Werkzeuge</b> (Toolbar): Auswahl (auch PDF-Links öffnen / Ann. verschieben wenn entsperrt), Highlight, Schwärzen (REDACT-Preview), Formen per Drag;
Notiz/Stempel/Callout/Overlay per Klick; <b>Stempel ↻</b> drehen; <b>HL</b>/<b>Stift</b>-Farben-Picker; <b>α Deckkraft</b>;
<b>Grau</b>-Toggle; <b>Nacht</b>-Toggle (nur Ansicht); <b>Sperre</b>; <b>Rahmen</b> (CropBox); Ann. löschen;
Seite <b>⟲/⟳ drehen</b>, <b>↔/↕ spiegeln</b>, <b>leere Seite</b>, <b>duplizieren</b>.</p>
<p><b>Editor-Encoding:</b> Datei → Öffnen/Speichern mit Encoding (UTF-8 / Latin-1); Standard in Einstellungen.</p>
<p><b>Drag &amp; Drop:</b> mehrere Dateien → mehrere Tabs in der Sidebar.</p>
<p><b>PDF-Suche:</b> Sidebar-Suche highlightet Treffer auf der aktuellen Seite;
„Weiter“ springt zum nächsten Treffer; <b>letzte Suchbegriffe</b> im Dropdown.</p>
<p><b>Annotationen:</b> eigene Liste in der Sidebar — <b>gruppiert nach Seite</b>; Klick springt zur Annotation;
Filter-Dropdown nach Typ; <b>Farben-Chips in der Statistik klickbar</b>; <b>Textsuche in der Liste</b>;
Text nachträglich editierbar; Deckkraft pro Annotation.</p>
<p><b>Seitenbereich:</b> PDF → Seitenbereich extrahieren… (von–bis → neues PDF)
bzw. Dialog „zusammenführen / teilen / Bereich“.</p>
<p><b>Suchen und Ersetzen:</b> Bearbeiten → Ctrl+R (nur Texteditor).</p>
<p><b>Gehe zu Zeile / Seite:</b> Bearbeiten → Ctrl+G (Editor: Zeile; PDF: Seite);
PDF → Gehe zu Seite… (Ctrl+Shift+G).</p>
<p><b>Tab duplizieren:</b> Datei → Ctrl+Shift+T (Editor-Inhalt klonen);
Erneut öffnen: Ctrl+Alt+Shift+O.</p>
<p><b>Annotation-Farben:</b> Sidebar-Statistik-Chips klicken → Liste nach Farbe filtern.</p>
<p><b>Statusleiste:</b> Hint „Ctrl+Z · Letzte Aktion rückgängig“.</p>
<p><b>Zeile duplizieren:</b> Bearbeiten → Ctrl+D (aktuelle Zeile oder Auswahl).</p>
<p><b>Zeile verschieben:</b> Bearbeiten → Alt+Up / Alt+Down (aktuelle Zeile oder Auswahl).</p>
<p><b>Zeilen sortieren (A–Z):</b> Bearbeiten → Ctrl+Shift+O (Auswahl; ohne Auswahl ganze Datei).</p>
<p><b>Sonderzeichen:</b> Ansicht → Sonderzeichen anzeigen (Ctrl+Shift+.) — Tabs/Leerzeichen/Absätze.</p>
<p><b>Kommentieren:</b> Bearbeiten → Ctrl+/ (# oder // je nach Dateityp).</p>
<p><b>Groß-/Kleinschreibung:</b> Bearbeiten → Ctrl+Shift+U (Auswahl).</p>
<p><b>Einrückung:</b> Bearbeiten → Ctrl+] / Ctrl+[ bzw. Tab / Shift+Tab (Block, aktuelle Zeile oder Auswahl).</p>
<p><b>Präsentation:</b> Ansicht → Präsentationsmodus (F5): Vollbild-PDF; Pfeiltasten/Leertaste; Esc beendet.</p>
<p><b>Farben-Favoriten:</b> Toolbar 1/2/3 — Klick = Highlight, Shift+Klick = Stift, Rechtsklick = speichern.</p>
<p><b>Zeilennummern:</b> Ansicht → Zeilennummern (optional, auch in Einstellungen).</p>
<p><b>PDF Graustufen:</b> Ansicht → PDF Graustufen / Toolbar „Grau“ (Ansicht + Export).</p>
<p><b>PDF Nachtmodus:</b> Ansicht → PDF Nachtmodus / Toolbar „Nacht“ (nur Invert-Ansicht, nicht speichern).</p>
<p><b>Logordner:</b> Hilfe → Logordner öffnen (Crash-/App-Logs).</p>
<p><b>Lizenz:</b> bei weniger als 7 Resttagen prominent in der Statusleiste.</p>
<p><b>Seiten als Bilder:</b> PDF → Seite/Seiten als PNG/JPEG exportieren (aktuell oder alle; DPI 72/150/300).</p>
<p><b>Thumbnails:</b> in der Sidebar ziehen zum Neuordnen der Seiten; Größe in Einstellungen (klein/normal/groß).</p>
<p><b>Statusleiste:</b> Dateiname · Seite x/y · Seitengröße (mm/inch, klickbar) · Zoom % · Wörter/Ann. · Version · Lizenz.</p>
<p><b>Schwärzung:</b> Rechteck ziehen → PDF → Schwärzung einbrennen… (Sidecar optional leeren)
bzw. Schwärzungs-Annotationen löschen…</p>
<p><b>Export-Overwrite:</b> Existiert die Zieldatei schon, Nachfrage (Default: Nein).</p>
<p><b>Ann.-Statistik:</b> Sidebar-Footer zeigt Anzahl je Annotationstyp.</p>
<p><b>Tray:</b> Tooltip enthält App-Version; Update-Hinweis beim Start nur wenn in Einstellungen aktiv.</p>
<p><b>Extras:</b> Einstellungen (Standard-Zoom, Thumbnail-Größe, Autosave-Intervall), Batch (Fortschrittsbalken), OCR (Fortschrittsdialog).</p>
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
