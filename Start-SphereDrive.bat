@echo off
setlocal
cd /d "%~dp0"
set "SCRIPT=%~dp0SphereDrive.pyw"

where pyw >nul 2>&1
if %errorlevel%==0 (
    start "" pyw -3 "%SCRIPT%" %*
    exit /b 0
)

where pythonw >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw "%SCRIPT%" %*
    exit /b 0
)

echo Python 3 wurde nicht gefunden.
echo Bitte Python fuer Windows installieren und "py"-Startprogramm aktivieren.
echo https://www.python.org/downloads/
pause
exit /b 1
