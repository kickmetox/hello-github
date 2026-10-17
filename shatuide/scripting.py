"""Python, Linux-Shell und PowerShell erkennen, prüfen und starten."""

from __future__ import annotations

import json
import os
import re
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
    candidates = [
        Path.home() / "pwsh" / "pwsh",
        Path.home() / "pwsh" / "pwsh.exe",
        Path("/opt/microsoft/powershell/7/pwsh"),
        Path("/usr/local/bin/pwsh"),
    ]
    if os.name == "nt":
        root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        candidates.append(root / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe")
        program = os.environ.get("ProgramFiles")
        if program:
            candidates.append(Path(program) / "PowerShell" / "7" / "pwsh.exe")
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
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


_PS_DECL = re.compile(r"(?im)^[ \t]*(function|filter|class)[ \t]+([A-Za-z_][\w-]*)")
_SH_DECL = re.compile(
    r"(?m)^[ \t]*(?:function[ \t]+([A-Za-z_][\w]*)(?:[ \t]*\(\))?|([A-Za-z_][\w]*)[ \t]*\(\))"
)
_SH_SKIP = {"if", "elif", "else", "while", "for", "until", "case", "select", "time", "coproc", "function"}
_BAT_LABEL = re.compile(r"(?m)^[ \t]*:([A-Za-z_][\w-]*)")
_PS_SKIP_VAR = {"true", "false", "null", "this", "_"}


def script_outline(source: str, path: str = "") -> list[dict]:
    lang = language_of(path or "")
    if lang == "powershell":
        return _powershell_outline(source)
    if lang == "shell":
        return _shell_outline(source)
    if lang == "batch":
        return _batch_outline(source)
    return []


def _line_at(source: str, index: int) -> int:
    return source.count("\n", 0, max(0, index)) + 1


def _brace_end(source: str, open_at: int) -> int:
    depth = 0
    i = open_at
    quote = ""
    while i < len(source):
        if quote:
            if source[i] == "\\":
                i += 2
                continue
            if source[i] == quote:
                quote = ""
            i += 1
            continue
        if source.startswith("<#", i):
            stop = source.find("#>", i + 2)
            i = len(source) if stop < 0 else stop + 2
            continue
        ch = source[i]
        if ch in "\"'":
            quote = ch
            i += 1
            continue
        if ch == "#":
            stop = source.find("\n", i)
            i = len(source) if stop < 0 else stop
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return _line_at(source, i)
        i += 1
    return _line_at(source, max(0, len(source) - 1))


def _span(source: str, start: int, end: int) -> tuple[int, int]:
    nxt = end
    brace = source.find("{", start, nxt if nxt > start else start)
    line = _line_at(source, start)
    if brace < 0:
        return line, line
    return line, _brace_end(source, brace)


def _ps_params(chunk: str) -> str:
    names: list[str] = []
    for name in re.findall(r"\$([A-Za-z_][\w]*)", chunk):
        if name.lower() in _PS_SKIP_VAR or name in names:
            continue
        names.append(name)
        if len(names) >= 12:
            break
    return ", ".join(names)


def _param_block(source: str, brace: int) -> str:
    if brace < 0 or brace >= len(source) or source[brace] != "{":
        return ""
    body = source[brace:brace + 700]
    found = re.search(r"(?is)\bparam\s*\(", body)
    if not found:
        return ""
    start = brace + found.end() - 1
    depth = 0
    i = start
    while i < len(source) and i < start + 800:
        if source[i] == "(":
            depth += 1
        elif source[i] == ")":
            depth -= 1
            if depth == 0:
                return _ps_params(source[start:i])
        i += 1
    return ""


def _powershell_outline(source: str) -> list[dict]:
    matches = list(_PS_DECL.finditer(source))
    items: list[dict] = []
    for index, match in enumerate(matches):
        window = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        line, end_line = _span(source, match.end(), window)
        kind_word = match.group(1).lower()
        kind = "class" if kind_word == "class" else ("filter" if kind_word == "filter" else "function")
        brace = source.find("{", match.end(), window)
        params = _ps_params(source[match.end(): brace if brace >= 0 else window])
        if not params:
            params = _param_block(source, brace)
        items.append(
            {
                "name": match.group(2),
                "kind": kind,
                "line": line,
                "end_line": end_line,
                "parent": "",
                "params": params,
            }
        )
    for item in items:
        if item["kind"] == "class":
            continue
        for cls in items:
            if cls["kind"] == "class" and cls["line"] < item["line"] <= cls["end_line"]:
                item["parent"] = cls["name"]
                break
    return items


def _shell_outline(source: str) -> list[dict]:
    matches = []
    for match in _SH_DECL.finditer(source):
        name = match.group(1) or match.group(2)
        if not name or name in _SH_SKIP:
            continue
        matches.append((match, name))
    items: list[dict] = []
    for index, (match, name) in enumerate(matches):
        window = matches[index + 1][0].start() if index + 1 < len(matches) else len(source)
        line, end_line = _span(source, match.end(), window)
        items.append(
            {
                "name": name,
                "kind": "function",
                "line": line,
                "end_line": end_line,
                "parent": "",
                "params": "",
            }
        )
    return items


def _batch_outline(source: str) -> list[dict]:
    items = []
    for match in _BAT_LABEL.finditer(source):
        line = _line_at(source, match.start())
        items.append(
            {
                "name": match.group(1),
                "kind": "label",
                "line": line,
                "end_line": line,
                "parent": "",
                "params": "",
            }
        )
    return items
