# SphereDrive

Grafische Oberfläche für die Windows-Werkzeuge, mit denen Ordner wie Laufwerke oder wie echte Pfade erscheinen.

- **subst** für lokale Ordner, auch tief in OneDrive, Google Drive oder Dropbox
- **net use** für Netzwerkfreigaben, dauerhaft mit `/persistent:yes`, plus Freigaben anlegen
- **mklink** für symbolische Links, Junctions und Hardlinks
- **New-PSDrive** für Ordner, Registrierung und Zertifikatspeicher
- **mountvol** und der Aufruf von `diskmgmt.msc` für Buchstaben und leere NTFS-Ordner

Die Startseite zeigt die Laufwerke als Kacheln, angelehnt an SUBSTitute. „Alle Laufwerke anzeigen“ blendet die echten Datenträger ein; ohne Haken bleiben Subst, net use und von SphereDrive gesetzte Bereitstellungen. Ein Klick auf eine Kachel oder auf „···“ öffnet die Möglichkeiten für genau diesen Buchstaben: Bezeichnung, Symbol, Subst, net use, Dauerhaftigkeit, Sichtbarkeit für Administratoren, Papierkorb, Explorer und Trennen. Auf einem echten Datenträger sind Subst und net use gesperrt, damit der Buchstabe nicht verdeckt wird. Ein Ordner auf diesem Datenträger kann einen neuen Buchstaben bekommen.

SphereDrive gleicht die bekannten Lücken von `subst` aus:

| Lücke | Was SphereDrive tut |
| --- | --- |
| Zuordnung ist nach einem Neustart weg | Autostart (`HKCU\...\Run`) und, mit Administratorrechten, `HKLM\...\DOS Devices` |
| Keine eigene Bezeichnung und kein Symbol | `DriveIcons\Buchstabe\DefaultLabel` und `DefaultIcon` |
| Erhöhte Programme sehen das Laufwerk nicht | `EnableLinkedConnections` und eine Anmeldungsaufgabe mit höchsten Rechten |
| Löschen ist sofort endgültig | Known-Folder-Registrierung, damit der Papierkorb des Zieldatenträgers greift |

Der vorgesehene Arbeitsordner ist `D:\AI_Temp\SphereDrive`. Ein Symbol in diesem Ordner hat Vorrang vor dem mitgelieferten `assets\SphereDrive.ico`. Liegt dort eine andere `.ico`-Datei, wird sie verwendet. Dieses Symbol erscheint in der Seitenleiste, im Infofenster und als Vorgabe im Feld „Symbol“ bei einer neuen Zuordnung. Ein Laufwerk, das schon ein eigenes Symbol hat, behält es.

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
