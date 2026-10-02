# InstantLens Doc — Kurzinfo

| | |
|---|---|
| Produkt | InstantLens Doc |
| Version | **0.6.1** |
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
- About: bei Trial zusätzlicher Keygen-Hinweis; **Privacy: lokal, keine Telemetrie**

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
Installer-Task: optionale **Desktop-Verknüpfung** (Checkbox, Standard an / `checkedonce`)

## Neu in 0.6.1

- PDF-Text aus Auswahl in Zwischenablage (Auswahl-Werkzeug + Ctrl+C)
- Annotation-Suche: Tag-Autocomplete
- Session-Tabs: Dokumentliste per Drag neu ordnen → Reihenfolge speichern
- Installer: Desktop-Shortcut-Checkbox dokumentiert/geprüft
- Stubs KI/Cloud/Stylus/3D unverändert
