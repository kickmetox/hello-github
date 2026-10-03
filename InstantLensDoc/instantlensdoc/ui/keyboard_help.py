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
<tr><td>Weitersuchen / Rückwärts</td><td><code>F3</code> / <code>Shift+F3</code> — PDF-Treffer-Highlight + Seiten-Nav — 0.9.0</td></tr>
<tr><td>Suchen und Ersetzen</td><td><code>Ctrl+R</code></td></tr>
<tr><td>Gehe zu Zeile / Seite</td><td><code>Ctrl+G</code> (Editor / PDF)</td></tr>
<tr><td>Gehe zu Seite (PDF-Menü)</td><td><code>Ctrl+Shift+G</code></td></tr>
<tr><td>Tab duplizieren</td><td><code>Ctrl+Alt+Shift+T</code> — 1.4.5 (früher Ctrl+Shift+T)</td></tr>
<tr><td>Theme zyklisch</td><td><code>Ctrl+Shift+T</code> System→Hell→Dunkel→System; Status-Toast „Theme: …“ — 1.4.5</td></tr>
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
<tr><td>Andere Tabs schließen</td><td><code>Ctrl+Shift+W</code> (Datei) — 0.6.2; Sidebar-Rechtsklick / Mittelklick schließen — 0.9.0</td></tr>
<tr><td>Dokument-Tab Mittelklick</td><td>Mittelklick schließt Tab; Rechtsklick → Schließen / Andere schließen — 0.9.0</td></tr>
<tr><td>Tabs Alle / Links / Rechts schließen</td><td>Sidebar-Rechtsklick + Datei-Menü; Alle: <code>Ctrl+Alt+Shift+W</code> — 0.9.1</td></tr>
<tr><td>Tab anheften / lösen</td><td>Sidebar-Rechtsklick; angeheftet bleibt bei „Alle schließen“; Indikator 📌 — 0.9.2</td></tr>
<tr><td>Tab Drag-Reorder</td><td>Dokumentliste ziehen → Reihenfolge; Session speichert `order` — 0.9.3</td></tr>
<tr><td>Tab umbenennen</td><td>Doppelklick / Rechtsklick „Umbenennen…“ → Anzeige-Label (≠ Dateiname); Session `label` — 0.9.4</td></tr>
<tr><td>Tab Originaltitel</td><td>Rechtsklick „Originaltitel“ setzt Anzeige-Label zurück; Tooltip = voller Pfad — 0.9.5</td></tr>
<tr><td>Tab Dirty-Indikator</td><td><code>*</code> bei ungespeicherten Änderungen (Label/Pin bleiben); Autosave-Toggle in Einstellungen — 0.9.6</td></tr>
<tr><td>Autosave-Intervall / Status</td><td>Einstellungen 15/30/60/120 s; Statusleiste „Gespeichert HH:MM:SS“ — 0.9.7; Pause bei Modal-Dialogen + Fehler-Blink; Ctrl+S bleibt — 0.9.8; optional .ildbak vor Überschreiben + max. 1–10 — 0.9.9</td></tr>
<tr><td>Opacity-Slider Auswahl</td><td>Toolbar-Slider steuert ausgewähltes Ann.-Objekt — 0.9.0; Undo erst beim Loslassen — 0.9.1</td></tr>
<tr><td>Stroke-Width Slider</td><td>Toolbar 1–12 px für ausgewähltes Shape; Undo beim Loslassen — 0.9.2</td></tr>
<tr><td>Fill-Color Picker</td><td>Toolbar „Füllung…“ für ausgewähltes Shape; Commit + Undo — 0.9.3</td></tr>
<tr><td>Stroke-Color Picker</td><td>Toolbar „Strich…“ Strichfarbe getrennt von Füllung; Commit + Undo — 0.9.4</td></tr>
<tr><td>Color-Presets Quick-Bar</td><td>6 Farben: Auswahl Klick=Strich · Shift=Füllung (Undo); ohne Auswahl HL/Stift/Notiz — 0.9.5; Rechtsklick speichern/zurücksetzen + Settings — 0.9.6; Export/Import JSON <code>ildcolors-v1</code> — 0.9.7; Alle zurücksetzen + Werksstandard (Factory) in Settings — 0.9.8; Factory-Bestätigung + Rückgängig — 0.9.9</td></tr>
<tr><td>PDF-Suche Aa / Wort</td><td>Suchleisten-Toggles Case-sensitive + Whole-word — 0.9.2</td></tr>
<tr><td>PDF-Suche Regex</td><td>Suchleisten-Toggle `.*`; Fehlerstatus in Statusleiste — 0.9.3</td></tr>
<tr><td>PDF-Suche CSV-Export</td><td>Treffer als CSV: Seite, Offset, Snippet — 0.9.4</td></tr>
<tr><td>PDF-Suche JSON-Export</td><td>Treffer als JSON (`ildsearch-v1`): Seite, Offset, Snippet — 0.9.5</td></tr>
<tr><td>PDF-Suche → Highlight</td><td>Button HL / Menü: Treffer der aktuellen Seite als Highlight-Annotationen (Batch + Undo) — 0.9.6; Checkbox/Menü „alle Seiten“ (ein Undo) — 0.9.7; optionaler Tag (Input-Dialog) — 0.9.8; Tag-Combobox aus zuletzt genutzten Tags — 0.9.9</td></tr>
<tr><td>Session-Toggles</td><td>Einstellungen: Fenstergeometrie + offene Tabs getrennt — 0.9.0</td></tr>
<tr><td>Session Last-Page / Scroll</td><td>Seite + Scroll-Position pro Tab speichern/wiederherstellen — 0.9.1</td></tr>
<tr><td>Session Zoom pro Tab</td><td>Zoom-Level speichern/wiederherstellen (Vorrang vor Fit/Default) — 0.9.2</td></tr>
<tr><td>Session Splitter</td><td>Sidebar/Viewer-Größen speichern/wiederherstellen — 0.9.3</td></tr>
<tr><td>Session Theme / aktiver Tab</td><td>Theme dark/light + aktiver Tab-Index speichern/wiederherstellen — 0.9.4</td></tr>
<tr><td>Session Panels Thumb/Ann/Bookmark</td><td>Panel-Sichtbarkeit speichern/wiederherstellen — 0.9.5</td></tr>
<tr><td>Session Suche Aa/Wort/Regex</td><td>Suchfilter-Toggles speichern/wiederherstellen — 0.9.6</td></tr>
<tr><td>Session Ann.-Werkzeug</td><td>Zuletzt genutztes Annotations-Werkzeug speichern/wiederherstellen — 0.9.7</td></tr>
<tr><td>Session Ann.-Opacity / Stroke</td><td>Letzte Deckkraft und Strichstärke speichern/wiederherstellen — 0.9.8</td></tr>
<tr><td>Session Fill-/Stroke-Color</td><td>Letzte Fill- und Stroke-Farb-Defaults speichern/wiederherstellen — 0.9.9</td></tr>
<tr><td>About Lizenz / Changelog</td><td>Hilfe → Info: Version, Lizenzstatus, Kontakt ame@sellerbach.de, Changelog-Kurzliste — 1.0.0</td></tr>
<tr><td>Backup jetzt / Ordner</td><td>Datei → Backup jetzt; max. 3 Versuche; Log letzte 20; Filter Erfolg/Fehler; Sortierung neueste zuerst (Toggle); Hinweis leere Liste; Export TXT (Zeitstempel + UTF-8 BOM); Doppelklick öffnet Datei/Ordner — 1.0.9</td></tr>
<tr><td>PDF Dokument drucken</td><td>PDF → Dokument drucken… (Seitenbereich + DPI + Graustufen; Vorschau PageUp/Down·Home/End + +/- Zoom + Fit-Page + Mausrad + Seitenwahl Mehrseiten; Fortschritt; Abbruch → Cleanup); Ctrl+P = Seite — 1.0.9</td></tr>
<tr><td>Willkommen</td><td>Weiterarbeiten disabled+Tooltip wenn Session fehlt/leer; sonst Tabs + Pfad-Snippet; Esc leert Filter → Fokus Liste; Clear + Treffer; Enter/Entf; Drag&amp;Drop — 1.0.9</td></tr>
<tr><td>About / Lizenz Ablauf</td><td>Banner Fokus-Ring + Enter→Aktivierung + Esc schließt + AccessibleName; Icon + Dismiss + Schließen-X; Persistenz dismiss_date; Farbe Warnung vs. abgelaufen; Ablauf TT.MM.JJJJ — 1.0.9</td></tr>
<tr><td>OCR gesamtes PDF</td><td>Extras → „Als Defaults speichern“ → Toast „OCR-Defaults gespeichert“ (Dauer Settings 1/2/3 s + Accessibility-Announcement) + Feld-Highlight; Fehler anhängen persistiert; Seitenfehler + Teilergebnis; von–bis → Textdatei-Tab — 1.1.9</td></tr>
<tr><td>PDF zusammenführen</td><td>Thumbnail-Klick → Readonly-Tab Banner „Vorschau“ + „Zum Bearbeiten öffnen“; Toggle Readonly schließen auch im Merge-Dialog (gleicher Persistenz-Tooltip in Settings); Drag&amp;Drop + Duplikat-Warnung + Doppelklick/Alle/Summe — 1.1.9</td></tr>
<tr><td>PDF Seitenbereich / Split</td><td>PDF → Seitenbereich extrahieren… / Teilen: Bereiche z. B. 1-3,5,8-10; Pfad-Log In Tabs öffnen: Status geöffnet X, übersprungen Y; Log-Footer klickbar → Filter übersprungene (Toggle); Pfad kopieren; Mehrfachauswahl — 1.2.9</td></tr>
<tr><td>Ann. Export JSON/Flatten</td><td>PDF → Annotationen exportieren (JSON / Flatten)…: Quick-Insert {stem}/{page}/{date}; Ctrl+Z lokal; Reset-Template → Live-Vorschau + Fokus mit Selektion ganzer Default-Text; Bestätigung nur bei Abweichung — 1.2.9</td></tr>
<tr><td>Text-Diff Panel</td><td>Datei → Text-Diff (offene Tabs)… (Ctrl+Alt+D): Wrap-Blink Dauer kurz/mittel/lang + System-Beep vs. stumm; Status Änderung i/n; F7/Shift+F7 — 1.2.9</td></tr>
<tr><td>run.bat Deps / pip</td><td>Windows-Start: gewählte Python-Binary als „gefunden: …“ inkl. python --version; %ILD_PYTHON% ungültig/leer → Fallback py -3 → python → python3; --help; .venv; --yes/-y; Exit 0/1 — 1.2.9</td></tr>
<tr><td>CLI Start</td><td><code>python -m instantlensdoc --open FILE</code> · <code>--version</code>/−V — 1.5.0</td></tr>
<tr><td>PDF-Metadaten</td><td>PDF → Metadaten: Titel/Autor/Betreff/Keywords (pikepdf DocInfo+XMP) Speichern — 1.5.0</td></tr>
<tr><td>Seiten als Bilder</td><td>PDF → aktuell / Seitenbereich (1-3,5) / alle → PNG/JPEG; DPI 72/150/300 — 1.5.0</td></tr>
<tr><td>Signatur (Bild)</td><td>Bildstempel Sidecar; optional Flatten-PDF — 1.5.0</td></tr>
<tr><td>PDF-Vergleich Diff</td><td>Diff-PNG Reset: Bestätigung nur bei Abweichung; Fokus+Selektion wie Ann.-Template — 1.4.5</td></tr>
<tr><td>Batch-Umbenennen</td><td>Undo-Skip: „rückgängig X, übersprungen Y“; kopierbarer Text — 1.4.5</td></tr>
<tr><td>Annotation-Suche offen</td><td>Ctrl+Shift+F3: CSV Neu-Scan Fortschritt bei vielen Docs + Abbruch — 1.4.5</td></tr>
<tr><td>Theme System</td><td>Ctrl+Shift+T zyklisch; Status-Toast „Theme: …“; Hilfe/About — 1.4.5</td></tr>
<tr><td>AcroForm-Sidebar</td><td>CSV Esc ohne Export; Enter auf OK; Zähler N von M; Default persistiert — 1.3.6</td></tr>
<tr><td>Redactions anwenden</td><td>Status „Sidecar übersprungen“; Fortsetzen-Option Settings merken — 1.3.6</td></tr>
<tr><td>Bookmarks ↔ Outlines</td><td>Fehlerdialog Retry-Zähler „Versuch k/3“; max. 3 wie Backup — 1.3.6</td></tr>
<tr><td>Thumbnail Lazy-Load</td><td>Prefetch-Label grau wenn Lazy aus (unter Schwellwert), sonst aktiv — 1.3.6</td></tr>
<tr><td>Alle Ann. auf Seite löschen</td><td>Bearbeiten → bei 0 Treffern Sticky-Status Statusleiste bis nächste Ann.-Aktion / Seiten-/Dokumentwechsel / Undo/Redo + i18n DE + Menü/Aktion no-op + Button disabled; Undo „N Annotationen (gefiltert)“ — 1.1.9</td></tr>
<tr><td>Keygen</td><td>Reveal Auto-Hide 5/10/30 s + Countdown „pausiert“ (Tooltip „Countdown pausiert (Fenster ohne Fokus)“) / Esc maskiert + History maskiert (letzte 4) / Doppelklick kopiert + Clear + .txt + --days — 1.1.9</td></tr>
<tr><td>Willkommen-Startseite</td><td>Ohne Tabs: Recent + Dokument öffnen / Leeres Text — 1.0.0</td></tr>
<tr><td>PDF-Trefferliste</td><td>Sidebar Seite + Snippet klickbar → Sprung + Highlight — 0.9.1</td></tr>
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
<tr><td>Thumbnail Drehen 90°</td><td>Rechtsklick L/R; <code>Ctrl+Z</code> Undo — 0.8.3</td></tr>
<tr><td>Thumbnail Seite duplizieren</td><td>Rechtsklick → Duplizieren; <code>Ctrl+Z</code> Undo — 0.8.5</td></tr>
<tr><td>Thumbnail Mehrfachauswahl</td><td><code>Shift</code>+Klick; Batch-Duplizieren/Löschen — 0.8.6; Batch-Drehen L/R — 0.8.7; als PDF extrahieren — 0.8.8; als neues Dokument öffnen — 0.8.9</td></tr>
<tr><td>Thumbnail Seite löschen</td><td>Rechtsklick → Löschen…; Bestätigung; <code>Ctrl+Z</code> Undo — 0.8.4</td></tr>
<tr><td>Annotation Mehrfachauswahl</td><td><code>Shift</code>+Klick; gemeinsame Verschiebung — 0.8.3</td></tr>
<tr><td>Auswahl ausrichten / verteilen</td><td>L/C/R + oben/mittig/unten (≥2); H/V verteilen (≥3) — Toolbar/Menü — 0.8.4/0.8.5</td></tr>
<tr><td>Auswahl Gruppieren / Entgruppieren</td><td>temporäre <code>group_id</code> Sidecar; Toolbar/Menü — 0.8.6</td></tr>
<tr><td>Gruppen-Auswahl / Sperre</td><td>Klick → alle Mitglieder; Gruppen-Sperre Toolbar/Menü <code>Ctrl+Alt+Shift+L</code> — 0.8.7</td></tr>
<tr><td>Gruppe umbenennen / Farbe</td><td>Sidecar-Markierung; Toolbar/Menü <code>Ctrl+Alt+Shift+N</code> — 0.8.8</td></tr>
<tr><td>Gruppe filtern / JSON</td><td>Rechtsklick → „Nur diese Gruppe“; Gruppe als JSON exportieren — 0.8.9</td></tr>
<tr><td>Thumbnail als PDF extrahieren</td><td>Rechtsklick Auswahl → neues PDF — 0.8.8</td></tr>
<tr><td>Thumbnail als neues Dokument</td><td>Rechtsklick Auswahl → speichern und in neuem Tab öffnen — 0.8.9</td></tr>
<tr><td>Seitennummer-Overlay</td><td>Ansicht / Einstellungen / Toolbar „Nr.“ — 0.8.3; Deckkraft — 0.8.4; Schriftgröße — 0.8.5; Position unten-/oben-mitte — 0.8.6; Format <code>{page}</code>/<code>{pages}</code> — 0.8.7; Start-Offset — 0.8.8; erste/letzte Seite aus — 0.8.9</td></tr>
<tr><td>Editor Tab-Breite</td><td>Einstellungen: 2 / 4 / 8 Zeichen — 0.8.5</td></tr>
<tr><td>Editor Soft-Tabs</td><td>Einstellungen: Soft-Tabs (Leerzeichen) vs. echte Tabs — 0.8.6</td></tr>
<tr><td>Editor Mehrzeilen-Indent</td><td><code>Tab</code>/<code>Shift+Tab</code> bei Mehrzeilen-Auswahl; sonst Tab einfügen — 0.8.7</td></tr>
<tr><td>Editor Einrückungs-Guides</td><td>Ansicht / Einstellungen: vertikale Linien an Tab-Stops — 0.8.8</td></tr>
<tr><td>Editor Aktuelle Zeile</td><td>Ansicht / Einstellungen: aktuelle Zeile hervorheben — 0.8.9</td></tr>
<tr><td>Zeilennummern Toggle</td><td>Ansicht ↔ Settings, persistiert — 0.8.3</td></tr>
<tr><td>Wortumbruch Toggle</td><td>Ansicht ↔ Settings, persistiert (<code>Ctrl+Shift+W</code>) — 0.8.4</td></tr>
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
<p><b>OCR gesamtes PDF:</b> Extras → OCR gesamtes PDF — Button <b>„Als Defaults speichern“</b>
→ Toast <b>„OCR-Defaults gespeichert“</b> (Dauer Settings <b>1/2/3 s</b> + Accessibility-Announcement)
+ Feld-Highlight; Toggle „Fehler anhängen“ persistiert;
Seitenfehler-Abschnitt / Teilergebnis; optional <b>von–bis</b> → Textdatei-Tab — 1.1.9.</p>
<p><b>PDF zusammenführen:</b> Thumbnail-Klick → Readonly-Tab mit Banner <b>„Vorschau“</b> +
<b>„Zum Bearbeiten öffnen“</b>; Toggle Readonly schließen <b>auch im Merge-Dialog</b>
(gleicher Persistenz-Tooltip in Settings); Drag&amp;Drop, Duplikat-Warnung, Doppelklick/Alle/Summe — 1.1.9.</p>
<p><b>Alle Annotationen auf Seite löschen:</b> Bearbeiten → bei 0 Treffern
<b>Sticky-Status Statusleiste</b> bis nächste Ann.-Aktion / Seiten-/Dokumentwechsel / <b>Undo/Redo</b>
+ i18n DE + Menü/Aktion no-op;
Undo <b>„N Annotationen (gefiltert)“</b> — 1.1.9.</p>
<p><b>Keygen:</b> Reveal Auto-Hide <b>5/10/30 s</b> + Countdown-Label <b>„pausiert“</b>
(Tooltip <b>„Countdown pausiert (Fenster ohne Fokus)“</b>) /
<b>Esc</b> maskiert; History maskiert (letzte 4); Doppelklick kopiert; <b>Clear History</b>;
Speichern als <b>.txt</b> + CLI <b>--days</b> — 1.1.9.</p>
<p><b>PDF bereinigen:</b> PDF → PDF bereinigen — optional Metadaten entfernen, neu speichern.</p>
<p><b>Seitenbereich:</b> PDF → Seitenbereich extrahieren… (z. B. 1-3,5,8-10; DE-Validierung + Seitenanzahl-Vorschau — 1.2.1)
bzw. Dialog „zusammenführen / teilen / Bereich“.</p>
<p><b>Suchen und Ersetzen:</b> Bearbeiten → Ctrl+R (nur Texteditor).</p>
<p><b>Gehe zu Zeile / Seite:</b> Bearbeiten → Ctrl+G (Editor: Zeile; PDF: Seite);
PDF → Gehe zu Seite… (Ctrl+Shift+G).</p>
<p><b>Tab duplizieren:</b> Datei → Ctrl+Alt+Shift+T (Editor-Inhalt klonen) — 1.4.5;
Theme zyklisch: Ctrl+Shift+T System→Hell→Dunkel (Status-Toast „Theme: …“); Erneut öffnen: Ctrl+Alt+Shift+O.</p>
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
<p><b>Seiten als Bilder:</b> PDF → aktuell / Seitenbereich (z. B. 1-3,5) / alle als PNG/JPEG; DPI 72/150/300 — 1.5.0.</p>
<p><b>PDF-Metadaten:</b> Titel/Autor/Betreff/Keywords lesen+schreiben (pikepdf) — 1.5.0.</p>
<p><b>Signatur (Bild):</b> Bildstempel Sidecar; optional Flatten — 1.5.0.</p>
<p><b>CLI:</b> <code>python -m instantlensdoc --open FILE</code> · <code>--version</code> — 1.5.0.</p>
<p><b>Thumbnails:</b> in der Sidebar ziehen zum Neuordnen der Seiten (Ctrl+Z rückgängig); Größe in Einstellungen (klein/normal/groß).</p>
<p><b>Statusleiste:</b> Dateiname · Seite x/y · Seitengröße (mm/inch, klickbar) · Zoom % · Wörter/Ann. · Version · Lizenz.</p>
<p><b>PDF-Vergleich:</b> Diff-PNG Reset Bestätigung nur bei Abweichung; Fokus+Selektion — 1.4.5</p>
<p><b>Batch-Umbenennen:</b> Undo „rückgängig X, übersprungen Y“ kopierbar — 1.4.5</p>
<p><b>Annotation-Suche:</b> CSV Neu-Scan Fortschritt + Abbruch — 1.4.5</p>
<p><b>Theme:</b> Ctrl+Shift+T zyklisch; Status-Toast „Theme: …“; siehe Hilfe/About — 1.4.5</p>
<p><b>Schwärzung / Redactions:</b> Rechteck ziehen → Sidecar; Status „Sidecar übersprungen“;
Fortsetzen-Option in Settings merken — 1.3.6</p>
<p><b>AcroForm:</b> CSV Esc ohne Export; Enter auf OK; Zähler N von M — 1.3.6</p>
<p><b>Bookmarks/Outlines:</b> Fehlerdialog Retry-Zähler „Versuch k/3“ — 1.3.6</p>
<p><b>Thumbnails:</b> Prefetch-Label grau wenn Lazy aus (unter Schwellwert), sonst aktiv — 1.3.6</p>
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
