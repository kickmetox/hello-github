# README.md — Abschnitt PDF (Windows)

## PDF unter Windows (ohne Poppler)

ScanTuxio nutzt **pypdfium2** (PDFium) zum Rendern von PDF-Seiten.

```powershell
pip install pypdfium2 pillow
```

Frozen-Build muss pypdfium2 inkl. nativer DLL sammeln
(`--collect-all pypdfium2`). Der Windows-Installer (`installer\scantuxio.iss`)
liefert **keine** Poppler-GPL-Binaries.

Code: `from pdf_render import convert_from_path` statt `pdf2image`.
