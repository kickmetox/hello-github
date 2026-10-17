"""EXE, MSI, PowerShell-Modul, GUI, Dienst, Messung, Hilfe und Wiederherstellung."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from shatuide.paths import inside
from shatuide.scripting import language_of, powershell_binary, shell_binary

_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,48}$")
_VERSION = re.compile(r"^\d+\.\d+\.\d+(\.\d+)?$")
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PS_NAME = re.compile(r"^[A-Za-z_][\w-]*$")
_HOST = re.compile(r"^[A-Za-z0-9._-]{1,200}$")
_USER = re.compile(r"^[A-Za-z0-9_.\\-]{1,80}$")
_TOPIC = re.compile(r"^[A-Za-z0-9_.*?-]{1,80}$")

PS_TYPES = {
    "string": "[string]",
    "int": "[int]",
    "long": "[long]",
    "bool": "[bool]",
    "switch": "[switch]",
    "double": "[double]",
    "object": "[object]",
    "datetime": "[datetime]",
}

_POSIX_C = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static const unsigned char SCRIPT[] = {
__BYTES__
};
static const unsigned int SCRIPT_LEN = __LEN__;
static const char *KIND = "__KIND__";
static const char *SUFFIX = "__SUFFIX__";

static void fail(const char *msg) {
    fprintf(stderr, "%s\n", msg);
    exit(127);
}

int main(int argc, char **argv) {
    char path[] = "/tmp/shatuXXXXXX";
    char named[4096];
    int fd = mkstemp(path);
    unsigned int off = 0;
    if (fd < 0) fail("Temporäre Datei fehlgeschlagen");
    while (off < SCRIPT_LEN) {
        ssize_t wrote = write(fd, SCRIPT + off, SCRIPT_LEN - off);
        if (wrote < 0) fail("Schreiben fehlgeschlagen");
        off += (unsigned int)wrote;
    }
    close(fd);
    chmod(path, 0700);
    if (snprintf(named, sizeof named, "%s%s", path, SUFFIX) >= (int)sizeof named) fail("Pfad zu lang");
    if (rename(path, named) != 0) {
        strncpy(named, path, sizeof named - 1);
        named[sizeof named - 1] = 0;
    }
    {
        char *args[64];
        int i = 0;
        int extra;
        const char *bin = "bash";
        if (strcmp(KIND, "python") == 0) bin = "python3";
        else if (strcmp(KIND, "powershell") == 0) bin = "pwsh";
        else if (strcmp(KIND, "batch") == 0) fail("Batch läuft nur unter Windows.");
        args[i++] = (char *)bin;
        if (strcmp(KIND, "powershell") == 0) {
            args[i++] = "-NoProfile";
            args[i++] = "-File";
        }
        args[i++] = named;
        extra = argc - 1;
        if (extra > 48) extra = 48;
        for (int a = 0; a < extra; a++) args[i++] = argv[a + 1];
        args[i] = NULL;
        execvp(bin, args);
        if (strcmp(KIND, "powershell") == 0) {
            args[0] = "powershell";
            execvp("powershell", args);
        }
        if (strcmp(KIND, "shell") == 0) {
            args[0] = "sh";
            execvp("sh", args);
        }
        if (strcmp(KIND, "python") == 0) {
            args[0] = "python";
            execvp("python", args);
        }
        perror(bin);
    }
    return 127;
}
"""

_WIN_C = r"""
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>

static const unsigned char SCRIPT[] = {
__BYTES__
};
static const unsigned int SCRIPT_LEN = __LEN__;
static const char *KIND = "__KIND__";
static const char *SUFFIX = "__SUFFIX__";

static void fail(const char *msg) {
#ifdef WINDOWED
    MessageBoxA(NULL, msg, "Shatu", MB_ICONERROR);
#else
    fprintf(stderr, "%s\n", msg);
#endif
    ExitProcess(127);
}

static int exists(const char *path) {
    DWORD attr = GetFileAttributesA(path);
    return attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY);
}

static const char *interpreter(char *storage) {
    char found[MAX_PATH];
    if (strcmp(KIND, "python") == 0) {
        if (SearchPathA(NULL, "python.exe", NULL, MAX_PATH, found, NULL)) {
            strncpy(storage, found, MAX_PATH - 1);
            return storage;
        }
        if (SearchPathA(NULL, "py.exe", NULL, MAX_PATH, found, NULL)) {
            strncpy(storage, found, MAX_PATH - 1);
            return storage;
        }
        return NULL;
    }
    if (strcmp(KIND, "shell") == 0) {
        if (SearchPathA(NULL, "bash.exe", NULL, MAX_PATH, found, NULL)) {
            strncpy(storage, found, MAX_PATH - 1);
            return storage;
        }
        return NULL;
    }
    if (strcmp(KIND, "batch") == 0) {
        const char *root = getenv("SystemRoot");
        if (!root) root = "C:\\Windows";
        snprintf(storage, MAX_PATH, "%s\\System32\\cmd.exe", root);
        return storage;
    }
    if (SearchPathA(NULL, "pwsh.exe", NULL, MAX_PATH, found, NULL)) {
        strncpy(storage, found, MAX_PATH - 1);
        return storage;
    }
    {
        const char *pf = getenv("ProgramFiles");
        if (pf) {
            snprintf(storage, MAX_PATH, "%s\\PowerShell\\7\\pwsh.exe", pf);
            if (exists(storage)) return storage;
        }
    }
    if (SearchPathA(NULL, "powershell.exe", NULL, MAX_PATH, found, NULL)) {
        strncpy(storage, found, MAX_PATH - 1);
        return storage;
    }
    {
        const char *root = getenv("SystemRoot");
        if (!root) root = "C:\\Windows";
        snprintf(storage, MAX_PATH, "%s\\System32\\WindowsPowerShell\\v1.0\\powershell.exe", root);
        if (exists(storage)) return storage;
    }
    return NULL;
}

static int run(void) {
    char dir[MAX_PATH];
    char path[MAX_PATH];
    char named[MAX_PATH];
    char exe[MAX_PATH];
    char cmdline[32768];
    const char *binary;
    HANDLE file;
    DWORD written = 0;
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    DWORD code = 1;
    if (!GetTempPathA(MAX_PATH, dir)) fail("Temp-Ordner fehlt");
    if (!GetTempFileNameA(dir, "shu", 0, path)) fail("Temporäre Datei fehlgeschlagen");
    snprintf(named, MAX_PATH, "%s%s", path, SUFFIX);
    DeleteFileA(named);
    if (!MoveFileA(path, named)) fail("Umbenennen fehlgeschlagen");
    file = CreateFileA(named, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) fail("Schreiben fehlgeschlagen");
    if (SCRIPT_LEN && !WriteFile(file, SCRIPT, SCRIPT_LEN, &written, NULL)) {
        CloseHandle(file);
        fail("Schreiben fehlgeschlagen");
    }
    CloseHandle(file);
    binary = interpreter(exe);
    if (!binary) fail("Interpreter nicht gefunden.");
    if (strcmp(KIND, "powershell") == 0)
        snprintf(cmdline, sizeof cmdline, "\"%s\" -NoProfile -ExecutionPolicy Bypass -File \"%s\"", binary, named);
    else if (strcmp(KIND, "batch") == 0)
        snprintf(cmdline, sizeof cmdline, "\"%s\" /c \"%s\"", binary, named);
    else
        snprintf(cmdline, sizeof cmdline, "\"%s\" \"%s\"", binary, named);
    ZeroMemory(&si, sizeof si);
    si.cb = sizeof si;
    ZeroMemory(&pi, sizeof pi);
    if (!CreateProcessA(NULL, cmdline, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) {
        DeleteFileA(named);
        fail("Start fehlgeschlagen");
    }
    WaitForSingleObject(pi.hProcess, INFINITE);
    GetExitCodeProcess(pi.hProcess, &code);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    DeleteFileA(named);
    return (int)code;
}

#ifdef WINDOWED
int WINAPI WinMain(HINSTANCE inst, HINSTANCE prev, LPSTR cmd, int show) {
    (void)inst; (void)prev; (void)cmd; (void)show;
    return run();
}
#else
int main(void) {
    return run();
}
#endif
"""


def safe_name(value: str, fallback: str = "ShatuApp") -> str:
    text = (value or "").strip() or fallback
    if not _NAME.match(text):
        raise ValueError("Name: Buchstabe, danach Ziffern, Unterstrich oder Bindestrich, höchstens 49 Zeichen.")
    return text


def safe_version(value: str) -> str:
    text = (value or "1.0.0").strip() or "1.0.0"
    if not _VERSION.match(text):
        raise ValueError("Version im Format 1.0.0 oder 1.0.0.0 angeben.")
    return text


def output_dir(workspace: Path) -> Path:
    path = Path(workspace) / "ausgabe"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ps_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def encode_powershell(script: str) -> str:
    return base64.b64encode(script.encode("utf-16le")).decode("ascii")


def binary_bits(path: str) -> int:
    low = path.replace("\\", "/").lower()
    if "syswow64" in low:
        return 32
    if "/system32/" in low or low.endswith("/system32"):
        return 64
    try:
        data = Path(path).read_bytes()[:64]
    except OSError:
        return 0
    if data[:4] == b"\x7fELF" and len(data) > 4:
        return 32 if data[4] == 1 else 64 if data[4] == 2 else 0
    if data[:2] == b"MZ" and len(data) > 0x40:
        offset = int.from_bytes(data[0x3C:0x40], "little")
        try:
            blob = Path(path).read_bytes()[offset:offset + 6]
        except OSError:
            return 64
        if blob[:4] == b"PE\x00\x00":
            machine = int.from_bytes(blob[4:6], "little")
            if machine == 0x14C:
                return 32
            if machine in {0x8664, 0xAA64}:
                return 64
        return 64
    return 0


def powershell_hosts() -> list[dict]:
    hosts: list[dict] = []
    seen: set[str] = set()

    def add(path: str, edition: str) -> None:
        if not path:
            return
        candidate = Path(path)
        if not candidate.is_file():
            return
        resolved = str(candidate.resolve())
        if resolved in seen or not os.access(resolved, os.X_OK):
            return
        seen.add(resolved)
        bits = binary_bits(resolved)
        hosts.append({
            "path": resolved,
            "edition": edition,
            "bits": bits,
            "kind": "powershell",
            "label": f"{edition}, {bits}-bit" if bits else edition,
        })

    binary = powershell_binary()
    if binary:
        edition = "PowerShell 7" if Path(binary).name.lower().startswith("pwsh") else "Windows PowerShell"
        add(binary, edition)
    if os.name == "nt":
        root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        add(str(root / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"), "Windows PowerShell")
        add(str(root / "SysWOW64" / "WindowsPowerShell" / "v1.0" / "powershell.exe"), "Windows PowerShell")
        for env_name, edition in (("ProgramFiles", "PowerShell 7"), ("ProgramFiles(x86)", "PowerShell 7")):
            base = os.environ.get(env_name)
            if base:
                add(str(Path(base) / "PowerShell" / "7" / "pwsh.exe"), edition)
    return hosts


def local_shells() -> list[dict]:
    shells = list(powershell_hosts())
    seen = {item["path"] for item in shells}
    for name in ("bash", "sh"):
        found = shutil.which(name)
        if not found:
            continue
        resolved = str(Path(found).resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        bits = binary_bits(resolved)
        shells.append({
            "path": resolved,
            "edition": Path(resolved).name,
            "bits": bits,
            "kind": "shell",
            "label": f"{Path(resolved).name}, {bits}-bit" if bits else Path(resolved).name,
        })
    return shells


def match_shell(requested: str) -> str:
    if not requested:
        return ""
    try:
        wanted = str(Path(requested).resolve())
    except OSError:
        return ""
    for item in local_shells():
        if item["path"] == wanted:
            return item["path"]
    return ""


def _count_braces(line: str, powershell: bool) -> tuple[int, int]:
    opens = closes = 0
    quote = ""
    escape = "`" if powershell else "\\"
    i = 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == escape and i + 1 < len(line):
                i += 2
                continue
            if ch == quote:
                quote = ""
            i += 1
            continue
        if ch in {"'", '"'}:
            quote = ch
            i += 1
            continue
        if ch == "#":
            break
        if ch == "{":
            opens += 1
        elif ch == "}":
            closes += 1
        i += 1
    return opens, closes


def _format_indent(source: str, powershell: bool, shell: bool) -> str:
    lines = source.replace("\t", "    ").splitlines()
    depth = 0
    raw_end = None
    block = False
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if raw_end:
            out.append(line.rstrip())
            if stripped == raw_end:
                raw_end = None
            continue
        if block:
            out.append(line.rstrip())
            if "#>" in stripped:
                block = False
            continue
        if stripped.startswith("<#"):
            out.append("    " * depth + stripped)
            if "#>" not in stripped:
                block = True
            continue
        if stripped.startswith("@'") or stripped.startswith('@"'):
            out.append("    " * depth + stripped)
            mark = "'@" if stripped.startswith("@'") else '"@'
            if mark not in stripped:
                raw_end = mark
            continue
        leading = 0
        while leading < len(stripped) and stripped[leading] == "}":
            leading += 1
        keyword_dedent = 0
        keyword_open = 0
        if shell and stripped:
            first = stripped.split()[0]
            if first in {"fi", "done", "esac"}:
                keyword_dedent = 1
            if re.search(r"\bthen\b", stripped) and not re.search(r"\bfi\b", stripped):
                keyword_open += 1
            if re.search(r"\bdo\b", stripped) and not re.search(r"\bdone\b", stripped):
                keyword_open += 1
            if first == "case" and "esac" not in stripped.split():
                keyword_open += 1
        opens, closes = _count_braces(stripped, powershell)
        indent = max(0, depth - leading - keyword_dedent)
        out.append(("    " * indent + stripped) if stripped else "")
        depth = max(0, depth + opens + keyword_open - closes - keyword_dedent)
    text = "\n".join(out)
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def format_script(language: str, source: str) -> dict:
    if language == "powershell":
        return {"ok": True, "content": _format_indent(source, True, False), "tool": "shatu"}
    if language == "shell":
        return {"ok": True, "content": _format_indent(source, False, True), "tool": "shatu"}
    if language == "batch":
        lines = [line.rstrip() for line in source.replace("\t", "    ").splitlines()]
        text = "\n".join(lines)
        if text and not text.endswith("\n"):
            text += "\n"
        return {"ok": True, "content": text, "tool": "shatu"}
    return {"ok": False, "error": "Für diese Datei gibt es keine Skriptformatierung."}


def advanced_function(spec: dict) -> str:
    name = str(spec.get("name") or "").strip()
    if not _PS_NAME.match(name):
        raise ValueError("Funktionsname fehlt oder enthält ungültige Zeichen.")
    synopsis = str(spec.get("synopsis") or "").strip().replace("\n", " ")
    description = str(spec.get("description") or "").strip().replace("\n", " ")
    output = str(spec.get("output") or "").strip().lower()
    parameters = spec.get("parameters") or []
    if not isinstance(parameters, list):
        raise ValueError("Parameter müssen eine Liste sein.")
    lines = [
        "<#",
        f".SYNOPSIS",
        f"    {synopsis or name}",
        ".DESCRIPTION",
        f"    {description or synopsis or name}",
    ]
    rendered: list[str] = []
    for index, item in enumerate(parameters):
        if not isinstance(item, dict):
            raise ValueError("Parameter ist kein Objekt.")
        param = str(item.get("name") or "").strip()
        if not _IDENT.match(param):
            raise ValueError(f"Parametername ungültig: {param or '(leer)'}")
        kind = str(item.get("type") or "string").strip().lower()
        if kind not in PS_TYPES:
            raise ValueError(f"Unbekannter Typ: {kind}")
        mandatory = item.get("mandatory")
        if isinstance(mandatory, str):
            mandatory = mandatory.strip().lower() in {"1", "ja", "yes", "true", "pflicht"}
        help_text = str(item.get("help") or "").strip().replace("\n", " ")
        lines.extend([".PARAMETER " + param, f"    {help_text or param}"])
        flag = "$true" if mandatory else "$false"
        rendered.append(f"        [Parameter(Mandatory = {flag}, Position = {index})]")
        rendered.append(f"        {PS_TYPES[kind]}${param}")
    if output in PS_TYPES:
        lines.extend([".OUTPUTS", f"    {output}"])
    lines.append("#>")
    lines.append(f"function {name} {{")
    lines.append("    [CmdletBinding()]")
    if output in PS_TYPES:
        lines.append(f"    [OutputType({PS_TYPES[output]})]")
    lines.append("    param(")
    if rendered:
        lines.append(",\n".join(_chunk_params(rendered)))
    lines.append("    )")
    lines.append("    process {")
    lines.append("        # Implementierung")
    lines.append("    }")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def _chunk_params(rendered: list[str]) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for line in rendered:
        current.append(line)
        if line.strip().startswith("[") and "$" in line:
            blocks.append("\n".join(current))
            current = []
    if current:
        blocks.append("\n".join(current))
    return blocks


def _match_brace(source: str, open_at: int) -> int:
    depth = 0
    quote = ""
    i = open_at
    while i < len(source):
        if quote:
            if source[i] == "`" and i + 1 < len(source):
                i += 2
                continue
            if source[i] == quote:
                quote = ""
            i += 1
            continue
        if source.startswith("@'", i) or source.startswith('@"', i):
            mark = "'@" if source[i + 1] == "'" else '"@'
            end = source.find(mark, i + 2)
            i = len(source) if end < 0 else end + 2
            continue
        if source.startswith("<#", i):
            end = source.find("#>", i + 2)
            i = len(source) if end < 0 else end + 2
            continue
        ch = source[i]
        if ch == "#":
            end = source.find("\n", i)
            i = len(source) if end < 0 else end
            continue
        if ch in {"'", '"'}:
            quote = ch
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(source)


def _help_start(source: str, index: int) -> int:
    cursor = index
    while cursor > 0:
        line_start = source.rfind("\n", 0, cursor - 1) + 1
        line = source[line_start:cursor].strip()
        if line == "":
            cursor = line_start
            continue
        if line.endswith("#>"):
            block = source.rfind("<#", 0, line_start + 1)
            return block if block >= 0 else index
        return index
    return index


def extract_functions(source: str) -> list[dict]:
    found: list[dict] = []
    for match in re.finditer(r"(?m)^function[ \t]+([A-Za-z_][\w-]*)\b", source):
        name = match.group(1)
        brace = source.find("{", match.end())
        if brace < 0:
            continue
        end = _match_brace(source, brace)
        start = _help_start(source, match.start())
        code = source[start:end].strip() + "\n"
        synopsis = ""
        summary = re.search(r"(?im)\.SYNOPSIS\s+(.+)", code)
        if summary:
            synopsis = summary.group(1).strip()
        found.append({"name": name, "synopsis": synopsis, "code": code})
    return found


def functions_from_help(source: str) -> list[dict]:
    found: list[dict] = []
    for match in re.finditer(r"(?s)<#(.*?)#>", source):
        block = match.group(1)
        if not re.search(r"(?im)\.SYNOPSIS\b", block):
            continue
        name_match = re.search(r"(?im)^\s*\.(?:NAME|FUNCTION)\s+([A-Za-z_][\w-]*)", block)
        if not name_match:
            continue
        name = name_match.group(1)
        synopsis = ""
        summary = re.search(r"(?im)\.SYNOPSIS\s+(.+)", block)
        if summary:
            synopsis = summary.group(1).strip()
        code = (
            "<#\n"
            + block.strip()
            + "\n#>\n"
            + f"function {name} {{\n    [CmdletBinding()]\n    param()\n    process {{\n        # Aus der Hilfe erzeugt\n    }}\n}}\n"
        )
        found.append({"name": name, "synopsis": synopsis, "code": code})
    return found


def build_module(source: str, name: str, version: str = "1.0.0", author: str = "ShatuIDE", description: str = "") -> dict:
    module = safe_name(name, "Modul")
    ver = safe_version(version)
    functions = extract_functions(source) or functions_from_help(source)
    if not functions:
        return {"ok": False, "error": "Keine Funktion und keine Kommentarhilfe mit .NAME gefunden."}
    psm1 = "\n".join(item["code"].rstrip() + "\n" for item in functions)
    names = ", ".join("'" + item["name"].replace("'", "''") + "'" for item in functions)
    summary = description.strip() or next((item["synopsis"] for item in functions if item["synopsis"]), module)
    guid = str(uuid.uuid5(uuid.NAMESPACE_URL, "shatuide-module:" + module)).upper()
    psd1 = (
        "@{\n"
        f"    RootModule = '{module}.psm1'\n"
        f"    ModuleVersion = '{ver}'\n"
        f"    GUID = '{guid}'\n"
        f"    Author = {_ps_literal(author.strip() or 'ShatuIDE')}\n"
        f"    Description = {_ps_literal(summary)}\n"
        f"    FunctionsToExport = @({names})\n"
        "    CmdletsToExport = @()\n"
        "    VariablesToExport = @()\n"
        "    AliasesToExport = @()\n"
        "    PowerShellVersion = '5.1'\n"
        "}\n"
    )
    return {
        "ok": True,
        "name": module,
        "psm1": psm1,
        "psd1": psd1,
        "functions": [item["name"] for item in functions],
    }


def gui_script(title: str, controls: list, language: str) -> dict:
    if not isinstance(controls, list) or not controls:
        return {"ok": False, "error": "Mindestens ein Steuerelement anlegen."}
    heading = str(title or "Werkzeug").replace("\n", " ")[:80]
    language = language if language in {"powershell", "python"} else "powershell"
    names: set[str] = set()
    cleaned: list[dict] = []
    kinds = {"label": "Label", "button": "Button", "textbox": "TextBox", "checkbox": "CheckBox", "combo": "ComboBox"}
    for item in controls:
        if not isinstance(item, dict):
            return {"ok": False, "error": "Steuerelement ist ungültig."}
        kind = str(item.get("kind") or "")
        if kind not in kinds:
            return {"ok": False, "error": "Unbekanntes Steuerelement."}
        name = str(item.get("name") or "")
        if not _IDENT.match(name) or name in names:
            return {"ok": False, "error": f"Name der Steuerung ungültig oder doppelt: {name or '(leer)'}"}
        names.add(name)

        def clamp(key: str, default: int) -> int:
            try:
                number = int(item.get(key, default))
            except (TypeError, ValueError):
                number = default
            return max(0, min(number, 4000))

        text = str(item.get("text") or kind)[:200]
        items = item.get("items") if isinstance(item.get("items"), list) else []
        cleaned.append({
            "kind": kind,
            "win": kinds[kind],
            "name": name,
            "text": text,
            "x": clamp("x", 12),
            "y": clamp("y", 12),
            "w": max(20, clamp("w", 140)),
            "h": max(16, clamp("h", 28)),
            "items": [str(entry)[:80] for entry in items[:20]],
        })
    if language == "python":
        return {"ok": True, "language": "python", "suffix": ".py", "content": _gui_python(heading, cleaned)}
    return {"ok": True, "language": "powershell", "suffix": ".ps1", "content": _gui_powershell(heading, cleaned)}


def _gui_powershell(title: str, controls: list[dict]) -> str:
    lines = [
        "# Erzeugt von ShatuIDE. Das Formular bleibt eine normale PowerShell-Datei.",
        "Add-Type -AssemblyName System.Windows.Forms",
        "Add-Type -AssemblyName System.Drawing",
        "$form = New-Object System.Windows.Forms.Form",
        f"$form.Text = {_ps_literal(title)}",
        "$form.ClientSize = New-Object System.Drawing.Size(640, 400)",
        "$form.StartPosition = 'CenterScreen'",
        "",
    ]
    for item in controls:
        var = "$" + item["name"]
        lines.append(f"{var} = New-Object System.Windows.Forms.{item['win']}")
        lines.append(f"{var}.Name = {_ps_literal(item['name'])}")
        lines.append(f"{var}.Text = {_ps_literal(item['text'])}")
        lines.append(f"{var}.Location = New-Object System.Drawing.Point({item['x']}, {item['y']})")
        lines.append(f"{var}.Size = New-Object System.Drawing.Size({item['w']}, {item['h']})")
        if item["kind"] == "combo":
            for entry in item["items"] or [item["text"]]:
                lines.append(f"[void]{var}.Items.Add({_ps_literal(entry)})")
        if item["kind"] == "button":
            lines.append(f"{var}.Add_Click({{")
            lines.append("    # Aktion")
            lines.append("})")
        lines.append(f"$form.Controls.Add({var})")
        lines.append("")
    lines.append("[void]$form.ShowDialog()")
    lines.append("")
    return "\n".join(lines)


def _gui_python(title: str, controls: list[dict]) -> str:
    lines = [
        "# Erzeugt von ShatuIDE.",
        "import tkinter as tk",
        "",
        "root = tk.Tk()",
        f"root.title({title!r})",
        'root.geometry("640x400")',
        "",
    ]
    widgets = {"label": "Label", "button": "Button", "textbox": "Entry", "checkbox": "Checkbutton", "combo": "OptionMenu"}
    for item in controls:
        if item["kind"] == "combo":
            entries = item["items"] or [item["text"]]
            lines.append(f"{item['name']}_var = tk.StringVar(value={entries[0]!r})")
            lines.append(f"{item['name']} = tk.OptionMenu(root, {item['name']}_var, {', '.join(repr(entry) for entry in entries)})")
        elif item["kind"] == "checkbox":
            lines.append(f"{item['name']}_var = tk.IntVar()")
            lines.append(f"{item['name']} = tk.Checkbutton(root, text={item['text']!r}, variable={item['name']}_var)")
        elif item["kind"] == "button":
            lines.append(f"def {item['name']}_click():")
            lines.append("    pass  # Aktion")
            lines.append("")
            lines.append(f"{item['name']} = tk.Button(root, text={item['text']!r}, command={item['name']}_click)")
        else:
            lines.append(f"{item['name']} = tk.{widgets[item['kind']]}(root, text={item['text']!r})" if item["kind"] == "label" else f"{item['name']} = tk.{widgets[item['kind']]}(root)")
            if item["kind"] == "textbox":
                lines.append(f"{item['name']}.insert(0, {item['text']!r})")
        lines.append(f"{item['name']}.place(x={item['x']}, y={item['y']}, width={item['w']}, height={item['h']})")
        lines.append("")
    lines.append("root.mainloop()")
    lines.append("")
    return "\n".join(lines)


def service_sources(name: str, description: str, script_name: str = "dienst.ps1") -> dict:
    service = safe_name(name, "ShatuDienst")
    file_name = Path(script_name).name
    if not re.match(r"^[A-Za-z0-9_.-]+\.ps1$", file_name):
        file_name = service + ".ps1"
    text = description.strip().replace("\n", " ") or service
    worker = (
        f"# Windows-Dienst {service}. Beenden: Stop-Service und die Stoppdatei.\n"
        "$ErrorActionPreference = 'Stop'\n"
        "$stopFile = Join-Path $PSScriptRoot 'stop.flag'\n"
        "if (Test-Path -LiteralPath $stopFile) { Remove-Item -LiteralPath $stopFile -Force }\n"
        "while (-not (Test-Path -LiteralPath $stopFile)) {\n"
        "    # Arbeit des Dienstes\n"
        "    Start-Sleep -Seconds 5\n"
        "}\n"
    )
    install = (
        f"# Einmal mit Administratorrechten ausführen. Legt den Dienst {service} an.\n"
        "$pwsh = (Get-Command pwsh -ErrorAction SilentlyContinue).Source\n"
        "if (-not $pwsh) {\n"
        "    $pwsh = Join-Path $env:SystemRoot 'System32\\WindowsPowerShell\\v1.0\\powershell.exe'\n"
        "}\n"
        f"$script = Join-Path $PSScriptRoot {_ps_literal(file_name)}\n"
        f"$binary = '\"' + $pwsh + '\" -NoProfile -ExecutionPolicy Bypass -File \"' + $script + '\"'\n"
        f"New-Service -Name {_ps_literal(service)} -BinaryPathName $binary -DisplayName {_ps_literal(service)} -StartupType Manual -Description {_ps_literal(text)}\n"
    )
    remove = (
        f"Stop-Service -Name {_ps_literal(service)} -Force -ErrorAction SilentlyContinue\n"
        f"sc.exe delete {_ps_literal(service)}\n"
        "New-Item -ItemType File -Path (Join-Path $PSScriptRoot 'stop.flag') -Force | Out-Null\n"
    )
    return {
        "ok": True,
        "name": service,
        "files": {
            file_name: worker,
            "install-" + service + ".ps1": install,
            "remove-" + service + ".ps1": remove,
        },
    }


def _bytes_c(data: bytes) -> str:
    if not data:
        return "    0"
    rows = []
    for index in range(0, len(data), 16):
        chunk = data[index:index + 16]
        rows.append("    " + ", ".join(str(number) for number in chunk))
    return ",\n".join(rows)


def _csc_path() -> str | None:
    found = shutil.which("csc") or shutil.which("csc.exe")
    if found:
        return found
    if os.name != "nt":
        return None
    windows = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    for folder in ("Framework64", "Framework"):
        root = windows / "Microsoft.NET" / folder
        if not root.is_dir():
            continue
        versions = sorted(root.glob("v4*"), reverse=True)
        for version in versions:
            compiler = version / "csc.exe"
            if compiler.is_file():
                return str(compiler)
    return None


def compiler_status() -> dict:
    return {
        "ok": True,
        "gcc": shutil.which("gcc") or "",
        "mingw": shutil.which("x86_64-w64-mingw32-gcc") or "",
        "csc": _csc_path() or "",
        "mcs": shutil.which("mcs") or "",
        "msibuild": shutil.which("msibuild") or "",
        "gcab": shutil.which("gcab") or "",
        "wix": shutil.which("wix") or "",
    }


def _choose_compiler(language: str, target: str) -> dict | None:
    mingw = shutil.which("x86_64-w64-mingw32-gcc")
    gcc = shutil.which("gcc")
    csc = _csc_path()
    mcs = shutil.which("mcs")
    want_windows = target == "windows" or (
        target == "auto" and language in {"powershell", "batch"} and bool(mingw or csc or mcs or os.name == "nt")
    )
    if target == "native":
        want_windows = False
    if want_windows:
        if mingw:
            return {"id": "mingw", "kind": "exe"}
        if csc:
            return {"id": "csc", "kind": "exe"}
        if mcs:
            return {"id": "mcs", "kind": "exe"}
        if target == "windows":
            return None
    if gcc:
        return {"id": "gcc", "kind": "elf"}
    if csc:
        return {"id": "csc", "kind": "exe"}
    if mcs:
        return {"id": "mcs", "kind": "exe"}
    return None


def _pyinstaller_ready(python: str) -> bool:
    if not python:
        return False
    try:
        proc = subprocess.run([python, "-c", "import PyInstaller"], capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def compile_exe(
    workspace: Path,
    source: str,
    language: str,
    name: str,
    *,
    target: str = "auto",
    windowed: bool = False,
    python: str = "",
    bundle: bool = True,
) -> dict:
    if language not in {"python", "powershell", "shell", "batch"}:
        return {"ok": False, "error": "Eine EXE gibt es für Python, PowerShell, Bash und Batch."}
    try:
        app_name = safe_name(name)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    folder = output_dir(workspace)
    data = source.encode("utf-8")
    if bundle and language == "python" and _pyinstaller_ready(python):
        suffix = ".pyw" if windowed else ".py"
        script = folder / "quelle" / f"{app_name}{suffix}"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(source, encoding="utf-8")
        argv = [
            python, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
            "--name", app_name, "--distpath", str(folder),
            "--workpath", str(folder / "pyi-build"), "--specpath", str(folder),
        ]
        if windowed:
            argv.append("--windowed")
        argv.append(str(script))
        return {
            "ok": True,
            "kind": "pyinstaller",
            "argv": argv,
            "message": "PyInstaller packt den Python-Interpreter in eine EXE. Die Ausgabe liegt in ausgabe/.",
        }
    if len(data) > 400_000:
        return {"ok": False, "error": "Das Skript ist größer als 400 KB. Python kann mit installiertem PyInstaller den Interpreter mitpacken."}
    compiler = _choose_compiler(language, target if target in {"auto", "windows", "native"} else "auto")
    suffix = { "python": ".py", "powershell": ".ps1", "shell": ".sh", "batch": ".bat" }[language]
    if compiler is None:
        return {
            "ok": False,
            "error": "Kein Compiler gefunden. Windows-EXE: x86_64-w64-mingw32-gcc oder csc. Linux-Programm: gcc.",
        }
    if compiler["id"] in {"csc", "mcs"}:
        source_path = folder / f"{app_name}.cs"
        payload = base64.b64encode(data).decode("ascii")
        cs = (
            "using System;\nusing System.Diagnostics;\nusing System.IO;\nusing System.Text;\n"
            "internal static class Program {\n"
            f"    private const string Kind = \"{language}\";\n"
            f"    private const string Suffix = \"{suffix}\";\n"
            f"    private const string Payload = \"{payload}\";\n"
            "    private static int Main(string[] args) {\n"
            "        var script = Encoding.UTF8.GetString(Convert.FromBase64String(Payload));\n"
            "        var path = Path.Combine(Path.GetTempPath(), \"shatu-\" + Guid.NewGuid().ToString(\"n\") + Suffix);\n"
            "        File.WriteAllText(path, script, new UTF8Encoding(false));\n"
            "        var exe = Kind == \"python\" ? \"python\" : Kind == \"shell\" ? \"bash\" : Kind == \"batch\" ? \"cmd.exe\" : \"pwsh\";\n"
            "        var psi = new ProcessStartInfo { FileName = exe, UseShellExecute = false };\n"
            "        psi.Arguments = Kind == \"powershell\" ? \"-NoProfile -File \\\"\" + path + \"\\\"\" : Kind == \"batch\" ? \"/c \\\"\" + path + \"\\\"\" : \"\\\"\" + path + \"\\\"\";\n"
            "        try { var proc = Process.Start(psi); proc.WaitForExit(); return proc.ExitCode; }\n"
            "        catch (Exception ex) { Console.Error.WriteLine(ex.Message); return 127; }\n"
            "    }\n}\n"
        )
        source_path.write_text(cs, encoding="utf-8")
        exe = folder / f"{app_name}.exe"
        if compiler["id"] == "csc":
            argv = [compiler_path(compiler), "/nologo", "/out:" + str(exe), str(source_path)]
        else:
            argv = [shutil.which("mcs") or "mcs", "-out:" + str(exe), str(source_path)]
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            return {"ok": False, "error": (proc.stderr or proc.stdout or "C#-Compiler fehlgeschlagen.").strip(), "source": str(source_path)}
        return {"ok": True, "path": str(exe), "kind": "exe", "source": str(source_path), "message": f"Windows-EXE {exe.name} erzeugt. Der Interpreter muss auf dem Zielrechner installiert sein."}
    c_source = _WIN_C if compiler["id"] == "mingw" else _POSIX_C
    c_source = (
        c_source.replace("__BYTES__", _bytes_c(data))
        .replace("__LEN__", str(len(data)))
        .replace("__KIND__", language)
        .replace("__SUFFIX__", suffix)
    )
    c_path = folder / f"{app_name}.c"
    c_path.write_text(c_source, encoding="utf-8")
    if compiler["id"] == "mingw":
        exe = folder / f"{app_name}.exe"
        argv = ["x86_64-w64-mingw32-gcc", "-O2", "-s", "-o", str(exe), str(c_path)]
        if windowed:
            argv.insert(1, "-mwindows")
            argv.insert(1, "-DWINDOWED")
        message = f"Windows-EXE {exe.name} erzeugt. PowerShell, Python oder Bash muss auf dem Zielrechner vorhanden sein."
        kind = "exe"
    else:
        exe = folder / app_name
        argv = ["gcc", "-O2", "-s", "-o", str(exe), str(c_path)]
        message = f"Programm {exe.name} erzeugt. Es startet den auf diesem Rechner installierten Interpreter."
        kind = "elf"
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        return {"ok": False, "error": (proc.stderr or proc.stdout or "Compiler fehlgeschlagen.").strip(), "source": str(c_path)}
    if kind == "elf":
        exe.chmod(0o755)
    return {"ok": True, "path": str(exe), "kind": kind, "source": str(c_path), "message": message}


def compiler_path(compiler: dict) -> str:
    if compiler["id"] == "csc":
        return _csc_path() or "csc"
    if compiler["id"] == "mingw":
        return "x86_64-w64-mingw32-gcc"
    if compiler["id"] == "mcs":
        return shutil.which("mcs") or "mcs"
    return shutil.which("gcc") or "gcc"


def _xml(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _wix_version(version: str) -> str:
    parts = version.split(".")
    while len(parts) < 4:
        parts.append("0")
    return ".".join(parts[:4])


def _short_dir(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9]", "", name).upper() or "SHATU"
    return (stem[:6] + "~1")


def _idt(table: str, columns: list[str], types: list[str], keys: list[str], rows: list[list[str]]) -> str:
    lines = ["\t".join(columns), "\t".join(types), "\t".join([table, *keys])]
    for row in rows:
        lines.append("\t".join(row))
    return "\r\n".join(lines) + "\r\n"


def build_msi(
    workspace: Path,
    name: str,
    version: str,
    manufacturer: str,
    files: list[Path],
) -> dict:
    try:
        product = safe_name(name)
        ver = safe_version(version)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    maker = (manufacturer or "ShatuIDE").strip()[:80] or "ShatuIDE"
    payloads = [Path(item) for item in files if Path(item).is_file()]
    if not payloads:
        return {"ok": False, "error": "Keine Datei für den Installer."}
    for payload in payloads:
        if not inside(workspace, payload):
            return {"ok": False, "error": "Der Installer nimmt nur Dateien aus dem Workspace."}
    folder = output_dir(workspace) / product
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    staged: list[tuple[str, Path]] = []
    for index, payload in enumerate(payloads):
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", payload.name) or f"datei{index}"
        if safe.startswith("-") or safe.startswith("."):
            safe = f"datei{index}_{safe.lstrip('.-')}"
        if any(safe == existing for existing, _path in staged):
            safe = f"{index}_{safe}"
        target = folder / safe
        shutil.copy2(payload, target)
        staged.append((safe, target))
    upgrade = str(uuid.uuid5(uuid.NAMESPACE_URL, "shatuide-msi:" + product)).upper()
    product_code = str(uuid.uuid4()).upper()
    package_code = str(uuid.uuid4()).upper()
    wxs_files = []
    for index, (safe, _path) in enumerate(staged):
        component = str(uuid.uuid5(uuid.NAMESPACE_URL, f"shatuide-file:{product}:{safe}")).upper()
        wxs_files.append(
            f'          <Component Id="cmp{index}" Guid="{component}">\n'
            f'            <File Id="fil{index}" Source="{_xml(safe)}" KeyPath="yes" />\n'
            "          </Component>"
        )
    wxs = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">\n'
        f'  <Product Id="{product_code}" Name="{_xml(product)}" Language="1031" Version="{_wix_version(ver)}" '
        f'Manufacturer="{_xml(maker)}" UpgradeCode="{upgrade}">\n'
        '    <Package InstallerVersion="301" Compressed="yes" InstallScope="perMachine" />\n'
        '    <MediaTemplate EmbedCab="yes" />\n'
        '    <Directory Id="TARGETDIR" Name="SourceDir">\n'
        '      <Directory Id="ProgramFilesFolder">\n'
        f'        <Directory Id="INSTALLDIR" Name="{_xml(product)}">\n'
        + "\n".join(wxs_files)
        + "\n        </Directory>\n      </Directory>\n    </Directory>\n"
        '    <Feature Id="Main" Title="' + _xml(product) + '" Level="1">\n'
        + "".join(f'      <ComponentRef Id="cmp{index}" />\n' for index in range(len(staged)))
        + "    </Feature>\n  </Product>\n</Wix>\n"
    )
    wxs_path = folder / (product + ".wxs")
    wxs_path.write_text(wxs, encoding="utf-8")
    msibuild = shutil.which("msibuild")
    gcab = shutil.which("gcab")
    if not msibuild or not gcab:
        return {
            "ok": False,
            "error": "MSI-Compiler nicht gefunden (msibuild und gcab, Paket msitools). Die WiX-Quelle liegt bereit.",
            "wxs": str(wxs_path),
        }
    cab = folder / "files.cab"
    proc = subprocess.run([gcab, "-c", "-n", str(cab), *[name for name, _path in staged]], cwd=str(folder), capture_output=True, text=True)
    if proc.returncode != 0:
        return {"ok": False, "error": (proc.stderr or proc.stdout or "cab fehlgeschlagen").strip(), "wxs": str(wxs_path)}
    rows_dir = [
        ["TARGETDIR", "", "SourceDir"],
        ["ProgramFilesFolder", "TARGETDIR", "PFiles"],
        ["INSTALLDIR", "ProgramFilesFolder", f"{_short_dir(product)}|{product}"],
    ]
    rows_component = []
    rows_feature_components = []
    rows_file = []
    for index, (safe, path) in enumerate(staged):
        component = "{" + str(uuid.uuid5(uuid.NAMESPACE_URL, f"shatuide-file:{product}:{safe}")).upper() + "}"
        rows_component.append([f"cmp{index}", component, "INSTALLDIR", "0", "", f"fil{index}"])
        rows_feature_components.append(["Main", f"cmp{index}"])
        rows_file.append([f"fil{index}", f"cmp{index}", safe, str(path.stat().st_size), "", "", "512", str(index + 1)])
    tables = {
        "Property.idt": _idt(
            "Property",
            ["Property", "Value"],
            ["s72", "l0"],
            ["Property"],
            [
                ["ProductName", product],
                ["ProductCode", "{" + product_code + "}"],
                ["ProductVersion", ver if ver.count(".") == 2 else _wix_version(ver)],
                ["Manufacturer", maker],
                ["ProductLanguage", "1031"],
                ["UpgradeCode", "{" + upgrade + "}"],
                ["ALLUSERS", "1"],
            ],
        ),
        "Directory.idt": _idt(
            "Directory",
            ["Directory", "Directory_Parent", "DefaultDir"],
            ["s72", "S72", "l255"],
            ["Directory"],
            rows_dir,
        ),
        "Component.idt": _idt(
            "Component",
            ["Component", "ComponentId", "Directory_", "Attributes", "Condition", "KeyPath"],
            ["s72", "S38", "s72", "i2", "S255", "S72"],
            ["Component"],
            rows_component,
        ),
        "Feature.idt": _idt(
            "Feature",
            ["Feature", "Feature_Parent", "Title", "Description", "Display", "Level", "Directory_", "Attributes"],
            ["s38", "S38", "L64", "L255", "I2", "i2", "S72", "i2"],
            ["Feature"],
            [["Main", "", product, "Dateien", "1", "1", "INSTALLDIR", "0"]],
        ),
        "FeatureComponents.idt": _idt(
            "FeatureComponents",
            ["Feature_", "Component_"],
            ["s38", "s72"],
            ["Feature_", "Component_"],
            rows_feature_components,
        ),
        "File.idt": _idt(
            "File",
            ["File", "Component_", "FileName", "FileSize", "Version", "Language", "Attributes", "Sequence"],
            ["s72", "s72", "l255", "i4", "S72", "S20", "I2", "i2"],
            ["File"],
            rows_file,
        ),
        "Media.idt": _idt(
            "Media",
            ["DiskId", "LastSequence", "DiskPrompt", "Cabinet", "VolumeLabel", "Source"],
            ["i2", "i2", "L64", "S255", "S32", "S72"],
            ["DiskId"],
            [["1", str(len(staged)), "", "#files.cab", "", ""]],
        ),
        "InstallExecuteSequence.idt": _idt(
            "InstallExecuteSequence",
            ["Action", "Condition", "Sequence"],
            ["s72", "S255", "I2"],
            ["Action"],
            [
                ["CostInitialize", "", "800"],
                ["FileCost", "", "900"],
                ["CostFinalize", "", "1000"],
                ["InstallValidate", "", "1400"],
                ["InstallInitialize", "", "1500"],
                ["ProcessComponents", "", "1600"],
                ["InstallFiles", "", "4000"],
                ["InstallFinalize", "", "6600"],
            ],
        ),
    }
    for filename, text in tables.items():
        (folder / filename).write_bytes(text.encode("utf-8"))
    msi = folder / f"{product}.msi"
    if msi.exists():
        msi.unlink()
    commands = [[msibuild, str(msi), "-s", product, maker, "x64;1031", "{" + package_code + "}"]]
    commands.extend([msibuild, str(msi), "-i", name] for name in tables)
    commands.append([msibuild, str(msi), "-a", "files.cab", str(cab)])
    for argv in commands:
        proc = subprocess.run(argv, cwd=str(folder), capture_output=True, text=True)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "msibuild fehlgeschlagen").strip()
            return {"ok": False, "error": detail, "wxs": str(wxs_path)}
    return {
        "ok": True,
        "path": str(msi),
        "wxs": str(wxs_path),
        "message": f"MSI {msi.name} erzeugt. Installieren unter Windows mit msiexec /i {msi.name}.",
    }


PYTHON_MEASURE = """import os, runpy, sys, time, tracemalloc
try:
    import resource
except ImportError:
    resource = None
tracemalloc.start()
start = time.perf_counter()
script = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_path(script, run_name="__main__")
elapsed = time.perf_counter() - start
_current, peak = tracemalloc.get_traced_memory()
rss = 0
if resource is not None:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if os.name == "nt":
        rss //= 1024
print("SHATU_MEASURE seconds=%.4f tracemalloc_peak_bytes=%s rss_kb=%s" % (elapsed, peak, rss))
"""

PS_MEASURE = """param([Parameter(Mandatory = $true)][string]$Script)
$sw = [Diagnostics.Stopwatch]::StartNew()
$before = (Get-Process -Id $PID).WorkingSet64
& $Script
$code = $LASTEXITCODE
$sw.Stop()
$after = (Get-Process -Id $PID).WorkingSet64
Write-Output ("SHATU_MEASURE seconds={0:N4} working_set_bytes={1} delta_bytes={2} exit={3}" -f $sw.Elapsed.TotalSeconds, $after, ($after - $before), $code)
"""

SH_MEASURE = """#!/bin/bash
start=$(date +%s%N)
bash "$1"
code=$?
end=$(date +%s%N)
awk -v s="$start" -v e="$end" 'BEGIN { printf "SHATU_MEASURE seconds=%.4f rss_kb=0\\n", (e - s) / 1000000000 }'
exit $code
"""


def measure_invocation(language: str, script: str, python: str, workdir: Path) -> dict:
    workdir.mkdir(parents=True, exist_ok=True)
    target = str(Path(script).resolve())
    if language == "python":
        harness = workdir / "measure.py"
        harness.write_text(PYTHON_MEASURE, encoding="utf-8")
        return {"ok": True, "argv": [python or "python3", str(harness), target]}
    if language == "powershell":
        binary = powershell_binary()
        if not binary:
            return {"ok": False, "error": "PowerShell nicht gefunden (pwsh oder powershell)."}
        wrapper = workdir / "measure.ps1"
        wrapper.write_text(PS_MEASURE, encoding="utf-8")
        return {"ok": True, "argv": [binary, "-NoProfile", "-File", str(wrapper), "-Script", target]}
    if language == "shell":
        wrapper = workdir / "measure.sh"
        wrapper.write_text(SH_MEASURE, encoding="utf-8")
        wrapper.chmod(0o755)
        binary = shell_binary() or "bash"
        return {"ok": True, "argv": [binary, str(wrapper), target]}
    return {"ok": False, "error": "Messen gibt es für Python, PowerShell und Bash."}


def powershell_help(topic: str) -> dict:
    text = (topic or "").strip()
    if not _TOPIC.match(text):
        return {"ok": False, "error": "Hilfethema ungültig."}
    binary = powershell_binary()
    if not binary:
        return {"ok": False, "error": "PowerShell nicht gefunden (pwsh oder powershell)."}
    command = "Get-Help -Name " + _ps_literal(text) + " | Out-String -Width 100"
    try:
        proc = subprocess.run([binary, "-NoProfile", "-Command", command], capture_output=True, text=True, timeout=40)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}
    body = (proc.stdout or proc.stderr or "").strip()
    if not body:
        return {"ok": False, "error": "Keine Hilfe zu diesem Thema."}
    return {"ok": True, "topic": text, "text": body[:20000], "edition": Path(binary).name}


def remote_powershell(transport: str, host: str, command: str, user: str = "") -> dict:
    command = command.replace("\x00", "")
    if not command.strip():
        return {"ok": False, "error": "Befehl fehlt."}
    if len(command) > 200_000:
        return {"ok": False, "error": "Befehl ist zu lang."}
    transport = (transport or "local").lower()
    binary = powershell_binary()
    if transport == "local":
        if not binary:
            return {"ok": False, "error": "PowerShell nicht gefunden (pwsh oder powershell)."}
        return {"ok": True, "argv": [binary, "-NoProfile", "-EncodedCommand", encode_powershell(command)]}
    if not _HOST.match(host or ""):
        return {"ok": False, "error": "Host nur mit Buchstaben, Ziffern, Punkt und Bindestrich."}
    if user and not _USER.match(user):
        return {"ok": False, "error": "Benutzername ungültig."}
    target = f"{user}@{host}" if user else host
    if transport == "ssh":
        if not shutil.which("ssh"):
            return {"ok": False, "error": "ssh ist nicht installiert."}
        return {
            "ok": True,
            "argv": [
                "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", target,
                "pwsh", "-NoProfile", "-EncodedCommand", encode_powershell(command),
            ],
        }
    if transport == "winrm":
        if not binary:
            return {"ok": False, "error": "PowerShell nicht gefunden (pwsh oder powershell)."}
        inner = encode_powershell(command)
        outer = (
            "$s = [Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('" + inner + "'))\n"
            "Invoke-Command -ComputerName " + _ps_literal(host) + " -ScriptBlock ([scriptblock]::Create($s))\n"
        )
        return {"ok": True, "argv": [binary, "-NoProfile", "-EncodedCommand", encode_powershell(outer)]}
    return {"ok": False, "error": "Transport ist local, ssh oder winrm."}


def remote_trace(language: str, script: str, content: str, transport: str, host: str, user: str, python: str) -> dict:
    transport = (transport or "local").lower()
    if language == "powershell":
        if transport == "local":
            body = "Set-PSDebug -Trace 1\n& " + _ps_literal(str(Path(script).resolve()))
        else:
            body = "Set-PSDebug -Trace 1\n" + content
        return remote_powershell(transport, host, body, user)
    if language == "shell":
        if transport == "local":
            binary = shell_binary()
            if not binary:
                return {"ok": False, "error": "Keine Linux-Shell gefunden (bash oder sh)."}
            return {"ok": True, "argv": [binary, "-x", str(Path(script).resolve())]}
        if not _HOST.match(host or ""):
            return {"ok": False, "error": "Host nur mit Buchstaben, Ziffern, Punkt und Bindestrich."}
        if user and not _USER.match(user):
            return {"ok": False, "error": "Benutzername ungültig."}
        if not shutil.which("ssh"):
            return {"ok": False, "error": "ssh ist nicht installiert."}
        payload = base64.b64encode(content.encode("utf-8")).decode("ascii")
        target = f"{user}@{host}" if user else host
        remote = "printf %s " + payload + " | base64 -d | bash -x"
        return {"ok": True, "argv": ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", target, "bash", "-lc", remote]}
    if language == "python":
        if transport == "local":
            return {"ok": True, "argv": [python or "python3", "-m", "trace", "--trace", str(Path(script).resolve())]}
        if not _HOST.match(host or ""):
            return {"ok": False, "error": "Host nur mit Buchstaben, Ziffern, Punkt und Bindestrich."}
        if not shutil.which("ssh"):
            return {"ok": False, "error": "ssh ist nicht installiert."}
        payload = base64.b64encode(content.encode("utf-8")).decode("ascii")
        target = f"{user}@{host}" if user else host
        remote = "printf %s " + payload + " | base64 -d > /tmp/shatu-remote.py && python3 -m trace --trace /tmp/shatu-remote.py"
        return {"ok": True, "argv": ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", target, "bash", "-lc", remote]}
    return {"ok": False, "error": "Remote-Ablauf gibt es für Python, PowerShell und Bash."}


def powershell_companions(script: Path, points: list | None = None) -> list[str]:
    try:
        main = script.resolve()
    except OSError:
        main = script
    found: list[str] = []
    if main.parent.is_dir():
        for child in sorted(main.parent.iterdir(), key=lambda item: item.name.lower()):
            if child.suffix.lower() in {".ps1", ".psm1"} and child.resolve() != main and child.stat().st_size < 200_000:
                found.append(str(child.resolve()))
            if len(found) >= 15:
                break
    for point in points or []:
        if not isinstance(point, dict):
            continue
        file_name = str(point.get("file") or "")
        if not file_name:
            continue
        try:
            candidate = Path(file_name).resolve()
        except OSError:
            continue
        if candidate.is_file() and candidate != main and candidate.suffix.lower() in {".ps1", ".psm1", ".psd1"}:
            found.append(str(candidate))
    unique: list[str] = []
    seen: set[str] = set()
    for item in found:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique[:20]


def _recovery_dir(workspace: Path) -> Path:
    folder = Path(workspace) / ".shatuide" / "recovery"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def recovery_store(workspace: Path, path: str, content: str) -> dict:
    if len(content.encode("utf-8")) > 2_000_000:
        return {"ok": False, "error": "Puffer ist zu groß für die Wiederherstellung."}
    if not path.strip():
        return {"ok": False, "error": "Pfad fehlt."}
    folder = _recovery_dir(workspace)
    ident = hashlib.sha1(path.encode("utf-8")).hexdigest()[:16]
    (folder / f"{ident}.txt").write_text(content, encoding="utf-8")
    meta = {
        "id": ident,
        "path": path,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "bytes": len(content.encode("utf-8")),
    }
    (folder / f"{ident}.json").write_text(json.dumps(meta), encoding="utf-8")
    return {"ok": True, **meta}


def recovery_list(workspace: Path) -> dict:
    folder = Path(workspace) / ".shatuide" / "recovery"
    items = []
    if folder.is_dir():
        for meta_path in sorted(folder.glob("*.json")):
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(meta, dict) and meta.get("id"):
                items.append(meta)
    items.sort(key=lambda item: str(item.get("time") or ""), reverse=True)
    return {"ok": True, "items": items}


def recovery_read(workspace: Path, ident: str) -> dict:
    if not re.match(r"^[a-f0-9]{16}$", ident or ""):
        return {"ok": False, "error": "Ungültige Wiederherstellung."}
    folder = Path(workspace) / ".shatuide" / "recovery"
    meta_path = folder / f"{ident}.json"
    data_path = folder / f"{ident}.txt"
    if not meta_path.is_file() or not data_path.is_file():
        return {"ok": False, "error": "Wiederherstellung nicht gefunden."}
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"ok": False, "error": "Wiederherstellung beschädigt."}
    return {"ok": True, "content": data_path.read_text(encoding="utf-8"), **meta}


def recovery_drop(workspace: Path, ident: str) -> dict:
    if not re.match(r"^[a-f0-9]{16}$", ident or ""):
        return {"ok": False, "error": "Ungültige Wiederherstellung."}
    folder = Path(workspace) / ".shatuide" / "recovery"
    for suffix in (".json", ".txt"):
        (folder / f"{ident}{suffix}").unlink(missing_ok=True)
    return {"ok": True}
