# InstantLens Doc

Moderne Textverarbeitung mit PDF-Annotator, OCR-Bridge und Formulargenerator.

**Version:** 1.2.2  
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
(`run.bat` kann fehlende Deps optional per J/N oder non-interactive mit **`run.bat --yes`** / **`-y`** nachziehen. Exit **0**/OK · **1**/Fehler.)

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

Installer: `.\installer\build-installer.ps1` (optional `-NoKeygen`)  
Desktop-Verknüpfung: optionale Checkbox (`desktopicon`, Standard an).

## Neu in 1.2.2

PDF-Split: optional erzeugte Dateien in Tabs öffnen + Pfad-Log; Ann.-Export-Template mit `{page}`/`{date}` + Live-Vorschau; Text-Diff Side-by-Side/Unified + Wort-Highlight; `run.bat --yes` non-interactive pip inkl. Exit-Codes. Stubs KI/Cloud/Stylus/3D unverändert.

Siehe [CHANGELOG.md](CHANGELOG.md), [FEATURES.md](FEATURES.md) und [INFO.md](INFO.md).
