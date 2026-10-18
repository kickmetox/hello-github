"""Python, Linux-Shell und PowerShell erkennen, prüfen und starten."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from shatuide.faults import locate_fault
from shatuide.runner import run_args

SHELL_SUFFIXES = {".sh", ".bash", ".ksh", ".zsh"}
POWERSHELL_SUFFIXES = {".ps1", ".psm1", ".psd1"}
PYTHON_SUFFIXES = {".py", ".pyw", ".pyi"}
JSON_SUFFIXES = {".json", ".jsonc"}
HTML_SUFFIXES = {".html", ".htm", ".xhtml"}
SHELL_NAMES = {".bashrc", ".bash_profile", ".bash_login", ".profile", ".zshrc"}
_HTML_VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr",
}
_HTML_OPTIONAL = {"html", "head", "body", "p", "li", "dt", "dd", "tr", "td", "th", "thead", "tbody", "tfoot", "option", "colgroup", "caption", "rt", "rp"}
_HTML_RAW = {"script", "style", "pre", "textarea"}
_HTML_HEADING = {"h1", "h2", "h3", "h4", "h5", "h6"}


def language_of(path: str) -> str:
    name = Path(path).name.lower()
    suffix = Path(path).suffix.lower()
    if suffix in PYTHON_SUFFIXES:
        return "python"
    if suffix in SHELL_SUFFIXES or name in SHELL_NAMES:
        return "shell"
    if suffix in JSON_SUFFIXES:
        return "json"
    if suffix in HTML_SUFFIXES:
        return "html"
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
    if lang == "html":
        raise RuntimeError("HTML-Dateien werden geprüft und formatiert, nicht ausgeführt.")
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
    if lang == "html":
        return _html_syntax(path, content)
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
        return _with_line(path, (proc.stderr or proc.stdout or "Syntaxfehler").strip())
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
        return _with_line(path, (proc.stdout or proc.stderr or "Syntaxfehler").strip())
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
        line = exc.lineno or 1
        return {"ok": False, "error": f"Zeile {line}: {exc.msg}", "line": line, "message": exc.msg or "Syntaxfehler"}
    return {"ok": True, "message": "Syntax in Ordnung."}


def _json_text(path: str, content: str | None) -> str:
    if content is not None:
        source = content
    else:
        source = Path(path).read_text(encoding="utf-8")
    if source.startswith("\ufeff"):
        source = source[1:]
    return source


def _with_line(path: str, text: str) -> dict:
    found = locate_fault(text, path)
    result = {"ok": False, "error": text}
    if found and found.get("line"):
        result["line"] = found["line"]
        result["message"] = found.get("message") or text
    return result


def _json_syntax(path: str, content: str | None) -> dict:
    try:
        source = _json_text(path, content)
        json.loads(source)
    except json.JSONDecodeError as exc:
        line = exc.lineno or 1
        return {"ok": False, "error": f"Zeile {line}, Spalte {exc.colno}: {exc.msg}", "line": line, "message": exc.msg}
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
    return {"shell": ".sh", "powershell": ".ps1", "batch": ".bat", "html": ".html", "json": ".json"}.get(lang, ".py")


_NEW_FILES = {
    "python": (".py", ""),
    "powershell": (".ps1", "Write-Output \"Hallo\"\n"),
    "shell": (".sh", "#!/bin/bash\necho Hallo\n"),
    "batch": (".bat", "@echo off\nsetlocal\necho Hallo\n"),
    "cmd": (".cmd", "@echo off\nsetlocal\necho Hallo\n"),
    "json": (".json", "{\n}\n"),
    "html": (
        ".html",
        "<!DOCTYPE html>\n<html lang=\"de\">\n<head>\n  <meta charset=\"utf-8\">\n  <title>Neu</title>\n</head>\n<body>\n</body>\n</html>\n",
    ),
    "text": (".txt", ""),
}


def plan_new_file(name: str, kind: str) -> dict:
    """Baut Pfad und Anfangstext für eine neue Datei. Die Art bestimmt die Endung."""
    key = (kind or "python").strip().lower()
    spec = _NEW_FILES.get(key)
    if not spec:
        return {"ok": False, "error": "Unbekannte Dateiart. Erlaubt sind Python, PowerShell, Shell, Batch, CMD, JSON, HTML und Text."}
    suffix, content = spec
    raw = (name or "").strip().strip("/\\").replace("\\", "/")
    if not raw:
        raw = "neu"
    if ":" in raw or raw.startswith("//") or any(part in {"", ".", ".."} for part in raw.split("/")):
        return {"ok": False, "error": "Name nur als Datei im Workspace, ohne Laufwerk."}
    current = Path(raw).suffix.lower()
    known = {item[0] for item in _NEW_FILES.values()}
    if current == suffix:
        path = raw
    elif current in known:
        path = str(Path(raw).with_suffix(suffix)).replace("\\", "/")
    elif current == "":
        path = raw + suffix
    else:
        path = raw
        content = ""
    return {"ok": True, "path": path, "content": content, "kind": key, "suffix": Path(path).suffix.lower()}


def _html_syntax(path: str, content: str | None) -> dict:
    try:
        source = _json_text(path, content)
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    problems = html_problems(source)
    if problems:
        first = problems[0]
        return {"ok": False, "error": f"Zeile {first['line']}: {first['message']}", "line": first["line"], "message": first["message"]}
    return {"ok": True, "message": "HTML in Ordnung."}


def html_problems(source: str) -> list[dict]:
    tokens, error = _html_tokens(source)
    if error:
        return [error]
    return _html_structure(tokens, source)


def html_outline(source: str) -> list[dict]:
    tokens, error = _html_tokens(source)
    if error:
        return []
    return _html_items(tokens, source)


def html_fragment(source: str, line: int) -> str:
    tokens, error = _html_tokens(source)
    if error:
        return source
    best = ""
    stack: list[dict] = []
    for token in tokens:
        if token["kind"] == "start" and token["void"]:
            if best == "" and _line_at(source, token["start"]) == line:
                best = token["raw"]
            continue
        if token["kind"] == "start" and not token["void"]:
            stack.append(token)
            continue
        if token["kind"] != "end":
            continue
        while stack:
            start = stack.pop()
            if start["name"] != token["name"]:
                continue
            start_line = _line_at(source, start["start"])
            end_line = _line_at(source, max(start["start"], token["end"] - 1))
            if best == "" and start_line <= line <= end_line:
                best = source[start["start"]:token["end"]]
            break
    return best or source


def format_html(content: str) -> dict:
    source = content[1:] if content.startswith("\ufeff") else content
    if not source.strip():
        return {"ok": True, "content": source, "tool": "html"}
    problems = html_problems(source)
    if problems:
        first = problems[0]
        return {"ok": False, "error": f"Zeile {first['line']}: {first['message']}"}
    tokens, _error = _html_tokens(source)
    chunks: list[str] = []
    depth = 0

    def emit(text: str, level: int) -> None:
        chunks.append(("  " * level) + text.strip())

    for token in tokens:
        kind = token["kind"]
        if kind == "text":
            if token.get("raw_block"):
                body = token["text"]
                if not body.strip():
                    continue
                if "\n" in body:
                    chunks.append(body.strip("\n"))
                else:
                    emit(body, depth)
                continue
            collapsed = re.sub(r"\s+", " ", token["text"]).strip()
            if collapsed:
                emit(collapsed, depth)
            continue
        if kind == "end":
            depth = max(0, depth - 1)
            emit(token["raw"], depth)
            continue
        emit(token["raw"], depth)
        if kind == "start" and not token["void"]:
            depth += 1
    text = "\n".join(chunks)
    if text and not text.endswith("\n"):
        text += "\n"
    return {"ok": True, "content": text, "tool": "html"}


def _html_problem(source: str, index: int, message: str) -> dict:
    line = _line_at(source, index)
    col = index - source.rfind("\n", 0, index)
    return {
        "line": line,
        "col": col,
        "end_line": line,
        "end_col": col,
        "severity": "error",
        "message": message,
        "code": "HTML",
    }


def _html_gt(source: str, start: int) -> int:
    quote = ""
    i = start + 1
    while i < len(source):
        ch = source[i]
        if quote:
            if ch == quote:
                quote = ""
            elif ch == "\\":
                i += 1
            i += 1
            continue
        if ch in "\"'":
            quote = ch
        elif ch == ">":
            return i
        i += 1
    return -1


def _html_tag_start(source: str, index: int) -> bool:
    if source.startswith("<!--", index) or source.startswith("<!", index) or source.startswith("<?", index):
        return True
    nxt = index + 1
    if nxt < len(source) and source[nxt] == "/":
        nxt += 1
    return nxt < len(source) and source[nxt].isalpha()


def _html_tokens(source: str) -> tuple[list[dict], dict | None]:
    tokens: list[dict] = []
    i = 0
    length = len(source)
    while i < length:
        if source.startswith("<!--", i):
            end = source.find("-->", i + 4)
            if end < 0:
                return tokens, _html_problem(source, i, "Kommentar wird nicht geschlossen.")
            tokens.append({"kind": "comment", "start": i, "end": end + 3, "raw": source[i:end + 3]})
            i = end + 3
            continue
        if source[i] == "<" and _html_tag_start(source, i):
            end = _html_gt(source, i)
            if end < 0:
                return tokens, _html_problem(source, i, "Tag wird nicht geschlossen.")
            raw = source[i:end + 1]
            token = _html_tag(raw, i, end + 1)
            tokens.append(token)
            i = end + 1
            if token["kind"] == "start" and token["name"] in _HTML_RAW and not token["void"]:
                match = re.search(rf"</{re.escape(token['name'])}\s*>", source[i:], re.I)
                if match is None:
                    tokens.append({"kind": "text", "raw_block": True, "start": i, "end": length, "text": source[i:], "raw": source[i:]})
                    break
                stop = i + match.start()
                tokens.append({"kind": "text", "raw_block": True, "start": i, "end": stop, "text": source[i:stop], "raw": source[i:stop]})
                close_end = i + match.end()
                close_raw = source[stop:close_end]
                tokens.append(_html_tag(close_raw, stop, close_end))
                i = close_end
            continue
        nxt = source.find("<", i + 1)
        if nxt < 0:
            nxt = length
        if nxt > i:
            tokens.append({"kind": "text", "start": i, "end": nxt, "text": source[i:nxt], "raw": source[i:nxt]})
        i = nxt
    return tokens, None


def _html_tag(raw: str, start: int, end: int) -> dict:
    body = raw[1:-1].strip()
    if body.startswith("!") or body.startswith("?"):
        return {"kind": "doctype", "start": start, "end": end, "raw": raw, "name": "", "void": True}
    closing = body.startswith("/")
    if closing:
        body = body[1:].strip()
    self_closing = body.endswith("/")
    if self_closing:
        body = body[:-1].strip()
    name = re.match(r"[A-Za-z][\w:-]*", body)
    tag = name.group(0).lower() if name else ""
    void = closing or self_closing or tag in _HTML_VOID
    return {
        "kind": "end" if closing else "start",
        "start": start,
        "end": end,
        "raw": raw,
        "name": tag,
        "void": void if not closing else True,
        "attrs": body[name.end():] if name else body,
    }


def _html_attr(attrs: str, key: str) -> str:
    match = re.search(rf"""(?i)\b{re.escape(key)}\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""", attrs)
    if not match:
        return ""
    return next(group for group in match.groups() if group is not None)


def _html_structure(tokens: list[dict], source: str) -> list[dict]:
    problems: list[dict] = []
    stack: list[tuple[str, int]] = []
    for token in tokens:
        if token["kind"] == "start" and not token["void"]:
            _html_open(stack, token["name"])
            stack.append((token["name"], token["start"]))
            continue
        if token["kind"] != "end":
            continue
        name = token["name"]
        while stack and stack[-1][0] != name and stack[-1][0] in _HTML_OPTIONAL:
            stack.pop()
        if stack and stack[-1][0] == name:
            stack.pop()
            continue
        if any(item[0] == name for item in stack):
            while stack and stack[-1][0] != name:
                open_name, open_at = stack.pop()
                if open_name not in _HTML_OPTIONAL:
                    problems.append(_html_problem(source, token["start"], f"Ende </{name}>, offen ist <{open_name}>."))
                    break
            if stack and stack[-1][0] == name:
                stack.pop()
            continue
        problems.append(_html_problem(source, token["start"], f"Unerwartetes </{name}>."))
    for name, index in stack:
        if name not in _HTML_OPTIONAL:
            problems.append(_html_problem(source, index, f"<{name}> ist nicht geschlossen."))
    return problems


def _html_open(stack: list[tuple[str, int]], incoming: str) -> None:
    closes_p = _HTML_HEADING | {"p", "div", "ul", "ol", "table", "section", "article", "header", "footer", "nav", "main", "aside", "form", "blockquote", "pre", "hr"}
    while stack and stack[-1][0] in _HTML_OPTIONAL:
        top = stack[-1][0]
        if top == "p" and incoming in closes_p:
            stack.pop()
            continue
        if top == incoming and top in {"li", "dt", "dd", "option", "tr", "td", "th", "p"}:
            stack.pop()
            continue
        break


def _html_items(tokens: list[dict], source: str) -> list[dict]:
    items: list[dict] = []
    stack: list[tuple[str, int | None]] = []
    for index, token in enumerate(tokens):
        if token["kind"] == "text" and token.get("raw_block"):
            items.extend(_html_script_functions(source, token))
            continue
        if token["kind"] == "start" and token["void"]:
            _html_add_item(items, tokens, source, index)
            continue
        if token["kind"] == "start" and not token["void"]:
            item_index = _html_add_item(items, tokens, source, index)
            stack.append((token["name"], item_index))
            continue
        if token["kind"] != "end":
            continue
        while stack:
            name, item_index = stack.pop()
            if item_index is not None:
                items[item_index]["end_line"] = _line_at(source, token["start"])
            if name == token["name"]:
                break
    return items


def _html_add_item(items: list[dict], tokens: list[dict], source: str, index: int) -> int | None:
    token = tokens[index]
    name = token["name"]
    ident = _html_attr(token.get("attrs", ""), "id")
    heading = name in _HTML_HEADING
    if not ident and not heading:
        return None
    text = ""
    if heading and index + 1 < len(tokens) and tokens[index + 1]["kind"] == "text" and not tokens[index + 1].get("raw_block"):
        text = re.sub(r"\s+", " ", tokens[index + 1]["text"]).strip()
    label = name
    if ident:
        label += "#" + ident
    if heading and text:
        label += " " + text[:80]
    items.append(
        {
            "name": label,
            "kind": "heading" if heading else "element",
            "line": _line_at(source, token["start"]),
            "end_line": _line_at(source, token["start"]),
            "parent": "",
            "params": "",
        }
    )
    return len(items) - 1


def _html_script_functions(source: str, token: dict) -> list[dict]:
    text = token["text"]
    base = token["start"]
    found = []
    pattern = re.compile(r"(?m)^[ \t]*(?:async[ \t]+)?function[ \t]+([A-Za-z_$][\w$]*)")
    for match in pattern.finditer(text):
        line = _line_at(source, base + match.start())
        found.append(
            {
                "name": match.group(1),
                "kind": "function",
                "line": line,
                "end_line": line,
                "parent": "",
                "params": "",
            }
        )
    return found


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
