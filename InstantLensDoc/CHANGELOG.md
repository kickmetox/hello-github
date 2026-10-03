# Changelog — InstantLens Doc

## 0.7.9 — Such-Export, Ann.-Filter-Presets, Bracket-Auto-Close

Nach 0.7.8: Suchergebnisse exportieren, Annotations-Filter merken und Editor-Klammern verfeinern. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **Suchergebnis-Export**: Trefferliste als **CSV** / **JSON** (`ildsearch-v1`) — Sidebar-Buttons + Menü Bearbeiten
- Ann.-**Filter-Presets**: aktuelle Filter (Typ/Farbe/Tags/Seite/Suche/Regex) **speichern / laden / löschen**

### Editor / Settings
- **Bracket-Auto-Close** Toggle in Einstellungen (Standard an): `()[]{}` und Anführungszeichen beim Tippen

### Packaging / Docs
- Version **0.7.9** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Such-Export CSV/JSON, Ann.-Filter-Presets, Bracket-Auto-Close (CLI + Qt)

---

## 0.7.8 — Dry-Run-TXT, Ann.-Tooltip, Blink-Hinweis, Merge-Diff-Länge

Nach 0.7.7: Zip-Dry-Run, Ann.-Liste, Debounce-Hinweis und Merge-Diff verfeinern. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- Ann.-**Liste**: bei Ellipsis-Kürzung **Tooltip mit vollem Text**
- Ann.-**Merge-Diff**: **max. Zeichenlänge** je Seite in Einstellungen (12–64)

### Editor / Settings
- Vorlagen-Zip-Import Dry-Run: **Konfliktliste als TXT** exportieren
- Status-Blink **aus**: trotzdem **einmaliger Status-Hinweis** ohne Blink

### Packaging / Docs
- Version **0.7.8** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Dry-Run-TXT, Ann.-Tooltip, Blink-Hinweis, Merge-Diff-Länge (CLI + Qt)

---

## 0.7.7 — Status-Blink Settings, Merge-Tags/Farbe, Zip-Dry-Run, Ann.-Ellipsis

Nach 0.7.6: Dirty-UX, Merge-Diff, Zip-Import und Ann.-Liste verfeinern. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- Ann.-**Merge-Vorschau**: Diff-Kurztext zeigt zusätzlich **Tags** und **Farbe**
- Ann.-**Liste**: gekürzter Text nutzt **Snippet-Ellipsis-Style** («…» / …)

### Editor / Settings
- Pending Sidecar-Debounce: **Status-Blink** Dauer/Intensität in Einstellungen (**kurz** / **aus**)
- Vorlagen-Zip-Import: **Dry-Run-Liste** was überschrieben würde (im Konflikt-Dialog)

### Packaging / Docs
- Version **0.7.7** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Status-Blink Settings, Merge-Tags/Farbe, Zip-Dry-Run, Ann.-Ellipsis (CLI + Qt)

---

## 0.7.6 — Snippet-Ellipsis, Zip-Konflikt, Merge-Diff, Debounce-Blink

Nach 0.7.5: Suche, Vorlagen-Import, Merge-Vorschau und Dirty-UX verfeinern. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **Snippet-Ellipsis-Style** in Einstellungen: Match-Markierung `«…»` (Guillemets) oder `…` (Ellipsis)
- Ann.-**Merge-Vorschau**: Diff-Kurztext der beiden Annotationen (Ähnlichkeit + Textausschnitte)

### Editor / Settings
- Vorlagen-Zip-Import: **Konflikt-Dialog** (Überschreiben / Überspringen / Abbrechen)
- Pending Sidecar-Debounce: kurzer **Statusleisten-Blink** + Message „Speichern ausstehend…“

### Packaging / Docs
- Version **0.7.6** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Ellipsis-Style, Zip-Konflikt, Merge-Diff, Debounce-Blink (CLI + Qt)

---

## 0.7.5 — Snippet-Länge, Alle mergen/behalten, Vorlagen-Zip, Debounce-Tooltip

Nach 0.7.4: Suche, Merge-Vorschau, Vorlagen und Dirty-UX verfeinern. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **Treffer-Snippet-Länge** in Einstellungen (20–80 Zeichen Kontext um Match, Standard 40)
- Ann.-**Merge-Vorschau**: Buttons **Alle mergen** / **Alle behalten**

### Editor / Settings
- Nutzer-Vorlagen: **Export/Import Ordner als Zip** (`templates.json` + `*.ildtpl.md`)
- Pending Sidecar-Debounce: Tab-Tooltip **„Speichern ausstehend…“**

### Packaging / Docs
- Version **0.7.5** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Snippet-Länge-Settings, Alle mergen/behalten, Vorlagen-Zip, Debounce-Tooltip (CLI + Qt)

---

## 0.7.4 — Kontext-Snippets, Merge je Paar, Vorlagen-Drag, Dirty-Debounce

Nach 0.7.3: Trefferliste, Merge und Vorlagen/Dirty verfeinern. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **Trefferliste**: Kontext-Snippet mit Zeichen um den Match (`«…»`)
- Ann.-**Merge-Vorschau**: je Paar/Gruppe einzeln **mergen** oder **behalten**

### Editor / Settings
- Nutzer-Vorlagen: **Drag-Reihenfolge** speichern (Dialog + Menü)
- Dirty-Indikator am Tab/`*` auch bei **pending Sidecar-Debounce**

### Packaging / Docs
- Version **0.7.4** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Kontext-Snippet, Merge je Paar, Vorlagen-Reorder, Dirty-Debounce (CLI + Qt)

---

## 0.7.3 — Trefferliste, Vorlagen-Ordner, Merge-Vorschau, Ctrl+S-Flush

Nach 0.7.2: Schnellsuche und Merge/Save-UX verfeinern. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **Schnellsuche**: klickbare **Trefferliste** direkt unter der Suche (Index sync mit Weiter/Zurück)
- Ann.-**Merge-Vorschau**: Dialog mit Gruppenübersicht vor Apply (älteste behalten)

### Editor / Settings
- **Vorlagen-Ordner öffnen**: Spiegel unter `config/templates` im Explorer (Datei → Neu)
- Sidecar-Debounce: **Ctrl+S** flusht ausstehendes Speichern sofort

### Packaging / Docs
- Version **0.7.3** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Trefferliste-Klick, Vorlagen-Ordner, Merge-Vorschau-Dialog, Ctrl+S-Flush (CLI + Qt)

---

## 0.7.2 — Schnellsuche-Nav, Merge-Undo, Vorlagen-UI, Debounce-Settings

Nach 0.7.1: Navigation und Verwaltung verfeinern. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **Schnellsuche**: Trefferanzahl in der Sidebar; **Weiter/Zurück** navigiert über Doc-Treffer (Alle Docs / Alle PDFs) sowie Seite/Editor
- Ann.-**Merge-Undo**: Duplikate-Zusammenführen als benannter Undo-Stack-Eintrag („Duplikate zusammenführen“), Status/Hint

### Editor / Settings
- Nutzer-Vorlagen: **Umbenennen** / **Löschen** im Menü Datei → Neu → Meine Vorlagen
- Sidecar-Debounce-**Intervall** in Einstellungen (200–1000 ms, Default 400)

### Packaging / Docs
- Version **0.7.2** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Treffer-Nav, Merge-Undo-Label, Vorlagen rename/delete, Debounce-Settings (CLI + Qt)

---

## 0.7.1 — PDF-Schnellsuche, Ann.-Duplikate, Vorlagen, Sidecar-Debounce

Nach Meilenstein 0.7.0: gezielte UX-/Performance-Härten. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **PDF-Schnellsuche** („Alle PDFs“): Volltext nur über geöffnete/gelistete PDFs; eine PDF-Öffnung pro Datei; Snippets um Treffer; Sprung + Highlight
- Volltext „Alle Docs“: casefold, bessere Snippets, bis 100 Treffer in der Liste
- Annotation-**Duplikate** (gleiche Seite+BBox±2px, gleicher Typ) finden und optional zusammenführen (Text/Tags mergen, älteste behalten)

### Editor / Performance
- **Als Vorlage speichern** aus aktuellem Dokument; Menü Datei → Neu → Meine Vorlagen
- Sidecar-Save **Debounce** (400 ms); Force-Save / Flush bei PDF-Wechsel, Close, Autosave

### Packaging / Docs
- Version **0.7.1** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: PDF-Suche, Duplikat-Merge, Nutzer-Vorlagen, Sidecar-Debounce (CLI + Qt wo sinnvoll)

---

## 0.7.0 — Release-Konsolidierung (0.6.0 → 0.7.0)

Meilenstein: alle 0.6.x-Inkremente gebündelt, Version einheitlich **0.7.0**, Smoke um ausgewählte 0.6.x-Pfade erweitert, kleine Review-Fixes. Stubs KI/Cloud/Stylus/3D bleiben Stubs (keine Fake-Features).

### PDF / Annotationen
- Selection→**Copy**/Notiz/Highlight+Notiz; Tag-**Autocomplete**/Multi-Select/**Cloud**/Rename (+ Undo, Confirm, Schwelle)
- Annotation-**Tag-Cloud** (Filter-Klick, Rechtsklick umbenennen); Sidecar-Tags unverändert

### Editor / Session / UX
- Session-**Tab-Order** Drag; **Andere Tabs schließen**; **Doc-Split** H/V (PDF+Editor, Panel-Session)
- **Sync-Scroll** optional + je Session; Dirty-Tabs Liste / Speichern / Alle speichern (Fortschritt, Abbrechen, **Fehlerliste**)
- Erste-Schritte-**Wizard** (0.6-Highlights, skip-once, dauerhaft, Reset); F1 Shortcuts + 0.6.8-Hinweise
- Sync: `-SkipStart`, Exit-Codes 0/1/2; Installer Desktopicon-Docs

### Packaging / Docs
- Inno Setup / Build / INFO / FEATURES / README auf **0.7.0**
- Sync: `scripts/sync-ild.ps1` (Repo) bzw. Store `docs/sync-ild.ps1`
- Smoke: open / annotate / export / license + ausgewählte 0.6.x-Pfade (CLI + offscreen Qt)

### Review-Fixes (0.7.0)
- Versionsstrings App / `ild_pdf` / ISS / Smoke / Docs vereinheitlicht
- CHANGELOG 0.6.1–0.6.9 zu Kurz-Tabelle verdichtet (wie zuvor 0.5.x)
- `ild_pdf/README.md` und `installer/build-installer.ps1` Versionshinweise auf aktuelle Release gebracht

---

## 0.6.0 — Release-Konsolidierung (0.5.0 → 0.6.0)

Meilenstein: alle 0.5.x-Inkremente gebündelt, Version einheitlich **0.6.0**, Smoke um ausgewählte 0.5.x-Pfade erweitert, kleine Review-Fixes. Stubs KI/Cloud/Stylus/3D bleiben Stubs (keine Fake-Features).

### PDF / Annotationen / OCR
- **Batch-OCR** gesamtes PDF; Annotation-**Tags**; **PDF bereinigen**; Selection→Highlight; Ann.-**Regex**
- Kommentar-**Bericht**; Farbe Palette-Zyklus; Seite löschen **Undo**; Annotation-**Gruppen**
- Seiten-**Historie**; Ann.-Export Tags/Gruppen; **Seiten-Favoriten** (Sidebar, Drag, JSON `ildfav-v1`)
- Ann.-Batch-**Farbe**/Opacity; Opacity Force-Save + **Toolbar-Slider**

### Editor / UX
- Projekt-**Workspace**; Dateien vergleichen; **Export-Profil**; Editor-**Minimap**; Soft-Hyphen/NBSP
- Startup-Deps-Check; Encoding **Auto**; Quiet Splash; Wortlisten-**Rechtschreibung**; Privacy-About
- Zeilenfavoriten (+ **Labels**); Crash-Report **ZIP** (+ optional Screenshot); **Erste-Schritte**-Wizard

### Packaging / Docs
- Inno Setup / Build / INFO / FEATURES / README auf **0.6.0**
- Sync: `scripts/sync-ild.ps1` (Repo) bzw. Store `docs/sync-ild.ps1`
- Smoke: open / annotate / export / license + ausgewählte 0.5.x-Pfade (CLI + offscreen Qt)

### Review-Fixes (0.6.0)
- Versionsstrings App / `ild_pdf` / ISS / Smoke / Docs vereinheitlicht
- CHANGELOG 0.5.1–0.5.9 zu Kurz-Tabelle verdichtet (wie zuvor 0.4.x)
- `ild_pdf/README.md` und `installer/build-installer.ps1` Versionshinweise auf aktuelle Release gebracht

### 0.6.x-Inkremente (Kurz)

| Ver. | Kern |
|------|------|
| **0.6.1** | Selection-Copy, Tag-Autocomplete, Session-Order, Installer-Docs |
| **0.6.2** | Selection→Notiz, Tag-Multi-Select, Close-Others, Sync-Exit |
| **0.6.3** | Highlight+Notiz, Tag-Cloud, Doc-Split, Unsaved-Count |
| **0.6.4** | Tag-Cloud-Filter, Sync-Scroll, Dirty-Tabs, Shortcuts |
| **0.6.5** | Tag-Rename, Vertikal-Split, Dirty-Save, Wizard-0.6 |
| **0.6.6** | Tag-Rename-Undo, Split-Settings, Alle-Speichern, Wizard-Skip |
| **0.6.7** | Tag-Undo-Label, Split-PDF+Editor, Save-Progress, Wizard-Dauerhaft |
| **0.6.8** | Split-Panel-Session, Save-Abbrechen, Wizard-Reset, Tag-Confirm |
| **0.6.9** | Sync-Scroll-Session, Tag-Schwelle, Save-Fehlerliste, F1-0.6.8 |

→ zusammengeführt in **0.7.0**.

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

### 0.5.x-Inkremente (Kurz)

| Ver. | Kern |
|------|------|
| **0.5.1** | Batch-OCR, Ann.-Tags, Projekt-Workspace, PDF bereinigen |
| **0.5.2** | Selection→Highlight, Ann.-Regex, Text-Diff, Export-Profil |
| **0.5.3** | Kommentar-Bericht, Farbe-Zyklus, Minimap, About-Keygen |
| **0.5.4** | Seiten-Löschen-Undo, Ann.-Gruppen, Soft-Hyphen/NBSP, Startup-Deps |
| **0.5.5** | Seiten-Historie-UI, Ann.-Export Tags/Gruppen, Encoding-Auto, Quiet Splash |
| **0.5.6** | Seiten-Favoriten, Ann.-Batch-Farbe, Wortlisten-Rechtschreibung, Privacy-About |
| **0.5.7** | Favoriten-Sidebar, Ann.-Opacity-Batch, Zeilenfavoriten, Crash-ZIP |
| **0.5.8** | Favoriten-Drag, Opacity-Force-Save, Zeilenfavoriten-Liste, Crash-Screenshot |
| **0.5.9** | Favoriten JSON, Opacity-Slider, Zeilenfavoriten-Labels, Erste-Schritte-Wizard |

→ zusammengeführt in **0.6.0**.

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
