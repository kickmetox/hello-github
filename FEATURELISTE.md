# Featureliste Office Display

Stand der Umsetzung in diesem Programmordner. Was ein Netz bräuchte, ist aus oder ein ausdrücklicher Klick.

## Klassische Performance und Datensteuerung

- Excel- und CSV-Kopplung: lokale Dateien werden gelesen, die ersten 500 Datenzeilen landen im Diagramm, „Daten aktualisieren“ liest die Datei neu. Sehr große Arbeitsmappen werden zeilenweise begrenzt, damit der Editor bedienbar bleibt.
- Animation: Morph-Vorschau schiebt Objekte mit gleichem Namen zur nächsten Folie. Weitere Eingangseffekte sind als Folienübergang im Datenmodell gespeichert.
- Offline-Formatierung: Schriften, Farben, Ausrichtung, Hintergründe und Markensperre funktionieren ohne Internet. Makros sind lokale Python-Dateien mit der Funktion `run(api)` und ohne Dateisystemzugriff.
- Kompatibilität: Export und Import von `.pptx` (python-pptx) und ein grundlegendes `.odp`. Das eigene Paket `.odisp` hält Texte und Mediendateien editierbar.
- Datenschutz: kein Tracking, kein Cloud-Zwang. Analyse der Verweildauer schreibt nur eine lokale JSON-Datei, wenn sie gespeichert wird.

## KI, offline und optional online

- Text-zu-Design offline: ein Satz wird zu Titel, Ablauf, Inhalt und Abschluss. Zahlen, die nicht im Satz stehen, sind als Beispielwerte markiert.
- Dieselbe Struktur kann online erzeugt werden, wenn die Online-KI eingeschaltet ist. Die Schnittstelle ist `POST {basis}/chat/completions` (OpenAI-kompatibel, auch Ollama unter `http://127.0.0.1:11434/v1`).
- Dokumente: TXT, Markdown und PDF werden in Folien zerlegt. Die Sätze bleiben erhalten, die Notiz nennt die Quellzeile.
- Inline-Befehle offline, zum Beispiel „zwei spalten“, „diagramm“, „dunkler hintergrund“.
- Quellenfokus: die Dokumentumwandlung formuliert keine neuen Fakten. Die Online-Anweisung verlangt dasselbe; ein fremdes Modell kann sich trotzdem nicht daran halten, deshalb bleibt der Schalter aus, bis er gebraucht wird.
- Layout-Klassifikator: kleines ONNX-Modell unter `models/layout_classifier.onnx`, dazu dieselbe Rechnung in NumPy. „Modell inspizieren“ startet Netron, falls das Paket installiert ist.
- Sprech-Coach: Füllwörter Deutsch/Englisch, Wörter pro Minute und Satzlängen aus der Sprechernotiz. Kein Mikrofonmitschnitt.
- Optionale Bildgenerierung: `POST {basis}/images/generations`, nur mit separatem Haken.

## Canva-Fähigkeiten

Lokal, ohne Canva-Konto:

- Vorlagen: Pitch, Unterricht, Kennzahlen, Zitat, Vergleich, Team, Titel.
- Magic Resize: 16:9, 4:3, Quadrat, Story 9:16, Portrait, A4, LinkedIn, Banner. Positionen sind relativ, Schriften und Hochformat werden nachgeführt.
- Elemente: Rahmen, Fläche, Kreis, Raute, Stern, Pfeil, Badge.
- Ausrichten und Raster beim Ziehen.
- Markenführung: gesperrte Schriften, Farbpalette, Logo.
- Fotowerkzeuge: Helligkeit, Graustufen, Weichzeichnen, Schärfen, Spiegeln, einfaches Freistellen nach der Eckfarbe.
- 3D: Würfel, Pyramide oder OBJ, softwaregerendert, als Bild auf der Folie.

Canva Connect, nur mit eigenem Token und nur auf Klick:

- Markenvorlagen listen: `GET https://api.canva.com/rest/v1/brand-templates`
- Autofill: `POST /rest/v1/autofills` mit `create_from_brand_template`
- Export: `POST /rest/v1/exports` mit Format `pptx`
- OAuth-Startadresse mit PKCE wird gebaut. Das Programm speichert keinen Canva-Client-Geheimschlüssel.

## Eingabe

- Maus, Stift (Druck, Neigung wird entgegengenommen, die Strichstärke folgt dem Druck), Radiererseite, Touch.
- Touch standardmäßig zum Verschieben und mit zwei Fingern zum Zoomen. Der Schalter „Touch: zeichnen“ lässt den Finger im Stiftwerkzeug zeichnen.
- Strg+Mausrad zoomt die Ansicht. Die Leinwand unter „Präsentieren → Leinwand“ zeigt alle Folien und zoomt.

## Nicht enthalten

- Kein eingebauter Videochat und keine fremde Cloud-Zusammenarbeit. Kommentare und Folienstatus liegen in der Datei.
- Keine Millionen externer Stockmotive. Die Formen sind lokal.
- Kein stilles Hochladen von Folien.
