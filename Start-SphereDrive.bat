@echo off
setlocal
set "TARGET=D:\AI_Temp\SphereDrive"
set "SOURCE=%~dp0"

if not exist "D:\" (
    echo Laufwerk D: ist nicht erreichbar.
    echo SphereDrive legt den Arbeitsordner unter %TARGET% an.
    pause
    exit /b 1
)

if /I not "%SOURCE%"=="%TARGET%\" (
    mkdir "%TARGET%" 2>nul
    if not exist "%TARGET%\" (
        echo Der Pfad kann nicht geoeffnet werden: %TARGET%
        pause
        exit /b 1
    )
    robocopy "%SOURCE%." "%TARGET%" SphereDrive.pyw Start-SphereDrive.bat README.md SphereDrive-Setup-1.0.0.exe /NFL /NDL /NJH /NJS /NC /NS /NP >nul
    robocopy "%SOURCE%assets" "%TARGET%\assets" /E /NFL /NDL /NJH /NJS /NC /NS /NP >nul
    robocopy "%SOURCE%spheredrive" "%TARGET%\spheredrive" /E /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NC /NS /NP >nul
    if not exist "%TARGET%\SphereDrive.ico" if exist "%SOURCE%assets\SphereDrive.ico" copy /Y "%SOURCE%assets\SphereDrive.ico" "%TARGET%\SphereDrive.ico" >nul
    if not exist "%TARGET%\SphereDrive.png" if exist "%SOURCE%assets\SphereDrive.png" copy /Y "%SOURCE%assets\SphereDrive.png" "%TARGET%\SphereDrive.png" >nul
)

cd /d "%TARGET%"
set "SCRIPT=%TARGET%\SphereDrive.pyw"

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
