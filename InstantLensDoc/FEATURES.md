# InstantLens Doc — Features

Statuslegende: **fertig** · **teilweise** · **geplant** · **Stub**

| Feature | Status | Hinweis |
|---------|--------|---------|
| Hauptfenster (Menü, Sidebar, Editor, Status) | fertig | PySide6; Status: Dateiname, Seite x/y (**Seitenlabels** 0.4.9), **Seitengröße mm/inch** 0.3.5, Zoom %, Wörter/Ann.; **ungespeicherte Tabs** 0.6.3 (**Klick → Dirty-Liste** 0.6.4, **Speichern je Datei** 0.6.5, **Alle speichern** 0.6.6, **Fortschritt >3** 0.6.7, **Abbrechen** 0.6.8, **Fehlerliste** 0.6.9); **Undo-Hint** 0.4.6 (**benannt z. B. Tag umbenennen** 0.6.7); Ann.-Liste Sidebar 0.2.4; **Ann.-Filter Typ** 0.2.6; **Ann.-Farben-Filter klickbar** 0.4.6; **Ann. nur aktuelle Seite** 0.4.9; **Ann.-Tag-Filter** 0.5.1 (**Multi-Select** 0.6.2, **Tag-Cloud** 0.6.3, **Cloud-Klick setzt Filter** 0.6.4, **Rechtsklick umbenennen** 0.6.5, **Rename-Undo ein Schritt** 0.6.6, **Undo-Stack-Label** 0.6.7, **Bestätigung >20** 0.6.8, **Schwelle in Einstellungen** 0.6.9); **Ann.-Regex** 0.5.2 |
| App-Icon Fenster/Taskleiste/About | fertig | Robuste Pfade: `assets/`, CWD, `D:\AI_Temp\InstantLensDoc` |
| Session-Restore (offene Docs) | fertig | `session.json`, Sidebar-Liste; **optional Toggle in Einstellungen** 0.3.7; **Tab-Reihenfolge Drag + order** 0.6.1; **Andere Tabs schließen** 0.6.2; **Fenster teilen zwei Docs** 0.6.3; **Sync-Scroll optional** 0.6.4; **Vertikal-Split Toggle** 0.6.5; **H/V in Einstellungen** 0.6.6; **PDF+Editor-Mischung zweites Panel** 0.6.7; **Panel-Typ secondary_path/kind je Session** 0.6.8; **Sync-Scroll je Session** 0.6.9 |
| Fenster-Geometrie speichern | fertig | Größe/Position/State in Settings 0.3.6 |
| PDF Präsentationsmodus | fertig | Vollbild F5; Pfeiltasten/Leertaste; Esc beendet 0.3.7 |
| Clipboard-Paste Bild | fertig | Editor + PDF (Stempel/Seite) |
| TXT / MD / HTML öffnen & speichern | fertig | HTML-Export mit einfachem Markdownish; **Encoding UTF-8/Latin-1** 0.4.1; **Auto-Erkennung BOM/chardet** 0.5.5 |
| DOCX öffnen & speichern | teilweise | python-docx; Headings/Listen beim Export |
| Editor → HTML / DOCX / PDF Export | fertig | Datei → Exportieren; Zielordner merken; Qualität/Format in Einstellungen; **Overwrite-Schutz** 0.3.8 |
| Drucken (Editor / PDF-Seite) | fertig | Qt PrintDialog (Ctrl+P) |
| Zuletzt geöffnete Dateien | fertig | Menü + Sidebar, `recent.json` |
| PDF lesen / rendern | fertig | pypdfium2; große-PDF-Limits; Timeout-Hinweis 0.2.1 |
| PDF Gehe zu Seite | fertig | Dialog Ctrl+G (PDF) / Ctrl+Shift+G; Menü PDF 0.4.6 |
| PDF Seiten-Favoriten | fertig | ★ markieren (Ctrl+Shift+F); Liste springen (Ctrl+Alt+F); **Sidebar-Liste mit Nummern** 0.5.7; **Drag-Umsortieren** 0.5.8; **JSON Export/Import ildfav-v1** 0.5.9; Sidecar `page_favorites` 0.5.6 |
| PDF Zwei-Seiten-Ansicht (Spread) | fertig | Optional; Ctrl+2 / Toolbar 2S; aktuelle+nächste Seite 0.4.7 |
| PDF Continuous Scroll | fertig | Optional; Ctrl+3 / Toolbar CS; Seiten untereinander; schließt Spread aus 0.4.8 |
| PDF Seitenlabels (römisch/arabisch) | fertig | Anzeige in Status/Toolbar wenn PageLabels vorhanden 0.4.9 |
| PDF Zoom / Seite einpassen | fertig | Debounce + Cache; Standard-Zoom in Einstellungen 0.2.2; **Fit-Width Ctrl+9** / **Fit-Height Ctrl+8** 0.3.9 |
| PDF-Wasserzeichen | fertig | Text diagonal, Deckkraft |
| PDF Seitennummer-Stempel | fertig | Vorlage `{n} / {total}` |
| PDF-Vergleich Seite-nebeneinander | fertig | Dialog |
| Dateien vergleichen (Editor-Tabs) | fertig | Side-by-Side Zeilen-Diff; Datei → Ctrl+Alt+D 0.5.2 |
| PDF-Metadaten-Editor | fertig | Titel/Autor/Thema/Keywords (DocInfo+XMP) |
| PDF bereinigen | fertig | Neuschreiben; optional Metadaten strippen; Menü PDF 0.5.1 |
| PDF Seitengröße / Zuschneiden | fertig | MediaBox-Presets + CropBox; **Anzeige mm/inch Toggle** 0.3.5; **Seitenrahmen/CropBox-Overlay** optional 0.4.3 |
| PDF-Schwärzung (Redaction) | teilweise | Drag + Preview-Label + Einbrennen-Dialog (Basis) |
| PDF-Passwort setzen/öffnen | fertig | pikepdf Encryption / pypdfium2 |
| Bildkompression vor/als PDF | fertig | JPEG vor Einfügen; Seiten neu einbetten |
| Export-Qualitätseinstellungen | fertig | JPEG-Q, Max-Kante, PDF-Seitenformat |
| Export-Profil (DPI/Format/Ziel) | fertig | Speichern/Anwenden; Vorbefüllung Seiten-Export 0.5.2 |
| Mehrsprach-UI DE/EN | teilweise | Einstellungen + Dialoge/Stubs (Minimal) |
| Update-Check-Hinweis | fertig | Hilfe-Menü; optional Start (nur wenn Einstellung aktiv); offline OK; Tray-Tooltip mit Version 0.3.9 |
| Sidebar Seiten-Thumbnails | fertig | Vorschaubilder, Klick → Seite; Drag-Reorder 0.2.3; **Lazy-Load** 0.3.1; **Größe in Einstellungen** 0.3.8 |
| Tastaturhilfe-Dialog | fertig | Hilfe → F1; **Cheat-Sheet als PDF exportieren** 0.4.7; **0.6.x-Keys** + kurze **0.6.8-Hinweise** / Sync-Scroll-Session / Tag-Schwelle / Save-Fehlerliste 0.6.9 |
| App-Logging | fertig | %APPDATA%/InstantLensDoc/logs; **Hilfe → Logordner öffnen** 0.3.0; **Crash-Report ZIP** 0.5.7; **optional Screenshot-Pfad-Hinweis** 0.5.8 |
| PDF-Annotationen (Highlight, Underline, Sticky, Text) | fertig | Sidecar `*.ildann.json` **v4** (`ildann-v4`); Farben-Picker Highlight/Stift 0.2.2; **Notizfarbe unabhängig** 0.4.7; Löschen Auswahl/letzte 0.2.3; **JSON Export/Import** 0.2.5; **PDF-Highlight Schema v4** 0.4.4; **Import-Validierung Schema v4** 0.4.5; **CSV Export** 0.3.8; **Sidebar-Filter nach Typ** 0.2.6; **Text nachträglich editierbar** 0.2.7; **Deckkraft/Opacity** 0.2.8; **Sidebar-Textsuche** 0.3.0; **Farben-Chips klickbar filtern** 0.4.6; **Zeitstempel in Liste** 0.4.8; **Filter nur aktuelle Seite** 0.4.9; **freie Tags/Labels filterbar** 0.5.1; **Selection→Highlight** 0.5.2; **Selection→Clipboard (Ctrl+C)** 0.6.1; **Selection→Notiz (Ctrl+Alt+N)** 0.6.2; **Selection→Highlight+Notiz (Checkbox)** 0.6.3 |
| Annotation Undo/Redo | fertig | Ctrl+Z/Y inkl. Overlay-Text; **benannte Stufen** (z. B. Tag umbenennen) im PDF-Undo-Stack 0.6.7 |
| Annotation löschen | fertig | Auswahl oder letzte; Entf / Menü 0.2.3 |
| Annotation duplizieren | fertig | Auswahl leicht versetzt; Ctrl+Shift+D 0.3.4 |
| Annotation-Duplikate zusammenführen | fertig | Gleiche Seite+BBox (±2px) + Typ erkennen; optional mergen (Text/Tags); Menü PDF 0.7.1 |
| Annotation kopieren/einfügen | fertig | Zwischen Seiten; Ctrl+Alt+C / Ctrl+Alt+V 0.4.2 |
| Annotation Select-All Seite | fertig | Alle Ann. der aktuellen Seite; Ctrl+A im PDF 0.3.6 |
| Annotation verschieben / Lock | fertig | Drag im Auswahl-Werkzeug; **Sperre-Toggle** (nicht verschiebbar) 0.4.3 |
| Annotation-Farben-Favoriten | fertig | 3 Presets speichern/anwenden (Toolbar 1/2/3) 0.3.7 |
| Annotation-Farbe Palette-Zyklus | fertig | Ctrl+Shift+C Zyklus / Ctrl+Alt+Shift+C Random aus fester Palette 0.5.3 |
| Annotation-Batch-Farbe (Auswahl) | fertig | Farbe für alle ausgewählten Ann. ändern; Ctrl+Alt+Shift+F 0.5.6 |
| Annotation-Deckkraft Batch (Auswahl) | fertig | Opacity für Auswahl; Ctrl+Alt+Shift+O / Toolbar α… 0.5.7; **Sidecar Force-Save / Clamp** 0.5.8; **Toolbar-Slider** 0.5.9 |
| Annotation-Text editieren | fertig | Notiz/Kommentar/Overlay nachträglich; Doppelklick / Ctrl+E 0.2.7 |
| Annotation-Tags/Labels | fertig | Freie Tags; Sidecar+CSV; Sidebar-Filter; Ctrl+Alt+T 0.5.1 |
| Annotation-Deckkraft | fertig | `opacity` Sidecar + Toolbar α + Dialog 0.2.8; **persistenter Force-Save** 0.5.8; **Toolbar-Slider** 0.5.9 |
| Annotation-Suche Sidebar | fertig | Textfilter in Annotationsliste 0.3.0; **optional Regex** 0.5.2; **Tag-Autocomplete** 0.6.1; **Tag-Filter Multi-Select (ODER)** 0.6.2; **Tag-Cloud häufigste Tags** 0.6.3; **Cloud-Klick setzt Filter** (Ctrl+Klick Multi) 0.6.4; **Rechtsklick → Tag umbenennen global** 0.6.5; **Ctrl+Z ein Undo-Schritt** 0.6.6; **Label „Tag umbenennen“ im PDF-Undo-Stack** 0.6.7; **Bestätigung bei >20 Treffern** 0.6.8; **Schwelle in Einstellungen** 0.6.9 |
| Stempel / Callouts | fertig | Bibliothek GENEHMIGT/ENTWURF/VERTRAULICH + Datum 0.3.1; Callout (2-Klick); **Rotation 90°** 0.4.1 |
| PDF URI-Links öffnen | fertig | Native Link-Annotationen http/https; Auswahl-Klick / Ctrl+Klick 0.4.1 |
| PDF AcroForm-Felder | fertig | Bestehende Felder lesen/schreiben (pikepdf) 0.3.1 |
| PDF-Anhänge | fertig | Auflisten/extrahieren (pikepdf Attachments) 0.3.2 |
| Annotation-Layer Toggle | fertig | Ansicht + Toolbar; Ctrl+Shift+A 0.3.2 |
| Annotationen flatten/bake Export | fertig | Alle Seiten mit Ann. → neues PDF; **Fortschrittsdialog + Abbrechen** 0.4.2 |
| Annotation Kommentar-Bericht | fertig | Zusammenhängender TXT/MD-Export (nach Seite gruppiert) 0.5.3; **Tags + Gruppen im Export** 0.5.5 |
| Annotation-Gruppen Name/Farbe | fertig | Seitengruppen umbenennen + Farbe; Sidebar/Ctrl+Alt+G 0.5.4 |
| Annotation CSV/JSON Export | fertig | CSV inkl. **tags/group_title/group_color**; JSON meta.page_groups 0.5.5 |
| PDF Seiten als Einzel-PDFs | fertig | Eine Datei pro Seite; Menü + `split_into_single_page_pdfs` 0.3.3 |
| PDF-Text → Editor | fertig | Seite oder gesamtes PDF; Menü PDF 0.3.4 |
| PDF-Seitenbild → Editor | fertig | Seite/alle Seiten als PNG + Verweiszeile; Menü PDF 0.4.5 |
| Tab schließen (dirty) | fertig | Speichern-Dialog; Datei → Schließen / Ctrl+W; Beenden 0.3.1 |
| PDF Signaturfeld / Signatur (Bild) | fertig | Sidecar; Menü PDF + Werkzeug |
| Theme Hell/Dunkel | fertig | Ansicht-Menü, persistiert |
| Einstellungen Reset-to-Defaults | fertig | Dialog-Button „Auf Standard zurücksetzen“ 0.4.4 |
| PDF-Toolbar Gruppen | fertig | Gruppen in Einstellungen ein-/ausblenden 0.4.5 |
| Autosave Editor / Annotationen | fertig | Intervall in Einstellungen (Default 60 s), nur mit Pfad |
| Drag-Drop Datei öffnen | fertig | Hauptfenster; **mehrere Dateien → Tabs** 0.4.1 |
| Formen (Rechteck / Linie / Pfeil) | fertig | Drag-Zeichnung |
| Messwerkzeug (Lineal) | fertig | Distanz in pt (Scale-bewusst) |
| Text-Overlay-Editor | fertig | Sidecar; Doppelklick/Strg+Klick; Bake optional |
| PDF-Text → Overlay | teilweise | Extraktion via pypdfium2; kein natives Rewrite |
| PDF Seite↔Bild Hooks | fertig | Seite/Seiten → PNG/JPEG Export 0.2.3; **DPI 72/150/300** 0.3.6; Bild als Seite / Bildstempel |
| PDF drehen / Seite löschen | fertig | Toolbar ⟲/⟳ (−90°/+90°) speichert; **Seite löschen Undo (Ctrl+Z)** 0.5.4; **Historie-Liste Wiederherstellen** 0.5.5; Annotation-Remap |
| PDF spiegeln (H/V) | fertig | Toolbar ↔/↕ + Menü; `ild_pdf.flip_page` 0.2.7 |
| PDF Druckermarken | fertig | Seitenrand Crop/Registration-Overlay optional; Toolbar „Marken“; Ctrl+Alt+M 0.4.4 |
| PDF Graustufen | fertig | Toggle Ansicht/Export; `render_page(..., grayscale=True)` 0.2.8 |
| PDF Nachtmodus | fertig | Invert-Ansicht nur Darstellung; `invert=True` — nicht speichern/exportieren 0.3.0 |
| PDF leere Seite / duplizieren | fertig | Toolbar + Menü; Annotation-Remap 0.2.4 |
| PDF neu anordnen | fertig | Dialog + Thumbnail-Drag + Annotation-Remap |
| Textsuche Seitenleiste | fertig | Editor + PDF-Text + Annotationen; Highlight 0.2.2; **letzte Suchbegriffe** merken 0.2.4 |
| Annotation-Liste Sidebar | fertig | Klick → Seite + Auswahl 0.2.4; **Filter nach Typ** 0.2.6; **Textsuche** 0.3.0; **Gruppierung nach Seite** 0.3.5; **Statistik je Typ (Footer)** 0.3.9; **Nur aktuelle Seite** 0.4.9; **Tag-Filter** 0.5.1 (**Multi-Select ODER** 0.6.2, **Tag-Cloud** 0.6.3, **setzt Filter** 0.6.4, **umbenennen** 0.6.5, **Rename-Undo** 0.6.6, **Undo-Label** 0.6.7, **Confirm >20** 0.6.8, **Schwelle Settings** 0.6.9); **Regex optional** 0.5.2; **Gruppen Name/Farbe** 0.5.4 |
| PDF Seitenbereich extrahieren | fertig | von–bis → neues PDF; Menü + Dialog-Tab 0.2.6 |
| Editor Find/Replace | fertig | Ctrl+R Dialog 0.2.6 |
| Editor Zeilennummern | fertig | Optional (Ansicht + Einstellungen) 0.2.7; **Zeilen-Lesezeichen/Favoriten** Ctrl+F2 / F2 0.5.7; **Sidebar-Liste** 0.5.8; **Labels editierbar** 0.5.9 |
| Editor Minimap | fertig | Optional Linien-Übersicht + dickere Scrollbar; Ansicht/Einstellungen; Ctrl+Shift+I 0.5.3 |
| Editor Soft-Hyphen / NBSP | fertig | Einfügen Ctrl+Shift+- / Ctrl+Shift+Space; Menü Bearbeiten 0.5.4 |
| Editor Groß-/Kleinschreibung | fertig | Auswahl umschalten Ctrl+Shift+U 0.2.8; **Alles groß/klein ganze Datei** 0.4.2 |
| Editor Einrückung | fertig | Erhöhen/Verringern Ctrl+]/[ bzw. **Tab/Shift+Tab Block** 0.3.7 |
| Editor Markdown-Vorschau | fertig | Optional Split (Ansicht); Ctrl+Shift+M 0.3.2 |
| Fenster teilen (zwei Docs) | fertig | Doc-Split Ctrl+\ ; zweites Pane read-only; Zweites Dokument wählen 0.6.3; **Sync-Scroll optional** Ctrl+Alt+\ 0.6.4; **Vertikal-Toggle** Ctrl+Shift+\ 0.6.5; **H/V in Einstellungen** 0.6.6; **PDF oder Editor im Zweit-Panel (Mischung)** 0.6.7; **Panel-Typ je Session merken** 0.6.8; **Sync-Scroll je Session** 0.6.9 |
| Editor Soft-Wrap | fertig | Toggle Ansicht/Einstellungen; Ctrl+Shift+W 0.3.3 |
| Editor Sonderzeichen | fertig | Tabs/Leerzeichen/Absätze sichtbar; Ansicht/Einstellungen; Ctrl+Shift+. 0.3.9; **Soft-Hyphen/NBSP einfügen** 0.5.4 |
| Editor Gehe zu Zeile | fertig | Dialog Ctrl+G (Editor; PDF → Seite) 0.3.4/0.4.6 |
| Editor Tab duplizieren | fertig | Inhalt klonen Ctrl+Shift+T; Erneut öffnen Ctrl+Alt+Shift+O 0.4.6 |
| Editor Zeile duplizieren | fertig | Ctrl+D (aktuelle/Auswahl) 0.3.5 |
| Editor Zeile verschieben | fertig | Alt+Up / Alt+Down (aktuelle/Auswahl) 0.3.8 |
| Editor Zeilen sortieren | fertig | A–Z Auswahl (ohne Auswahl: Datei); Ctrl+Shift+O 0.4.4 |
| Editor Trim trailing whitespace | fertig | Optional beim Speichern/Autosave; Einstellung 0.4.5 |
| Editor Whitespace trim on paste | fertig | Optional Trailing-Spaces beim Einfügen; Einstellung 0.4.7 |
| Editor Bracket-Match Highlight | fertig | Passende Klammern ()[]{} am Cursor; Einstellung (Standard an) 0.4.8 |
| Editor Rechtschreibung (Wortliste) | fertig | Wörterbuch-Pfad in Einstellungen; F7 prüft ohne Spell-Lib (wellig) 0.5.6 |
| Editor Zwischenablage-Verlauf | fertig | Letzte 3 Paste-Texte; Menü Bearbeiten 0.4.9 |
| Editor Kommentar/Unkommentar | fertig | Ctrl+/ für # und // (einfache Sprachen) 0.3.6 |
| Editor Textbausteine | fertig | 3 gespeicherte Snippets; Einfügen Ctrl+Alt+1..3; Auswahl→Slot 0.4.3 |
| Neues Dokument Vorlagen | fertig | Leer / Brief / Notiz unter Datei → Neu 0.4.3; **Als Vorlage speichern** + Meine Vorlagen 0.7.1 |
| Backup .bak beim Speichern | fertig | Optional in Einstellungen 0.3.5 |
| Zuletzt verwendete Ordner | fertig | Datei-Dialoge merken `recent_dirs` 0.3.2 |
| Projekt-Ordner / Workspace | fertig | Datei → Projekt-Ordner; letzte 5; Dialog-Startpfad 0.5.1 |
| Alles speichern (Tabs) | fertig | Datei → Alles speichern; aktuelles Doc + PDF-Sidecars 0.2.7 |
| Volltextsuche geöffnete Docs | fertig | Sidebar „Alle Docs“; **PDF-Schnellsuche „Alle PDFs“** (eine Open/Datei, Snippet, Sprung+Highlight) 0.7.1 |
| Sidecar-Save Debounce | fertig | Annotation-Sidecar verzögert speichern (400 ms); Flush bei Wechsel/Close/Autosave 0.7.1 |
| Lesezeichen / PDF-Outline | fertig | Baum in Sidebar; Doppelklick/Enter → Seite; **Destination via objgen gehärtet** 0.4.2; hinzufügen/löschen 0.2.5 |
| PDF als Kopie speichern | fertig | Datei + Sidecar; aktuelles Doc bleibt offen 0.2.5 |
| Editor Wortzählung | fertig | Statusleiste Wörter · Zeichen 0.2.5 |
| Batch-Konvertierung Ordner | fertig | Bilder→PDF, OCR-Ordner, PDF-OCR-Text; Fortschrittsbalken; **Abbrechen/Fehler robust** 0.4.2 |
| PDF zusammenführen / teilen | fertig | Dialog unter Menü PDF |
| Einstellungen-Dialog | fertig | OCR, Theme, Sprache, Export-Q, Standard-Zoom, **PDF-Thumbnail-Größe** 0.3.8, Autosave, optional Tray-Minimize, **Backup .bak**, **Seitengröße-Einheit**, **Session-Restore Toggle**, **Sonderzeichen** 0.3.9, **Doc-Split Layout H/V** 0.6.6, **Wizard-Reset** 0.6.8, **Tag-Rename-Schwelle** 0.6.9, Pfade, Update |
| Markieren im Editor | fertig | Ctrl+H |
| Bilder JPEG/PNG anzeigen | fertig | |
| OCR Bild/PDF-Seite | teilweise | Presets + Modi; Tabellen-Heuristik; Fortschrittsdialog 0.2.1 |
| OCR gesamtes PDF (Batch) | fertig | Alle Seiten mit Fortschritt/Abbrechen → Editor 0.5.1 |
| OCR Ausgabe: editierbarer Text | fertig | → Editor |
| OCR Ausgabe: durchsuchbares Bild | teilweise | PDF + `*.ildocr.txt` Sidecar |
| Formulargenerator → HTML/PDF | fertig | Mehr Feldtypen; Definition speichern/laden |
| Layout: Textrahmen + Verkettung | teilweise | `flow_text_chain` |
| Layout: einfacher Umbruch | fertig | Wortgrenzen |
| Lizenz Trial 28d / Keys 32d | fertig | Statusleiste farbig + Tooltip; **<7 Tage prominent** 0.2.6; Dialog Resttage/Ablauf 0.3.3 |
| Keygenerator (CLI/GUI) | fertig | `run-keygen.bat` |
| PyInstaller Build Windows | fertig | `build-windows.ps1`, Icon `assets/app.ico` |
| Inno-Installer | fertig | Icon, **optionale Desktop-Checkbox** (`desktopicon`/`checkedonce`) 0.6.1, Uninstaller, Keygen optional (`InstantLensKeygen.exe`) 0.2.1 |
| Sync-Skript Windows | fertig | Repo `scripts/sync-ild.ps1`; Store `docs/sync-ild.ps1`; **-SkipStart** + Exit-Codes 0/1/2 **0.6.2** |
| Arbeitsverzeichnis öffnen | fertig | Datei-Menü Ctrl+Shift+E; Ordner der Datei bzw. CWD 0.4.8 |
| In-App Hilfe / About | fertig | Version 0.7.1; Fenstertitel + Splash; Logordner-Button; **Feature-Kurzliste + FEATURES.md** 0.4.9; **Keygen-Hinweis bei Trial** 0.5.3; **Splash überspringbar** 0.5.5; **Privacy: lokal, keine Telemetrie** 0.5.6; **Crash-Report ZIP** 0.5.7; **Screenshot-Pfad optional** 0.5.8; **Erste-Schritte-Wizard (4 Seiten inkl. 0.6 / 0.6.8-Hinweise)** 0.6.9; **skip-once Checkbox + Auto-Show** 0.6.6; **Nicht mehr zeigen (dauerhaft)** 0.6.7; **Reset in Einstellungen** 0.6.8 |
| Startup-Abhängigkeiten-Check | fertig | pypdfium2 kritisch + Tesseract optional; Dialog bei Problemen 0.5.4 |
| Quiet Startup / Splash | fertig | Einstellungen: Splash überspringen 0.5.5 |
| CHANGELOG | fertig | **0.7.1** PDF-Schnellsuche / Ann.-Duplikate / Vorlagen / Sidecar-Debounce; **0.7.0** Konsolidierung 0.6.x |
| FEATURES.md / INFO.md | fertig | |
| `ild_pdf` Modul + Beispielskript | fertig | metadata / page size / watermark / redact / acroform / attachments / flatten / **plain text** / **selection_to_highlight_rects** / **selection_to_plain_text** / **export_report** / **page_favorites JSON** |
| Font-Matching | geplant | |
| Objekt-/Bildbearbeitung | geplant | |
| Layout-Erhaltung (Scan→edit) | geplant | |
| Freihand | geplant | |
| KI-Assistent | Stub | Menü „Geplant“ 0.7.1 (keine Fake-KI) |
| Signieren (rechtssicher) | Stub | |
| Cloud-Sync | Stub | Menü „Geplant“ 0.7.1 (keine Fake-Cloud) |
| Text on Path / Text zu Pfaden | geplant | |
| Envelope Distort / Text Wrap / Area Type | Stub/geplant | |
| Schnittmasken | geplant | |
| Füllungen / Live-Effekte | geplant | |
| 3D-Extrusion | Stub | Menü „Geplant“ 0.7.1 |
| Variable Fonts (voll) | Stub | |
| Glyphen-Palette | geplant | |
| Stylus / Palm Rejection | Stub | Menü „Geplant“ 0.7.1 |
| Intelligente Formerkennung | Stub | Menü „Geplant“ 0.7.1 |

Nicht behauptet als fertig: Cloud, KI, Stylus, 3D — nur Menü-Stubs + dieser Status.
