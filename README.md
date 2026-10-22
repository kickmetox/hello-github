# DocMan

Lokales Dokumentenarchiv für Python und Visual Studio. Dateien, Stammdaten und der Suchindex bleiben im Projektordner.

Zielordner auf dem Windows-Rechner: `I:\AI_Temp\DocMan`. Dieses Repository ist das Projekt. `DocMan.sln` dort öffnen oder den Checkout genau in diesen Ordner legen.

## Start in Visual Studio

1. Python-Workload in Visual Studio installiert lassen.
2. `DocMan.sln` öffnen.
3. Im Projektmappen-Explorer die Python-Umgebung hinzufügen. PowerShell im Projektordner:

```powershell
.\setup.ps1
```

4. Die entstandene `.venv` dem Projekt als Umgebung zuweisen.
5. Startdatei ist `run.py`. Mit F5 starten.
6. Browser: <http://127.0.0.1:8000>
7. Erstanmeldung: `admin` / `admin`. Das Passwort danach in der Oberfläche ändern.

Ohne Visual Studio:

```powershell
.\.venv\Scripts\python.exe run.py
```

Kommandozeile, analog zum Mini-Search-Engine-Ablauf:

```powershell
.\.venv\Scripts\python.exe cli.py search "Kündigung Mietvertrag"
.\.venv\Scripts\python.exe cli.py reindex
```

## Funktionsumfang

DocMan ist ein lokales Ein-Prozess-Archiv. Die folgende Liste beschreibt nur Funktionen, die im Programm vorhanden sind.

### Betrieb

- Python-Anwendung, Projektmappe `DocMan.sln`, Start über `run.py` oder `cli.py serve`
- Lauscht standardmäßig nur auf `127.0.0.1`
- SQLite-Datei `data\docman.db`
- Dateiablage `data\files`, Posteingang `data\inbox`, Abweisungen `data\rejected`
- Konfiguration über `DOCMAN_HOST`, `DOCMAN_PORT`, `DOCMAN_DATA`, `DOCMAN_SEED`
- OpenAPI unter `/docs`, Health unter `/api/health`
- Fünf Beispieldokumente beim ersten Start, abschaltbar mit `DOCMAN_SEED=0`

### Erfassung

- Upload einer oder mehrerer Dateien, höchstens 20 Stück, höchstens 25 MB je Datei
- Erlaubte Endungen: PDF, TXT, MD, CSV, JSON, LOG, DOCX, PNG, JPG, JPEG, WEBP, GIF
- Andere Endungen werden abgelehnt
- SHA-256-Duplikatsperre
- Dateinamen werden auf den Basisnamen gekürzt
- Text aus Textdateien, aus der PDF-Textebene und aus DOCX
- Bilder bleiben als Datei erhalten; ohne Textebene sucht das Archiv über Titel, Notiz und Stammdaten
- Ziehen und Ablegen in der Oberfläche
- Posteingang: Schaltfläche liest `data\inbox`, übernimmt gültige Dateien und verschiebt ungültige nach `data\rejected`
- Metadaten beim Ablegen: Titel, Notiz, Dokumentdatum, Wiedervorlage, Steuerkennzeichen, Korrespondent, Dokumenttyp, Schlagwörter

### Dokumente, Metadaten, Suche

- Bibliothek mit Filter auf Titel, Dateiname, Notiz und Volltext sowie nach Schlagwort, Dokumenttyp, Korrespondent und Steuerkennzeichen
- Schlagwörter mit Farbe, Korrespondenten mit E-Mail und Notiz, Dokumenttypen mit Beschreibung
- Dokumentdetail: Metadaten ändern, Datei herunterladen, Dokument löschen
- Vorschau für PDF und Bilder im Browser, extrahierter Text daneben
- Dashboard: Anzahl, Speicher, steuerrelevante Dokumente, Indexgröße, zuletzt abgelegt, Wiedervorlagen bis 30 Tage einschließlich überfälliger Termine
- TF-IDF-Index mit Kosinusähnlichkeit, deutschen und englischen Füllwörtern, Textauszug und Score
- Der Index umfasst Titel, Dateiname, Notiz, Volltext, Korrespondent, Dokumenttyp und Schlagwörter
- Neuaufbau nach Änderungen, über die Schaltfläche und über `cli.py reindex`
- Kommandozeilensuche: `cli.py search`

### Zugang und Protokoll

- Benutzername und Passwort, PBKDF2-HMAC-SHA256
- Sitzungscookie, 14 Tage, HttpOnly, SameSite Lax; in der Datenbank liegt nur der SHA-256 des Tokens
- Schreibende API-Aufrufe verlangen den Header `X-DocMan: 1`
- Administrator legt weitere Benutzer an und vergibt das Admin-Flag
- Passwortwechsel in der Oberfläche; das Startpasswort `admin` wird zum Wechsel angezeigt
- Jede angemeldete Person darf lesen, ändern, löschen, herunterladen und Stammdaten pflegen
- Protokoll der letzten 200 Ereignisse: Anmeldung, Fehlanmeldung, Abmeldung, Passwort, Benutzeranlage, Upload, Änderung, Löschung, Download, Suche, Neuindex, Posteingang
- Zeiten in der Oberfläche in Europe/Berlin

### Oberfläche

- Dunkler Webclient ohne Plugin: Übersicht, Dokumente, Suche, Stammdaten, Protokoll, Dokument, Upload, Passwort
- REST-API unter `/api`

## Einordnung

DocMan liegt näher an einem kleinen Paperless-Archiv als an ecoDMS oder Docutain: Tags, Korrespondenten, Dokumenttypen, lokaler Volltext, manueller Posteingangsordner und Weboberfläche. Es gibt keine OCR-Engine, keine PDF/A-Wandlung, keine GoBD-Archivierung, keine Office- oder Mail-Plugins, keine Scanner- oder Smartphone-App und keine Zahlungsfunktion.

## Daten

| Pfad | Inhalt |
| --- | --- |
| `data\docman.db` | SQLite |
| `data\files` | abgelegte Dateien |
| `data\inbox` | noch nicht übernommene Dateien |
| `data\rejected` | abgelehnte Posteingänge |

`DOCMAN_HOST`, `DOCMAN_PORT`, `DOCMAN_DATA` und `DOCMAN_SEED` stehen in `.env.example`. Die Anwendung liest die Variablen aus der Umgebung. Standardadresse ist nur `127.0.0.1`.

## Grundlagen

Der Funktionsumfang folgt einem Dokumentenarchiv: Dokumente, Korrespondenten, Dokumenttypen, Schlagwörter, Volltext und Protokoll. Quelle der fachlichen Orientierung: [JayRHa/document-manager](https://github.com/JayRHa/document-manager).

Die Suche folgt einem kleinen Suchindex: Terme, Termfrequenz, inverse Dokumenthäufigkeit, Ranking über die Kosinusähnlichkeit. Quelle der fachlichen Orientierung: [JasonSu14/Mini_Search_Engine](https://github.com/JasonSu14/Mini_Search_Engine).

Diese Codebasis ist eine eigene Umsetzung und kein Abbild der beiden Repositories. Es gibt keinen externen KI- oder Vektordienst.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```
