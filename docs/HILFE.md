# Hilfe Office Display

Andreas Meyer, ame@sellerbach.de

Office Display bearbeitet Folien auf diesem Rechner. PowerPoint, OpenOffice, OnlyOffice und SoftMaker lesen den Export `.pptx`. OpenOffice liest zusätzlich `.odp`.

## Fläche

- Mitte: die aktuelle Folie.
- Rechts: Miniaturen. Ein Klick lädt die Folie.
- Oben: Werkzeuge, Schrift, Thema, Touch-Modus, Stiftstärke.
- Unten: Zeigerart (Maus, Stift, Radierer, Touch) und ob Online-KI aus ist.

Themen: hell, dunkel, farbe, grau.

## Objekte

Werkzeuge: Auswahl, Text, Rechteck, Ellipse, Rahmen, Pfeil, Stern, Linie, Stift, Marker, Radierer, Diagramm, Verschieben.

Text doppelklicken und tippen. Schriftart, Größe, Fett, Kursiv, Unterstrichen und Farbe gelten für den gewählten Text. Ist die Marke gesperrt, bleiben nur die erlaubten Schriften und Farben.

Ziehen verschiebt. Die Anfasser skalieren. Strg+G gruppiert die Auswahl, Strg+Umschalt+G löst sie. Entf löscht, Strg+D dupliziert.

Objekt auf eine andere Folie: das Objekt mit Umschalt gedrückt auf eine Miniatur rechts ziehen. Alternativ „Bearbeiten → Auf Folie verschieben“.

Bilder, Videos, Texte, PDF, CSV, PPTX und ODP können aus dem Dateidialog oder per Drag-and-drop auf die Folie. Lange Texte werden zu Folien, kurze zu einem Textfeld. CSV und Excel werden zu einem Diagramm.

Hintergründe: volle Fläche als Farbe, Verlauf oder Bild (decken, im Datenmodell auch enthalten und kacheln, Deckkraft, Versatz).

## Stift, Tablett, Touch

- Stift im Stiftwerkzeug: Strichstärke folgt dem Druck. Die Kurve glättet über das native Modul oder in Python.
- Radiererseite oder Radiererwerkzeug: trifft einen Strich und entfernt ihn.
- Touch, Schalter „verschieben“: ein Finger zieht die Ansicht, zwei Finger zoomen.
- Touch, Schalter „zeichnen“: der Finger zeichnet im Stift- oder Markerwerkzeug.
- Maus: folgt dem Werkzeug, mit festem Druck.
- Strg und Mausrad: Zoom der Ansicht, nicht der Foliengröße.

Ohne angeschlossenes Tablett bleibt alles mit der Maus bedienbar. Die Zuordnung von Gerät zu Aktion ist unabhängig von Qt testbar.

## Dateien

- Speichern: `.odisp` (Zip mit `presentation.json` und Medien).
- Export PPTX und ODP über das Menü Datei.
- Öffnen liest `.odisp`, `.pptx` und `.odp`.

## KI

Menü KI.

Offline erzeugen baut einen Foliensatz nur aus dem eingegebenen Satz. Diagrammzahlen, die nicht im Satz stehen, heißen Beispielwerte.

Dokument umwandeln liest TXT, MD oder PDF und setzt die Sätze auf Folien. Die Notiz nennt die Quellzeilen.

Befehle auf der aktuellen Folie: `zwei spalten`, `diagramm`, `zeitstrahl`, `dunkler hintergrund`, `heller hintergrund`, `größer`, `kleiner`, `zentrieren`, `folie hinzu`.

Sprech-Coach prüft die Sprechernotiz auf Füllwörter, Länge und Eintönigkeit. Es wird nichts aufgenommen.

Modell inspizieren öffnet das kleine ONNX-Layoutmodell mit Netron, wenn `netron` installiert ist. Sonst zeigt es den Dateipfad `models/layout_classifier.onnx`.

Online erzeugen, Umformulieren und Bild erzeugen gehen nur, wenn unter „Einstellungen Online-KI / Canva“ der Haken gesetzt und ein Schlüssel gespeichert ist. Erlaubt sind HTTPS und `http://127.0.0.1` bzw. `http://localhost` für ein lokales Modell wie Ollama. Der Schlüssel steht in `~/.config/officedisplay/secrets.json` mit Dateirechten 600.

## Canva

Menü Canva → Studio.

Lokal: Vorlage anwenden, Magic Resize, Element einfügen.

Canva Connect: Token eintragen, dann Markenvorlagen listen, Autofill oder PPTX-Export anstoßen. Das sind Aufrufe an `https://api.canva.com/rest/v1`. Nötige Berechtigungen des Tokens: `brandtemplate:meta:read`, `brandtemplate:content:read`, `design:content:read`, `design:content:write`. Ein Autofill-Job und ein Export-Job sind asynchron; die Antwort enthält die Job-Kennung. Fertige PPTX-Dateien danach über Import PPTX laden.

Die OAuth-Adresse mit PKCE kann das Programm zusammensetzen. Den Zugriffstoken holt die eigene Canva-Integration; das Programm enthält kein Client-Geheimnis.

## Weitere Werkzeuge

- Markenführung sperrt Schrift und Palette.
- Tabelle verbinden liest XLSX oder CSV und merkt sich den Dateipfad. Daten aktualisieren liest neu.
- 3D rendert Würfel, Pyramide oder eine OBJ-Datei und legt das Bild auf die Folie.
- Makro: eine lokale `.py` mit `def run(api)`. Vor dem Lauf kommt eine Rückfrage. `macros/beispiel.py` zeigt die Form.
- Präsentieren zeigt die Folie groß, Notizen darunter, Klick blättert. Objekte können `action` vom Typ `goto` oder `popup` tragen.
- Leinwand zoomt alle Folien.
- Morph-Vorschau bewegt gleich benannte Objekte zur nächsten Folie.
- Verweildauer speichern schreibt die gemessenen Sekunden in eine JSON-Datei neben dem, was Sie wählen. Es wird nichts hochgeladen.

## Tasten

- Strg+N neu, Strg+O öffnen, Strg+S speichern
- Strg+Z rückgängig, Strg+Y wiederholen
- Strg+G gruppieren, Strg+Umschalt+G lösen, Strg+D duplizieren, Entf löschen
- F1 Hilfe
