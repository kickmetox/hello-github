# Changelog — InstantLens Doc

## 0.3.6 — Raster-DPI, Ann. Select-All, Kommentar, Fenstergeometrie

Fokus auf sinnvolle Ausbauten nach 0.3.5. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- **Raster-Export DPI wählbar** (72 / 150 / 300) beim Export Seite/Seiten als Bild; Einstellung merken
- **Alle Annotationen auf Seite auswählen** (Ctrl+A im PDF-Modus; Mehrfachauswahl + Löschen)

### Editor / UX
- **Zeile kommentieren/auskommentieren** (Ctrl+/; Präfix `#` oder `//` je nach Dateityp)
- **Fenster-Geometrie** speichern/wiederherstellen (Größe, Position, Window-State)

### Packaging / Docs
- Version **0.3.6** (App, `ild_pdf`, ISS, Smoke, INFO/FEATURES/README)

---

## 0.3.5 — Seitengröße, Ann.-Gruppen, Zeile duplizieren, Backup

Fokus auf sinnvolle Ausbauten nach 0.3.4. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- **Seitengröße in Statusleiste** (MediaBox mm/inch; Klick oder Ctrl+Alt+U zum Umschalten)
- **Seitengröße-Dialog**: Einheit mm/inch Toggle (persistiert)
- **Annotationen in Sidebar nach Seite gruppiert** (Überschriften „Seite n“)

### Editor / UX
- **Zeile duplizieren** (Ctrl+D; Auswahl mehrerer Zeilen möglich)
- **Backup-Kopie (.bak) beim Speichern** optional in Einstellungen

### Packaging / Docs
- Version **0.3.5** (App, `ild_pdf`, ISS, Smoke, INFO/FEATURES/README)

---

## 0.3.4 — PDF-Text→Editor, Ann.-Duplikat, Goto Line, Tray

Fokus auf sinnvolle Ausbauten nach 0.3.3. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- **Text extrahieren → Editor**: aktuelle Seite oder gesamtes PDF (mit Seitenköpfen) in den Editor-Tab (`extract_page_plain_text` / `extract_all_plain_text`)
- **Annotation duplizieren** (Auswahl; leicht versetzt, neue ID; Ctrl+Shift+D)

### Editor / UX
- **Gehe zu Zeile** Dialog (Ctrl+G)
- **Minimieren in System-Tray** optional in Einstellungen

### Packaging / Docs
- Version **0.3.4** (App, `ild_pdf`, ISS, Smoke, INFO/FEATURES/README)

---


## 0.3.3 — Einzel-PDFs, Ann.-Flatten, Soft-Wrap, Lizenz

Fokus auf sinnvolle Ausbauten nach 0.3.2. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- **Seiten als Einzel-PDFs** (PDF → Seiten als Einzel-PDFs…; `split_into_single_page_pdfs`)
- **Annotationen flatten/bake** Export: alle Seiten mit eingezeichneten Annotationen → neues PDF (`flatten_annotations_to_pdf`)

### Editor / UX
- **Soft-Wrap Toggle** (Ansicht + Einstellungen; Ctrl+Shift+W)
- **Lizenz-Dialog**: Resttage und Ablaufdatum klarer dargestellt

### Packaging / Docs
- Version **0.3.3** (App, `ild_pdf`, ISS, Smoke, INFO/FEATURES/README)

---

## 0.3.2 — Anhänge, Ann.-Layer, MD-Preview, Ordner

Fokus auf sinnvolle Ausbauten nach 0.3.1. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- **Anhänge** auflisten/extrahieren wenn vorhanden (PDF → Anhänge…; `ild_pdf.attachments`)
- **Annotation-Layer** ein-/ausblenden (Ansicht + Toolbar „Ann.“; Ctrl+Shift+A)

### Editor / UX
- **Markdown-Vorschau** optional als Split (Ansicht → Markdown-Vorschau; Ctrl+Shift+M)
- **Zuletzt verwendete Ordner** in Datei-Dialogen merken (`recent_dirs` in Settings)

### Packaging / Docs
- Version **0.3.2** (App, `ild_pdf`, ISS, Smoke, INFO/FEATURES/README)

---

## 0.3.1 — Formulare, Stempel, Close, Thumbs

Fokus auf sinnvolle Ausbauten nach dem 0.3.0-Meilenstein. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- **AcroForm-Formularfelder** lesen/schreiben (pikepdf `Form`): Text, Checkbox, Choice, Radio — Menü PDF → Formularfelder ausfüllen…
- **Stempel-Bibliothek** GENEHMIGT / ENTWURF / VERTRAULICH mit optionalem Datum; Dialog statt einfacher Liste

### UX / Performance
- **Tab schließen** (Datei → Schließen / Ctrl+W) mit Speichern-Dialog wenn dirty; auch beim Beenden
- **Thumbnail-Lazy-Load**: Platzhalter sofort, Seiten einzeln nachladen (aktuelle Seite zuerst)

### Packaging / Docs
- Version **0.3.1** (App, `ild_pdf`, ISS, Smoke, INFO/FEATURES/README)

---

## 0.3.0 — Release-Konsolidierung (0.2.0 → 0.3.0)

Meilenstein: alle 0.2.x-Inkremente gebündelt, Version einheitlich **0.3.0**, Smoke um Kernpfade erweitert, kleine Review-Fixes. Stubs KI/Cloud/Stylus/3D bleiben Stubs (keine Fake-Features).

### PDF / Seiten
- Drehen, spiegeln (H/V), leere Seite, duplizieren, Thumb-Reorder
- Seitenbereich extrahieren, Seite(n) → PNG/JPEG, Graustufen (Ansicht + Export)
- **Nachtmodus** (Invert-Ansicht, nur Darstellung — nicht speichern/exportieren)
- Outline hinzufügen/löschen, PDF als Kopie, Wasserzeichen/Seitennummern, Metadaten, Seitengröße/Crop
- Passwort, Bildkompression, Redaction einbrennen, Signaturfeld/-bild

### Annotationen
- Sidecar `*.ildann.json` v3; Farben-Picker; Löschen Auswahl/letzte; Undo/Redo
- Sidebar-Liste mit Typ-Filter + **Textsuche** (inkl. DE-Typ-Labels)
- Text nachträglich editierbar; Deckkraft/Opacity (ohne doppelte α-Multiplikation)
- JSON Export/Import

### Editor / UX
- Find/Replace, Zeilennummern, Groß-/Kleinschreibung, **Einrückung** +/-
- Wortzählung Statusleiste; Alles speichern; Lizenz <7 Tage prominent
- Splash + Fenstertitel/About; **Hilfe → Logordner öffnen**
- Suchhistorie, Session, Theme, i18n DE/EN (teilweise)

### Packaging / Docs
- Inno Setup / Build / INFO / FEATURES / README Quickstart auf **0.3.0**
- Sync: `scripts/sync-ild.ps1` (Repo) bzw. Store `docs/sync-ild.ps1`
- Smoke: open / annotate / export / license + 0.2.x-Kernpfade (CLI + offscreen Qt)

### Review-Fixes (0.3.0)
- Toolbar Graustufen/Nacht sync mit Ansicht-Menü
- Annotation-Opacity nicht doppelt angewandt
- Annotation-Suche findet deutsche Typ-Labels
- Einrückung: Auswahl über Blocknummern wiederherstellen
- Sync-Pfad-Hinweise korrigiert

---

## 0.2.0 — Release-Meilenstein

Fokus: Release-Reife (Versioning, Installer, Smoke, Docs). Inno gehärtet, `open_document`-Fehler klar, Stubs ohne Fake-Features. README Quickstart + CHANGELOG eingeführt.

### 0.2.x-Inkremente (Kurz)

| Ver. | Kern |
|------|------|
| **0.2.1** | Sidecar/Fortschritt-UX, PDF-Open-Stabilität, Keygen-Pfad |
| **0.2.2** | Textsuche-Highlight, Farben-Picker, Export/Settings |
| **0.2.3** | Seiten→Bild, Ann. löschen, Statusleiste, Thumb-Reorder |
| **0.2.4** | Drehen, leere/duplizieren, Ann.-Liste, Suchhistorie |
| **0.2.5** | Outline edit, Ann.-JSON, Wortzählung, PDF-Kopie |
| **0.2.6** | Seitenbereich, Ann.-Filter, Find/Replace, Lizenz-Warnung |
| **0.2.7** | Spiegeln, Ann.-Edit, Zeilennummern, Alles speichern |
| **0.2.8** | Graustufen, Ann.-Opacity, Case-Toggle, Splash/Titel |
| **0.2.9** | Nachtmodus, Ann.-Suche, Einrückung, Logordner |

→ zusammengeführt in **0.3.0**.

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
