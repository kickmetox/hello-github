# Office Display

Office Display erstellt Präsentationen lokal und schreibt sie als PowerPoint-Datei (`.pptx`), OpenDocument (`.odp`) und im eigenen Paket (`.odisp`). Damit lassen sich die Dateien in PowerPoint, OpenOffice, OnlyOffice und SoftMaker öffnen.

Andreas Meyer · ame@sellerbach.de

Der Programmordner ist dieses Repository. Auf diesem Linux-System gibt es kein Laufwerk `D:\AI_Temp\OfficeDisplay`. Unter Windows kann der Ordner dorthin kopiert werden; die Startdatei sucht keine feste Platte.

## Start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cmake -S native/cpp -B native/cpp/build && cmake --build native/cpp/build
.venv/bin/python scripts/build_onnx.py
./start-officedisplay.sh
```

Unter Windows, wenn Python und die Pakete installiert sind:

```bat
start-officedisplay.bat
```

Visual Studio öffnet `OfficeDisplay.sln` (C#-Farbwerkzeug und C++-Bibliothek). Die Oberfläche selbst ist Python mit PySide6.

## Kurz

Eine Folie liegt in der Mitte. Rechts stehen die bereits angelegten Folien; ein Klick lädt sie in den Editor. Texte, Bilder, Formen, Stiftstriche, Diagramme und Videos bleiben Objekte: auswählen, verschieben, skalieren, gruppieren. Umschalt+Ziehen einer Auswahl auf eine Folienminiatur legt das Objekt auf diese Folie.

Stift, Grafiktablett und Touch sind eigene Zeiger. Der Stift zeichnet mit Druck, die Radiererseite radiert, Touch verschiebt oder zeichnet je nach Schalter. Ohne Tablett bleibt die Maus bedienbar.

Online-KI und Canva Connect sind aus. Sie senden nur dann Daten, wenn der Schalter gesetzt ist und eine Aktion angeklickt wird. Schlüssel liegen in `~/.config/officedisplay/secrets.json`.

Ausführliche Bedienung: `docs/HILFE.md`. Merkmale: `FEATURELISTE.md`.
