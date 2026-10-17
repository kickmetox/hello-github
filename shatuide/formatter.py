"""PEP-8-Formatierung über Black, Ruff oder einen eingebauten Fallback."""

from __future__ import annotations

import shutil
import subprocess


def format_source(source: str, python: str | None = None) -> dict:
    interpreters = []
    if python:
        interpreters.append(python)
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found and found not in interpreters:
            interpreters.append(found)
    attempts = [
        ("black", ["-m", "black", "-q", "-"]),
        ("ruff", ["-m", "ruff", "format", "-"]),
    ]
    for tool, args in attempts:
        for exe in interpreters:
            try:
                proc = subprocess.run(
                    [exe, *args],
                    input=source,
                    text=True,
                    capture_output=True,
                    timeout=40,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            if proc.returncode == 0 and proc.stdout:
                text = proc.stdout
                if not text.endswith("\n"):
                    text += "\n"
                return {"ok": True, "content": text, "tool": tool}
    return {"ok": True, "content": fallback_format(source), "tool": "shatu"}


def fallback_format(source: str) -> str:
    lines = source.replace("\t", "    ").splitlines()
    cleaned = [line.rstrip() for line in lines]
    text = "\n".join(cleaned)
    if text and not text.endswith("\n"):
        text += "\n"
    return text
