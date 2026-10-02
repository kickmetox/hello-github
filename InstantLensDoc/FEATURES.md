# InstantLens Doc — Features

Statuslegende: **fertig** · **teilweise** · **geplant** · **Stub**

| Feature | Status | Hinweis |
|---------|--------|---------|
| Hauptfenster (Menü, Sidebar, Editor, Status) | fertig | PySide6 |
| TXT / MD / HTML öffnen & speichern | fertig | |
| DOCX öffnen & speichern | teilweise | python-docx; Layout nicht 1:1 |
| PDF lesen / rendern | fertig | pypdfium2 |
| PDF-Annotationen (Highlight, Underline, Sticky, Text) | fertig | Sidecar `*.ildann.json` |
| PDF drehen / Seite löschen | fertig | pikepdf |
| PDF neu anordnen | teilweise | API in `ild_pdf.pages.reorder_pages`, UI noch ohne Dialog |
| Bilder JPEG/PNG anzeigen | fertig | |
| OCR Bild/PDF-Seite | teilweise | Bridge; braucht Tesseract-Runtime |
| Formulargenerator → HTML/PDF | fertig | |
| Layout: Textrahmen, Bild, einfacher Umbruch | teilweise | MVP, kein DTP |
| Lizenz Trial 28d / Keys 32d | fertig | |
| Keygenerator (CLI/GUI) | fertig | `python -m keygen` |
| In-App Hilfe / About | fertig | |
| FEATURES.md / INFO.md | fertig | |
| `ild_pdf` Modul | fertig | |
| Font-Matching | geplant | |
| Objekt-/Bildbearbeitung | geplant | |
| Layout-Erhaltung (Scan→edit) | geplant | |
| Ausgabe: durchsuchbares Bild / editierbarer Text | geplant | |
| Freihand / Formen / Messwerkzeuge | geplant | |
| Stempel / Callouts | geplant | |
| KI-Assistent | Stub | Menü „Geplant“ |
| Signieren (rechtssicher) | Stub | |
| Cloud-Sync | Stub | |
| Text on Path / Text zu Pfaden | geplant | |
| Envelope Distort / Text Wrap / Area Type | Stub/geplant | |
| Verkettete Rahmen / Schnittmasken | geplant | |
| Füllungen / Live-Effekte | geplant | |
| 3D-Extrusion | Stub | |
| Variable Fonts (voll) | Stub | |
| Glyphen-Palette | geplant | |
| Stylus / Palm Rejection | Stub | |
| Intelligente Formerkennung | Stub | |

Nicht behauptet als fertig: Cloud, KI, Stylus — nur Menü-Stubs + dieser Status.
