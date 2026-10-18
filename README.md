# CrossOS Intelligent Workflow & System Sync

Lokale Suite für drei Aufgaben zwischen Linux und Windows: Konfigurationen übersetzen, Protokolle in Klartext auflösen, Hardwareprofile vergleichbar halten. Es gibt kein Cloud-LLM. Der Standard ist Dry-Run. Skripte werden gezeigt, bevor etwas läuft.

## Start

Python 3.12, keine Pflichtabhängigkeiten.

```bash
PYTHONPATH=src python3 -m crossos serve
```

Die Oberfläche liegt auf [http://127.0.0.1:8765/](http://127.0.0.1:8765/). Seiten: Übersicht, Migrator, Diagnose, Hardware. Die API antwortet unter `/api/...`.

Weitere Kommandos:

```bash
PYTHONPATH=src python3 -m crossos translate --input examples/gitconfig.sample --from ini --to reg --target-os windows --user andreas
PYTHONPATH=src python3 -m crossos diagnose --input examples/journal-sample.log --shell bash
PYTHONPATH=src python3 -m crossos apps plan --os linux --app Photoshop --app Notepad++
PYTHONPATH=src python3 -m crossos hardware probe
```

Optional, nur für das Konsolenskript `crossos`:

```bash
pip install -e .
```

Tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Modul 1 — Migrator

- Semantik für INI, JSON, XML, Bash-Exporte, `.env` und `.reg`. Git `core.autocrlf` wird zu `true` (Windows) oder `input` (Linux/WSL). VS-Code-Schlüssel `.linux` und `.windows` werden umbenannt, der Wert nicht erfunden. `files.eol` folgt dem Ziel.
- Pfade: `/home/<user>` ↔ `C:\Users\<user>`, `~/.config` ↔ `AppData\Roaming`, `~/.local/share` ↔ `AppData\Local`, `~/.local/state` ↔ `AppData\Local\State`, `~/.local/bin` ↔ `AppData\Local\bin`, `~/.cache` ↔ `AppData\Local\Cache`, WSL `/mnt/<laufwerk>/...`. `AppData\Local\Cache` ist absichtlich nicht `Temp`, damit die Rückübersetzung eindeutig bleibt. Systempfade außerhalb des Profils (`C:\Program Files`) werden als `/mnt/...` markiert, nicht als Heimatverzeichnis ausgegeben.
- App-Katalog mit den Stufen gleich, Port und Workflow. Photoshop ist kein Linux-Paket; der Plan nennt GIMP und Krita. Notepad++ wird auf Notepad-Next abgebildet.
- Eine Paket-API für winget, scoop, apt, pacman, dnf, flatpak und snap. Vorhandene Manager werden erkannt. Paketnamen laufen durch eine Zeichensatzprüfung, bevor ein argv entsteht. `;`, Leerzeichen, `$()`, Pipes und `..` erzeugen keinen Befehl.
- Kürzel: Strg/Ctrl, Alt, Super/Win/Meta, inklusive VS-Code-Akkorden (`ctrl+k ctrl+s`, `win` gegen `meta`).
- Touchpad: gsettings, libinput-Quirks und ein Precision-Touchpad-Registry-Plan. Nichts davon wird gesetzt.
- Design: dunkel, hell oder Zeitplan, Akzent, Wallpaper-Pfad, Zeiger. GNOME, KDE, XFCE und Windows-Personalisierung bleiben Text.

## Modul 2 — Diagnose

Lokale Regeln, kein Netzmodell. Ereignisanzeige, journalctl und dmesg werden gelesen. Unter anderem 0x80070002, 0x80070005, 0x80004005, 0x80070057, 0xC0000005, Segmentation fault, fehlende DLL oder `.so`, gebrochene apt/dpkg-Abhängigkeiten und systemd-Units. Dazu entstehen Bash- und PowerShell-Pläne.

Ein-Klick führt nur die Freigabeliste aus, und nur mit JSON-`confirm: true`: `df -hT`, `systemctl --failed`, `apt-get check`, `uname -a`, `locale`. Das sind Lese- oder Prüfvorgänge. `shell=True` kommt nicht vor. Paketnamen und Pfade mit `..` werden abgelehnt.

Nicht auf der Liste, also nur Plan: `fsck`, `ntfsfix` ohne `--no-action`, Firmware-Flash, Spannungsänderungen, `apt-get install`, `systemctl restart`.

Firmware: wenn `fwupdmgr` existiert, läuft `fwupdmgr get-devices`. Sonst ein Plan für LVFS gegenüber Windows Update. `fwupdmgr update` wird nicht aufgerufen.

Dateisysteme: von Linux aus NTFS nur als Plan mit `ntfsfix --no-action`. Von Windows aus ext4/btrfs kein nativer fsck; der Plan nennt `fsck -n` in WSL oder das Linux, dem das Dateisystem gehört.

## Modul 3 — Hardware

- Lüfterprofile Silent, Balanced, Performance, Turbo mit denselben Punkten (°C → Duty %) für beide Systeme. PWM wird nicht geschrieben.
- Linux liest sysfs (`thermal`, `hwmon`, `cpufreq`, `power_supply`), wenn die Knoten da sind. Fehlende Knoten bleiben leer. Unter Windows werden `powercfg`- und WMI-Befehle nur erzeugt.
- ASUS, Lenovo, HP und Dell sind eine Modulkarte (`asus_nb_wmi`, `thinkpad_acpi`, `hp_wmi`, `dell_smm_hwmon`). Ohne geladenes Modul und ohne Plattformknoten ist `usable` falsch.
- Undervolt/OC für Intel/AMD-CPU und NVIDIA/AMD/Intel-GPU speichert Offsets. Es gibt keinen MSR-Zugriff. Der Hinweis zu modernen Intel-CPUs steht im Datensatz: Plundervolt-Mitigation und Overclocking-Lock können Undervolting sperren.
- Energiesparpläne: Windows-GUIDs ↔ `powerprofilesctl` ↔ TLP-Schnipsel. `powerprofilesctl set` nur mit Bestätigung und nur wenn das Programm existiert. TLP-Dateien werden nicht geschrieben.
- Ladeschwelle, zum Beispiel 80 %, wird gespeichert. `charge_control_end_threshold` oder `charge_stop_threshold` wird nur beschrieben, wenn der Knoten existiert, für diesen Benutzer beschreibbar ist und `confirm` wahr ist. Bereich 20 bis 100.

## Sicherheitsgrenzen

| Vorgang | Verhalten |
| --- | --- |
| Konfiguration übersetzen | nur Text |
| Pakete installieren | Plan; Start nur mit `confirm`, `dry_run=false` und `CROSSOS_ALLOW_PACKAGE_INSTALL=1` |
| Diagnose-Ein-Klick | Freigabeliste, bestätigen, kein Shell-String aus Benutzereingaben |
| fsck, ntfsfix, chkdsk /f | Plan |
| Firmware schreiben | nie |
| Lüfter-PWM | nie |
| Spannung | nur speichern |
| Ladeschwelle | sysfs nur unter den Bedingungen oben |

Der Server bindet standardmäßig an `127.0.0.1`.
