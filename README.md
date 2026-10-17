# ShatuIDE

Lokale Python-IDE von Andreas Meyer (ame@sellerbach.de).

Unter Windows ist das Arbeitsverzeichnis `D:\AI_Temp\ShatuIDE`. Die IDE liest und schreibt in diesem Ordner ohne zusätzliche Sandbox. Der eingebaute Server hört nur auf `127.0.0.1`.

## Start

```bash
python3 shatuide.py
```

Unter Windows: `ShatuIDE.bat` oder `py -3 shatuide.py`.

**Datei → Öffnen** lädt vorhandene Python-Skripte und andere Textdateien aus dem Workspace, aus darüberliegenden Ordnern oder vom Home-Verzeichnis. Dateien außerhalb des Workspace sind nur lesbar. **Datei laden** übernimmt Dateien aus der Dateiauswahl; Speichern schreibt sie in den Workspace. **Bearbeiten** schneidet aus, kopiert die Markierung oder einen Zeilenbereich und fügt ein. **Fenster → Zweites Fenster** öffnet eine weitere IDE-Ansicht.

**Strg+F** sucht in der offenen Datei, **Strg+H** ersetzt darin. Groß/Klein, ganzes Wort und reguläre Ausdrücke lassen sich umschalten. **Strg+Umschalt+H** ersetzt im Workspace, nach einer Vorschau und nur in Dateien dieses Ordners. Weitere Editorbefehle: Zeile kommentieren, duplizieren, verschieben, löschen und verbinden, Einrücken, Groß-/Kleinschreibung, nächstes Vorkommen, Gehe zu Zeile und Zeilenumbruch.

`.sh`, `.bash` und `.ps1` lassen sich laden und bearbeiten. **Ausführen** startet Bash beziehungsweise PowerShell (`pwsh` oder `powershell`). **Syntax prüfen** nutzt `bash -n` oder den PowerShell-Parser. **Debug** hält an Haltepunkten an, zeigt Variablen und geht schrittweise weiter. Fehlt der Interpreter, meldet die IDE das, statt ein Ergebnis zu erfinden.

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

- Editor mit Syntaxfarben, SQL/HTML/JSON in Strings, Faltung, Snippets, Autovervollständigung (Jedi, sobald installiert)
- Echtzeit-Linting, Type-Hints, ungenutzte Imports, optionales Ruff
- Projektweites Umbenennen, Methode extrahieren, Dubletten
- Suche, Ersetzen in der Datei und im Workspace, Gliederung, Gehe-zu-Definition inklusive Bibliotheken, TODO, Lesezeichen
- Ausführen, Bytecode kompilieren, PyInstaller, grafischer Debugger (Haltepunkte, Bedingungen, Schritt, Watches)
- Bash- und PowerShell-Skripte laden, prüfen, ausführen und an Haltepunkten debuggen
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
