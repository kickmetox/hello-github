# ShatuIDE

Version 1.0.0
Andreas Meyer, ame@sellerbach.de

Lokale Entwicklungsumgebung für Python, PowerShell unter Windows, Linux-Shell und Windows-Batch.
Diese Info- und Feature-Liste darf weitergegeben werden.

## Feature-Liste

### Arbeitsweise

- Lokale IDE für Python, PowerShell, Linux-Shell und Windows-Batch.
- Der eingebaute Server hört nur auf 127.0.0.1.
- Unter Windows ist das Arbeitsverzeichnis D:\AI_Temp\ShatuIDE.
- Autor: Andreas Meyer, ame@sellerbach.de.

### Start

- ShatuIDE.exe öffnet ein eigenes Windows-Fenster. Darin läuft die IDE.
- ShatuIDE.bat startet diese Anwendung.
- py -3 shatuide.py öffnet dieselbe IDE im Browser.
- ShatuIDE-Setup.exe ist der Einrichtungsassistent mit Zielordner, Startmenü, Fortschritt und Fertigstellen.
- Python 3 muss auf dem Rechner vorhanden sein.

### Editor

- Menüband mit Start, Entwurf, Erzeugen und Ansicht.
- Syntaxfarben, Faltung, Snippets und Autovervollständigung.
- Suchen und Ersetzen in der Datei und im Arbeitsordner.
- Ausschneiden, Kopieren, Einfügen, zweites Fenster und Schließen der Bereiche.
- Funktionen und Eigenschaften der offenen Datei stehen rechts.

### Python

- Ausführen, Bytecode kompilieren und grafischer Debugger mit Haltepunkten.
- unittest, pytest, doctest und Coverage.
- venv, pip, conda, Poetry und Pipenv.
- Terminal, REPL, Notebooks und Plots.

### PowerShell, Linux-Shell und Batch

- PowerShell: .ps1, .psm1 und .psd1, Windows PowerShell und PowerShell 7, 32-bit und 64-bit.
- Linux-Shell: .sh und .bash, Syntaxprüfung mit bash -n, Ausführen und Debug.
- Windows-Batch: .bat und .cmd über cmd.exe, Sprungmarken in der Funktionsleiste.
- Format rückt PowerShell-, Shell- und Batch-Blöcke ein.
- Ausführen und Debuggen färben die Fehlerzeile bei Python, Bash und PowerShell, bis die Zeile korrigiert ist.
- JSON und HTML werden geprüft und formatiert.
- Befehlslisten mit Erklärung, Syntax und Beispiel für alle drei Sprachen.

### Erzeugen

- Baukasten aus Modulen für Python, PowerShell, Bash und einen Teil von Batch.
- Skript aus Abfrage für Python, PowerShell, Bash und Batch.
- Datenbank erzeugen: SQLite-Datei, sonst SQL oder ein MongoDB-Schema.
- EXE, MSI-Installer, PowerShell-Modul, Funktion, GUI-Entwurf und Windows-Dienst.
- Get-Help für ein PowerShell-Thema und Remote-PowerShell lokal, per WinRM oder per SSH.

### Weitergeben

- Die Kurzanleitung liegt als KURZANLEITUNG.md und unter Hilfe → Kurzanleitung.
- Diese Feature-Liste liegt als INFO.md im Arbeitsordner.
- Im Fenster Hilfe kopiert Alles zur Weitergabe denselben Text.
- Speichern schreibt ausgabe/ShatuIDE-Info.md.
- ShatuIDE.zip enthält den kompletten Arbeitsordner.

Die folgenden Befehlslisten erklären die häufigen Befehle mit Syntax und einem kurzen Beispiel.

# PowerShell unter Windows

PowerShell steuert Windows: Dateien, Prozesse, Dienste und eigene Skripte. ShatuIDE öffnet .ps1, .psm1 und .psd1. Ausführen sucht zuerst pwsh (PowerShell 7), danach powershell.exe, auch die 32-bit- und die 64-bit-Fassung, sobald beide vorhanden sind. Syntax prüfen nutzt den PowerShell-Parser. Debug hält an Haltepunkten an und zeigt Variablen. Get-Help in der Leiste Studio holt die eingebaute Hilfe des installierten PowerShell.

## Ordner und Dateien

Der Punkt ist der aktuelle Ordner. Pfade mit Leerzeichen stehen in Anführungszeichen.

### Get-Location (pwd, gl)

Zeigt den aktuellen Ordner.

Syntax:

    Get-Location

Beispiel:

```
Get-Location
```

### Set-Location (cd, sl)

Wechselt den Ordner.

Syntax:

    Set-Location -Path <Ordner>

Beispiel:

```
Set-Location -Path C:\Temp
```

### Get-ChildItem (dir, ls, gci)

Listet Dateien und Unterordner.

Syntax:

    Get-ChildItem -Path <Ordner> [-Filter <Muster>] [-Recurse]

Beispiel:

```
Get-ChildItem -Path C:\Temp -Filter *.ps1
```

### New-Item (ni)

Legt eine Datei oder einen Ordner an.

Syntax:

    New-Item -Path <Pfad> -ItemType File|Directory

Beispiel:

```
New-Item -Path .\notiz.txt -ItemType File
```

### Copy-Item (copy, cp)

Kopiert eine Datei oder einen Ordner.

Syntax:

    Copy-Item -Path <Quelle> -Destination <Ziel>

Beispiel:

```
Copy-Item -Path .\alt.txt -Destination .\neu.txt
```

### Move-Item (move, mv)

Verschiebt oder benennt um.

Syntax:

    Move-Item -Path <Quelle> -Destination <Ziel>

Beispiel:

```
Move-Item -Path .\alt.txt -Destination .\neu.txt
```

### Remove-Item (del, rm)

Löscht eine Datei oder einen Ordner.

Syntax:

    Remove-Item -Path <Pfad> [-Recurse]

Beispiel:

```
Remove-Item -Path .\notiz.txt
```

### Test-Path

Antwortet True, wenn der Pfad existiert.

Syntax:

    Test-Path -Path <Pfad>

Beispiel:

```
if (Test-Path .\daten.csv) { 'da' }
```

## Lesen und Schreiben

Get-Content liefert Zeilen. Set-Content ersetzt die Datei. Add-Content hängt an.

### Get-Content (gc, type, cat)

Liest den Text einer Datei.

Syntax:

    Get-Content -Path <Datei>

Beispiel:

```
Get-Content -Path .\notiz.txt
```

### Set-Content (sc)

Schreibt den Text und ersetzt den bisherigen Inhalt.

Syntax:

    Set-Content -Path <Datei> -Value <Text>

Beispiel:

```
Set-Content -Path .\notiz.txt -Value 'Hallo'
```

### Add-Content (ac)

Hängt eine Zeile an die Datei an.

Syntax:

    Add-Content -Path <Datei> -Value <Text>

Beispiel:

```
Add-Content -Path .\protokoll.txt -Value (Get-Date)
```

### Out-File

Schreibt die Ausgabe eines Befehls in eine Datei.

Syntax:

    Befehl | Out-File -FilePath <Datei>

Beispiel:

```
Get-ChildItem | Out-File -FilePath .\liste.txt
```

## Variablen und Text

Ein Dollarzeichen leitet den Namen ein. In doppelten Anführungszeichen wird $Name eingesetzt.

### $Variable

Speichert einen Wert unter einem Namen.

Syntax:

    $Name = <Wert>

Beispiel:

```
$Name = 'Ada'
Write-Output $Name
```

### Write-Output (echo, write)

Gibt den Text an den nächsten Befehl in der Pipeline weiter.

Syntax:

    Write-Output <Text>

Beispiel:

```
Write-Output 'fertig'
```

### Write-Host

Schreibt nur auf den Bildschirm, nicht in die Pipeline.

Syntax:

    Write-Host <Text>

Beispiel:

```
Write-Host 'Bitte warten' -ForegroundColor Yellow
```

### Text mit Variable

Setzt den Variablenwert in den Text ein.

Syntax:

    "Text $Name"

Beispiel:

```
$Ort = 'Hamburg'
"Ort: $Ort"
```

## Entscheidungen und Schleifen

Geschweifte Klammern fassen den Block. Die Bedingung steht in runden Klammern.

### if

Führt einen Block aus, wenn die Bedingung zutrifft.

Syntax:

    if (<Bedingung>) { } elseif (<Bedingung>) { } else { }

Beispiel:

```
if ($Zahl -gt 10) {
    'gross'
} else {
    'klein'
}
```

### foreach

Geht eine Liste Element für Element durch.

Syntax:

    foreach ($Element in $Liste) { }

Beispiel:

```
foreach ($Datei in Get-ChildItem *.txt) {
    $Datei.Name
}
```

### ForEach-Object (%, foreach)

Verarbeitet jedes Pipeline-Objekt. $_ ist das aktuelle Objekt.

Syntax:

    Befehl | ForEach-Object { $_ }

Beispiel:

```
Get-ChildItem *.log | ForEach-Object { $_.Length }
```

### Where-Object (?, where)

Lässt nur Objekte durch, auf die die Bedingung zutrifft.

Syntax:

    Befehl | Where-Object { <Bedingung> }

Beispiel:

```
Get-Service | Where-Object { $_.Status -eq 'Running' }
```

### try

Fängt einen Abbruch und führt den catch-Block aus.

Syntax:

    try { } catch { } finally { }

Beispiel:

```
try {
    Get-Content .\fehlt.txt -ErrorAction Stop
} catch {
    $_.Exception.Message
}
```

## Funktionen und Hilfe

Eine Funktion steht im Skript und wird danach mit ihrem Namen aufgerufen.

### function

Bündelt Befehle unter einem Namen.

Syntax:

    function Name { param($Wert) }

Beispiel:

```
function Gruss {
    param($Name)
    "Hallo $Name"
}
Gruss -Name Ada
```

### Get-Help (help)

Zeigt Erklärung, Parameter und Beispiele des Befehls.

Syntax:

    Get-Help <Befehl> [-Examples]

Beispiel:

```
Get-Help Get-ChildItem -Examples
```

### Get-Command (gcm)

Sucht Befehle, Aliase und Funktionen.

Syntax:

    Get-Command [-Name <Muster>]

Beispiel:

```
Get-Command *service*
```

### Get-Member (gm)

Zeigt Eigenschaften und Methoden eines Objekts.

Syntax:

    Objekt | Get-Member

Beispiel:

```
Get-Date | Get-Member
```

## System

Diese Befehle fragen Windows ab. Stop-Process beendet einen Prozess.

### Get-Process (ps, gps)

Listet laufende Prozesse.

Syntax:

    Get-Process [-Name <Name>]

Beispiel:

```
Get-Process -Name notepad
```

### Stop-Process (kill, spps)

Beendet einen Prozess über seinen Namen.

Syntax:

    Stop-Process -Name <Name>

Beispiel:

```
Stop-Process -Name notepad
```

### Get-Service (gsv)

Zeigt den Zustand eines Windows-Dienstes.

Syntax:

    Get-Service [-Name <Name>]

Beispiel:

```
Get-Service -Name Spooler
```

### Get-Date

Liefert das aktuelle Datum.

Syntax:

    Get-Date [-Format <Muster>]

Beispiel:

```
Get-Date -Format 'yyyy-MM-dd HH:mm'
```

# Linux-Shell

Bash-Skripte steuern Linux: Ordner, Dateien, Suche und eigene Abläufe. ShatuIDE öffnet .sh, .bash, .ksh, .zsh sowie .bashrc und .profile. Ausführen startet bash, sonst sh. Syntax prüfen ruft bash -n auf. Debug hält an Haltepunkten an. Unter Windows läuft dasselbe Skript, sobald Bash vorhanden ist, zum Beispiel über WSL oder Git Bash.

## Ordner und Dateien

Ein Leerzeichen trennt Befehl und Argument. Pfade mit Leerzeichen stehen in Anführungszeichen.

### pwd

Zeigt den aktuellen Ordner.

Syntax:

    pwd

Beispiel:

```
pwd
```

### cd

Wechselt den Ordner. cd ohne Argument geht ins Home-Verzeichnis.

Syntax:

    cd <Ordner>

Beispiel:

```
cd /tmp
```

### ls

Listet den Ordnerinhalt. -l zeigt Größe und Rechte, -a auch versteckte Namen.

Syntax:

    ls [-l] [-a] <Ordner>

Beispiel:

```
ls -la "$HOME"
```

### mkdir

Legt einen Ordner an. -p legt fehlende Zwischenordner mit an.

Syntax:

    mkdir [-p] <Ordner>

Beispiel:

```
mkdir -p "$HOME/arbeit/neu"
```

### cp

Kopiert eine Datei. -r kopiert einen Ordner samt Inhalt.

Syntax:

    cp <Quelle> <Ziel>

Beispiel:

```
cp notiz.txt sicherung.txt
```

### mv

Verschiebt oder benennt um.

Syntax:

    mv <Quelle> <Ziel>

Beispiel:

```
mv alt.txt neu.txt
```

### rm

Löscht eine Datei. -r löscht einen Ordner samt Inhalt.

Syntax:

    rm <Datei>

Beispiel:

```
rm notiz.txt
```

### touch

Legt eine leere Datei an oder setzt die Änderungszeit.

Syntax:

    touch <Datei>

Beispiel:

```
touch protokoll.txt
```

## Anzeigen und Suchen

grep sucht Text. find sucht Dateinamen.

### cat

Gibt den ganzen Dateiinhalt aus.

Syntax:

    cat <Datei>

Beispiel:

```
cat notiz.txt
```

### head

Zeigt die ersten Zeilen, voreingestellt zehn.

Syntax:

    head [-n <Anzahl>] <Datei>

Beispiel:

```
head -n 20 protokoll.txt
```

### tail

Zeigt die letzten Zeilen.

Syntax:

    tail [-n <Anzahl>] <Datei>

Beispiel:

```
tail -n 20 protokoll.txt
```

### grep

Sucht ein Muster. -n zeigt die Zeilennummer, -i ignoriert Groß- und Kleinschreibung.

Syntax:

    grep [-n] [-i] <Muster> <Datei>

Beispiel:

```
grep -n Fehler protokoll.txt
```

### find

Sucht Dateien unterhalb eines Ordners.

Syntax:

    find <Ordner> -name <Muster>

Beispiel:

```
find . -name '*.sh'
```

## Variablen und Eingabe

Vor und hinter dem Gleichheitszeichen steht kein Leerzeichen. $Name liest den Wert.

### Variable

Speichert einen Wert. Beim Lesen steht ein Dollarzeichen davor.

Syntax:

    name=wert

Beispiel:

```
name=Ada
echo "$name"
```

### echo

Gibt Text aus. In doppelten Anführungszeichen wird $name eingesetzt.

Syntax:

    echo <Text>

Beispiel:

```
echo "Hallo $name"
```

### printf

Gibt Text mit Format aus, zum Beispiel Zahlen und Zeilenenden.

Syntax:

    printf '<Format>' <Werte>

Beispiel:

```
printf 'Wert: %s\n' "$name"
```

### read

Liest eine Zeile von der Tastatur in die Variable.

Syntax:

    read -r <Name>

Beispiel:

```
read -r ort
echo "Ort: $ort"
```

### export

Macht die Variable für aufgerufene Programme sichtbar.

Syntax:

    export <Name>=<Wert>

Beispiel:

```
export LANG=de_DE.UTF-8
```

## Entscheidungen und Schleifen

then, do und done schließen den Block. Die Einrückung dient der Lesbarkeit.

### if

Der if-Zweig läuft, wenn der Befehl mit Status 0 endet.

Syntax:

    if <Befehl>; then ...; else ...; fi

Beispiel:

```
if [ -f notiz.txt ]; then
    echo da
else
    echo fehlt
fi
```

### for

Setzt die Variable nacheinander auf jeden Listeneintrag.

Syntax:

    for name in <Liste>; do ...; done

Beispiel:

```
for datei in *.txt; do
    echo "$datei"
done
```

### while

Wiederholt den Block, solange der Befehl mit Status 0 endet.

Syntax:

    while <Befehl>; do ...; done

Beispiel:

```
n=1
while [ "$n" -le 3 ]; do
    echo "$n"
    n=$((n + 1))
done
```

### function

Bündelt Befehle. Der Aufruf ist der Funktionsname.

Syntax:

    name() { ...; }

Beispiel:

```
gruss() {
    echo "Hallo $1"
}
gruss Ada
```

## Rechte, Pipes und Prüfung

Eine Pipe schickt die Ausgabe des linken Befehls an den rechten. bash -n prüft, ohne zu starten.

### chmod

Setzt die Rechte. +x macht ein Skript ausführbar.

Syntax:

    chmod <Modus> <Datei>

Beispiel:

```
chmod +x hallo.sh
```

### Pipe

Gibt die Ausgabe weiter. > schreibt eine Datei neu, >> hängt an.

Syntax:

    befehl | befehl

Beispiel:

```
ls | grep txt > liste.txt
```

### bash -n

Prüft die Syntax und führt das Skript nicht aus.

Syntax:

    bash -n <Skript>

Beispiel:

```
bash -n hallo.sh
```

### set -x

Zeigt vor jeder Zeile den ausgeführten Befehl. set +x schaltet das wieder aus.

Syntax:

    set -x

Beispiel:

```
set -x
echo hallo
set +x
```

# Windows-Batch

Eine Batch-Datei ist eine Liste von Befehlen für die Windows-Eingabeaufforderung cmd.exe. ShatuIDE öffnet .bat und .cmd. Ausführen startet cmd.exe /c und gibt es nur unter Windows. Die Funktionsleiste zeigt die Sprungmarken. cmd.exe hat keine getrennte Syntaxprüfung; ein Tippfehler fällt beim Lauf auf. In der Datei heißen Schleifenvariablen %%A, auf der Kommandozeile %A.

## Grundgerüst

@echo off unterdrückt die Befehlszeilen selbst. rem ist der Kommentar.

### @echo off

Zeigt die folgenden Befehle nicht mehr selbst an, nur ihre Ausgabe.

Syntax:

    @echo off

Beispiel:

```
@echo off
echo Hallo
```

### echo

Gibt eine Zeile aus. echo. gibt eine leere Zeile aus.

Syntax:

    echo <Text>

Beispiel:

```
echo Fertig.
```

### rem

Kommentar. Die Zeile wird nicht ausgeführt. :: am Zeilenanfang gilt ebenso als Kommentar.

Syntax:

    rem <Text>

Beispiel:

```
rem Diese Zeile erklärt den nächsten Schritt.
```

### pause

Wartet auf eine Taste, damit das Fenster offen bleibt.

Syntax:

    pause

Beispiel:

```
echo Ende
pause
```

### exit

Beendet die Batch-Datei. Die Zahl ist der Rückgabewert.

Syntax:

    exit /b <Zahl>

Beispiel:

```
exit /b 0
```

## Variablen

set speichert Text. Beim Lesen steht der Name zwischen Prozentzeichen. setlocal hält die Variablen in dieser Datei.

### set

Speichert Text. set ohne Argument listet alle Variablen.

Syntax:

    set NAME=Wert

Beispiel:

```
set NAME=Ada
echo %NAME%
```

### setlocal

Änderungen an Variablen gelten bis endlocal oder bis zum Ende der Datei.

Syntax:

    setlocal

Beispiel:

```
setlocal
set NAME=Ada
endlocal
```

### %NAME%

Setzt den gespeicherten Wert ein. Die Ersetzung passiert beim Lesen der Zeile.

Syntax:

    echo %NAME%

Beispiel:

```
set ORT=Hamburg
echo Ort: %ORT%
```

### set /a

Rechnet mit ganzen Zahlen.

Syntax:

    set /a NAME=Ausdruck

Beispiel:

```
set /a SUMME=2+3
echo %SUMME%
```

## Dateien und Ordner

Pfade mit Leerzeichen stehen in Anführungszeichen.

### cd

Wechselt den Ordner. /d wechselt dabei auch das Laufwerk.

Syntax:

    cd /d <Ordner>

Beispiel:

```
cd /d D:\AI_Temp\ShatuIDE
```

### dir

Listet den Ordnerinhalt.

Syntax:

    dir <Ordner>

Beispiel:

```
dir C:\Temp\*.txt
```

### md

Legt einen Ordner an.

Syntax:

    md <Ordner>

Beispiel:

```
md ausgabe
```

### copy

Kopiert eine Datei.

Syntax:

    copy <Quelle> <Ziel>

Beispiel:

```
copy notiz.txt sicherung.txt
```

### move

Verschiebt oder benennt um.

Syntax:

    move <Quelle> <Ziel>

Beispiel:

```
move alt.txt neu.txt
```

### del

Löscht eine Datei.

Syntax:

    del <Datei>

Beispiel:

```
del notiz.txt
```

### type

Gibt den Dateiinhalt aus.

Syntax:

    type <Datei>

Beispiel:

```
type notiz.txt
```

### if exist

Führt den Befehl aus, wenn die Datei oder der Ordner vorhanden ist.

Syntax:

    if exist <Pfad> <Befehl>

Beispiel:

```
if exist notiz.txt echo da
```

## Entscheidungen und Sprünge

Eine Sprungmarke beginnt mit einem Doppelpunkt. goto springt dorthin. call kehrt danach zurück.

### if

Vergleicht zwei Texte. Der Block in Klammern darf mehrere Zeilen haben.

Syntax:

    if "<Text>"=="<Text>" <Befehl>

Beispiel:

```
if "%NAME%"=="Ada" (
    echo hallo
) else (
    echo unbekannt
)
```

### goto

Springt zur Zeile :Marke und kehrt nicht zurück.

Syntax:

    goto :Marke

Beispiel:

```
goto :Ende
echo unsichtbar
:Ende
echo hier
```

### call

Springt zur Marke und macht nach dem Rücksprung mit der nächsten Zeile weiter.

Syntax:

    call :Marke

Beispiel:

```
call :Gruss
echo danach
goto :eof
:Gruss
echo hallo
goto :eof
```

### :Marke

Sprungziel. Der Name erscheint in der Funktionsleiste von ShatuIDE.

Syntax:

    :Name

Beispiel:

```
:Start
echo noch einmal
```

## Schleifen und Argumente

%%A ist die Schleifenvariable in der Datei. %1 ist das erste Argument beim Start.

### for

Wiederholt den Befehl für jeden Eintrag. for /f liest Zeilen einer Datei oder eines Befehls.

Syntax:

    for %%A in (<Liste>) do <Befehl>

Beispiel:

```
for %%F in (*.txt) do echo %%F
```

### %1

%1 ist das erste Argument, %2 das zweite. %* sind alle Argumente.

Syntax:

    %1  %*

Beispiel:

```
echo Datei: %1
```

### %~dp0

Ordner der Batch-Datei, mit einem Backslash am Ende.

Syntax:

    %~dp0

Beispiel:

```
cd /d "%~dp0"
```

### %ERRORLEVEL%

Nach einem Befehl steht hier dessen Rückgabewert. 0 bedeutet in der Regel Erfolg.

Syntax:

    if errorlevel 1

Beispiel:

```
copy notiz.txt ziel.txt
if errorlevel 1 echo Kopieren fehlgeschlagen
```
