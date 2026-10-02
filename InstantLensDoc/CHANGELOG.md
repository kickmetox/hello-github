# Changelog — InstantLens Doc

## 0.2.2 — Suche, Farben, Export, Einstellungen

Fokus: PDF-Textsuche sichtbar machen, Annotation-Farben, Export/Settings-UX.

### PDF / Annotationen
- **Textsuche Highlight**: Treffer auf der aktuellen Seite werden hervorgehoben; „Weiter“ springt zum nächsten Treffer
- **Farben-Picker**: Highlight- und Stift-Farbe (Linie/Pfeil/Rechteck/Unterstreichen) in der Toolbar; persistiert

### Export / Einstellungen
- **Export-Dialog**: zuletzt genutzter Zielordner wird gemerkt (`last_export_dir`)
- **Standard-Zoom** und **Autosave-Intervall** in Einstellungen (persistiert, live übernommen)

### Bugfixes / Docs
- PDF-Suche „Weiter“ funktioniert jetzt (vorher ohne Wirkung)
- Version **0.2.2**; Stubs KI/Cloud/Stylus/3D unverändert (keine Fake-Features)
- Docs/CHANGELOG/ISS/Smoke auf 0.2.2

---

## 0.2.1 — Qualitäts-Patch

Fokus: UX-Lücken und Stabilität, keine Feature-Spam.

### UX
- **Speichern unter (PDF)**: klar Sidecar-Annotationen (`*.ildann.json`) wählen — PDF bleibt unverändert; Menü PDF → Annotationen speichern unter…; Shortcut `Ctrl+Shift+S`
- **Batch**: Fortschrittsbalken + Statuszeile (Datei i/n)
- **OCR**: Fortschrittsdialog während der Erkennung

### Stabilität
- Crash-sichere PDF-Öffnung (Datei-Check, Sidecar-Fehler isoliert, Busy-Cursor)
- Timeout-/Hang-Hinweis (~30s) bei großen/problematischen PDFs

### Packaging / Docs
- Keygen-EXE-Pfad im Installer dokumentiert (`InstantLensKeygen.exe` neben App bzw. `run-keygen.bat`)
- Menü-Ordnung: Einstellungen → Extras; PDF-Gruppen; Hilfe (F1 zuerst)
- F1-Tastaturhilfe um fehlende Shortcuts ergänzt
- Version **0.2.1**; Stubs KI/Cloud/Stylus/3D unverändert (keine Fake-Features)

---

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
