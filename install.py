#!/usr/bin/env python3
"""Kopiert ShatuIDE nach D:\\AI_Temp\\ShatuIDE und lässt vorhandene Icons stehen."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
TARGET = Path(r"D:\AI_Temp\ShatuIDE")
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".shatuide", ".pytest_cache", "dist", "build"}
PRESERVE = {
    "icon.png",
    "icon.ico",
    "icon.jpg",
    "icon.jpeg",
    "icon.webp",
    "logo.png",
    "logo.ico",
    "grafik.png",
    "grafik.jpg",
    "graphic.png",
    "bild.png",
    "app.ico",
    "app.png",
    "shatuide.png",
    "shatuide.jpg",
    "shatuide.jpeg",
}


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.relative_to(SOURCE).parts)


def install(target: Path = TARGET) -> Path:
    target.mkdir(parents=True, exist_ok=True)
    for dirpath, dirnames, filenames in os.walk(SOURCE):
        current = Path(dirpath)
        if current != SOURCE and should_skip(current):
            dirnames[:] = []
            continue
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS and not name.startswith(".")]
        relative = current.relative_to(SOURCE)
        destination_dir = target / relative
        destination_dir.mkdir(parents=True, exist_ok=True)
        for name in filenames:
            if name.endswith(".pyc"):
                continue
            src = current / name
            dest = destination_dir / name
            if name in PRESERVE and dest.exists():
                continue
            if src.resolve() == dest.resolve():
                continue
            shutil.copy2(src, dest)
    return target


def main() -> None:
    if os.name != "nt" and "--force" not in sys.argv:
        print("Dieses System hat kein Windows-Laufwerk D:.")
        print("ShatuIDE liegt hier:", SOURCE)
        print("Start: python3 shatuide.py")
        print("Unter Windows kopiert `python install.py` nach", TARGET)
        print("und überschreibt icon.png, grafik.png und logo.* nicht.")
        return
    target = install()
    print("Installiert nach", target)
    print("Vorhandene Icon- und Grafikdateien wurden beibehalten.")
    print("Start: python shatuide.py")


if __name__ == "__main__":
    main()
