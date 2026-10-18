"""SSH, Docker und WSL über die vorhandenen Kommandozeilen-Werkzeuge."""

from __future__ import annotations

import os
import re
import shutil
import subprocess

_HOST = re.compile(r"^[\w.\-]+@[\w.\-]+$")
_NAME = re.compile(r"^[A-Za-z0-9_.:/-]+$")


def _run(args: list[str], timeout: int = 30) -> dict:
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError:
        return {"ok": False, "error": f"Befehl nicht gefunden: {args[0]}", "stdout": "", "stderr": ""}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Zeitlimit erreicht.", "stdout": "", "stderr": ""}
    return {
        "ok": proc.returncode == 0,
        "code": proc.returncode,
        "stdout": proc.stdout[-20000:],
        "stderr": proc.stderr[-8000:],
        "error": proc.stderr.strip() if proc.returncode else "",
    }


def ssh_run(target: str, command: str, timeout: int = 40) -> dict:
    if not _HOST.match(target):
        return {"ok": False, "error": "Host im Format benutzer@rechner angeben."}
    if not command.strip():
        return {"ok": False, "error": "Befehl fehlt."}
    if not shutil.which("ssh"):
        return {"ok": False, "error": "ssh ist nicht installiert."}
    return _run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", target, command],
        timeout=timeout,
    )


def docker_ps() -> dict:
    if not shutil.which("docker"):
        return {"ok": False, "error": "Docker-CLI ist nicht installiert."}
    return _run(["docker", "ps", "-a", "--format", "{{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}"])


def docker_logs(container: str) -> dict:
    if not _NAME.match(container):
        return {"ok": False, "error": "Ungültiger Containername."}
    return _run(["docker", "logs", "--tail", "200", container], timeout=20)


def docker_exec(container: str, command: str) -> dict:
    if not _NAME.match(container):
        return {"ok": False, "error": "Ungültiger Containername."}
    if not command.strip():
        return {"ok": False, "error": "Befehl fehlt."}
    return _run(["docker", "exec", container, "sh", "-lc", command], timeout=60)


def wsl_run(command: str) -> dict:
    if os.name != "nt":
        return {"ok": False, "error": "WSL gibt es nur unter Windows."}
    if not command.strip():
        return {"ok": False, "error": "Befehl fehlt."}
    return _run(["wsl.exe", "-e", "bash", "-lc", command], timeout=60)
