# InstantLens Doc

Moderne Textverarbeitung mit PDF-Annotator, OCR-Bridge und Formulargenerator.

**Version:** 2.0.4  
**Hersteller:** Andreas Meyer · ame@sellerbach.de

## Quickstart (Windows)

Eine Sync-Zeile (Branch → `D:\AI_Temp\InstantLensDoc`, pip, Start):

```powershell
powershell -ExecutionPolicy Bypass -File "D:\AI_Temp\sync-ild.ps1"
```

Ohne Start: `…\sync-ild.ps1 -SkipStart` (Exit **0**/OK, **1**/Fehler, **2**/Git).

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
User-Shortcuts: `.\scripts\install-ild.ps1` · Deinstallieren: `-Uninstall [-Quiet]` (Exit **0**/OK · **1**/Fehler; Log-Pfad wird ausgegeben).

## Neu in 2.0.4

Post-Release-Polish nach **2.0.3**: Multi-Doc CSV Template **Quick-Insert `{date}`/`{query}` · ungültige rot · Reset Default**; Portfolio Extrakt Footer **„extrahiert X, übersprungen Y“ · Ordner öffnen**; HC-Toast **Dauer OCR-Settings · A11y Announcement**; **install-ild.ps1 -Uninstall** Log-Pfad + **-Quiet**. Stubs unverändert.

## Neu in 2.0.3

Post-Release-Polish nach **2.0.2**: Multi-Doc CSV **Zielordner · Live-Template `{date}_multisearch.csv`**; Portfolio Extrakt **Abbruch · Teilergebnis · Statuszählung**; HC-Toast **an/aus**; UI-Reset **Bestätigung nur ≠100**; **install-ild.ps1** fehlende Shortcuts kein Fehler. Stubs unverändert.

## Neu in 2.0.1

Post-Release-Polish nach **2.0.0**: Multi-Doc **Aa/Wort/Regex · CSV · Fortschritt**; Portfolio **Sidebar · Auswahl · leere Collection**; High-Contrast **Persistenz**; UI-Schrift **100/125/150 % Live-Vorschau**; **install-ild.ps1** `-NoDesktop` / Idempotenz / sync-Hinweis. Stubs unverändert.

## Neu in 2.0.0

Major-Release nach **1.9.5** (Basis **1.9.4** / **1.9.3** / **1.9.2** / **1.9.1** / **1.9.0** / **1.8.5**): **Multi-Dokument-Suche** (Volltext Textlayer aller offenen PDFs · zentrale Trefferliste); **PDF-Portfolios** (pikepdf Collection/Attachments erstellen/öffnen); **Accessibility** High-Contrast Theme + größere UI-Schrift (Outline-Vorlesen bleibt Stub); **install-ild.ps1** Startmenü + optional Desktop (ohne Admin). Stubs KI/Cloud/Stylus/3D/Plugin-Hooks unverändert klar markiert.

Siehe [CHANGELOG.md](CHANGELOG.md), [FEATURES.md](FEATURES.md) und [INFO.md](INFO.md).
