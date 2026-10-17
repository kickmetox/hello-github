"""Python, Linux-Shell und PowerShell erkennen, prüfen und starten."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from shatuide.runner import run_args

SHELL_SUFFIXES = {".sh", ".bash", ".ksh", ".zsh"}
POWERSHELL_SUFFIXES = {".ps1", ".psm1", ".psd1"}
PYTHON_SUFFIXES = {".py", ".pyw", ".pyi"}
JSON_SUFFIXES = {".json", ".jsonc"}
SHELL_NAMES = {".bashrc", ".bash_profile", ".bash_login", ".profile", ".zshrc"}


def language_of(path: str) -> str:
    name = Path(path).name.lower()
    suffix = Path(path).suffix.lower()
    if suffix in PYTHON_SUFFIXES:
        return "python"
    if suffix in SHELL_SUFFIXES or name in SHELL_NAMES:
        return "shell"
    if suffix in JSON_SUFFIXES:
        return "json"
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
    if lang == "json":
        raise RuntimeError("JSON-Dateien werden geprüft und formatiert, nicht ausgeführt.")
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
    if lang == "json":
        return _json_syntax(path, content)
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


def _json_text(path: str, content: str | None) -> str:
    if content is not None:
        source = content
    else:
        source = Path(path).read_text(encoding="utf-8")
    if source.startswith("\ufeff"):
        source = source[1:]
    return source


def _json_syntax(path: str, content: str | None) -> dict:
    try:
        source = _json_text(path, content)
        json.loads(source)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"Zeile {exc.lineno}, Spalte {exc.colno}: {exc.msg}"}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "message": "JSON in Ordnung."}


def json_problems(source: str) -> list[dict]:
    if not source.strip():
        return []
    try:
        json.loads(source[1:] if source.startswith("\ufeff") else source)
    except json.JSONDecodeError as exc:
        line = exc.lineno or 1
        return [
            {
                "line": line,
                "col": exc.colno or 1,
                "end_line": line,
                "end_col": exc.colno or 1,
                "severity": "error",
                "message": exc.msg,
                "code": "JSON",
            }
        ]
    return []


def json_outline(source: str) -> list[dict]:
    try:
        data = json.loads(source[1:] if source.startswith("\ufeff") else source)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    items = []
    for key in data:
        needle = json.dumps(key, ensure_ascii=False)
        pos = source.find(needle)
        line = source.count("\n", 0, pos) + 1 if pos >= 0 else 1
        items.append({"name": str(key), "kind": "key", "line": line, "end_line": line, "parent": ""})
    return items


def format_json(content: str) -> dict:
    try:
        data = json.loads(content[1:] if content.startswith("\ufeff") else content)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"Zeile {exc.lineno}, Spalte {exc.colno}: {exc.msg}"}
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if not text.endswith("\n"):
        text += "\n"
    return {"ok": True, "content": text, "tool": "json"}


def selection_suffix(path: str) -> str:
    lang = language_of(path) if path else "python"
    return {"shell": ".sh", "powershell": ".ps1", "batch": ".bat"}.get(lang, ".py")
