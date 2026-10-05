# InstantLens Doc — Kurzinfo

| | |
|---|---|
| Produkt | InstantLens Doc |
| Version | **2.6.43** |
| Hersteller | Andreas Meyer |
| Kontakt | ame@sellerbach.de |
| PDF | pypdfium2 / PDFium |
| Code | `/workspace/InstantLensDoc/` → Ziel `D:\AI_Temp\InstantLensDoc` |
| Branch | `cursor/instantlensdoc-2108` · [PR #3](https://github.com/kickmetox/hello-github/pull/3) |
| GUI | Python 3.12 + PySide6 |

## Lizenz

- Trial: **28 Tage** ab Erststart  
- Keys: **32 Tage (30+2)**, Format `ILD1.…`  
- Neu anfordern: **ame@sellerbach.de**  
- Statusleiste: bei **<7 Tagen** Restlaufzeit prominent hervorgehoben  
- Resttage Statusleiste + About **konsistent** („noch X Tage“ / „noch 1 Tag“)  
- Ablaufdatum **TT.MM.JJJJ** in About + Status (+ Lizenzdialog)  
- Warnung **≤3 Tage** vor Ablauf: Banner (nicht modal); **Klick → About/Aktivierung**  
- Banner: **Icon** + **Dismiss** + **Schließen-X**; Persistenz **`dismiss_date`** (bis morgen)  
- Banner: **Esc** schließt; **AccessibleName** für Screenreader  
- Banner: **Fokus-Ring** sichtbar; **Enter** öffnet Aktivierung  
- Banner-Text **i18n** (DE); Farbe **Warnung** (gelb) vs. **abgelaufen** (rot)  
- Lizenz-Dialog: Resttage + Ablaufdatum klar  
- About: Version, **Lizenzstatus**, Kontakt, Changelog-Kurzliste; bei Trial/ungültig **Lizenz aktivieren…**; **Privacy: lokal, keine Telemetrie**

## Sync (eine Zeile, copy-ready)

`powershell -ExecutionPolicy Bypass -File "D:\AI_Temp\sync-ild.ps1"`

Skript: [sync-ild.ps1](scripts/sync-ild.ps1) — Branch `cursor/instantlensdoc-2108` (oder `-LocalPack` / Pack-Zip) nach `D:\AI_Temp\InstantLensDoc`, pip, Start. **Nutzer-Icon in `assets` wird nicht überschrieben.**

**FEATURES.md lokal sync:** Nach Sync liegt `FEATURES.md` lokal im App-Ordner (`D:\AI_Temp\InstantLensDoc\FEATURES.md`); About/Stubs öffnen diese lokale Datei — Version **2.6.43**.

Ohne Start: `-NoStart` (Alias `-SkipStart`). Exit-Codes: **0** OK · **1** allgemein · **2** Git-Fehler.

Fallback bei Git-Fehler:
```powershell
powershell -ExecutionPolicy Bypass -File "D:\AI_Temp\sync-ild.ps1" -LocalPack D:\AI_Temp\InstantLensDoc-pack.zip -SkipStart
```

## Start (manuell)

```bat
cd D:\AI_Temp\InstantLensDoc
pip install -r requirements.txt
run.bat
```

`run.bat` prüft Python ≥3.10 und Kern-Deps (PySide6, pypdfium2, pikepdf, Pillow) mit klaren DE-Meldungen; bei fehlenden Paketen optional `python -m pip install -r requirements.txt` (J/N) oder non-interactive **`run.bat --yes`** / **`-y`**. Hilfe: **`run.bat --help`** / **`-h`**. Env-Override: **`set ILD_PYTHON=C:\Pfad\zu\python.exe`** (höchste Priorität); bei ungültigem/leerem Pfad Warnung, dann `.venv` falls vorhanden, sonst Fallback **`py -3` → `python` → `python3`**. Gewählte Binary: **`gefunden: …`** inkl. kurz **`--version`**. Hinweis wenn lokale **`.venv`** vorhanden aber unvollständig. Fehlt Python: kurzer Download-Hinweis **Microsoft Store** / **python.org**.

Exit-Codes `run.bat`: **0** OK / Hilfe · **1** Python/Deps/pip-Fehler bzw. Installation abgelehnt (App-Exitcode ≠0 wird durchgereicht).

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

Voraussetzung: **Python 3.10+ 64-Bit**. Optional: `-Allow32Bit`, `-SkipKeygen`, `-NoKeygenInApp`, `-Clean`.

Python-Layout-Zip (ohne PyInstaller-EXE):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\pack-windows-runnable.ps1
```

Installer: `.\scripts\build-windows-installer.ps1` bzw. `.\installer\build-installer.ps1` (optional `-NoKeygen`) → `dist\InstantLensDoc-Setup-2.6.43.exe`  
Desktop-/Keygen-Shortcuts: `.\scripts\install-ild.ps1` (Keygen wenn `run-keygen.bat` / EXE vorhanden; `-SkipKeygen`)  
Desktop-Verknüpfung Installer: optionale Checkbox (`desktopicon`, Standard an / `checkedonce`)

**Nach Sync (DE, copy-ready):**

```powershell
cd D:\AI_Temp\InstantLensDoc
powershell -ExecutionPolicy Bypass -File .\scripts\install-ild.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1   # optional, Inno Setup 6
```

Oder Sync inkl. optionalem Installer-Build: `…\sync-ild.ps1 -BuildInstaller -SkipStart`

## Keygen

```bat
run-keygen.bat
python -m keygen kunde@example.com
python -m keygen --verify "ILD1...."
```

PowerShell: `powershell -ExecutionPolicy Bypass -File .\run-keygen.ps1`  
`run-keygen.bat`/`.ps1` setzen `PYTHONPATH` auf diesen Ordner und den Parent (nested `InstantLensDoc-keygen` unter App-Root; Standalone mit Vendor `instantlensdoc\`).  
Trial 28 Tage · Keys 32 Tage (HMAC `ILD1.…`). Details: `keygen/README.md`.

## Scripting

```bat
python -m ild --help
run-ild.bat pages dokument.pdf
powershell -ExecutionPolicy Bypass -File .\scripts\ild.ps1 license generate kunde@example.com
```

Anleitung: Store `docs/instantlensdoc-scripting.md` · Beispiel `examples/ild_scripting_demo.py`.

## Neu in 2.6.43

Patch nach **2.6.42** (Tesseract-Runtime) — Speichern unter für Text/Word-Suite:

- **Kein `.py`-Default** mehr bei neuem Text (Windows/`python.exe`)
- Filter: `.ild` (nativ), `.txt`, `.md`, `.html`, `.docx`, `.rtf`, `.pdf`, `.xlsx`
- `setDefaultSuffix` + Vorschlagsname mit Endung (`Unbenannt.ild` / `.md` …)
- Text → PDF über Export; Öffnen inkl. `*.ild`
- Pack: `InstantLensDoc-2.6.43-pack.zip`

## Neu in 2.6.42

Patch nach **2.6.41**: OCR ohne separates Tesseract, wenn ScanTuxio-Runtime vorhanden.

- Lookup: `{app}\vendor\tesseract\tesseract.exe` · `{app}\tesseract\tesseract.exe` · `D:\AI_Temp\ScanTuxio Win\tesseract\` / `vendor\tesseract\` / `bin\` · Program Files / PATH
- `TESSDATA_PREFIX` = tessdata neben `tesseract.exe` (deu+eng)
- Zip ohne Binaries: Copy-Hint `xcopy /E /I /Y "D:\AI_Temp\ScanTuxio Win\tesseract" .\vendor\tesseract`
- Pack: `InstantLensDoc-2.6.42-pack.zip`

## Neu in 2.6.41

Patch nach **2.6.40** (Blank-View/Build Guard) — enthaelt dessen Fixes:

- **Scannen starten:** Menü **Geräte → Scanner / Scannen…** · PDF → Scannen / Import… · Toolbar **Scan…** · Welcome **Scannen…** · Ctrl+Alt+Shift+I
- **ScanTuxio-Port:** `instantlensdoc/core/scantuxio/` (NAPS2 WIA/TWAIN, native-eSCL, SANE, mDNS, Qt/CUPS-Druck)
- Acquire: ScanTuxio dispatch → WIA-Fallback; leere Geräteliste mit DE-Status
- Enthaelt **2.6.40**: `_ensure_page_painted`, Pack-Entry `run_instantlensdoc.py`, EXE-Build-Guard
- Pack: `InstantLensDoc-2.6.41-pack.zip`

## Neu in 2.6.40

- Blank PDF View: `_ensure_page_painted` + Thumb-Klick erzwingt Paint
- Windows Build Guard: Pack inkl. `run_instantlensdoc.py`; EXE-Preflight; kleines Setup = Fehler
- Pack: `InstantLensDoc-2.6.40-pack.zip`

## Neu in 2.6.39

- **Large-PDF:** cancelbarer Open mit Progress; 1. Seite sofort gerendert
- **Thumbnails:** Shared-Placeholder, Chunked Add, Viewport±Prefetch (kein Voll-Queue ab Threshold)
- **Edit/Text:** page-scoped Warn bei Voll-Extraktion; Doc-Stats Sample statt Full-Extract
- Pack: `InstantLensDoc-2.6.39-pack.zip`

## Neu in 2.6.38

- Windows Drucker/Scanner-Discovery gehaertet (Get-Printer, WIA/PnP/TWAIN, Winspool)
- Menue **Geraete** (Scanner / Drucker / Erkennen); klare DE-Treiberhinweise
- Scan-Acquire ohne Crash; Tesseract-Pfad-Autodetect unter Windows
- Pack: `InstantLensDoc-2.6.38-pack.zip`

## Neu in 2.6.36

Patch nach **2.6.35** (Sync/Fresh-Dest):

- **`InstantLensDoc.exe`:** Relative-Import-Crash behoben (`attempted relative import with no known parent package`)
- Neuer Entry **`run_instantlensdoc.py`** (absolute Imports); `__main__.py` absolut; Build/Spec umgestellt
- Hiddenimports/`--collect-submodules instantlensdoc` fuer Package-Daten
- Pack: `InstantLensDoc-2.6.36-pack.zip`

## Neu in 2.6.35

Patch nach **2.6.34** (Keygen Import):

- **`sync-ild.ps1`:** Ordner-Sperre haerten (Kinder einzeln, Keygen skip-or-retry, DE `taskkill`/`handle`)
- **`-Dest`** frischer Ordner (z. B. `D:\AI_Temp\InstantLensDoc-2635`) + optional **`-Swap`**
- Sync verlangt `scripts\build-windows-installer.ps1` (kein gemischter Alt-Tree)
- **`build-windows.ps1`:** PyInstaller-Probe ohne opaken stderr-Abbruch; klares `pip install`
- Pack: `InstantLensDoc-2.6.35-pack.zip`

## Neu in 2.6.34

Patch nach **2.6.33** (Installer/run.bat cmd-Loop):

- **`run-keygen.bat` / `run-keygen.ps1`:** PYTHONPATH = Keygen-Ordner + Parent; DE-Fehler wenn `instantlensdoc` fehlt
- **`keygen/__main__.py`:** App-Root-/Vendor-Suche; History ohne `config` (Standalone)
- Store-Zip `InstantLensDoc-keygen` mit Minimal-Vendor `instantlensdoc.license`
- Pack: `InstantLensDoc-2.6.34-pack.zip`

## Neu in 2.6.33

Patch nach **2.6.32** (Build-PS Encoding):

- **`run.bat` / `run-ild.bat` / `run-keygen.bat`:** pure ASCII (kein UTF-8-Mojibake in cmd.exe)
- **`installer/build-installer.ps1`:** bevorzugt EXE-Layout nach `build-windows.ps1` (Post-Install = `InstantLensDoc.exe`)
- ISS / `installer-hinweis.txt` ASCII-safe
- Pack: `InstantLensDoc-2.6.33-pack.zip`

## Neu in 2.6.32

Patch nach **2.6.31** (Sync-Parser-Fix):

- **`build-windows.ps1`** / **`scripts/build-windows-installer.ps1`** / **`installer/build-installer.ps1`**: ASCII-Punctuation + UTF-8 BOM für Windows PowerShell 5.1
- Weitere Pack-`.ps1` (`install-ild.ps1`, `ild.ps1`, `pack-windows-runnable.ps1`, `run.ps1`) gleich gehärtet
- Pack: `InstantLensDoc-2.6.32-pack.zip`

## Neu in 2.6.31

Patch nach **2.6.30** (Sync flat/nested):

- **sync-ild.ps1:** Windows PS 5.1 Parser-Fix (ASCII statt Em-Dash/Smart-Quotes; UTF-8 mit BOM)
- Mojibake / Try-Catch-/String-Fehler behoben
- Pack: `InstantLensDoc-2.6.31-pack.zip`

## Neu in 2.6.30

Patch nach **2.6.29** (Silbentrennung-UI):

- **sync-ild.ps1:** flat Pack-Root **oder** nested `InstantLensDoc/` via Marker (`VERSION.txt` / `build-windows.ps1` / `requirements.txt`)
- Kein Windows-Case-Mixup mehr mit Python-Paket `instantlensdoc\`
- **ForceClean** default (Icons bleiben); Ziel in use → `cd D:\AI_Temp`
- Pack nested: `InstantLensDoc-2.6.30-pack.zip`

## Neu in 2.6.29

Minor nach **2.6.28** (Audit-Closure):

- **Silbentrennung Menü/Palette** für alle 9 UI-Sprachen (DE/EN/FR/RU/ES/ZH/PT/AR/IT; ZH/AR no-break)
- FEATURES: Signieren-Zeile = eIDAS-Trust; Mehrsprach-UI-Zeile → i18n **2.6.17**

## Neu in 2.6.28

Minor nach **2.6.27** (Installer-Sync + Mausrad):

- **Mausrad Default-PDF / Frames:** Rad blättert Einzelseite; Canvas-Wheel; CS/1S/Editor/`apply_wheel_scroll` bleiben
- **Abbildungs- & Stichwortverzeichnis** (`ILD-LOF-*` / `ILD-IDX-*`)
- **F12 Speichern unter** + Ribbon Save-as + Alt+1…6
- **`.pptx`** Export/Import · Abschnittsumbrüche · Grammatik DE/EN
- **Silbentrennung** 9 Sprachen · Pantone-ähnlich/Spot · Web-PDF · Print-Preview
- **eIDAS Trust-Pfad** (ohne TSA) · lokaler Realtime-Hub · Handschrift Multi-PSM
- Freier KI-Chat-Stub / Outline-TTS / gehostete Cloud+QES-TSA = externe Abhängigkeit

## Neu in 2.6.27

Minor nach **2.6.26** (Polish / Installer):

- Installer im Sync-Flow (`sync-ild.ps1 -BuildInstaller`)
- Mausrad-Härtung Text/Word-Suite (`apply_wheel_scroll`, Trackpad pixelDelta)
- Hilfe/Info Installer+Keygen+Scripting


## Neu in 2.6.26

Minor nach **2.6.25** (Stylus / Outline / Hooks / Telemetrie / 3D / Installer):

- **Polish / Konsolidierung:** keine großen neuen Produktflächen; Serie 2.6.20–2.6.25 stabilisiert
- **Windows-Installer gehärtet:** Version aus `VERSION.txt`, Preflight (run.bat/EXE), ISCC `/DMyAppVersion=`, CustomMessages DE/EN, AppMutex/MinVersion/64-Bit
- **Einzeiler Setup.exe (Windows x64 + Inno Setup 6):** `powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1` → `dist\InstantLensDoc-Setup-2.6.26.exe`
- Runnable-/Installer-Pack und Docs/i18n aktualisiert
- Freier KI-Chat-Stub und Outline-TTS bleiben geplant

## Neu in 2.6.25

Minor nach **2.6.24** (Hyperlinks / Medien / EPUB):

- **Stylus / Palm Rejection:** Tablet-Stift mit Druck→Strichstärke; Palm-Rejection; sonst verbesserte Freihand-Integration
- **Dokumentstruktur (Outline-Pane):** Überschriften, PDF-Lesezeichen, Favoriten, Filter, Navigation (Sidebar) — jenseits reinem TOC
- **Script-/Plugin-Hooks:** User-Skripte für open/save/export/ocr via Python/PowerShell `ild` (`config_dir()/hooks`)
- **Telemetrie:** optionale lokale Diagnostik, Opt-in Default aus, kein Netzwerk, kein PII (`diagnostics.jsonl`)
- **3D-Extrusion Limited Viewer:** isometrische Vorschau einfacher Formen (kein Mesh/OpenGL)
- **Windows-Installer (Inno):** `scripts\build-windows-installer.ps1` → `InstantLensDoc-Setup-2.6.25.exe` (Startmenü, optional Desktop, Uninstall, 64-Bit; Build auf Windows x64)
- **ild API:** `hooks_*` / `document_outline_api` / `stylus_status` / `telemetry_*` / `extrude3d_preview`
- Freier KI-Chat-Stub und Outline-TTS bleiben geplant

## Neu in 2.6.24

Minor nach **2.6.23** (Gemeinsames Review / Cloud-Ordner):

- **Hyperlinks:** Text mit URL oder Dokumentziel (`#anker`, `ild://line/N`, Überschrift); Markdown/HTML; Dialog Ctrl+Shift+K; Sidecar `*.ildlinks.json`
- **Grafiken & Medien:** Bild skalieren/zuschneiden; Formen; Online-Video-Platzhalter (URL); Textumfluss bleibt
- **EPUB-Export:** Text/Markdownish → EPUB 2 (Kapitel aus H1); Import als Text
- **ild API:** `insert_hyperlink` / `extract_hyperlinks` / `layout_scale_image` / `layout_crop_image` / `layout_add_shape_frame` / `layout_add_video_placeholder` / `export_epub_api`
- CLI `hyperlink`/`hyperlinks`/`anchors`/`layout-shape`/`layout-video`/`layout-scale`/`layout-crop`/`export-epub` · PS `Add-IldHyperlink` / `Export-IldEpub` / …
- Stubs Stylus/3D/Hooks/Outline/Telemetrie/freier KI-Chat unverändert (→ 2.6.25)

## Neu in 2.6.23

Minor nach **2.6.22** (Stapel/eIDAS/Seriendruck-Polish):

- **Gemeinsames Review / Cloud-Ordner:** Notizen, Markierungen, Stempel und Kommentare zwischen Nutzern austauschbar
- **Freigabeordner-Sync:** `session.ildshare.json` (ildshare-v1) — NAS/OneDrive/SMB/USB
- **Optionaler HTTP-Endpoint:** einfaches GET/PUT JSON-Bundle; Polling (Auto-Sync)
- **Integration:** Kommentare/Review (2.6.21) + Annotationen/Stempel (2.6.9)
- **UI:** Starten/Beitreten/Sync + dokumentierte Einschränkungen; Ribbon/Palette/Extras
- **ild API:** `shared_review_start/join/sync/status/info` · CLI `share-*` · PS `Start-/Join-/Sync-IldSharedReview`
- Offline bleibt voll nutzbar; freier KI-Chat-Stub unverändert; kein gehosteter Cloud-Dienst

## Neu in 2.6.22

Minor nach **2.6.21** (Review/Kommentare/Versionen/Seriendruck):

- **Stapelverarbeitung:** Viele PDFs — Konvertieren (→PNG), Wasserzeichen, Komprimieren, Verschlüsseln (AES); Pipeline möglich
- **Digitale Signaturen (eIDAS):** SES-Stempel · AES mit PKCS#12 · QES als QTSP-Import-Pfad; Sidecar `*.ildesign.json`
- **Seriendruck-Polish:** Vorschau, fehlende Felder, Delimiter, HTML/DOCX, kombinierte Datei
- **ild API:** `run_batch_job` / `sign_pdf_api` / `verify_signature_api` / `mail_merge_preview`
- CLI `batch`/`sign`/`sign-verify`/`eidas` · PS `Invoke-IldBatch` / `Invoke-IldSign` / `Test-IldSignature`
- Cloud-Echtzeit-Kollaboration damals noch Stub (→ 2.6.23); freier KI-Chat-Stub unverändert
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert

## Neu in 2.6.21

Minor nach **2.6.20** (Spell/Autocorrect/Ribbon/Undo):

- **Review / Track Changes:** Einfügen/Löschen je Autor; Sidecar `*.ildreview.json`; Accept/Reject
- **Kommentare:** Feedback an Textstellen ohne Body-Änderung; `*.ildcomments.json`
- **Versionsverlauf:** Snapshots unter `*.ildversions/`; Speichern/Wiederherstellen
- **Seriendruck (Basis):** Empfänger CSV/Excel → Briefe mit `{{Feld}}` / `«Feld»`
- **ild API:** `review_*` / `comment_*` / `version_*` / `mail_merge_run`
- CLI `review-*`/`comment-*`/`version-*`/`mail-merge` · PS `Enable-IldReview` / `Add-IldComment` / `Save-IldVersion` / `Invoke-IldMailMerge`
- Ribbon-Tab **Review**; freier KI-Chat-Stub unverändert; keine Cloud-Echtzeit-Kollaboration; eIDAS wartet
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert

## Neu in 2.6.20

Minor nach **2.6.19** (Compare/Book/Tabs/Ribbon):

- **Rechtschreibung:** Vorschläge + leichte Grammatik-Hints; Builtin der UI-Sprache (F7 / Shift+F7)
- **Autokorrektur & Textbausteine:** Tippfehler/Kürzel beim Tippen; 9 Baustein-Slots
- **Ribbon/Workspace:** Tabs Bearbeiten/Fenster; Dokument-Tabs Drag; separates Fenster
- **Undo/Redo:** Annotation-/Seiten-Ops-Stacks praktisch unbegrenzt; Editor undoLimit=0
- **ild API:** `spellcheck` / `suggest_word` / `autocorrect_text` / `list_snippets`
- CLI `spellcheck`/`suggest`/`autocorrect`/`snippets` · PS `Invoke-IldSpellcheck` / `Invoke-IldAutocorrect` / `Get-IldSnippets`
- Freier KI-Chat-Stub unverändert; keine Cloud-Echtzeit-Kollaboration
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert

## Neu in 2.6.19

Minor nach **2.6.18** (CMYK/Bleed/Preflight/PDF/X):

- **Document Comparison:** Side-by-Side, Drag-and-Drop, Sync-Scroll, Diff-Highlight
- **ild API:** `compare_pdfs` · CLI `compare` · PS `Invoke-IldCompare`
- **Buch-Layout:** Cover allein, danach Doppelseiten (Ctrl+Alt+2)
- **Seite-für-Seite-Scroll:** Mausrad blättert Seiten (Ctrl+Alt+3)
- **Dokument-Tabs** + partielle **Ribbon-Chrome** (Start/Ansicht/PDF)
- Keine volle Cloud-Kollaboration
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert

## Neu in 2.6.18

Minor nach **2.6.17** (i18n + Handschrift):

- **Farbmanagement:** RGB/CMYK-Workflows, eingebaute Paletten, Spot-Hinweise, `convert-color`
- **Bleed/Anschnitt:** Presets + TrimBox/BleedBox (`apply-bleed` / UI)
- **Dokument-Ebenen:** Hintergrund / Bilder / Text für Rahmen (`layers` / `layout-set-layer`)
- **Preflight:** fehlende Schriften, niedrige Bildauflösung, Bleed-Hinweise
- **PDF/X / print-ready:** Export neben normalem PDF (`export-pdfx`)
- Scripting: `palettes` / `preflight` / `export-pdfx` / `apply-bleed` · PS `Invoke-IldPreflight` / `Export-IldPdfX`
- Kein volles PDF-Compare, kein Ribbon-Overhaul
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert

## Neu in 2.6.17

Minor nach **2.6.16** (volles InstantLens Doc i18n + Handschrift-Hook):

- **UI-Sprachen:** DE, EN, FR, RU, ES, ZH, PT, AR, IT — Einstellungen → Oberflächensprache (persistiert)
- **Module:** Viewer, OCR, Scan, Annotationen, Formulare, Export, Assistenten, Einstellungen inkl. Hilfe/Info
- **RTL** für Arabisch wo praktikabel; Locale-Katalog `instantlensdoc/locales/`
- **Externe Docs:** `docs/i18n/{lang}/` (DE+EN vollständig, übrige scaffolded)
- **Handschriftenerkennung:** Basis-Hook Tesseract PSM (OCR-Dialog / Menü / `ild.ocr_handwriting`)
- Scripting: `ui-langs` / `set-ui-lang` / `tr` / `ocr-handwriting` · PS `Get-IldUiLangs` / `Set-IldUiLang` / `Invoke-IldOcrHandwriting`
- Freier KI-Chat-Stub unverändert; kein CMYK/Bleed/Preflight/PDF/X damals, kein PDF-Compare
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert

## Neu in 2.6.16

Minor nach **2.6.15** (isolierte KI-Dokument-Wizards):

- **KI-Wizards:** Formular, Anschreiben, Kaufvertrag, Rechnungsformular — geführte Abfragen
- Generisch oder unternehmensbezogen (Firma, Adresse, USt-Id, IBAN …)
- UI: Extras → **Dokument erstellen… (KI-Wizard)** (Ctrl+Alt+Shift+Q); kein freier Chat
- Lokal templatebasiert; optionaler LLM-Hook nur hinter dem Wizard
- Scripting: `ild.generate_ki_document` / `list_ki_wizards` · CLI `ki-wizard` · PS `Invoke-IldKiWizard`
- Kein CMYK/Bleed/Preflight/PDF/X, kein volles i18n, kein PDF-Compare
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert (freier Assistent bleibt Stub)

## Neu in 2.6.15

Minor nach **2.6.14** (OCR → Word-Suite):

- **OCR → Word-Suite:** Layout-OCR / `*.ildocr.*`-Sidecars als editierbares Dokument übernehmen
- UI: Extras → **In Word-Suite öffnen/übernehmen…** (Ctrl+Alt+Shift+W); Checkbox in OCR- & Scan-Dialog
- Lesereihenfolge/Blöcke bleiben; weiterformatieren/exportieren mit 2.6.10–2.6.14
- Scripting: `ild.ocr_to_word_suite` / `import_ildocr` · CLI `ocr-word-suite` / `import-ildocr` · PS `Invoke-IldOcrWordSuite`
- Kein CMYK/Bleed/Preflight/PDF/X, kein volles i18n, keine KI-Wizards, kein PDF-Compare
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert

## Neu in 2.6.14

Minor nach **2.6.13** (Tabellen & Office-I/O):

- **Tabellen:** Erstellen, formatieren, sortieren (Markdown/`ild-table`; Ctrl+Alt+Shift+T)
- **Daten-Import:** CSV und Excel/`.xlsx` in Dokument-Tabellen
- **Speichern/Export/Import:** `.docx`, `.xlsx`, `.pdf`, `.txt`, `.rtf` (+ HTML/JPG)
- Scripting: `ild.create_table` / `import_table_csv` / `import_table_xlsx` / `save_document` / …
- Kein CMYK/Bleed/Preflight/PDF/X, kein volles i18n, keine KI-Wizards, kein PDF-Compare
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert

## Neu in 2.6.13

Minor nach **2.6.12** (DTP-Typografie):

- **Erweiterte Typografie:** Tracking, Kerning, Leading; Absatz-/Zeichenstile auf 2.6.10 Presets
- **Textumfluss:** Text fließt um Bild-/Formrahmen (`bounding_box` / `contour` / `jump_object`)
- **Silbentrennung:** intelligent DE/EN (Soft-Hyphens) + Hook für weitere Sprachen
- **Drop Caps:** Initiale (Marker + Editor Ctrl+Alt+Shift+D)
- Scripting: `ild.apply_typography` / `hyphenate` / `apply_drop_cap` / `layout_set_text_wrap` / …
- Kein CMYK/Bleed/Preflight/PDF/X, kein volles i18n, keine KI-Wizards, kein PDF-Compare
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert

## Neu in 2.6.12

Minor nach **2.6.11** (DTP-Schritt: Frames / Musterseiten / Satzspiegel):

- **Frames/Boxes:** bewegliche, skalierbare Text- und Bildrahmen (`move_frame` / `resize_frame`)
- **Textrahmen-Verkettung:** Overflow fließt in nächste Spalte/Seite (`flow_text_chain`, Spalten-/Seitenketten)
- **Musterseiten:** wiederkehrende Kopf-/Fußzeilen + Seitenzahlen über Seiten (baut auf 2.6.11 HF)
- **Satzspiegel:** Ränder an Seitenformat-Presets; Overlay Ctrl+Alt+S / Toolbar
- Scripting: `ild.satzspiegel` / `apply_master_page` / `layout_flow_text` / `layout_move_frame` / …
- Kein CMYK/Bleed/Preflight/PDF/X, kein volles i18n, keine KI-Wizards, kein PDF-Compare
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert

## Neu in 2.6.11

Minor nach **2.6.10** (Layout-Hilfen / Word-Suite):

- **Lineal:** horizontal/vertikal (mm/inch), Toolbar + Ctrl+Alt+R
- **Raster / Guides:** Ausrichtungsraster einblendbar, Hilfslinien, optional Snap — Ctrl+Alt+G
- **Kopf-/Fußzeilen:** Seitenzahlen, Titel, **Ersteller/Autor** (`{title}`/`{author}`/`{creator}`)
- **Seitenformate:** US Letter, DIN-A, Buchformate Taschenbuch/DINA5/Roman/Sachbuch/DINA4/Quadrat
- **Absatzformatierung:** Ausrichtung + Zeilenabstand, an Style-Presets (2.6.10) angebunden
- Scripting: `ild.list_page_formats` / `set_page_format` / `apply_header_footer` / `apply_paragraph_format`
- Kein volles DTP damals (Musterseiten/CMYK/Frames → 2.6.12), kein i18n-Pack, keine KI-Wizards
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert

## Neu in 2.6.10

Minor nach **2.6.9** (Word-Suite Basis: Auto-Format / TOC / Shortcuts):

- **Automatische Formatierung:** Heading/Body/Quote-Presets + Heuristik (Markdown/Fontgröße/ALL CAPS)
- **Automatisches Inhaltsverzeichnis:** aus Überschriften → Editor-Markdown bzw. PDF-Outline (Sidebar klickbar)
- **Word-/InDesign-ähnliche Shortcuts:** Ctrl+B/I/U, Ctrl+S, Ctrl+F, Ctrl+H Ersetzen, Ctrl+Z/Y, Ctrl+C/V, Ctrl+P — Liste in Hilfe/F1
- **Suchen/Ersetzen:** Ctrl+H (Word); Scripting `ild find-replace`
- **Windows-Systemschriften** im Inline-Schriftarten-Picker (`QFontComboBox` + `list_system_fonts`)
- Scripting: `ild.auto_format_*` / `generate_toc` / `list_system_fonts` / `find_replace` · CLI · PowerShell
- Kein volles DTP (Musterseiten/CMYK), kein i18n-Pack, keine KI-Wizards
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert

## Neu in 2.6.9

Minor nach **2.6.8** (Annotationen ausbauen):

- **Pinselstärke** einstellbar (Toolbar-Slider, Freihand + Formen)
- **Color-Picker** für Strich- und Füllfarben
- **Formen:** Kreis/Ellipse (gefüllt und Outline), Rechtecke, Dreieck, Rundrect
- **Stempel:** Paid, Bezahlt, Rechnung, Datum plus benutzerdefinierte Text-Stempel
- **Absatz-Highlight:** ganze Textabschnitte markieren (Toolbar „Absatz“, Ctrl+Alt+Shift+H)
- Scripting: `ild.add_shape` / `add_stamp` / `highlight_paragraphs`
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert

## Neu in 2.6.8

Minor nach **2.6.7** (Build + Keygen):

- **Windows-Build:** `build-windows.ps1` mit **64-Bit-Check**, App + `InstantLensKeygen.exe`
- **Runnable-Pack:** `scripts/pack-windows-runnable.py` → Zip mit `run.bat` + Deps + Keygen + `WINDOWS-START.md`
- **Keygen:** CLI/GUI HMAC `ILD1.…`; `install-ild` Startmenü-Shortcut
- **Scripting:** `python -m ild` / `import ild` / `scripts/ild.ps1` (open, OCR, Export, Schwärzen, Seiten, Lizenz)
- Keine Annotationen-/Word-Suite-/i18n-Features in diesem Minor
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert

## Neu in 2.6.7

Minor-Feature nach **2.6.6** (Zusatzanforderungen #8):

- **Verschlüsselung & Rechte:** Passwortschutz **AES-256** (R=6 / AESV3, Fallback AES-128); Rechte Druck/Kopieren/Ändern/Formulare/…
- **UI:** Dialog „Verschlüsselung & Rechte…“ (Status · setzen · entfernen · Rechte) · PDF-Menü / Palette · Ctrl+Alt+Shift+P; Öffnen mit Passwort-Dialog
- Kein Batch / Office-Export / E-Signatur / KI / Cloud / voller Windows-Installer
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert

## Neu in 2.6.6

Minor-Feature nach **2.6.5** (Zusatzanforderungen #7):

- **Interaktive Formularerstellung:** AcroForm Textfelder, Checkboxen und Dropdowns erkennen und erstellen; bestehende Felder ausfüllen
- **UI:** Toolbar „Formular“ (Rechteck ziehen) · Dialog ausfüllen/anlegen/löschen/erkennen · PDF-Menü / Palette · Ctrl+Alt+Shift+K
- Keine E-Signatur / Office-Export / KI / Cloud
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert

## Neu in 2.6.5

Minor-Feature nach **2.6.4** (Zusatzanforderungen #6):

- **Objektmanipulation:** Bilder, Vektorgrafiken und Tabellen verschieben, skalieren, spiegeln oder ersetzen (pypdfium2 PageObjects + pikepdf/Pillow)
- **UI:** Toolbar „Objekt“ · Auswahlrahmen/Handles · Ziehen verschiebt · Ecken skalieren · Dialog für Flip/Ersetzen · PDF-Menü / Palette · Ctrl+Alt+Shift+O
- Keine Formulare / Verschlüsselung / Office-Export / KI / Cloud
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert

## Neu in 2.6.4

Minor-Feature nach **2.6.3** (Zusatzanforderungen #5):

- **Inline-Textbearbeitung:** Text direkt ändern/löschen/einfügen; Reflow in Box-Breite (pypdfium2/pikepdf)
- **Schriftart- & Formatabgleich:** erkennt Familie, Größe, Farbe; Standard-14-Mapping beim Schreiben
- **UI:** Toolbar „Text bearbeiten“ · PDF-Menü · Palette · Doppelklick auf Text · Auswahl → Text bearbeiten · Ctrl+Alt+Shift+E
- Keine Objektmanipulation / Formulare / Verschlüsselung / Office-Export / KI / Cloud
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert

## Neu in 2.6.3

Minor-Feature nach **2.6.2** (Zusatzanforderungen #4):

- **Erweiterte OCR mit Layout-Erhalt:** Tesseract-Blöcke + Lesereihenfolge → editierbarer Text (Absätze)
- **Sidecars:** `*.ildocr.txt` (Text + Block-Metadaten) · optional `*.ildocr.hocr` · `*.ildocr.tsv`
- **OCR-Dialog:** Modus „Text mit Layout-Erhalt“ (Default) · hOCR/TSV-Checkboxen
- **Scan/Import:** Layout-OCR Default · hOCR/TSV-Optionen · Seiten-Sidecars `*.pN.ildocr.*`
- Kein Inline-Textedit / Formulare / Verschlüsselung / Office-Export / KI / Cloud
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert

## Neu in 2.6.2

Minor-Feature nach **2.6.1** (Zusatzanforderungen #2):

- **Scannen / Import:** Scanner-Acquire (WIA/SANE) oder Bilder importieren → Seiten in die aktuelle Session
- **OCR Tesseract:** pytesseract / Tesseract-Binary → durchsuchbarer Text + Sidecar `*.ildocr.txt` (gleiche OCR-Bridge)
- **Geräteerkennung:** lokale + Netzwerk-Drucker (Qt/Winspool) und Scanner (WIA/PnP bzw. SANE); UI Aktualisieren/Neu suchen
- **UI:** PDF → Scannen / Import… (Ctrl+Alt+Shift+I) · Drucker & Scanner… · Palette `scan_import` / `devices` · Toolbar „Scan…“
- **Windows-Deps:** `winget install UB-Mannheim.TesseractOCR` (deu+eng) · `pip install pytesseract` · WIA-Treiber; ohne Hardware: Bildimport
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert; Layout-OCR in **2.6.3**

## Neu in 2.6.1

Minor-Feature nach **2.6.0** (Zusatzanforderungen #3; Scan übersprungen):

- **Seitenmanagement:** Seiten per Drag-and-Drop neu anordnen, einfügen, drehen, löschen; Seiten aus anderen PDFs einfügen/zusammenfügen
- **UI:** PDF → Seitenmanagement… (Ctrl+Shift+M) · Palette `page_manage` · Toolbar „Seiten…“
- **Sidebar:** **Schnellvorschau** (Seitenminiaturen) · klickbares **Inhaltsverzeichnis** (PDF-Outline → Seite)
- **API:** `ild_pdf.insert_pages_from_pdf` · `page_count`
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert; Scan/OCR in **2.6.2**

## Neu in 2.6.0

Minor-Feature nach **2.5.20** (Zusatzanforderungen #1):

- **Echtes Schwärzen:** Unwiderrufliche Redaktion — betroffene Seiten werden gerastert, Zonen schwarz, Content-Stream/Textschicht entfernt (nicht nur Overlay)
- **Metadaten-Bereinigung:** Optional DocInfo/XMP strippen (Default an; Settings)
- **UI:** PDF → Echt schwärzen… · Auswahl → Schwärzung · Palette `true_redact` / `selection_redact` · Overlay-Bake bleibt
- **Settings:** Echt-schwärzen DPI (72/150/300) · Meta-Checkbox
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert; Seitenmanagement **2.6.1**

## Neu in 2.5.20

Post-Release-Polish nach **2.5.19**:

- **OCR-Region:** Open Fail-Path A11y (Tab/Ordner/Datei ohne Pfad · Open-Exception)
- **Farben-Themes:** Swatch Ctrl+Shift+C alle Hex · Hex-All Fail-A11y
- **Dokument-Tags:** Tag−/Clear Fail-Path A11y · Pfad-Copy Fail-A11y
- **Export-Presets:** Summary-Copy Fail-A11y (Zwischenablage)
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.19

Post-Release-Polish nach **2.5.18**:

- **OCR-Region:** Text-Copy Clip-Fail A11y (fehlt/Zwischenablage)
- **Farben-Themes:** Swatch Shift+←/→ ±2 · Hex-Copy Fail-A11y
- **Dokument-Tags:** Tags-Copy/Paste Fail-Path A11y
- **Export-Presets:** Pfad-Copy / Apply-fehlt Fail-A11y
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.18

Post-Release-Polish nach **2.5.17**:

- **OCR-Region:** Pfad-Copy Fail-Path A11y (fehlt/leer)
- **Farben-Themes:** Swatch PageUp/PageDown · Ctrl+C Hex
- **Dokument-Tags:** Menü Öffnen\tEnter · Fail-A11y
- **Export-Presets:** JSON Imp/Exp A11y · Ordner-fehlt Fail-A11y
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.17

Post-Release-Polish nach **2.5.16**:

- **OCR-Region:** Text-Copy Fail-Path A11y (Ergebnis fehlt/leer)
- **Farben-Themes:** Swatch-Ziffern 1–6 → Fokus
- **Dokument-Tags:** F5 → Datei öffnen · Menü Entfernen\tEntf
- **Export-Presets:** Duplizieren/Umbenennen/Löschen A11y Announce
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.16

Post-Release-Polish nach **2.5.15**:

- **OCR-Region:** Fail-Path A11y wenn Ergebnisdatei fehlt
- **Farben-Themes:** Swatch Home/End · RMB Mid/Dbl-Hinweise
- **Dokument-Tags:** Tag± Status/A11y Announce
- **Export-Presets:** Reorder A11y · Menü Anwenden⏎Enter
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.15

Post-Release-Polish nach **2.5.14**:

- **OCR-Region:** F5 → Ergebnisdatei öffnen (Status aktiv · Menü-Hinweise)
- **Farben-Themes:** Swatch-Tastatur Space/H→HL · P→Stift · N→Notiz · C→Hex · ←/→ · AccessibleName
- **Dokument-Tags:** F4 → Ordner öffnen (Recent · Status/A11y)
- **Export-Presets:** F4 → Zielordner öffnen
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.14

Post-Release-Polish nach **2.5.13**:

- **OCR-Region:** F4 → Ergebnis-Ordner öffnen (Status aktiv)
- **Farben-Themes:** Shift+Doppelklick → Stift · Ctrl+Doppelklick → Notiz
- **Dokument-Tags:** Ctrl+Shift+C Pfad kopieren (Recent)
- **Export-Presets:** Ctrl+Home/End an Anfang/Ende verschieben
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.13

Post-Release-Polish nach **2.5.12**:

- **OCR-Region:** Ctrl+C → Text kopieren · Ctrl+Shift+C → Pfad (Status aktiv)
- **Farben-Themes:** Doppelklick Swatch → Highlight-Farbe setzen
- **Dokument-Tags:** F3 Tag entfernen (Recent)
- **Export-Presets:** Ctrl+↑/↓ Reihenfolge verschieben
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.12

Post-Release-Polish nach **2.5.11**:

- **OCR-Region:** Enter → Ergebnis-Tab fokussieren
- **Farben-Themes:** Shift+Mittelklick → Stift · Ctrl+Mittelklick → Notiz
- **Dokument-Tags:** F2 Tag hinzufügen (Recent)
- **Export-Presets:** Ctrl+Enter Anwenden ohne Schließen
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.11

Post-Release-Polish nach **2.5.10**:

- **OCR-Region:** Esc / Menü → Status schließen
- **Farben-Themes:** Swatch-Mittelklick → Highlight-Farbe setzen
- **Dokument-Tags:** Shift+Entf/Backspace → Alle Tags entfernen
- **Export-Presets:** Ctrl+D Duplizieren
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.10

Post-Release-Polish nach **2.5.9**:

- **OCR-Region:** Status-Rechtsklick → Kontextmenü (Tab · Ordner · Pfad · Text · Datei)
- **Farben-Themes:** Swatch-RMB → als Highlight-/Stift-/Notizfarbe setzen
- **Dokument-Tags:** Ctrl+X Tags ausschneiden · „Alle Tags entfernen“
- **Export-Presets:** F2 Umbenennen
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.9

Post-Release-Polish nach **2.5.8**:

- **OCR-Region:** Status-Alt+Klick öffnet Ergebnisdatei · Tooltip mit Textvorschau
- **Farben-Themes:** Swatch-Klick kopiert einzelne Hex-Farbe
- **Dokument-Tags:** Ctrl+C / Ctrl+V Tags kopieren/einfügen (Recent)
- **Export-Presets:** Pfad kopieren (RMB · Ctrl+Shift+C)
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.8

Post-Release-Polish nach **2.5.7**:

- **OCR-Region:** Status-Shift+Klick kopiert Ergebnistext (ohne Fehlerabschnitt)
- **Farben-Themes:** Button „Hex kopieren“ (6 Farben in Zwischenablage)
- **Dokument-Tags:** Kontextmenü „Tags einfügen“ aus Zwischenablage
- **Export-Presets:** Summary kopieren (RMB · Ctrl+C)
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.7

Post-Release-Polish nach **2.5.6**:

- **OCR-Region:** Status-Mittelklick/Ctrl+Klick kopiert Ergebnis-Pfad (Tooltip mit Pfad)
- **Farben-Themes:** Combo-Tooltip mit 6 Hex-Farben · Custom-Zähler N/20
- **Dokument-Tags:** Kontextmenü „Tags kopieren“
- **Export-Presets:** Rechtsklick → Zielordner öffnen · Entf löschen
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.6

Post-Release-Polish nach **2.5.5**:

- **OCR-Region:** Status-Rechtsklick öffnet Ergebnis-Ordner (Linksklick → Tab)
- **Farben-Themes:** Custom duplizieren (Builtins geschützt)
- **Dokument-Tags:** Quick-Tag Sort A–Z ↔ Häufigkeit (persistiert)
- **Export-Presets:** Listen-Tooltip Summary · Apply A11y Announcement
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.5

Post-Release-Polish nach **2.5.4**:

- **OCR-Region:** Status-Klick fokussiert Ergebnis-Tab
- **Farben-Themes:** Custom umbenennen (Builtins geschützt)
- **Dokument-Tags:** Quick-Tag A–Z mit Doc-Anzahl (N)
- **Export-Presets:** ★ aktiv in Liste · Duplizieren
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.4

Post-Release-Polish nach **2.5.3**:

- **OCR-Region:** Wörter/Zeichen im Status · A11y Announcement nach Erfolg
- **Farben-Themes:** Custom löschen (Builtins geschützt) · ★ Default in Combo
- **Dokument-Tags:** Tag-Vorschläge (Recent/Index) · Quick-Tag-Filter Combo
- **Export-Presets:** Umbenennen · Doppelklick/Enter Anwenden
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.3

Post-Release-Polish nach **2.5.2**:

- **OCR-Region:** Tab-Titel Ellipsis + Tooltip voll · Fehlerabschnitt wie Batch-OCR
- **Farben-Themes:** Merge Kollision skip/rename (`_2`) · Import-Log
- **Dokument-Tags-Filter:** Esc → Fokus Liste · Trefferanzahl A11y
- **Export-Presets:** Live-Pfad-Vorschau · ungültige JSON-Einträge überspringen + zählen
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.2

Post-Release-Polish nach **2.5.1**:

- **OCR-Region:** Fortschritt (Schritte) · Ergebnis-Tab Titel mit Seite/Region · Fehler anhängen Toggle
- **Farben-Themes:** Schema `ildcolors-theme-v1` · ungültig klar DE · Import Merge vs Ersetzen
- **Dokument-Tags-Filter:** Trefferanzahl · Esc leert Filter · fehlende getaggte Recent grau
- **Export-Presets:** Duplikat-Namen ablehnen · Export/Import aller Presets JSON (`ildexportpresets-v1`)
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.1

Post-Release-Polish nach **2.5.0**:

- **OCR-Region:** DPI/Sprache aus Defaults · Abbruch Esc/Progress · Hinweis bei leerem Ergebnis
- **Farben-Themes:** Vorschau-Swatches · Als Default speichern · Import/Export JSON
- **Dokument-Tags:** Tag hinzufügen/entfernen am Recent · Filter Clear · Persistenz
- **Export-Presets:** benannte Presets max. 10 · Anwenden/Löschen · Live-Zusammenfassung
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.0

Minor-Bump nach **2.4.5**:

- **PDF-OCR-Region:** Rechteck wählen → nur Region OCR → Text-Tab
- **Annotation-Farben-Themes:** vordefinierte Paletten Markieren/Corporate laden
- **Dokument-Tags global:** `ildtags-v1` über Docs hinweg filterbar in Willkommen/Recent
- **Export-Preset:** letzte Export-Einstellungen (DPI/Format/Pfad) als Preset „Zuletzt“
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.4.5

Post-Release-Polish nach **2.4.4**:

- **Thumb Auto-Prune:** Toast Dauer OCR-Toast-Settings · Klick kopiert Status erneut
- **Annotation-Vorlagen:** Esc → „Apply abgebrochen“ + Vorlagenname · A11y Announcement
- **Sync-Scroll:** AccessibleName live bei Toggle (an/aus im Namen)
- **F1 Cheat-Sheet TXT:** Reset Default über gemeinsamen Helper (`template_reset`)
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.4.4

Post-Release-Polish nach **2.4.3**:

- **Thumb Auto-Prune:** Status kopierbar (Klick → Zwischenablage) · Toast optional Settings
- **Annotation-Vorlagen:** Esc → Status „Apply abgebrochen“ · Fokus Toolbar
- **Sync-Scroll:** Announcement bei Toggle · AccessibleName Status-Widget
- **F1 Cheat-Sheet TXT:** Reset Default Bestätigung nur bei Abweichung · Fokus+Selektion
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.4.3

Post-Release-Polish nach **2.4.2**:

- **Thumb Auto-Prune:** Log/Status „N Dateien / X MB entfernt“ · Settings Intervall oder on-write
- **Annotation-Vorlagen:** Quick-Apply Rechtsklick wählen · Esc bricht Apply-Modus ab
- **Sync-Scroll:** Tooltip zeigt Zustand an/aus · A11y AccessibleName/Description
- **F1 Cheat-Sheet TXT:** Live-Vorschau Dateiname · Quick-Insert `{date}` · Reset Default
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.4.2

Post-Release-Polish nach **2.4.1**:

- **Thumb-Cache:** Bestätigung · freigegebene MB in Status · Auto-Prune bei Limit
- **Annotation-Vorlagen:** Toolbar Quick-Apply ★ · zuletzt verwendet merken
- **Sync-Scroll:** Status-Klick toggled · Tooltip mit Shortcut
- **F1 Cheat-Sheet TXT:** Zielordner merken · Template `{date}_shortcuts.txt`
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.4.1

Post-Release-Polish nach **2.4.0**:

- **Thumb-Cache:** max MB Settings · „Cache leeren“ · Hit/Miss Status optional Debug
- **Annotation-Vorlagen:** Umbenennen/Löschen · Vorschau · Standard ★
- **Sync-Scroll:** Statusleisten-Indikator an/aus · nur PDF↔PDF
- **F1 Cheat-Sheet:** Suche/Filter · Drucken · Export TXT
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.4.0

Minor-Bump nach **2.3.5**:

- **PDF-Seiten-Thumbnail Disk-Cache:** mtime-invalidiert · spürbar bei großen Docs
- **Annotation-Templates:** Stempel/Highlight-Styles speichern/laden (**ildtmpl-v1**)
- **Split-View Sync-Scroll:** Toggle für zwei PDF-Tabs nebeneinander (Scroll + Seiten-Sync)
- **Tastatur-Cheat-Sheet:** F1 / Hilfe Dialog mit Shortcut-Liste DE
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.3.5

Post-Release-Polish nach **2.3.4**:

- **PDF-Kompression:** Toggle AccessibleName/Description · Status Ersparnis-% announced
- **URL-Links TXT:** Reset Default Bestätigung nur bei Abweichung · Fokus+Selektion
- **Command Palette:** Pin-ersetzen-Bestätigung mit Namen des zu ersetzenden Pins
- **Telemetrie-Stub:** „Stubs öffnen“ → Fokus erste Stub-Zeile · Dialog schließt · weiter no-op
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.3.4

Post-Release-Polish nach **2.3.3**:

- **PDF-Kompression:** Label klar „Ergebnis nach Kompression öffnen“ · A11y (AccessibleName/Description)
- **URL-Links TXT:** Live-Vorschau Dateiname · Quick-Insert `{stem}`/`{date}` · Reset Default
- **Command Palette:** Overflow-Hinweis bei Pin-Limit · Option ältesten Pin ersetzen
- **Telemetrie-Stub:** Esc schließt Info-Dialog · Button „Stubs öffnen“ · weiter no-op
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.3.3

Post-Release-Polish nach **2.3.2**:

- **PDF-Kompression:** Öffnen-Toggle Settings merken · Status mit Ersparnis-% auch bei Fehler
- **URL-Links TXT:** Template `{stem}_links.txt` · Zielordner merken · UTF-8-BOM Option
- **Command Palette:** Pin-Persistenz · Unpin · max Pins Settings 3/5/10
- **Telemetrie-Stub:** kurz warum Stub · Verweis Tab Stubs · weiter no-op
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.3.2

Post-Release-Polish nach **2.3.1**:

- **PDF-Kompression:** optional neues File öffnen · Größenersparnis-% in Status
- **URL-Links Sidebar:** Suche/Filter · Doppelklick springt zur Seite · Export URL-Liste TXT
- **Command Palette:** Pin häufige Befehle · Recent-Anzahl Settings 5/10/20
- **Telemetrie-Stub:** Toggle disabled bleibt · Info-Dialog warum Stub
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.3.1

Post-Release-Polish nach **2.3.0**:

- **PDF-Kompression:** Vorher/Nachher-Größenanzeige · Abbruch · DPI/Qualität-Presets (Bildschirm/E-Book/Druck)
- **URL-Links:** Live-Validierung · Hover-Tooltip · Sidebar-Liste · Bearbeiten/Löschen
- **Command Palette:** Fuzzy-Filter · letzte Befehle · Esc schließt · Kategorien
- **Telemetrie-Stub:** Settings-Warntext „keine Datenübertragung“ · bleibt no-op
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.3.0

Minor-Bump nach **2.2.5**:

- **PDF-Kompression/Downsample:** Qualitäts-Dialog · optional Bilder-Downsample (pypdfium2-Raster + pikepdf) → neues File
- **Link-Annotationen:** Rechteck + URI in Sidecar · Klick öffnet Browser · optional Bake als PDF-Link
- **Schnellaktionen-Palette:** Ctrl+K Command Palette (öffnen, suchen, OCR, export…)
- **Telemetrie-Stub:** Settings opt-in „anonym Nutzung melden“ Default aus · immer no-op
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.2.5

Post-Release-Polish nach **2.2.4**:

- **Seitenbeschriftungen:** TXT **Live-Vorschau Dateiname** · Quick-Insert **`{stem}`/`{date}`** · **Reset Default**
- **Ink/Freihand:** Toast-**Klick fokussiert Ink-Tool** · Announcement **wie OCR**
- **Dokument-Historie:** **Redo** nach Undo Clear · **klarer DE-Hinweis** wenn kein Undo möglich
- **CONTRIBUTING:** Sync-Zeile **Windows** · optional **`-NoStart`**
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert (Ink ≠ Stylus)

## Neu in 2.2.4

Post-Release-Polish nach **2.2.3**:

- **Seitenbeschriftungen:** TXT-Template **`{stem}_labels.txt`** · Zielordner merken · UTF-8-BOM Option
- **Ink/Freihand:** Status **„Glättung angewandt“** Toast-Dauer Settings · A11y Announcement
- **Dokument-Historie:** Clear-Zähler **„N Einträge entfernt“** · Undo Clear (Session) bzw. Hinweis
- **CONTRIBUTING:** Sync-Befehl als **eine Zeile copy-ready**
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert (Ink ≠ Stylus)

## Neu in 2.2.3

Post-Release-Polish nach **2.2.2**:

- **Seitenbeschriftungen:** Vorschau Scroll-Liste erste 20 · Export Labels als TXT
- **Ink/Freihand:** Undo-Glätten mit **Redo ok** · Status **„Glättung angewandt“**
- **Dokument-Historie:** Clear optional nur aktuellen Filter · Export gefilterte Sicht
- **CONTRIBUTING:** Exitcode-Tabelle kurz · Link zu [`scripts/smoke_ild.py`](scripts/smoke_ild.py)
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert (Ink ≠ Stylus)

## Neu in 2.2.2

Post-Release-Polish nach **2.2.1**:

- **Seitenbeschriftungen:** Range-Überlappungs-Validierung (DE) · Vorschau erste Labels
- **Ink/Freihand:** Glättungsstärke leicht/mittel/stark · Undo nach Glätten eigener Stack-Eintrag
- **Dokument-Historie:** Doppelklick springt zur Seite (wenn page im Eintrag) · Clear mit Bestätigung
- **CONTRIBUTING:** Sync-Einzeiler = sync-ild.ps1-Pfad · Smoke-Beispielkommando
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert (Ink ≠ Stylus)

## Neu in 2.2.1

Post-Release-Polish nach **2.2.0**:

- **Seitenbeschriftungen:** Range-Editor · Import aus PDF · Reset arabisch 1…
- **Ink/Freihand:** Strichstärke/Farbe · Löschen letzter Strich · Glätten optional leicht
- **Dokument-Historie:** Panel letzte 50 · Filter Aktionstyp · Export JSON
- **CI:** Workflow-Stub klar **manual only**; CONTRIBUTING Sync-Einzeiler
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert (Ink ≠ Stylus)

## Neu in 2.2.0

Minor-Bump nach **2.1.5**:

- **PDF-Seitenbeschriftungen:** benutzerdefinierte Labels (i, ii, 1…) Sidecar + Anzeige; optional PDF PageLabels (pikepdf)
- **Ink/Freihand:** Maus-Polyline-Annotation · Sidecar · Undo (kein Stylus)
- **Dokument-Historie:** `*.ildhist.json` Schema **ildhist-v1** mit Zeitstempeln
- **CI:** `smoke_ild` in CONTRIBUTING/Docs; optional GitHub-Actions-Workflow-Stub (nur lokal dokumentiert)
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Nightly-Smoke

```bat
python scripts\smoke_ild.py
python scripts\smoke_ild.py --qt
python scripts\smoke_ild.py --json
```

Siehe auch **CONTRIBUTING.md**. Workflow-Stub: `.github/workflows/smoke-ild.yml` (**manual only**, keine Cloud-CI-Pflicht).

Exit **0**/OK (`ok=true`) · **1**/Fehler (`ok=false`) · **2**/ungültige Option. `--json` liefert `ok`, `checks`, `duration_ms`, `version`; bei Fail enthält `checks[]` ein Objekt mit `error` (max 200 Zeichen, Overflow `…`).

Beispiel Erfolg:

```json
{"ok": true, "version": "2.3.5", "duration_ms": 1234, "checks": ["version", "imports", "cli", "measure_diff_import", "changelog"]}
```

Beispiel Fail:

```json
{"ok": false, "version": "2.3.5", "duration_ms": 12, "checks": ["version", {"name": "imports", "error": "import x: …"}]}
```

Ende (ohne `--json`): `Laufzeit: N ms` · `smoke_ild: OK`.

## Neu in 2.1.5

Post-Release-Polish nach **2.1.4**:

- **PDF-Kommentar-Import:** Status-Copy-Toast **Dauer OCR-Settings** · **Klick fokussiert Statusleiste/Log** falls vorhanden
- **Messung / Diff:** Reset Default über **gemeinsamen Helper** · **Esc im Feld verwirft Edit** (nicht speichern)
- **Nightly-Smoke:** Fail-`error` **max 200 Zeichen truncated mit …** · Docs Fail-Beispiel
- **FEATURES.md lokal sync** Hinweis (siehe Sync)
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.1.4

Post-Release-Polish nach **2.1.3**:

- **PDF-Kommentar-Import:** Status kopieren → **Clipboard + Toast + A11y Announcement**
- **Messung:** CSV-Template **Reset Default** · Bestätigung nur bei Abweichung · **Fokus+Selektion**
- **PDF-Vergleich:** Diff-TXT **Quick-Insert-Buttons** · **Reset Default** (Bestätigung≠Default · Fokus+Selektion)
- **Nightly-Smoke:** `smoke_ild.py --json` bei Fail **`checks[].error` Text** · **Exitcode spiegelt `ok`**
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.1.3

Post-Release-Polish nach **2.1.2**:

- **PDF-Kommentar-Import:** Status **ersetzt / übersprungen / neu** · **kopierbarer Text** (Status kopieren)
- **Messung:** CSV Live-Template **`{stem}_measures.csv`** · Quick-Insert `{stem}`/`{date}` · ungültige rot
- **PDF-Vergleich:** Diff-TXT Template **`{stemA}_vs_{stemB}_{mode}.txt`** · Live-Vorschau · ungültige rot
- **Nightly-Smoke:** `smoke_ild.py --json` Felder **`ok`**, **`checks[]`**, **`duration_ms`**, **`version`** · Beispiel in Docs
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.1.2

Post-Release-Polish nach **2.1.1**:

- **PDF-Kommentar-Import:** Toggle **Nach Import Sidecar speichern** · Status **„N importiert, M übersprungen“**
- **Messung:** CSV-Spalten **Typ,Seite,Wert,Einheit** · Zielordner merken · UTF-8-BOM Option
- **PDF-Vergleich:** Textlayer **Unified/Side-by-Side Toggle** · Diff-TXT **Dateiname-Template**
- **Nightly-Smoke:** `smoke_ild.py` **`--json` Summary** · **Laufzeit ms** · in Docs erwähnt
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.1.1

Post-Release-Polish nach **2.1.0**:

- **PDF-Kommentar-Import:** Dry-Run-Zähler · Duplikat-Strategie keep/skip/replace · Fortschritt/Abbruch
- **Messung:** Snap-to-Annotation optional · Labels persistent · Messwerte-CSV
- **PDF-Vergleich:** Textlayer Ignore-Whitespace · Nur-Unterschiede · Export Unified Diff TXT
- **Nightly-Smoke:** `smoke_ild.py` Exit 0/1/2 · `--qt`/`--skip-qt` · DE-Hilfe
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.1.0

Minor-Bump nach **2.0.5**:

- **PDF-Kommentar-Import:** native Markup (pikepdf) grob → Sidecar
- **Messung:** Fläche (Rechteck) + Winkel (zwei Linien); Anzeige **mm/px Toggle**
- **PDF-Vergleich:** Textlayer-Diff (Unified) im Diff-Panel
- **Nightly-Smoke:** `scripts/smoke_ild.py` CLI+Import-Checks
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.0.5

Post-Release-Polish nach **2.0.4** (Basis **2.0.3** / **2.0.2** / **2.0.1** / **2.0.0** / **1.9.5**):

- **Multi-Dokument-Suche:** Reset Default **Bestätigung nur bei Abweichung** · **Fokus+Selektion**
- **PDF-Portfolios:** Footer-Klick filtert **übersprungene** (Toggle) · **leerer Footer bei 0**
- **Accessibility:** HC-Toast **gleiche Announcement-Pipeline wie OCR-Toast**
- **Installer:** `install-ild.ps1` **-Quiet -Uninstall**: **Exit 0 auch wenn nichts zu entfernen** · **Kurz-Summary stdout**
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.0.4

Post-Release-Polish nach **2.0.3** (Basis **2.0.2** / **2.0.1** / **2.0.0** / **1.9.5**):

- **Multi-Dokument-Suche:** CSV-Template **Quick-Insert `{date}`/`{query}`** · **ungültige Platzhalter rot** · **Reset Default**
- **PDF-Portfolios:** Footer **„extrahiert X, übersprungen Y“** · Button **Ordner öffnen**
- **Accessibility:** HC-Toast **Dauer aus OCR-Toast-Settings** · **A11y Announcement**
- **Installer:** `install-ild.ps1` **-Uninstall**: **Log-Datei-Pfad** ausgeben · **-Quiet** unterdrückt Prompts
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.0.3

Post-Release-Polish nach **2.0.2** (Basis **2.0.1** / **2.0.0** / **1.9.5**):

- **Multi-Dokument-Suche:** CSV **Zielordner merken** · Live-Dateiname-Template **`{date}_multisearch.csv`**
- **PDF-Portfolios:** Extrakt **Abbruch** · **Teilergebnis behalten** · **Statuszählung**
- **Accessibility:** HC-Toast **„High-Contrast an/aus“** · UI-Skala Reset **Bestätigung nur bei ≠100 %**
- **Installer:** `install-ild.ps1` **-Uninstall**: fehlende Shortcuts **kein Fehler** · Log-Zeile
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.0.2

Post-Release-Polish nach **2.0.1** (Basis **2.0.0** / **1.9.5**):

- **Multi-Dokument-Suche:** CSV-Spalten **Doc,Seite,Snippet,Match** · **UTF-8 BOM** Option · **Regex-Fehlerstatus**
- **PDF-Portfolios:** Extrakt **Zielordner merken** · **Namenskollision umbenennen** · **Fortschritt**
- **Accessibility:** UI-Skala Button **Reset 100 %** · High-Contrast Shortcut **Ctrl+Alt+H**
- **Installer:** `install-ild.ps1` **-Uninstall** entfernt Shortcuts · Exit-Codes **0/1** dokumentiert
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.0.1

Post-Release-Polish nach **2.0.0** (Basis **1.9.5** / **1.9.4** / **1.9.3** / **1.9.2** / **1.9.1** / **1.9.0**):

- **Multi-Dokument-Suche:** Case / Whole-word / Regex · Treffer-CSV · Fortschritt bei vielen Docs
- **PDF-Portfolios:** Inhaltsliste Sidebar · Auswahl extrahieren · Hinweis bei leerer Collection
- **Accessibility:** High-Contrast Persistenz live · UI-Schrift Skala 100/125/150 % Live-Vorschau (Settings)
- **Installer:** `install-ild.ps1` `-NoDesktop` · Idempotenz · DE-Meldungen · sync-ild.ps1-Hinweis
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.0.0

Major-Release nach **1.9.5** (Basis **1.9.4** / **1.9.3** / **1.9.2** / **1.9.1** / **1.9.0**):

- **Multi-Dokument-Suche:** Volltext über alle offenen PDFs (Textlayer) · zentrale Trefferliste (Ctrl+Shift+F)
- **PDF-Portfolios:** mehrere Dateien → Container-PDF (pikepdf Attachments + `/Collection`) erstellen/öffnen/extrahieren
- **Accessibility:** Document Outline Vorlesen bleibt Stub; neu High-Contrast Theme Toggle + größere UI-Schrift (Settings)
- **Installer:** `scripts/install-ild.ps1` — Startmenü-Shortcut + optional Desktop-Link (User-Profil, ohne Admin)
- About zeigt Serie **„2.0“**; Stubs KI/Cloud/Stylus/3D/Plugin-Hooks unverändert klar markiert

## Neu in 1.9.5

Post-Release-Polish nach **1.9.4** (Basis **1.9.3** / **1.9.2** / **1.9.1** / **1.9.0**):

- **PDF-Anhänge:** Footer-Klick filtert Liste auf **umbenannt/übersprungen** (Toggle) · **leerer Footer wenn 0**
- **Quick-Stempel:** Esc → Fokus Toolbar · Shortcut **Ctrl+Shift+S** = Standard-Stempel ★
- **Tabellen-OCR → CSV:** Abbruch setzt **Trennzeichen-Combobox synchron** zurück · **A11y bei Speichern**
- **Settings-Seite „Stubs“:** Info-Dialog mit **Kurzbeschreibung** + Badge **„Geplant“** · **Esc schließt**
- Stubs klar als Stub / nicht produktiv markiert

## Neu in 1.9.4

Post-Release-Polish nach **1.9.3** (Basis **1.9.2** / **1.9.1** / **1.9.0**):

- **PDF-Anhänge:** Footer **„hinzugefügt X, umbenannt Y, übersprungen Z“** · **kopierbar**
- **Quick-Stempel:** Esc → **„Platzieren abgebrochen“** · **Zoom/Opacity** wie Signatur merken
- **Tabellen-OCR → CSV:** Live-Trennzeichen **Persistenz erst Speichern** · **Vorschau-Reset bei Abbruch**
- **Settings-Seite „Stubs“:** FEATURES fehlt → **Statushinweis** · **Doppelklick Stub = Info-Dialog**
- Stubs klar als Stub / nicht produktiv markiert

## Neu in 1.9.3

Post-Release-Polish nach **1.9.2** (Basis **1.9.1** / **1.9.0**):

- **PDF-Anhänge:** Duplikat-Dialog **„Für alle anwenden“** · Statuszählung am Ende
- **Quick-Stempel:** Rechtsklick Bibliothek wählen · **Esc** bricht Platzieren ab
- **Tabellen-OCR → CSV:** Zeilen/Spalten-Zähler · Trennzeichen live in Vorschau
- **Settings-Seite „Stubs“:** Link zu FEATURES.md · „keine Aktion“ klar · Sortierung A–Z
- Stubs klar als Stub / nicht produktiv markiert

## Neu in 1.9.2

Post-Release-Polish nach **1.9.1** (Basis **1.9.0**):

- **PDF-Anhänge:** Mehrfach-Drag&Drop · Duplikat-Namen Warnung + Umbenennen
- **Quick-Stempel:** Toolbar-Button · zuletzt verwendet merken (Fallback Standard ★)
- **Tabellen-OCR → CSV:** Vorschau erste 5 Zeilen vor Speichern · Abbruch möglich
- **Settings-Seite „Stubs“:** KI / Cloud / Stylus / 3D / Plugin-Hooks mit Status
- Stubs klar als Stub / nicht produktiv markiert

## Neu in 1.9.1

Post-Release-Polish nach **1.9.0** (Basis **1.8.5**):

- **PDF-Anhänge:** Spalten Größe/Typ · Doppelklick extrahieren · Drag&Drop hinzufügen
- **Stempel-Bildbibliothek:** Umbenennen/Löschen · Vorschau · Standard-Stempel ★
- **Tabellen-OCR → CSV:** Trennzeichen `;`/`,`/Tab · Zielordner merken · UTF-8-BOM Option
- **Plugin-Hooks Stub:** About „nicht produktiv“ · Event-Namen in Docs
- Stubs KI/Cloud/Stylus/3D + Plugin-Hooks klar als Stub / nicht produktiv

## Neu in 1.9.0

Minor-Release nach **1.8.5** (Basis **1.8.4** / **1.8.3** / **1.8.2**):

- **PDF-Anhänge:** listen / extrahieren / **hinzufügen** (pikepdf; Entfernen im Dialog)
- **Stempel-Bildbibliothek:** eigene Bilder unter `config/stamps/` · Sidecar-Stempel aus Bibliothek
- **Tabellen-OCR → CSV:** grobe Tabellenerkennung → CSV (UTF-8 BOM, `;`)
- **Plugin-Hooks Stub:** interner Event-Bus + no-op Loader (kein Plugin-System)
- Stubs KI/Cloud/Stylus/3D unverändert; Plugin-Hooks zusätzlich als Stub
