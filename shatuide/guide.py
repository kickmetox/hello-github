"""Befehlslisten und die weitergebbare Feature-Liste."""

from __future__ import annotations

from shatuide import __author__, __email__, __version__

_KINDS = {
    "powershell": "powershell",
    "ps": "powershell",
    "pwsh": "powershell",
    "shell": "shell",
    "bash": "shell",
    "linux": "shell",
    "sh": "shell",
    "batch": "batch",
    "bat": "batch",
    "cmd": "batch",
    "features": "features",
    "feature": "features",
    "info": "features",
    "liste": "features",
    "kurz": "kurz",
    "kurzanleitung": "kurz",
    "anleitung": "kurz",
}


def _cmd(name: str, syntax: str, text: str, example: str, alias: str = "") -> dict:
    item = {"name": name, "syntax": syntax, "text": text, "example": example}
    if alias:
        item["alias"] = alias
    return item


def _group(title: str, text: str, commands: list[dict]) -> dict:
    return {"title": title, "text": text, "commands": commands}


_POWERSHELL = {
    "title": "PowerShell unter Windows",
    "intro": (
        "PowerShell steuert Windows: Dateien, Prozesse, Dienste und eigene Skripte. "
        "ShatuIDE öffnet .ps1, .psm1 und .psd1. Ausführen sucht zuerst pwsh (PowerShell 7), "
        "danach powershell.exe, auch die 32-bit- und die 64-bit-Fassung, sobald beide vorhanden sind. "
        "Syntax prüfen nutzt den PowerShell-Parser. Debug hält an Haltepunkten an und zeigt Variablen. "
        "Get-Help in der Leiste Studio holt die eingebaute Hilfe des installierten PowerShell."
    ),
    "groups": [
        _group("Ordner und Dateien", "Der Punkt ist der aktuelle Ordner. Pfade mit Leerzeichen stehen in Anführungszeichen.", [
            _cmd("Get-Location", "Get-Location", "Zeigt den aktuellen Ordner.", "Get-Location", "pwd, gl"),
            _cmd("Set-Location", "Set-Location -Path <Ordner>", "Wechselt den Ordner.", "Set-Location -Path C:\\Temp", "cd, sl"),
            _cmd("Get-ChildItem", "Get-ChildItem -Path <Ordner> [-Filter <Muster>] [-Recurse]", "Listet Dateien und Unterordner.", "Get-ChildItem -Path C:\\Temp -Filter *.ps1", "dir, ls, gci"),
            _cmd("New-Item", "New-Item -Path <Pfad> -ItemType File|Directory", "Legt eine Datei oder einen Ordner an.", "New-Item -Path .\\notiz.txt -ItemType File", "ni"),
            _cmd("Copy-Item", "Copy-Item -Path <Quelle> -Destination <Ziel>", "Kopiert eine Datei oder einen Ordner.", "Copy-Item -Path .\\alt.txt -Destination .\\neu.txt", "copy, cp"),
            _cmd("Move-Item", "Move-Item -Path <Quelle> -Destination <Ziel>", "Verschiebt oder benennt um.", "Move-Item -Path .\\alt.txt -Destination .\\neu.txt", "move, mv"),
            _cmd("Remove-Item", "Remove-Item -Path <Pfad> [-Recurse]", "Löscht eine Datei oder einen Ordner.", "Remove-Item -Path .\\notiz.txt", "del, rm"),
            _cmd("Test-Path", "Test-Path -Path <Pfad>", "Antwortet True, wenn der Pfad existiert.", "if (Test-Path .\\daten.csv) { 'da' }", ""),
        ]),
        _group("Lesen und Schreiben", "Get-Content liefert Zeilen. Set-Content ersetzt die Datei. Add-Content hängt an.", [
            _cmd("Get-Content", "Get-Content -Path <Datei>", "Liest den Text einer Datei.", "Get-Content -Path .\\notiz.txt", "gc, type, cat"),
            _cmd("Set-Content", "Set-Content -Path <Datei> -Value <Text>", "Schreibt den Text und ersetzt den bisherigen Inhalt.", "Set-Content -Path .\\notiz.txt -Value 'Hallo'", "sc"),
            _cmd("Add-Content", "Add-Content -Path <Datei> -Value <Text>", "Hängt eine Zeile an die Datei an.", "Add-Content -Path .\\protokoll.txt -Value (Get-Date)", "ac"),
            _cmd("Out-File", "Befehl | Out-File -FilePath <Datei>", "Schreibt die Ausgabe eines Befehls in eine Datei.", "Get-ChildItem | Out-File -FilePath .\\liste.txt", ""),
        ]),
        _group("Variablen und Text", "Ein Dollarzeichen leitet den Namen ein. In doppelten Anführungszeichen wird $Name eingesetzt.", [
            _cmd("$Variable", "$Name = <Wert>", "Speichert einen Wert unter einem Namen.", "$Name = 'Ada'\nWrite-Output $Name", ""),
            _cmd("Write-Output", "Write-Output <Text>", "Gibt den Text an den nächsten Befehl in der Pipeline weiter.", "Write-Output 'fertig'", "echo, write"),
            _cmd("Write-Host", "Write-Host <Text>", "Schreibt nur auf den Bildschirm, nicht in die Pipeline.", "Write-Host 'Bitte warten' -ForegroundColor Yellow", ""),
            _cmd("Text mit Variable", "\"Text $Name\"", "Setzt den Variablenwert in den Text ein.", "$Ort = 'Hamburg'\n\"Ort: $Ort\"", ""),
        ]),
        _group("Entscheidungen und Schleifen", "Geschweifte Klammern fassen den Block. Die Bedingung steht in runden Klammern.", [
            _cmd("if", "if (<Bedingung>) { } elseif (<Bedingung>) { } else { }", "Führt einen Block aus, wenn die Bedingung zutrifft.", "if ($Zahl -gt 10) {\n    'gross'\n} else {\n    'klein'\n}", ""),
            _cmd("foreach", "foreach ($Element in $Liste) { }", "Geht eine Liste Element für Element durch.", "foreach ($Datei in Get-ChildItem *.txt) {\n    $Datei.Name\n}", ""),
            _cmd("ForEach-Object", "Befehl | ForEach-Object { $_ }", "Verarbeitet jedes Pipeline-Objekt. $_ ist das aktuelle Objekt.", "Get-ChildItem *.log | ForEach-Object { $_.Length }", "%, foreach"),
            _cmd("Where-Object", "Befehl | Where-Object { <Bedingung> }", "Lässt nur Objekte durch, auf die die Bedingung zutrifft.", "Get-Service | Where-Object { $_.Status -eq 'Running' }", "?, where"),
            _cmd("try", "try { } catch { } finally { }", "Fängt einen Abbruch und führt den catch-Block aus.", "try {\n    Get-Content .\\fehlt.txt -ErrorAction Stop\n} catch {\n    $_.Exception.Message\n}", ""),
        ]),
        _group("Funktionen und Hilfe", "Eine Funktion steht im Skript und wird danach mit ihrem Namen aufgerufen.", [
            _cmd("function", "function Name { param($Wert) }", "Bündelt Befehle unter einem Namen.", "function Gruss {\n    param($Name)\n    \"Hallo $Name\"\n}\nGruss -Name Ada", ""),
            _cmd("Get-Help", "Get-Help <Befehl> [-Examples]", "Zeigt Erklärung, Parameter und Beispiele des Befehls.", "Get-Help Get-ChildItem -Examples", "help"),
            _cmd("Get-Command", "Get-Command [-Name <Muster>]", "Sucht Befehle, Aliase und Funktionen.", "Get-Command *service*", "gcm"),
            _cmd("Get-Member", "Objekt | Get-Member", "Zeigt Eigenschaften und Methoden eines Objekts.", "Get-Date | Get-Member", "gm"),
        ]),
        _group("System", "Diese Befehle fragen Windows ab. Stop-Process beendet einen Prozess.", [
            _cmd("Get-Process", "Get-Process [-Name <Name>]", "Listet laufende Prozesse.", "Get-Process -Name notepad", "ps, gps"),
            _cmd("Stop-Process", "Stop-Process -Name <Name>", "Beendet einen Prozess über seinen Namen.", "Stop-Process -Name notepad", "kill, spps"),
            _cmd("Get-Service", "Get-Service [-Name <Name>]", "Zeigt den Zustand eines Windows-Dienstes.", "Get-Service -Name Spooler", "gsv"),
            _cmd("Get-Date", "Get-Date [-Format <Muster>]", "Liefert das aktuelle Datum.", "Get-Date -Format 'yyyy-MM-dd HH:mm'", ""),
        ]),
    ],
}

_SHELL = {
    "title": "Linux-Shell",
    "intro": (
        "Bash-Skripte steuern Linux: Ordner, Dateien, Suche und eigene Abläufe. "
        "ShatuIDE öffnet .sh, .bash, .ksh, .zsh sowie .bashrc und .profile. "
        "Ausführen startet bash, sonst sh. Syntax prüfen ruft bash -n auf. "
        "Debug hält an Haltepunkten an. Unter Windows läuft dasselbe Skript, sobald Bash vorhanden ist, zum Beispiel über WSL oder Git Bash."
    ),
    "groups": [
        _group("Ordner und Dateien", "Ein Leerzeichen trennt Befehl und Argument. Pfade mit Leerzeichen stehen in Anführungszeichen.", [
            _cmd("pwd", "pwd", "Zeigt den aktuellen Ordner.", "pwd"),
            _cmd("cd", "cd <Ordner>", "Wechselt den Ordner. cd ohne Argument geht ins Home-Verzeichnis.", "cd /tmp"),
            _cmd("ls", "ls [-l] [-a] <Ordner>", "Listet den Ordnerinhalt. -l zeigt Größe und Rechte, -a auch versteckte Namen.", "ls -la \"$HOME\""),
            _cmd("mkdir", "mkdir [-p] <Ordner>", "Legt einen Ordner an. -p legt fehlende Zwischenordner mit an.", "mkdir -p \"$HOME/arbeit/neu\""),
            _cmd("cp", "cp <Quelle> <Ziel>", "Kopiert eine Datei. -r kopiert einen Ordner samt Inhalt.", "cp notiz.txt sicherung.txt"),
            _cmd("mv", "mv <Quelle> <Ziel>", "Verschiebt oder benennt um.", "mv alt.txt neu.txt"),
            _cmd("rm", "rm <Datei>", "Löscht eine Datei. -r löscht einen Ordner samt Inhalt.", "rm notiz.txt"),
            _cmd("touch", "touch <Datei>", "Legt eine leere Datei an oder setzt die Änderungszeit.", "touch protokoll.txt"),
        ]),
        _group("Anzeigen und Suchen", "grep sucht Text. find sucht Dateinamen.", [
            _cmd("cat", "cat <Datei>", "Gibt den ganzen Dateiinhalt aus.", "cat notiz.txt"),
            _cmd("head", "head [-n <Anzahl>] <Datei>", "Zeigt die ersten Zeilen, voreingestellt zehn.", "head -n 20 protokoll.txt"),
            _cmd("tail", "tail [-n <Anzahl>] <Datei>", "Zeigt die letzten Zeilen.", "tail -n 20 protokoll.txt"),
            _cmd("grep", "grep [-n] [-i] <Muster> <Datei>", "Sucht ein Muster. -n zeigt die Zeilennummer, -i ignoriert Groß- und Kleinschreibung.", "grep -n Fehler protokoll.txt"),
            _cmd("find", "find <Ordner> -name <Muster>", "Sucht Dateien unterhalb eines Ordners.", "find . -name '*.sh'"),
        ]),
        _group("Variablen und Eingabe", "Vor und hinter dem Gleichheitszeichen steht kein Leerzeichen. $Name liest den Wert.", [
            _cmd("Variable", "name=wert", "Speichert einen Wert. Beim Lesen steht ein Dollarzeichen davor.", "name=Ada\necho \"$name\""),
            _cmd("echo", "echo <Text>", "Gibt Text aus. In doppelten Anführungszeichen wird $name eingesetzt.", "echo \"Hallo $name\""),
            _cmd("printf", "printf '<Format>' <Werte>", "Gibt Text mit Format aus, zum Beispiel Zahlen und Zeilenenden.", "printf 'Wert: %s\\n' \"$name\""),
            _cmd("read", "read -r <Name>", "Liest eine Zeile von der Tastatur in die Variable.", "read -r ort\necho \"Ort: $ort\""),
            _cmd("export", "export <Name>=<Wert>", "Macht die Variable für aufgerufene Programme sichtbar.", "export LANG=de_DE.UTF-8"),
        ]),
        _group("Entscheidungen und Schleifen", "then, do und done schließen den Block. Die Einrückung dient der Lesbarkeit.", [
            _cmd("if", "if <Befehl>; then ...; else ...; fi", "Der if-Zweig läuft, wenn der Befehl mit Status 0 endet.", "if [ -f notiz.txt ]; then\n    echo da\nelse\n    echo fehlt\nfi"),
            _cmd("for", "for name in <Liste>; do ...; done", "Setzt die Variable nacheinander auf jeden Listeneintrag.", "for datei in *.txt; do\n    echo \"$datei\"\ndone"),
            _cmd("while", "while <Befehl>; do ...; done", "Wiederholt den Block, solange der Befehl mit Status 0 endet.", "n=1\nwhile [ \"$n\" -le 3 ]; do\n    echo \"$n\"\n    n=$((n + 1))\ndone"),
            _cmd("function", "name() { ...; }", "Bündelt Befehle. Der Aufruf ist der Funktionsname.", "gruss() {\n    echo \"Hallo $1\"\n}\ngruss Ada"),
        ]),
        _group("Rechte, Pipes und Prüfung", "Eine Pipe schickt die Ausgabe des linken Befehls an den rechten. bash -n prüft, ohne zu starten.", [
            _cmd("chmod", "chmod <Modus> <Datei>", "Setzt die Rechte. +x macht ein Skript ausführbar.", "chmod +x hallo.sh"),
            _cmd("Pipe", "befehl | befehl", "Gibt die Ausgabe weiter. > schreibt eine Datei neu, >> hängt an.", "ls | grep txt > liste.txt"),
            _cmd("bash -n", "bash -n <Skript>", "Prüft die Syntax und führt das Skript nicht aus.", "bash -n hallo.sh"),
            _cmd("set -x", "set -x", "Zeigt vor jeder Zeile den ausgeführten Befehl. set +x schaltet das wieder aus.", "set -x\necho hallo\nset +x"),
        ]),
    ],
}

_BATCH = {
    "title": "Windows-Batch",
    "intro": (
        "Eine Batch-Datei ist eine Liste von Befehlen für die Windows-Eingabeaufforderung cmd.exe. "
        "ShatuIDE öffnet .bat und .cmd. Ausführen startet cmd.exe /c und gibt es nur unter Windows. "
        "Die Funktionsleiste zeigt die Sprungmarken. cmd.exe hat keine getrennte Syntaxprüfung; "
        "ein Tippfehler fällt beim Lauf auf. In der Datei heißen Schleifenvariablen %%A, auf der Kommandozeile %A."
    ),
    "groups": [
        _group("Grundgerüst", "@echo off unterdrückt die Befehlszeilen selbst. rem ist der Kommentar.", [
            _cmd("@echo off", "@echo off", "Zeigt die folgenden Befehle nicht mehr selbst an, nur ihre Ausgabe.", "@echo off\necho Hallo"),
            _cmd("echo", "echo <Text>", "Gibt eine Zeile aus. echo. gibt eine leere Zeile aus.", "echo Fertig."),
            _cmd("rem", "rem <Text>", "Kommentar. Die Zeile wird nicht ausgeführt. :: am Zeilenanfang gilt ebenso als Kommentar.", "rem Diese Zeile erklärt den nächsten Schritt."),
            _cmd("pause", "pause", "Wartet auf eine Taste, damit das Fenster offen bleibt.", "echo Ende\npause"),
            _cmd("exit", "exit /b <Zahl>", "Beendet die Batch-Datei. Die Zahl ist der Rückgabewert.", "exit /b 0"),
        ]),
        _group("Variablen", "set speichert Text. Beim Lesen steht der Name zwischen Prozentzeichen. setlocal hält die Variablen in dieser Datei.", [
            _cmd("set", "set NAME=Wert", "Speichert Text. set ohne Argument listet alle Variablen.", "set NAME=Ada\necho %NAME%"),
            _cmd("setlocal", "setlocal", "Änderungen an Variablen gelten bis endlocal oder bis zum Ende der Datei.", "setlocal\nset NAME=Ada\nendlocal"),
            _cmd("%NAME%", "echo %NAME%", "Setzt den gespeicherten Wert ein. Die Ersetzung passiert beim Lesen der Zeile.", "set ORT=Hamburg\necho Ort: %ORT%"),
            _cmd("set /a", "set /a NAME=Ausdruck", "Rechnet mit ganzen Zahlen.", "set /a SUMME=2+3\necho %SUMME%"),
        ]),
        _group("Dateien und Ordner", "Pfade mit Leerzeichen stehen in Anführungszeichen.", [
            _cmd("cd", "cd /d <Ordner>", "Wechselt den Ordner. /d wechselt dabei auch das Laufwerk.", "cd /d D:\\AI_Temp\\ShatuIDE"),
            _cmd("dir", "dir <Ordner>", "Listet den Ordnerinhalt.", "dir C:\\Temp\\*.txt"),
            _cmd("md", "md <Ordner>", "Legt einen Ordner an.", "md ausgabe"),
            _cmd("copy", "copy <Quelle> <Ziel>", "Kopiert eine Datei.", "copy notiz.txt sicherung.txt"),
            _cmd("move", "move <Quelle> <Ziel>", "Verschiebt oder benennt um.", "move alt.txt neu.txt"),
            _cmd("del", "del <Datei>", "Löscht eine Datei.", "del notiz.txt"),
            _cmd("type", "type <Datei>", "Gibt den Dateiinhalt aus.", "type notiz.txt"),
            _cmd("if exist", "if exist <Pfad> <Befehl>", "Führt den Befehl aus, wenn die Datei oder der Ordner vorhanden ist.", "if exist notiz.txt echo da"),
        ]),
        _group("Entscheidungen und Sprünge", "Eine Sprungmarke beginnt mit einem Doppelpunkt. goto springt dorthin. call kehrt danach zurück.", [
            _cmd("if", "if \"<Text>\"==\"<Text>\" <Befehl>", "Vergleicht zwei Texte. Der Block in Klammern darf mehrere Zeilen haben.", "if \"%NAME%\"==\"Ada\" (\n    echo hallo\n) else (\n    echo unbekannt\n)"),
            _cmd("goto", "goto :Marke", "Springt zur Zeile :Marke und kehrt nicht zurück.", "goto :Ende\necho unsichtbar\n:Ende\necho hier"),
            _cmd("call", "call :Marke", "Springt zur Marke und macht nach dem Rücksprung mit der nächsten Zeile weiter.", "call :Gruss\necho danach\ngoto :eof\n:Gruss\necho hallo\ngoto :eof"),
            _cmd(":Marke", ":Name", "Sprungziel. Der Name erscheint in der Funktionsleiste von ShatuIDE.", ":Start\necho noch einmal"),
        ]),
        _group("Schleifen und Argumente", "%%A ist die Schleifenvariable in der Datei. %1 ist das erste Argument beim Start.", [
            _cmd("for", "for %%A in (<Liste>) do <Befehl>", "Wiederholt den Befehl für jeden Eintrag. for /f liest Zeilen einer Datei oder eines Befehls.", "for %%F in (*.txt) do echo %%F"),
            _cmd("%1", "%1  %*", "%1 ist das erste Argument, %2 das zweite. %* sind alle Argumente.", "echo Datei: %1"),
            _cmd("%~dp0", "%~dp0", "Ordner der Batch-Datei, mit einem Backslash am Ende.", "cd /d \"%~dp0\""),
            _cmd("%ERRORLEVEL%", "if errorlevel 1", "Nach einem Befehl steht hier dessen Rückgabewert. 0 bedeutet in der Regel Erfolg.", "copy notiz.txt ziel.txt\nif errorlevel 1 echo Kopieren fehlgeschlagen"),
        ]),
    ],
}

_GUIDES = {"powershell": _POWERSHELL, "shell": _SHELL, "batch": _BATCH}

_QUICK = [
    {
        "title": "Start",
        "items": [
            "ShatuIDE-Setup.exe starten und den Assistenten bis Fertigstellen durchgehen, oder ShatuIDE.exe direkt öffnen.",
            "Python 3 muss auf dem Rechner installiert sein.",
            "ShatuIDE.bat startet die Windows-Anwendung. py -3 shatuide.py öffnet dieselbe IDE im Browser.",
        ],
    },
    {
        "title": "Neue Datei",
        "items": [
            "Datei → Neue Datei oder die Schaltfläche Neu.",
            "Art wählen: Python, PowerShell, Linux-Shell, Windows-Batch, CMD, JSON, HTML oder Text.",
            "Namen eintragen. Aus hallo wird hallo.py, hallo.ps1, hallo.sh oder hallo.bat.",
            "Anlegen öffnet die Datei. Strg+S speichert sie.",
            "Strg+F5 führt sie aus. Eine Batch-Datei startet unter Windows mit cmd.exe.",
        ],
    },
    {
        "title": "Öffnen und bearbeiten",
        "items": [
            "Datei → Öffnen lädt eine vorhandene Datei. Datei laden übernimmt eine Datei in den Arbeitsordner.",
            "Strg+X schneidet aus, Strg+C kopiert, Strg+V fügt ein.",
            "Strg+F sucht in der Datei, Strg+H ersetzt darin.",
        ],
    },
    {
        "title": "Ausführen und Debug",
        "items": [
            "Ausführen → Syntax prüfen kontrolliert Python, PowerShell und die Linux-Shell.",
            "F9 setzt einen Haltepunkt, F5 startet den Debug, F10 geht einen Schritt weiter.",
            "Eine Fehlerzeile bleibt rot, bis ihr Text korrigiert ist oder ein Lauf ohne Fehler endet.",
        ],
    },
    {
        "title": "PowerShell, Linux-Shell und Batch",
        "items": [
            "PowerShell-Dateien enden auf .ps1, Linux-Shell auf .sh, Windows-Batch auf .bat oder .cmd.",
            "Hilfe → Befehlslisten zeigt Erklärung, Syntax und ein Beispiel zu den häufigen Befehlen.",
            "Erzeugen → Skript aus Abfrage baut ein fertiges Skript unter ausgabe/.",
        ],
    },
    {
        "title": "Weitergeben",
        "items": [
            "Hilfe → Feature-Liste ist die Übersicht für andere. Dieselbe Fassung steht in INFO.md.",
            "Alles zur Weitergabe kopiert den Text. Speichern schreibt ausgabe/ShatuIDE-Info.md.",
            "ShatuIDE.zip enthält den kompletten Arbeitsordner.",
        ],
    },
]

_FEATURES = [
    {
        "title": "Arbeitsweise",
        "items": [
            "Lokale IDE für Python, PowerShell, Linux-Shell und Windows-Batch.",
            "Der eingebaute Server hört nur auf 127.0.0.1.",
            "Unter Windows ist das Arbeitsverzeichnis D:\\AI_Temp\\ShatuIDE.",
            "Autor: Andreas Meyer, ame@sellerbach.de.",
        ],
    },
    {
        "title": "Start",
        "items": [
            "ShatuIDE.exe öffnet ein eigenes Windows-Fenster. Darin läuft die IDE.",
            "ShatuIDE.bat startet diese Anwendung.",
            "py -3 shatuide.py öffnet dieselbe IDE im Browser.",
            "ShatuIDE-Setup.exe ist der Einrichtungsassistent mit Zielordner, Startmenü, Fortschritt und Fertigstellen.",
            "Python 3 muss auf dem Rechner vorhanden sein.",
        ],
    },
    {
        "title": "Editor",
        "items": [
            "Menüband mit Start, Entwurf, Erzeugen und Ansicht.",
            "Syntaxfarben, Faltung, Snippets und Autovervollständigung.",
            "Suchen und Ersetzen in der Datei und im Arbeitsordner.",
            "Ausschneiden, Kopieren, Einfügen, zweites Fenster und Schließen der Bereiche.",
            "Funktionen und Eigenschaften der offenen Datei stehen rechts.",
        ],
    },
    {
        "title": "Python",
        "items": [
            "Ausführen, Bytecode kompilieren und grafischer Debugger mit Haltepunkten.",
            "unittest, pytest, doctest und Coverage.",
            "venv, pip, conda, Poetry und Pipenv.",
            "Terminal, REPL, Notebooks und Plots.",
        ],
    },
    {
        "title": "PowerShell, Linux-Shell und Batch",
        "items": [
            "PowerShell: .ps1, .psm1 und .psd1, Windows PowerShell und PowerShell 7, 32-bit und 64-bit.",
            "Linux-Shell: .sh und .bash, Syntaxprüfung mit bash -n, Ausführen und Debug.",
            "Windows-Batch: .bat und .cmd über cmd.exe, Sprungmarken in der Funktionsleiste.",
            "Format rückt PowerShell-, Shell- und Batch-Blöcke ein.",
            "Ausführen und Debuggen färben die Fehlerzeile bei Python, Bash und PowerShell, bis die Zeile korrigiert ist.",
            "JSON und HTML werden geprüft und formatiert.",
            "Befehlslisten mit Erklärung, Syntax und Beispiel für alle drei Sprachen.",
        ],
    },
    {
        "title": "Erzeugen",
        "items": [
            "Baukasten aus Modulen für Python, PowerShell, Bash und einen Teil von Batch.",
            "Skript aus Abfrage für Python, PowerShell, Bash und Batch.",
            "Datenbank erzeugen: SQLite-Datei, sonst SQL oder ein MongoDB-Schema.",
            "EXE, MSI-Installer, PowerShell-Modul, Funktion, GUI-Entwurf und Windows-Dienst.",
            "Get-Help für ein PowerShell-Thema und Remote-PowerShell lokal, per WinRM oder per SSH.",
        ],
    },
    {
        "title": "Weitergeben",
        "items": [
            "Die Kurzanleitung liegt als KURZANLEITUNG.md und unter Hilfe → Kurzanleitung.",
            "Diese Feature-Liste liegt als INFO.md im Arbeitsordner.",
            "Im Fenster Hilfe kopiert Alles zur Weitergabe denselben Text.",
            "Speichern schreibt ausgabe/ShatuIDE-Info.md.",
            "ShatuIDE.zip enthält den kompletten Arbeitsordner.",
        ],
    },
]


def kinds() -> list[str]:
    return ["kurz", "powershell", "shell", "batch", "features"]


def _normalize(kind: str) -> str:
    return _KINDS.get((kind or "").strip().lower(), "")


def _commands(guide: dict) -> list[dict]:
    found = []
    for group in guide["groups"]:
        found.extend(group["commands"])
    return found


def language_document(kind: str) -> str:
    key = _normalize(kind)
    guide = _GUIDES.get(key)
    if not guide:
        return ""
    lines = [f"# {guide['title']}", "", guide["intro"], ""]
    for group in guide["groups"]:
        lines.append(f"## {group['title']}")
        lines.append("")
        lines.append(group["text"])
        lines.append("")
        for command in group["commands"]:
            alias = f" ({command['alias']})" if command.get("alias") else ""
            lines.append(f"### {command['name']}{alias}")
            lines.append("")
            lines.append(command["text"])
            lines.append("")
            lines.append("Syntax:")
            lines.append("")
            lines.append(f"    {command['syntax']}")
            lines.append("")
            lines.append("Beispiel:")
            lines.append("")
            lines.append("```")
            lines.extend(command["example"].splitlines() or [""])
            lines.append("```")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def quick_document() -> str:
    lines = [
        "# ShatuIDE Kurzanleitung",
        "",
        f"Version {__version__}",
        f"{__author__}, {__email__}",
        "",
        "Kurze Schritte für den Alltag. Die Befehlslisten stehen unter Hilfe.",
        "",
    ]
    for section in _QUICK:
        lines.append(f"## {section['title']}")
        lines.append("")
        for number, item in enumerate(section["items"], start=1):
            lines.append(f"{number}. {item}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def feature_document() -> str:
    lines = [
        "# ShatuIDE",
        "",
        f"Version {__version__}",
        f"{__author__}, {__email__}",
        "",
        "Lokale Entwicklungsumgebung für Python, PowerShell unter Windows, Linux-Shell und Windows-Batch.",
        "Diese Info- und Feature-Liste darf weitergegeben werden.",
        "",
        "## Feature-Liste",
        "",
    ]
    for section in _FEATURES:
        lines.append(f"### {section['title']}")
        lines.append("")
        for item in section["items"]:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def share_document() -> str:
    parts = [feature_document().rstrip(), ""]
    parts.append("Die folgenden Befehlslisten erklären die häufigen Befehle mit Syntax und einem kurzen Beispiel.")
    parts.append("")
    for key in ("powershell", "shell", "batch"):
        parts.append(language_document(key).rstrip())
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def catalog(kind: str) -> dict:
    key = _normalize(kind)
    if not key:
        return {"ok": False, "error": "Unbekannte Hilfe. Erlaubt sind kurz, powershell, shell, batch und features."}
    if key == "kurz":
        return {
            "ok": True,
            "kind": "kurz",
            "title": "Kurzanleitung",
            "intro": f"Version {__version__}. {__author__}, {__email__}. Kurze Schritte für den Alltag.",
            "sections": _QUICK,
            "document": quick_document(),
            "share": share_document(),
        }
    if key == "features":
        return {
            "ok": True,
            "kind": "features",
            "title": "ShatuIDE",
            "intro": f"Version {__version__}. {__author__}, {__email__}. Diese Liste darf weitergegeben werden.",
            "sections": _FEATURES,
            "document": feature_document(),
            "share": share_document(),
        }
    guide = _GUIDES[key]
    return {
        "ok": True,
        "kind": key,
        "title": guide["title"],
        "intro": guide["intro"],
        "groups": guide["groups"],
        "document": language_document(key),
        "share": share_document(),
    }
