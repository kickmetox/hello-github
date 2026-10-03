# InstantLens Doc — Kurzinfo

| | |
|---|---|
| Produkt | InstantLens Doc |
| Version | **0.7.6** |
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

Ohne App-Start: `…\sync-ild.ps1 -SkipStart`  
Exit-Codes: **0** OK · **1** allgemein · **2** Git-Fehler  

Oder: `cd D:\AI_Temp\InstantLensDoc` → `run.bat`

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

Installer: `.\installer\build-installer.ps1` (optional `-NoKeygen`)  
Installer-Task: optionale **Desktop-Verknüpfung** (Checkbox, Standard an / `checkedonce`)

## Neu in 0.7.6

- Treffer-Snippet: **Ellipsis-Style** «…» / … in Einstellungen
- Ann.-Merge-Vorschau: **Diff-Kurztext** der beiden Annotationen
- Vorlagen-Zip-Import: **Konflikt-Dialog** (Überschreiben / Überspringen / Abbrechen)
- Pending Sidecar-Debounce: kurzer **Statusleisten-Blink**
- Stubs KI/Cloud/Stylus/3D unverändert
