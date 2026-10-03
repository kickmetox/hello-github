# InstantLens Doc

Moderne Textverarbeitung mit PDF-Annotator, OCR-Bridge und Formulargenerator.

**Version:** 1.8.2  
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

## Neu in 1.8.2

Post-Release-Polish nach **1.8.1**: Batch Spiegel H/V remappt Ann.-Koordinaten · Undo-Text „N Seiten gedreht/gespiegelt“; Kopf-/Fußzeile Vorschau-Zoom · „Auf alle anwenden“ vs. Seitenbereich klar getrennt; Layer-Zähler-Klick filtert Ann.-Liste · „Alle ein“/„Alle aus“; Crash-Recovery Snapshot-Alter · „Als Kopie öffnen“. Stubs KI/Cloud/Stylus/3D unverändert.

Siehe [CHANGELOG.md](CHANGELOG.md), [FEATURES.md](FEATURES.md) und [INFO.md](INFO.md).
