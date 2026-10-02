# InstantLens Doc — Kurzinfo

| | |
|---|---|
| Produkt | InstantLens Doc |
| Version | 0.2.3 |
| Hersteller | Andreas Meyer |
| Kontakt | ame@sellerbach.de |
| PDF | pypdfium2 / PDFium |
| GUI | Python 3.12 + PySide6 |

## Lizenz

- Trial: **28 Tage** ab Erststart  
- Keys: **32 Tage (30+2)**, Format `ILD1.…`  
- Neu anfordern: **ame@sellerbach.de**

## Quickstart (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File "D:\AI_Temp\sync-ild.ps1"
```

Oder: `cd D:\AI_Temp\InstantLensDoc` → `run.bat`

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

Installer: `.\installer\build-installer.ps1` (optional `-NoKeygen`)

## Neu in 0.2.3

- PDF-Seiten als PNG/JPEG (aktuell / alle Seiten)  
- Annotation löschen (Auswahl / letzte); Entf  
- Statusleiste: Dateiname, Seite x/y, Zoom %  
- Thumbnail-Drag-Reorder  
- Stubs KI/Cloud/Stylus/3D unverändert  

Details: [CHANGELOG.md](CHANGELOG.md)
