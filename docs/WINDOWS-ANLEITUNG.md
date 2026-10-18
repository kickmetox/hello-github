# Windows-Fassung – fertigstellen

Andreas Meyer  
ame@sellerbach.de

Diese Fassung ist die Referenz. Die Linux-Fassung wird daraus später nachgebaut, nicht neu geschrieben. Erst wenn die Prüfung am Ende dieses Blattes erfüllt ist, die Datei `docs/LINUX-ANLEITUNG.md` öffnen.

Zielordner: `D:\AI_Temp\CPCM`

## Setup

Normaler Weg: `CPCM-Setup.exe` doppelklicken. Python 3.12 (64-bit) ist im Setup enthalten, ein separates Python ist nicht nötig. Der Assistent schlägt `D:\AI_Temp\CPCM` vor. Der Ordner lässt sich ändern. Das Setup legt eine Desktop-Verknüpfung und einen Startmenü-Eintrag an. Beide starten die mitgelieferte `python.exe` mit `cpcm.py serve`, Arbeitsverzeichnis ist der Installationsordner, Icon `cpcm.ico`. Die Deinstallation steht in der Windows-Softwareliste. `vault\` und `cpcm-settings.json` werden beim Aktualisieren und beim Deinstallieren nicht gelöscht. `AUTOR.txt` nennt die Rolle Windows-Referenz, Andreas Meyer, ame@sellerbach.de.

`Install-CPCM.ps1` ist die Alternative, wenn der Quellordner schon vorliegt. Dafür gilt der folgende Ablauf, inklusive selbst installiertem Python.

## 1. Python

Python 3.11 oder neuer von https://www.python.org/downloads/windows/ installieren. Beim Installer „Add python.exe to PATH“ aktivieren. Der Starter `py` muss in einer neuen Eingabeaufforderung antworten:

```bat
py -3 --version
```

## 2. Programm ablegen

Den gesamten Programmordner auf den Windows-Rechner kopieren. Im Ordner müssen mindestens diese Dateien liegen:

- `cpcm.py`, Ordner `cpcm\`, Ordner `web\`
- `icon.png`, `cpcm.ico`
- `CPCM.bat`, `Install-CPCM.ps1`, `Create-Shortcut.ps1`
- `docs\WINDOWS-ANLEITUNG.md`, `docs\LINUX-ANLEITUNG.md`

In PowerShell, im kopierten Ordner:

```powershell
powershell -ExecutionPolicy Bypass -File .\Install-CPCM.ps1
```

Das Skript kopiert nach `D:\AI_Temp\CPCM`, schreibt `AUTOR.txt` und legt `Desktop\CPCM.lnk` mit `cpcm.ico` an. Ein vorhandener Vault und `cpcm-settings.json` werden nicht überschrieben.

Liegt der Ordner schon in `D:\AI_Temp\CPCM`, denselben Befehl dort ausführen. Robocopy kopiert dann auf sich selbst und die Verknüpfung wird neu gesetzt.

## 3. Start

`CPCM.bat` oder die Desktop-Verknüpfung. Der Browser öffnet `http://127.0.0.1:8765/`. In der Kopfzeile stehen Vault-Pfad und „Andreas Meyer · ame@sellerbach.de“.

Installer dieser Referenz bleibt `Install-CPCM.ps1`. Eine `CPCM.exe` wird nicht mitgeliefert; der Start bleibt `CPCM.bat` bzw. `Desktop\CPCM.lnk` mit installiertem Python 3.11 oder neuer.

Der normale Weg ist `CPCM-Setup.exe` im Abschnitt Setup. `Install-CPCM.ps1` bleibt die Alternative für den Quellordner.

Ohne Browserfenster:

```bat
py -3 cpcm.py serve --no-browser
```

## 4. Erste Sicherung

1. Unter **Welten** das Windows-Home prüfen, zum Beispiel `C:\Users\Andreas`. Das Linux-Home schon eintragen, auch wenn Linux noch nicht installiert ist, zum Beispiel `/home/andreas`.
2. Unter **Sicherung** einen eigenen Ordner wählen, nicht das ganze Laufwerk.
3. **Sicherung erstellen**.
4. Unter **Wiederherstellen** dieselbe Sicherung in einen leeren Testordner schreiben. Die Datei muss bytegleich ankommen.

Der Vault liegt neben dem Programm: `D:\AI_Temp\CPCM\vault`. Diesen Ordner später unverändert für Linux verwenden, wenn beide Systeme dieselbe Partition lesen.

## 5. Fertig

Die Windows-Fassung ist fertig, wenn alle Punkte zutreffen:

- `D:\AI_Temp\CPCM\cpcm.py` existiert.
- `D:\AI_Temp\CPCM\AUTOR.txt` nennt Andreas Meyer und `ame@sellerbach.de`.
- Die Verknüpfung auf dem Desktop zeigt das CPCM-Icon.
- Eine selbst gewählte Datei lässt sich sichern und in einen anderen Ordner zurückschreiben.
- Die Oberfläche bleibt auf `127.0.0.1`.

Danach `docs\LINUX-ANLEITUNG.md` verwenden.
