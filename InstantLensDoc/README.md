# InstantLens Doc

Moderne Textverarbeitung mit PDF-Annotator, Layout-Basics, OCR-Bridge und Formulargenerator.

**Hersteller:** Andreas Meyer · ame@sellerbach.de  
**PDF-Engine:** pypdfium2 / PDFium (lizenzfreundlich — **kein** Poppler/GPL als Standard)

## Zielordner (Windows)

```
D:\AI_Temp\InstantLensDoc
```

Dieses Repo nach dorthin kopieren. Icon liegt im Nutzerordner — bitte nach `assets/app.ico` (optional auch `assets/icon.png`) übernehmen:

```powershell
Copy-Item "D:\AI_Temp\InstantLensDoc\app.ico" ".\assets\app.ico" -ErrorAction SilentlyContinue
# bzw. falls Icon schon im Zielordner-Root liegt, vor dem Überschreiben sichern
```

Platzhalter: `assets/README-ICON.txt`.

## Start

```bat
cd D:\AI_Temp\InstantLensDoc
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
run.bat
```

oder:

```powershell
.\run.ps1
```

```bash
# Linux/macOS
pip install -r requirements.txt
python -m instantlensdoc
```

## Keygenerator

```bash
python -m keygen kunde@example.com
python -m keygen --gui
```

- Ohne Key: **4 Wochen** Trial ab Erststart  
- Keys: **30+2 Tage** gültig, danach neu per Mail an **ame@sellerbach.de**

## Module

| Pfad | Zweck |
|------|--------|
| `instantlensdoc/` | Desktop-App (PySide6) |
| `ild_pdf/` | Auskoppelbares PDF-Modul (siehe `ild_pdf/README.md`) |
| `keygen/` | Separater Keygenerator |
| `FEATURES.md` / `INFO.md` | Feature-Status & Produktinfo |
| `installer/instantlensdoc.iss` | Inno-Setup-Vorlage |

## Lizenzlaufzeit

Lokal verifizierbarer HMAC-Key (`ILD1.…`). Details in `INFO.md`.
