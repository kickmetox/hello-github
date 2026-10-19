# Office Display

Office Display ist ein lokales Präsentationsprogramm. Es schreibt PowerPoint (`.pptx`), OpenDocument (`.odp`) und das eigene Paket (`.odisp`). Diese Dateien lassen sich in PowerPoint, OpenOffice, OnlyOffice und SoftMaker öffnen.

Andreas Meyer · ame@sellerbach.de

## Programmordner

Der Programmordner ist das Repository, also das Verzeichnis dieser Datei. Auf diesem Linux-System gibt es kein Laufwerk `D:`. Der ursprünglich genannte Ordner `D:\AI_Temp\OfficeDisplay` existiert hier nicht. Unter Windows kann das Repository an einen beliebigen Ort kopiert werden; die Startdateien suchen keine feste Platte.

## Kurzbeschreibung

Eine Folie liegt in der Mitte. Rechts stehen die Miniaturen der angelegten Folien; ein Klick lädt die Folie in den Editor. Präsentieren startet den Vollbild-Player; Bilder, Videos und Texte lassen sich zusätzlich als Slideshow (`.oshow`) abspielen. Texte, Bilder, Formen, Stiftstriche, Diagramme und Videos bleiben Objekte und lassen sich auswählen, verschieben, skalieren und gruppieren. Eine Auswahl mit Umschalt auf eine Miniatur ziehen legt das Objekt auf diese Folie.

Stift, Grafiktablett und Touch sind eigene Zeiger. Der Stift zeichnet mit Druck, die Radiererseite radiert, Touch verschiebt oder zeichnet je nach Schalter. Ohne Tablett bleibt die Maus bedienbar.

Standard ist offline: kein Tracking, kein automatischer Netzaufruf. Online-KI (OpenAI-kompatible HTTPS-API) und Canva Connect sind möglich, aber nur nach Freigabe unter „KI → Einstellungen Online-KI / Canva“ und nur auf Klick. Schlüssel liegen unter `~/.config/officedisplay/secrets.json` mit Modus 600. Die ausführliche Bedienung steht in `docs/HILFE.md`, die Merkmale in `FEATURELISTE.md`, die kurze Fassung in `KURZBESCHREIBUNG.md`.

## Installieren

Windows: den Ordner entpacken und `installer\install.bat` per Doppelklick starten. Danach im Programmordner `Office Display.bat` starten.

Linux und macOS: `chmod +x installer/install.sh` und `./installer/install.sh`. Danach `./Office Display.sh`. `start.sh` und `start-officedisplay.sh` bleiben liegen.

## Start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cmake -S native/cpp -B native/cpp/build && cmake --build native/cpp/build
./start.sh
```

Alternativ `./start-officedisplay.sh`. Unter Windows, wenn Python und die Pakete installiert sind: `start-officedisplay.bat`.

Ohne Startdatei:

```bash
PYTHONPATH=src python3 -m officedisplay
```

Das ONNX-Modell liegt bereits unter `models/layout_classifier.onnx`. `scripts/build_onnx.py` schreibt es bei Bedarf neu.

Visual Studio öffnet `OfficeDisplay.sln`. Das ist ein C#-Farbwerkzeug. Die Oberfläche selbst ist Python mit PySide6. Fehlt `dotnet`, nutzt das Programm die Python-Farbreihe.

## Tests

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
```
