# Changelog — InstantLens Doc

## 0.4.9 — Seitenlabels, Ann.-Seitenfilter, Clipboard-Verlauf, About-Features

Fokus (letzte 0.4.x vor 0.5.0): PDF-Seitenlabels (römisch/arabisch) anzeigen wenn vorhanden, Annotation-Filter „nur aktuelle Seite“, Editor Zwischenablage-Verlauf (3 Einträge), About-Dialog mit Feature-Kurzliste + FEATURES.md. Stubs KI/Cloud/Stylus/3D unverändert.

### PDF / Annotationen
- **PDF-Seitenlabels**: römische/arabische Labels aus dem PDF in Statusleiste und Toolbar, wenn PageLabels vorhanden (`ild_pdf.PdfDocument.page_label` / `format_page_status`)
- **Annotation-Filter „nur aktuelle Seite“**: Checkbox in der Sidebar; Liste folgt der aktuellen PDF-Seite

### Editor / UX
- **Zwischenablage-Verlauf**: letzte 3 eingefügten Textschnipsel (Bearbeiten-Menü); erneutes Einfügen
- **About-Dialog**: Feature-Kurzliste + Button „FEATURES.md öffnen…“

### Packaging / Docs
- Version **0.4.9** (App, `ild_pdf`, ISS, Build, Docs, Smoke)
- FEATURES / INFO / CHANGELOG / Hilfe aktualisiert

---

## 0.4.8 — Continuous Scroll, Ann.-Zeitstempel, Bracket-Match, Arbeitsverzeichnis

Fokus: optionaler PDF Continuous Scroll statt Einzelseite, Annotation-Zeitstempel in der Sidebar-Liste, Editor Bracket-Match Highlight, Menü „Arbeitsverzeichnis öffnen“. Stubs KI/Cloud/Stylus/3D unverändert.

### PDF / Annotationen
- **Continuous Scroll** optional (Ansicht / Toolbar „CS“ / Ctrl+3): Seiten untereinander scrollen; schließt Zwei-Seiten-Ansicht aus; Fenster bis 40 Seiten
- **Annotation-Zeitstempel** in der Sidebar-Liste (modified/created, lokal formatiert)

### Editor / UX
- **Bracket-Match Highlight** (Einstellungen, Standard an): passende Klammern `()[]{}` am Cursor hervorheben
- **Arbeitsverzeichnis öffnen** (Datei / Ctrl+Shift+E): Ordner der aktuellen Datei bzw. Prozess-CWD im Dateimanager

### Packaging / Docs
- Version **0.4.8** (App, `ild_pdf`, ISS, Build, Docs, Smoke)
- FEATURES / INFO / CHANGELOG / Hilfe aktualisiert

---

## 0.4.7 — Spread, Notizfarbe, Paste-Trim, Cheat-Sheet-PDF


Fokus: optionale PDF-Zwei-Seiten-Ansicht, Annotation-Notizfarbe unabhängig von Highlight, optionales Whitespace-Trim beim Einfügen, Keyboard-Cheat-Sheet als PDF aus F1. Stubs KI/Cloud/Stylus/3D unverändert.

### PDF / Annotationen
- **Zwei-Seiten-Ansicht (Spread)** optional (Ansicht / Toolbar „2S“ / Ctrl+2): aktuelle + nächste Seite nebeneinander; Blättern springt um 2 Seiten
- **Notizfarbe unabhängig von Highlight**: eigener Picker „Notiz“ + Setting `ann_note_color`; Sticky nutzt diese Farbe (nicht mehr fest bzw. HL)

### Editor / UX
- **Whitespace trim on paste** optional (Einstellungen): Trailing Spaces/Tabs pro Zeile beim Einfügen entfernen
- **Tastaturhilfe → PDF**: F1-Dialog „Als PDF exportieren…“ schreibt das Cheat-Sheet

### Packaging / Docs
- Version **0.4.7** (App, `ild_pdf`, ISS, Build, Docs, Smoke)
- FEATURES / INFO / CHANGELOG / Hilfe aktualisiert

---

## 0.4.6 — Goto Page, Ann.-Farben-Filter, Duplikat-Tab, Undo-Hint

Fokus: PDF-Seitensprung per Dialog, klickbare Annotation-Farben in der Sidebar-Statistik, Editor-Tab duplizieren, Statusleisten-Hinweis „Letzte Aktion rückgängig“. Stubs KI/Cloud/Stylus/3D unverändert.

### PDF / Annotationen
- **Gehe zu Seite** (Ctrl+G im PDF / Ctrl+Shift+G / Menü PDF): Dialog mit Seitennummer → Sprung
- **Annotation-Farben-Filter**: Farben-Chips in der Sidebar-Statistik klickbar; erneuter Klick / „Alle“ hebt Filter auf

### Editor / UX
- **Tab duplizieren** (Ctrl+Shift+T): Editor-Inhalt als neues Dokument klonen; **Erneut öffnen** (Ctrl+Alt+Shift+O) lädt Datei vom Datenträger neu
- **Statusleiste**: Hint „Ctrl+Z · Letzte Aktion rückgängig“ (statt Quiet-Hours)

### Packaging / Docs
- Version **0.4.6** (App, `ild_pdf`, ISS, Build, Docs, Smoke)
- FEATURES / INFO / CHANGELOG / Hilfe aktualisiert

---

## 0.4.5 — PDF-Seitenbild Editor, Ann.-Import v4, Trim, Toolbar

Fokus: gerenderte PDF-Seiten als Bildreferenz in den Editor, strikte Schema-v4-Validierung beim Annotation-JSON-Import, optionales Trailing-Whitespace-Trim beim Speichern, anpassbare PDF-Toolbar-Gruppen. Stubs KI/Cloud/Stylus/3D unverändert.

### PDF / Editor
- **PDF-Seitenbild → Editor**: aktuelle Seite oder alle Seiten als PNG neben dem PDF + Verweiszeile im Editor (Menü PDF)
- **Annotation-Import Schema v4**: JSON-Import prüft `version`/`schema` und Annotation-Struktur; klare Fehlermeldung bei Abweichung (`AnnotationImportError`)

### Editor / UX
- **Trailing Whitespace beim Speichern** optional (Einstellungen; gilt für Speichern/Autosave)
- **PDF-Toolbar anpassbar**: Gruppen (Werkzeuge, Farben, Ansicht, …) in Einstellungen ein-/ausblenden

### Packaging / Docs
- Version **0.4.5** (App, `ild_pdf`, ISS, Build, Docs, Smoke)
- FEATURES / INFO / CHANGELOG / Hilfe aktualisiert

---

## 0.4.4 — Druckermarken, Ann.-Schema v4, Zeilen sortieren, Settings-Reset

Fokus: Seitenrand-Druckermarken, PDF-Highlight-kompatibler Annotation-Export (Schema v4), Editor-Sortierung, Einstellungen zurücksetzen. Stubs KI/Cloud/Stylus/3D unverändert.

### PDF
- **Seitenrand-Druckermarken** optional (Ansicht + Toolbar „Marken“, Ctrl+Alt+M) — Crop-/Registration-Marks am CropBox/MediaBox (Spiegeln H/V bleibt wie in 0.2.7)
- **Annotation-Export Schema v4** (`ildann-v4`): Highlights/Underlines mit `rects`, `quadPoints`, `colorRGB`, `pdf_highlight` — PDF-Highlight-Interop; Sidecar speichert Kernfelder mit `version: 4` / `schema`

### Editor / UX
- **Zeilen sortieren (A–Z)**: Auswahl alphabetisch (ohne Auswahl: gesamte Datei); Ctrl+Shift+O
- **Einstellungen → Auf Standard zurücksetzen**: alle UI-Settings auf Werkseinstellungen

### Packaging / Docs
- Version **0.4.4** (App, `ild_pdf`, ISS, Build, Docs, Smoke)
- FEATURES / INFO / CHANGELOG / Hilfe / Schema-Doku aktualisiert

---

## 0.4.3 — CropBox-Overlay, Ann.-Lock, Snippets, Templates

Fokus: Seitenrahmen-Overlay, Annotation-Sperre, Editor-Textbausteine, Dokument-Vorlagen. Stubs KI/Cloud/Stylus/3D unverändert.

### PDF
- **Seitenrahmen / CropBox-Overlay** optional (Ansicht + Toolbar „Rahmen“; MediaBox durchgezogen, CropBox gestrichelt wenn abweichend)
- **Annotation-Lock**: Toggle sperrt Verschieben per Drag (Auswahl-Werkzeug + Ziehen wenn entsperrt); Persistenz in Settings

### Editor / UX
- **Textbausteine**: 3 gespeicherte Snippets (Einfügen Ctrl+Alt+1..3; Auswahl → Slot)
- **Neues Dokument**: Vorlagen Leer / Brief / Notiz (Datei → Neu)

### Packaging / Docs
- Version **0.4.3** (App, `ild_pdf`, ISS, Build, Docs, Smoke)
- FEATURES / INFO / CHANGELOG / Hilfe aktualisiert

---

## 0.4.2 — Outline-Goto, Ann.-Copy/Paste, Case-Datei, Progress

Fokus: Navigation/Clipboard/Editor-Batch-Härte. Stubs KI/Cloud/Stylus/3D unverändert.

### PDF
- **Lesezeichen-Goto gehärtet**: Destination-Auflösung über `objgen` (nicht `==` — Blank-Pages trafen sonst immer Seite 1); `resolved_destination` / GoTo-Action; Doppelklick + Enter; Status bei fehlendem Ziel
- **Annotationen kopieren/einfügen** zwischen Seiten (Ctrl+Alt+C / Ctrl+Alt+V; internes Clipboard)
- **Flatten/Bake**: QProgressDialog mit Seitenfortschritt und Abbrechen

### Editor / UX
- **Alles großschreiben / Alles kleinschreiben** für die gesamte Datei (Ctrl+Alt+Shift+U / L)
- **Batch**: Abbrechen-Lauf, Fehlerdialog, UI während Lauf gesperrt; `InterruptedError` nicht als Item-Fehler geschluckt

### Packaging / Docs
- Version **0.4.2** (App, `ild_pdf`, ISS, Build, Docs, Smoke)
- FEATURES / INFO / CHANGELOG / Hilfe aktualisiert

---

## 0.4.1 — PDF-Links, Stempel-Rotation, Encoding, Multi-Drop

Fokus: sinnvolle UX-Inkremente ohne Feature-Spam. Stubs KI/Cloud/Stylus/3D unverändert.

### PDF
- Native **Link-Annotationen** (http/https) klickbar öffnen — Werkzeug Auswahl oder Ctrl+Klick; Hand-Cursor
- Einfache **Stempel-Rotation** in 90°-Schritten (Toolbar „Stempel ↻“, Menü, Edit-Dialog; Sidecar-Feld `rotation`)

### Editor / UX
- **Encoding** UTF-8 / Latin-1 beim Öffnen und Speichern (Menü + Einstellungen-Standard)
- **Drag & Drop** mehrerer Dateien öffnet mehrere Tabs (Sidebar)

### Packaging / Docs
- Version **0.4.1** (App, `ild_pdf`, ISS, Build, Docs, Smoke)
- FEATURES / INFO / CHANGELOG / Hilfe aktualisiert

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
