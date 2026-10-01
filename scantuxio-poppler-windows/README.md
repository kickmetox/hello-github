# ScanTuxio — Poppler für Windows (Integrationspaket)

Dieses Verzeichnis enthält Patches, Launcher, Download-Skript und Inno-Setup-
Vorlage, um Poppler neben ScanTuxio zu bündeln.

## Ausgangslage (dieser Cloud-Lauf)

- Nutzerpfad `D:\AI_Temp\ScanTuxio Win` war **nicht gemountet**.
- Genannte Upload-Dateien (FEATURES.txt, README.md, requirements.txt, run.*,
  scantuxio_entry.py, ScanTuxio.exe, `_*.pyd`) waren **nur als Namen** bekannt —
  **keine Dateiinhalte** im Worker-VM.
- Workspace-Repo ist `hello-github` (kein ScanTuxio-Quellbaum).
- Erkennbar aus Namen: **Python 3.12 / win_amd64**, **PyInstaller-frozen** Artefakte,
  Dev-Launcher, **kein** Inno/NSIS/WiX im Dateilisten-Ausschnitt.

## Schnellstart auf dem Windows-Build-Rechner

```powershell
cd "D:\AI_Temp\ScanTuxio Win"
# Dieses Paket daneben oder hinein kopieren, dann:
.\scantuxio-poppler-windows\scripts\download-poppler.ps1 -DestRoot .
# Launcher überschreiben/mergen:
copy .\scantuxio-poppler-windows\run\run.bat .\run.bat
copy .\scantuxio-poppler-windows\run\run.ps1 .\run.ps1
copy .\scantuxio-poppler-windows\python\poppler_paths.py .\python\poppler_paths.py
# Entry: Snippet einfügen oder patches\scantuxio_entry.py mergen
```

Installer (Inno Setup 6): `installer\scantuxio-poppler.iss` — `SourceRoot` /
`PopplerRoot` anpassen, dann ISCC.

## Lizenz (kurz)

| Komponente | Lizenz | Für „lizenzfrei“? |
|---|---|---|
| Poppler-Tools | **GPL** | Nein — mitliefern = GPL-Pflichten für Poppler |
| poppler-windows Packaging | MIT | Nur Verpackung |
| pypdfium2 / PDFium | Apache-2.0 / BSD-ähnlich | Ja, deutlich freundlicher — braucht Quellcode-API-Umbau |

Empfehlung: Poppler bundlen (wie gewünscht) + GPL klar dokumentieren.
Wenn wirklich permissive PDF-Raster nötig: auf **pypdfium2** umstellen
(sobald vollständiger Quellbaum da ist).

## Inhalt

- `python/poppler_paths.py` — Suche Bundle/Env/PATH, setzt `POPPLER_PATH`
- `patches/` — Entry-Snippet + Vorlage `scantuxio_entry.py`
- `run/` — run.bat / run.ps1 / run.sh mit Poppler-PATH
- `scripts/download-poppler.ps1` — holt Release-Zip nach `vendor/poppler`
- `installer/scantuxio-poppler.iss` — Inno inkl. vendor\poppler
- `docs/LICENSE-THIRD-PARTY.txt` — GPL-Hinweis
