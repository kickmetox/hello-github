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

- Ablage von PDF, Text, Markdown, CSV, JSON, DOCX und Bildern (bis 25 MB)
- Text aus PDF-Textebene, DOCX und Textdateien
- Schlagwörter, Korrespondenten, Dokumenttypen, Steuerkennzeichen, Wiedervorlage
- Bibliotheksfilter und Dokumentvorschau
- TF-IDF-Suche mit Kosinusähnlichkeit und Textauszug
- Posteingang `data\inbox` (Schaltfläche „Posteingang“)
- Benutzer, Sitzungscookie, Protokoll
- Beispieldokumente beim ersten Start

Bilder und gescannte PDFs ohne Textebene bleiben als Datei erhalten und sind über Titel, Notiz und Stammdaten suchbar.

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
