"""Python, Linux-Shell und PowerShell erkennen, prüfen und starten."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from shatuide.runner import run_args

SHELL_SUFFIXES = {".sh", ".bash", ".ksh", ".zsh"}
POWERSHELL_SUFFIXES = {".ps1", ".psm1", ".psd1"}
PYTHON_SUFFIXES = {".py", ".pyw", ".pyi"}
SHELL_NAMES = {".bashrc", ".bash_profile", ".bash_login", ".profile", ".zshrc"}


def language_of(path: str) -> str:
    name = Path(path).name.lower()
    suffix = Path(path).suffix.lower()
    if suffix in PYTHON_SUFFIXES:
        return "python"
    if suffix in SHELL_SUFFIXES or name in SHELL_NAMES:
        return "shell"
    if suffix in POWERSHELL_SUFFIXES:
        return "powershell"
    if suffix in {".bat", ".cmd"}:
        return "batch"
    return "text"


def shell_binary() -> str | None:
    for name in ("bash", "sh"):
        found = shutil.which(name)
        if found:
            return found
    return None


def powershell_binary() -> str | None:
    for name in ("pwsh", "powershell", "powershell.exe"):
        found = shutil.which(name)
        if found:
            return found
    if os.name == "nt":
        root = os.environ.get("SystemRoot", r"C:\Windows")
        system = Path(root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        if system.is_file():
            return str(system)
    return None


def run_argv(path: str, python: str, args: list[str] | None = None) -> list[str]:
    extra = [str(item) for item in (args or [])]
    lang = language_of(path)
    if lang == "shell":
        binary = shell_binary()
        if not binary:
            raise RuntimeError("Keine Linux-Shell gefunden (bash oder sh).")
        return [binary, path, *extra]
    if lang == "powershell":
        binary = powershell_binary()
        if not binary:
            raise RuntimeError("PowerShell nicht gefunden (pwsh oder powershell).")
        return [binary, "-NoProfile", "-File", path, *extra]
    if lang == "batch":
        if os.name != "nt":
            raise RuntimeError("Windows-Batch läuft nur unter Windows (cmd.exe).")
        return ["cmd.exe", "/c", path, *extra]
    return run_args(python, path, extra)


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def syntax_check(path: str, content: str | None = None) -> dict:
    lang = language_of(path)
    if lang == "shell":
        binary = shell_binary()
        if not binary:
            return {"ok": False, "error": "Keine Linux-Shell gefunden (bash oder sh)."}
        if content is None:
            proc = subprocess.run([binary, "-n", path], capture_output=True, text=True)
        else:
            proc = subprocess.run([binary, "-n"], input=content, capture_output=True, text=True)
        if proc.returncode == 0:
            return {"ok": True, "message": "Shell-Syntax in Ordnung."}
        return {"ok": False, "error": (proc.stderr or proc.stdout or "Syntaxfehler").strip()}
    if lang == "powershell":
        binary = powershell_binary()
        if not binary:
            return {"ok": False, "error": "PowerShell nicht gefunden (pwsh oder powershell)."}
        if content is None:
            command = (
                "$e=$null; $t=$null; "
                f"[void][System.Management.Automation.Language.Parser]::ParseFile({_ps_quote(path)}, [ref]$t, [ref]$e); "
                "if ($e) { $e | ForEach-Object { $_.ToString() }; exit 1 }"
            )
            proc = subprocess.run([binary, "-NoProfile", "-Command", command], capture_output=True, text=True)
        else:
            command = (
                "$s = [Console]::In.ReadToEnd(); $e=$null; $t=$null; "
                "[void][System.Management.Automation.Language.Parser]::ParseInput($s, [ref]$t, [ref]$e); "
                "if ($e) { $e | ForEach-Object { $_.ToString() }; exit 1 }"
            )
            proc = subprocess.run(
                [binary, "-NoProfile", "-Command", command],
                input=content,
                capture_output=True,
                text=True,
            )
        if proc.returncode == 0:
            return {"ok": True, "message": "PowerShell-Syntax in Ordnung."}
        return {"ok": False, "error": (proc.stdout or proc.stderr or "Syntaxfehler").strip()}
    if lang == "batch":
        return {"ok": False, "error": "Für Batch-Dateien gibt es keine Syntaxprüfung. Unter Windows startet cmd.exe die Datei."}
    source = content
    if source is None:
        try:
            source = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
    try:
        compile(source, path or "<memory>", "exec")
    except SyntaxError as exc:
        return {"ok": False, "error": f"Zeile {exc.lineno}: {exc.msg}"}
    return {"ok": True, "message": "Syntax in Ordnung."}


def selection_suffix(path: str) -> str:
    lang = language_of(path) if path else "python"
    return {"shell": ".sh", "powershell": ".ps1", "batch": ".bat"}.get(lang, ".py")
