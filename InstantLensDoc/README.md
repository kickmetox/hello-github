# InstantLens Doc

Moderne Textverarbeitung mit PDF-Annotator, Layout-Basics, OCR-Bridge und Formulargenerator.

**Hersteller:** Andreas Meyer · ame@sellerbach.de  
**Version:** 0.1.4  
**PDF-Engine:** pypdfium2 / PDFium (lizenzfreundlich — **kein** Poppler/GPL als Standard)

## Zielordner (Windows)

```
D:\AI_Temp\InstantLensDoc
```

## Start

```bat
cd D:\AI_Temp\InstantLensDoc
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
run.bat
```

```powershell
.\run.ps1
```

```bash
# Linux/macOS
pip install -r requirements.txt
python -m instantlensdoc
```

## Keygenerator

```bat
run-keygen.bat
```

```bash
python -m keygen kunde@example.com
python -m keygen --gui
```

- Ohne Key: **4 Wochen** Trial ab Erststart  
- Keys: **30+2 Tage** gültig, danach neu per Mail an **ame@sellerbach.de**

## Icon

`assets/app.ico` / `assets/icon.png` (auch JPG). Die App löst Pfade robust auf (assets, CWD, Zielordner).

## Build Windows (App + Keygen)

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

## Installer (Inno Setup 6)

```powershell
powershell -ExecutionPolicy Bypass -File .\installer\build-installer.ps1
```

## Module

| Pfad | Zweck |
|------|--------|
| `instantlensdoc/` | Desktop-App (PySide6) |
| `ild_pdf/` | Auskoppelbares PDF-Modul |
| `examples/ild_pdf_demo.py` | API-Beispiel für andere Programme |
| `keygen/` | Separater Keygenerator |
| `build-windows.ps1` | PyInstaller App + Keygen |
| `run-keygen.bat` | Keygen-Start Windows |
| `FEATURES.md` / `INFO.md` | Feature-Status & Produktinfo |
| `installer/` | Inno `.iss` + `build-installer.ps1` |

## Smoke-Test

```bash
python scripts/smoke_test.py
```
