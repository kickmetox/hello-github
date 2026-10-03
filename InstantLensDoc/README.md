# InstantLens Doc

Moderne Textverarbeitung mit PDF-Annotator, OCR-Bridge und Formulargenerator.

**Version:** 1.2.0  
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

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

Installer: `.\installer\build-installer.ps1` (optional `-NoKeygen`)  
Desktop-Verknüpfung: optionale Checkbox (`desktopicon`, Standard an).

## Neu in 1.2.0

PDF-Split: Seitenbereiche `1-3,5,8-10` → neue Datei(en); Annotation-Export Seite/Dokument als JSON (ildann-v4) + optional Flatten-PDF; Text-Diff Panel für zwei offene Text-Tabs; `run.bat` prüft Python/Deps mit DE-Meldungen. Stubs KI/Cloud/Stylus/3D unverändert.

Siehe [CHANGELOG.md](CHANGELOG.md), [FEATURES.md](FEATURES.md) und [INFO.md](INFO.md).
