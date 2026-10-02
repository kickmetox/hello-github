# InstantLens Doc — Kurzinfo

| | |
|---|---|
| Produkt | InstantLens Doc |
| Version | 0.3.2 |
| Hersteller | Andreas Meyer |
| Kontakt | ame@sellerbach.de |
| PDF | pypdfium2 / PDFium |
| GUI | Python 3.12 + PySide6 |

## Lizenz

- Trial: **28 Tage** ab Erststart  
- Keys: **32 Tage (30+2)**, Format `ILD1.…`  
- Neu anfordern: **ame@sellerbach.de**  
- Statusleiste: bei **<7 Tagen** Restlaufzeit prominent hervorgehoben

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

## Neu in 0.3.2

- PDF-Anhänge auflisten/extrahieren (wenn vorhanden)
- Annotation-Layer ein-/ausblenden
- Editor: Markdown-Vorschau Split (optional)
- Zuletzt verwendete Ordner in Datei-Dialogen
- Stubs KI/Cloud/Stylus/3D unverändert
