# InstantLens Doc — Kurzinfo

| | |
|---|---|
| Produkt | InstantLens Doc |
| Version | 0.2.0 |
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

## Neu in 0.2.0

- **Release-Meilenstein**: Version überall 0.2.0  
- **Installer** gehärtet (Icon, Desktop-Shortcut, Uninstaller, Keygen optional)  
- **CHANGELOG** 0.1.x → 0.2.0  
- **Smoke** Kernpfade open / annotate / export / license  
- Stabilität: fehlende Dateien klar gemeldet; Stubs ohne Fake-KI/Cloud  

Details: [CHANGELOG.md](CHANGELOG.md)

## Aus 0.1.x (Auswahl)

- Metadaten, Seitengröße/Crop, Export-Qualität, i18n DE/EN, Update-Check  
- Redaction, Passwort, Kompression, Thumbnails, Logging  
- Wasserzeichen, Vergleich, Session, Undo/Redo, Zoom, Recent, Druck  
- Batch, merge/split, Outline, Volltext, Einstellungen  
- Annotationen, Overlay, Formen, OCR-Bridge, Formulare, Lizenz/Keygen  
