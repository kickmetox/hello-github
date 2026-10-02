# InstantLens Doc — Features

Statuslegende: **fertig** · **teilweise** · **geplant** · **Stub**

| Feature | Status | Hinweis |
|---------|--------|---------|
| Hauptfenster (Menü, Sidebar, Editor, Status) | fertig | PySide6; Status: Dateiname, Seite x/y, Zoom %, Wörter/Ann.; Ann.-Liste Sidebar 0.2.4; **Ann.-Filter Typ** 0.2.6 |
| App-Icon Fenster/Taskleiste/About | fertig | Robuste Pfade: `assets/`, CWD, `D:\AI_Temp\InstantLensDoc` |
| Session-Restore (offene Docs) | fertig | `session.json`, Sidebar-Liste |
| Clipboard-Paste Bild | fertig | Editor + PDF (Stempel/Seite) |
| TXT / MD / HTML öffnen & speichern | fertig | HTML-Export mit einfachem Markdownish |
| DOCX öffnen & speichern | teilweise | python-docx; Headings/Listen beim Export |
| Editor → HTML / DOCX / PDF Export | fertig | Datei → Exportieren; Zielordner merken; Qualität/Format in Einstellungen |
| Drucken (Editor / PDF-Seite) | fertig | Qt PrintDialog (Ctrl+P) |
| Zuletzt geöffnete Dateien | fertig | Menü + Sidebar, `recent.json` |
| PDF lesen / rendern | fertig | pypdfium2; große-PDF-Limits; Timeout-Hinweis 0.2.1 |
| PDF Zoom / Seite einpassen | fertig | Debounce + Cache; Standard-Zoom in Einstellungen 0.2.2 |
| PDF-Wasserzeichen | fertig | Text diagonal, Deckkraft |
| PDF Seitennummer-Stempel | fertig | Vorlage `{n} / {total}` |
| PDF-Vergleich Seite-nebeneinander | fertig | Dialog |
| PDF-Metadaten-Editor | fertig | Titel/Autor/Thema/Keywords (DocInfo+XMP) |
| PDF Seitengröße / Zuschneiden | fertig | MediaBox-Presets + CropBox |
| PDF-Schwärzung (Redaction) | teilweise | Drag + Preview-Label + Einbrennen-Dialog (Basis) |
| PDF-Passwort setzen/öffnen | fertig | pikepdf Encryption / pypdfium2 |
| Bildkompression vor/als PDF | fertig | JPEG vor Einfügen; Seiten neu einbetten |
| Export-Qualitätseinstellungen | fertig | JPEG-Q, Max-Kante, PDF-Seitenformat |
| Mehrsprach-UI DE/EN | teilweise | Einstellungen + Dialoge/Stubs (Minimal) |
| Update-Check-Hinweis | fertig | Hilfe-Menü; optional Start; offline OK |
| Sidebar Seiten-Thumbnails | fertig | Vorschaubilder, Klick → Seite; **Drag-Reorder** 0.2.3 |
| Tastaturhilfe-Dialog | fertig | Hilfe → F1 |
| App-Logging | fertig | %APPDATA%/InstantLensDoc/logs |
| PDF-Annotationen (Highlight, Underline, Sticky, Text) | fertig | Sidecar `*.ildann.json` **v3**; Farben-Picker Highlight/Stift 0.2.2; Löschen Auswahl/letzte 0.2.3; **JSON Export/Import** 0.2.5; **Sidebar-Filter nach Typ** 0.2.6; **Text nachträglich editierbar** 0.2.7; **Deckkraft/Opacity** 0.2.8 |
| Annotation Undo/Redo | fertig | Ctrl+Z/Y inkl. Overlay-Text |
| Annotation löschen | fertig | Auswahl oder letzte; Entf / Menü 0.2.3 |
| Annotation-Text editieren | fertig | Notiz/Kommentar/Overlay nachträglich; Doppelklick / Ctrl+E 0.2.7 |
| Annotation-Deckkraft | fertig | `opacity` Sidecar + Toolbar α + Dialog 0.2.8 |
| Stempel / Callouts | teilweise | Stempel-Presets + Callout (2-Klick) |
| PDF Signaturfeld / Signatur (Bild) | fertig | Sidecar; Menü PDF + Werkzeug |
| Theme Hell/Dunkel | fertig | Ansicht-Menü, persistiert |
| Autosave Editor / Annotationen | fertig | Intervall in Einstellungen (Default 60 s), nur mit Pfad |
| Drag-Drop Datei öffnen | fertig | Hauptfenster |
| Formen (Rechteck / Linie / Pfeil) | fertig | Drag-Zeichnung |
| Messwerkzeug (Lineal) | fertig | Distanz in pt (Scale-bewusst) |
| Text-Overlay-Editor | fertig | Sidecar; Doppelklick/Strg+Klick; Bake optional |
| PDF-Text → Overlay | teilweise | Extraktion via pypdfium2; kein natives Rewrite |
| PDF Seite↔Bild Hooks | fertig | Seite/Seiten → PNG/JPEG Export 0.2.3; Bild als Seite / Bildstempel |
| PDF drehen / Seite löschen | fertig | Toolbar ⟲/⟳ (−90°/+90°) speichert; Annotation-Remap |
| PDF spiegeln (H/V) | fertig | Toolbar ↔/↕ + Menü; `ild_pdf.flip_page` 0.2.7 |
| PDF Graustufen | fertig | Toggle Ansicht/Export; `render_page(..., grayscale=True)` 0.2.8 |
| PDF leere Seite / duplizieren | fertig | Toolbar + Menü; Annotation-Remap 0.2.4 |
| PDF neu anordnen | fertig | Dialog + Thumbnail-Drag + Annotation-Remap |
| Textsuche Seitenleiste | fertig | Editor + PDF-Text + Annotationen; Highlight 0.2.2; **letzte Suchbegriffe** merken 0.2.4 |
| Annotation-Liste Sidebar | fertig | Klick → Seite + Auswahl 0.2.4; **Filter nach Typ** 0.2.6 |
| PDF Seitenbereich extrahieren | fertig | von–bis → neues PDF; Menü + Dialog-Tab 0.2.6 |
| Editor Find/Replace | fertig | Ctrl+R Dialog 0.2.6 |
| Editor Zeilennummern | fertig | Optional (Ansicht + Einstellungen) 0.2.7 |
| Editor Groß-/Kleinschreibung | fertig | Auswahl umschalten Ctrl+Shift+U 0.2.8 |
| Alles speichern (Tabs) | fertig | Datei → Alles speichern; aktuelles Doc + PDF-Sidecars 0.2.7 |
| Volltextsuche geöffnete Docs | fertig | Sidebar „Alle Docs“ |
| Lesezeichen / PDF-Outline | fertig | Baum in Sidebar; Doppelklick → Seite; **hinzufügen/löschen** 0.2.5 |
| PDF als Kopie speichern | fertig | Datei + Sidecar; aktuelles Doc bleibt offen 0.2.5 |
| Editor Wortzählung | fertig | Statusleiste Wörter · Zeichen 0.2.5 |
| Batch-Konvertierung Ordner | fertig | Bilder→PDF, OCR-Ordner, PDF-OCR-Text; Fortschrittsbalken 0.2.1 |
| PDF zusammenführen / teilen | fertig | Dialog unter Menü PDF |
| Einstellungen-Dialog | fertig | OCR, Theme, Sprache, Export-Q, Standard-Zoom, Autosave, Pfade, Update |
| Markieren im Editor | fertig | Ctrl+H |
| Bilder JPEG/PNG anzeigen | fertig | |
| OCR Bild/PDF-Seite | teilweise | Presets + Modi; Tabellen-Heuristik; Fortschrittsdialog 0.2.1 |
| OCR Ausgabe: editierbarer Text | fertig | → Editor |
| OCR Ausgabe: durchsuchbares Bild | teilweise | PDF + `*.ildocr.txt` Sidecar |
| Formulargenerator → HTML/PDF | fertig | Mehr Feldtypen; Definition speichern/laden |
| Layout: Textrahmen + Verkettung | teilweise | `flow_text_chain` |
| Layout: einfacher Umbruch | fertig | Wortgrenzen |
| Lizenz Trial 28d / Keys 32d | fertig | Statusleiste farbig + Tooltip; **<7 Tage prominent** 0.2.6 |
| Keygenerator (CLI/GUI) | fertig | `run-keygen.bat` |
| PyInstaller Build Windows | fertig | `build-windows.ps1`, Icon `assets/app.ico` |
| Inno-Installer | fertig | Icon, Desktop, Uninstaller, Keygen optional (`InstantLensKeygen.exe`) 0.2.1 |
| Sync-Skript Windows | fertig | Store `docs/sync-ild.ps1` |
| In-App Hilfe / About | fertig | Version 0.2.8; Fenstertitel + Splash |
| CHANGELOG | fertig | 0.2.8 Graustufen / Opacity / Case / Splash |
| FEATURES.md / INFO.md | fertig | |
| `ild_pdf` Modul + Beispielskript | fertig | metadata / page size / watermark / redact |
| Font-Matching | geplant | |
| Objekt-/Bildbearbeitung | geplant | |
| Layout-Erhaltung (Scan→edit) | geplant | |
| Freihand | geplant | |
| KI-Assistent | Stub | Menü „Geplant“ 0.2.8 (keine Fake-KI) |
| Signieren (rechtssicher) | Stub | |
| Cloud-Sync | Stub | Menü „Geplant“ 0.2.8 (keine Fake-Cloud) |
| Text on Path / Text zu Pfaden | geplant | |
| Envelope Distort / Text Wrap / Area Type | Stub/geplant | |
| Schnittmasken | geplant | |
| Füllungen / Live-Effekte | geplant | |
| 3D-Extrusion | Stub | |
| Variable Fonts (voll) | Stub | |
| Glyphen-Palette | geplant | |
| Stylus / Palm Rejection | Stub | |
| Intelligente Formerkennung | Stub | |

Nicht behauptet als fertig: Cloud, KI, Stylus, 3D — nur Menü-Stubs + dieser Status.
