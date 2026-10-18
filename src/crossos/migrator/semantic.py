"""Semantische Übersetzung von Dotfiles, INI, JSON, XML und .reg.

Pfade in Werten werden über :mod:`crossos.migrator.paths` korrigiert.
Bekannte Schlüssel werden zusätzlich umbenannt oder umbewertet:

- Git ``core.autocrlf``: Linux/WSL ``input``, Windows ``true``
- VS-Code-Schlüsselendung ``.linux`` ↔ ``.windows``
- ``files.eol``: Linux/WSL LF, Windows CRLF
"""

from __future__ import annotations

import configparser
import io
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

from crossos.migrator.paths import rewrite_obj, rewrite_text
from crossos.safety import SafetyError

FORMATS = {"json", "reg", "xml", "ini", "bash", "env"}

_EXPORT = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
_SECTION = re.compile(r"^\[(.+)\]$")
_REG_VALUE = re.compile(
    r'^"(?P<name>(?:\\.|[^"\\])*)"=(?P<body>dword:(?P<dword>[0-9a-fA-F]+)|"(?P<sz>(?:\\.|[^"\\])*)")\s*$'
)


@dataclass
class Entry:
    key: str
    value: object
    type_name: str = "str"


@dataclass
class Section:
    name: str
    entries: list[Entry] = field(default_factory=list)


@dataclass
class Document:
    source_format: str
    profile: str
    sections: list[Section]
    changes: list[dict] = field(default_factory=list)


@dataclass
class SemanticChange:
    key: str
    before: object
    after: object
    reason: str

    def as_dict(self) -> dict:
        return {
            "kind": "semantic",
            "key": self.key,
            "before": self.before,
            "after": self.after,
            "reason": self.reason,
        }


def detect_format(text: str) -> str:
    sample = text.lstrip("\ufeff").lstrip()
    if not sample:
        raise SafetyError("Leeres Dokument.")
    if sample.startswith("Windows Registry Editor"):
        return "reg"
    if sample.startswith("{"):
        return "json"
    if sample.startswith("["):
        first = sample.splitlines()[0].strip()
        if first == "[" or first.startswith("[{") or first.startswith('["') or first.startswith("['"):
            return "json"
        if re.match(r"^\[[^\]\n]+\]$", first):
            return "ini"
    if sample.startswith("<?xml") or sample.startswith("<"):
        return "xml"
    if re.search(r"(?m)^(?:export\s+[A-Za-z_]|alias\s+)", sample):
        return "bash"
    if re.search(r"(?m)^\[[^\]\n]+\]\s*$", sample):
        return "ini"
    if re.search(r"(?m)^[A-Za-z_][A-Za-z0-9_]*=", sample):
        return "env"
    raise SafetyError("Format nicht erkannt. Erlaubt: json, reg, xml, ini, bash, env.")


def _profile_for(sections: list[Section], source_format: str) -> str:
    names = {section.name.strip().lower() for section in sections}
    if names & {"user", "core", "alias", "credential", "color", "diff"}:
        return "gitconfig"
    if source_format == "json":
        keys = [entry.key for section in sections for entry in section.entries]
        if any(key.startswith("editor.") or key.startswith("terminal.integrated.") or key == "files.eol" for key in keys):
            return "vscode"
    if source_format == "reg":
        blob = " ".join(section.name for section in sections).lower()
        if "\\software\\git" in blob.replace("/", "\\"):
            return "gitconfig"
        if "vscode" in blob or "\\software\\microsoft\\vscode" in blob:
            return "vscode"
    return "generic"


def _unescape_reg(value: str) -> str:
    out: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value):
            nxt = value[index + 1]
            mapping = {"\\": "\\", '"': '"', "n": "\n", "r": "\r"}
            out.append(mapping.get(nxt, nxt))
            index += 2
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _escape_reg(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")


def parse_document(text: str, source_format: str | None = None) -> Document:
    fmt = source_format or detect_format(text)
    if fmt not in FORMATS:
        raise SafetyError("Unbekanntes Quellformat.")
    if fmt == "json":
        sections = _parse_json(text)
    elif fmt == "ini":
        sections = _parse_ini(text)
    elif fmt == "env":
        sections = _parse_env(text)
    elif fmt == "bash":
        sections = _parse_bash(text)
    elif fmt == "reg":
        sections = _parse_reg(text)
    else:
        sections = _parse_xml(text)
    return Document(source_format=fmt, profile=_profile_for(sections, fmt), sections=sections)


def _parse_json(text: str) -> list[Section]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SafetyError(f"JSON ungültig: {exc.msg}") from exc
    if isinstance(data, list):
        return [Section("[]", [Entry(str(index), item) for index, item in enumerate(data)])]
    if not isinstance(data, dict):
        return [Section("", [Entry("value", data)])]
    # Verschachtelte Objekte bleiben erhalten, flache Schlüssel werden Einträge.
    return [Section("", [_json_entry(key, value) for key, value in data.items()])]


def _json_entry(key: str, value: object) -> Entry:
    if isinstance(value, dict):
        return Entry(key, value, "object")
    if isinstance(value, list):
        return Entry(key, value, "array")
    if isinstance(value, bool):
        return Entry(key, value, "bool")
    if isinstance(value, int) and not isinstance(value, bool):
        return Entry(key, value, "int")
    return Entry(key, value, "str")


def _parse_ini(text: str) -> list[Section]:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    try:
        parser.read_string(text)
    except configparser.Error as exc:
        raise SafetyError(f"INI ungültig: {exc}") from exc
    sections: list[Section] = []
    for name in parser.sections():
        entries = [Entry(key, value, "str") for key, value in parser.items(name)]
        sections.append(Section(name, entries))
    if not sections:
        raise SafetyError("INI ohne Abschnitt.")
    return sections


def _parse_env(text: str) -> list[Section]:
    entries: list[Entry] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _EXPORT.match(stripped)
        if not match:
            continue
        raw = match.group(2).strip()
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {"'", '"'}:
            raw = raw[1:-1]
        entries.append(Entry(match.group(1), raw, "str"))
    if not entries:
        raise SafetyError("Keine KEY=VALUE-Zeilen gefunden.")
    return [Section("env", entries)]


def _parse_bash(text: str) -> list[Section]:
    entries: list[Entry] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("alias "):
            body = stripped[6:]
            if "=" in body:
                name, value = body.split("=", 1)
                entries.append(Entry(name.strip(), value.strip().strip("'\""), "alias"))
            continue
        match = _EXPORT.match(stripped)
        if not match:
            continue
        raw = match.group(2).strip()
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {"'", '"'}:
            raw = raw[1:-1]
        entries.append(Entry(match.group(1), raw, "export"))
    if not entries:
        raise SafetyError("Keine export- oder alias-Zeilen gefunden.")
    return [Section("bash", entries)]


def _parse_reg(text: str) -> list[Section]:
    current: Section | None = None
    sections: list[Section] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(";") or line.startswith("Windows Registry Editor"):
            continue
        if line.startswith("[") and line.endswith("]"):
            name = line[1:-1]
            if name.startswith("-"):
                continue
            current = Section(name)
            sections.append(current)
            continue
        match = _REG_VALUE.match(line)
        if not match or current is None:
            continue
        name = _unescape_reg(match.group("name"))
        if match.group("dword") is not None:
            current.entries.append(Entry(name, int(match.group("dword"), 16), "dword"))
        else:
            current.entries.append(Entry(name, _unescape_reg(match.group("sz") or ""), "str"))
    if not sections:
        raise SafetyError("Keine Registry-Schlüssel gefunden.")
    return sections


def _parse_xml(text: str) -> list[Section]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise SafetyError(f"XML ungültig: {exc}") from exc
    sections: list[Section] = []
    section_nodes = [node for node in list(root) if node.tag in {"section", "appSettings"}]
    if not section_nodes and root.tag == "section":
        section_nodes = [root]
    if section_nodes:
        for node in section_nodes:
            name = node.attrib.get("name", node.tag)
            entries: list[Entry] = []
            for child in list(node):
                if "key" in child.attrib:
                    entries.append(Entry(child.attrib["key"], child.attrib.get("value", ""), "str"))
            sections.append(Section(name, entries))
    if not sections:
        # Generischer Fallback: jedes Element mit key/value-Attribut.
        entries = []
        for node in root.iter():
            if "key" in node.attrib:
                entries.append(Entry(node.attrib["key"], node.attrib.get("value", node.text or ""), "str"))
        if entries:
            sections.append(Section(root.tag or "xml", entries))
    if not sections:
        raise SafetyError("XML enthält keine key/value-Einträge.")
    return sections


def _target_family(target_os: str) -> str:
    if target_os == "windows":
        return "windows"
    return "linux"


def apply_semantics(document: Document, target_os: str, user: str | None = None) -> list[SemanticChange]:
    family = _target_family(target_os)
    changes: list[SemanticChange] = []
    for section in document.sections:
        new_entries: list[Entry] = []
        for entry in section.entries:
            key, value, entry_changes = _transform_entry(document.profile, section.name, entry, family)
            changes.extend(entry_changes)
            if isinstance(value, str):
                rewritten, path_changes = rewrite_text(value, target_os, user)
                for change in path_changes:
                    document.changes.append(change.as_dict() | {"key": key})
                value = rewritten
            elif isinstance(value, (dict, list)):
                rewritten_obj, path_changes = rewrite_obj(value, target_os, user)
                for change in path_changes:
                    document.changes.append(change.as_dict() | {"key": key})
                value = rewritten_obj
            new_entries.append(Entry(key, value, entry.type_name))
        section.entries = new_entries
    for change in changes:
        document.changes.append(change.as_dict())
    return changes


def _transform_entry(profile: str, section: str, entry: Entry, family: str) -> tuple[str, object, list[SemanticChange]]:
    key = entry.key
    value = entry.value
    changes: list[SemanticChange] = []
    logical = key.lower()
    section_name = section.lower()

    if profile == "gitconfig" and (logical == "autocrlf" or logical.endswith(".autocrlf") or (section_name.endswith("core") and logical == "autocrlf")):
        desired = "true" if family == "windows" else "input"
        current = str(value).strip().lower()
        if current != desired:
            changes.append(
                SemanticChange(
                    key=f"{section}.{key}" if section else key,
                    before=value,
                    after=desired,
                    reason="Git core.autocrlf: Windows true, Linux/WSL input.",
                )
            )
            value = desired

    if logical == "files.eol" or logical.endswith(".files.eol"):
        desired = "\r\n" if family == "windows" else "\n"
        if value != desired:
            changes.append(
                SemanticChange(
                    key=key,
                    before=value,
                    after=desired,
                    reason="files.eol folgt dem Zielsystem (CRLF oder LF).",
                )
            )
            value = desired

    suffix_from, suffix_to = (".linux", ".windows") if family == "windows" else (".windows", ".linux")
    if key.endswith(suffix_from):
        new_key = key[: -len(suffix_from)] + suffix_to
        changes.append(
            SemanticChange(
                key=key,
                before=key,
                after=new_key,
                reason="Plattform-Suffix des Schlüssels an das Zielsystem angepasst. Der Wert wird nicht erfunden.",
            )
        )
        key = new_key
    return key, value, changes


def render_document(document: Document, target_format: str) -> str:
    if target_format not in FORMATS:
        raise SafetyError("Unbekanntes Zielformat.")
    if target_format == "json":
        return _render_json(document)
    if target_format == "ini":
        return _render_ini(document)
    if target_format == "env":
        return _render_env(document)
    if target_format == "bash":
        return _render_bash(document)
    if target_format == "reg":
        return _render_reg(document)
    return _render_xml(document)


def _sections_as_json(document: Document) -> dict:
    if len(document.sections) == 1 and document.sections[0].name in {"", "env", "bash", "[]"}:
        data: dict = {}
        for entry in document.sections[0].entries:
            data[entry.key] = entry.value
        return data
    data = {}
    for section in document.sections:
        bucket: dict = {}
        for entry in section.entries:
            bucket[entry.key] = entry.value
        data[section.name] = bucket
    return data


def _render_json(document: Document) -> str:
    return json.dumps(_sections_as_json(document), indent=2, ensure_ascii=False) + "\n"


def _render_ini(document: Document) -> str:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    for section in document.sections:
        name = section.name or "crossos"
        if name == "[]":
            name = "crossos"
        parser.add_section(name)
        for entry in section.entries:
            parser.set(name, entry.key, _stringify(entry.value))
    buffer = io.StringIO()
    parser.write(buffer)
    return buffer.getvalue()


def _stringify(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _render_env(document: Document) -> str:
    lines = []
    for section in document.sections:
        for entry in section.entries:
            key = entry.key if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", entry.key) else _env_key(section.name, entry.key)
            lines.append(f"{key}={_stringify(entry.value)}")
    return "\n".join(lines) + ("\n" if lines else "")


def _env_key(section: str, key: str) -> str:
    raw = f"{section}_{key}" if section else key
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", raw)
    if not cleaned or not cleaned[0].isalpha() and cleaned[0] != "_":
        cleaned = "K_" + cleaned
    return cleaned.upper()


def _render_bash(document: Document) -> str:
    lines = ["# CrossOS-Übersetzung. Nur Exporte, nicht ausgeführt."]
    for section in document.sections:
        for entry in section.entries:
            key = entry.key if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", entry.key) else _env_key(section.name, entry.key)
            value = _stringify(entry.value).replace("'", "'\"'\"'")
            if entry.type_name == "alias":
                lines.append(f"alias {key}='{value}'")
            else:
                lines.append(f"export {key}='{value}'")
    return "\n".join(lines) + "\n"


def _registry_root(document: Document, section: Section) -> str:
    if document.profile == "gitconfig":
        base = r"HKEY_CURRENT_USER\Software\Git"
        if section.name and section.name not in {"env", "bash", ""}:
            return base + "\\" + section.name.replace("/", "\\")
        return base
    if document.profile == "vscode":
        return r"HKEY_CURRENT_USER\Software\Microsoft\VSCode"
    if document.source_format == "reg":
        return section.name
    leaf = section.name.replace("/", "\\") if section.name else "Import"
    return r"HKEY_CURRENT_USER\Software\CrossOS" + "\\" + leaf


def _render_reg(document: Document) -> str:
    lines = ["Windows Registry Editor Version 5.00", ""]
    for section in document.sections:
        lines.append(f"[{_registry_root(document, section)}]")
        for entry in section.entries:
            name = _escape_reg(entry.key)
            if entry.type_name == "dword" or (isinstance(entry.value, int) and not isinstance(entry.value, bool)):
                lines.append(f'"{name}"=dword:{int(entry.value) & 0xFFFFFFFF:08x}')
            else:
                lines.append(f'"{name}"="{_escape_reg(_stringify(entry.value))}"')
        lines.append("")
    return "\n".join(lines)


def _render_xml(document: Document) -> str:
    parts = ['<?xml version="1.0" encoding="utf-8"?>', "<configuration>"]
    for section in document.sections:
        name = section.name or "crossos"
        parts.append(f'  <section name="{escape(name)}">')
        for entry in section.entries:
            parts.append(
                f'    <add key="{escape(entry.key)}" value="{escape(_stringify(entry.value))}"/>'
            )
        parts.append("  </section>")
    parts.append("</configuration>")
    return "\n".join(parts) + "\n"


def translate_document(
    text: str,
    *,
    target_format: str,
    target_os: str,
    source_format: str | None = None,
    user: str | None = None,
) -> dict:
    if target_os not in {"linux", "windows", "wsl"}:
        raise SafetyError("target_os muss linux, windows oder wsl sein.")
    document = parse_document(text, source_format)
    apply_semantics(document, target_os, user)
    output = render_document(document, target_format)
    return {
        "source_format": document.source_format,
        "target_format": target_format,
        "target_os": target_os,
        "profile": document.profile,
        "output": output,
        "changes": document.changes,
        "executed": False,
        "dry_run": True,
    }
