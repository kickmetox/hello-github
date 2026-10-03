# InstantLens Doc — Kurzinfo

| | |
|---|---|
| Produkt | InstantLens Doc |
| Version | **1.1.9** |
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
- Resttage Statusleiste + About **konsistent** („noch X Tage“ / „noch 1 Tag“)  
- Ablaufdatum **TT.MM.JJJJ** in About + Status (+ Lizenzdialog)  
- Warnung **≤3 Tage** vor Ablauf: Banner (nicht modal); **Klick → About/Aktivierung**  
- Banner: **Icon** + **Dismiss** + **Schließen-X**; Persistenz **`dismiss_date`** (bis morgen)  
- Banner: **Esc** schließt; **AccessibleName** für Screenreader  
- Banner: **Fokus-Ring** sichtbar; **Enter** öffnet Aktivierung  
- Banner-Text **i18n** (DE); Farbe **Warnung** (gelb) vs. **abgelaufen** (rot)  
- Lizenz-Dialog: Resttage + Ablaufdatum klar  
- About: Version, **Lizenzstatus**, Kontakt, Changelog-Kurzliste; bei Trial/ungültig **Lizenz aktivieren…**; **Privacy: lokal, keine Telemetrie**

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

## Neu in 1.1.9

- OCR-Defaults-Toast: Dauer in Settings **1/2/3 s** + **Accessibility-Announcement**
- Merge: Settings-Checkbox **Readonly schließen** mit **demselben Persistenz-Tooltip** wie Merge-Dialog
- Ann. Sticky-Status: Clear zusätzlich bei Annotationen-**Undo/Redo**
- Keygen-Countdown pausiert: Tooltip **„Countdown pausiert (Fenster ohne Fokus)“**
- Stubs KI/Cloud/Stylus/3D unverändert
