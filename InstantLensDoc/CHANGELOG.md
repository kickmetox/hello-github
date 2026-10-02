# Changelog — InstantLens Doc

## 0.6.6 — Tag-Rename-Undo, Split-Settings, Alle-Speichern, Wizard-Skip

Nach 0.6.5: Tag-Umbenennen ist mit Ctrl+Z ein Undo-Schritt (Filter mit); Doc-Split H/V zusätzlich in Einstellungen; Dirty-Tabs-Menü mit „Alle speichern“; Wizard mit skip-once-Checkbox. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Annotationen
- **Tag umbenennen Undo**: globale Umbenennung als eine Undo-Stufe (`AnnotationStore.rename_tag` via `atomic`); Filter wird beim Undo zurückgesetzt

### Editor / UX
- **Doc-Split Layout in Einstellungen**: Combo Horizontal/Vertikal (Setting `editor_doc_split_vertical`, sync mit Ansicht-Menü)
- Dirty-Tabs-Menü: **Alle speichern** für alle ungespeicherten Tabs
- **Erste-Schritte-Wizard**: Checkbox „Dieses Mal überspringen“; Auto-Show bis abgeschlossen (`wizard_completed` / `wizard_skip_once`)

### Packaging / Docs
- Version **0.6.6**; Smoke um 0.6.6-Pfade erweitert

---

## 0.6.5 — Tag-Rename, Vertikal-Split, Dirty-Save, Wizard-0.6

Nach 0.6.4: Tag-Cloud Rechtsklick benennt Tags global um; Doc-Split optional vertikal; Dirty-Tabs-Menü mit Speichern je Datei; Erste-Schritte-Wizard um 0.6-Highlights erweitert. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Annotationen
- **Tag-Cloud Rechtsklick → umbenennen**: Tag global in allen Annotationen des Dokuments umbenennen (`AnnotationStore.rename_tag`)

### Editor / UX
- **Vertikaler Doc-Split**: Toggle übereinander (`Ctrl+Shift+\` / Ansicht); Setting `editor_doc_split_vertical`
- Dirty-Tabs-Menü: zusätzlich **Speichern: Dateiname** je ungespeicherter Datei
- **Erste-Schritte-Wizard**: 4. Seite mit 0.6-Highlights (Tag-Cloud, Split, Dirty-Save)

### Packaging / Docs
- Version **0.6.5**; Smoke um 0.6.5-Pfade erweitert

---

## 0.6.4 — Tag-Cloud-Filter, Sync-Scroll, Dirty-Tabs, Shortcuts

Nach 0.6.3: Tag-Cloud-Klick setzt den Annotation-Filter; optionaler Sync-Scroll im Doc-Split; Klick auf „ungespeichert“ öffnet die Liste dirty Tabs; Shortcut-Übersicht um 0.6.x-Keys erweitert. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Annotationen
- **Tag-Cloud Klick setzt Filter**: exklusiv auf den gewählten Tag; erneuter Klick löscht; **Ctrl+Klick** Multi-Select (ODER)

### Editor / UX
- **Sync-Scroll** (optional): vertikales Scrollen links↔rechts im Doc-Split (`Ctrl+Alt+\` / Ansicht)
- Statusleiste **„N ungespeichert“**: Klick öffnet Menü mit dirty Tabs → Wechseln
- **Shortcut-Übersicht (F1)**: 0.6.x-Keys (Copy/Notiz/Close-Others/Doc-Split/Sync-Scroll/Tag-Cloud/Dirty-Tabs)

### Packaging / Docs
- Version **0.6.4**; Smoke um 0.6.4-Pfade erweitert

---

## 0.6.3 — Highlight+Notiz, Tag-Cloud, Doc-Split, Unsaved-Count

Nach 0.6.2: PDF-Auswahl kann Highlight und Notiz in einem Schritt anlegen; Annotation-Tag-Cloud in der Sidebar; Editor-Fenster horizontal für zwei Docs teilen; Statusleiste zählt ungespeicherte Tabs. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Annotationen
- **Auswahl → Highlight + Notiz**: Dialog-Checkbox „Zusätzlich Highlight“ (Einstellung persistent); ein Schritt für Sticky und Text-Highlight
- Annotation-**Tag-Cloud**: häufigste Tags als klickbare Chips in der Sidebar (Filter umschalten)

### Editor / UX
- **Fenster teilen (zwei Docs)**: horizontaler Split (Ctrl+\); rechtes Pane zeigt weiteres offenes Tab (read-only); „Zweites Dokument wählen…“
- Statusleiste: **ungespeicherte Tabs** zählen (`N ungespeichert`)

### Packaging / Docs
- Version **0.6.3**; Smoke um 0.6.3-Pfade erweitert

---

## 0.6.2 — Selection→Notiz, Tag-Multi-Select, Close-Others, Sync-Exit

Nach 0.6.1: PDF-Textauswahl als Sticky/Notiz mit vorausgefülltem Text; Annotation-Tag-Filter Multi-Select (ODER); andere Tabs schließen; Sync-Skript `-SkipStart` und klare Exit-Codes. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Annotationen
- **Auswahl → Notiz**: Textauswahl → Sticky mit vorausgefülltem Inhalt (`Ctrl+Alt+N` / Notiz-Werkzeug); Dialog editierbar
- Annotation-Tag-Filter: **Multi-Select** (mehrere Tags, ODER-Match); leere Auswahl = alle

### Editor / Session
- **Andere Tabs schließen**: Datei → Ctrl+Shift+W — Sidebar-Dokumente außer aktuellem entfernen

### Packaging / Docs
- Sync: `-SkipStart` (= `-NoStart`); Exit-Codes **0** OK / **1** allgemein / **2** Git-Fehler dokumentiert
- Version **0.6.2**; Smoke um 0.6.2-Pfade erweitert

---

## 0.6.1 — Selection-Copy, Tag-Autocomplete, Session-Order, Installer-Docs

Nach 0.6.0: PDF-Text aus Auswahl in die Zwischenablage; Annotation-Suche mit Tag-Autocomplete; Session-Tab-Reihenfolge per Drag speichern; Installer-Desktop-Shortcut dokumentiert/geprüft. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Annotationen
- **PDF-Text kopieren**: Auswahl-Werkzeug → Text aufziehen → **Ctrl+C** / Bearbeiten→Kopieren (ohne Highlight-Annotation)
- API `selection_to_plain_text` (ergänzt Selection→Highlight)
- Annotation-Suche: **Tag-Autocomplete** (Completer aus vorhandenen Tags)

### Editor / Session
- Dokument-/Session-Tabs: **Drag-Reihenfolge** in der Sidebar; `session.json` speichert `order`

### Packaging / Docs
- Inno: Task `desktopicon` — Checkbox dokumentiert (`checkedonce`, Standard an); Hinweistext erweitert
- Version **0.6.1**; Smoke um 0.6.1-Pfade erweitert

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
