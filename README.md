# ShatuIDE

Lokale Python-IDE von Andreas Meyer (ame@sellerbach.de).

Unter Windows ist das Arbeitsverzeichnis `D:\AI_Temp\ShatuIDE`. Die IDE liest und schreibt in diesem Ordner ohne zusätzliche Sandbox. Der eingebaute Server hört nur auf `127.0.0.1`.

## Start

```bash
python3 shatuide.py
```

Unter Windows: `ShatuIDE.bat` oder `py -3 shatuide.py`.

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
- Suche, Gliederung, Gehe-zu-Definition inklusive Bibliotheken, TODO, Lesezeichen
- Ausführen, Bytecode kompilieren, PyInstaller, grafischer Debugger (Haltepunkte, Bedingungen, Schritt, Watches)
- unittest, pytest, doctest, Coverage-Markierung
- venv, pip, conda, Poetry, Pipenv, Download einer eigenständigen CPython-Distribution
- Terminal, REPL-Kernel, Notebooks, Variablen, Matplotlib-Plots
- Git inklusive Konfliktseiten, lokale Dateihistorie
- SQLite sowie PostgreSQL, MySQL und MongoDB, wenn der Treiber installiert ist
- HTTP- und GraphQL-Anfragen aus `.http`-Dateien
- Django, Flask und FastAPI werden erkannt und können gestartet werden
- KI-Chat mit `@datei`, `@terminal`, `@git`, Inline-Edit, Traceback-Reparatur und Agent (OpenAI-kompatibel, auch Ollama)
- SSH, Docker, WSL und eine lokale Live-Sitzung für ein Dokument

KI-Zugang: Menü **KI → Sprachmodell verbinden**. Dort stehen Basis-URL, Modell, API-Schlüssel, System-Prompt und ein Prompt; **Verbinden und senden** speichert die Verbindung und schickt den Prompt sofort. Für Ollama zum Beispiel `http://127.0.0.1:11434/v1`. Chat, Inline-Edit und Reparatur verwenden den gespeicherten System-Prompt. Der Agent behält sein Werkzeugprotokoll und hängt den System-Prompt als zusätzliche Anweisung an. Der Schlüssel liegt nur in `~/.shatuide/config.json`.

## Tests

```bash
python3 -m unittest tests.test_shatu -v
```

Es werden keine Zusatzpakete benötigt. Black, Ruff, Jedi, pytest und Coverage schalten sich ein, sobald sie im gewählten Interpreter installiert sind.
