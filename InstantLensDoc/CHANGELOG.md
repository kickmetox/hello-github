# Changelog — InstantLens Doc

## 0.5.5 — Seiten-Historie-UI, Ann.-Export Tags/Gruppen, Encoding-Auto, Quiet Splash

Nach 0.5.4: vier sinnvolle Ausbauten. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Annotationen
- **Seiten-Historie-Liste**: Undo-Stack (gelöschte/gedrehte Seiten) klar in UI — Toolbar „Historie…“ / PDF-Menü; Wiederherstellen bis zum gewählten Eintrag
- **Annotation-Export Tags + Gruppen**: CSV mit `tags`/`group_title`/`group_color`; Bericht mit Gruppenkopf; JSON weiter mit `meta.page_groups`

### Editor / Startup
- **Encoding automatisch**: BOM-Erkennung, optional chardet; Einstellung „Automatisch“ (Default)
- **Quiet Startup**: Splash in Einstellungen überspringbar (`skip_splash`)

### Packaging / Docs
- Version **0.5.5** (App / ild_pdf / ISS / Smoke / Docs)
- Stubs KI/Cloud/Stylus/3D unverändert

---

## 0.5.4 — Seiten-Löschen-Undo, Ann.-Gruppen, Soft-Hyphen/NBSP, Startup-Deps

Nach 0.5.3: vier sinnvolle Ausbauten. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Annotationen
- **Seite löschen mit Undo**: gelöschte Seite inkl. Annotationen per Ctrl+Z wiederherstellen (auch Seitendrehung undo-fähig)
- **Annotation-Gruppen**: Seitengruppen in der Sidebar umbenennen und farblich markieren (Ctrl+Alt+G / Rechtsklick)

### Editor / Startup
- **Soft-Hyphen / NBSP**: Bearbeiten → Sonderzeichen einfügen (Ctrl+Shift+- / Ctrl+Shift+Space)
- **Startup-Check**: pypdfium2 (kritisch) und Tesseract (optional) mit Dialog bei Problemen

### Packaging / Docs
- Version **0.5.4** (App / ild_pdf / ISS / Smoke / Docs)
- Stubs KI/Cloud/Stylus/3D unverändert

---

## 0.5.3 — Kommentar-Bericht, Farbe-Zyklus, Minimap, About-Keygen

Nach 0.5.2: vier sinnvolle Ausbauten. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Annotationen
- **Kommentar-Bericht**: Annotationen als zusammenhängenden TXT- oder Markdown-Bericht exportieren (nach Seite gruppiert)
- **Farbe Palette-Zyklus / Randomizer**: Ctrl+Shift+C bzw. Ctrl+Alt+Shift+C für Highlight-Farbe

### Editor / Lizenz
- **Editor-Minimap** optional (Linien-Übersicht rechts + dickere Scrollbar); Ansicht / Einstellungen / Ctrl+Shift+I
- **About**: Keygen-Hinweis (`run-keygen.bat` / `InstantLensKeygen.exe`) wenn Trial aktiv

### Packaging / Docs
- Version **0.5.3** (App / ild_pdf / ISS / Smoke / Docs)
- Stubs KI/Cloud/Stylus/3D unverändert

---

## 0.5.2 — Selection→Highlight, Ann.-Regex, Text-Diff, Export-Profil

Nach 0.5.1: vier sinnvolle Ausbauten. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Annotationen
- **Selection→Highlight**: Highlight-Drag über PDF-Text erzeugt textgenaue Annotation(en) inkl. Inhalt; sonst freies Rechteck
- Annotation-Suche: optionales **Regex** (Checkbox neben Suchfeld, case-insensitive)

### Editor / Export
- **Dateien vergleichen** (zwei Tabs Side-by-Side, einfacher Zeilen-Diff); Datei → Ctrl+Alt+D
- **Export-Profil speichern** (DPI / Format / Zielordner); Anwenden + Vorbefüllung beim Seiten-Export

### Packaging / Docs
- Version **0.5.2** (App / ild_pdf / ISS / Smoke / Docs)
- Stubs KI/Cloud/Stylus/3D unverändert

---

## 0.5.1 — Batch-OCR, Tags, Workspace, PDF bereinigen

Nach dem Meilenstein 0.5.0: vier sinnvolle Ausbauten. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / OCR / Annotationen
- **Batch-OCR gesamtes PDF** mit Fortschrittsdialog (Seite x/y, Abbrechen) → Editor
- Annotation-**Tags/Labels** (frei, komma-getrennt); Sidecar + CSV; Sidebar-Filter; Ctrl+Alt+T
- Schnellaktion **PDF bereinigen** (Neuschreiben, optional Metadaten strippen)

### Editor / UX
- **Projekt-Ordner als Workspace** (letzte 5); Datei → Projekt-Ordner; Dialog-Startpfad bevorzugt aktiv

### Packaging / Docs
- Version **0.5.1** (App / ild_pdf / ISS / Smoke / Docs)
- Stubs KI/Cloud/Stylus/3D unverändert

---

## 0.5.0 — Release-Konsolidierung (0.4.0 → 0.5.0)

Meilenstein: alle 0.4.x-Inkremente gebündelt, Version einheitlich **0.5.0**, Smoke um ausgewählte 0.4.x-Pfade erweitert, kleine Review-Fixes. Stubs KI/Cloud/Stylus/3D bleiben Stubs (keine Fake-Features).

### PDF / Annotationen
- Native **Link-Annotationen**; **Stempel-Rotation** 90°; Outline-Goto gehärtet (objgen)
- Annotation **Copy/Paste**, **Lock**, CropBox-/**Druckermarken**-Overlay
- Sidecar **Schema v4** (`ildann-v4`) Export + Import-Validierung; **Notizfarbe** unabhängig
- Farben-Chips-Filter; Zeitstempel in Liste; Filter **nur aktuelle Seite**
- **Seitenlabels** (römisch/arabisch); Seitenbild→Editor; **Gehe zu Seite**
- Zwei-Seiten-Ansicht (**Spread**); **Continuous Scroll**

### Editor / UX
- Encoding UTF-8/Latin-1; Multi-Drop; Case gesamte Datei; Snippets; Templates
- Zeilen sortieren; Settings-Reset; Trim trailing/paste; Bracket-Match
- Zwischenablage-Verlauf; Tab duplizieren; Undo-Hint; Arbeitsverzeichnis öffnen
- Cheat-Sheet als PDF; About Feature-Kurzliste + FEATURES.md
- Flatten/Bake Progress; Batch Abbrechen

### Packaging / Docs
- Inno Setup / Build / INFO / FEATURES / README auf **0.5.0**
- Sync: `scripts/sync-ild.ps1` (Repo) bzw. Store `docs/sync-ild.ps1`
- Smoke: open / annotate / export / license + ausgewählte 0.4.x-Pfade (CLI + offscreen Qt)

### Review-Fixes (0.5.0)
- Versionsstrings App / `ild_pdf` / ISS / Smoke / Docs vereinheitlicht
- CHANGELOG 0.4.1–0.4.9 zu Kurz-Tabelle verdichtet (wie zuvor 0.3.x)
- Doppelte Leerzeile im Changelog-Abschnitt 0.4.7 entfernt (Kompaktierung)

---

## 0.4.0 — Release-Konsolidierung (0.3.0 → 0.4.0)

Meilenstein: alle 0.3.x-Inkremente gebündelt, Version einheitlich **0.4.0**, Smoke um ausgewählte 0.3.x-Pfade erweitert, kleine Review-Fixes. Stubs KI/Cloud/Stylus/3D bleiben Stubs (keine Fake-Features).

### PDF / Seiten
- AcroForm-Felder lesen/schreiben; Stempel-Bibliothek GENEHMIGT/ENTWURF/VERTRAULICH
- Anhänge auflisten/extrahieren; Seiten als Einzel-PDFs; Text → Editor (Seite/gesamt)
- Raster-Export DPI 72/150/300; Thumbnail-Größe klein/normal/groß; Lazy-Load
- Fit-Width Ctrl+9 / **Fit-Height Ctrl+8**; Präsentationsmodus F5
- Seitengröße Statusleiste mm/inch; Fenster-Geometrie speichern

### Annotationen
- Layer ein-/ausblenden; Flatten/Bake → PDF; Duplizieren; Select-All Seite
- Sidebar: Typ-Filter, Textsuche, Gruppierung nach Seite, **Statistik je Typ**
- Farben-Favoriten (3 Presets); CSV-Export; Sidecar v3

### Editor / UX
- Soft-Wrap; Markdown-Vorschau; Sonderzeichen; Gehe zu Zeile; Zeile duplizieren/verschieben
- Block Tab/Shift+Tab; Kommentar Ctrl+/; Backup `.bak`; Overwrite-Schutz Export
- Session-Restore Toggle; Tray-Minimize + Tray-Tooltip mit Version
- Tab schließen (dirty); Lizenz Resttage/Ablauf klar; Zuletzt verwendete Ordner

### Packaging / Docs
- Inno Setup / Build / INFO / FEATURES / README auf **0.4.0**
- Sync: `scripts/sync-ild.ps1` (Repo) bzw. Store `docs/sync-ild.ps1`
- Smoke: open / annotate / export / license + ausgewählte 0.3.x-Pfade (CLI + offscreen Qt)

### Review-Fixes (0.4.0)
- `installer/installer-hinweis.txt` Version auf aktuelle Release gebracht (war 0.3.3)
- Versionsstrings App / `ild_pdf` / ISS / Smoke / Docs vereinheitlicht
- CHANGELOG 0.3.1–0.3.9 zu Kurz-Tabelle verdichtet (wie zuvor 0.2.x)

### 0.4.x-Inkremente (Kurz)

| Ver. | Kern |
|------|------|
| **0.4.1** | PDF-Links, Stempel-Rotation, Encoding, Multi-Drop |
| **0.4.2** | Outline-Goto, Ann.-Copy/Paste, Case-Datei, Progress |
| **0.4.3** | CropBox-Overlay, Ann.-Lock, Snippets, Templates |
| **0.4.4** | Druckermarken, Ann.-Schema v4, Zeilen sortieren, Settings-Reset |
| **0.4.5** | Seitenbild→Editor, Ann.-Import-Validierung, Trim, Toolbar |
| **0.4.6** | Goto Page, Ann.-Farben-Filter, Duplikat-Tab, Undo-Hint |
| **0.4.7** | Spread, Notizfarbe, Paste-Trim, Cheat-Sheet-PDF |
| **0.4.8** | Continuous Scroll, Ann.-Zeitstempel, Bracket-Match, Arbeitsverzeichnis |
| **0.4.9** | Seitenlabels, Ann.-Seitenfilter, Clipboard-Verlauf, About-Features |

→ zusammengeführt in **0.5.0**.

---

## 0.3.0 — Release-Meilenstein

Fokus: Konsolidierung 0.2.x → 0.3.0 (Versioning, Smoke, Docs, Review-Fixes Opacity/Ann-Suche/Toolbar/Indent/Sync). Inno gehärtet, Stubs ohne Fake-Features.

### 0.3.x-Inkremente (Kurz)

| Ver. | Kern |
|------|------|
| **0.3.1** | AcroForm, Stempel-Bibliothek, Tab schließen, Thumb Lazy-Load |
| **0.3.2** | Anhänge, Ann.-Layer, Markdown-Vorschau, recent_dirs |
| **0.3.3** | Einzel-PDFs, Ann.-Flatten, Soft-Wrap, Lizenz Resttage |
| **0.3.4** | PDF-Text→Editor, Ann.-Duplikat, Goto Line, Tray-Minimize |
| **0.3.5** | Seitengröße Status, Ann.-Gruppen, Zeile duplizieren, Backup .bak |
| **0.3.6** | Raster-DPI, Ann. Select-All, Kommentar Ctrl+/, Fenstergeometrie |
| **0.3.7** | Präsentation F5, Ann.-Favoriten, Block-Tab, Session-Toggle |
| **0.3.8** | Thumbnail-Größe, Ann.-CSV, Zeile verschieben, Overwrite-Schutz |
| **0.3.9** | Fit-Height, Ann.-Statistik, Sonderzeichen, Tray-Version |

→ zusammengeführt in **0.4.0**.

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
