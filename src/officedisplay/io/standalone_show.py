"""Programmordner: show.oshow plus abgeschlossener Player, ohne den Editor."""

from __future__ import annotations

import stat
from pathlib import Path

from officedisplay.io.slideshow_io import save_presentation_oshow
from officedisplay.model.presentation import Presentation


_PLAYER = Path(__file__).with_name("standalone_player.py")

LIESMICH = (
    "Doppelklick auf Slideshow.bat.\n"
    "Escape beendet.\n"
    "PySide6 muss installiert sein.\n"
)

SLIDESHOW_BAT = """@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0"
where pythonw >nul 2>&1
if %errorlevel%==0 (
  start "" pythonw "%~dp0player.py"
  exit /b 0
)
where python >nul 2>&1
if %errorlevel%==0 (
  python "%~dp0player.py"
  exit /b %errorlevel%
)
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 "%~dp0player.py"
  exit /b %errorlevel%
)
echo Python wurde nicht gefunden.
echo Bitte Python installieren: https://www.python.org/downloads/
echo PySide6 wird benötigt: python -m pip install PySide6
pause
exit /b 1
"""

SLIDESHOW_SH = """#!/bin/sh
cd "$(dirname "$0")" || exit 1
export PYTHONPATH="$PWD"
if command -v python3 >/dev/null 2>&1; then
  exec python3 "$PWD/player.py"
fi
echo "Python wurde nicht gefunden."
echo "Bitte Python installieren: https://www.python.org/downloads/"
echo "PySide6 wird benötigt: python -m pip install PySide6"
exit 1
"""


def write_standalone_show(presentation: Presentation, folder: str | Path) -> Path:
    """Ordner zum Kopieren: Player, show.oshow und Startskripte."""
    target = Path(folder)
    target.mkdir(parents=True, exist_ok=True)
    save_presentation_oshow(presentation, target / "show.oshow")
    (target / "player.py").write_text(_PLAYER.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    (target / "Slideshow.bat").write_bytes(SLIDESHOW_BAT.replace("\n", "\r\n").encode("utf-8"))
    script = target / "Slideshow.sh"
    script.write_text(SLIDESHOW_SH, encoding="utf-8", newline="\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    (target / "liesmich.txt").write_text(LIESMICH, encoding="utf-8", newline="\n")
    return target
