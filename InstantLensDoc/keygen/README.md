# InstantLens Doc — Keygenerator

Separates Tool zur Erzeugung und Prüfung von Lizenzkeys.

## Windows (schnell)

```bat
run-keygen.bat
```

Startet die GUI. Ausgabe als **Klartext (ohne QR)** mit **Kopieren**-Button;
**Gültigkeitstage** erscheinen neben dem generierten Key.
Keys gelten **32 Tage (30+2)**. Kontakt: **ame@sellerbach.de**.

## Installer-Pfad (EXE-Build)

Nach `build-windows.ps1` (ohne `-SkipKeygen` / ohne `-NoKeygenInApp`):

| Ort | Pfad |
|-----|------|
| Keygen-Dist | `dist\InstantLensKeygen\InstantLensKeygen.exe` |
| App-Dist (Installer) | `dist\InstantLensDoc\InstantLensKeygen.exe` |
| Installiert | `{app}\InstantLensKeygen.exe` |
| Startmenü | „Keygenerator“ → diese EXE |

Python-/Dev-Installer (`UsePythonLauncher=1`): Shortcut auf `run-keygen.bat` statt EXE.
Ohne Keygen: `build-installer.ps1 -NoKeygen` bzw. ISCC `/DIncludeKeygen=0`.

## CLI

```bash
# Erzeugen
python -m keygen kunde@example.com

# Prüfen
python -m keygen --verify "ILD1...."

# GUI
python -m keygen --gui
```

Format: `ILD1.<payload>.<sig>`.
