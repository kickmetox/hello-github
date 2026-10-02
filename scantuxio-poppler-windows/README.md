# ScanTuxio — PDF Windows (lizenzfreundlich: pypdfium2)

Standard: **pypdfium2 / PDFium** (Apache/BSD-ähnlich).  
**Kein Poppler-GPL-Bundle** im Installer.

## Grenzen dieses Pakets

- `D:\AI_Temp\ScanTuxio Win` und Upload-Inhalte waren in der Cloud-VM nicht verfügbar.
- Frozen `ScanTuxio.exe` muss **lokal neu gebaut** werden, damit pypdfium2 drin ist.
- Bis dahin: Dev mit `pip install -r patches/requirements-pdfium.txt` + Entry-Snippet.

## Dev

```powershell
pip install -r .\scantuxio-poppler-windows\patches\requirements-pdfium.txt
# Entry: patches\ENTRY_SNIPPET.py einfügen
# PDF-Aufrufe: from pdf_render import convert_from_path
```

## Frozen-Build (PyInstaller)

```text
pyinstaller --noconfirm --collect-all pypdfium2 --collect-all PIL ^
  scantuxio_entry.py
```

Oder in der `.spec`: `from PyInstaller.utils.hooks import collect_all` und
`datas/binaries/hiddenimports` für `pypdfium2` ergänzen. Siehe
`docs/PYINSTALLER-PDFIUM.txt`.

## Installer (Inno Setup 6)

1. App mit pypdfium2 bauen → Output nach `SourceRoot`
2. `installer\scantuxio.iss` → `#define SourceRoot` / Version anpassen
3. `ISCC.exe scantuxio.iss` → `dist\ScanTuxio-Setup-*.exe`

`scantuxio-poppler.iss` ist **veraltet** (bricht absichtlich ab).

## Poppler?

Nur optionaler lokaler Fallback (`poppler_paths.py`, download-Skript).  
**Nicht** mit ausliefern, wenn „lizenzfrei“ gilt.

## Inhalt

| Pfad | Zweck |
|---|---|
| `python/pdf_render.py` | PDF→PIL via pypdfium2 |
| `python/poppler_paths.py` | Legacy-Fallback (nicht Installer) |
| `installer/scantuxio.iss` | Inno **ohne** Poppler |
| `patches/` | Entry, requirements, FEATURES/README |
| `run/` | Launcher |
