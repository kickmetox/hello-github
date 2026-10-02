# InstantLens Doc — Kurzinfo

| | |
|---|---|
| Produkt | InstantLens Doc |
| Version | 0.3.9 |
| Hersteller | Andreas Meyer |
| Kontakt | ame@sellerbach.de |
| PDF | pypdfium2 / PDFium |
| GUI | Python 3.12 + PySide6 |

## Lizenz

- Trial: **28 Tage** ab Erststart  
- Keys: **32 Tage (30+2)**, Format `ILD1.…`  
- Neu anfordern: **ame@sellerbach.de**  
- Statusleiste: bei **<7 Tagen** Restlaufzeit prominent hervorgehoben  
- Lizenz-Dialog: Resttage + Ablaufdatum klar

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

## Neu in 0.3.9

- PDF: Höhe einpassen (Ctrl+8) / Breite (Ctrl+9)
- Annotation-Statistik je Typ im Sidebar-Footer
- Editor: Sonderzeichen anzeigen (Toggle)
- Tray-Tooltip mit Version; Update-Hinweis nur bei erlaubter Einstellung
- Stubs KI/Cloud/Stylus/3D unverändert
