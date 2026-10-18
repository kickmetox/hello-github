# ShatuIDE Anleitung

Version 1.0.0
Andreas Meyer, ame@sellerbach.de

Diese Anleitung ist für andere Nutzer. Sie erklärt Installation und die tägliche Arbeit.
Die Funktionen stehen in FEATURE-LISTE.md.

## Für andere Nutzer

1. ShatuIDE ist eine lokale IDE für Python, PowerShell unter Windows, Linux-Shell und Windows-Batch.
2. Diese Anleitung erklärt Installation und die tägliche Arbeit. Die Feature-Liste nennt, was das Programm kann.
3. Autor: Andreas Meyer, ame@sellerbach.de.

## Installieren

1. Python 3 muss auf dem Rechner installiert sein. Dieses Paket enthält kein Python.
2. ShatuIDE-Setup.exe doppelklicken. Der Assistent bleibt vor den anderen Fenstern.
3. Seiten: Willkommen, Zielordner, Startmenü-Ordner, Installieren, Fortschritt, Fertigstellen.
4. Das Kästchen ShatuIDE jetzt starten ist frei. Das Programm startet erst, wenn der Assistent zu ist.
5. Der Assistent legt ein Symbol auf dem Desktop und einen Eintrag im Startmenü an.

## Starten

1. ShatuIDE.exe öffnet ein eigenes Windows-Fenster. Darin läuft die IDE.
2. ShatuIDE.bat startet diese Anwendung.
3. py -3 shatuide.py öffnet dieselbe IDE im Browser. Unter Linux lautet der Start python3 shatuide.py.
4. Unter Windows ist der Arbeitsordner D:\AI_Temp\ShatuIDE. Die IDE liest und schreibt dort.
5. Der eingebaute Server hört nur auf 127.0.0.1.

## Neue Datei

1. Datei → Neue Datei oder die Schaltfläche Neu.
2. Art wählen: Python, PowerShell, Linux-Shell, Windows-Batch, CMD, JSON, HTML oder Text.
3. Namen eintragen. Aus hallo wird hallo.py, hallo.ps1, hallo.sh oder hallo.bat.
4. Anlegen öffnet die Datei. Eine Batch-Datei beginnt mit @echo off, eine Shell mit #!/bin/bash.
5. Strg+S speichert. Strg+F5 führt aus.

## Öffnen und speichern

1. Datei → Öffnen lädt eine vorhandene Datei aus dem Arbeitsordner, aus darüberliegenden Ordnern oder vom Home-Verzeichnis.
2. Dateien außerhalb des Arbeitsordners sind nur lesbar.
3. Datei laden übernimmt eine Datei in den Arbeitsordner. Speichern schreibt sie dorthin.
4. Datei → Wiederherstellen holt einen ungespeicherten Puffer zurück.

## Bearbeiten

1. Strg+X schneidet aus, Strg+C kopiert, Strg+V fügt ein.
2. Strg+F sucht in der Datei, Strg+H ersetzt darin. Strg+Umschalt+H ersetzt im Arbeitsordner.
3. Fenster → Zweites Fenster öffnet eine weitere Ansicht. Fenster schließen schließt sie.
4. Rechts stehen Funktionen und Eigenschaften der offenen Datei. Ein Klick springt an die Stelle.

## Ausführen

1. Strg+F5 oder Ausführen startet die offene Datei.
2. Python läuft mit dem installierten Python. PowerShell sucht pwsh, danach powershell.exe.
3. Eine Linux-Shell läuft mit bash. Eine Batch-Datei startet unter Windows mit cmd.exe.
4. Ausführen → Syntax prüfen kontrolliert Python, PowerShell und die Linux-Shell, bevor die Datei läuft.

## Debug und Fehler

1. F9 setzt einen Haltepunkt, F5 startet den Debug oder läuft weiter, F10 geht einen Schritt weiter.
2. Eine Fehlerzeile bleibt rot, bis ihr Text korrigiert ist oder ein Lauf ohne Fehler endet.
3. Das gilt für Python, Bash und PowerShell. JSON und HTML werden geprüft, aber nicht ausgeführt.
4. Alt+F5 prüft die markierte Zeile in einem eigenen Fenster. Umschalt+Alt+F5 prüft die Funktion an der Schreibmarke.

## PowerShell, Linux-Shell und Batch

1. PowerShell-Dateien enden auf .ps1, .psm1 oder .psd1. Linux-Shell auf .sh oder .bash. Windows-Batch auf .bat oder .cmd.
2. Hilfe → Befehlslisten erklärt die häufigen Befehle mit Syntax und einem Beispiel.
3. Format rückt Blöcke ein. Sprungmarken einer Batch-Datei stehen in der Funktionsleiste.

## Erzeugen

1. Erzeugen → Baukasten setzt ein Skript aus Modulen zusammen. Das Ergebnis liegt unter ausgabe/.
2. Erzeugen → Skript aus Abfrage baut ein Python-, PowerShell-, Bash- oder Batch-Skript aus den Antworten.
3. Datenbank erzeugen legt SQLite im Arbeitsordner an. Andere Systeme bekommen ein SQL-Skript oder ein Schema.
4. EXE, MSI, PowerShell-Modul, Funktion, GUI-Entwurf und Windows-Dienst liegen ebenfalls unter Erzeugen.

## Weitergeben

1. Hilfe → Anleitung ist diese Fassung. Die Datei heißt ANLEITUNG.md.
2. Hilfe → Feature-Liste ist die Übersicht der Funktionen. Die Datei heißt FEATURE-LISTE.md.
3. Hilfe → Kurzanleitung fasst die täglichen Schritte kurz zusammen.
4. Speichern schreibt ausgabe/ANLEITUNG.md, ausgabe/FEATURE-LISTE.md und ausgabe/ShatuIDE-Info.md.
5. ShatuIDE.zip enthält den kompletten Arbeitsordner und kann an andere weitergegeben werden.
