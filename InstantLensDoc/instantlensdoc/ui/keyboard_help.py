"""Tastaturhilfe-Dialog inkl. optionalem PDF-Export des Cheat-Sheets."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from instantlensdoc.core.app_settings import dialog_start_dir, get_last_export_dir, remember_recent_dir, set_last_export_dir

SHORTCUTS_HTML = """
<h2>Tastaturhilfe — InstantLens Doc</h2>
<table cellpadding="4" cellspacing="0">
<tr><th align="left">Aktion</th><th align="left">Kürzel</th></tr>
<tr><td>Neu (leer)</td><td><code>Ctrl+N</code></td></tr>
<tr><td>Textbaustein 1–3 einfügen</td><td><code>Ctrl+Alt+1</code> … <code>3</code></td></tr>
<tr><td>Annotationen sperren</td><td><code>Ctrl+Shift+L</code></td></tr>
<tr><td>Seitenrahmen / CropBox</td><td><code>Ctrl+Shift+B</code></td></tr>
<tr><td>Druckermarken</td><td><code>Ctrl+Alt+M</code></td></tr>
<tr><td>Zwei-Seiten-Ansicht (Spread)</td><td><code>Ctrl+2</code> / Toolbar „2S“</td></tr>
<tr><td>Continuous Scroll</td><td><code>Ctrl+3</code> / Toolbar „CS“</td></tr>
<tr><td>Arbeitsverzeichnis öffnen</td><td><code>Ctrl+Shift+E</code></td></tr>
<tr><td>Projekt-Ordner / Workspace</td><td>Datei → Projekt-Ordner (letzte 5)</td></tr>
<tr><td>Zeilen sortieren (A–Z)</td><td><code>Ctrl+Shift+O</code></td></tr>
<tr><td>Öffnen</td><td><code>Ctrl+O</code></td></tr>
<tr><td>Speichern</td><td><code>Ctrl+S</code> — flush Sidecar-Debounce sofort</td></tr>
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
<tr><td>Dateien vergleichen (Side-by-Side)</td><td><code>Ctrl+Alt+D</code></td></tr>
<tr><td>Erneut öffnen</td><td><code>Ctrl+Alt+Shift+O</code></td></tr>
<tr><td>Zeile / Annotation duplizieren</td><td><code>Ctrl+D</code> (Editor Zeile; PDF Auswahl) — 0.8.2</td></tr>
<tr><td>Zeile kommentieren/auskommentieren</td><td><code>Ctrl+/</code> (# oder //)</td></tr>
<tr><td>Auswahl markieren</td><td><code>Ctrl+H</code></td></tr>
<tr><td>Groß-/Kleinschreibung umschalten</td><td><code>Ctrl+Shift+U</code></td></tr>
<tr><td>Einrückung erhöhen</td><td><code>Ctrl+]</code> / <code>Tab</code> (Block)</td></tr>
<tr><td>Einrückung verringern</td><td><code>Ctrl+[</code> / <code>Shift+Tab</code></td></tr>
<tr><td>Präsentationsmodus</td><td><code>F5</code> (Vollbild; ←/→ Esc)</td></tr>
<tr><td>Bild aus Zwischenablage</td><td><code>Ctrl+Shift+V</code></td></tr>
<tr><td>PDF-Text kopieren (Auswahl)</td><td><code>Ctrl+C</code> (Auswahl-Werkzeug + Text aufziehen) — 0.6.1</td></tr>
<tr><td>Auswahl → Notiz (Sticky)</td><td><code>Ctrl+Alt+N</code> (Text vorausgefüllt; optional +Highlight) — 0.6.2/0.6.3</td></tr>
<tr><td>Andere Tabs schließen</td><td><code>Ctrl+Shift+W</code> (Datei) — 0.6.2</td></tr>
<tr><td>Fenster teilen (zwei Docs)</td><td><code>Ctrl+\\</code> — 0.6.3</td></tr>
<tr><td>Vertikaler Split (übereinander)</td><td><code>Ctrl+Shift+\\</code> (Toggle) — 0.6.5</td></tr>
<tr><td>Sync-Scroll (geteilte Docs)</td><td><code>Ctrl+Alt+\\</code>; Zustand je Session gemerkt — 0.6.4 / 0.6.9</td></tr>
<tr><td>Tag-Cloud Filter</td><td>Klick setzt Filter; <code>Ctrl</code>+Klick Multi-Select — 0.6.4; Rechtsklick → filtern — 0.8.0</td></tr>
<tr><td>Tag-Cloud Farbe / umbenennen</td><td>Rechtsklick → Farbe ändern / umbenennen; Ctrl+Z; Bestätigung ab Schwelle — 0.6.5–0.6.9 / 0.8.0</td></tr>
<tr><td>Zeilen-Lesezeichen Export/Import</td><td>Bearbeiten → JSON (<code>ildbm-v1</code>) — 0.8.0; Drag-Reorder + Sidecar — 0.8.1</td></tr>
<tr><td>Tag-Cloud Sortierung</td><td>Toggle Häufigkeit / A–Z — 0.8.1</td></tr>
<tr><td>Recent fehlend</td><td>Grau + Rechtsklick Entfernen — 0.8.1</td></tr>
<tr><td>Status Zoom</td><td>PDF: Zoom n% in der Statusleiste — 0.8.1</td></tr>
<tr><td>Thumbnail-Reorder Undo</td><td>Seiten ziehen; <code>Ctrl+Z</code> rückgängig — 0.8.2</td></tr>
<tr><td>Fit-Width / Fit-Page</td><td><code>Ctrl+9</code> / <code>Ctrl+0</code>; Standard-Zoom-Modus — 0.8.2</td></tr>
<tr><td>Zoom als Standard</td><td><code>Ctrl+Shift+0</code> aktuellen Zoom-% speichern — 0.8.2</td></tr>
<tr><td>Ungespeicherte Tabs</td><td>Alle speichern: Fortschritt &gt;3, Abbrechen, Fehlerliste am Ende — 0.6.4–0.6.9</td></tr>
<tr><td>Doc-Split PDF+Editor</td><td>Panel-Typ + Sync-Scroll je Session; H/V Ctrl+Shift+\\ — 0.6.3–0.6.9</td></tr>
<tr><td>Wizard / 0.6.8</td><td>Nicht mehr zeigen; Reset; Panel-Session; Save-Abbrechen; Tag-Confirm — 0.6.6–0.6.8</td></tr>
<tr><td>PDF: Bild einfügen (Viewer)</td><td><code>Ctrl+V</code></td></tr>
<tr><td>Zoom +</td><td><code>Ctrl++</code></td></tr>
<tr><td>Zoom −</td><td><code>Ctrl+-</code></td></tr>
<tr><td>Seite einpassen (Fit-Page)</td><td><code>Ctrl+0</code> — 0.8.2</td></tr>
<tr><td>Breite einpassen (Fit-Width)</td><td><code>Ctrl+9</code> — 0.8.2</td></tr>
<tr><td>Höhe einpassen</td><td><code>Ctrl+8</code></td></tr>
<tr><td>Zoom 100&nbsp;%</td><td><code>Ctrl+1</code></td></tr>
<tr><td>Overlay / Notiz bearbeiten</td><td>Doppelklick / <code>Ctrl</code>+Klick / <code>Ctrl+E</code></td></tr>
<tr><td>Annotation auswählen</td><td>Werkzeug Auswahl / Shift+Klick / Rechtsklick</td></tr>
<tr><td>PDF-Link (http/https) öffnen</td><td>Auswahl + Klick / <code>Ctrl</code>+Klick</td></tr>
<tr><td>Stempel drehen 90°</td><td>Toolbar „Stempel ↻“ / PDF-Menü (Auswahl)</td></tr>
<tr><td>Annotation löschen</td><td><code>Entf</code> / <code>Backspace</code> (Auswahl oder letzte)</td></tr>
<tr><td>Annotation-Tags bearbeiten</td><td><code>Ctrl+Alt+T</code></td></tr>
<tr><td>Annotation duplizieren</td><td><code>Ctrl+D</code> / <code>Ctrl+Shift+D</code> (Auswahl) — 0.8.2</td></tr>
<tr><td>Alle Annotationen auf Seite</td><td><code>Ctrl+A</code> (PDF-Modus)</td></tr>
<tr><td>Seitengröße mm/inch</td><td><code>Ctrl+Alt+U</code> / Klick Status</td></tr>
<tr><td>Seite als Favorit umschalten</td><td><code>Ctrl+Shift+F</code> / Toolbar ★</td></tr>
<tr><td>Seiten-Favoriten springen</td><td><code>Ctrl+Alt+F</code> / Toolbar ★… / Sidebar-Liste</td></tr>
<tr><td>Auswahl-Farbe ändern (Batch)</td><td><code>Ctrl+Alt+Shift+F</code></td></tr>
<tr><td>Auswahl-Deckkraft ändern</td><td><code>Ctrl+Alt+Shift+O</code> / Toolbar α-Slider / α…</td></tr>
<tr><td>Zeile favorisieren (Editor)</td><td><code>Ctrl+F2</code> / Klick Zeilennummer</td></tr>
<tr><td>Zeilenfavorit-Label</td><td>Sidebar Doppelklick / Rechtsklick</td></tr>
<tr><td>Nächstes / vorheriges Zeilen-Lesezeichen</td><td><code>F2</code> / <code>Shift+F2</code></td></tr>
<tr><td>Erste Schritte (Wizard)</td><td>Hilfe → Erste Schritte…</td></tr>
<tr><td>Rechtschreibung prüfen</td><td><code>F7</code></td></tr>
<tr><td>Diese Hilfe</td><td><code>F1</code></td></tr>
<tr><td>Cheat-Sheet als PDF</td><td>F1 → „Als PDF exportieren…“</td></tr>
</table>
<p><b>Speichern unter (PDF):</b> speichert die Annotationen als Sidecar
<code>*.ildann.json</code> (PDF-Datei bleibt unverändert). Auch unter
PDF → Annotationen speichern unter…</p>
<p><b>Alles speichern:</b> aktuelles Dokument sowie Annotation-Sidecars der offenen PDF-Tabs
(<code>Ctrl+Alt+Shift+S</code> / Datei).</p>
<p><b>Als Kopie speichern (PDF):</b> schreibt PDF + Sidecar an neuen Pfad;
aktuelles Dokument bleibt geöffnet (<code>Ctrl+Alt+S</code> / Datei / PDF).</p>
<p><b>Lesezeichen:</b> Sidebar +/− oder PDF → Lesezeichen hinzufügen/löschen.</p>
<p><b>PDF-Favoriten:</b> Sidebar-Liste mit Nummern (1. Seite N …); <b>ziehen zum Umsortieren</b>; ★ / Ctrl+Shift+F markiert;
Ctrl+Alt+F Dialog; Sidecar-Meta <code>page_favorites</code>; <b>JSON Export/Import</b> (ildfav-v1).</p>
<p><b>Editor-Zeilenfavoriten:</b> Marker in der Zeilennummernleiste; <b>Sidebar-Liste</b>; Labels per Doppelklick/Rechtsklick;
Ctrl+F2 umschalten; F2 / Shift+F2 springen.</p>
<p><b>Auswahl-Deckkraft:</b> Annotation(en) auswählen → <b>Toolbar-Slider</b> oder Ctrl+Alt+Shift+O / „α…“.</p>
<p><b>Erste Schritte:</b> Hilfe → Erste Schritte… (Kurz-Wizard, 4 Seiten inkl. 0.6-Highlights).</p>
<p><b>Crash-Report:</b> Hilfe → Crash-Report erstellen… (Logordner als ZIP; optional Screenshot-Pfad-Hinweis).</p>
<p><b>Annotationen JSON/CSV/Bericht:</b> PDF → als JSON oder CSV exportieren / JSON importieren;
<strong>Kommentar-Bericht</strong> als zusammenhängendes TXT oder Markdown (nach Seite gruppiert).</p>
<p><b>PDF-Werkzeuge</b> (Toolbar): Auswahl (auch PDF-Links öffnen / Ann. verschieben wenn entsperrt), Highlight, Schwärzen (REDACT-Preview), Formen per Drag;
Notiz/Stempel/Callout/Overlay per Klick; <b>Stempel ↻</b> drehen; <b>HL</b>/<b>Stift</b>/<b>Notiz</b>-Farben-Picker; <b>α Deckkraft</b>;
<b>Grau</b>-Toggle; <b>Nacht</b>-Toggle; <b>2S</b> Zwei-Seiten-Spread; <b>CS</b> Continuous Scroll; <b>Sperre</b>; <b>Rahmen</b> (CropBox); Ann. löschen;
Seite <b>⟲/⟳ drehen</b>, <b>↔/↕ spiegeln</b>, <b>leere Seite</b>, <b>duplizieren</b>.</p>
<p><b>Editor-Encoding:</b> Datei → Öffnen/Speichern mit Encoding (UTF-8 / Latin-1); Standard in Einstellungen.</p>
<p><b>Drag &amp; Drop:</b> mehrere Dateien → mehrere Tabs in der Sidebar.</p>
<p><b>PDF-Suche:</b> Sidebar-Suche highlightet Treffer auf der aktuellen Seite;
„Weiter/Zurück“ springt zum nächsten/vorherigen Treffer (auch über Docs bei Alle Docs/PDFs);
Trefferanzahl + <b>klickbare Trefferliste</b> mit <b>Kontext-Snippet</b> («Match» oder …) in der Sidebar;
Snippet-Länge (Zeichen um Match) und <b>Snippet-Ellipsis-Style</b> («…» / …) in <b>Einstellungen</b>
(gilt auch für gekürzten Text in der <b>Ann.-Liste</b>);
Trefferliste als <b>CSV/JSON</b> exportieren (Sidebar-Buttons / Bearbeiten-Menü);
<b>letzte Suchbegriffe</b> im Dropdown.</p>
<p><b>Ctrl+S:</b> speichert das Dokument und <b>flusht</b> ausstehendes Sidecar-Debounce sofort.
Dirty-Indikator am Tab auch während pending Debounce; Tooltip <b>„Speichern ausstehend…“</b>;
<b>Statusleisten-Blink</b> beim Start des Debounce — in Einstellungen <b>kurz</b> (Blink)
oder <b>aus</b> (einmaliger Status-Hinweis ohne Blink).</p>
<p><b>Vorlagen:</b> Datei → Neu → Vorlagen-Ordner öffnen… / <b>Vorlagen-Reihenfolge…</b> (Drag) /
<b>Export/Import als Zip</b> (Import mit <b>Dry-Run</b> + Konflikt-Dialog;
Konfliktliste optional als <b>TXT</b> exportieren).</p>
<p><b>Duplikate mergen:</b> Vorschau je Paar mit <b>Diff-Kurztext</b> (Text + Tags + Farbe;
max. Zeichenlänge in <b>Einstellungen</b>);
Buttons <b>Alle mergen</b> / <b>Alle behalten</b>.</p>
<p><b>Ann.-Liste:</b> gekürzter Text mit Ellipsis — Hover zeigt <b>vollen Text</b> als Tooltip;
<b>Filter-Presets</b> speichern/laden (Typ/Farbe/Tags/Seite/Suche).</p>
<p><b>Annotationen:</b> eigene Liste in der Sidebar — <b>gruppiert nach Seite</b>; Klick springt zur Annotation;
Filter-Dropdown nach Typ; <b>Nur aktuelle Seite</b>-Checkbox; <b>Tag-Filter Multi-Select</b> (ODER); <b>Tag-Cloud</b> (häufigste Tags); <b>Farben-Chips in der Statistik klickbar</b>; <b>Textsuche in der Liste</b> (optional <b>Regex</b>);
Text nachträglich editierbar; Deckkraft pro Annotation; <b>Notizfarbe unabhängig von Highlight</b>;
freie <b>Tags/Labels</b> (Ctrl+Alt+T) filterbar in der Sidebar;
<b>Zeitstempel (modified/created) in der Liste</b>;
Highlight-Drag über Text = <b>Selection→Highlight</b> (Annotation mit Inhalt).
Auswahl-Werkzeug + Text aufziehen + <code>Ctrl+C</code> = <b>Text in Zwischenablage</b> (ohne Annotation).
<code>Ctrl+Alt+N</code> = <b>Auswahl→Notiz</b> (Sticky mit vorausgefülltem Text; Checkbox <b>+Highlight</b>).
Annotation-Suche: Tag-<b>Autocomplete</b>. Session-Tabs: ziehen → Reihenfolge; <b>Andere Tabs schließen</b> (Ctrl+Shift+W).
<b>Fenster teilen</b> (Ctrl+\\); optional <b>vertikal</b> (Ctrl+Shift+\\); optional <b>Sync-Scroll</b> (Ctrl+Alt+\\).
<b>Tag-Cloud</b>: Klick setzt Filter (exklusiv), Ctrl+Klick Multi-Select; <b>Rechtsklick → filtern / Farbe ändern / umbenennen</b>.
Statusleiste <b>ungespeicherte Tabs</b>: Klick öffnet Liste zum Wechseln + <b>Speichern je Datei</b>.</p>
<p><b>PDF-Seitenlabels:</b> römische/arabische Labels aus dem PDF werden in Statusleiste und Toolbar angezeigt, wenn vorhanden.</p>
<p><b>Zwischenablage-Verlauf:</b> Bearbeiten → letzte 3 eingefügten Textschnipsel erneut einfügen.</p>
<p><b>About:</b> Hilfe → Über… — Feature-Kurzliste + FEATURES.md öffnen;
bei <b>Trial</b> zusätzlicher Keygen-Hinweis (run-keygen.bat / InstantLensKeygen.exe).</p>
<p><b>Zwei-Seiten-Ansicht:</b> Ansicht → Zwei-Seiten-Ansicht / Toolbar „2S“ / Ctrl+2 — aktuelle und nächste Seite nebeneinander; Blättern springt um 2 Seiten.</p>
<p><b>Continuous Scroll:</b> Ansicht → Continuous Scroll / Toolbar „CS“ / Ctrl+3 — Seiten untereinander scrollen (schließt Spread aus).</p>
<p><b>Arbeitsverzeichnis öffnen:</b> Datei → Ctrl+Shift+E — Ordner der aktuellen Datei (sonst CWD) im Dateimanager.</p>
<p><b>Projekt-Ordner:</b> Datei → Projekt-Ordner — Workspace wählen (letzte 5); Dialoge starten dort.</p>
<p><b>OCR gesamtes PDF:</b> Extras → OCR gesamtes PDF — Batch mit Fortschritt/Abbrechen → Editor.</p>
<p><b>PDF bereinigen:</b> PDF → PDF bereinigen — optional Metadaten entfernen, neu speichern.</p>
<p><b>Seitenbereich:</b> PDF → Seitenbereich extrahieren… (von–bis → neues PDF)
bzw. Dialog „zusammenführen / teilen / Bereich“.</p>
<p><b>Suchen und Ersetzen:</b> Bearbeiten → Ctrl+R (nur Texteditor).</p>
<p><b>Gehe zu Zeile / Seite:</b> Bearbeiten → Ctrl+G (Editor: Zeile; PDF: Seite);
PDF → Gehe zu Seite… (Ctrl+Shift+G).</p>
<p><b>Tab duplizieren:</b> Datei → Ctrl+Shift+T (Editor-Inhalt klonen);
Erneut öffnen: Ctrl+Alt+Shift+O.</p>
<p><b>Dateien vergleichen:</b> Datei → Ctrl+Alt+D — zwei Tabs/Dateien Side-by-Side (Zeilen-Diff).</p>
<p><b>Export-Profil:</b> Datei → Exportieren → Profil speichern/anwenden (DPI/Format/Ziel);
Vorbefüllung beim Seiten-Bild-Export.</p>
<p><b>Annotation-Farben:</b> Sidebar-Statistik-Chips klicken → Liste nach Farbe filtern.</p>
<p><b>Statusleiste:</b> Hint „Ctrl+Z · Letzte Aktion rückgängig“.</p>
<p><b>Zeile / Annotation duplizieren:</b> Bearbeiten → Ctrl+D (Editor: Zeile; PDF: ausgewählte Annotation).</p>
<p><b>Zeile verschieben:</b> Bearbeiten → Alt+Up / Alt+Down (aktuelle Zeile oder Auswahl).</p>
<p><b>Zeilen sortieren (A–Z):</b> Bearbeiten → Ctrl+Shift+O (Auswahl; ohne Auswahl ganze Datei).</p>
<p><b>Sonderzeichen:</b> Ansicht → Sonderzeichen anzeigen (Ctrl+Shift+.) — Tabs/Leerzeichen/Absätze.</p>
<p><b>Soft-Hyphen / NBSP:</b> Bearbeiten → Sonderzeichen einfügen — Soft-Hyphen (Ctrl+Shift+-) /
geschütztes Leerzeichen (Ctrl+Shift+Space).</p>
<p><b>Seite löschen Undo:</b> PDF → Seite löschen… — Ctrl+Z stellt Seite (+ Annotationen) wieder her;
auch Seitendrehung ist undo-fähig. Toolbar/Menü „Seiten-Historie (Undo)…“ zeigt die Liste.</p>
<p><b>Annotationsgruppe:</b> Ctrl+Alt+G oder Rechtsklick auf Gruppenkopf — Name + Farbe.
Export CSV/Bericht enthält Tags und Gruppen.</p>
<p><b>Encoding Auto:</b> Einstellungen → Editor-Encoding „Automatisch“ (BOM; optional chardet).</p>
<p><b>Quiet Startup:</b> Einstellungen → Splash beim Start überspringen.</p>
<p><b>Seiten-Favoriten:</b> PDF → ★ / Ctrl+Shift+F markiert die aktuelle Seite; Ctrl+Alt+F springt zu Favoriten
(gespeichert in Sidecar-Meta <code>page_favorites</code>); <b>Sidebar-Liste mit Nummern</b>; <b>ziehen zum Umsortieren</b>;
<b>JSON Export/Import</b>.</p>
<p><b>Auswahl-Farbe Batch:</b> Annotation(en) auswählen → Ctrl+Alt+Shift+F oder Bearbeiten → Auswahl-Farbe ändern…</p>
<p><b>Auswahl-Deckkraft:</b> Annotation(en) auswählen → <b>Toolbar-Slider</b> / Ctrl+Alt+Shift+O / α… (Sidecar force-save).</p>
<p><b>Editor-Zeilenfavoriten:</b> Ctrl+F2 oder Klick auf Zeilennummer; F2 / Shift+F2 springen; <b>Sidebar-Liste</b>;
Labels editierbar (Doppelklick/Rechtsklick); <b>JSON Export/Import</b> (<code>ildbm-v1</code>).</p>
<p><b>Tag-Cloud Kontext:</b> Rechtsklick → filtern / Farbe ändern / umbenennen.</p>
<p><b>Zuletzt geöffnet:</b> Einstellungen → Max-Anzahl + Liste leeren (auch Datei-Menü).</p>
<p><b>Statusleiste:</b> PDF → Seite x/y; Editor → Zeile x/y (wechselt mit der Ansicht).</p>
<p><b>Erste Schritte:</b> Hilfe → Erste Schritte… (Kurz-Wizard, 4 Seiten inkl. 0.6-Highlights).</p>
<p><b>Rechtschreibung:</b> Einstellungen → Rechtschreibwörterbuch (Wortliste) → F7 prüft ohne Spell-Lib;
About: Datenschutz-Hinweis (lokal, keine Telemetrie).</p>
<p><b>Startup-Deps:</b> beim Start Prüfung pypdfium2 / Tesseract; Dialog wenn etwas fehlt.</p>
<p><b>Whitespace trim on paste:</b> optional in Einstellungen — Trailing Spaces beim Einfügen entfernen.</p>
<p><b>Bracket-Match Highlight:</b> passende Klammern ()[]{} am Cursor (Einstellungen, Standard an).</p>
<p><b>Bracket-Auto-Close:</b> schließende Klammern/Anführungszeichen beim Tippen (Einstellungen, Standard an).</p>
<p><b>Kommentieren:</b> Bearbeiten → Ctrl+/ (# oder // je nach Dateityp).</p>
<p><b>Groß-/Kleinschreibung:</b> Bearbeiten → Ctrl+Shift+U (Auswahl).</p>
<p><b>Einrückung:</b> Bearbeiten → Ctrl+] / Ctrl+[ bzw. Tab / Shift+Tab (Block, aktuelle Zeile oder Auswahl).</p>
<p><b>Präsentation:</b> Ansicht → Präsentationsmodus (F5): Vollbild-PDF; Pfeiltasten/Leertaste; Esc beendet.</p>
<p><b>Farben-Favoriten:</b> Toolbar 1/2/3 — Klick = Highlight, Shift+Klick = Stift, Ctrl+Klick = Notiz, Rechtsklick = speichern.</p>
<p><b>Farbe Palette-Zyklus / Random:</b> Ctrl+Shift+C = nächste Palette-Farbe; Ctrl+Alt+Shift+C = zufällig.</p>
<p><b>Zeilennummern:</b> Ansicht → Zeilennummern (optional, auch in Einstellungen).</p>
<p><b>Editor-Minimap:</b> Ansicht → Editor-Minimap (Ctrl+Shift+I) — Linien-Übersicht + dickere Scrollbar.</p>
<p><b>PDF Graustufen:</b> Ansicht → PDF Graustufen / Toolbar „Grau“ (Ansicht + Export).</p>
<p><b>PDF Nachtmodus:</b> Ansicht → PDF Nachtmodus / Toolbar „Nacht“ (nur Invert-Ansicht, nicht speichern).</p>
<p><b>Logordner:</b> Hilfe → Logordner öffnen (Crash-/App-Logs).</p>
<p><b>Crash-Report:</b> Hilfe → Crash-Report erstellen… (ZIP aus Logordner; optional Screenshot-Pfad-Hinweis).</p>
<p><b>Lizenz:</b> bei weniger als 7 Resttagen prominent in der Statusleiste.</p>
<p><b>Seiten als Bilder:</b> PDF → Seite/Seiten als PNG/JPEG exportieren (aktuell oder alle; DPI 72/150/300).</p>
<p><b>Thumbnails:</b> in der Sidebar ziehen zum Neuordnen der Seiten (Ctrl+Z rückgängig); Größe in Einstellungen (klein/normal/groß).</p>
<p><b>Statusleiste:</b> Dateiname · Seite x/y · Seitengröße (mm/inch, klickbar) · Zoom % · Wörter/Ann. · Version · Lizenz.</p>
<p><b>Schwärzung:</b> Rechteck ziehen → PDF → Schwärzung einbrennen… (Sidecar optional leeren)
bzw. Schwärzungs-Annotationen löschen…</p>
<p><b>Export-Overwrite:</b> Existiert die Zieldatei schon, Nachfrage (Default: Nein).</p>
<p><b>Ann.-Statistik:</b> Sidebar-Footer zeigt Anzahl je Annotationstyp.</p>
<p><b>Tray:</b> Tooltip enthält App-Version; Update-Hinweis beim Start nur wenn in Einstellungen aktiv.</p>
<p><b>Extras:</b> Einstellungen (Standard-Zoom, Thumbnail-Größe, Autosave-Intervall), Batch (Fortschrittsbalken), OCR Seite/Bild und OCR gesamtes PDF (Fortschrittsdialog).</p>
<p>Vollständige Bedienung: Hilfe → Hilfe…</p>
"""


def export_shortcuts_pdf(path: str | Path) -> Path:
    """Schreibe das Keyboard-Cheat-Sheet als PDF (Qt QTextDocument)."""
    from PySide6.QtCore import QMarginsF
    from PySide6.QtGui import QPageLayout

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = QTextDocument()
    doc.setHtml(SHORTCUTS_HTML)
    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(str(path))
    layout = printer.pageLayout()
    layout.setUnits(QPageLayout.Millimeter)
    layout.setMargins(QMarginsF(12, 12, 12, 12))
    printer.setPageLayout(layout)
    doc.print_(printer)
    return path


class KeyboardHelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tastaturhilfe")
        self.resize(520, 560)
        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setHtml(SHORTCUTS_HTML)
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        btn_pdf = QPushButton("Als PDF exportieren…")
        btn_pdf.setToolTip("Keyboard-Cheat-Sheet als PDF speichern")
        btn_pdf.clicked.connect(self._export_pdf)
        buttons.addButton(btn_pdf, QDialogButtonBox.ActionRole)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.clicked.connect(self.accept)
        layout.addWidget(buttons)

    def _export_pdf(self):
        start = get_last_export_dir() or dialog_start_dir()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Tastaturhilfe als PDF",
            str(Path(start) / "InstantLensDoc-Tastaturhilfe.pdf"),
            "PDF (*.pdf)",
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        out = Path(path)
        if out.exists():
            reply = QMessageBox.question(
                self,
                "Überschreiben?",
                f"{out.name} existiert bereits. Überschreiben?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        try:
            export_shortcuts_pdf(out)
            remember_recent_dir(out)
            set_last_export_dir(out.parent)
            QMessageBox.information(self, "Tastaturhilfe", f"PDF gespeichert:\n{out}")
        except Exception as e:
            QMessageBox.warning(self, "Tastaturhilfe", f"PDF-Export fehlgeschlagen:\n{e}")
