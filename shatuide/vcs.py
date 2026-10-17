"""Git-Befehle für die Oberfläche. Es wird kein Shell-String zusammengebaut."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

_URL = re.compile(r"^(https://|http://|ssh://|git@)[\w.\-/:@~]+$")


def git_available() -> bool:
    return shutil.which("git") is not None


def run_git(cwd: Path, args: list[str], timeout: int = 30) -> dict:
    if not git_available():
        return {"ok": False, "error": "Git ist nicht installiert.", "stdout": "", "stderr": ""}
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Git-Befehl hat das Zeitlimit erreicht.", "stdout": "", "stderr": ""}
    except OSError as exc:
        return {"ok": False, "error": str(exc), "stdout": "", "stderr": ""}
    return {
        "ok": proc.returncode == 0,
        "code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "error": proc.stderr.strip() if proc.returncode else "",
    }


def status(cwd: Path) -> dict:
    result = run_git(cwd, ["status", "--porcelain=v1", "-b"])
    if not result.get("ok") and result.get("code") not in (0, None) and "not a git repository" in (result.get("stderr") or "").lower():
        return {**result, "branch": "", "entries": [], "repo": False}
    if not result.get("ok") and "not a git" in (result.get("stderr") or "").lower():
        return {**result, "branch": "", "entries": [], "repo": False}
    lines = (result.get("stdout") or "").splitlines()
    branch = ""
    entries = []
    for line in lines:
        if line.startswith("##"):
            branch = line[2:].strip()
            continue
        if len(line) < 4:
            continue
        entries.append({"code": line[:2], "path": line[3:]})
    return {**result, "branch": branch, "entries": entries, "repo": result.get("ok", False) or bool(branch)}


def diff(cwd: Path, path: str | None = None, staged: bool = False) -> dict:
    args = ["diff", "--"]
    if staged:
        args = ["diff", "--cached", "--"]
    if path:
        args.append(path)
    return run_git(cwd, args)


def log(cwd: Path, limit: int = 30) -> dict:
    return run_git(cwd, ["log", f"-n{limit}", "--pretty=format:%h%x09%an%x09%ad%x09%s", "--date=short"])


def branches(cwd: Path) -> dict:
    return run_git(cwd, ["branch", "--list"])


def clone(url: str, dest: Path) -> dict:
    if not _URL.match(url) or ".." in url:
        return {"ok": False, "error": "Ungültige Git-URL."}
    dest.parent.mkdir(parents=True, exist_ok=True)
    return run_git(dest.parent, ["clone", "--", url, dest.name], timeout=120)


def conflicts(cwd: Path) -> list[str]:
    result = run_git(cwd, ["diff", "--name-only", "--diff-filter=U"])
    if not result.get("ok"):
        return []
    return [line for line in result.get("stdout", "").splitlines() if line.strip()]


def take_side(text: str, side: str) -> str:
    """Einfacher Konfliktauflöser: ours oder theirs."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    mode = "keep"
    for line in lines:
        if line.startswith("<<<<<<<"):
            mode = "ours"
            continue
        if line.startswith("=======") and mode in {"ours", "theirs"}:
            mode = "theirs"
            continue
        if line.startswith(">>>>>>>"):
            mode = "keep"
            continue
        if mode == "keep" or (side == "ours" and mode == "ours") or (side == "theirs" and mode == "theirs"):
            out.append(line)
    return "".join(out)
