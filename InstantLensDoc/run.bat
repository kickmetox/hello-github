@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM InstantLens Doc 2.6.38 - ASCII-safe launcher (cmd.exe / CP1252-safe)
REM No fancy Unicode (em-dash/ellipsis/arrows/smart-quotes) - those break cmd as mojibake quotes.
REM No markdown/help prose executed as commands; paren-safe echo inside IF blocks.
chcp 65001 >nul
cd /d "%~dp0"

REM Optional: pip install -r requirements.txt via J/N - or non-interactive --yes / -y
REM Help: run.bat --help / -h
REM
REM Env override (highest priority):
REM   set ILD_PYTHON=C:\Path\to\python.exe
REM   run.bat
REM If ILD_PYTHON is set and points to an existing file, that interpreter is used
REM (before .venv and PATH). Invalid/empty ILD_PYTHON: warn (if set) + fallback
REM   py -3 -> python -> python3 (then .venv if present, else error).
REM
REM Exit codes:
REM   0  OK (app exit 0) or --help shown
REM   1  Error: Python missing / version ^<3.10 / deps missing / pip failed /
REM      install declined / non-zero app exit is passed through
REM
REM Examples:
REM   run.bat
REM   run.bat --yes
REM   set ILD_PYTHON=C:\Python312\python.exe ^& run.bat
REM   run.bat --help

set "ILD_YES="
set "ILD_HELP="
set "ILD_APP_ARGS="
for %%A in (%*) do (
  if /i "%%~A"=="--yes" (
    set "ILD_YES=1"
  ) else if /i "%%~A"=="-y" (
    set "ILD_YES=1"
  ) else if /i "%%~A"=="--help" (
    set "ILD_HELP=1"
  ) else if /i "%%~A"=="-h" (
    set "ILD_HELP=1"
  ) else if /i "%%~A"=="/?" (
    set "ILD_HELP=1"
  ) else (
    set "ILD_APP_ARGS=!ILD_APP_ARGS! %%~A"
  )
)

if defined ILD_HELP goto :show_help
goto :resolve_python

:show_help
echo.
echo InstantLens Doc - run.bat Hilfe
echo.
echo Verwendung:
echo   run.bat [Optionen] [App-Argumente...]
echo.
echo Optionen:
echo   --help, -h, /?   Diese Hilfe auf Deutsch anzeigen und beenden ^(Exit 0^)
echo   --yes, -y        Fehlende Abhaengigkeiten ohne Rueckfrage per pip installieren
echo.
echo Umgebungsvariable:
echo   ILD_PYTHON       Optionaler Pfad zu python.exe ^(Env-Override, hoechste Prio^)
echo                    Beispiel: set ILD_PYTHON=C:\Python312\python.exe
echo                    Wenn gesetzt und Datei existiert: wird vor .venv/PATH genutzt.
echo                    Ungueltig/leer: Warnung, dann .venv falls vorhanden,
echo                    sonst Fallback py -3 -^> python -^> python3.
echo.
echo Pruefungen:
echo   - Python 3.10+ ^(ILD_PYTHON, sonst .venv, sonst py -3/python/python3^)
echo   - Nach Auswahl: gefunden + kurz python --version
echo   - Kern-Pakete: PySide6, pypdfium2, pikepdf, Pillow
echo.
echo Exit-Codes:
echo   0  OK ^(App beendet mit 0^) bzw. Hilfe angezeigt
echo   1  Python/Deps/pip-Fehler bzw. Installation abgelehnt;
echo      App-Exitcode != 0 wird durchgereicht
echo.
echo Beispiele:
echo   run.bat
echo   run.bat --yes
echo   run.bat -y
echo   set ILD_PYTHON=C:\Python312\python.exe
echo   run.bat
echo   run.bat --help
echo.
exit /b 0

:resolve_python
set "PYEXE="
set "ILD_USED_VENV="
set "ILD_USED_ENV="
set "ILD_NEED_FALLBACK="

if defined ILD_PYTHON (
  if exist "%ILD_PYTHON%" (
    set "PYEXE=%ILD_PYTHON%"
    set "ILD_USED_ENV=1"
    echo [InstantLens Doc] Nutze ILD_PYTHON=%ILD_PYTHON%
  ) else (
    echo.
    echo [InstantLens Doc] WARNUNG: ILD_PYTHON ist ungueltig.
    echo Die Datei existiert nicht oder ist kein ausfuehrbarer Python-Interpreter:
    echo   %ILD_PYTHON%
    echo Fallback: versuche py -3, dann python, dann python3 ...
    echo.
    set "ILD_NEED_FALLBACK=1"
  )
) else (
  set "ILD_NEED_FALLBACK=1"
)

if defined ILD_NEED_FALLBACK if not defined PYEXE (
  if exist ".venv\Scripts\python.exe" (
    set "PYEXE=.venv\Scripts\python.exe"
    set "ILD_USED_VENV=1"
  )
)
if defined ILD_NEED_FALLBACK if not defined PYEXE (
  py -3 -c "import sys" >nul 2>&1
  if not errorlevel 1 (
    set "PYEXE=py -3"
    echo [InstantLens Doc] Fallback: py -3
  )
)
if defined ILD_NEED_FALLBACK if not defined PYEXE (
  python -c "import sys" >nul 2>&1
  if not errorlevel 1 (
    set "PYEXE=python"
    echo [InstantLens Doc] Fallback: python
  )
)
if defined ILD_NEED_FALLBACK if not defined PYEXE (
  python3 -c "import sys" >nul 2>&1
  if not errorlevel 1 (
    set "PYEXE=python3"
    echo [InstantLens Doc] Fallback: python3
  )
)
if defined ILD_NEED_FALLBACK if not defined PYEXE (
  echo.
  echo [InstantLens Doc] FEHLER: Python wurde nicht gefunden.
  echo Fallback-Reihenfolge ohne Treffer: py -3 -^> python -^> python3
  echo.
  if exist ".venv\" (
    echo Hinweis: Lokaler Ordner .venv ist vorhanden, aber
    echo   .venv\Scripts\python.exe fehlt ^(venv unvollstaendig^).
    echo Bitte neu anlegen:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    echo.
  )
  echo Optional: set ILD_PYTHON=C:\Pfad\zu\python.exe
  echo.
  echo Download Python 3.12+ ^(kurz^):
  echo   Microsoft Store: Python 3.12 suchen und installieren
  echo   oder https://www.python.org/downloads/
  echo Beim Installer Add python.exe to PATH aktivieren, dann erneut run.bat.
  echo.
  if not defined ILD_YES pause
  exit /b 1
)
if defined ILD_NEED_FALLBACK if defined PYEXE if not defined ILD_USED_VENV if exist ".venv\" (
  echo [InstantLens Doc] Hinweis: Lokaler Ordner .venv vorhanden, aber
  echo   .venv\Scripts\python.exe fehlt - System-Python wird genutzt.
  echo   Zum Reparieren: python -m venv .venv
  echo   .venv\Scripts\pip install -r requirements.txt
  echo   Oder: set ILD_PYTHON=C:\Pfad\zu\python.exe
  echo.
)

set "ILD_PYVER="
for /f "delims=" %%V in ('%PYEXE% --version 2^>^&1') do (
  if not defined ILD_PYVER set "ILD_PYVER=%%V"
)
if defined ILD_PYVER (
  echo [InstantLens Doc] gefunden: %PYEXE%  ^(%ILD_PYVER%^)
) else (
  echo [InstantLens Doc] gefunden: %PYEXE%
)

echo [InstantLens Doc] Python-Pruefung ...
%PYEXE% -c "import sys; v=sys.version_info; raise SystemExit(0 if v.major==3 and v.minor>=10 else 1)" >nul 2>&1
if errorlevel 1 (
  echo.
  echo [InstantLens Doc] FEHLER: Python 3.10 oder neuer ist erforderlich.
  echo Gefundene Python-Version:
  %PYEXE% --version 2>&1
  echo.
  echo Bitte eine passende Version installieren und PATH pruefen.
  echo Optional: set ILD_PYTHON=C:\Pfad\zu\python.exe
  echo.
  if not defined ILD_YES pause
  exit /b 1
)

echo [InstantLens Doc] Abhaengigkeiten pruefen ...
%PYEXE% -c "import PySide6, pypdfium2, pikepdf, PIL" >nul 2>&1
if not errorlevel 1 goto :start_app

echo.
echo [InstantLens Doc] FEHLER: Erforderliche Pakete fehlen.
echo Benoetigt u. a.: PySide6, pypdfium2, pikepdf, Pillow
echo Optional fuer OCR: pytesseract + Tesseract-Runtime
echo.
if exist ".venv\" if not defined ILD_USED_VENV if not defined ILD_USED_ENV (
  echo Hinweis: Lokaler Ordner .venv vorhanden - ggf. dort installieren:
  echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
  echo   ^(run.bat nutzt .venv automatisch, sobald Scripts\python.exe existiert^)
  echo.
)
if not exist "requirements.txt" (
  echo [InstantLens Doc] requirements.txt nicht gefunden - bitte manuell installieren:
  echo   %PYEXE% -m pip install -r requirements.txt
  echo.
  if not defined ILD_YES pause
  exit /b 1
)
echo Fehlende Pakete mit pip installieren:
echo   %PYEXE% -m pip install -r requirements.txt
if defined ILD_YES (
  echo [InstantLens Doc] --yes: Installation ohne Rueckfrage ...
  goto :do_pip
)
set "ILD_PIP="
set /p "ILD_PIP=Jetzt installieren? [J/N]: "
if /i "!ILD_PIP!"=="J" goto :do_pip
if /i "!ILD_PIP!"=="Y" goto :do_pip
if /i "!ILD_PIP!"=="JA" goto :do_pip
echo.
echo Installation abgebrochen. Manuell ausfuehren:
echo   %PYEXE% -m pip install -r requirements.txt
echo Oder non-interactive: run.bat --yes
echo.
pause
exit /b 1

:do_pip
echo.
echo [InstantLens Doc] Installiere Abhaengigkeiten ...
%PYEXE% -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [InstantLens Doc] FEHLER: pip install ist fehlgeschlagen.
  echo Bitte Netzwerk/Rechte pruefen und erneut versuchen.
  echo.
  if not defined ILD_YES pause
  exit /b 1
)
echo [InstantLens Doc] Abhaengigkeiten erneut pruefen ...
%PYEXE% -c "import PySide6, pypdfium2, pikepdf, PIL" >nul 2>&1
if errorlevel 1 (
  echo.
  echo [InstantLens Doc] FEHLER: Pakete fehlen weiterhin nach der Installation.
  echo.
  if not defined ILD_YES pause
  exit /b 1
)

:start_app
echo [InstantLens Doc] Start ...
%PYEXE% -m instantlensdoc !ILD_APP_ARGS!
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
  echo.
  echo [InstantLens Doc] Die Anwendung wurde mit Fehlercode %EC% beendet.
  if not defined ILD_YES pause
)
exit /b %EC%
