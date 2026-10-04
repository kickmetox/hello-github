# InstantLens Doc — Keygenerator

Separates Tool zur Erzeugung und Prüfung von Lizenzkeys (HMAC, Format `ILD1.…`).
Kompatibel mit dem Trial-/Lizenzschema der App (Trial **28 Tage**, Keys standardmäßig **32 Tage / 30+2**).

## Windows (schnell)

```bat
run-keygen.bat
```

Startet die GUI. Ausgabe als **Klartext (ohne QR)** mit **Kopieren**- und
**Speichern als .txt**-Button; **Gültigkeitstage** neben dem Key (Spinbox / `--days`);
lokale **History der letzten 10 Keys** + **Clear History** (keine Secrets in Logs);
History **maskiert** (nur letzte 4), Hover/Reveal zeigt Klartext (**Auto-Hide 5/10/30 s** + Countdown mit Label **„pausiert“** bei Fokusverlust, Tooltip **„Countdown pausiert (Fenster ohne Fokus)“**, **Esc** maskiert), **Doppelklick kopiert**.
Kontakt: **ame@sellerbach.de**.

Voraussetzung: Python 3.10+ und installierte Abhängigkeiten (`pip install -r requirements.txt`
im App-Root) bzw. gebündelte EXE nach `build-windows.ps1`.

## CLI

```bat
REM Erzeugen (Standard: 32 Tage)
python -m keygen kunde@example.com

REM Erzeugen mit Gültigkeit
python -m keygen kunde@example.com --days 32

REM Prüfen
python -m keygen --verify "ILD1...."

REM GUI
python -m keygen --gui

REM History leeren
python -m keygen --clear-history
```

Format: `ILD1.<payload_b64url>.<sig_b64url>`.  
Payload (JSON): E-Mail, Ausstellungszeit, Tage, Schema-Version `v=1`.  
Signatur: HMAC-SHA256 über den Payload (gemeinsames App-/Keygen-Geheimnis).

### Aktivierung in der App

1. Key erzeugen (GUI oder CLI).
2. InstantLens Doc starten → Hilfe/About oder Lizenzdialog → **Lizenz aktivieren…**.
3. Key einfügen → Status wechselt auf **lizenziert** (Resttage / Ablauf TT.MM.JJJJ).

## Installer-Pfad (EXE-Build)

Nach `build-windows.ps1` (ohne `-SkipKeygen` / ohne `-NoKeygenInApp`):

| Ort | Pfad |
|-----|------|
| Keygen-Dist | `dist\InstantLensKeygen\InstantLensKeygen.exe` |
| App-Dist (Installer) | `dist\InstantLensDoc\InstantLensKeygen.exe` |
| Installiert | `{app}\InstantLensKeygen.exe` |
| Startmenü | „Keygenerator“ → diese EXE |

Python-/Dev-Installer (`UsePythonLauncher=1` bzw. `install-ild.ps1`): Shortcut auf `run-keygen.bat` statt EXE.
Ohne Keygen: `build-installer.ps1 -NoKeygen` bzw. ISCC `/DIncludeKeygen=0` · `install-ild.ps1 -SkipKeygen`.

## Hinweis

Der Keygen ist für den Hersteller/Support gedacht (Offline-Aktivierung ohne Server).
Keys nicht öffentlich verteilen. Bei Ablauf: neuen Key anfordern (**ame@sellerbach.de**).
