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
- Konfiguration über `DOCMAN_HOST`, `DOCMAN_PORT`, `DOCMAN_DATA`, `DOCMAN_SEED`, `DOCMAN_WATCH`, `DOCMAN_WATCH_SECONDS`
- OpenAPI unter `/docs`, Health unter `/api/health`
- Fünf Beispieldokumente beim ersten Start, abschaltbar mit `DOCMAN_SEED=0`

### Erfassung

- Upload einer oder mehrerer Dateien, höchstens 20 Stück, höchstens 25 MB je Datei
- Erlaubte Endungen: PDF, TXT, MD, CSV, JSON, LOG, DOCX, PNG, JPG, JPEG, WEBP, GIF
- Andere Endungen werden abgelehnt
- SHA-256-Duplikatsperre
- Dateinamen werden auf den Basisnamen gekürzt
- Text aus Textdateien, aus der PDF-Textebene und aus DOCX, ohne OCR
- Bilder (PNG, JPG, WEBP, GIF) und PDF-Seiten ohne ausreichende Textebene: lokales Tesseract, Sprachen deu und eng, soweit installiert. Die Originaldatei bleibt unverändert, der erkannte Text liegt im Suchindex. Höchstens acht textlose PDF-Seiten je Datei
- Ohne Tesseract bleiben Scans Bilder. Digitale Dateien mit Textebene sind trotzdem durchsuchbar. Installation unter Windows: `winget install UB-Mannheim.TesseractOCR`, Programm in `C:\Program Files\Tesseract-OCR\` oder im PATH. Unter Linux: `tesseract-ocr` plus `tesseract-ocr-deu`
- Schaltfläche „Text neu erkennen“ liest ein Bild oder PDF erneut, nachdem Tesseract installiert wurde
- Ziehen und Ablegen in der Oberfläche
- Posteingang: Schaltfläche und Hintergrundwächter lesen `data\inbox`, übernehmen gültige Dateien und verschieben ungültige nach `data\rejected`. Der Wächter startet mit der Anwendung, Abstand mindestens 3 Sekunden, Standard 8 Sekunden, abschaltbar mit `DOCMAN_WATCH=0`. Ein leerer Posteingang schreibt kein Protokoll
- Metadaten beim Ablegen: Titel, Notiz, Dokumentdatum, Wiedervorlage, Steuerkennzeichen, Korrespondent, Dokumenttyp, Schlagwörter
- Neue Version einer bestehenden Akte: die bisherige Datei liegt unter `data\versions`, die neue Datei wird die aktuelle Fassung. Dieselbe Prüfsumme wie die aktuelle Fassung oder wie ein anderes Dokument wird abgelehnt
- Klartext-Export der extrahierten Textebene als Textdatei

### Dokumente, Metadaten, Suche

- Bibliothek mit Filter auf Titel, Dateiname, Notiz, Volltext und eigene Feldwerte sowie nach Schlagwort, Dokumenttyp, Korrespondent, Status und Steuerkennzeichen
- Gespeicherte Sichten je Benutzer
- Schlagwörter mit Farbe, Korrespondenten mit E-Mail und Notiz, Dokumenttypen mit Beschreibung
- Eigene Felder der Art Text, Zahl oder Datum. Zahlen dürfen ein Komma enthalten. Die Werte gehen in den Suchindex
- Status `neu`, `geprueft`, `freigegeben`, `bezahlt`, `abgelegt`
- Verknüpfung zweier Dokumente, in beide Richtungen sichtbar
- Aufbewahrung bis zu einem Datum sperrt das Löschen. Ein Administrator kann die Sperre mit `force` übergehen. Das ist eine Anwendungssperre, keine GoBD- oder WORM-Archivierung
- Regeln: passen Korrespondent, Dokumenttyp und Schlagwort, soweit gesetzt, setzt die Regel beim Ablegen und Speichern einen Status und kann ein Schlagwort ergänzen. Eine Regel ohne Kriterium wird nicht angelegt und eine leere Regel ignoriert
- Dokumentdetail: Metadaten, Status, Felder, Aufbewahrung, Versionen und Verknüpfungen ändern, Datei und Text herunterladen, Dokument löschen
- Vorschau für PDF und Bilder im Browser, extrahierter Text daneben
- Dashboard: Anzahl, Speicher, steuerrelevante Dokumente, Indexgröße, zuletzt abgelegt, Wiedervorlagen bis 30 Tage einschließlich überfälliger Termine, ob Tesseract erreichbar ist
- TF-IDF-Index mit Kosinusähnlichkeit, deutschen und englischen Füllwörtern, Textauszug und Score
- Der Index umfasst Titel, Dateiname, Notiz, Volltext inklusive OCR-Text, Korrespondent, Dokumenttyp, Schlagwörter, Status und eigene Feldwerte
- Schlagwörter bleiben sinnvoll, weil sie die Treffermenge eingrenzen, Regeln auslösen und Begriffe tragen, die im Dokumenttext nicht stehen
- Neuaufbau nach Änderungen, über die Schaltfläche und über `cli.py reindex`
- Kommandozeilensuche: `cli.py search`

### Zugang und Protokoll

- Benutzername und Passwort, PBKDF2-HMAC-SHA256
- Sitzungscookie, 14 Tage, HttpOnly, SameSite Lax; in der Datenbank liegt nur der SHA-256 des Tokens
- Schreibende API-Aufrufe verlangen den Header `X-DocMan: 1`
- Administrator legt weitere Benutzer an und vergibt das Admin-Flag
- Passwortwechsel in der Oberfläche; das Startpasswort `admin` wird zum Wechsel angezeigt
- Jede angemeldete Person darf lesen, ändern, löschen, herunterladen und Stammdaten pflegen
- Protokoll der letzten 200 Ereignisse: Anmeldung, Fehlanmeldung, Abmeldung, Passwort, Benutzeranlage, Upload, Änderung, Löschung, Download, Version, Verknüpfung, Text-Export, OCR, Suche, Neuindex, Posteingang
- Zeiten in der Oberfläche in Europe/Berlin

### Oberfläche

- Dunkler Webclient ohne Plugin: Übersicht, Dokumente, Suche, Stammdaten, Protokoll, Dokument, Upload, Version, Verknüpfung, eigene Felder, Regeln, gespeicherte Sichten, Passwort
- REST-API unter `/api`

## Einordnung

DocMan liegt näher an einem kleinen Paperless-Archiv als an ecoDMS oder Docutain: Tags, Korrespondenten, Dokumenttypen, lokaler Volltext, Posteingang, Versionen, Verknüpfungen, Status, eigene Felder, einfache Regeln und Weboberfläche. Gescannte und fotografierte Seiten liest ein lokales Tesseract, wenn es installiert ist. Die Aufbewahrungssperre hält ein Dokument bis zu einem Datum gegen Löschen fest. Es gibt keine PDF/A-Wandlung, keine automatische KI-Verschlagwortung, keine GoBD-Archivierung, keine Office- oder Mail-Plugins, keine Scanner- oder Smartphone-App und keine Zahlungsfunktion.

## Daten

| Pfad | Inhalt |
| --- | --- |
| `data\docman.db` | SQLite |
| `data\files` | aktuelle Dateien |
| `data\versions` | frühere Fassungen |
| `data\inbox` | noch nicht übernommene Dateien |
| `data\rejected` | abgelehnte Posteingänge |

`DOCMAN_HOST`, `DOCMAN_PORT`, `DOCMAN_DATA`, `DOCMAN_SEED`, `DOCMAN_WATCH` und `DOCMAN_WATCH_SECONDS` stehen in `.env.example`. Die Anwendung liest die Variablen aus der Umgebung. Standardadresse ist nur `127.0.0.1`. Der Posteingangs-Wächter ist standardmäßig an.

## Grundlagen

Der Funktionsumfang folgt einem Dokumentenarchiv: Dokumente, Korrespondenten, Dokumenttypen, Schlagwörter, Volltext und Protokoll. Quelle der fachlichen Orientierung: [JayRHa/document-manager](https://github.com/JayRHa/document-manager).

Die Suche folgt einem kleinen Suchindex: Terme, Termfrequenz, inverse Dokumenthäufigkeit, Ranking über die Kosinusähnlichkeit. Quelle der fachlichen Orientierung: [JasonSu14/Mini_Search_Engine](https://github.com/JasonSu14/Mini_Search_Engine).

Diese Codebasis ist eine eigene Umsetzung und kein Abbild der beiden Repositories. Es gibt keinen externen KI- oder Vektordienst.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```
