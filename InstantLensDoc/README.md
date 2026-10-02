# InstantLens Doc

Moderne Textverarbeitung mit PDF-Annotator, OCR-Bridge und Formulargenerator.

**Version:** 0.3.6  
**Hersteller:** Andreas Meyer · ame@sellerbach.de

## Quickstart (Windows)

Eine Sync-Zeile (Branch → `D:\AI_Temp\InstantLensDoc`, pip, Start):

```powershell
powershell -ExecutionPolicy Bypass -File "D:\AI_Temp\sync-ild.ps1"
```

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

## Neu in 0.3.6

PDF-Raster-Export mit DPI 72/150/300, Annotation Select-All auf Seite (Ctrl+A), Editor Kommentar/Unkommentar (Ctrl+/ für # //), Fenster-Geometrie speichern/wiederherstellen. Stubs KI/Cloud/Stylus/3D unverändert.


Siehe [CHANGELOG.md](CHANGELOG.md), [FEATURES.md](FEATURES.md) und [INFO.md](INFO.md).
