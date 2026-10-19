# Hilfe Office Display

Andreas Meyer, ame@sellerbach.de

Office Display bearbeitet Folien auf diesem Rechner. PowerPoint, OpenOffice, OnlyOffice und SoftMaker lesen den Export `.pptx`. OpenOffice liest zusätzlich `.odp`.

Standard ist offline. Die Statuszeile zeigt „Offline · kein Tracking“, solange die Online-KI nicht freigegeben ist. Danach steht dort „Online an · kein Tracking“. Es gibt kein Tracking.

## Fläche

- Mitte: die aktuelle Folie.
- Rechts: Miniaturen. Ein Klick lädt die Folie. Darunter die Folienaktionen.
- Oben: Werkzeuge, Schrift, Fett, Kursiv, Unterstrichen, Farbe, Thema, Touch-Modus, Stiftstärke, Druckkurve, Glättung.
- Unten: Zeigerart (Maus, Stift, Radierer, Touch).

Themen: hell, dunkel, farbe, graustufen.

## Objekte

Werkzeuge: Auswahl, Text, Rechteck, Ellipse, Rahmen, Pfeil, Stern, Linie, Stift, Marker, Radierer, Diagramm, Verschieben. Zusätzlich Bild, Video und 3D.

Text doppelklicken und tippen. Schriftart, Größe, Fett, Kursiv, Unterstrichen und Farbe gelten für den gewählten Text. Ist die Marke gesperrt, bleiben nur die erlaubten Schriften und Farben.

Ziehen verschiebt. Die Anfasser skalieren. Strg+G gruppiert die Auswahl, Strg+Umschalt+G löst sie. Entf löscht, Strg+D dupliziert.

Objekt auf eine andere Folie: das Objekt mit Umschalt gedrückt auf eine Miniatur rechts ziehen. Alternativ „Bearbeiten → Auf Folie verschieben“.

Bilder, Videos, Texte, PDF, CSV, PPTX und ODP können aus dem Dateidialog oder per Drag-and-drop auf die Folie. Lange Texte werden zu Folien, kurze zu einem Textfeld. CSV und Excel werden zu einem Diagramm.

Hintergründe: volle Fläche als Farbe, Verlauf oder Bild. Die Anpassung ist cover, contain oder kacheln, dazu Deckkraft.

Das Diagramm-Werkzeug setzt beschriftete Beispielwerte `[3, 5, 4]`. Die Reihe ist als Platzhalter benannt und ersetzt die Quelle nicht. „KI → Text zu Folien“ und der Befehl „diagramm“ übernehmen nur Zahlen, die im Text stehen.

## Stift, Tablett, Touch

- Stift im Stiftwerkzeug: Strichstärke folgt dem Druck. Die Kurve glättet über das native Modul oder in Python.
- Radiererseite oder Radiererwerkzeug: trifft einen Strich und entfernt ihn.
- Touch, Schalter „verschieben“: ein Finger zieht die Ansicht, zwei Finger zoomen.
- Touch, Schalter „zeichnen“: der Finger zeichnet im Stift- oder Markerwerkzeug.
- Maus: folgt dem Werkzeug, mit festem Druck.
- Strg und Mausrad: Zoom der Ansicht, nicht der Foliengröße.

Ohne angeschlossenes Tablett bleibt alles mit der Maus bedienbar.

## Dateien

- Speichern: `.odisp` (Zip mit `presentation.json` und Medien).
- Export PPTX und ODP über das Menü Datei.
- Öffnen liest `.odisp`, `.pptx` und `.odp`.
- Tabelle verbinden liest XLSX oder CSV und merkt sich den Dateipfad. Daten aktualisieren liest neu.

## Lokale Gestaltung

Menü KI.

Lokal erzeugen baut einen Foliensatz nur aus dem eingegebenen Satz. Stehen keine Zahlen darin, bleibt das Diagramm ohne erfundene Werte.

Dokument umwandeln liest TXT, MD oder PDF und setzt die Sätze auf Folien. Die Notiz nennt die Quellzeilen.

Befehle auf der aktuellen Folie: `zwei spalten`, `diagramm`, `zeitstrahl`, `dunkler hintergrund`, `heller hintergrund`, `größer`, `kleiner`, `zentrieren`, `folie hinzu`.

Sprech-Coach prüft die Sprechernotiz auf Füllwörter, Länge und Eintönigkeit. Es wird nichts aufgenommen.

Modell inspizieren öffnet das kleine ONNX-Layoutmodell mit Netron, wenn `netron` installiert ist, und nur auf diesem Rechner. Sonst zeigt es den Dateipfad `models/layout_classifier.onnx`.

## Online-KI und Canva

Menü KI → Einstellungen Online-KI / Canva.

Ohne Haken bleibt alles lokal. Mit Haken und hinterlegtem Schlüssel ruft „Online erzeugen“ eine OpenAI-kompatible Chat-API auf und baut daraus Folien. „Markierten Text online umformulieren“ und „Bild online erzeugen“ brauchen denselben Schalter; Bilder zusätzlich den Haken für die Bildgenerierung. Erlaubt sind nur HTTPS sowie `http://127.0.0.1` und `http://localhost`.

Canva Connect liegt unter Menü Canva → Studio und Connect. Markenvorlagen listen, Autofill und PPTX-Export laufen nur mit einem selbst eingefügten Token und nur auf Klick. Die lokale Vorlage, die Größe und die Elemente brauchen kein Konto.

Schlüsseldatei: `~/.config/officedisplay/secrets.json`, Dateimodus 600.

## Bibliothek

Menü Canva → Studio und Connect.

Vorlagen: Pitch, Unterricht, Kennzahlen, Zitat, Vergleich, Team, Titel. Größe anpassen stellt 16:9, 4:3, Quadrat, Story, Portrait, A4, LinkedIn oder Banner ein. Elemente sind Rahmen, Fläche, Kreis, Raute, Stern, Pfeil und Badge. Das sind lokale Formen. Der Canva-Katalog wird nur auf ausdrücklichen Klick abgefragt.

## Weitere Werkzeuge

- Markenführung sperrt Schrift und Palette. Die Datei ist `assets/brand.json`.
- 3D rendert Würfel, Pyramide oder eine OBJ-Datei und legt das Bild auf die Folie.
- Fotofilter: aufhellen, Graustufen, weichzeichnen, schärfen, spiegeln, Eckfarbe freistellen.
- Makro: eine lokale `.py` mit `def run(api)`. Vor dem Lauf kommt eine Rückfrage. `macros/beispiel.py` zeigt die Form.
- Präsentieren zeigt die Folie groß, Notizen darunter, Klick blättert. Objekte können eine Aktion „gehe zu Folie“ oder „Hinweis“ tragen.
- Leinwand zoomt alle Folien. Ein Klick öffnet die gewählte Folie.
- Morph-Vorschau bewegt gleich benannte Objekte zur nächsten Folie. Eingangseffekte sind Einblenden, Einfliegen und Zoom.
- Kamera-Einblendung nutzt ein lokales Aufnahmegerät, wenn Qt eines findet. Sonst erscheint der Hinweis, dass keine Kamera da ist. Einen Videochat gibt es nicht.
- Lokaler Ordner-Sync schreibt `deck.json` in einen gewählten Ordner und liest sie, wenn sich die Dateizeit ändert.
- Verweildauer speichern schreibt die gemessenen Sekunden in eine JSON-Datei. Es wird nichts hochgeladen.

## Tasten

- Strg+N neu, Strg+O öffnen, Strg+S speichern
- Strg+Z rückgängig, Strg+Y wiederholen
- Strg+G gruppieren, Strg+Umschalt+G lösen, Strg+D duplizieren, Entf löschen
- F1 Hilfe
