# InstantLens Doc — Features

Statuslegende: **fertig** · **teilweise** · **geplant** · **Stub**

| Feature | Status | Hinweis |
|---------|--------|---------|
| Hauptfenster (Menü, Sidebar, Editor, Status) | fertig | PySide6 |
| App-Icon Fenster/Taskleiste/About | fertig | Robuste Pfade: `assets/`, CWD, `D:\AI_Temp\InstantLensDoc` |
| TXT / MD / HTML öffnen & speichern | fertig | |
| DOCX öffnen & speichern | teilweise | python-docx; Layout nicht 1:1 |
| PDF lesen / rendern | fertig | pypdfium2 |
| PDF-Annotationen (Highlight, Underline, Sticky, Text) | fertig | Sidecar `*.ildann.json`; speichern/laden in UI + Menü PDF |
| PDF drehen / Seite löschen | fertig | pikepdf + Bestätigung |
| PDF neu anordnen | fertig | Dialog in Toolbar / Menü PDF |
| Textsuche Seitenleiste | fertig | Editor: alle Treffer markieren; PDF: Annotationen filtern |
| Markieren im Editor | fertig | Ctrl+H / Bearbeiten → Auswahl markieren |
| Bilder JPEG/PNG anzeigen | fertig | |
| OCR Bild/PDF-Seite | teilweise | Bridge; klare UX + Install-Hinweis wenn Tesseract fehlt |
| Formulargenerator → HTML/PDF | fertig | Live-Vorschau, Feld entfernen, Export |
| Layout: Textrahmen, Bild, einfacher Umbruch | teilweise | MVP, kein DTP |
| Lizenz Trial 28d / Keys 32d | fertig | |
| Keygenerator (CLI/GUI) | fertig | `run-keygen.bat` / `python -m keygen --gui` |
| Inno-Installer | fertig | `installer/instantlensdoc.iss` + `build-installer.ps1` |
| Sync-Skript Windows | fertig | Store `docs/sync-ild.ps1` (Icon nicht überschreiben) |
| In-App Hilfe / About | fertig | Icon im About |
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
