# InstantLens Doc — Kurzinfo

| | |
|---|---|
| Produkt | InstantLens Doc |
| Version | **0.9.6** |
| Hersteller | Andreas Meyer |
| Kontakt | ame@sellerbach.de |
| PDF | pypdfium2 / PDFium |
| Code | `/workspace/InstantLensDoc/` → Ziel `D:\AI_Temp\InstantLensDoc` |
| Branch | `cursor/instantlensdoc-2108` · [PR #3](https://github.com/kickmetox/hello-github/pull/3) |
| GUI | Python 3.12 + PySide6 |

## Lizenz

- Trial: **28 Tage** ab Erststart  
- Keys: **32 Tage (30+2)**, Format `ILD1.…`  
- Neu anfordern: **ame@sellerbach.de**  
- Statusleiste: bei **<7 Tagen** Restlaufzeit prominent hervorgehoben  
- Lizenz-Dialog: Resttage + Ablaufdatum klar  
- About: bei Trial zusätzlicher Keygen-Hinweis; **Privacy: lokal, keine Telemetrie**

## Sync (eine Zeile)

```powershell
powershell -ExecutionPolicy Bypass -File "D:\AI_Temp\sync-ild.ps1"
```

Skript: [sync-ild.ps1](scripts/sync-ild.ps1) — Branch `cursor/instantlensdoc-2108` (oder `-LocalPack` / Pack-Zip) nach `D:\AI_Temp\InstantLensDoc`, pip, Start. **Nutzer-Icon in `assets` wird nicht überschrieben.**

Ohne Start: `-SkipStart` (Alias `-NoStart`). Exit-Codes: **0** OK · **1** allgemein · **2** Git-Fehler.

Fallback bei Git-Fehler:
```powershell
powershell -ExecutionPolicy Bypass -File "D:\AI_Temp\sync-ild.ps1" -LocalPack D:\AI_Temp\InstantLensDoc-pack.zip -SkipStart
```

## Start (manuell)

```bat
cd D:\AI_Temp\InstantLensDoc
pip install -r requirements.txt
run.bat
```

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

Installer: `.\installer\build-installer.ps1` (optional `-NoKeygen`)  
Desktop-Verknüpfung: optionale Checkbox (`desktopicon`, Standard an / `checkedonce`)

## Neu in 0.9.6

- Dokument-Tabs: **Dirty-Indikator (*)** bei ungespeicherten Änderungen; **Autosave-Toggle** in Einstellungen
- PDF-Suche: Treffer der aktuellen Seite als **Highlight-Annotationen** (Batch, Button HL / Menü)
- Annotationen: Color-Presets **Rechtsklick speichern/zurücksetzen**; User-Presets in Settings
- Session: Suchfilter **Aa / Wort / Regex** speichern/wiederherstellen
- Stubs KI/Cloud/Stylus/3D unverändert
