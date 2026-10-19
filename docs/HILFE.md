# Hilfe Office Display

Andreas Meyer, ame@sellerbach.de

Office Display bearbeitet Folien auf diesem Rechner. PowerPoint, OpenOffice, OnlyOffice und SoftMaker lesen den Export `.pptx`. OpenOffice liest zusätzlich `.odp`.

Standard ist offline. Die Statuszeile zeigt „Offline · kein Tracking“, solange die Online-KI nicht freigegeben ist. Danach steht dort „Online an · kein Tracking“. Es gibt kein Tracking.

## Fläche

- Mitte: die aktuelle Folie.
- Rechts: Miniaturen. Ein Klick lädt die Folie. Darunter die Folienaktionen.
- Oben: Leisten Auswahl, Text, Grafik/Foto, Video und Player. Menü Ansicht schaltet jede Leiste ein und aus. „Alle Leisten anzeigen“ setzt sie alle an. Der Zustand bleibt in den Programmeinstellungen. Die Folienaktionen bleiben sichtbar.
- Unten: Zeigerart (Maus, Stift, Radierer, Touch).

Themen: hell, dunkel, farbe, graustufen.

## Objekte

Werkzeuge: Auswahl, Text, Rechteck, Ellipse, Rahmen, Pfeil, Stern, Linie, Stift, Marker, Radierer, Diagramm, Verschieben. Zusätzlich Bild, Video, Kamera und 3D. Die Textleiste setzt Schrift, Größe, Fett, Kursiv, Unterstrichen, Farbe und Ausrichtung. Die Grafikleiste trägt Formen, Stift, Stärke, Druck, Glättung, Bild und Filter. Die Videoleiste fügt ein Video ein oder öffnet die Kamera. Die Playerleiste startet Präsentieren, Slideshow, Leinwand, Morph und den Eingangseffekt.

Text doppelklicken und tippen. Schriftart, Größe, Fett, Kursiv, Unterstrichen und Farbe gelten für den gewählten Text. Ist die Marke gesperrt, bleiben nur die erlaubten Schriften und Farben.

Ziehen verschiebt. Die Anfasser skalieren. Strg+G gruppiert die Auswahl, Strg+Umschalt+G löst sie. Entf löscht, Strg+D dupliziert.

Objekt auf eine andere Folie: das Objekt mit Umschalt gedrückt auf eine Miniatur rechts ziehen. Alternativ „Bearbeiten → Auf Folie verschieben“.

Bilder, Videos, Texte, PDF, CSV, PPTX und ODP können aus dem Dateidialog oder per Drag-and-drop auf die Folie. Lange Texte werden zu Folien, kurze zu einem Textfeld. CSV und Excel werden zu einem Diagramm.

Hintergründe: volle Fläche als Farbe, Verlauf oder Bild. Die Anpassung ist cover, contain oder kacheln. „Gestalten → Deckkraft Hintergrund“ setzt die Deckkraft des Hintergrundbilds in Prozent. 100 ist deckend, 0 ist durchsichtig; darunter bleibt die Folienfarbe. Miniatur und Player nutzen denselben Wert `background.opacity`.

Rechtsklick auf Rechteck, Ellipse, Rahmen, Pfeil, Stern, Linie oder Fläche öffnet ein Menü: Füllfarbe ändern, Linienfarbe ändern, Bild laden, als Folienhintergrund übernehmen. Das Bild füllt die Form. Als Hintergrund übernimmt es die aktuelle Deckkraft. Die Auswahl bleibt bestehen. Linksklick verschiebt und wählt wie bisher.

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
- Öffnen und Import PPTX lesen `.pptx` (auch neben `.odisp` und `.odp` im ersten Filter). Folien, Texte, Bilder und einfache Formen werden übernommen. Eine defekte Datei bleibt liegen; es erscheint eine Meldung, die Präsentation wird nicht geleert. Ziehen einer `.pptx` auf die Fläche hängt die Folien an.
- Slideshow: Datei → Slideshow öffnen, speichern, aus Dateien anlegen, als Präsentation exportieren. Das Paket ist `.oshow` (Zip mit `slideshow.json` und Medien). Einträge sind Bild, Video oder Text (TXT, MD, PDF). Der Export `.odisp` macht aus jedem Eintrag eine Folie. Öffnen einer `.odisp` oder `.pptx` legt je Folie einen Eintrag an, als Text mit erstem Bild, als Video oder als gerenderte Vorschau.
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

Magic Design liegt unter Menü Canva → Magic Design…. Ein Satz baut lokal einen Foliensatz: Titelfolie mit vollflächigem Verlauf, Inhaltsfolien und die passende lokale Vorlage. Verwendet werden nur Wörter aus dem Satz, keine erfundenen Zahlen. Ist schon Inhalt da, kommt eine kurze Rückfrage, sonst wird ersetzt. „Über Canva erzeugen“ sendet denselben Satz nur auf Klick und nur mit Token an den dokumentierten Aufruf `POST /rest/v1/generations` (HTTPS, Bearer) und zeigt die Design-ID. PPTX holt danach Studio und Connect mit dieser Design-ID. Ohne Token geht nichts ins Netz. Das Öffnen des Dialogs ruft Canva nicht auf.

Schlüsseldatei: `~/.config/officedisplay/secrets.json`, Dateimodus 600.

## Bibliothek

Menü Canva → Studio und Connect.

Vorlagen: Pitch, Unterricht, Kennzahlen, Zitat, Vergleich, Team, Titel. Größe anpassen stellt 16:9, 4:3, Quadrat, Story, Portrait, A4, LinkedIn oder Banner ein. Elemente sind Rahmen, Fläche, Kreis, Raute, Stern, Pfeil und Badge. Das sind lokale Formen. Der Canva-Katalog wird nur auf ausdrücklichen Klick abgefragt.

## Weitere Werkzeuge

- Markenführung sperrt Schrift und Palette. Die Datei ist `assets/brand.json`.
- 3D rendert Würfel, Pyramide oder eine OBJ-Datei und legt das Bild auf die Folie.
- Fotofilter: aufhellen, Graustufen, weichzeichnen, schärfen, spiegeln, Eckfarbe freistellen.
- Makro: eine lokale `.py` mit `def run(api)`. Vor dem Lauf kommt eine Rückfrage. `macros/beispiel.py` zeigt die Form.
- Präsentieren (Menü Präsentieren oder F5) öffnet den Vollbild-Player. Die Folie füllt den Schirm. Weiter: Klick, Pfeil rechts, Leertaste, Bild ab. Zurück: Pfeil links, Bild auf. Pos1 erste Folie, Ende letzte, Escape beendet. B oder Punkt legt eine schwarze Blende, W eine weiße; dieselbe Taste hebt sie auf. N blendet die schmale Leiste mit Foliennummer und Sprechernotiz ein und aus. Klick-Aktionen „gehe zu Folie“ und „Hinweis“ laufen nur ohne Blende.
- Slideshow abspielen nutzt denselben Player. Bilder liegen seitenfüllend im schwarzen Rand (contain). Video spielt, wenn Qt Multimedia das Format kann, sonst stehen Pfad und Hinweis. Text ist scrollbar.
- Leinwand zoomt alle Folien. Ein Klick öffnet die gewählte Folie.
- Morph-Vorschau bewegt gleich benannte Objekte zur nächsten Folie. Eingangseffekte sind Einblenden, Einfliegen und Zoom.
- Kamera-Einblendung nutzt ein lokales Aufnahmegerät, wenn Qt eines findet. Sonst erscheint der Hinweis, dass keine Kamera da ist. Einen Videochat gibt es nicht.
- Lokaler Ordner-Sync schreibt `deck.json` in einen gewählten Ordner und liest sie, wenn sich die Dateizeit ändert.
- Verweildauer speichern schreibt die gemessenen Sekunden in eine JSON-Datei. Es wird nichts hochgeladen.

## Tasten

- Strg+N neu, Strg+O öffnen, Strg+S speichern
- Strg+Z rückgängig, Strg+Y wiederholen
- Strg+G gruppieren, Strg+Umschalt+G lösen, Strg+D duplizieren, Entf löschen
- F1 Hilfe, F5 Präsentieren
- Im Player: Pfeile, Leertaste, Bild auf/ab, Pos1, Ende, Escape, B, Punkt, W, N

## Installieren

Unter Windows den entpackten Ordner öffnen und `installer\install.bat` doppelklicken. Fehlt Python, nennt der Installer https://www.python.org/downloads/ und bricht ab. Danach startet `Office Display.bat` das Programm. Unter Linux und macOS `./installer/install.sh`, danach `./Office Display.sh`.
