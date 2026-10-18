# SphereDrive

## Beschreibung

SphereDrive ist die Windows-Oberfläche für virtuelle Laufwerke und Ordnerverknüpfungen. Sie fasst subst, net use, mklink, New-PSDrive und mountvol in einem Fenster zusammen. Ein Ordner, ein Unterordner oder eine Freigabe erscheint damit wie ein eigenes Laufwerk, ohne dass die Dateien verschoben werden.

Die Startseite zeigt die Laufwerke als Kacheln. Ein Klick öffnet die Aktionen für genau diesen Buchstaben. Echte Datenträger bleiben unangetastet: subst und net use legen sich nicht über einen vorhandenen Buchstaben. Ordner und Unterordner eines Laufwerks lassen sich aufklappen und als neuer Buchstabe einhängen. Auf Windows 11 steht der Systemname in der Seitenleiste.

Die Menüleiste enthält Subst, net use, Verknüpfungen, PowerShell und Bereitstellung im selben Aufbau. net use bietet Seite öffnen, Freigabe verbinden, Ordner freigeben und Trennen. Die drei Punkte an einer Kachel enthalten zusätzlich net use.

Dieselbe Beschreibung und die Feature-Liste stehen im Programm unter Hilfe. Die Dateien `SphereDrive-Hilfe.html` und `SphereDrive-Feature-Liste.txt` liegen neben dem Programm und werden in den Arbeitsordner kopiert.

## Feature-Liste

### Laufwerkszuordnungen

- Kacheln oder Liste, Filter „Alle Laufwerke anzeigen“
- Klick auf eine Kachel oder auf ··· öffnet die Aktionen dieses Buchstabens
- Bezeichnung, Symbol, Explorer und Trennen
- Echte Datenträger werden nicht durch subst oder net use verdeckt

### Ordner und Unterordner

- Baum der Ordner eines Laufwerks, weitere Ebenen beim Aufklappen
- Ein Unterordner wird als eigenes Laufwerk eingehängt
- Dieselbe Auswahl unter Subst und als Ziel einer Ordner-Bereitstellung

### subst

- Lokale Ordner, auch tief in OneDrive, Google Drive oder Dropbox
- Dauerhaft über den Autostart und, mit Administratorrechten, über DOS Devices
- Papierkorb über die Known-Folder-Registrierung
- Sichtbarkeit für erhöhte Programme über EnableLinkedConnections und eine Anmeldungsaufgabe

### net use

- UNC-Freigaben, dauerhaft mit `/persistent:yes`
- Freigaben anlegen und entfernen
- Kennwörter werden für den Aufruf verwendet und nicht gespeichert

### Verknüpfungen

- `mklink /J` für Junctions, `/D` für Ordnerlinks, dazu Dateisymlinks und Hardlinks
- Entfernen löscht nur die Verknüpfung, nicht den Zielordner

### PowerShell

- New-PSDrive für Dateisystem, Registrierung, Zertifikate und weitere Anbieter
- Optional im PowerShell-Profil; `-Persist` nur für UNC-Pfade

### Bereitstellung

- Partition oder VHD/VHDX auf einen Buchstaben oder in einen leeren NTFS-Ordner
- Aufruf der Datenträgerverwaltung (`diskmgmt.msc`)

### Programm

- Vergleich, welcher Befehl wofür gedacht ist
- Arbeitsordner `D:\AI_Temp\SphereDrive`, ein Logo in diesem Ordner hat Vorrang
- Installer mit eingebettetem Python, Wiederherstellung beim Anmelden mit `--restore`
- Hilfe im Programm und als `SphereDrive-Hilfe.html` neben dem Programm
- Feature-Liste im Menü Hilfe und als `SphereDrive-Feature-Liste.txt`

SphereDrive gleicht die bekannten Lücken von `subst` aus:

| Lücke | Was SphereDrive tut |
| --- | --- |
| Zuordnung ist nach einem Neustart weg | Autostart (`HKCU\...\Run`) und, mit Administratorrechten, `HKLM\...\DOS Devices` |
| Keine eigene Bezeichnung und kein Symbol | `DriveIcons\Buchstabe\DefaultLabel` und `DefaultIcon` |
| Erhöhte Programme sehen das Laufwerk nicht | `EnableLinkedConnections` und eine Anmeldungsaufgabe mit höchsten Rechten |
| Löschen ist sofort endgültig | Known-Folder-Registrierung, damit der Papierkorb des Zieldatenträgers greift |

Der vorgesehene Arbeitsordner ist `D:\AI_Temp\SphereDrive`. `Start-SphereDrive.bat` legt ihn an und kopiert Programm und Logo dorthin. Ein Symbol in diesem Ordner hat Vorrang vor dem mitgelieferten `assets\SphereDrive.ico`. Liegt dort eine andere `.ico`-Datei, wird sie verwendet. Dieses Symbol erscheint in der Seitenleiste, im Infofenster und als Vorgabe im Feld „Symbol“ bei einer neuen Zuordnung. Ein Laufwerk, das schon ein eigenes Symbol hat, behält es.

## Installation

`SphereDrive-Setup-1.0.0.exe` installiert das Programm und ein eingebettetes Windows-Python. Eine eigene Python-Installation ist dafür nicht nötig. Der Installer legt eine Verknüpfung im Startmenü an und `bin\SphereDrive.exe` für den Start ohne Konsole. Die Wiederherstellung beim Anmelden ruft diese Datei mit `--restore` auf.

Gebaut wird der Installer auf einem Rechner mit NSIS und pynsist:

```bash
python3 tools/build_installer.py
```

Das Skript lädt Python 3.12.10 für Windows und die dazu passenden Tcl/Tk-Dateien, packt SphereDrive dazu und schreibt `build/nsis/SphereDrive-Setup-1.0.0.exe`. Dieselbe Datei liegt im Projektordner, neben `SphereDrive.pyw` und `assets\SphereDrive.ico`.

## Start aus dem Quelltext

Python 3.10 oder neuer, keine zusätzlichen Pakete.

```bat
Start-SphereDrive.bat
```

Oder direkt:

```bat
pyw -3 SphereDrive.pyw
```

Stille Wiederherstellung, wie sie Autostart und die erhöhte Anmeldungsaufgabe aufrufen:

```bat
pyw -3 SphereDrive.pyw --restore
```

Die Konfiguration liegt unter `%APPDATA%\SphereDrive\config.json`. Kennwörter werden nicht gespeichert.

Administratorrechte sind nur für DOS Devices, den Papierkorb, `EnableLinkedConnections`, symbolische Links ohne Entwicklermodus, Freigaben und die Anmeldungsaufgabe nötig. Junctions, Bezeichnungen im Benutzerprofil und `subst` selbst laufen ohne Erhöhung. Die Schaltfläche „Als Administrator neu starten“ fragt die Benutzerkontensteuerung einmal ab.

`EnableLinkedConnections` wirkt nach einem Neustart. Der Papierkorb kann eine Ab- und Anmeldung brauchen, bis der Explorer ihn anzeigt. Gelöschte Dateien bleiben auf dem Datenträger des Zielordners.

## Vergleich

| Befehl | Ziel | Erstellt | Übersteht Neustart |
| --- | --- | --- | --- |
| subst | Lokaler Ordner | Virtuelles Laufwerk | Nein, außer über Autostart oder DOS Devices |
| net use | Netzwerkfreigabe | Virtuelles Laufwerk | Ja, mit `/persistent:yes` |
| mklink /D | Lokaler Ordner | Symbolischen Link | Ja, im Dateisystem |
| mklink /J | Lokaler Ordner | Junction | Ja, im Dateisystem |
| New-PSDrive | Ordner, Registry, Zertifikate | PowerShell-Laufwerk | Nein, außer über das Profil; `-Persist` nur bei UNC |
| mountvol | Partition oder VHD/VHDX | Buchstabe oder Ordner | Ja, über den Volume-Manager |

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Auf anderen Systemen als Windows führt die Oberfläche die Befehle nicht aus. Sie zeigt dann den Vorschau-Modus und speichert den Ablauf nur im Speicher. Die Tests prüfen diesen Ablauf, die Registry-Schlüssel und die erzeugten Befehlszeilen.
