# Featureliste Office Display

Stand der Umsetzung in diesem Programmordner. Standard ist lokal, ohne Tracking. Online-KI und Canva Connect sind optional und bleiben aus, bis sie freigegeben werden.

## Editor

- Werkzeuge: Auswahl, Text, Formen, Stift, Marker, Radierer, Diagramm, Bild, Video, 3D.
- Vier Leisten über Menü Ansicht: Text (Schrift, Größe, Fett, Kursiv, Unterstrichen, Farbe, Ausrichtung), Grafik/Foto (Formen, Stift, Marker, Radierer, Stärke, Druck, Glättung, Bild, Filter), Video (Video, Kamera), Player (Präsentieren, Slideshow, Leinwand, Morph, Eingangseffekt). Sichtbarkeit liegt in QSettings. Auswahl und Folienaktionen bleiben erreichbar.
- Rechtsklick auf Formen: Füllfarbe, Linienfarbe, Bild in die Form, Formbild als Folienhintergrund mit der aktuellen Deckkraft. Die Auswahl bleibt.
- Text: Schriftfamilie, Größe, fett, kursiv, unterstrichen, Farbe, Ausrichtung. Markensperre begrenzt Schrift und Farbe.
- Hintergründe: Farbe, Verlauf, Bild, volle Fläche, Deckkraft in Prozent (`background.opacity`), cover, contain, kacheln. Die Bilddeckkraft ist in der Miniatur und im Player sichtbar.
- Rechts die Folienminiaturen. Ein Klick lädt die Folie. Objekte lassen sich per Ziehen oder Menü auf eine andere Folie legen.
- Gruppieren und Gruppierung aufheben. Drag-and-drop von Bild, Video, Text und Dateien auf die Fläche.
- Themen: hell, dunkel, farbe, graustufen.
- Foliengröße ist nicht auf 16:9 festgelegt. Elemente liegen in relativen Koordinaten und bleiben in den Rändern.

## Stift, Grafiktablett, Touch

- Maus, Stift und Touch werden über Qt-Tablet- und Touch-Ereignisse unterschieden. Die Statuszeile zeigt Maus, Stift, Radierer oder Touch.
- Stift: Strichstärke folgt dem Druck. Stärke, Druckkurve und Glättung sind einstellbar. Neigung wird entgegengenommen, wenn das System sie meldet.
- Radiererseite oder Radiererwerkzeug entfernt getroffene Striche.
- Touch verschiebt und zoomt mit zwei Fingern, oder zeichnet, wenn „Touch: zeichnen“ gewählt ist.
- Ohne Tablett bleibt die Maus der Eingabeweg. Die Strichlogik ist ohne Gerät testbar.

## Dateien und Daten

- `.pptx` über python-pptx. Texte und Bilder bleiben nach dem Rundweg editierbar. Gruppen werden beim Export flach geschrieben.
- `.odp` mit grundlegender `content.xml` für Textinhalte.
- `.odisp`: Zip mit `presentation.json` und Medien.
- Excel und CSV: lokale Datei an ein Diagramm binden und erneut einlesen (openpyxl).
- TXT, Markdown und PDF (pypdf) werden nur aus dem Quelltext in Folien zerlegt. Die Notiz nennt die Quelle. Es werden keine Fakten ergänzt.
- Makros: bestätigte Python-Dateien aus `macros/` mit `def run(api)` und einer kleinen API.
- Kommentare, Folienstatus und Verweildauer liegen in der Datei bzw. in einer lokalen JSON.
- Präsentationsplayer: Vollbild, Folie füllt den Schirm. Weiter und Zurück über Klick, Pfeile, Leertaste, Bild auf/ab, Pos1 und Ende. Escape beendet. Schwarze Blende mit B oder Punkt, weiße mit W. Leiste mit Foliennummer und Sprechernotiz, Taste N. Klickaktionen laufen, solange keine Blende liegt.
- Slideshow (`.oshow`): geordnete Einträge Bild, Video, Text. Speichern und Laden als Zip. Export nach `.odisp` mit einer Folie je Eintrag. Import aus `.odisp` und `.pptx`. Derselbe Player, Bilder mit contain und schwarzem Rand, Video über Qt Multimedia oder Pfadhinweis, Text scrollbar.
- Ordner-Sync schreibt `deck.json` und liest sie bei geänderter Zeit neu. Das ist ein lokaler Dateiabgleich, kein Server und kein Videochat.
- Kamera: Qt Multimedia, wenn ein Gerät da ist. Sonst eine Meldung, dass keine Kamera und kein Cloud-Videochat vorhanden sind.

## Gestaltung, offline

- Ein deutscher oder englischer Satz erzeugt einen Foliensatz (Titel, Ablauf, Inhalt, bei passendem Text auch zwei Spalten, Kennzahl, Diagramm, Zitat, Zeitstrahl, Abschluss). Zahlen stammen nur aus dem Satz. Fehlen sie, steht das im Text.
- Befehle auf der aktuellen Folie, zum Beispiel „zwei spalten“, „dunkler hintergrund“, „diagramm“. Ein Diagramm ohne Zahlen im Text bekommt keine Beispielreihe.
- Das Diagramm-Werkzeug in der Leiste legt beschriftete Beispielwerte an, die ersetzt werden sollen. Das ist eine leere Schablone, keine Aussage über eine Quelle.
- Schriftgröße, höchstens sechs Aufzählungen und Ränder begrenzen den Überlauf.
- `assets/brand.json` sperrt auf Wunsch Schrift, Palette und Logo.
- Lokale Bibliothek: Vorlagen, Vektorformen, Diagramm- und Kennzahl-Objekte, Größen wie 16:9, 4:3, Quadrat, 9:16, A4 und Banner.
- 3D: Würfel, Pyramide oder OBJ, perspektivisch in Software gerendert, als Bild auf der Folie.
- Animation: Eingang Einblenden, Einfliegen, Zoom. Morph verschiebt Objekte mit gleichem Namen zwischen zwei Folien in einer Vorschau.
- Klickaktion: zu einer Folie springen oder einen Hinweis zeigen.
- Leinwand: Übersicht aller Folien, Klick öffnet eine Folie.
- Sprech-Coach liest die Sprechernotiz: Füllwörter Deutsch und Englisch, Wörter pro Minute, Variation der Satzlänge. Es wird nichts aufgenommen.

## Modell, C++ und C#

- Kleiner Layout-Klassifikator unter `models/layout_classifier.onnx`. Dieselbe Rechnung liegt in NumPy, damit das Programm ohne onnxruntime läuft.
- „Modell inspizieren“ startet Netron auf diesem ONNX, wenn das Paket installiert ist, nur auf `127.0.0.1`. Sonst zeigt es den Pfad.
- `native/cpp` baut `libodnative.so` (Helligkeit, Kontrast, Graustufen, Strichglättung). Fehlt die Bibliothek, rechnet Python dasselbe.
- `OfficeDisplay.sln` enthält ein C#-Werkzeug für eine Farbreihe. Ohne installiertes `dotnet` nutzt Python dieselbe Reihe.

## Optional online

- Online-KI: OpenAI-kompatibles `POST {basis}/chat/completions` und, nur mit extra Haken, `POST {basis}/images/generations`. Erlaubt sind HTTPS sowie `http://127.0.0.1` und `http://localhost`. Ausgeschaltet bleibt der Aufruf lokal.
- Canva Connect: Markenvorlagen listen, Autofill `create_from_brand_template`, Export als PPTX. OAuth-URL mit PKCE S256. Das Token wird vom Nutzer eingefügt, kein Client-Geheimnis im Programm.
- Lokales Canva-ähnliches Studio bleibt ohne Netz: Vorlagen, Größen, Elemente, Ausrichten, Markenpalette, Fotofilter, Freistellen, Software-3D.

## Nicht enthalten

- Kein Tracking, keine Telemetrie, kein automatischer Netzaufruf.
- Kein Cloud-Videochat und kein Katalog mit fremden Stockmotiven.
- Keine großen Sprachmodelle im Installationspaket und kein Download von Modellgewichten.
