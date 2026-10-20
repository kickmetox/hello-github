@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0\.."
set "ROOT=%CD%"

set "PYCMD="
python --version >nul 2>&1
if not errorlevel 1 set "PYCMD=python"
if not defined PYCMD (
  py -3 --version >nul 2>&1
  if not errorlevel 1 set "PYCMD=py -3"
)
if not defined PYCMD (
  echo Python wurde nicht gefunden.
  echo Bitte Python 3.12 installieren: https://www.python.org/downloads/
  echo Beim Setup "Add python.exe to PATH" aktivieren, danach installer\install.bat erneut starten.
  pause
  exit /b 1
)

echo Python wird verwendet:
%PYCMD% --version
if errorlevel 1 (
  echo Python ließ sich nicht starten.
  echo Bitte Python 3.12 installieren: https://www.python.org/downloads/
  pause
  exit /b 1
)

if not exist "%ROOT%\.venv\Scripts\python.exe" (
  %PYCMD% -m venv "%ROOT%\.venv"
  if errorlevel 1 (
    echo Die Umgebung .venv ließ sich nicht anlegen.
    pause
    exit /b 1
  )
)

"%ROOT%\.venv\Scripts\python.exe" -m pip install -r "%ROOT%\requirements.txt"
if errorlevel 1 (
  echo Die Pakete aus requirements.txt ließen sich nicht installieren.
  pause
  exit /b 1
)

> "%ROOT%\Office Display.bat" (
  echo @echo off
  echo setlocal
  echo cd /d "%%~dp0"
  echo set "PYTHONPATH=%%CD%%\src"
  echo "%%CD%%\.venv\Scripts\python.exe" -m officedisplay
)

where cmake >nul 2>&1
if errorlevel 1 (
  echo CMake wurde nicht gefunden. Die Python-Farbrechnung wird genutzt.
) else (
  cmake -S "%ROOT%\native\cpp" -B "%ROOT%\native\cpp\build"
  if errorlevel 1 (
    echo native\cpp wurde nicht gebaut. Die Python-Farbrechnung wird genutzt.
  ) else (
    cmake --build "%ROOT%\native\cpp\build"
    if errorlevel 1 (
      echo native\cpp wurde nicht gebaut. Die Python-Farbrechnung wird genutzt.
    ) else (
      echo native\cpp wurde gebaut.
    )
  )
)

echo Installation fertig. Start über Office Display.bat
pause
exit /b 0
