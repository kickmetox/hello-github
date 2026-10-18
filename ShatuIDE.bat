@echo off
cd /d "%~dp0"
if exist "%~dp0ShatuIDE.exe" (
  start "" "%~dp0ShatuIDE.exe" %*
  exit /b 0
)
where py >nul 2>nul && py -3 shatuide.py %* && exit /b %errorlevel%
python shatuide.py %*
