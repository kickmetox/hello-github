# CPCM – Cross Platform Config Manager

CPCM sichert selbst gewählte Dateien und Ordner in einen gemeinsamen Vault, liest denselben Vault unter Windows und Linux und stellt die Dateien in den passenden Ordnern wieder her. Konfigurationen, Programmlisten, Logs und Leistungsprofile liegen in derselben Oberfläche.

Andreas Meyer, ame@sellerbach.de.

Die Windows-Fassung in `D:\AI_Temp\CPCM` ist die Referenz. Die Linux-Fassung wird daraus später nachgebaut.

- Windows, zuerst: [docs/WINDOWS-ANLEITUNG.md](docs/WINDOWS-ANLEITUNG.md)
- Linux, danach: [docs/LINUX-ANLEITUNG.md](docs/LINUX-ANLEITUNG.md)

## Start

Python 3.11 oder neuer, keine zusätzlichen Pakete.

Windows, im Ordner `D:\AI_Temp\CPCM`:

```bat
CPCM.bat
```

Linux:

```bash
./cpcm.sh
```

Die Oberfläche bindet nur an `127.0.0.1`. Der Port ist 8910. 8765 bis 8864 bleiben für ShatuIDE frei.

## Windows-Setup

Normaler Weg: `CPCM-Setup.exe` doppelklicken. Python 3.12 ist enthalten. Zielordner standardmäßig `D:\AI_Temp\CPCM`, im Assistenten änderbar. Details: [docs/WINDOWS-ANLEITUNG.md](docs/WINDOWS-ANLEITUNG.md).

## Nach `D:\AI_Temp\CPCM` legen

Alternative für den Quellordner, wenn Python 3.11 oder neuer schon installiert ist. Auf dem Windows-Rechner, im entpackten Programmordner:

```powershell
powershell -ExecutionPolicy Bypass -File .\Install-CPCM.ps1
```

Das Skript kopiert das Programm nach `D:\AI_Temp\CPCM` und legt eine Desktop-Verknüpfung mit `cpcm.ico` an.

## Sicherung und Wiederherstellung

1. Unter **Sicherung** Dateien oder Ordner auswählen.
2. **Sicherung erstellen**. Der Vault ist ein normaler Ordner (`vault` neben dem Programm, oder ein selbst gewählter Pfad).
3. Unter **Welten** das Linux-Home und das Windows-Home eintragen. Daraus entstehen die Pfade der anderen Welt.
4. Unter **Wiederherstellen** die Sicherung wählen.

Abbildung:

| Vault | Linux | Windows |
| --- | --- | --- |
| `documents/` | `~/Documents` oder `~/Dokumente` | `Dokumente` im Home |
| `config/` | `~/.config` | `%APPDATA%` |
| `local/` | `~/.local/share` | `%LOCALAPPDATA%` |
| `home/` | Home | `%USERPROFILE%` |

Pfade außerhalb des Homes bleiben `external/...` und werden nur auf demselben System zurückgeschrieben.

Vor dem Überschreiben kopiert CPCM die vorhandene Datei nach `vault/pre-restore/`. Textdateien können absolute Pfade dabei auf das aktuelle System umschreiben. Eine Sicherung lässt sich als `.cpcm`-Zip exportieren und auf der anderen Welt importieren.

## Weitere Bereiche

- **Programme:** feste Äquivalenzliste, Paketbefehle nur aus dieser Liste. Photoshop wird als Arbeitsablauf mit GIMP geführt, nicht als dasselbe Programm.
- **Konfiguration:** Shell, JSON, INI und Registry-Auszüge, dazu Kürzel (`Strg`/`Win`/`Super`), Touchpad-Gesten und Hell/Dunkel-Plan für Windows, GNOME, KDE und XFCE.
- **Diagnose:** bekannte Windows-Codes und Linux-Meldungen in Klartext, dazu ein Prüfplan für NTFS, ext4 und Btrfs. Skripte mit Lösch- oder Verkettungszeichen werden nicht ausgeführt.
- **Hardware:** gemeinsame Profile Silent, Balanced, Performance und Turbo. Spannungs-Offsets werden gespeichert und nicht angewendet. Eine Ladeschwelle wird nur geschrieben, wenn die sysfs-Datei existiert und beschreibbar ist.

## Tests

```bash
python3 -m unittest discover -s tests -p 'test_cpcm_*.py'
```
