# ShatuIDE Feature-Liste

Version 1.0.0
Andreas Meyer, ame@sellerbach.de

Diese Feature-Liste ist für andere Nutzer und darf weitergegeben werden.
Die Bedienung steht in ANLEITUNG.md.

## Arbeitsweise

- Lokale IDE für Python, PowerShell, Linux-Shell und Windows-Batch.
- Der eingebaute Server hört nur auf 127.0.0.1.
- Unter Windows ist das Arbeitsverzeichnis D:\AI_Temp\ShatuIDE.
- Autor: Andreas Meyer, ame@sellerbach.de.

## Start

- ShatuIDE.exe öffnet ein eigenes Windows-Fenster. Darin läuft die IDE.
- ShatuIDE.bat startet diese Anwendung.
- py -3 shatuide.py öffnet dieselbe IDE im Browser.
- ShatuIDE-Setup.exe ist der Einrichtungsassistent mit Zielordner, Startmenü, Fortschritt und Fertigstellen.
- Python 3 muss auf dem Rechner vorhanden sein.

## Editor

- Menüband mit Start, Entwurf, Erzeugen und Ansicht.
- Syntaxfarben, Faltung, Snippets und Autovervollständigung.
- Suchen und Ersetzen in der Datei und im Arbeitsordner.
- Ausschneiden, Kopieren, Einfügen, zweites Fenster und Schließen der Bereiche.
- Funktionen und Eigenschaften der offenen Datei stehen rechts.

## Python

- Ausführen, Bytecode kompilieren und grafischer Debugger mit Haltepunkten.
- unittest, pytest, doctest und Coverage.
- venv, pip, conda, Poetry und Pipenv.
- Terminal, REPL, Notebooks und Plots.

## PowerShell, Linux-Shell und Batch

- PowerShell: .ps1, .psm1 und .psd1, Windows PowerShell und PowerShell 7, 32-bit und 64-bit.
- Linux-Shell: .sh und .bash, Syntaxprüfung mit bash -n, Ausführen und Debug.
- Windows-Batch: .bat und .cmd über cmd.exe, Sprungmarken in der Funktionsleiste.
- Format rückt PowerShell-, Shell- und Batch-Blöcke ein.
- Ausführen und Debuggen färben die Fehlerzeile bei Python, Bash und PowerShell, bis die Zeile korrigiert ist.
- JSON und HTML werden geprüft und formatiert.
- Befehlslisten mit Erklärung, Syntax und Beispiel für alle drei Sprachen.

## Erzeugen

- Baukasten aus Modulen für Python, PowerShell, Bash und einen Teil von Batch.
- Skript aus Abfrage für Python, PowerShell, Bash und Batch.
- Datenbank erzeugen: SQLite-Datei, sonst SQL oder ein MongoDB-Schema.
- EXE, MSI-Installer, PowerShell-Modul, Funktion, GUI-Entwurf und Windows-Dienst.
- Get-Help für ein PowerShell-Thema und Remote-PowerShell lokal, per WinRM oder per SSH.

## Weitergeben

- Die Anleitung für andere Nutzer liegt als ANLEITUNG.md und unter Hilfe → Anleitung.
- Die Kurzanleitung liegt als KURZANLEITUNG.md und unter Hilfe → Kurzanleitung.
- Diese Feature-Liste liegt als FEATURE-LISTE.md und unter Hilfe → Feature-Liste.
- INFO.md enthält dieselbe Feature-Liste plus die Befehlslisten.
- Speichern schreibt ausgabe/ANLEITUNG.md, ausgabe/FEATURE-LISTE.md und ausgabe/ShatuIDE-Info.md.
- ShatuIDE.zip enthält den kompletten Arbeitsordner.
