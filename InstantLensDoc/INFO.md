# InstantLens Doc — Info

| | |
|---|---|
| Produkt | InstantLens Doc |
| Version | 0.1.3 |
| Hersteller | Andreas Meyer |
| Kontakt | ame@sellerbach.de |
| Plattform | Windows-first (Python 3.12 + PySide6), Linux/macOS lauffähig |
| PDF | pypdfium2 / PDFium — **kein** Poppler/GPL im Standard |
| Zielordner | `D:\AI_Temp\InstantLensDoc` |

## Lizenzmodell

1. **Trial:** 28 Tage (4 Wochen) ab erstem Start, voll nutzbar  
2. **Key:** Format `ILD1.<payload>.<sig>`, Laufzeit **32 Tage (30+2)** ab Ausstellung  
3. Nach Ablauf: neuen Key per Mail an **ame@sellerbach.de** anfordern  
4. Keygenerator: `run-keygen.bat` oder `python -m keygen --gui` (separates Extra)

Lizenzdaten lokal unter `%APPDATA%\InstantLensDoc\license.json` (Windows) bzw. `~/.config/InstantLensDoc/`.

## Icon

Die App sucht automatisch (Reihenfolge): `assets/app.ico`, `assets/icon.png`, JPG-Varianten, CWD, `D:\AI_Temp\InstantLensDoc`.  
Eigenes Icon dort ablegen — Sync-Skript überschreibt vorhandene Nutzer-Icons nicht.

## OCR

Optional. `pip install pytesseract` + Tesseract-OCR Runtime (`winget install UB-Mannheim.TesseractOCR`).  
Sprach-Presets in der UI; Modi: editierbarer Text oder durchsuchbares Bild (PDF + Sidecar).  
Fehlt die Runtime, zeigt Extras → OCR eine klare Installationsanleitung.

## Neu in 0.1.3

- Text-Overlay-Editor (Sidecar v3) + optional Einbrennen  
- Formen (Rechteck/Linie/Pfeil) + Lineal/Messung  
- Editor-Export HTML/DOCX/PDF  
- Installer: Desktop- und Startmenü-Hinweise  
- `examples/ild_pdf_demo.py` + erweiterte API-Doku  

## Build (Windows, eine Zeile)

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

Erzeugt per PyInstaller `dist/InstantLensDoc/` und `dist/InstantLensKeygen/`. Optional Inno: `installer/build-installer.ps1`.

## Sync (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File "D:\AI_Temp\sync-ild.ps1"
```

## Auskoppelbares PDF-Modul

Siehe `ild_pdf/README.md` und `examples/ild_pdf_demo.py`.
