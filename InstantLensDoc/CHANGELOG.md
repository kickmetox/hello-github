# Changelog — InstantLens Doc

## 0.2.7 — Spiegeln, Ann.-Edit, Zeilennummern, Alles speichern

Fokus: PDF-Spiegeln, Annotation-Text nachträglich, Editor-Zeilennummern, Speichern aller Tabs.

### PDF
- **Seite spiegeln**: horizontal (↔) und vertikal (↕) (`ild_pdf.flip_page`; Toolbar + Menü PDF)

### Annotationen
- **Notiz/Kommentar/Overlay-Text nachträglich editierbar** (Doppelklick / Ctrl+Klick / Bearbeiten → Ctrl+E)

### Editor / UX
- **Zeilennummern optional** (Ansicht-Menü + Einstellungen)
- **Alles speichern** für offene Tabs (Ctrl+Alt+Shift+S; aktuelles Doc + PDF-Sidecars)

### Docs / Packaging
- Version **0.2.7**; Stubs KI/Cloud/Stylus/3D unverändert (keine Fake-Features)
- Docs/CHANGELOG/ISS/Smoke auf 0.2.7

---

## 0.2.6 — Seitenbereich, Ann.-Filter, Find/Replace, Lizenz-Warnung

Fokus: PDF-Seitenbereich, Annotation-Filter, Editor Ersetzen, Lizenz <7 Tage.

### PDF
- **Seitenbereich extrahieren**: von–bis → neues PDF (`ild_pdf.extract_page_range`; Menü PDF + Dialog-Tab)

### Annotationen / Sidebar
- **Filter nach Typ** in der Annotationen-Liste (Dropdown)

### Editor / UX
- **Suchen und Ersetzen** (Ctrl+R, Dialog Find/Replace/Alle)
- **Lizenz-Resttage** bei <7 Tagen prominent (Hintergrund + Warnung in Statusleiste)

### Docs / Packaging
- Version **0.2.6**; Stubs KI/Cloud/Stylus/3D unverändert (keine Fake-Features)
- Docs/CHANGELOG/ISS/Smoke auf 0.2.6

---

## 0.2.5 — Outline editieren, Ann.-JSON, Wortzählung, PDF-Kopie

Fokus: Lesezeichen bearbeiten, Annotation-Austausch, Editor-Status, PDF-Kopie.

### PDF / Outline
- **Lesezeichen hinzufügen/löschen**: Sidebar +/− und Menü PDF; `ild_pdf.add_outline_item` / `delete_outline_item`
- **PDF als Kopie speichern**: Datei + Sidecar kopieren, aktuelles Dokument bleibt geöffnet (Datei / Menü PDF)

### Annotationen
- **JSON exportieren/importieren**: Menü PDF; Import ersetzen oder anhängen (`AnnotationStore.export_json` / `import_json`)

### UX
- **Wortzählung Statusleiste** (Editor: Wörter · Zeichen; PDF: Annotation-Anzahl); keine schwere Spellcheck-Lib

### Docs / Packaging
- Version **0.2.5**; Stubs KI/Cloud/Stylus/3D unverändert (keine Fake-Features)
- Docs/CHANGELOG/ISS/Smoke auf 0.2.5

---

## 0.2.4 — Seiten drehen, leere/duplizieren, Ann.-Liste, Suchhistorie

Fokus: PDF-Seiten-Ops in der Toolbar, Annotation-Navigation, Suchbegriffe merken.

### PDF / Seiten
- **Seite drehen**: Toolbar ⟲ (−90°) / ⟳ (+90°), speichert sofort; Menü PDF; Thumbnails aktualisieren
- **Leere Seite einfügen** / **Seite duplizieren** (Toolbar + Menü), Annotation-Remap, speichern

### UX
- **Annotation-Liste** in der Sidebar (klickbar → Seite + Auswahl)
- **Letzte Suchbegriffe** merken (Dropdown, persistiert)

### Docs / Packaging
- Version **0.2.4**; Stubs KI/Cloud/Stylus/3D unverändert (keine Fake-Features)
- Docs/CHANGELOG/ISS/Smoke auf 0.2.4

---

## 0.2.3 — Seitenbilder, Annotation löschen, Statusleiste, Thumb-Reorder

Fokus: PDF-Seiten→Bild, Annotation-Löschen, Statusinfo, Thumbnail-Drag.

### PDF / Export
- **Seiten als Bild**: aktuelle oder alle Seiten als PNG/JPEG exportieren (Menü + Toolbar); Zielordner merken
- **Annotation löschen**: Auswahl (Werkzeug Auswahl / Shift-Klick / Rechtsklick) oder letzte Annotation; Entf / Menü Bearbeiten

### UX
- **Statusleiste**: Dateiname, Seite x/y, Zoom % (permanent neben Version/Lizenz)
- **Thumbnail-Sidebar**: Drag-Reorder der Seiten (wie Dialog „Neu anordnen“), Annotation-Remap

### Docs / Packaging
- Version **0.2.3**; Stubs KI/Cloud/Stylus/3D unverändert (keine Fake-Features)
- Docs/CHANGELOG/ISS/Smoke auf 0.2.3

---

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
| **0.1.2** | Stempel/Callout, Rahmen-Kette, OCR-Modi, Formulare, build-windows |
| **0.1.1** | Icon-Auflösung, Inno + Sync, Annotation speichern, Seiten neu anordnen |
| **0.1.0** | MVP: UI, PDF/Annotationen, OCR-Bridge, Formulare, Lizenz Trial/Keys, Keygen |

Vollständige Feature-Liste: [FEATURES.md](FEATURES.md).
