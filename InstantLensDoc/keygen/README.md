# InstantLens Doc — Keygenerator

Separates Tool zur Erzeugung und Prüfung von Lizenzkeys.

## Windows (schnell)

```bat
run-keygen.bat
```

Startet die GUI. Ausgabe als **Klartext (ohne QR)** mit **Kopieren**- und
**Speichern als .txt**-Button; **Gültigkeitstage** neben dem Key (Spinbox / `--days`);
lokale **History der letzten 10 Keys** + **Clear History** (keine Secrets in Logs);
History **maskiert** (nur letzte 4), Hover/Reveal zeigt Klartext (**Auto-Hide 5/10/30 s** + Countdown, Pause bei Fokusverlust, **Esc** maskiert), **Doppelklick kopiert**.
Keys gelten standardmäßig **32 Tage (30+2)**. Kontakt: **ame@sellerbach.de**.

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
# Erzeugen (Standard-Tage)
python -m keygen kunde@example.com

# Erzeugen mit Gültigkeit (--days, optional/kompatibel)
python -m keygen kunde@example.com --days 32

# Prüfen
python -m keygen --verify "ILD1...."

# GUI
python -m keygen --gui

# History leeren
python -m keygen --clear-history
```

Format: `ILD1.<payload>.<sig>`.
