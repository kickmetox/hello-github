# InstantLens Doc

Moderne Textverarbeitung mit PDF-Annotator, OCR-Bridge und Formulargenerator.

**Version:** 2.3.4  
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

Installer: `.\installer\build-installer.ps1` (optional `-NoKeygen`)  
Desktop-Verknüpfung: optionale Checkbox (`desktopicon`, Standard an).  
User-Shortcuts: `.\scripts\install-ild.ps1` · Deinstallieren: `-Uninstall [-Quiet]` (Exit **0**/OK · **1**/Fehler; Quiet: Kurz-Summary, Exit 0 auch ohne Shortcuts).

Nightly-Smoke: `python scripts\smoke_ild.py` · optional `--qt` · `--json` (Summary: `ok`, `checks[]`, `duration_ms`, `version`; Fail: `checks[].error` max 200…, Exit=ok). Siehe **CONTRIBUTING.md**; Workflow-Stub `.github/workflows/smoke-ild.yml` (manual only).

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
