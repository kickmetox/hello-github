# README.md — Abschnitt zum Einfügen

## Poppler unter Windows

ScanTuxio erwartet die Poppler-Tools `pdftoppm` und `pdfinfo`.

**Mitgeliefert (Installer / vendor):**

- Pfad: `vendor\poppler\Library\bin\` (Layout von poppler-windows)
- Start bevorzugt über `run.bat` / `run.ps1` (setzt PATH)

**Manuell:**

```powershell
.\scantuxio-poppler-windows\scripts\download-poppler.ps1 -DestRoot .
```

Oder Variable setzen:

```powershell
$env:SCANTUXIO_POPPLER = "C:\Pfad\zu\poppler\Library\bin"
```

**Lizenz:** Poppler steht unter der **GPL**. Details: `LICENSE-THIRD-PARTY.txt`.
Für eine permissivere PDF-Engine (ohne GPL-Bundle) ist ein Umbau auf
**pypdfium2** vorgesehen — dafür wird der vollständige Anwendungsquellcode benötigt.
