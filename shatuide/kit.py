"""Baukasten: ein Skript aus Modulen in fester Reihenfolge."""

from __future__ import annotations

import json
import keyword
import re
from pathlib import Path

from shatuide.paths import inside
from shatuide.studio import safe_name

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,40}$")
_REF = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
_LANG = {"python": "python", "powershell": "powershell", "shell": "shell", "bash": "shell", "batch": "batch"}
_SUFFIX = {"python": ".py", "powershell": ".ps1", "shell": ".sh", "batch": ".bat"}
_OPS = {"+": "+", "-": "-", "*": "*", "/": "/"}
_BATCH = {"eingabe", "ausgabe", "rechnen", "datei_schreiben", "ordner", "pause", "bedingung", "text_bauen"}

MODULES = [
    {
        "id": "eingabe",
        "title": "Eingabe",
        "text": "Fragt den Benutzer und speichert die Antwort in einer Variablen.",
        "fields": [
            {"name": "ziel", "label": "Variable", "kind": "ident", "default": "Antwort"},
            {"name": "frage", "label": "Frage", "kind": "text", "default": "Eingabe"},
            {"name": "art", "label": "Art", "kind": "choice", "default": "text", "choices": ["text", "zahl"]},
        ],
    },
    {
        "id": "ausgabe",
        "title": "Ausgabe",
        "text": "Gibt Text aus. {Variable} setzt einen vorherigen Wert ein.",
        "fields": [{"name": "text", "label": "Text", "kind": "text", "default": "{Antwort}"}],
    },
    {
        "id": "rechnen",
        "title": "Rechnen",
        "text": "Rechnet mit einer Zahl oder {Variable} und speichert das Ergebnis.",
        "fields": [
            {"name": "ziel", "label": "Variable", "kind": "ident", "default": "Ergebnis"},
            {"name": "links", "label": "Links", "kind": "text", "default": "2"},
            {"name": "operator", "label": "Operator", "kind": "choice", "default": "+", "choices": ["+", "-", "*", "/"]},
            {"name": "rechts", "label": "Rechts", "kind": "text", "default": "3"},
        ],
    },
    {
        "id": "text_bauen",
        "title": "Text bauen",
        "text": "Fügt Werte mit einem Trenner zusammen. Mehrere Werte mit Semikolon trennen.",
        "fields": [
            {"name": "ziel", "label": "Variable", "kind": "ident", "default": "Text"},
            {"name": "teile", "label": "Teile", "kind": "text", "default": "{Antwort}"},
            {"name": "trenner", "label": "Trenner", "kind": "text", "default": " "},
        ],
    },
    {
        "id": "datei_lesen",
        "title": "Datei lesen",
        "text": "Liest eine Textdatei in eine Variable.",
        "fields": [
            {"name": "quelle", "label": "Datei", "kind": "text", "default": "notiz.txt"},
            {"name": "ziel", "label": "Variable", "kind": "ident", "default": "Inhalt"},
        ],
    },
    {
        "id": "datei_schreiben",
        "title": "Datei schreiben",
        "text": "Schreibt Text in eine Datei.",
        "fields": [
            {"name": "datei", "label": "Datei", "kind": "text", "default": "notiz.txt"},
            {"name": "inhalt", "label": "Inhalt", "kind": "text", "default": "{Antwort}"},
        ],
    },
    {
        "id": "ordner",
        "title": "Ordner",
        "text": "Gibt die Namen im Ordner aus. Leer bedeutet der aktuelle Ordner.",
        "fields": [{"name": "pfad", "label": "Ordner", "kind": "text", "default": "."}],
    },
    {
        "id": "csv_zeile",
        "title": "CSV-Zeile",
        "text": "Hängt eine Zeile an. Spalten mit Semikolon trennen.",
        "fields": [
            {"name": "datei", "label": "Datei", "kind": "text", "default": "daten.csv"},
            {"name": "werte", "label": "Spalten", "kind": "text", "default": "{Antwort}"},
        ],
    },
    {
        "id": "json_lesen",
        "title": "JSON lesen",
        "text": "Liest JSON. Ein leerer Schlüssel nimmt das ganze Dokument. Bash und PowerShell rufen python3 auf.",
        "fields": [
            {"name": "datei", "label": "Datei", "kind": "text", "default": "daten.json"},
            {"name": "schluessel", "label": "Schlüssel", "kind": "text", "default": ""},
            {"name": "ziel", "label": "Variable", "kind": "ident", "default": "Daten"},
        ],
    },
    {
        "id": "sqlite",
        "title": "SQLite",
        "text": "Führt eine SQL-Anweisung aus und gibt Zeilen aus. Bash und PowerShell rufen python3 auf.",
        "fields": [
            {"name": "datei", "label": "Datenbank", "kind": "text", "default": "datenbanken/app.sqlite"},
            {"name": "sql", "label": "SQL", "kind": "text", "default": "SELECT 1"},
        ],
    },
    {
        "id": "web",
        "title": "Webseite",
        "text": "Holt eine Adresse und speichert die ersten 4000 Zeichen.",
        "fields": [
            {"name": "adresse", "label": "Adresse", "kind": "text", "default": "https://example.com"},
            {"name": "ziel", "label": "Variable", "kind": "ident", "default": "Seite"},
        ],
    },
    {
        "id": "bedingung",
        "title": "Bedingung",
        "text": "Gibt Text aus, wenn der Vergleich zutrifft.",
        "fields": [
            {"name": "variable", "label": "Variable", "kind": "ident", "default": "Antwort"},
            {"name": "vergleich", "label": "Vergleich", "kind": "choice", "default": "gleich", "choices": ["gleich", "enthaelt", "leer", "groesser"]},
            {"name": "wert", "label": "Wert", "kind": "text", "default": ""},
            {"name": "text", "label": "Dann ausgeben", "kind": "text", "default": "trifft zu"},
        ],
    },
    {
        "id": "pause",
        "title": "Pause",
        "text": "Wartet höchstens 30 Sekunden.",
        "fields": [{"name": "sekunden", "label": "Sekunden", "kind": "number", "default": "1"}],
    },
]


def catalog_view(workspace: Path | None = None) -> dict:
    modules = []
    for module in MODULES:
        fields = []
        for spec in module["fields"]:
            item = {"name": spec["name"], "label": spec["label"], "kind": spec["kind"], "default": spec.get("default", "")}
            if "choices" in spec:
                item["choices"] = list(spec["choices"])
            fields.append(item)
        modules.append({"id": module["id"], "title": module["title"], "text": module["text"], "fields": fields})
    return {"ok": True, "modules": modules, "kits": list_kits(workspace) if workspace else []}


def build_kit(spec: dict) -> dict:
    try:
        language, name, blocks = _plan(spec)
        content = _render(language, name, blocks)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": True,
        "content": content,
        "name": name,
        "suffix": _SUFFIX[language],
        "language": language,
        "blocks": blocks,
        "message": f"Baukasten mit {len(blocks)} Modulen erzeugt.",
    }


def save_kit(workspace: Path, spec: dict) -> dict:
    try:
        language, name, blocks = _plan(spec)
        target = _kit_file(workspace, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps({"name": name, "language": language, "blocks": blocks}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "path": str(target), "name": name, "language": language, "blocks": blocks}


def load_kit(workspace: Path, name: str) -> dict:
    try:
        target = _kit_file(workspace, name)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    if not target.is_file():
        return {"ok": False, "error": "Baukasten nicht gefunden."}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"ok": False, "error": "Baukasten ist beschädigt."}
    if not isinstance(data, dict):
        return {"ok": False, "error": "Baukasten ist beschädigt."}
    try:
        language, kit_name, blocks = _plan(data)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "name": kit_name, "language": language, "blocks": blocks, "path": str(target)}


def list_kits(workspace: Path | None) -> list[dict]:
    if workspace is None:
        return []
    folder = Path(workspace) / "baukasten"
    items = []
    if not folder.is_dir():
        return items
    for path in sorted(folder.glob("*.json")):
        if not _IDENT.match(path.stem) and not re.match(r"^[A-Za-z][A-Za-z0-9_-]{0,48}$", path.stem):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            items.append({"name": path.stem, "language": str(data.get("language") or "")})
    return items


def _plan(spec: dict) -> tuple[str, str, list[dict]]:
    language = _LANG.get(str(spec.get("language") or "python").strip().lower(), "")
    if not language:
        raise ValueError("Sprache: python, powershell, shell oder batch.")
    name = safe_name(str(spec.get("name") or "Baukasten"), "Baukasten")
    raw = spec.get("blocks")
    if not isinstance(raw, list) or not raw:
        raise ValueError("Mindestens ein Modul setzen.")
    if len(raw) > 30:
        raise ValueError("Höchstens 30 Module.")
    known = {item["id"]: item for item in MODULES}
    blocks = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise ValueError("Modul ist ungültig.")
        module = known.get(str(entry.get("id") or ""))
        if module is None:
            raise ValueError("Unbekanntes Modul.")
        if language == "batch" and module["id"] not in _BATCH:
            raise ValueError(f"Modul {module['title']} gibt es für Batch nicht.")
        cleaned = {"id": module["id"]}
        for field in module["fields"]:
            value = entry.get(field["name"])
            if value is None or str(value) == "":
                value = field.get("default", "")
            text = str(value)
            if len(text) > 4000:
                raise ValueError(f"{field['label']} ist zu lang.")
            if field["kind"] == "ident":
                text = _ident(text, field["label"])
            elif field["kind"] == "choice" and text not in field["choices"]:
                raise ValueError(f"{field['label']}: Wert ist nicht erlaubt.")
            elif field["kind"] == "number":
                if not re.fullmatch(r"\d+(\.\d+)?", text.strip()):
                    raise ValueError(f"{field['label']} muss eine Zahl ab 0 sein.")
                if float(text) > 30:
                    raise ValueError("Pause höchstens 30 Sekunden.")
                text = text.strip()
            cleaned[field["name"]] = text
        blocks.append(cleaned)
    return language, name, blocks


def _render(language: str, name: str, blocks: list[dict]) -> str:
    script = _Script(language)
    titles = {item["id"]: item["title"] for item in MODULES}
    for index, block in enumerate(blocks, start=1):
        script.note(f"{index}. {titles[block['id']]}")
        _emit(script, block)
    return script.finish(name)


class _Script:
    def __init__(self, language: str) -> None:
        self.language = language
        self.known: set[str] = set()
        self.lines: list[str] = []
        self.notes: list[str] = []
        self.needs: set[str] = set()
        self.count = 0

    def add(self, *lines: str) -> None:
        self.lines.extend(lines)

    def note(self, text: str) -> None:
        self.notes.append(text)

    def define(self, name: str) -> None:
        self.known.add(name)

    def temp(self) -> str:
        self.count += 1
        return f"_shatu{self.count}"

    def finish(self, name: str) -> str:
        comment = "REM " if self.language == "batch" else "# "
        head = [comment + "Baukasten " + name + ", erzeugt von ShatuIDE."]
        head.extend(comment + note for note in self.notes)
        if self.language == "python":
            return _finish_python(head, self)
        if self.language == "powershell":
            return _finish_powershell(head, self)
        if self.language == "shell":
            return _finish_shell(head, self)
        return _finish_batch(head, self)


def _emit(script: _Script, block: dict) -> None:
    module = block["id"]
    language = script.language
    if language == "python":
        _py_block(script, module, block)
    elif language == "powershell":
        _ps_block(script, module, block)
    elif language == "shell":
        _sh_block(script, module, block)
    else:
        _bat_block(script, module, block)


def _pieces(text: str) -> list[tuple[str, str]]:
    parts: list[tuple[str, str]] = []
    pos = 0
    for match in _REF.finditer(text):
        if match.start() > pos:
            parts.append(("lit", text[pos : match.start()]))
        parts.append(("var", match.group(1)))
        pos = match.end()
    if pos < len(text):
        parts.append(("lit", text[pos:]))
    return parts or [("lit", "")]


def _require(script: _Script, text: str) -> None:
    for kind, value in _pieces(text):
        if kind == "var" and value not in script.known:
            raise ValueError(f"Variable {value} ist noch nicht gesetzt.")


def _columns(text: str) -> list[str]:
    return [part.strip() for part in text.split(";") if part.strip()]


def _py(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def _ps(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def _sh(text: str) -> str:
    return "'" + text.replace("'", "'\\''") + "'"


def _bat(text: str) -> str:
    return "".join(" " if char in "%&|<>" else char for char in text)


def _py_expr(script: _Script, text: str) -> str:
    _require(script, text)
    bits = []
    for kind, value in _pieces(text):
        bits.append(f"str({value})" if kind == "var" else _py(value))
    return " + ".join(bits)


def _ps_expr(script: _Script, text: str) -> str:
    _require(script, text)
    bits = []
    for kind, value in _pieces(text):
        bits.append(f"[string]${value}" if kind == "var" else _ps(value))
    return " + ".join(bits)


def _sh_printf(script: _Script, text: str) -> str:
    _require(script, text)
    parts = _pieces(text)
    fmt = "".join("%s" for _ in parts)
    args = " ".join(f'"${value}"' if kind == "var" else _sh(value) for kind, value in parts)
    return f"printf '{fmt}\\n' {args}"


def _num(script: _Script, text: str) -> str:
    raw = text.strip()
    if re.fullmatch(r"\{[A-Za-z_][A-Za-z0-9_]*\}", raw):
        name = raw[1:-1]
        if name not in script.known:
            raise ValueError(f"Variable {name} ist noch nicht gesetzt.")
        return name
    if _NUMBER.fullmatch(raw):
        return raw
    raise ValueError("Zahl oder {Variable} erwartet.")


def _sql(text: str) -> str:
    body = text.strip()
    if not body:
        raise ValueError("SQL fehlt.")
    stripped = body[:-1].strip() if body.endswith(";") else body
    if ";" in stripped or "\x00" in stripped:
        raise ValueError("Eine SQL-Anweisung je Modul.")
    return stripped


def _py_block(script: _Script, module: str, block: dict) -> None:
    ind = "    "
    if module == "eingabe":
        label = _py(block["frage"] + ": ")
        if block["art"] == "zahl":
            script.needs.add("zahl")
            script.add(f"{ind}{block['ziel']} = _zahl({label})")
        else:
            script.add(f"{ind}{block['ziel']} = input({label}).strip()")
        script.define(block["ziel"])
    elif module == "ausgabe":
        script.add(f"{ind}print({_py_expr(script, block['text'])})")
    elif module == "rechnen":
        left = _num(script, block["links"])
        right = _num(script, block["rechts"])
        op = _OPS[block["operator"]]
        temp = script.temp()
        script.add(f"{ind}{temp} = float({left}) {op} float({right})")
        script.add(f"{ind}{block['ziel']} = str(int({temp})) if {temp} == int({temp}) else str({temp})")
        script.define(block["ziel"])
    elif module == "text_bauen":
        parts = _columns(block["teile"]) or [""]
        joined = ", ".join(_py_expr(script, part) for part in parts)
        script.add(f"{ind}{block['ziel']} = {_py(block['trenner'])}.join([{joined}])")
        script.define(block["ziel"])
    elif module == "datei_lesen":
        script.needs.add("path")
        script.add(f"{ind}{block['ziel']} = Path({_py_expr(script, block['quelle'])}).read_text(encoding='utf-8')")
        script.define(block["ziel"])
    elif module == "datei_schreiben":
        script.needs.add("path")
        script.add(
            f"{ind}Path({_py_expr(script, block['datei'])}).write_text({_py_expr(script, block['inhalt'])} + '\\n', encoding='utf-8')"
        )
    elif module == "ordner":
        script.needs.add("path")
        temp = script.temp()
        script.add(f"{ind}{temp} = Path({_py_expr(script, block['pfad'])} or '.')")
        script.add(f"{ind}if not {temp}.is_dir():")
        script.add(f"{ind}    raise SystemExit('Ordner nicht gefunden: ' + str({temp}))")
        script.add(f"{ind}for _eintrag in sorted({temp}.iterdir()):")
        script.add(f"{ind}    print(_eintrag.name)")
    elif module == "csv_zeile":
        script.needs.add("csv")
        script.needs.add("path")
        columns = _columns(block["werte"]) or [""]
        values = ", ".join(_py_expr(script, part) for part in columns)
        handle = script.temp()
        script.add(f"{ind}with Path({_py_expr(script, block['datei'])}).open('a', newline='', encoding='utf-8') as {handle}:")
        script.add(f"{ind}    csv.writer({handle}).writerow([{values}])")
    elif module == "json_lesen":
        script.needs.add("json")
        script.needs.add("path")
        temp = script.temp()
        script.add(f"{ind}{temp} = json.loads(Path({_py_expr(script, block['datei'])}).read_text(encoding='utf-8'))")
        key = block["schluessel"].strip()
        if key:
            script.add(f"{ind}{block['ziel']} = {temp}[{_py(key)}]")
        else:
            script.add(f"{ind}{block['ziel']} = {temp}")
        script.define(block["ziel"])
    elif module == "sqlite":
        script.needs.add("sqlite")
        sql = _sql(block["sql"])
        con = script.temp()
        cur = script.temp()
        script.add(f"{ind}with sqlite3.connect({_py_expr(script, block['datei'])}) as {con}:")
        script.add(f"{ind}    {cur} = {con}.execute({_py(sql)})")
        script.add(f"{ind}    if {cur}.description:")
        script.add(f"{ind}        for _zeile in {cur}.fetchall():")
        script.add(f"{ind}            print('\\t'.join(str(_zelle) for _zelle in _zeile))")
        script.add(f"{ind}    else:")
        script.add(f"{ind}        {con}.commit()")
    elif module == "web":
        script.needs.add("web")
        script.add(f"{ind}with urlopen({_py_expr(script, block['adresse'])}, timeout=20) as _antwort:")
        script.add(f"{ind}    {block['ziel']} = _antwort.read(4000).decode('utf-8', errors='replace')")
        script.define(block["ziel"])
    elif module == "bedingung":
        if block["variable"] not in script.known:
            raise ValueError(f"Variable {block['variable']} ist noch nicht gesetzt.")
        cond = _py_condition(block)
        script.add(f"{ind}if {cond}:")
        script.add(f"{ind}    print({_py_expr(script, block['text'])})")
    elif module == "pause":
        script.needs.add("time")
        script.add(f"{ind}time.sleep({block['sekunden']})")


def _py_condition(block: dict) -> str:
    var = f"str({block['variable']})"
    wert = _py(block["wert"])
    if block["vergleich"] == "gleich":
        return f"{var} == {wert}"
    if block["vergleich"] == "enthaelt":
        return f"{wert} in {var}"
    if block["vergleich"] == "leer":
        return f"not {var}.strip()"
    return f"float({block['variable']}) > float({wert})"


def _ps_block(script: _Script, module: str, block: dict) -> None:
    if module == "eingabe":
        if block["art"] == "zahl":
            script.needs.add("zahl")
            script.add(f"${block['ziel']} = Read-Zahl {_ps(block['frage'])}")
        else:
            script.add(f"${block['ziel']} = (Read-Host {_ps(block['frage'])}).Trim()")
        script.define(block["ziel"])
    elif module == "ausgabe":
        script.add(f"Write-Output ({_ps_expr(script, block['text'])})")
    elif module == "rechnen":
        left = _ps_num(script, block["links"])
        right = _ps_num(script, block["rechts"])
        temp = script.temp()
        script.add(f"${temp} = {left} {block['operator']} {right}")
        script.add(f"if (${temp} -eq [math]::Floor(${temp})) {{ ${block['ziel']} = [string][long]${temp} }} else {{ ${block['ziel']} = [string]${temp} }}")
        script.define(block["ziel"])
    elif module == "text_bauen":
        parts = _columns(block["teile"]) or [""]
        joined = ", ".join(f"({_ps_expr(script, part)})" for part in parts)
        script.add(f"${block['ziel']} = (({joined}) -join {_ps(block['trenner'])})")
        script.define(block["ziel"])
    elif module == "datei_lesen":
        script.add(f"${block['ziel']} = Get-Content -LiteralPath ({_ps_expr(script, block['quelle'])}) -Raw")
        script.define(block["ziel"])
    elif module == "datei_schreiben":
        script.add(f"Set-Content -LiteralPath ({_ps_expr(script, block['datei'])}) -Value ({_ps_expr(script, block['inhalt'])}) -Encoding utf8")
    elif module == "ordner":
        script.add(f"Get-ChildItem -LiteralPath ({_ps_expr(script, block['pfad'])}) | ForEach-Object {{ $_.Name }}")
    elif module == "csv_zeile":
        columns = _columns(block["werte"]) or [""]
        pairs = []
        for index, part in enumerate(columns, start=1):
            pieces = _pieces(part)
            column = pieces[0][1] if len(pieces) == 1 and pieces[0][0] == "var" else f"Wert{index}"
            pairs.append(f"{column} = ({_ps_expr(script, part)})")
        handle = script.temp()
        script.add(f"${handle} = [pscustomobject]@{{ {'; '.join(pairs)} }}")
        path = _ps_expr(script, block["datei"])
        script.add(f"if (Test-Path -LiteralPath ({path})) {{")
        script.add(f"    ${handle} | Export-Csv -LiteralPath ({path}) -NoTypeInformation -Encoding utf8 -Append")
        script.add("} else {")
        script.add(f"    ${handle} | Export-Csv -LiteralPath ({path}) -NoTypeInformation -Encoding utf8")
        script.add("}")
    elif module == "json_lesen":
        script.needs.add("python")
        key = _py(block["schluessel"].strip())
        call = _python_json(key)
        script.add(f"${block['ziel']} = & python3 -c {_ps(call)} ({_ps_expr(script, block['datei'])})")
        script.define(block["ziel"])
    elif module == "sqlite":
        script.needs.add("python")
        sql = _sql(block["sql"])
        call = _python_sql()
        script.add(f"& python3 -c {_ps(call)} ({_ps_expr(script, block['datei'])}) {_ps(sql)}")
    elif module == "web":
        script.add(f"${block['ziel']} = (Invoke-WebRequest -Uri ({_ps_expr(script, block['adresse'])}) -UseBasicParsing -TimeoutSec 20).Content")
        script.add(f"if (${block['ziel']}.Length -gt 4000) {{ ${block['ziel']} = ${block['ziel']}.Substring(0, 4000) }}")
        script.define(block["ziel"])
    elif module == "bedingung":
        if block["variable"] not in script.known:
            raise ValueError(f"Variable {block['variable']} ist noch nicht gesetzt.")
        script.add(f"if ({_ps_condition(block)}) {{")
        script.add(f"    Write-Output ({_ps_expr(script, block['text'])})")
        script.add("}")
    elif module == "pause":
        script.add(f"Start-Sleep -Seconds {block['sekunden']}")


def _ps_num(script: _Script, text: str) -> str:
    token = _num(script, text)
    if _NUMBER.fullmatch(token):
        return f"[double]::Parse({_ps(token)}, [cultureinfo]::InvariantCulture)"
    return f"[double]${token}"


def _ps_condition(block: dict) -> str:
    var = f"[string]${block['variable']}"
    wert = _ps(block["wert"])
    if block["vergleich"] == "gleich":
        return f"{var} -eq {wert}"
    if block["vergleich"] == "enthaelt":
        return f"{var}.Contains({wert})"
    if block["vergleich"] == "leer":
        return f"[string]::IsNullOrWhiteSpace({var})"
    return f"[double]${block['variable']} -gt [double]::Parse({wert}, [cultureinfo]::InvariantCulture)"


def _sh_block(script: _Script, module: str, block: dict) -> None:
    if module == "eingabe":
        script.needs.add("ask")
        script.add(f"{block['ziel']}=$(ask {_sh(block['frage'])})")
        if block["art"] == "zahl":
            script.add(f"{block['ziel']}=${{{block['ziel']}//,/.}}")
        script.define(block["ziel"])
    elif module == "ausgabe":
        script.add(_sh_printf(script, block["text"]))
    elif module == "rechnen":
        left = _sh_num(script, block["links"])
        right = _sh_num(script, block["rechts"])
        op = block["operator"]
        script.add(
            f"{block['ziel']}=$(awk -v a={left} -v b={right} 'BEGIN {{ wert = a {op} b; if (wert == int(wert)) print int(wert); else print wert }}')"
        )
        script.define(block["ziel"])
    elif module == "text_bauen":
        parts = _columns(block["teile"]) or [""]
        script.add(_sh_join_simple(script, block["ziel"], parts, block["trenner"]))
        script.define(block["ziel"])
    elif module == "datei_lesen":
        script.add(f"{block['ziel']}=$(cat -- {_sh_word(script, block['quelle'])})")
        script.define(block["ziel"])
    elif module == "datei_schreiben":
        script.add(f"printf '%s\\n' {_sh_word(script, block['inhalt'])} > {_sh_word(script, block['datei'])}")
    elif module == "ordner":
        temp = script.temp()
        script.add(f"{temp}={_sh_word(script, block['pfad'])}")
        script.add(f'if [ -z "${temp}" ]; then {temp}=.; fi')
        script.add(f'if [ ! -d "${temp}" ]; then echo "Ordner nicht gefunden: ${temp}" >&2; exit 1; fi')
        script.add(f'find "${temp}" -mindepth 1 -maxdepth 1 -exec basename {{}} \\;')
    elif module == "csv_zeile":
        columns = _columns(block["werte"]) or [""]
        fmt = ",".join(["%s"] * len(columns))
        args = " ".join(_sh_word(script, part) for part in columns)
        script.add(f"printf '{fmt}\\n' {args} >> {_sh_word(script, block['datei'])}")
    elif module == "json_lesen":
        key = _sh(block["schluessel"].strip())
        script.add(f"{block['ziel']}=$(python3 -c {_sh(_python_json(_py(block['schluessel'].strip())))} {_sh_word(script, block['datei'])})")
        script.define(block["ziel"])
        del key
    elif module == "sqlite":
        sql = _sql(block["sql"])
        script.add(f"python3 -c {_sh(_python_sql())} {_sh_word(script, block['datei'])} {_sh(sql)}")
    elif module == "web":
        script.add(f"{block['ziel']}=$(curl -fsS --max-time 20 {_sh_word(script, block['adresse'])} | head -c 4000)")
        script.define(block["ziel"])
    elif module == "bedingung":
        if block["variable"] not in script.known:
            raise ValueError(f"Variable {block['variable']} ist noch nicht gesetzt.")
        script.add(_sh_condition(block))
        script.add(_sh_printf(script, block["text"]))
        script.add("fi")
    elif module == "pause":
        script.add(f"sleep {block['sekunden']}")


def _sh_num(script: _Script, text: str) -> str:
    token = _num(script, text)
    if _NUMBER.fullmatch(token):
        return _sh(token)
    return f'"${token}"'


def _sh_word(script: _Script, text: str) -> str:
    _require(script, text)
    parts = _pieces(text)
    if len(parts) == 1 and parts[0][0] == "lit":
        return _sh(parts[0][1])
    if len(parts) == 1 and parts[0][0] == "var":
        return f'"${parts[0][1]}"'
    temp = script.temp()
    fmt = "".join("%s" for _ in parts)
    args = " ".join(f'"${value}"' if kind == "var" else _sh(value) for kind, value in parts)
    script.add(f"{temp}=$(printf '{fmt}' {args})")
    return f'"${temp}"'


def _sh_join_simple(script: _Script, ziel: str, parts: list[str], trenner: str) -> str:
    bits = []
    for index, part in enumerate(parts):
        if index:
            bits.append(_sh(trenner))
        bits.append(_sh_word(script, part))
    fmt = "".join("%s" for _ in bits)
    return f"{ziel}=$(printf '{fmt}' {' '.join(bits)})"


def _sh_condition(block: dict) -> str:
    var = block["variable"]
    wert = _sh(block["wert"])
    if block["vergleich"] == "gleich":
        return f'if [ "${var}" = {wert} ]; then'
    if block["vergleich"] == "enthaelt":
        return f'if [[ "${var}" == *{wert}* ]]; then'
    if block["vergleich"] == "leer":
        return f'if [ -z "${{{var}// /}}" ]; then'
    return f"if awk -v a=\"${var}\" -v b={wert} 'BEGIN {{ exit !(a > b) }}'; then"


def _bat_block(script: _Script, module: str, block: dict) -> None:
    if module == "eingabe":
        script.add(f"set /p {block['ziel']}={_bat(block['frage'])}: ")
        script.define(block["ziel"])
    elif module == "ausgabe":
        script.add("echo " + _bat_text(script, block["text"]))
    elif module == "rechnen":
        left = _bat_num(script, block["links"])
        right = _bat_num(script, block["rechts"])
        if "." in left or "." in right:
            raise ValueError("Batch rechnet mit ganzen Zahlen.")
        script.add(f"set /a {block['ziel']}={left}{block['operator']}{right}")
        script.define(block["ziel"])
    elif module == "text_bauen":
        parts = _columns(block["teile"]) or [""]
        body = _bat(block["trenner"]).join(_bat_text(script, part) for part in parts)
        script.add(f"set {block['ziel']}={body}")
        script.define(block["ziel"])
    elif module == "datei_schreiben":
        script.add(f"(echo {_bat_text(script, block['inhalt'])})> \"{_bat_text(script, block['datei'])}\"")
    elif module == "ordner":
        pfad = _bat_text(script, block["pfad"]) or "."
        script.add(f"dir /b \"{pfad}\"")
    elif module == "bedingung":
        if block["variable"] not in script.known:
            raise ValueError(f"Variable {block['variable']} ist noch nicht gesetzt.")
        var = block["variable"]
        wert = _bat(block["wert"])
        if block["vergleich"] == "gleich":
            script.add(f"if \"%{var}%\"==\"{wert}\" echo {_bat_text(script, block['text'])}")
        elif block["vergleich"] == "leer":
            script.add(f"if \"%{var}%\"==\"\" echo {_bat_text(script, block['text'])}")
        elif block["vergleich"] == "enthaelt":
            script.add(f"echo %{var}% | findstr /C:\"{wert}\" >nul && echo {_bat_text(script, block['text'])}")
        else:
            script.add(f"if %{var}% GTR {wert or '0'} echo {_bat_text(script, block['text'])}")
    elif module == "pause":
        script.add(f"timeout /t {str(int(float(block['sekunden'])))} /nobreak >nul")


def _bat_text(script: _Script, text: str) -> str:
    _require(script, text)
    bits = []
    for kind, value in _pieces(text):
        bits.append(f"%{value}%" if kind == "var" else _bat(value))
    return "".join(bits)


def _bat_num(script: _Script, text: str) -> str:
    token = _num(script, text)
    if _NUMBER.fullmatch(token):
        return token
    return f"%{token}%"


def _python_json(key_literal: str) -> str:
    return (
        "import json,sys; data=json.load(open(sys.argv[1], encoding='utf-8')); "
        f"key={key_literal}; value=data if not key else data[key]; "
        "print(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))"
    )


def _python_sql() -> str:
    return (
        "import sqlite3,sys; con=sqlite3.connect(sys.argv[1]); cur=con.execute(sys.argv[2]); "
        "rows=cur.fetchall() if cur.description else []; "
        "con.commit() if not cur.description else None; "
        "[print('\\t'.join(str(cell) for cell in row)) for row in rows]"
    )


def _finish_python(head: list[str], script: _Script) -> str:
    lines = ["#!/usr/bin/env python3", *head, ""]
    if "csv" in script.needs:
        lines.append("import csv")
    if "json" in script.needs:
        lines.append("import json")
    if "sqlite" in script.needs:
        lines.append("import sqlite3")
    if "time" in script.needs:
        lines.append("import time")
    if "path" in script.needs:
        lines.append("from pathlib import Path")
    if "web" in script.needs:
        lines.append("from urllib.request import urlopen")
    if "zahl" in script.needs:
        lines += [
            "",
            "def _zahl(label: str) -> float:",
            "    while True:",
            "        raw = input(label).strip().replace(',', '.')",
            "        try:",
            "            return float(raw)",
            "        except ValueError:",
            "            print('Bitte eine Zahl eingeben.')",
        ]
    lines += ["", "def main() -> None:"]
    lines.extend(script.lines or ["    pass"])
    lines += ["", "", "if __name__ == '__main__':", "    main()", ""]
    return "\n".join(lines)


def _finish_powershell(head: list[str], script: _Script) -> str:
    lines = [*head, ""]
    if "zahl" in script.needs:
        lines += [
            "function Read-Zahl([string]$Label) {",
            "    while ($true) {",
            "        $raw = (Read-Host $Label).Trim().Replace(',', '.')",
            "        $value = 0.0",
            "        if ([double]::TryParse($raw, [Globalization.NumberStyles]::Float, [cultureinfo]::InvariantCulture, [ref]$value)) {",
            "            return $value",
            "        }",
            "        Write-Output 'Bitte eine Zahl eingeben.'",
            "    }",
            "}",
            "",
        ]
    lines.extend(script.lines)
    lines.append("")
    return "\n".join(lines)


def _finish_shell(head: list[str], script: _Script) -> str:
    lines = ["#!/usr/bin/env bash", *head, ""]
    if "ask" in script.needs:
        lines += [
            "ask() {",
            "    local value=\"\"",
            "    read -r -p \"$1: \" value",
            "    printf '%s' \"$value\"",
            "}",
            "",
        ]
    lines.extend(script.lines)
    lines.append("")
    return "\n".join(lines)


def _finish_batch(head: list[str], script: _Script) -> str:
    lines = ["@echo off", "setlocal", *head]
    lines.extend(script.lines)
    lines.append("")
    return "\n".join(lines)


def _ident(value: str, kind: str) -> str:
    text = value.strip()
    if not _IDENT.match(text) or text in keyword.kwlist:
        raise ValueError(f"{kind}: Buchstabe oder Unterstrich, danach Buchstaben oder Ziffern.")
    return text


def _kit_file(workspace: Path, name: str) -> Path:
    safe = safe_name(name, "Baukasten")
    root = Path(workspace).resolve()
    target = (root / "baukasten" / f"{safe}.json").resolve()
    if target == root or not inside(root, target):
        raise ValueError("Schreiben nur im geöffneten Workspace.")
    return target
