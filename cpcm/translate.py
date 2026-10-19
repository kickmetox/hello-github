"""Semantische Übersetzung von Shell, JSON, INI und Registry."""

from __future__ import annotations

import json
import re
from configparser import ConfigParser
from io import StringIO
from pathlib import Path

from cpcm.paths import Identity, World, identity_for_home, rewrite_text
from cpcm.shortcuts import translate_shortcut

_EXPORT = re.compile(r"^\s*export\s+([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
_ALIAS = re.compile(r"^\s*alias\s+([A-Za-z0-9_]+)=(.*)$")
_SET = re.compile(r"^\s*\$env:([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", re.I)
_REG_HEADER = re.compile(r"^Windows Registry Editor", re.I)
_REG_KEY = re.compile(r"^\[(.+)\]\s*$")
_REG_VALUE = re.compile(r'^"([^"]+)"="(.*)"\s*$')


def detect_format(text: str) -> str:
    stripped = text.lstrip()
    if _REG_HEADER.match(stripped):
        return "reg"
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            json.loads(text)
            return "json"
        except json.JSONDecodeError:
            pass
    if _looks_like_ini(text):
        return "ini"
    if any(_EXPORT.match(line) or _ALIAS.match(line) for line in text.splitlines()):
        return "shell"
    if any(_SET.match(line) for line in text.splitlines()):
        return "powershell"
    return "text"


def _looks_like_ini(text: str) -> bool:
    section = pair = False
    for line in text.splitlines():
        raw = line.strip()
        if not raw or raw.startswith(("#", ";")):
            continue
        if raw.startswith("[") and raw.endswith("]"):
            section = True
        elif "=" in raw:
            pair = True
    return section and pair


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def translate_config(text: str, source: Identity, target: Identity, *, fmt: str | None = None) -> dict:
    kind = fmt or detect_format(text)
    changes: list[dict] = []
    if kind == "json":
        body = _translate_json(text, source, target, changes)
        return {"format": "json", "text": body, "reg": "", "changes": changes, "warnings": []}
    if kind == "ini":
        return {"format": "ini", "text": _translate_ini(text, source, target, changes), "reg": "", "changes": changes, "warnings": []}
    if kind == "reg":
        body = _reg_to_shell(text, changes) if target.world == World.LINUX else rewrite_text(text, source, target)
        return {"format": "shell" if target.world == World.LINUX else "reg", "text": body, "reg": body if target.world == World.WINDOWS else "", "changes": changes, "warnings": []}
    if kind == "powershell":
        return {"format": "shell", "text": _powershell_to_shell(text, source, target, changes), "reg": "", "changes": changes, "warnings": []}
    if kind == "shell" and target.world == World.WINDOWS:
        shell_text, reg_text = _shell_to_windows(text, source, target, changes)
        return {"format": "powershell", "text": shell_text, "reg": reg_text, "changes": changes, "warnings": []}
    rewritten = rewrite_text(text, source, target)
    if rewritten != text:
        changes.append({"kind": "paths", "detail": "Absolute Pfade auf die Zielwelt umgesetzt"})
    return {"format": kind, "text": rewritten, "reg": "", "changes": changes, "warnings": []}


def _translate_json(text, source, target, changes) -> str:
    data = json.loads(text)

    def walk(node, path):
        if isinstance(node, dict):
            for key, value in list(node.items()):
                child = f"{path}.{key}" if path else key
                if key == "key" and isinstance(value, str):
                    converted = translate_shortcut(value, target.world)
                    if converted != value:
                        node[key] = converted
                        changes.append({"kind": "shortcut", "path": child, "from": value, "to": converted})
                elif isinstance(value, str):
                    updated = rewrite_text(value, source, target)
                    if updated != value:
                        node[key] = updated
                        changes.append({"kind": "path", "path": child, "from": value, "to": updated})
                else:
                    walk(value, child)
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    walk(data, "")
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _translate_ini(text, source, target, changes) -> str:
    parser = ConfigParser(interpolation=None)
    parser.optionxform = str  # type: ignore[method-assign]
    parser.read_file(StringIO(text))
    for section in parser.sections():
        for key, value in parser.items(section):
            updated = rewrite_text(value, source, target)
            if updated != value:
                parser.set(section, key, updated)
                changes.append({"kind": "path", "path": f"{section}.{key}", "from": value, "to": updated})
    buffer = StringIO()
    parser.write(buffer)
    return buffer.getvalue()


def _shell_to_windows(text, source, target, changes):
    ps = ["# Erzeugt von CPCM aus einer Shell-Konfiguration", ""]
    reg = ["Windows Registry Editor Version 5.00", "", r"[HKEY_CURRENT_USER\Environment]"]
    aliases = []
    for line in text.splitlines():
        exported, aliased = _EXPORT.match(line), _ALIAS.match(line)
        if exported:
            name, raw_value = exported.group(1), _unquote(exported.group(2))
            value = rewrite_text(raw_value, source, target).replace("$HOME", str(target.home))
            ps.append(f"[Environment]::SetEnvironmentVariable('{name}', '{value.replace(chr(39), chr(39)*2)}', 'User')")
            reg.append(f'"{name}"="{value.replace(chr(92), chr(92)*2).replace(chr(34), chr(92)+chr(34))}"')
            changes.append({"kind": "env", "path": name, "from": raw_value, "to": value})
        elif aliased:
            raw_value = _unquote(aliased.group(2))
            body = "Get-ChildItem -Force" if raw_value.strip() in ("ls -al", "ls -alF", "ls -la", "ls -a") else raw_value
            aliases.append(f"function {aliased.group(1)} {{ {body} }}")
            changes.append({"kind": "alias", "path": aliased.group(1), "from": raw_value, "to": aliases[-1]})
    if aliases:
        ps.extend(["", "# Aliase als Funktionen für das PowerShell-Profil", *aliases])
    return "\n".join(ps).rstrip() + "\n", "\n".join(reg).rstrip() + "\n"


def _powershell_to_shell(text, source, target, changes) -> str:
    lines = ["# Erzeugt von CPCM aus PowerShell"]
    for line in text.splitlines():
        matched = _SET.match(line)
        if not matched:
            continue
        name, raw_value = matched.group(1), _unquote(matched.group(2))
        value = rewrite_text(raw_value, source, target)
        lines.append(f"export {name}={value}")
        changes.append({"kind": "env", "path": name, "from": raw_value, "to": value})
    return "\n".join(lines).rstrip() + "\n"


def _reg_to_shell(text, changes) -> str:
    lines, section = ["# Erzeugt von CPCM aus einer Registry-Datei"], ""
    for line in text.splitlines():
        key, value = _REG_KEY.match(line.strip()), _REG_VALUE.match(line.strip())
        if key:
            section = key.group(1)
        elif value and section.lower().endswith("\\environment"):
            lines.append(f"export {value.group(1)}={value.group(2)}")
            changes.append({"kind": "env", "path": value.group(1), "from": value.group(2), "to": value.group(2)})
    return "\n".join(lines).rstrip() + "\n"


def identities_from_request(payload: dict, host: Identity) -> tuple[Identity, Identity]:
    source_world = World(str(payload.get("source") or host.world.value))
    target_world = World(str(payload.get("target") or ("windows" if source_world == World.LINUX else "linux")))
    homes = payload.get("homes") or {}

    def home_for(world: World) -> str:
        if homes.get(world.value):
            return str(homes[world.value])
        if world == host.world:
            return str(host.home)
        return rf"C:\Users\{host.user}" if world == World.WINDOWS else f"/home/{host.user}"

    return (
        identity_for_home(source_world, Path(home_for(source_world)), host.user),
        identity_for_home(target_world, Path(home_for(target_world)), host.user),
    )
