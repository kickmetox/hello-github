# Changelog — InstantLens Doc

## 0.2.0 — Release-Meilenstein

Fokus: Release-Reife (Versioning, Installer, Smoke, Docs) statt neuer Micro-Features.

### Stabilität & Packaging
- Version **0.2.0** einheitlich (App, `ild_pdf`, About, ISS, Docs, Smoke, Sync)
- Inno Setup gehärtet: Setup-/Uninstall-Icon, Desktop-Shortcut (Standard an), Startmenü-Uninstaller, optionaler Keygen (`IncludeKeygen`)
- `build-windows.ps1`: Icon-Check, Docs/CHANGELOG in Dist, Keygen optional in App-Dist
- `open_document`: klare Fehler bei fehlender/ungültiger Datei
- Stubs KI/Cloud/Stylus/3D bleiben Stubs (keine Fake-Funktionalität)

### Dokumentation
- `CHANGELOG.md` (diese Datei)
- README Quickstart Windows (Sync-Zeile + `run.bat`)
- INFO/FEATURES auf 0.2.0

### Tests
- Regression-Smoke: Kernpfade **open / annotate / export / license**

---

## 0.1.x — Kurzüberblick (→ 0.2.0)

| Version | Kern |
|---------|------|
| **0.1.9** | Metadaten-Editor, Seitengröße/Crop, Export-Qualität, i18n DE/EN, Update-Check, Redaction-UX |
| **0.1.8** | Redaction, PDF-Passwort, Bildkompression, Thumbnails, F1-Hilfe, Logging |
| **0.1.7** | Wasserzeichen, Seitennummern, PDF-Vergleich, Clipboard-Paste, Session-Restore, Zoom-Cache |
| **0.1.6** | Batch, PDF merge/split, Outline, Volltext, Einstellungen |
| **0.1.5** | Signatur, Theme, OCR-Tabellen, Autosave, Drag-Drop |
| **0.1.4** | Undo/Redo, Zoom/Fit, Recent, Druck, Lizenz-Statusleiste |
| **0.1.3** | Overlay-Editor, Formen/Lineal, Export HTML/DOCX/PDF, Installer-Basis |
| **0.1.2** | Stempel/Callout, Rahmen-Kette, OCR-Modi, Formular-Typen, build-windows |
| **0.1.1** | Icon-Auflösung, Inno + Sync, Annotation speichern, Seiten neu anordnen |
| **0.1.0** | MVP: UI, PDF/Annotationen, OCR-Bridge, Formulare, Lizenz Trial/Keys, Keygen |

Vollständige Feature-Liste: [FEATURES.md](FEATURES.md).
