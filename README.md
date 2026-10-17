# ShatuIDE

Lokale Python-IDE von Andreas Meyer (ame@sellerbach.de).

Unter Windows ist das Arbeitsverzeichnis `D:\AI_Temp\ShatuIDE`. Die IDE liest und schreibt in diesem Ordner ohne zusätzliche Sandbox. Der eingebaute Server hört nur auf `127.0.0.1`.

## Start

```bash
python3 shatuide.py
```

Unter Windows: `ShatuIDE.bat` oder `py -3 shatuide.py`.

**Datei → Öffnen** lädt vorhandene Python-Skripte und andere Textdateien aus dem Workspace, aus darüberliegenden Ordnern oder vom Home-Verzeichnis. Dateien außerhalb des Workspace sind nur lesbar. **Datei laden** übernimmt Dateien aus der Dateiauswahl; Speichern schreibt sie in den Workspace. **Bearbeiten** schneidet aus, kopiert die Markierung oder einen Zeilenbereich und fügt ein. **Fenster → Zweites Fenster** öffnet eine weitere IDE-Ansicht.

Das Menüband hat die Reiter **Start**, **Entwurf**, **Erzeugen** und **Ansicht**. Darunter liegen Zwischenablage, Starten, Debug, Baukasten, GUI, EXE, MSI und die Fenster. Rechts listet **Funktionen** die Funktionen, Methoden, Shell-Funktionen oder Sprungmarken der offenen Datei. **Eigenschaften** zeigt Name, Art und Zeile. Ein Klick springt an die Stelle, **Im Fenster prüfen** startet die Funktion getrennt von der Datei. Die KI bleibt im selben Bereich als Reiter.

**Strg+F** sucht in der offenen Datei, **Strg+H** ersetzt darin. Groß/Klein, ganzes Wort und reguläre Ausdrücke lassen sich umschalten. **Strg+Umschalt+H** ersetzt im Workspace, nach einer Vorschau und nur in Dateien dieses Ordners. Weitere Editorbefehle: Zeile kommentieren, duplizieren, verschieben, löschen und verbinden, Einrücken, Groß-/Kleinschreibung, nächstes Vorkommen, Gehe zu Zeile und Zeilenumbruch.

Bash- und PowerShell-Skripte lassen sich laden und bearbeiten. **Ausführen** startet Bash beziehungsweise PowerShell (`pwsh` oder `powershell`, auch Windows PowerShell 32-bit und 64-bit, sobald beide vorhanden sind). **Syntax prüfen** nutzt `bash -n` oder den PowerShell-Parser. **Format** rückt Klammern und Shell-Blöcke ein. **Debug** hält an Haltepunkten an, auch in weiteren Dateien und Modulen im selben Ordner, zeigt Variablen und geht schrittweise weiter. Fehlt der Interpreter, meldet die IDE das, statt ein Ergebnis zu erfinden.

**Erzeugen → Baukasten** setzt ein Skript aus Modulen zusammen: Eingabe, Ausgabe, Rechnen, Text, Dateien, Ordner, CSV, JSON, SQLite, Webseite, Bedingung und Pause. Die Module laufen von oben nach unten. `{Variable}` setzt einen früheren Wert ein. Der Kasten liegt unter `baukasten/`, das Skript unter `ausgabe/`. **Erzeugen → Skript aus Abfrage** fragt Sprache, Name, Aktion, Aufgabe und die Fragen, die das Skript später stellt. Daraus entsteht ohne Sprachmodell ein lauffähiges Python-, PowerShell-, Bash- oder Batch-Skript unter `ausgabe/`. Ein freier Prompt füllt leere Felder. Ist das Kästchen für das Sprachmodell gesetzt und unter **KI** eine Verbindung gespeichert, übernimmt die IDE den Codeblock aus der Antwort. **Datenbank erzeugen** legt SQLite als Datei im Workspace an und schreibt das SQL daneben. PostgreSQL und MySQL bekommen das SQL-Skript; MongoDB ein Schema und ein Python-Skript. Anlegen auf einem Server braucht den jeweiligen Treiber und eine Verbindung.

**Erzeugen** macht aus dem Skript ein Programm: Python mit installiertem PyInstaller als EXE inklusive Interpreter, sonst eine EXE (MinGW oder `csc`) beziehungsweise ein Linux-Programm (`gcc`), das den Interpreter auf dem Zielrechner startet. **MSI-Installer** packt die Dateien mit `msibuild` und legt zusätzlich eine WiX-Quelle ab. **Modul aus Funktionen** schreibt `.psm1` und `.psd1` aus Funktionen oder aus Kommentarhilfe mit `.NAME`. **Funktion erzeugen** baut eine erweiterte Funktion mit Kommentarhilfe. **GUI entwerfen** setzt Beschriftung, Schaltfläche, Eingabe, Auswahl und Liste auf eine Fläche und schreibt WinForms-PowerShell oder tkinter. **Windows-Dienst** schreibt das Dienstskript plus Installation und Entfernung; anlegen lässt sich der Dienst unter Windows mit Administratorrechten. **Leistung messen** nennt Laufzeit und Speicher. **PS-Hilfe** zeigt `Get-Help`. **Remote** führt PowerShell lokal, per WinRM oder per SSH aus und kann den Ablauf verfolgen. **Datei → Wiederherstellen** holt ungespeicherte Puffer zurück. Git bleibt die Versionsverwaltung für alle diese Dateien.

`.json` wird mit Schlüsseln, Zeichenketten, Zahlen und `true`/`false`/`null` gefärbt. **Syntax prüfen** und die Problemleiste nennen die Fehlerzeile. **Format** rückt das JSON ein. Ausführen und Debuggen gibt es für JSON nicht.

**Alt+F5** prüft die markierte Zeile oder den Abschnitt in einem eigenen Fenster. **Umschalt+Alt+F5** nimmt die Funktion, Methode oder Klasse an der Schreibmarke, ruft sie ohne Argumente auf, spielt ihren Doctest oder genau diesen Test. Die geöffnete Datei bleibt unverändert. Im Fenster kann der Ausschnitt vor einem erneuten Lauf geändert werden.

Installation in das Zielverzeichnis, ohne vorhandene Icons zu überschreiben:

```bash
python install.py
```

Auf diesem Linux-System gibt es kein Laufwerk `D:`. `install.py` kopiert erst unter Windows nach `D:\AI_Temp\ShatuIDE`.

## Icon

Liegt im Programmordner bereits `icon.png`, `icon.ico`, `logo.png` oder `grafik.png`, wird diese Datei verwendet. Eine nicht quadratische PNG wird auf das Quadrat in der Mitte zugeschnitten. Sonst gilt `assets/icon.png`.

## Funktionen

- Menüband mit Start, Entwurf, Erzeugen und Ansicht; rechts Funktionen und Eigenschaften der offenen Datei
- Editor mit Syntaxfarben, SQL/HTML/JSON in Strings, Faltung, Snippets, Autovervollständigung (Jedi, sobald installiert)
- Echtzeit-Linting, Type-Hints, ungenutzte Imports, optionales Ruff
- Projektweites Umbenennen, Methode extrahieren, Dubletten
- Suche, Ersetzen in der Datei und im Workspace, Gliederung, Gehe-zu-Definition inklusive Bibliotheken, TODO, Lesezeichen
- Ausführen, Bytecode kompilieren, PyInstaller, grafischer Debugger (Haltepunkte, Bedingungen, Schritt, Watches)
- Bash- und PowerShell-Skripte laden, formatieren, prüfen, ausführen und über mehrere Dateien debuggen
- Baukasten aus Modulen für Python, PowerShell, Bash und einen Teil von Batch
- Skript aus Abfrage oder Prompt (Python, PowerShell, Bash, Batch), optional über das verbundene Sprachmodell
- Datenbank erzeugen: SQLite-Datei, sonst SQL oder MongoDB-Schema im Workspace
- EXE erzeugen (PyInstaller, MinGW oder gcc) und MSI-Installer mit WiX-Quelle
- PowerShell-Modul, Funktionsgenerator, GUI-Entwurf, Windows-Dienst, Leistungsmessung, Get-Help
- PowerShell lokal, per WinRM oder SSH; integrierte 32-bit- und 64-bit-Konsole, soweit der Rechner sie hat
- Wiederherstellung ungespeicherter Puffer
- JSON-Dateien laden, färben, auf Fehlerzeilen prüfen und formatieren
- Markierte Zeile, Abschnitt oder Funktion in einem eigenen Testfenster ausführen
- unittest, pytest, doctest, Coverage-Markierung
- venv, pip, conda, Poetry, Pipenv, Download einer eigenständigen CPython-Distribution
- Terminal, REPL-Kernel, Notebooks, Variablen, Matplotlib-Plots
- Git inklusive Konfliktseiten, lokale Dateihistorie
- SQLite sowie PostgreSQL, MySQL und MongoDB, wenn der Treiber installiert ist
- HTTP- und GraphQL-Anfragen aus `.http`-Dateien
- Django, Flask und FastAPI werden erkannt und können gestartet werden
- KI-Chat mit `@datei`, `@terminal`, `@git`, Inline-Edit, Traceback-Reparatur und Agent (OpenAI-kompatibel, auch Ollama)
- SSH, Docker, WSL und eine lokale Live-Sitzung für ein Dokument

KI-Zugang: Menü **KI → Sprachmodell verbinden**. Dort stehen Anbieter, Basis-URL, Modell, API-Schlüssel, System-Prompt und ein Prompt; **Verbinden und senden** speichert die Verbindung und schickt den Prompt sofort. Für Ollama zum Beispiel `http://127.0.0.1:11434/v1`. Voreingestellt sind außerdem Kimi (`https://api.moonshot.ai/v1`), Gemini und OpenAI. Chat, Inline-Edit und Reparatur verwenden den gespeicherten System-Prompt. Der Agent behält sein Werkzeugprotokoll und hängt den System-Prompt als zusätzliche Anweisung an. Schlüssel liegen nur in `~/.shatuide/config.json`.

GitHub und Editoren: Im selben Dialog lässt sich ein GitHub-Token für HTTPS gegen `github.com` prüfen. Es gilt für Klonen, Push und Pull, nicht als Modell-API. Die neun VS-Code-Erweiterungen Kimi Code, GitHub Copilot, Tabnine, Bito, Mintlify Doc Writer, Code GPT, Windsurf, Qodo Gen und Gemini Code Assist können angekreuzt werden. **Editor-Konfiguration schreiben** legt `.vscode/extensions.json` und `.vscode/shatuide.ai.json` ohne Schlüssel an. **VS Code öffnen** und **Visual Studio öffnen** starten den gefundenen oder eingetragenen Editor mit dem Workspace. Copilot, Tabnine, Bito, Mintlify, Windsurf und Qodo meldet man in dem jeweiligen Editor an.

## Tests

```bash
python3 -m unittest tests.test_shatu -v
```

Es werden keine Zusatzpakete benötigt. Black, Ruff, Jedi, pytest und Coverage schalten sich ein, sobald sie im gewählten Interpreter installiert sind.
