# InstantLens Doc

Moderne Textverarbeitung mit PDF-Annotator, OCR-Bridge und Formulargenerator.

**Version:** 2.6.29  
**Hersteller:** Andreas Meyer · ame@sellerbach.de

## Quickstart (Windows)

Copy-ready Sync (eine Zeile → `D:\AI_Temp\InstantLensDoc`, pip, Start):

`powershell -ExecutionPolicy Bypass -File "D:\AI_Temp\sync-ild.ps1"`

Ohne Start: `…\sync-ild.ps1 -NoStart` (Alias `-SkipStart`; Exit **0**/OK, **1**/Fehler, **2**/Git).

Oder lokal im App-Ordner:

```bat
cd /d D:\AI_Temp\InstantLensDoc && pip install -r requirements.txt && run.bat
```

Nur starten (nach Sync/pip): `run.bat`  
(`run.bat --help` zeigt deutsche Hilfe; optional Env-Override **`set ILD_PYTHON=C:\Pfad\zu\python.exe`** — bei ungültigem/leerem Pfad Fallback **`py -3` → `python` → `python3`**; gewählte Binary als **`gefunden: …`** inkl. **`--version`**; fehlende Deps optional per J/N oder non-interactive mit **`run.bat --yes`** / **`-y`**. Exit **0**/OK · **1**/Fehler.)

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

64-Bit-Python erforderlich. Runnable-Pack ohne EXE: `.\scripts\pack-windows-runnable.ps1`.  
Installer-Einzeiler: `powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1` → `dist\InstantLensDoc-Setup-2.6.29.exe`  
(oder `.\installer\build-installer.ps1`, optional `-NoKeygen`)  
Desktop-Verknüpfung: optionale Checkbox (`desktopicon`, Standard an).  
User-Shortcuts: `.\scripts\install-ild.ps1` (inkl. Keygen) · Deinstallieren: `-Uninstall [-Quiet]` (Exit **0**/OK · **1**/Fehler; Quiet: Kurz-Summary, Exit 0 auch ohne Shortcuts).  
Sync mit optionalem Installer: `…\sync-ild.ps1 -BuildInstaller -SkipStart`.

Keygen: `run-keygen.bat` · `python -m keygen kunde@example.com` · siehe `keygen/README.md`.  
Scripting: `python -m ild --help` · `.\scripts\ild.ps1` · `run-ild.bat`.

Nightly-Smoke: `python scripts\smoke_ild.py` · optional `--qt` · `--json` (Summary: `ok`, `checks[]`, `duration_ms`, `version`; Fail: `checks[].error` max 200…, Exit=ok). Siehe **CONTRIBUTING.md**; Workflow-Stub `.github/workflows/smoke-ild.yml` (manual only).

## Neu in 2.6.29

- Silbentrennung: Menü + Command-Palette für alle 9 UI-Sprachen (Engine aus 2.6.28)
- FEATURES-Bereinigung: Signieren/eIDAS + Mehrsprach-UI-Zeile

## Neu in 2.6.28

- Audit-Closure Word-Suite/DTP/Mausrad (LOF/Index, F12, pptx, Abschnitte, Grammatik, Hyphen-Engine×9, Spot/Web-PDF, eIDAS-Trust, Realtime, Handschrift)
- Default-PDF/Frame-Mausrad; 2.6.27 Trackpad/`apply_wheel_scroll` erhalten

## Neu in 2.6.26

- Polish / Konsolidierung 2.6.20–2.6.25 (keine großen neuen Produktflächen)
- Windows-Installer gehärtet: VERSION.txt → ISCC, Preflight, CustomMessages DE/EN
- Einzeiler Setup.exe: `powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1`

## Neu in 2.6.25

- Stylus / Palm Rejection; Dokumentstruktur-Pane; Script-/Plugin-Hooks
- Telemetrie Opt-in lokal; 3D Limited Viewer; Inno-Installer-Projekt
- `ild.hooks_*` / `document_outline_api` / `stylus_status` / `telemetry_*` / `extrude3d_preview`

## Neu in 2.6.23

- Gemeinsames Review / Cloud-Ordner: Notizen, Markierungen, Stempel, Kommentare austauschbar
- Freigabeordner-Sync (`session.ildshare.json`) + optionaler HTTP-Endpoint; Polling
- UI Starten/Beitreten/Sync; `ild.shared_review_*` / CLI `share-*` / PS `Start-/Join-/Sync-IldSharedReview`
- Offline bleibt nutzbar; freier KI-Chat-Stub unverändert

## Neu in 2.6.22

- Stapelverarbeitung: viele PDFs konvertieren / Wasserzeichen / komprimieren / verschlüsseln
- Digitale Signaturen (eIDAS-Pfad SES/AES/QES); PKCS#12; `ild.sign_pdf_api` / `run_batch_job`
- Seriendruck-Polish: Vorschau, fehlende Felder, HTML/DOCX

## Neu in 2.6.21

- Review / Track Changes (lokal, je Autor; Accept/Reject)
- Kommentare an Textstellen ohne Body-Änderung
- Versionsverlauf speichern/wiederherstellen (`*.ildversions/`)
- Seriendruck-Basis CSV/Excel → Briefe; `ild.review_*` / `comment_*` / `version_*` / `mail_merge_run`

## Neu in 2.6.20

- Rechtschreibung mit Vorschlägen + leichte Grammatik-Hints (UI-Sprache)
- Autokorrektur & Textbausteine (9 Slots, Kürzel beim Tippen)
- Ribbon-Polish (Bearbeiten/Fenster), Tabs Drag, separates Fenster
- Undo/Redo praktisch unbegrenzt; `ild.spellcheck` / `autocorrect` / `snippets`

## Neu in 2.6.19

Minor nach **2.6.18**: **Document Comparison** (Side-by-Side, Drag-and-Drop, Sync-Scroll, Diff-Highlight) · **Buch-Layout** + **Seite-für-Seite-Scroll** · partielle **Dokument-Tabs** + **Ribbon-Chrome**. Scripting `ild.compare_pdfs` / CLI `compare` / PS `Invoke-IldCompare`. Keine Cloud-Kollab. Stubs unverändert.

## Neu in 2.6.18

Minor nach **2.6.17**: **Druck/DTP** — RGB/CMYK-Farbmanagement + Paletten, Bleed/Anschnitt, Dokument-Ebenen (Hintergrund/Bilder/Text), Preflight (Schriften/Auflösung), PDF/X bzw. print-ready Export. Scripting `palettes`/`apply-bleed`/`preflight`/`export-pdfx`/`layers`. Kein volles PDF-Compare, kein Ribbon-Overhaul. Stubs unverändert.

## Neu in 2.6.17

Minor nach **2.6.16**: **Volles InstantLens Doc i18n** — Einstellungen: DE/EN/FR/RU/ES/ZH/PT/AR/IT für gesamte UI (Viewer, OCR, Scan, Annotationen, Formulare, Export, Assistenten, Hilfe, Info); Persistenz; Arabisch RTL wo praktikabel; Locale-Katalog + Hilfe-HTML; externe Docs `docs/i18n/`. **Handschriftenerkennung** Basis-Hook (Tesseract PSM). Scripting `ui-langs`/`set-ui-lang`/`ocr-handwriting`. Freier KI-Chat-Stub unverändert. Kein CMYK/Bleed/Preflight/PDF/X damals, kein PDF-Compare.

## Neu in 2.6.16

Minor nach **2.6.15**: **Isolierte KI-Dokument-Wizards** — Formular/Anschreiben/Kaufvertrag/Rechnung (generisch oder Firma/USt-Id); UI Ctrl+Alt+Shift+Q; lokal templatebasiert, optionaler LLM-Hook nur hinter dem Wizard; **kein** freier Chat. Scripting `ki-wizard`/`generate_ki_document`. Kein CMYK/Bleed/Preflight/PDF/X, kein i18n/PDF-Compare. Stubs (freier KI-Assistent) unverändert.

## Neu in 2.6.15

Minor nach **2.6.14**: **OCR → Word-Suite** — Layout-OCR/`*.ildocr.*` als editierbares Dokument (Blöcke/Lesereihenfolge); UI Ctrl+Alt+Shift+W; Scripting `ocr-word-suite`/`import-ildocr`. Kein CMYK/Bleed/Preflight/PDF/X, kein i18n/KI-Wizards/PDF-Compare. Stubs unverändert.

## Neu in 2.6.14

Minor nach **2.6.13**: **Dokument-Tabellen** (erstellen/formatieren/sortieren), **CSV/Excel-Import** in Tabellen, **Speichern/Export/Import** `.docx`/`.xlsx`/`.pdf`/`.txt`/`.rtf` (+ HTML/JPG). Scripting `table-create`/`table-import-csv`/`save`/`import-doc`. Kein CMYK/Bleed/Preflight/PDF/X, kein i18n/KI-Wizards/PDF-Compare. Stubs unverändert.

## Neu in 2.6.13

Minor nach **2.6.12**: **Erweiterte Typografie** (Tracking/Kerning/Leading, Absatz-/Zeichenstile), **Textumfluss** um Bild-/Formrahmen, **Silbentrennung** DE/EN (+ Hook), **Drop Caps**. Scripting `typography`/`hyphenate`/`drop-cap`/`layout-text-wrap`. Kein CMYK/Bleed/Preflight/PDF/X, kein i18n/KI-Wizards/PDF-Compare. Stubs unverändert.

## Neu in 2.6.12

Minor nach **2.6.11**: **Frames/Boxes** (Move/Resize), **Textrahmen-Verkettung** (Spalte/Seite), **Musterseiten**, **Satzspiegel**. Scripting `satzspiegel`/`apply-master`/`layout-flow`/`layout-move`/`layout-resize`. Kein CMYK/Bleed/Preflight/PDF/X, kein i18n/KI-Wizards/PDF-Compare. Stubs unverändert.

## Neu in 2.6.11

Minor nach **2.6.10**: **Lineal**, **Raster/Guides**, **Kopf-/Fußzeilen** (Titel/Autor/Seitenzahl), **Buch-/DIN-/US-Seitenformate**, **Absatzformatierung** (Ausrichtung/Abstand) an Styles. Scripting `page-formats`/`header-footer`/`paragraph-format`. Stubs unverändert.

## Neu in 2.6.10

Minor nach **2.6.9**: **Auto-Format**, **automatisches Inhaltsverzeichnis**, **Word-/InDesign-Shortcuts** (Ctrl+B/I/U, Ctrl+H Ersetzen, …), **Systemschriften**, Suchen/Ersetzen. Scripting `auto-format`/`toc`/`fonts`/`find-replace`. Kein volles DTP/i18n/KI-Wizards. Stubs unverändert.

## Neu in 2.6.9

Minor nach **2.6.8**: **Annotationen ausbauen** — Pinselstärke, Color-Picker Strich/Füllung, Kreis/Ellipse/Dreieck/Rundrect (gefüllt/Outline), Stempel Paid/Bezahlt/Rechnung/Datum + Custom, Absatz-Highlight. Scripting `ild.add_shape`/`add_stamp`/`highlight_paragraphs`. Stubs unverändert.

## Neu in 2.6.8

Minor nach **2.6.7**: **Windows-Build + Keygen-Paket + Scripting** — `build-windows.ps1` (x64), `pack-windows-runnable`, Keygen-Shortcut, HMAC-Keys `ILD1.…`, headless `python -m ild` / `scripts/ild.ps1`. Keine Annotationen/Word-Suite. Stubs unverändert.

## Neu in 2.6.7

Minor-Feature nach **2.6.6** (Zusatzanforderungen #8): **Verschlüsselung & Rechte** — AES-256-Passwortschutz, granulare Rechte (Druck/Kopieren/Ändern/…), Dialog setzen/entfernen/Rechte, Öffnen mit Passwort-Prompt; Ctrl+Alt+Shift+P. Kein Batch/Office/E-Sign/KI/Cloud. Stubs unverändert.

## Neu in 2.6.6

Minor-Feature nach **2.6.5** (Zusatzanforderungen #7): **Interaktive Formularerstellung** — AcroForm Text/Checkbox/Dropdown erkennen und anlegen; UI ausfüllen/bearbeiten (Dialog + Toolbar „Formular“ + Rechteck ziehen); Ctrl+Alt+Shift+K. Keine E-Sign/Office/KI/Cloud. Stubs unverändert.

## Neu in 2.6.5

Minor-Feature nach **2.6.4**: **Objektmanipulation** — Bilder, Vektorgrafiken und Tabellen verschieben, skalieren, spiegeln oder ersetzen (pypdfium2 PageObjects + pikepdf); Toolbar „Objekt“, Handles, Dialog; Ctrl+Alt+Shift+O. Keine Formulare/Verschlüsselung/Office/KI/Cloud. Stubs unverändert.

## Neu in 2.6.4

Minor-Feature nach **2.6.3**: **Inline-Textbearbeitung** + **Schriftart-/Formatabgleich** — Text ändern/löschen/einfügen mit Reflow; Font/Größe/Farbe aus Kontext (Standard-14); Toolbar/Menü/Palette/Doppelklick. Keine Objektmanipulation/Formulare/Office/KI/Cloud. Stubs unverändert.

## Neu in 2.6.3

Minor-Feature nach **2.6.2**: **Erweiterte OCR mit Layout-Erhalt** — Tesseract-Blöcke + Lesereihenfolge; Sidecars `*.ildocr.txt` / optional hOCR / TSV; OCR-Dialog Default + Scan-/Import-Flow. Kein Inline-Edit/Office/KI/Cloud. Stubs unverändert.

## Neu in 2.6.2

Minor-Feature nach **2.6.1**: **Scannen / Import** (WIA/SANE oder Bilder) + **Tesseract-OCR** → durchsuchbarer Text; **Drucker-/Scannererkennung** lokal + Netzwerk mit Aktualisieren. UI **Scannen / Import…** / **Drucker & Scanner…**. Windows: `winget install UB-Mannheim.TesseractOCR`. Stubs unverändert.

## Neu in 2.6.1

Minor-Feature nach **2.6.0**: **Seitenmanagement** (Drag-Reorder, einfügen/drehen/löschen, Seiten aus PDF) + Sidebar **Schnellvorschau** / klickbares **Inhaltsverzeichnis**. Stubs unverändert.

## Neu in 2.6.0

Minor-Feature nach **2.5.20**: **Echtes Schwärzen** (unwiderruflich, Content-Stream/Textschicht weg) + optional **Metadaten-Bereinigung**; UI **Echt schwärzen…** / **Auswahl → Schwärzung**; Overlay-Bake bleibt. Stubs unverändert.

## Neu in 2.5.20

Post-Release-Polish nach **2.5.19**: **OCR-Region** Open Fail-Path A11y; **Farben-Themes** Ctrl+Shift+C alle Hex · Hex-All Fail-A11y; **ildtags** Tag−/Clear Fail-A11y · Pfad-Copy Fail-A11y; **Export-Presets** Summary-Copy Fail-A11y. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.19

Post-Release-Polish nach **2.5.18**: **OCR-Region** Text-Copy Clip-Fail A11y; **Farben-Themes** Shift+←/→ ±2 · Hex-Copy Fail-A11y; **ildtags** Tags-Copy/Paste Fail-A11y; **Export-Presets** Pfad-Copy / Apply-fehlt Fail-A11y. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.18

Post-Release-Polish nach **2.5.17**: **OCR-Region** Pfad-Copy Fail-Path A11y; **Farben-Themes** PageUp/PageDown · Ctrl+C Hex; **ildtags** Öffnen⏎ · Fail-A11y; **Export-Presets** JSON Imp/Exp A11y · Ordner-fehlt. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.17

Post-Release-Polish nach **2.5.16**: **OCR-Region** Text-Copy Fail-Path A11y; **Farben-Themes** Swatch-Ziffern 1–6; **ildtags** F5 → Datei · Entf-Menü; **Export-Presets** CRUD A11y. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.16

Post-Release-Polish nach **2.5.15**: **OCR-Region** Fail-Path A11y; **Farben-Themes** Swatch Home/End · RMB Mid/Dbl-Hints; **ildtags** Tag± A11y; **Export-Presets** Reorder A11y · Anwenden⏎. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.15

Post-Release-Polish nach **2.5.14**: **OCR-Region** F5 → Datei; **Farben-Themes** Swatch-Tastatur Space/H/P/N/C · ←/→ · A11y; **ildtags** F4 → Ordner; **Export-Presets** F4 → Zielordner. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.14

Post-Release-Polish nach **2.5.13**: **OCR-Region** F4 → Ordner; **Farben-Themes** Shift+Doppelklick → Stift · Ctrl+Doppelklick → Notiz; **ildtags** Ctrl+Shift+C Pfad; **Export-Presets** Ctrl+Home/End Anfang/Ende. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.13

Post-Release-Polish nach **2.5.12**: **OCR-Region** Ctrl+C Text · Ctrl+Shift+C Pfad; **Farben-Themes** Doppelklick → Highlight; **ildtags** F3 Tag entfernen; **Export-Presets** Ctrl+↑/↓ Reihenfolge. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.12

Post-Release-Polish nach **2.5.11**: **OCR-Region** Enter → Ergebnis-Tab; **Farben-Themes** Shift+Mittelklick → Stift · Ctrl+Mittelklick → Notiz; **ildtags** F2 Tag hinzufügen; **Export-Presets** Ctrl+Enter Anwenden ohne Schließen. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.11

Post-Release-Polish nach **2.5.10**: **OCR-Region** Esc / Menü → Status schließen; **Farben-Themes** Swatch-Mittelklick → Highlight; **ildtags** Shift+Entf Alle Tags; **Export-Presets** Ctrl+D Duplizieren. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.10

Post-Release-Polish nach **2.5.9**: **OCR-Region** Status-Rechtsklick → Kontextmenü (Tab/Ordner/Pfad/Text/Datei); **Farben-Themes** Swatch-RMB → Highlight/Stift/Notiz; **ildtags** Ctrl+X · Alle Tags entfernen; **Export-Presets** F2 Umbenennen. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.9

Post-Release-Polish nach **2.5.8**: **OCR-Region** Alt+Klick → Datei öffnen · Tooltip Textvorschau; **Farben-Themes** Swatch-Klick Hex; **ildtags** Ctrl+C/V Tags; **Export-Presets** Pfad kopieren (Ctrl+Shift+C). Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.8

Post-Release-Polish nach **2.5.7**: **OCR-Region** Shift+Klick → Text kopieren; **Farben-Themes** Hex kopieren; **ildtags** Tags einfügen; **Export-Presets** Summary kopieren (RMB/Ctrl+C). Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.7

Post-Release-Polish nach **2.5.6**: **OCR-Region** Mittelklick/Ctrl+Klick → Pfad kopieren; **Farben-Themes** Hex-Tooltip · Custom N/20; **ildtags** Tags kopieren; **Export-Presets** RMB Zielordner · Entf. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.6

Post-Release-Polish nach **2.5.5**: **OCR-Region** Status-Rechtsklick → Ordner; **Farben-Themes** Custom duplizieren; **ildtags** Quick-Tag Sort A–Z/Häufigkeit; **Export-Presets** Listen-Tooltip · Apply A11y. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.5

Post-Release-Polish nach **2.5.4**: **OCR-Region** Status-Klick → Ergebnis-Tab; **Farben-Themes** Custom umbenennen; **ildtags** Quick-Tag A–Z mit Doc-Anzahl; **Export-Presets** ★ aktiv · Duplizieren. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.4

Post-Release-Polish nach **2.5.3**: **OCR-Region** Wörter/Zeichen Status · A11y Announcement; **Farben-Themes** Custom löschen · ★ Default; **ildtags** Tag-Vorschläge · Quick-Tag-Filter; **Export-Presets** Umbenennen · Doppelklick Anwenden. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.3

Post-Release-Polish nach **2.5.2**: **OCR-Region** Tab-Titel Ellipsis + Tooltip voll · Fehlerabschnitt wie Batch-OCR; **Farben-Theme Merge** skip/rename (`_2`) · Import-Log; **ildtags** Esc → Fokus Liste · Trefferanzahl A11y; **Export-Presets** Live-Pfad-Vorschau · ungültige JSON-Einträge überspringen+zählen. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.2

Post-Release-Polish nach **2.5.1**: **OCR-Region** Fortschritt · Ergebnis-Tab Titel Seite/Region · Fehler anhängen Toggle; **Farben-Theme JSON** `ildcolors-theme-v1` · ungültig klar DE · Merge/Ersetzen; **ildtags-Filter** Trefferanzahl · Esc leert · fehlende getaggte Recent grau; **Export-Presets** Duplikat-Namen ablehnen · Export/Import JSON (`ildexportpresets-v1`). Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.1

Post-Release-Polish nach **2.5.0**: **OCR-Region** Defaults DPI/Sprache · Abbruch · leeres Ergebnis Hinweis; **Farben-Themes** Swatches · Als Default · Import/Export JSON; **ildtags** Tag+/− Recent · Filter Clear · Persistenz; **Export-Presets** max. 10 · Anwenden/Löschen · Live-Zusammenfassung. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.5.0

Minor-Bump nach **2.4.5**: **PDF-OCR-Region** Rechteck → Region-OCR → Text-Tab; **Annotation-Farben-Themes** Markieren/Corporate; **Dokument-Tags** `ildtags-v1` in Welcome/Recent filterbar; **Export-Preset „Zuletzt“** (DPI/Format/Pfad). Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.4.5

Post-Release-Polish nach **2.4.4**: **Thumb Auto-Prune** Toast Dauer OCR-Settings · Klick kopiert Status erneut; **Quick-Apply Esc** „Apply abgebrochen“ + Vorlagenname · A11y; **Sync-Scroll** AccessibleName live an/aus; **F1 Reset** gemeinsamer Helper. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.4.4

Post-Release-Polish nach **2.4.3**: **Thumb Auto-Prune** Status kopierbar · Toast optional Settings; **Quick-Apply Esc** „Apply abgebrochen“ · Fokus Toolbar; **Sync-Scroll** Announcement bei Toggle · AccessibleName Status-Widget; **F1 Reset** Bestätigung nur bei Abweichung · Fokus+Selektion. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.4.3

Post-Release-Polish nach **2.4.2**: **Thumb Auto-Prune** Status „N Dateien / X MB entfernt“ · Settings Intervall oder on-write; **Templates** Quick-Apply Rechtsklick · Esc Apply-Modus; **Sync-Scroll** Tooltip Zustand an/aus · A11y; **F1 TXT** Live-Vorschau · Quick-Insert `{date}` · Reset Default. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.4.2

Post-Release-Polish nach **2.4.1**: **Thumb-Cache** Bestätigung · freigegebene MB Status · Auto-Prune; **Templates** Toolbar Quick-Apply · zuletzt verwendet; **Sync-Scroll** Status-Klick Toggle · Tooltip-Shortcut; **F1 TXT** Zielordner · `{date}_shortcuts.txt`. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.4.1

Post-Release-Polish nach **2.4.0**: **Thumb-Cache** max MB · Cache leeren · Hit/Miss Debug; **Templates** Umbenennen/Vorschau/★; **Sync-Scroll** nur PDF↔PDF · Statusleiste; **F1** Suche/Filter · Drucken · TXT. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.4.0

Minor-Bump nach **2.3.5**: **Thumbnail Disk-Cache** (mtime); **Annotation-Templates** `ildtmpl-v1`; **Split-View Sync-Scroll** für zwei PDF-Tabs; **Tastatur-Cheat-Sheet** F1 (DE). Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.3.5

Post-Release-Polish nach **2.3.4**: Kompression **A11y Toggle · Status-% announced**; Links TXT **Reset Bestätigung nur bei Abweichung · Fokus+Selektion**; Palette **Pin-ersetzen mit Namen**; Telemetrie **„Stubs öffnen“ Fokus erste Stub-Zeile**. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.3.4

Post-Release-Polish nach **2.3.3**: Kompression Label **„Ergebnis nach Kompression öffnen“ · A11y**; Links TXT **Live-Vorschau · Quick-Insert `{stem}`/`{date}` · Reset Default**; Palette **Overflow-Hinweis · ältesten Pin ersetzen**; Telemetrie **Esc schließt · „Stubs öffnen“**. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.3.3

Post-Release-Polish nach **2.3.2**: Kompression **Toggle Settings · Status-% bei Fehler**; Links TXT **Template `{stem}_links.txt` · Zielordner · BOM**; Palette **Pin Persistenz · Unpin · max Pins**; Telemetrie **warum Stub + Stubs-Tab**. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.3.2

Post-Release-Polish nach **2.3.1**: Kompression **optional öffnen · Ersparnis-% Status**; Links Sidebar **Filter · Doppelklick→Seite · TXT-Export**; Palette **Pin · Recent 5/10/20**; Telemetrie **Toggle disabled · Info-Dialog**. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.3.1

Post-Release-Polish nach **2.3.0**: Kompression **Vorher/Nachher · Abbruch · DPI/Q-Presets**; Links **Validierung · Tooltip · Sidebar Edit/Löschen**; Palette **Fuzzy · Recent · Esc · Kategorien**; Telemetrie-Warntext **„keine Datenübertragung“**. Stubs klar markiert (Ink ≠ Stylus).

## Neu in 2.3.0

Minor-Bump nach **2.2.5**: **PDF-Kompression/Downsample** Qualitäts-Dialog → neues File; **Link-Annotationen** Sidecar+Bake; **Ctrl+K** Command Palette; **Telemetrie-Stub** opt-in no-op. Stubs KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie klar markiert (Ink ≠ Stylus).

## Neu in 2.2.5

Post-Release-Polish nach **2.2.4**: PageLabels TXT **Live-Vorschau · Quick-Insert `{stem}`/`{date}` · Reset Default**; Ink Toast **Klick→Ink-Tool · A11y wie OCR**; Historie **Undo Clear Redo · klarer DE-Hinweis**; CONTRIBUTING Sync **Windows · optional `-NoStart`**. Stubs unverändert (Ink ≠ Stylus).

## Neu in 2.2.4

Post-Release-Polish nach **2.2.3**: PageLabels TXT **Template `{stem}_labels.txt` · Zielordner · BOM**; Ink Status **Toast-Dauer Settings · A11y**; Historie **Clear-Zähler · Undo Clear**; CONTRIBUTING **Sync copy-ready Einzeiler**. Stubs unverändert (Ink ≠ Stylus).

## Neu in 2.2.3

Post-Release-Polish nach **2.2.2**: PageLabels **Scroll-Liste erste 20 · Export Labels TXT**; Ink **Redo nach Glätten · Status „Glättung angewandt“**; Historie **Clear optional Filter · Export gefilterte Sicht**; CONTRIBUTING **Exitcode-Tabelle kurz** + Link `scripts/smoke_ild.py`. Stubs unverändert (Ink ≠ Stylus).

## Neu in 2.2.2

Post-Release-Polish nach **2.2.1**: PageLabels **Range-Überlappung DE · Vorschau erste Labels**; Ink **Glättungsstärke · Undo eigener Stack-Eintrag**; Historie **Doppelklick→Seite · Clear Bestätigung**; CONTRIBUTING **Sync-Einzeiler=sync-ild.ps1** + smoke Beispiel. Stubs unverändert (Ink ≠ Stylus).

## Neu in 2.2.1

Post-Release-Polish nach **2.2.0**: PageLabels **Range-Editor · PDF-Import · Reset arabisch 1…**; Ink **Strichstärke/Farbe · letzter Strich · Glätten**; Historie-Panel **50 · Filter · Export JSON**; smoke Stub **manual only** + CONTRIBUTING Sync. Stubs unverändert (Ink ≠ Stylus).

## Neu in 2.2.0

Minor-Bump nach **2.1.5**: **Seitenbeschriftungen** (Sidecar + optional PDF PageLabels); **Freihand-Ink** Maus-Polyline + Undo; **Dokument-Historie ildhist-v1**; `smoke_ild` in CONTRIBUTING + CI-Stub. Stubs unverändert (Ink ≠ Stylus).

## Neu in 2.1.5

Post-Release-Polish nach **2.1.4**: Import-Copy Toast **OCR-Dauer · Klick Status/Log**; Mess/Diff-Reset **gemeinsamer Helper · Esc verwirft Edit**; `smoke_ild.py` Fail-error **max 200…**; **FEATURES.md lokal sync** in Info. Stubs unverändert.

## Neu in 2.1.4

Post-Release-Polish nach **2.1.3**: Import-Status **Clipboard · Toast · A11y**; Mess-CSV **Reset Default Bestätigung≠Default · Fokus+Selektion**; Diff-TXT **Quick-Insert · Reset Default**; `smoke_ild.py --json` **Fail `checks[].error` · Exitcode=ok**. Stubs unverändert.

## Neu in 2.1.3

Post-Release-Polish nach **2.1.2**: Kommentar-Import Status **ersetzt/übersprungen/neu · kopierbar**; Mess-CSV Live-Template **`{stem}_measures.csv` · Quick-Insert**; Diff-TXT **`{stemA}_vs_{stemB}_{mode}.txt` · Live · ungültige rot**; `smoke_ild.py --json` Schema+Beispiel. Stubs unverändert.

## Neu in 2.1.2

Post-Release-Polish nach **2.1.1**: Kommentar-Import **Sidecar-Toggle · Status N/M**; Mess-CSV **Typ,Seite,Wert,Einheit · Ordner · BOM**; Textlayer **Side-by-Side · TXT-Template**; `smoke_ild.py` **`--json` · Laufzeit ms**. Stubs unverändert.

## Neu in 2.1.1

Post-Release-Polish nach **2.1.0**: Kommentar-Import **Dry-Run/Duplikate/Fortschritt/Abbruch**; Messung **Snap · Labels persistent · Messwerte-CSV**; Textlayer **Ignore-WS · Nur-Diff · Diff-TXT**; `smoke_ild.py` Exit **0/1/2** · `--qt`/`--skip-qt` · DE-Hilfe. Stubs unverändert.

## Neu in 2.1.0

Minor-Bump nach **2.0.5**: **PDF-Kommentar-Import** (native Markup → Sidecar); **Messung Fläche + Winkel** mit **mm/px Toggle**; **Textlayer-Diff** im PDF-Vergleich; Nightly-Smoke `scripts/smoke_ild.py`. Stubs unverändert.

## Neu in 2.0.5

Post-Release-Polish nach **2.0.4**: Multi-Doc Reset Default **Bestätigung nur bei Abweichung · Fokus+Selektion**; Portfolio Footer **Klick-Filter übersprungene · leer bei 0**; HC-Toast **A11y wie OCR-Toast**; **install-ild -Quiet** Kurz-Summary · Exit 0 wenn nichts zu entfernen. Stubs unverändert.

## Neu in 2.0.4

Post-Release-Polish nach **2.0.3**: Multi-Doc CSV Template **Quick-Insert `{date}`/`{query}` · ungültige rot · Reset Default**; Portfolio Extrakt Footer **„extrahiert X, übersprungen Y“ · Ordner öffnen**; HC-Toast **Dauer OCR-Settings · A11y Announcement**; **install-ild.ps1 -Uninstall** Log-Pfad + **-Quiet**. Stubs unverändert.

## Neu in 2.0.3

Post-Release-Polish nach **2.0.2**: Multi-Doc CSV **Zielordner · Live-Template `{date}_multisearch.csv`**; Portfolio Extrakt **Abbruch · Teilergebnis · Statuszählung**; HC-Toast **an/aus**; UI-Reset **Bestätigung nur ≠100**; **install-ild.ps1** fehlende Shortcuts kein Fehler. Stubs unverändert.

## Neu in 2.0.1

Post-Release-Polish nach **2.0.0**: Multi-Doc **Aa/Wort/Regex · CSV · Fortschritt**; Portfolio **Sidebar · Auswahl · leere Collection**; High-Contrast **Persistenz**; UI-Schrift **100/125/150 % Live-Vorschau**; **install-ild.ps1** `-NoDesktop` / Idempotenz / sync-Hinweis. Stubs unverändert.

## Neu in 2.0.0

Major-Release nach **1.9.5** (Basis **1.9.4** / **1.9.3** / **1.9.2** / **1.9.1** / **1.9.0** / **1.8.5**): **Multi-Dokument-Suche** (Volltext Textlayer aller offenen PDFs · zentrale Trefferliste); **PDF-Portfolios** (pikepdf Collection/Attachments erstellen/öffnen); **Accessibility** High-Contrast Theme + größere UI-Schrift (Outline-Vorlesen bleibt Stub); **install-ild.ps1** Startmenü + optional Desktop (ohne Admin). Stubs KI/Cloud/Stylus/3D/Plugin-Hooks unverändert klar markiert.

Siehe [CHANGELOG.md](CHANGELOG.md), [FEATURES.md](FEATURES.md) und [INFO.md](INFO.md).
