"""Unit-Tests und Coverage."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_argv(python: str, workspace: str, target: str, framework: str) -> list[str]:
    framework = framework or "auto"
    if framework == "pytest":
        return [python, "-m", "pytest", "-q", "--tb=short", target or workspace]
    if framework == "doctest":
        if not target:
            raise ValueError("doctest braucht eine Datei.")
        return [python, "-m", "doctest", "-v", target]
    if framework == "unittest":
        return [python, "-m", "unittest", "discover", "-s", target or workspace, "-v"]
    # auto: pytest wenn vorhanden, sonst unittest
    probe = subprocess.run([python, "-c", "import pytest"], capture_output=True, check=False)
    if probe.returncode == 0:
        return [python, "-m", "pytest", "-q", "--tb=short", target or workspace]
    return [python, "-m", "unittest", "discover", "-s", target or workspace, "-v"]


def coverage_argv(python: str, workspace: str, target: str) -> list[str]:
    return [python, "-m", "coverage", "run", "--source", workspace, "-m", "pytest", "-q", target or workspace]


def read_coverage(python: str, workspace: str) -> dict:
    proc = subprocess.run(
        [python, "-m", "coverage", "json", "-o", "-"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
        timeout=40,
    )
    if proc.returncode != 0:
        return {"ok": False, "error": (proc.stderr or proc.stdout or "coverage json fehlgeschlagen")[-800:]}
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": "Coverage-Bericht ist kein JSON."}
    files = {}
    for path, info in data.get("files", {}).items():
        files[str(Path(path))] = {
            "executed": info.get("executed_lines", []),
            "missing": info.get("missing_lines", []),
        }
    return {"ok": True, "files": files, "percent": data.get("totals", {}).get("percent_covered")}
