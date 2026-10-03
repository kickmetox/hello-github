@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

REM InstantLens Doc 1.2.8 — Start mit Python-/Abhängigkeitsprüfung (DE-Meldungen)
REM Optional: pip install -r requirements.txt per J/N — oder non-interactive mit --yes / -y
REM Hilfe: run.bat --help / -h
REM
REM Env-Override (höchste Priorität):
REM   set ILD_PYTHON=C:\Pfad\zu\python.exe
REM   run.bat
REM Wenn %%ILD_PYTHON%% gesetzt ist und auf eine existierende Datei zeigt, wird genau
REM dieser Interpreter genutzt (vor .venv und PATH).
REM Bei ungültigem/leerem ILD_PYTHON: Warnung (wenn gesetzt) + Fallback
REM   py -3 → python → python3 (danach .venv falls vorhanden, sonst Fehler).
REM Nach Auswahl: Konsolenzeile „gefunden: …“ mit gewählter Python-Binary — 1.2.8
REM
REM Exit-Codes:
REM   0  OK (App beendet mit 0) bzw. --help angezeigt
REM   1  Fehler: Python fehlt / Version ^<3.10 / Deps fehlen / pip fehlgeschlagen /
REM      Installation abgelehnt / App-Exitcode != 0 wird durchgereicht
REM
REM Beispiele:
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

if defined ILD_HELP (
  echo.
  echo InstantLens Doc — run.bat Hilfe
  echo.
  echo Verwendung:
  echo   run.bat [Optionen] [App-Argumente...]
  echo.
  echo Optionen:
  echo   --help, -h, /?   Diese Hilfe auf Deutsch anzeigen und beenden (Exit 0^)
  echo   --yes, -y        Fehlende Abhaengigkeiten ohne Rueckfrage per pip installieren
  echo.
  echo Umgebungsvariable:
  echo   ILD_PYTHON       Optionaler Pfad zu python.exe ^(Env-Override, hoechste Prio^)
  echo                    Beispiel: set ILD_PYTHON=C:\Python312\python.exe
  echo                    Wenn gesetzt und Datei existiert: wird vor .venv/PATH genutzt.
  echo                    Ungueltig/leer: Warnung, dann .venv falls vorhanden,
  echo                    sonst Fallback py -3 → python → python3.
  echo.
  echo Pruefungen:
  echo   - Python 3.10+ ^(ILD_PYTHON, sonst .venv, sonst py -3/python/python3^)
  echo   - Nach Auswahl: „gefunden: …“ mit gewaehlter Binary
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
)

set "PYEXE="
set "ILD_USED_VENV="
set "ILD_USED_ENV="
set "ILD_NEED_FALLBACK="

REM 1.2.5–1.2.8: %%ILD_PYTHON%% Env-Override (höchste Priorität)
REM Bei ungültig/leer: Fallback-Kette py -3 → python → python3 — 1.2.7
REM Gewählte Binary: „gefunden: …“ — 1.2.8
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
    echo Fallback: versuche py -3, dann python, dann python3 …
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
  REM 1.2.7: PATH-Fallback-Reihenfolge py -3 → python → python3
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
  echo Fallback-Reihenfolge ohne Treffer: py -3 → python → python3
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
  echo   Microsoft Store: „Python 3.12“ suchen und installieren
  echo   oder https://www.python.org/downloads/
  echo Beim Installer „Add python.exe to PATH“ aktivieren, dann erneut run.bat.
  echo.
  if not defined ILD_YES pause
  exit /b 1
)
if defined ILD_NEED_FALLBACK if defined PYEXE if not defined ILD_USED_VENV if exist ".venv\" (
  echo [InstantLens Doc] Hinweis: Lokaler Ordner .venv vorhanden, aber
  echo   .venv\Scripts\python.exe fehlt — System-Python wird genutzt.
  echo   Zum Reparieren: python -m venv .venv
  echo   .venv\Scripts\pip install -r requirements.txt
  echo   Oder: set ILD_PYTHON=C:\Pfad\zu\python.exe
  echo.
)

REM 1.2.8: gewählte Python-Binary in Konsolenzeile ausgeben
echo [InstantLens Doc] gefunden: %PYEXE%

echo [InstantLens Doc] Python-Pruefung …
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

echo [InstantLens Doc] Abhaengigkeiten pruefen …
%PYEXE% -c "import PySide6, pypdfium2, pikepdf, PIL" >nul 2>&1
if not errorlevel 1 goto :start_app

echo.
echo [InstantLens Doc] FEHLER: Erforderliche Pakete fehlen.
echo Benoetigt u. a.: PySide6, pypdfium2, pikepdf, Pillow
echo Optional fuer OCR: pytesseract + Tesseract-Runtime
echo.
if exist ".venv\" if not defined ILD_USED_VENV if not defined ILD_USED_ENV (
  echo Hinweis: Lokaler Ordner .venv vorhanden — ggf. dort installieren:
  echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
  echo   ^(run.bat nutzt .venv automatisch, sobald Scripts\python.exe existiert^)
  echo.
)
if not exist "requirements.txt" (
  echo [InstantLens Doc] requirements.txt nicht gefunden — bitte manuell installieren:
  echo   %PYEXE% -m pip install -r requirements.txt
  echo.
  if not defined ILD_YES pause
  exit /b 1
)
echo Fehlende Pakete mit pip installieren:
echo   %PYEXE% -m pip install -r requirements.txt
if defined ILD_YES (
  echo [InstantLens Doc] --yes: Installation ohne Rueckfrage …
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
echo [InstantLens Doc] Installiere Abhaengigkeiten …
%PYEXE% -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [InstantLens Doc] FEHLER: pip install ist fehlgeschlagen.
  echo Bitte Netzwerk/Rechte pruefen und erneut versuchen.
  echo.
  if not defined ILD_YES pause
  exit /b 1
)
echo [InstantLens Doc] Abhaengigkeiten erneut pruefen …
%PYEXE% -c "import PySide6, pypdfium2, pikepdf, PIL" >nul 2>&1
if errorlevel 1 (
  echo.
  echo [InstantLens Doc] FEHLER: Pakete fehlen weiterhin nach der Installation.
  echo.
  if not defined ILD_YES pause
  exit /b 1
)

:start_app
echo [InstantLens Doc] Start …
%PYEXE% -m instantlensdoc !ILD_APP_ARGS!
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
  echo.
  echo [InstantLens Doc] Die Anwendung wurde mit Fehlercode %EC% beendet.
  if not defined ILD_YES pause
)
exit /b %EC%
