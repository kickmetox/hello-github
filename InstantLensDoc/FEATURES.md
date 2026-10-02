# InstantLens Doc — Features

Statuslegende: **fertig** · **teilweise** · **geplant** · **Stub**

| Feature | Status | Hinweis |
|---------|--------|---------|
| Hauptfenster (Menü, Sidebar, Editor, Status) | fertig | PySide6 |
| App-Icon Fenster/Taskleiste/About | fertig | Robuste Pfade: `assets/`, CWD, `D:\AI_Temp\InstantLensDoc` |
| TXT / MD / HTML öffnen & speichern | fertig | |
| DOCX öffnen & speichern | teilweise | python-docx; Layout nicht 1:1 |
| PDF lesen / rendern | fertig | pypdfium2 |
| PDF-Annotationen (Highlight, Underline, Sticky, Text) | fertig | Sidecar `*.ildann.json` v2 (dirty/meta/timestamps) |
| Stempel / Callouts | teilweise | Stempel-Presets + Callout (2-Klick Anker→Box) |
| PDF Seite↔Bild Hooks | fertig | Extrahieren / Bild als Seite / Bildstempel-Annotation |
| PDF drehen / Seite löschen | fertig | pikepdf; Annotation-Remap |
| PDF neu anordnen | fertig | Dialog + Annotation-Remap |
| Textsuche Seitenleiste | fertig | Editor: alle Treffer; PDF: Annotationen filtern |
| Markieren im Editor | fertig | Ctrl+H |
| Bilder JPEG/PNG anzeigen | fertig | |
| OCR Bild/PDF-Seite | teilweise | Presets + Modi; klare UX ohne Tesseract |
| OCR Ausgabe: editierbarer Text | fertig | → Editor |
| OCR Ausgabe: durchsuchbares Bild | teilweise | PDF + `*.ildocr.txt` Sidecar (kein unsichtbarer Textlayer) |
| Formulargenerator → HTML/PDF | fertig | Mehr Feldtypen; Definition speichern/laden |
| Layout: Textrahmen + Verkettung | teilweise | `flow_text_chain` Overflow real |
| Layout: einfacher Umbruch | fertig | Wortgrenzen |
| Lizenz Trial 28d / Keys 32d | fertig | |
| Keygenerator (CLI/GUI) | fertig | `run-keygen.bat` |
| PyInstaller Build Windows | fertig | `build-windows.ps1` (App + Keygen) |
| Inno-Installer | fertig | `installer/build-installer.ps1` |
| Sync-Skript Windows | fertig | Store `docs/sync-ild.ps1` |
| In-App Hilfe / About | fertig | |
| FEATURES.md / INFO.md | fertig | |
| `ild_pdf` Modul | fertig | inkl. images-Hooks |
| Font-Matching | geplant | |
| Objekt-/Bildbearbeitung | geplant | |
| Layout-Erhaltung (Scan→edit) | geplant | |
| Freihand / Formen / Messwerkzeuge | geplant | |
| KI-Assistent | Stub | Menü „Geplant“ |
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
