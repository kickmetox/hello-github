# InstantLens Doc — Features

Statuslegende: **fertig** · **teilweise** · **geplant** · **Stub**

| Feature | Status | Hinweis |
|---------|--------|---------|
| Hauptfenster (Menü, Sidebar, Editor, Status) | fertig | PySide6 |
| App-Icon Fenster/Taskleiste/About | fertig | Robuste Pfade: `assets/`, CWD, `D:\AI_Temp\InstantLensDoc` |
| Session-Restore (offene Docs) | fertig | `session.json`, Sidebar-Liste |
| Clipboard-Paste Bild | fertig | Editor + PDF (Stempel/Seite) |
| TXT / MD / HTML öffnen & speichern | fertig | HTML-Export mit einfachem Markdownish |
| DOCX öffnen & speichern | teilweise | python-docx; Headings/Listen beim Export |
| Editor → HTML / DOCX / PDF Export | fertig | Datei → Exportieren |
| Drucken (Editor / PDF-Seite) | fertig | Qt PrintDialog (Ctrl+P) |
| Zuletzt geöffnete Dateien | fertig | Menü + Sidebar, `recent.json` |
| PDF lesen / rendern | fertig | pypdfium2; große-PDF-Limits |
| PDF Zoom / Seite einpassen | fertig | Debounce + Render-LRU-Cache |
| PDF-Wasserzeichen | fertig | Text diagonal, Deckkraft |
| PDF Seitennummer-Stempel | fertig | Vorlage `{n} / {total}` |
| PDF-Vergleich Seite-nebeneinander | fertig | Dialog |
| PDF-Schwärzung (Redaction) | teilweise | Drag-Annotation + Einbrennen (Basis) |
| PDF-Passwort setzen/öffnen | fertig | pikepdf Encryption / pypdfium2 |
| Bildkompression vor/als PDF | fertig | JPEG vor Einfügen; Seiten neu einbetten |
| Sidebar Seiten-Thumbnails | fertig | Vorschaubilder, Klick → Seite |
| Tastaturhilfe-Dialog | fertig | Hilfe → F1 |
| App-Logging | fertig | %APPDATA%/InstantLensDoc/logs |
| PDF-Annotationen (Highlight, Underline, Sticky, Text) | fertig | Sidecar `*.ildann.json` **v3** |
| Annotation Undo/Redo | fertig | Ctrl+Z/Y inkl. Overlay-Text |
| Stempel / Callouts | teilweise | Stempel-Presets + Callout (2-Klick) |
| PDF Signaturfeld / Signatur (Bild) | fertig | Sidecar; Menü PDF + Werkzeug |
| Theme Hell/Dunkel | fertig | Ansicht-Menü, persistiert |
| Autosave Editor / Annotationen | fertig | ~60 s, nur mit Pfad |
| Drag-Drop Datei öffnen | fertig | Hauptfenster |
| Formen (Rechteck / Linie / Pfeil) | fertig | Drag-Zeichnung |
| Messwerkzeug (Lineal) | fertig | Distanz in pt (Scale-bewusst) |
| Text-Overlay-Editor | fertig | Sidecar; Doppelklick/Strg+Klick; Bake optional |
| PDF-Text → Overlay | teilweise | Extraktion via pypdfium2; kein natives Rewrite |
| PDF Seite↔Bild Hooks | fertig | Extrahieren / Bild als Seite / Bildstempel |
| PDF drehen / Seite löschen | fertig | pikepdf; Annotation-Remap |
| PDF neu anordnen | fertig | Dialog + Annotation-Remap |
| Textsuche Seitenleiste | fertig | Editor + PDF-Text + Annotationen |
| Volltextsuche geöffnete Docs | fertig | Sidebar „Alle Docs“ |
| Lesezeichen / PDF-Outline | fertig | Baum in Sidebar, Doppelklick → Seite |
| Batch-Konvertierung Ordner | fertig | Bilder→PDF, OCR-Ordner, PDF-OCR-Text |
| PDF zusammenführen / teilen | fertig | Dialog unter Menü PDF |
| Einstellungen-Dialog | fertig | OCR-Sprache, Theme, Pfade |
| Markieren im Editor | fertig | Ctrl+H |
| Bilder JPEG/PNG anzeigen | fertig | |
| OCR Bild/PDF-Seite | teilweise | Presets + Modi; Tabellen-Heuristik; Tesseract-Link |
| OCR Ausgabe: editierbarer Text | fertig | → Editor |
| OCR Ausgabe: durchsuchbares Bild | teilweise | PDF + `*.ildocr.txt` Sidecar |
| Formulargenerator → HTML/PDF | fertig | Mehr Feldtypen; Definition speichern/laden |
| Layout: Textrahmen + Verkettung | teilweise | `flow_text_chain` |
| Layout: einfacher Umbruch | fertig | Wortgrenzen |
| Lizenz Trial 28d / Keys 32d | fertig | Statusleiste farbig + Tooltip |
| Keygenerator (CLI/GUI) | fertig | `run-keygen.bat` |
| PyInstaller Build Windows | fertig | `build-windows.ps1`, Icon `assets/app.ico` |
| Inno-Installer | fertig | Desktop + Startmenü-Hinweis 0.1.8 |
| Sync-Skript Windows | fertig | Store `docs/sync-ild.ps1` |
| In-App Hilfe / About | fertig | Version 0.1.8 |
| FEATURES.md / INFO.md | fertig | |
| `ild_pdf` Modul + Beispielskript | fertig | watermark / compare / limits |
| Font-Matching | geplant | |
| Objekt-/Bildbearbeitung | geplant | |
| Layout-Erhaltung (Scan→edit) | geplant | |
| Freihand | geplant | |
| KI-Assistent | Stub | Menü „Geplant“ 0.1.8 |
| Signieren (rechtssicher) | Stub | |
| Cloud-Sync | Stub | |
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
