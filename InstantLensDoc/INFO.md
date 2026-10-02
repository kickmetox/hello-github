# InstantLens Doc — Kurzinfo

| | |
|---|---|
| Produkt | InstantLens Doc |
| Version | 0.1.7 |
| Hersteller | Andreas Meyer |
| Kontakt | ame@sellerbach.de |
| PDF | pypdfium2 / PDFium |
| GUI | Python 3.12 + PySide6 |

## Lizenz

- Trial: **28 Tage** ab Erststart  
- Keys: **32 Tage (30+2)**, Format `ILD1.…`  
- Neu anfordern: **ame@sellerbach.de**

## Start

```bat
pip install -r requirements.txt
run.bat
```

## Sync (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File "D:\AI_Temp\sync-ild.ps1"
```

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

## Neu in 0.1.7

- **PDF-Wasserzeichen** + **Seitennummer-Stempel**  
- **PDF-Vergleich** Seite-nebeneinander  
- **Clipboard-Paste** Bild → Editor / PDF (Stempel oder neue Seite)  
- **Session-Restore** offener Dokumente (Sidebar-Tabs)  
- Bessere Fehlerbehandlung **große PDFs** (Warnung/Limits)  
- **Zoom-Performance** (Debounce + Render-Cache)  
- Stubs: KI / Cloud / Stylus / 3D (0.1.7)

## Neu in 0.1.6

- **Batch-Konvertierung** (Ordner → PDF / OCR)  
- **PDF zusammenführen & teilen** (Dialog)  
- **Lesezeichen / Outline** in der Seitenleiste  
- **Volltextsuche** über alle geöffneten Dokumente  
- **Einstellungen** (OCR-Sprache, Theme, Pfade)  
- PyInstaller-Icon aus `assets/app.ico`  

## Neu in 0.1.5

- PDF Signaturfeld + Signatur (Bild einfügen)  
- OCR Tabellen-Export (Heuristik)  
- Dark/Light Theme, Autosave, Drag-Drop  
- Tesseract-Install-Hinweis mit Link  

## Neu in 0.1.4

- Undo/Redo für Annotationen und Overlay-Text  
- Zoom: Seite/Breite einpassen + Shortcuts  
- Zuletzt geöffnete Dateien (Menü + Sidebar)  
- Drucken (Qt) für Editor und PDF-Seite  
- Klarerer Lizenz-Status; About 0.1.4  
