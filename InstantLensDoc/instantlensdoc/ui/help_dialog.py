"""Hilfe- und About-Dialoge."""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
)

from instantlensdoc import __series__, __version__
from instantlensdoc.config import CONTACT_EMAIL, DISPLAY_NAME, ROOT, VENDOR, icon_paths_for_qt
from instantlensdoc.core.logging_setup import log_dir


def changelog_short_html(max_versions: int = 4, changelog_path: Path | None = None) -> str:
    """Kurzliste aus CHANGELOG.md: aktuelle Version + Vorgänger (Bullet-Zeilen)."""
    path = Path(changelog_path) if changelog_path is not None else ROOT / "CHANGELOG.md"
    if not path.is_file():
        return f"<p>CHANGELOG.md nicht gefunden. Version {__version__}.</p>"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return f"<p>CHANGELOG.md nicht lesbar. Version {__version__}.</p>"
    sections: list[tuple[str, list[str]]] = []
    current_title = ""
    bullets: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^##\s+(\S+)", line)
        if m:
            if current_title:
                sections.append((current_title, bullets))
                if len(sections) >= max_versions:
                    current_title = ""
                    break
            current_title = m.group(1).strip()
            bullets = []
            continue
        if current_title and line.startswith("- ") and len(bullets) < 4:
            bullets.append(line[2:].strip())
    if current_title and len(sections) < max_versions:
        sections.append((current_title, bullets))
    if not sections:
        return f"<p>Keine Changelog-Einträge. Version {__version__}.</p>"
    parts = ["<h3>Changelog (Kurz)</h3><ul>"]
    for ver, items in sections[:max_versions]:
        if items:
            preview = "; ".join(items[:3])
            # Markdown-Fett grob entfernen
            preview = preview.replace("**", "")
            if len(preview) > 160:
                preview = preview[:157] + "…"
            parts.append(f"<li><b>{ver}</b> — {preview}</li>")
        else:
            parts.append(f"<li><b>{ver}</b></li>")
    parts.append("</ul>")
    parts.append("<p>Vollständig: CHANGELOG.md</p>")
    return "".join(parts)


HELP_HTML = f"""
<h2>InstantLens Doc — Hilfe</h2>
<p>Moderne Textverarbeitung mit PDF-Annotator, OCR-Bridge und Formulargenerator.</p>
<p><b>Kurz-Wizard:</b> Hilfe → Erste Schritte… (4 Seiten, inkl. 0.6-Highlights).</p>
<h3>Erste Schritte</h3>
<ul>
<li><b>Datei → Öffnen</b>: TXT, MD, HTML, DOCX, PDF, Bilder</li>
<li><b>Extras → Einstellungen</b>: Theme, <b>UI-Sprache DE/EN</b>, OCR, Export-Qualität,
    <b>Standard-Zoom</b> (Prozent / Fit-Width / Fit-Page), <b>Autosave-Intervall</b>, Soft-Wrap, <b>Sonderzeichen anzeigen</b>,
    optional <b>Trailing Whitespace trimmen</b>, optional <b>Whitespace trim on paste</b>,
    optional <b>Bracket-Match Highlight</b>,
    optional <b>Bracket-Auto-Close</b>,
    optional <b>Minimieren in System-Tray</b>,
    optional <b>Backup .bak beim Speichern</b>, optional <b>Autosave-Backup .ildbak</b> (max. 1–10),
    <b>Seitengröße-Einheit mm/inch</b>,
    optional <b>Fenstergeometrie</b> und <b>offene Tabs</b> beim Start (getrennte Toggles),
    <b>PDF-Toolbar-Gruppen</b> ein-/ausblenden,
    optional <b>PDF Zwei-Seiten-Ansicht (Spread)</b>, optional <b>PDF Continuous Scroll</b>,
    <b>Doc-Split Layout horizontal/vertikal</b>,
    Update-Hinweis (nur wenn aktiv), Pfade;
    <b>Auf Standard zurücksetzen</b></li>
<li><b>Datei → Zuletzt geöffnet</b>: Menü + Seitenleiste (persistiert); Einstellungen: Max-Anzahl + Clear</li>
<li><b>Datei → Speichern unter</b> (Ctrl+Alt+Shift+U): Text → Dokument; PDF → Annotation-Sidecar wählen (PDF unverändert) — 1.9.5 (Ctrl+Shift+S = Standard-Stempel ★)</li>
<li><b>Datei → Alles speichern</b> (Ctrl+Alt+Shift+S): aktuelles Doc + PDF-Sidecars offener Tabs</li>
<li><b>Datei → Als Kopie speichern</b> (Ctrl+Alt+S): PDF + Sidecar kopieren (Doc bleibt offen); Editor → Speichern unter</li>
<li><b>Datei → Arbeitsverzeichnis öffnen</b> (Ctrl+Shift+E): Ordner der aktuellen Datei bzw. Prozess-CWD</li>
<li><b>Datei → Projekt-Ordner</b>: Workspace wählen (letzte 5); Dialoge starten im aktiven Ordner</li>
<li><b>Datei → Exportieren</b>: Editor-Inhalt als HTML, DOCX oder PDF (zuletzt genutzter Ordner wird gemerkt);
    <b>Export-Profil</b> speichern/anwenden (DPI / Format / Ziel)</li>
<li><b>OCR gesamtes PDF</b>: Button <b>„Als Defaults speichern“</b> → Toast <b>„OCR-Defaults gespeichert“</b> (Dauer Settings <b>1/2/3 s</b> + Accessibility-Announcement) + Feld-Highlight; Defaults vorbelegt; Toggle <b>„Fehler anhängen“</b> Settings-persistiert; Seitenfehler → Abschnitt im TXT; Abbruch behält Teilergebnis; optional <b>Seitenbereich von–bis</b>; Fortschritt → <b>Textdatei-Tab</b> — 1.1.9</li>
<li><b>PDF zusammenführen</b>: Thumbnail-Klick → Readonly-Tab mit Banner <b>„Vorschau“</b> + <b>„Zum Bearbeiten öffnen“</b>; Toggle Readonly schließen <b>auch im Merge-Dialog</b> (gleicher Persistenz-Tooltip in Settings); Vorschau-Thumbnail; Drag&amp;Drop; Duplikat-Warnung; Doppelklick/Alle/Seiten-Summe — 1.1.9</li>
<li><b>Forms CSV</b>: <b>Esc</b> schließt ohne Export; <b>Enter</b> auf OK startet Export; Zähler N von M — 1.3.6</li>
<li><b>Redaction Sidecar</b>: Status <b>„Sidecar übersprungen“</b>; Fortsetzen-Option in Settings merken — 1.3.6</li>
<li><b>Outlines Export</b>: Fehlerdialog Retry-Zähler <b>Versuch k/3</b> — 1.3.6</li>
<li><b>Thumbnail Prefetch</b>: Live-Label <b>grau</b> wenn Lazy aus (unter Schwellwert), sonst aktiv — 1.3.6</li>
<li><b>AcroForm-Sidebar</b>: Feldliste <b>Name/Typ/Wert</b>; Klick → Seite; Textfeld-Wert speichern via <b>pikepdf</b> — 1.3.0</li>
<li><b>Redactions anwenden</b>: Rechteck → Sidecar; Menü erzeugt <b>neues PDF</b> mit schwarzen Flächen — 1.3.0</li>
<li><b>Bookmarks ↔ Outlines</b>: Import aus PDF-Outlines / Export als PDF-Outlines — 1.3.0</li>
<li><b>Thumbnail Lazy-Load</b>: große PDFs <b>&gt;50 Seiten</b> mit Platzhaltern für alle Seiten — 1.3.0</li>
<li><b>PDF Seitenbereich / Split</b>: Bereiche <b>1-3,5,8-10</b>; Pfad-Log <b>In Tabs öffnen</b>: Status <b>geöffnet X, übersprungen Y</b>; <b>Log-Footer klickbar</b> → Filter übersprungene (Toggle); Pfad kopieren; Mehrfachauswahl; Ordner der Auswahl — 1.2.9</li>
<li><b>Annotationen exportieren (JSON / Flatten)</b>: Quick-Insert <b>{{stem}}</b>/<b>{{page}}</b>/<b>{{date}}</b>; <b>Ctrl+Z lokal</b>; <b>Reset-Template</b> → Live-Vorschau + Fokus mit Selektion ganzer Default-Text — 1.2.9</li>
<li><b>Text-Diff Panel</b>: Wrap-Blink Dauer Settings <b>kurz/mittel/lang</b> + <b>System-Beep vs. stumm</b>; Status <b>Änderung i/n</b>; F7/Shift+F7 — 1.2.9</li>
<li><b>run.bat</b>: gewählte Binary als <b>gefunden: …</b> inkl. <b>python --version</b>; bei ungültigem/leerem <b>%ILD_PYTHON%</b> Fallback <b>py -3 → python → python3</b>; --help; .venv; --yes; Exit 0/1 — 1.2.9</li>
<li><b>Alle Annotationen auf Seite löschen</b>: bei <b>0 gefilterten Treffern</b> Sticky-Status in Statusleiste bis nächste Ann.-Aktion / Seiten-/Dokumentwechsel / <b>Undo/Redo</b> + i18n DE + Menü/Aktion no-op + Button disabled; Undo <b>„N Annotationen (gefiltert)“</b> — 1.1.9</li>
<li><b>Keygen</b>: Reveal Auto-Hide <b>5/10/30 s</b> + <b>Countdown</b> (Label <b>„pausiert“</b>; Tooltip <b>„Countdown pausiert (Fenster ohne Fokus)“</b>) / <b>Esc</b> maskiert; History maskiert (letzte 4); Doppelklick kopiert; Clear History; .txt; --days — 1.1.9</li>
<li><b>Datei → Drucken</b> (Ctrl+P): Editor oder aktuelle PDF-Seite (Qt Print); <b>PDF → Dokument drucken…</b> Seitenbereich + DPI + Graustufen; <b>Vorschau PageUp/Down·Home/End + +/- Zoom + Fit-Page + Mausrad + Seitenwahl</b> bei Mehrseiten; Fortschritt; Abbruch → Cleanup — 1.0.9</li>
<li><b>Datei → Backup jetzt</b> / <b>Backup-Ordner öffnen…</b>: manuelles Backup; max. 3 Versuche; Log letzte 20; Filter Erfolg/Fehler; <b>Sortierung neueste zuerst</b> (Toggle); Hinweis bei leerer Liste; <b>Export TXT</b> (Zeitstempel-Name, UTF-8 BOM); Doppelklick öffnet Datei/Ordner — 1.0.9</li>
<li><b>Willkommen</b>: <b>Weiterarbeiten</b> deaktiviert + Tooltip wenn Session fehlt/leer; sonst Tab-Anzahl + Pfad-Snippet; Esc leert Filter → Fokus Liste; Clear + Treffer; Enter/Entf; Drag&amp;Drop — 1.0.9</li>
<li><b>Hilfe → Info / Lizenz</b>: Banner <b>Fokus-Ring</b> + <b>Enter → Aktivierung</b> + Esc schließt + AccessibleName; Icon + Dismiss + Schließen-X; Persistenz <b>dismiss_date</b>; Farbe Warnung vs. abgelaufen — 1.0.9</li>
<li><b>Seitenleiste</b>: Suche (inkl. letzte Suchbegriffe), „Alle Docs“-Volltext, Zuletzt geöffnet, Dokumente,
    Lesezeichen/Outline (+/− hinzufügen/löschen), <b>Formularfelder (AcroForm)</b> Name/Typ/Wert,
    <b>Annotationen</b> (klickbar, <b>nach Seite gruppiert</b>,
    <b>Filter nach Typ</b>, <b>Textsuche in der Liste</b> (optional <b>Regex</b>), <b>Statistik je Typ</b>,
    <b>Farben-Chips klickbar filtern</b>, <b>Zeitstempel</b>,
    <b>Filter nur aktuelle Seite</b>), Markierungen/Treffer</li>
<li><b>Bearbeiten → Rückgängig/Wiederholen</b>: Editor-Text <i>oder</i> PDF-Annotationen/Overlay-Text (Ctrl+Z / Ctrl+Y);
    Statusleisten-Hint „Ctrl+Z · … rückgängig“ (benannt, z. B. Tag umbenennen)</li>
<li><b>Bearbeiten → Suchen und Ersetzen</b> (Ctrl+R): Find/Replace im Texteditor</li>
<li><b>Bearbeiten → Gehe zu Zeile / Seite</b> (Ctrl+G): Editor → Zeile; PDF → Seite (auch PDF → Gehe zu Seite…, Ctrl+Shift+G)</li>
<li><b>Datei → Tab duplizieren</b> (Ctrl+Alt+Shift+T): Editor-Inhalt als neues Dokument klonen — 1.4.5;
    <b>Ansicht → Theme zyklisch</b> (Ctrl+Shift+T): System→Hell→Dunkel→System; Status-Toast „Theme: …“;
    <b>Text-Diff (offene Tabs)</b> (Ctrl+Alt+D): Wrap-Blink Dauer kurz/mittel/lang · System-Beep/stumm · Änderung i/n · Wrap-around · F7/Shift+F7 · Sync-Scroll · Ignore-Whitespace · Diff-TXT — 1.2.9;
    <b>Erneut öffnen</b> (Ctrl+Alt+Shift+O): Datei vom Datenträger neu laden</li>
<li><b>Bearbeiten → Zeile / Annotation duplizieren</b> (Ctrl+D): Editor Zeile/Auswahl; PDF ausgewählte Annotation (auch Ctrl+Shift+D)</li>
<li><b>Bearbeiten → Zeile verschieben</b> (Alt+Up / Alt+Down)</li>
<li><b>Bearbeiten → Zeilen sortieren (A–Z)</b> (Ctrl+Shift+O): Auswahl alphabetisch</li>
<li><b>Bearbeiten → Auswahl markieren</b> (Ctrl+H): Markierung im Editor + Eintrag in der Seitenleiste</li>
<li><b>Bearbeiten → Groß-/Kleinschreibung umschalten</b> (Ctrl+Shift+U): Auswahl GROSS → klein → Titel</li>
<li><b>Bearbeiten → Alles groß-/kleinschreiben</b> (Ctrl+Alt+Shift+U / L): gesamte Datei</li>
<li><b>Bearbeiten → Textbausteine</b>: 3 gespeicherte Snippets (Einfügen Ctrl+Alt+1..3; Auswahl → Slot)</li>
<li><b>Bearbeiten → Zwischenablage-Verlauf</b>: letzte 3 eingefügten Textschnipsel erneut einfügen</li>
<li><b>Datei → Neu</b>: leeres Dokument oder Vorlage <b>Brief</b> / <b>Notiz</b></li>
<li><b>Bearbeiten → Einrückung erhöhen/verringern</b> (Ctrl+] / Ctrl+[; Tab / Shift+Tab Block)</li>
<li><b>Ansicht</b>: Zoom +/−, Fit-Page (Ctrl+0), Fit-Width (Ctrl+9), Höhe (Ctrl+8), 100&nbsp;% (Ctrl+1),
    <b>Aktuellen Zoom als Standard</b> (Ctrl+Shift+0);
    <b>Präsentationsmodus</b> (F5 Vollbild; Space Pause; Countdown; Intervalle 3/5/10/30 — 1.7.2);
    <b>Lesezeichen-Leiste</b> (Label·neuer Tab·Duplikat-Pfade — 1.7.2); <b>Hell/Dunkel</b>-Design umschalten; optionale <b>Zeilennummern</b>; <b>Markdown-Vorschau</b> (Split, Ctrl+Shift+M);
    <b>Soft-Wrap</b>; <b>Sonderzeichen anzeigen</b> (Ctrl+Shift+.);
    <b>PDF Graustufen</b>; <b>PDF Nachtmodus</b> (Invert-Ansicht, nur Darstellung);
    <b>Zwei-Seiten-Ansicht (Spread)</b> (Ctrl+2 / Toolbar 2S);
    <b>Continuous Scroll</b> (Ctrl+3 / Toolbar CS — Seiten untereinander, schließt Spread aus);
    <b>Seitenlabels</b> (römisch/arabisch) in Status/Toolbar wenn im PDF vorhanden;
    <b>Annotation-Layer</b> ein/aus (Ctrl+Shift+A);
    <b>Annotationen sperren</b> (Ctrl+Shift+L — nicht verschiebbar);
    <b>Seitenrahmen / CropBox</b> Overlay (Ctrl+Shift+B);
    <b>Druckermarken</b> Overlay (Ctrl+Alt+M)</li>
<li><b>Datei → Öffnen/Speichern mit Encoding</b>: UTF-8, Latin-1 oder <b>Automatisch</b> (BOM / optional chardet)</li>
<li><b>Drag &amp; Drop</b>: eine oder mehrere Dateien auf das Fenster ziehen → mehrere Tabs</li>
<li><b>Autosave</b>: Textdokumente (mit Pfad) und PDF-Annotationen — Intervall 15/30/60/120 s; Status „Gespeichert HH:MM:SS“;
    optional <b>.ildbak</b> vor Überschreiben (max. 1–10);
    Pause bei Modal-Dialogen; Ctrl+S bleibt; kurzer Status-Blink bei Fehler</li>
<li><b>PDF</b>: Blättern, Zoom/Fit (debounced + Cache), <b>⟲/⟳ drehen</b> / <b>↔/↕ spiegeln</b> (speichert),
    <b>Graustufen</b> (Ansicht + Bild-Export), <b>Nachtmodus</b> (nur Ansicht, nicht speichern),
    <b>leere Seite / duplizieren</b>, Seite löschen (<b>Undo Ctrl+Z</b> / <b>Historie-Liste</b>), Seiten neu anordnen;
    <b>Annotationsgruppen</b> umbenennen/Farbe (Ctrl+Alt+G); <b>Seiten-Favoriten</b> (★ / Ctrl+Shift+F, springen Ctrl+Alt+F, <b>Sidebar-Liste mit Nummern</b>, <b>Export/Import JSON</b>);
    <b>Auswahl-Farbe Batch</b> (Ctrl+Alt+Shift+F); <b>Auswahl-Deckkraft</b> (Toolbar-Slider / Ctrl+Alt+Shift+O / α…);
    Soft-Hyphen / NBSP im Editor; <b>Zeilen-Lesezeichen</b> (Ctrl+F2 / Klick Zeilennummer, F2/Shift+F2, <b>Labels editierbar</b>);
    <b>Rechtschreibung</b> per lokaler Wortliste (F7, Pfad in Einstellungen);
    Startup-Check pypdfium2/Tesseract; Splash optional überspringbar;
    <b>PDF-Links (http/https)</b> per Auswahl-Werkzeug / Ctrl+Klick öffnen;
    Annotationen: Highlight (Drag, <b>Selection→Highlight</b> über Text) + <b>Farben-Picker HL/Stift</b> + <b>3 Favoriten</b> + <b>Deckkraft α + Toolbar-Slider</b>, <b>Schwärzen/Redaction</b> (Drag + Preview „REDACT“ + Einbrennen-Dialog), Unterstreichen, Notiz, <b>Text-Overlay</b>,
    <b>Stempel-Bibliothek</b> (GENEHMIGT/ENTWURF/VERTRAULICH + Datum, <b>Rotation 90°</b>), Callout,
    <b>Rechteck / Linie / Pfeil / Lineal</b> —
    Sidecar <code>*.ildann.json</code> (v4 / <code>ildann-v4</code>, Auto-Save, Undo/Redo);
    JSON-Export PDF-Highlight-kompatibel (rects/quadPoints/colorRGB); CSV Export;
    JSON Import mit Schema-v4-Validierung (klare Fehlermeldung);
    <b>Textsuche</b> highlightet Treffer auf der aktuellen Seite;
    Doppelklick / Strg+Klick / <b>Ctrl+E</b> auf Notiz/Overlay zum Bearbeiten;
    <b>Ctrl+Alt+T</b> Annotation-Tags (frei, Sidebar Multi-Select-Filter / Tag-Cloud);
    <b>Ctrl+Alt+N</b> Auswahl→Notiz (Sticky vorausgefüllt, optional +Highlight);
    <b>Ctrl+Shift+D</b> Auswahl duplizieren; <b>Ctrl+Alt+C/V</b> Annotationen kopieren/einfügen (auch seitenübergreifend);
    Auswahl-Werkzeug: Annotationen per Drag verschieben (wenn nicht gesperrt);
    PDF → Text→Overlay / Overlay einbrennen / <b>Text Seite/alles → Editor</b> /
    <b>Seitenbild(er) → Editor</b>;
    Flatten/Bake mit Fortschrittsdialog (Abbrechen);
    <b>Signaturfeld</b> (Platzhalter) und <b>Signatur (Bild)</b> Mausrad-Zoom + Esc + Aspect-Lock + Flatten — 1.5.3;
    <b>PDFs zusammenführen / teilen / Seitenbereich</b>;
    <b>Wasserzeichen / Seitennummern</b> Template Reset-Template·Fokus/Selektion · Quick-Insert {{stem}}/{{date}}·ungültige rot — 1.6.5;
    <b>PDF verschlüsseln/entschlüsseln</b> Prefill „jetzt ausschalten“+Toast · <b>Dokument-Statistik</b> Quick-Insert {{stem}}/{{date}}·ungültige rot · <b>Workspace-Layouts</b> Import-Log kopieren/TXT·Zusammenfassung — 1.6.5;
    <b>Zwei PDFs vergleichen</b> (Seite neben Seite);
    <b>Passwort setzen/öffnen</b>; <b>Bildkompression</b> (Seiten neu als JPEG);
    <b>Metadaten bearbeiten</b> Toast-Klick nur wenn Dialog zu · sonst Fokus/raise · Backup <code>.ildbak</code> — 1.5.5; <b>PDF bereinigen</b> (optional Metadaten strippen);
    <b>AcroForm-Formularfelder ausfüllen</b>; <b>Anhänge</b> auflisten/extrahieren;
    <b>Seitengröße / Zuschneiden</b> (Anzeige mm/inch, Statusleiste klickbar / Ctrl+Alt+U);
    Seite/Seiten als PNG/JPEG exportieren (Footer-Filter·Badge „Filter: übersprungen“·Ordner·Template <code>{{stem}}_p{{page}}</code>) — 1.5.5 / Bild als neue Seite / Seite drucken; Annotation löschen (Auswahl/letzte, Entf); Statusleiste Seite/Größe/Zoom/Dateiname/Wörter; Thumbnails per Drag neu ordnen (<b>Lazy-Load</b>, Größe in Einstellungen, <b>Ctrl+Z Undo</b>);
    Start: <code>python -m instantlensdoc --list-pages FILE [--json]</code> / <code>--export-page N --out PATH [--dpi] [--format png|jpeg]</code> One-Shot / <code>--open</code> / <code>--help</code> DE / <code>--version</code> — 1.5.5;
    PDF als Kopie speichern; <b>Seitenbereich extrahieren</b> (z. B. 1-3,5,8-10; DE-Validierung + Vorschau — 1.2.1);
    große PDFs: Warnung / Limits;
    <b>Seiten-Thumbnails</b> in der Sidebar</li>
<li><b>Datei → Schließen</b>: Speichern-Dialog bei ungespeicherten Änderungen;
    <b>Andere Tabs schließen</b> (Ctrl+Shift+W);
    <b>Alle / Links / Rechts schließen</b> (Kontextmenü / Datei);
    Sidebar: <b>Mittelklick</b> schließt Tab, Rechtsklick → Schließen / Andere / Links / Rechts / Alle</li>
<li><b>Bearbeiten → Weitersuchen / Rückwärtssuchen</b> (F3 / Shift+F3):
    PDF-Treffer-Highlight auf der Seite, Navigation auch über Seiten;
    klickbare <b>Trefferliste</b> (Seite + Snippet) in der Sidebar</li>
<li><b>Bearbeiten → Auswahl → Notiz</b> (Ctrl+Alt+N): PDF-Textauswahl als Sticky; optional Checkbox zusätzlich Highlight</li>
<li><b>Ansicht → Fenster teilen (zwei Docs)</b> (Ctrl+\\): zwei Dokumente; optional <b>vertikal</b> (Ctrl+Shift+\\); Sync-Scroll; Statusleiste dirty Tabs inkl. Speichern</li>
<li><b>Datei → Exportieren → Text → PDF</b>: Zielordner merken; optional nach Export öffnen; Schrift/Rand·Vorschau — 1.7.2</li>
<li><b>Hilfe → Jetzt prüfen…</b>: Status aktuell / neuer Build Hinweis; Offline ohne Fehlerdialog; Dismiss; lokal
    <code>docs/VERSION</code> / <code>VERSION.txt</code> (kein Auto-Download) — 1.7.2</li>
<li><b>Hilfe → Über InstantLens Doc</b>: Feature-Kurzliste + Link zu FEATURES.md;
    Datenschutz-Hinweis (lokal, keine Telemetrie, keine Cloud)</li>
<li><b>Hilfe → Logordner öffnen</b>: Crash-/App-Logs im Dateimanager</li>
<li><b>Hilfe → Crash-Report erstellen</b>: Logordner als ZIP speichern (optional Screenshot-Pfad-Hinweis)</li>
<li><b>Zwischenablage</b>: Bild einfügen (Editor Ctrl+Shift+V / PDF Strg+V) — Stempel oder neue Seite</li>
<li><b>Session</b>: Offene Dokumente (Sidebar-Liste) und Fenstergeometrie werden beim Beenden gespeichert;
    Wiederherstellung beim Start über getrennte Toggles in den Einstellungen
    (Fenstergeometrie / offene Tabs); <b>Last-Page</b> und <b>Scroll-Position</b> pro Tab</li>
<li><b>Logging</b>: Datei unter <code>%APPDATA%/InstantLensDoc/logs/</code> (Windows) bzw. <code>~/.config/InstantLensDoc/logs/</code></li>
<li><b>Tastatur-Cheat-Sheet</b>: Hilfe → Tastatur-Cheat-Sheet… / F1; Suche/Filter · Drucken · TXT {date}_shortcuts.txt · Zielordner — 2.4.2</li>
<li><b>Extras → Batch-Konvertierung</b>: Ordner → PDF oder OCR</li>
<li><b>Einfügen → Verketteter Textrahmen</b>: Overflow fließt in den Folgeahmen</li>
<li><b>OCR</b>: Extras → OCR (Seite/Bild) oder <b>OCR gesamtes PDF</b> (Batch mit
    <b>Sprach-Preset</b>-Combobox, Fortschritt/Abbrechen;
    Ergebnis als <b>neue Textdatei-Tab</b> <code>*-ocr.txt</code>) —
    Modus „editierbarer Text“ oder
    „durchsuchbares Bild“ (PDF + <code>*.ildocr.txt</code>); Tabellen-Heuristik als Markdown wo möglich.
    Ohne Tesseract: Install-Hinweis mit Link und <b>Pfad-Hilfe</b>
    (<a href="https://github.com/UB-Mannheim/tesseract/wiki">UB-Mannheim Wiki</a>,
    <code>winget install UB-Mannheim.TesseractOCR</code>,
    typisch <code>C:\\Program Files\\Tesseract-OCR\\tesseract.exe</code>);
    Button <b>„Als Defaults speichern“</b> → Toast (Dauer 1/2/3 s + A11y-Announcement) + Feld-Highlight; optionaler Seitenbereich;
    Toggle „Fehler anhängen“ Settings-persistiert; Seitenfehler-Abschnitt + Teilergebnis — 1.1.9</li>
<li><b>PDF zusammenführen</b>: Thumbnail-Klick → Readonly-Tab mit Banner „Vorschau“ +
    „Zum Bearbeiten öffnen“; Toggle Readonly schließen auch im Merge-Dialog (gleicher Persistenz-Tooltip in Settings); Drag&amp;Drop; Duplikat-Warnung — 1.1.9</li>
<li><b>Forms CSV</b>: <b>Esc</b> schließt ohne Export; <b>Enter</b> auf OK startet Export; Zähler N von M — 1.3.6</li>
<li><b>Redaction Sidecar</b>: Status <b>„Sidecar übersprungen“</b>; Fortsetzen-Option in Settings merken — 1.3.6</li>
<li><b>Outlines Export</b>: Fehlerdialog Retry-Zähler <b>Versuch k/3</b> — 1.3.6</li>
<li><b>Thumbnail Prefetch</b>: Live-Label <b>grau</b> wenn Lazy aus (unter Schwellwert), sonst aktiv — 1.3.6</li>
<li><b>AcroForm-Sidebar</b>: Feldliste <b>Name/Typ/Wert</b>; Klick → Seite; Textfeld-Wert speichern via <b>pikepdf</b> — 1.3.0</li>
<li><b>Redactions anwenden</b>: Rechteck → Sidecar; Menü erzeugt <b>neues PDF</b> mit schwarzen Flächen — 1.3.0</li>
<li><b>Bookmarks ↔ Outlines</b>: Import aus PDF-Outlines / Export als PDF-Outlines — 1.3.0</li>
<li><b>Thumbnail Lazy-Load</b>: große PDFs <b>&gt;50 Seiten</b> mit Platzhaltern für alle Seiten — 1.3.0</li>
<li><b>PDF Seitenbereich / Split</b>: Bereiche <b>1-3,5,8-10</b>; Pfad-Log <b>In Tabs öffnen</b>: Status <b>geöffnet X, übersprungen Y</b>; <b>Log-Footer klickbar</b> → Filter übersprungene (Toggle); Pfad kopieren; Mehrfachauswahl; Ordner der Auswahl — 1.2.9</li>
<li><b>Annotationen exportieren (JSON / Flatten)</b>: Quick-Insert <b>{{stem}}</b>/<b>{{page}}</b>/<b>{{date}}</b>; <b>Ctrl+Z lokal</b>; <b>Reset-Template</b> → Live-Vorschau + Fokus mit Selektion ganzer Default-Text — 1.2.9</li>
<li><b>Text-Diff Panel</b>: Wrap-Blink Dauer Settings <b>kurz/mittel/lang</b> + <b>System-Beep vs. stumm</b>; Status <b>Änderung i/n</b>; F7/Shift+F7 — 1.2.9</li>
<li><b>run.bat</b>: gewählte Binary als <b>gefunden: …</b> inkl. <b>python --version</b>; bei ungültigem/leerem <b>%ILD_PYTHON%</b> Fallback <b>py -3 → python → python3</b>; --help; .venv; --yes; Exit 0/1 — 1.2.9</li>
<li><b>Alle Annotationen auf Seite löschen</b>: bei 0 Treffern Sticky-Status Statusleiste
    (Clear bei Seiten-/Dokumentwechsel / Undo/Redo) + i18n DE + Menü/Aktion no-op + Button disabled; Undo „N Annotationen (gefiltert)“ — 1.1.9</li>
<li><b>Keygen</b>: Reveal Auto-Hide 5/10/30 s + Countdown (Label „pausiert“; Tooltip „Fenster ohne Fokus“) / Esc maskiert;
    History maskiert (letzte 4); Doppelklick kopiert; Clear History; .txt; --days — 1.1.9</li>
<li><b>Formulare</b>: Extras → Formulargenerator — mehr Feldtypen, Definition speichern/laden
    (<code>*.ildform.json</code>), Live-Vorschau, Export HTML/PDF</li>
<li><b>Build (Windows)</b>: <code>build-windows.ps1</code> — PyInstaller App + Keygen</li>
<li><b>Installer</b>: optionale Desktop-Verknüpfung (Checkbox, Standard an, <code>checkedonce</code>)
    + Startmenü-Gruppe (siehe Inno-Hinweis)</li>
<li><b>Lizenz</b>: Statusleiste (farbig; bei &lt;7 Tagen Restlaufzeit prominent) + Hilfe → Lizenz — Trial 4 Wochen, Keys 30+2 Tage</li>
<li><b>Keygen</b>: <code>run-keygen.bat</code> / <code>python -m keygen --gui</code>;
    Installer-EXE: <code>{{app}}/InstantLensKeygen.exe</code> (siehe <code>keygen/README.md</code>)</li>
</ul>
<h3>PDF-Modul</h3>
<p>Das Paket <code>ild_pdf</code> kann von anderen Programmen genutzt werden (pypdfium2, kein Poppler).
Beispiel: <code>examples/ild_pdf_demo.py</code>. API: <code>ild_pdf/README.md</code>.</p>
<h3>Sync / Update</h3>
<p>Windows: Repo-Skript <code>scripts/sync-ild.ps1</code> bzw. Store <code>docs/sync-ild.ps1</code> — Branch oder Zip nach
<code>D:\\AI_Temp\\InstantLensDoc</code>, pip, optional Start (<code>-SkipStart</code>/<code>-NoStart</code> unterdrückt Start).
Exit-Codes: 0 OK, 1 allgemein, 2 Git-Fehler. Eigenes Icon in <code>assets</code> bleibt erhalten.</p>
<h3>Geplante Features</h3>
<p>KI-Assistent, Cloud-Sync, Stylus/Palm Rejection, 3D u. a. sind im Menü als „Geplant“ markiert
(Stub {__version__}) — siehe FEATURES.md.</p>
<p><b>Plugin-Hooks</b> sind ein Stub und <b>nicht produktiv</b> (interner Event-Bus + no-op Loader).
Dokumentierte Event-Namen: <code>app.started</code>, <code>document.opened</code>,
<code>document.saved</code>, <code>annotation.changed</code>, <code>ocr.finished</code>
— siehe FEATURES.md.</p>
"""


WIZARD_PAGES = (
    (
        "1 / 4 — Dokument öffnen",
        "<h3>Dokument öffnen</h3>"
        "<p><b>Datei → Öffnen</b> (Ctrl+O): TXT, Markdown, HTML, DOCX, PDF oder Bild.</p>"
        "<ul>"
        "<li>Mehrere Dateien per Drag &amp; Drop → mehrere Tabs</li>"
        "<li><b>Zuletzt geöffnet</b> in Menü und Seitenleiste</li>"
        "<li>PDF: Annotationen liegen im Sidecar <code>*.ildann.json</code> (PDF unverändert)</li>"
        "</ul>",
    ),
    (
        "2 / 4 — PDF annotieren",
        "<h3>PDF annotieren</h3>"
        "<p>Werkzeuge in der PDF-Toolbar: Highlight, Notiz, Stempel, Formen …</p>"
        "<ul>"
        "<li><b>★</b> / Ctrl+Shift+F: Seite als Favorit; Sidebar zum Springen/Umsortieren</li>"
        "<li>Favoriten <b>JSON Export/Import</b> unter PDF-Menü</li>"
        "<li><b>α-Slider</b> in der Toolbar: Deckkraft der Auswahl (ohne Dialog)</li>"
        "</ul>",
    ),
    (
        "3 / 4 — Editor &amp; Hilfe",
        "<h3>Editor &amp; weiter</h3>"
        "<ul>"
        "<li>Ctrl+F2: Zeile favorisieren; Sidebar-Liste; Doppelklick → <b>Label</b></li>"
        "<li>F1: Tastatur-Cheat-Sheet · Suche/Filter · Drucken/TXT {date}_shortcuts.txt · Hilfe… — 2.4.2</li>"
        "<li>Lokal, ohne Telemetrie — Stubs KI/Cloud/Stylus/3D bewusst ohne Funktion</li>"
        "</ul>",
    ),
    (
        "4 / 4 — Neu in 0.6",
        "<h3>Highlights 0.6</h3>"
        "<ul>"
        "<li><b>Tag-Cloud</b>: Klick filtert; Ctrl+Klick Multi; <b>Rechtsklick → filtern / Farbe / umbenennen</b> "
        "(global, <b>Ctrl+Z</b>; Bestätigung ab Schwelle in Einstellungen)</li>"
        "<li><b>Fenster teilen</b> (Ctrl+\\): PDF+Editor; Sync-Scroll; Panel-Typ + Sync-Scroll "
        "<b>je Session</b> gemerkt</li>"
        "<li>Statusleiste <b>ungespeichert</b>: <b>Alle speichern</b> mit Fortschritt, Abbrechen, "
        "<b>Fehlerliste</b> am Ende</li>"
        "<li><b>0.6.8 kurz:</b> Panel-Typ Session · Save-Abbrechen · Wizard-Reset · Tag-Confirm &gt;20</li>"
        "</ul>"
        "<p>Fertig — viel Erfolg mit InstantLens Doc.</p>",
    ),
)


class GettingStartedWizard(QDialog):
    """Kurz-Wizard „Erste Schritte“ — vier Seiten (inkl. 0.6-Highlights)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Erste Schritte")
        self.resize(480, 360)
        self._index = 0
        self.skipped_once = False
        self.completed = False
        layout = QVBoxLayout(self)
        self._title = QLabel()
        self._title.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(self._title)
        self._stack = QStackedWidget()
        for _caption, html in WIZARD_PAGES:
            page = QTextBrowser()
            page.setOpenExternalLinks(False)
            page.setHtml(html)
            self._stack.addWidget(page)
        layout.addWidget(self._stack, 1)
        self.skip_once_cb = QCheckBox("Dieses Mal überspringen (beim nächsten Start wieder zeigen)")
        self.skip_once_cb.setToolTip(
            "Wizard für diesen Start ausblenden — erscheint beim nächsten App-Start erneut"
        )
        layout.addWidget(self.skip_once_cb)
        self.dont_show_cb = QCheckBox("Nicht mehr zeigen")
        self.dont_show_cb.setToolTip(
            "Wizard dauerhaft ausblenden (Hilfe → Erste Schritte öffnet ihn weiterhin manuell)"
        )
        layout.addWidget(self.dont_show_cb)
        # Mutual exclusive UX: dauerhaft vs. einmal überspringen
        self.skip_once_cb.toggled.connect(self._on_skip_once_toggled)
        self.dont_show_cb.toggled.connect(self._on_dont_show_toggled)
        nav = QHBoxLayout()
        self._btn_back = QPushButton("Zurück")
        self._btn_back.clicked.connect(self._back)
        self._btn_next = QPushButton("Weiter")
        self._btn_next.setDefault(True)
        self._btn_next.clicked.connect(self._next)
        self._btn_close = QPushButton("Schließen")
        self._btn_close.clicked.connect(self._close_clicked)
        nav.addWidget(self._btn_back)
        nav.addStretch(1)
        nav.addWidget(self._btn_close)
        nav.addWidget(self._btn_next)
        layout.addLayout(nav)
        self._show_page(0)

    def _on_skip_once_toggled(self, checked: bool) -> None:
        if checked and self.dont_show_cb.isChecked():
            self.dont_show_cb.blockSignals(True)
            self.dont_show_cb.setChecked(False)
            self.dont_show_cb.blockSignals(False)

    def _on_dont_show_toggled(self, checked: bool) -> None:
        if checked and self.skip_once_cb.isChecked():
            self.skip_once_cb.blockSignals(True)
            self.skip_once_cb.setChecked(False)
            self.skip_once_cb.blockSignals(False)

    def _apply_outcome(self, *, complete: bool) -> None:
        """Skip-once, „Nicht mehr zeigen“ oder Fertig → Settings schreiben."""
        from instantlensdoc.core.app_settings import set_wizard_completed, set_wizard_skip_once

        if self.dont_show_cb.isChecked():
            set_wizard_completed(True)
            set_wizard_skip_once(False)
            self.completed = True
            self.skipped_once = False
            return
        if self.skip_once_cb.isChecked():
            set_wizard_skip_once(True)
            set_wizard_completed(False)
            self.skipped_once = True
            self.completed = False
            return
        if complete:
            set_wizard_completed(True)
            set_wizard_skip_once(False)
            self.completed = True
            self.skipped_once = False

    def _close_clicked(self):
        self._apply_outcome(complete=False)
        self.accept()

    def _show_page(self, index: int):
        n = len(WIZARD_PAGES)
        self._index = max(0, min(int(index), n - 1))
        self._stack.setCurrentIndex(self._index)
        caption, _html = WIZARD_PAGES[self._index]
        self._title.setText(caption)
        self._btn_back.setEnabled(self._index > 0)
        if self._index >= n - 1:
            self._btn_next.setText("Fertig")
        else:
            self._btn_next.setText("Weiter")

    def _back(self):
        self._show_page(self._index - 1)

    def _next(self):
        if self._index >= len(WIZARD_PAGES) - 1:
            self._apply_outcome(complete=True)
            self.accept()
            return
        self._show_page(self._index + 1)


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


def create_crash_report_zip_dialog(parent=None):
    """
    Logordner als Crash-Report-ZIP speichern (Dateidialog).
    Optional: Screenshot-Pfad als Hinweis (und Datei ins ZIP, falls vorhanden).
    Rückgabe: Path bei Erfolg, sonst None.
    """
    from datetime import datetime
    from pathlib import Path

    from PySide6.QtWidgets import QFileDialog, QMessageBox

    from instantlensdoc.core.app_settings import (
        get_last_export_dir,
        remember_recent_dir,
        set_last_export_dir,
    )
    from instantlensdoc.core.logging_setup import create_crash_report_zip

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    default_name = f"InstantLensDoc-crash-report-{stamp}.zip"
    last = get_last_export_dir()
    start_dir = Path(last) if last else log_dir()
    start = str(start_dir / default_name)
    path, _ = QFileDialog.getSaveFileName(
        parent,
        "Crash-Report speichern",
        start,
        "ZIP-Archiv (*.zip)",
    )
    if not path:
        return None
    dest = Path(path)
    if dest.suffix.lower() != ".zip":
        dest = dest.with_suffix(".zip")

    screenshot_path: Path | str | None = None
    if parent is not None:
        reply = QMessageBox.question(
            parent,
            "Crash-Report — Screenshot",
            "Optional: Screenshot-Pfad als Hinweis hinzufügen?\n\n"
            "Ja → Datei wählen (wird in REPORT.txt vermerkt und, falls vorhanden, "
            "unter screenshots/ ins ZIP kopiert).\n"
            "Nein → nur Logordner.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            shot, _ = QFileDialog.getOpenFileName(
                parent,
                "Screenshot auswählen (optional)",
                str(start_dir),
                "Bilder (*.png *.jpg *.jpeg *.bmp *.webp);;Alle Dateien (*)",
            )
            if shot:
                screenshot_path = shot
            else:
                # Nutzer hat Dialog abgebrochen — trotzdem Pfad-Hinweis leer lassen,
                # aber erlauben, einen manuellen Hinweis zu setzen
                from PySide6.QtWidgets import QInputDialog

                hint, ok = QInputDialog.getText(
                    parent,
                    "Screenshot-Pfad-Hinweis",
                    "Pfad-Hinweis (optional, auch ohne vorhandene Datei):",
                )
                if ok and str(hint).strip():
                    screenshot_path = str(hint).strip()
    try:
        out = create_crash_report_zip(dest, screenshot_path=screenshot_path)
    except Exception as e:
        if parent is not None:
            QMessageBox.warning(parent, "Crash-Report", str(e))
        return None
    try:
        set_last_export_dir(str(out.parent))
        remember_recent_dir(str(out))
    except Exception:
        pass
    if parent is not None:
        extra = ""
        if screenshot_path:
            extra = f"\n\nScreenshot-Hinweis:\n{screenshot_path}"
        QMessageBox.information(
            parent,
            "Crash-Report",
            f"Crash-Report gespeichert:\n{out}\n\n"
            "Enthält die Dateien aus dem Logordner (keine Dokumente)."
            f"{extra}",
        )
    return out


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
        btn_crash = QPushButton("Crash-Report…")
        btn_crash.setToolTip("Logordner als ZIP speichern (Support / Diagnose)")
        btn_crash.clicked.connect(lambda: create_crash_report_zip_dialog(self))
        btn_row.addWidget(btn_crash)
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
        self._parent_win = parent
        self._license_mgr = None
        self.setWindowTitle(f"{DISPLAY_NAME} {__series__}")
        self.resize(560, 640)
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
                f"<h2>{DISPLAY_NAME} {__series__}</h2>"
                f"<p><b>Version</b> {__version__} · Serie <b>{__series__}</b><br>"
                f"Hersteller: {VENDOR}<br>"
                f"Kontakt: <a href='mailto:{CONTACT_EMAIL}'>{CONTACT_EMAIL}</a></p>"
                f"<p>PDF-Engine: pypdfium2 / PDFium (lizenzfreundlich)</p>"
                f"<p>Icon: assets/app.ico · assets/icon.png</p>"
            )
        )
        # Lizenzstatus: Resttage + Ablauf TT.MM.JJJJ konsistent Status — 1.0.3
        license_html = ""
        trial_hint = ""
        show_activate = False
        try:
            from instantlensdoc.license import (
                LicenseManager,
                format_ablaufdatum,
                resttage_phrase,
            )

            mgr = None
            if parent is not None and hasattr(parent, "license_manager"):
                mgr = parent.license_manager
            if mgr is None:
                mgr = LicenseManager()
            self._license_mgr = mgr
            st = mgr.status()
            rest = resttage_phrase(st.days_remaining)  # „noch X Tag(e)“ wie Statusleiste
            mode_lbl = {
                "trial": "Testversion (Trial)",
                "licensed": "Lizenziert",
                "expired": "Abgelaufen",
            }.get(st.mode, st.mode)
            exp = format_ablaufdatum(st.expires_at, empty="")
            email_line = f"<br>E-Mail: {st.email}" if st.email else ""
            bg = "#E3F2FD" if st.mode == "licensed" else (
                "#FFF3CD" if st.mode == "trial" else "#FFEBEE"
            )
            border = "#64B5F6" if st.mode == "licensed" else (
                "#E0C36A" if st.mode == "trial" else "#E57373"
            )
            license_html = (
                f"<p style='background:{bg};padding:8px;border:1px solid {border};'>"
                f"<b>Lizenzstatus</b>: {mode_lbl}<br>"
                f"Restlaufzeit: <b>{rest}</b>"
                + (f"<br>Ablauf: {exp}" if exp else "")
                + email_line
                + f"<br>{st.message}<br>"
                f"Kontakt / Key: <a href='mailto:{CONTACT_EMAIL}'>{CONTACT_EMAIL}</a>"
                f"</p>"
            )
            # Button bei Trial / abgelaufen / ungültig — 1.0.1
            show_activate = st.mode != "licensed"
            if st.mode == "trial":
                trial_hint = (
                    f"<p style='background:#FFF3CD;padding:8px;border:1px solid #E0C36A;'>"
                    f"<b>Testversion</b> — {rest}.<br>"
                    f"Lizenzschlüssel erzeugen: <code>run-keygen.bat</code> bzw. "
                    f"<code>python -m keygen --gui</code> "
                    f"(Installer: <code>InstantLensKeygen.exe</code>).<br>"
                    f"Neuen Key anfordern: <a href='mailto:{CONTACT_EMAIL}'>{CONTACT_EMAIL}</a>"
                    f"</p>"
                )
        except Exception:
            license_html = (
                f"<p><b>Lizenzstatus</b>: unbekannt<br>"
                f"Kontakt: <a href='mailto:{CONTACT_EMAIL}'>{CONTACT_EMAIL}</a></p>"
            )
            trial_hint = ""
            show_activate = True
        if license_html:
            lic_lbl = QLabel(license_html)
            lic_lbl.setWordWrap(True)
            lic_lbl.setOpenExternalLinks(True)
            layout.addWidget(lic_lbl)
        if show_activate:
            btn_activate = QPushButton("Lizenz aktivieren…")
            btn_activate.setToolTip("Lizenzschlüssel eingeben (Trial / ungültig / abgelaufen)")
            btn_activate.clicked.connect(self._activate_license)
            layout.addWidget(btn_activate)
            self._btn_activate = btn_activate
        else:
            self._btn_activate = None
        if trial_hint:
            hint_lbl = QLabel(trial_hint)
            hint_lbl.setWordWrap(True)
            hint_lbl.setOpenExternalLinks(True)
            layout.addWidget(hint_lbl)
        privacy = QLabel(
            "<p style='background:#E8F5E9;padding:8px;border:1px solid #81C784;'>"
            "<b>Datenschutz / Privacy</b><br>"
            "InstantLens Doc arbeitet <b>lokal</b> auf diesem Rechner. "
            "Telemetrie-Stub (2.3.1): Settings opt-in „anonym Nutzung melden“ "
            "Default <b>aus</b>, immer <b>no-op</b> — keine Datenübertragung. "
            "Kein produktives Nutzungs-Tracking und "
            "<b>kein Cloud-Upload</b> von Dokumenten oder Annotationen. "
            "Optionale Online-Update-Prüfung nur wenn in den Einstellungen aktiviert "
            "(sonst offline). Stubs KI/Cloud/Telemetrie bleiben bewusst ohne Funktion."
            "</p>"
        )
        privacy.setWordWrap(True)
        layout.addWidget(privacy)
        # Plugin-Hooks Stub: klar „nicht produktiv“ — 1.9.1
        try:
            from instantlensdoc.core.plugin_hooks import (
                KNOWN_EVENTS,
                STUB_MESSAGE,
                plugin_stub_info,
            )

            ev_list = ", ".join(f"<code>{e}</code>" for e in KNOWN_EVENTS)
            info = plugin_stub_info()
            plugins_note = QLabel(
                "<p style='background:#FFF8E1;padding:8px;border:1px solid #FFD54F;'>"
                "<b>Plugin-Hooks — Stub / nicht produktiv</b><br>"
                f"{STUB_MESSAGE}<br>"
                f"Geplante Events: {ev_list}<br>"
                "Stubs KI/Cloud/Stylus/3D + Plugin-Hooks bewusst ohne produktive Funktion."
                "</p>"
            )
            plugins_note.setWordWrap(True)
            plugins_note.setToolTip(str(info.get("message") or STUB_MESSAGE))
            layout.addWidget(plugins_note)
        except Exception:
            plugins_note = QLabel(
                "<p style='background:#FFF8E1;padding:8px;border:1px solid #FFD54F;'>"
                "<b>Plugin-Hooks — Stub / nicht produktiv</b> "
                "(interner Event-Bus + no-op Loader; kein Plugin-System)."
                "</p>"
            )
            plugins_note.setWordWrap(True)
            layout.addWidget(plugins_note)
        # Changelog-Kurzliste — 1.0.0
        cl_lbl = QLabel(changelog_short_html(max_versions=4))
        cl_lbl.setWordWrap(True)
        layout.addWidget(cl_lbl)
        features_short = QLabel(
            "<h3>Features (Kurz)</h3>"
            "<ul>"
            "<li>PDF lesen/annotieren (Highlight, Notiz, Stempel, Formen) · Sidecar v4</li>"
            "<li><b>Metadaten Toast Fokus/raise · Seiten→Bilder Filter-Badge · Signatur Zoom Settings·Reset · CLI</b> "
            "<code>--list-pages --json</code> · <code>--export-page</code> · Exit 0/1/2 · "
            "Wasserzeichen Reset-Template·Fokus · Encrypt Prefill Toast · Doc-Stats Quick-Insert·ungültige-rot · Layouts Import-Log kopieren/TXT·Zusammenfassung — 1.6.5</li>"
            "<li><b>Theme zyklisch</b> <code>Ctrl+Shift+T</code> "
            "System→Hell→Dunkel (Status-Toast „Theme: …“) — 1.4.5</li>"
            "<li>Willkommen Drag&amp;Drop/Clear-Recent, Druck-DPI 72/150/300, Trial-Resttage konsistent, Backup-Retry — 1.0.2</li>"
            "<li>Editor: Find/Replace, Snippets, Bracket-Match, Minimap, Zeilen-Lesezeichen</li>"
            "<li>OCR-Bridge, Formulargenerator, Batch, Export · Ann.-Batch-Farbe/Deckkraft</li>"
            "<li>Lizenz Trial/Keys · lokal, ohne Telemetrie · "
            "Stubs: KI, Cloud, Stylus, 3D, Plugin-Hooks (nicht produktiv)</li>"
            "</ul>"
            "<p>Vollständige Liste: FEATURES.md</p>"
        )
        features_short.setWordWrap(True)
        features_short.setOpenExternalLinks(False)
        layout.addWidget(features_short)

        btn_row = QHBoxLayout()
        btn_features = QPushButton("FEATURES.md öffnen…")
        btn_features.setToolTip("FEATURE-Liste im Standard-Editor / Dateimanager öffnen")
        btn_features.clicked.connect(self._open_features_md)
        btn_row.addWidget(btn_features)
        btn_cl = QPushButton("CHANGELOG.md öffnen…")
        btn_cl.setToolTip("Changelog im Standard-Editor / Dateimanager öffnen")
        btn_cl.clicked.connect(self._open_changelog_md)
        btn_row.addWidget(btn_cl)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _activate_license(self) -> None:
        """Lizenzdialog öffnen (Trial / ungültig / abgelaufen) — 1.0.1."""
        from instantlensdoc.ui.license_dialog import LicenseDialog

        mgr = self._license_mgr
        if mgr is None:
            from instantlensdoc.license import LicenseManager

            mgr = LicenseManager()
            self._license_mgr = mgr
        parent = self._parent_win if self._parent_win is not None else self
        if LicenseDialog(mgr, parent).exec():
            # Statusleiste aktualisieren wenn Hauptfenster
            if self._parent_win is not None and hasattr(
                self._parent_win, "_update_license_status"
            ):
                try:
                    self._parent_win._update_license_status()
                except Exception:
                    pass
            # About schließen — Status hat sich ggf. geändert
            self.accept()

    def _open_features_md(self) -> None:
        path = ROOT / "FEATURES.md"
        if not path.is_file():
            QMessageBox.information(
                self,
                "FEATURES.md",
                f"FEATURES.md nicht gefunden:\n{path}",
            )
            return
        ok = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        if not ok:
            QMessageBox.information(
                self,
                "FEATURES.md",
                f"Konnte FEATURES.md nicht öffnen.\nPfad:\n{path}",
            )

    def _open_changelog_md(self) -> None:
        path = ROOT / "CHANGELOG.md"
        if not path.is_file():
            QMessageBox.information(
                self,
                "CHANGELOG.md",
                f"CHANGELOG.md nicht gefunden:\n{path}",
            )
            return
        ok = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        if not ok:
            QMessageBox.information(
                self,
                "CHANGELOG.md",
                f"Konnte CHANGELOG.md nicht öffnen.\nPfad:\n{path}",
            )
