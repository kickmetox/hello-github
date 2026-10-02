# InstantLens Doc — Info

| | |
|---|---|
| Produkt | InstantLens Doc |
| Version | 0.1.0 |
| Hersteller | Andreas Meyer |
| Kontakt | ame@sellerbach.de |
| Plattform | Windows-first (Python 3.12 + PySide6), Linux/macOS lauffähig |
| PDF | pypdfium2 / PDFium — **kein** Poppler/GPL im Standard |
| Zielordner | `D:\AI_Temp\InstantLensDoc` |

## Lizenzmodell

1. **Trial:** 28 Tage (4 Wochen) ab erstem Start, voll nutzbar  
2. **Key:** Format `ILD1.<payload>.<sig>`, Laufzeit **32 Tage (30+2)** ab Ausstellung  
3. Nach Ablauf: neuen Key per Mail an **ame@sellerbach.de** anfordern  
4. Keygenerator: separates Programm (`python -m keygen`) — nicht in der Endnutzer-Distribution zwingend mitliefern  

Lizenzdaten lokal unter `%APPDATA%\InstantLensDoc\license.json` (Windows) bzw. `~/.config/InstantLensDoc/`.

## Icon

Bitte `app.ico` aus dem Nutzerordner nach `assets/app.ico` kopieren (siehe README).

## OCR

Optional. `pip install pytesseract` + Tesseract-OCR Runtime. Fehlt die Runtime, zeigt die App einen klaren Hinweis.

## Auskoppelbares PDF-Modul

Siehe `ild_pdf/README.md` — andere Apps können Rendern, Annotationen und Seitenoperationen ohne Poppler nutzen.
