@echo off
cd /d "%~dp0"
where py >nul 2>nul && py -3 shatuide.py %* && exit /b %errorlevel%
python shatuide.py %*
