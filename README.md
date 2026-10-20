# ReckonGrid

Tabellenkalkulation mit Datenbankfunktionen. Andreas Meyer, ame@sellerbach.de.

ReckonGrid rechnet lokal im Browser: deutsche und englische Formeln, dynamische Arrays, intelligente Tabellen, D-Funktionen, Pivot, Diagramme, Import und Export. Zusammenarbeit läuft über `BroadcastChannel` zwischen Tabs desselben Browsers. Der Formel-Assistent erzeugt, erklärt und repariert Formeln mit festen Regeln, ohne Cloud-Modell.

## Start

```bash
npm install
npm test
npm run dev
```

Die Entwicklungsumgebung liegt auf Port 5173. `npm run build` prüft TypeScript und schreibt `dist/`. `npm run package` baut zusätzlich `release/ReckonGrid-1.0.0-Setup.zip` und `release/ReckonGrid-1.0.0-Workspace.zip`.

## Installation

Das Setup-Archiv enthält die kompilierte App. Unter Windows `install.ps1` ausführen, unter Linux `sh install.sh`. Ohne Installation startet `Start-ReckonGrid.bat` beziehungsweise `sh start.sh` die App im Browser auf `127.0.0.1`. Es sind keine Administratorrechte nötig.

Die Beispielmappe **Umsatzdatenbank** ist beim ersten Öffnen aktiv. `DSUMME` für Region Nord und Jahr nach 2025 steht in H9. Änderungen bleiben unter dem Schlüssel `reckongrid-v1` im lokalen Speicher des Browsers.

## Bedienung

Die Leiste folgt dem dunklen PlanMaker-Aufbau: Datei, Start, Einfügen, Layout, Formeln, Daten, Überprüfen, Ansicht. Das Namensfeld springt zu einer Adresse, die Bearbeitungsleiste und `fx` öffnen die Funktionsbibliothek. Pfeiltasten, Enter, Tab, F2, Entf, Strg+Z, Strg+B/I/U, Strg+C/X/V und Strg+F arbeiten wie in einer Tabellenkalkulation.

## Formeln

Argumente werden mit Strichpunkt getrennt, Dezimalzahlen mit Komma. Englische Namen und Kommas werden ebenfalls gelesen. Eingebaute Bereiche sind Mathematik, Statistik, Logik, Text, Datum, Suche (`SVERWEIS`, `XVERWEIS`, `INDEX`/`VERGLEICH`), dynamische Arrays (`FILTER`, `SORTIEREN`, `EINDEUTIG`, `SEQUENZ`), Matrix (`MMULT`, `MINV`, `MDET`), Finanzen (`RMZ`, `ZW`, `BW`, `IKV`), D-Funktionen (`DSUMME`, `DMITTELWERT`, `DANZAHL`, `DMAX`, `DMIN`, `DPRODUKT`, `DSTABW`, `DVARIANZ`, `DAUSZUG`), `LAMBDA`/`LET`/`MAP`, `ABFRAGE` und technische Funktionen (`UMWANDELN`, Zahlensysteme, komplexe Zahlen).

`TEILERGEBNIS` ignoriert per Filter, Gliederung oder Zeilenhöhe 0 ausgeblendete Zeilen.

## Dateien

| Format | Richtung |
| --- | --- |
| `.rggrid` | Lesen und Schreiben, optional AES-GCM |
| `.xlsx`, `.xls`, `.ods` | Lesen und Schreiben über SheetJS, Formeln deutsch/englisch |
| `.csv`, `.txt`, `.tsv` | Lesen und Schreiben, Semikolon oder erkanntes Trennzeichen |

Blattschutz speichert ein SHA-256 des Passworts. Die Dateiverschlüsselung ist AES-GCM mit PBKDF2.

## Automatisierung

JavaScript läuft über `rg.get`, `rg.set`, `rg.value`, `rg.style`, `rg.sheet`, `rg.log`. Python versteht Zuweisungen, `range`-Schleifen, `print`, `get` und `set`. VBA versteht `Range`, `Cells`, `MsgBox` und `For`/`Next`. Der Makro-Rekorder schreibt JavaScript.

## Grenzen

Es gibt keinen entfernten Co-Authoring-Server, keine Live-Börse und kein gehostetes KI-Modell. Kurse im Dialog „Beispielkurse“ sind ein fest hinterlegter Katalog. Die Regionenkarte fasst die Werte Nord, Süd, Ost, West und DACH aus dem Blatt zusammen. Web-Import und Webhooks brauchen eine erreichbare Adresse.
