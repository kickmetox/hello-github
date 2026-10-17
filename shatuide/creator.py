"""Skript- und Datenbank-Erzeuger. Läuft ohne Sprachmodell; ein Modell ist optional."""

from __future__ import annotations

import json
import keyword
import re
import sqlite3
from pathlib import Path

from shatuide.paths import inside
from shatuide.studio import safe_name

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,40}$")
_LANG = {
    "python": "python",
    "py": "python",
    "powershell": "powershell",
    "ps1": "powershell",
    "pwsh": "powershell",
    "bash": "shell",
    "shell": "shell",
    "sh": "shell",
    "linux": "shell",
    "batch": "batch",
    "cmd": "batch",
    "bat": "batch",
}
_ACTION = {
    "print": "print",
    "ausgeben": "print",
    "ausgabe": "print",
    "sum": "sum",
    "summe": "sum",
    "addiere": "sum",
    "addieren": "sum",
    "rechnen": "sum",
    "list": "list",
    "ordner": "list",
    "verzeichnis": "list",
    "auflisten": "list",
    "fetch": "fetch",
    "http": "fetch",
    "https": "fetch",
    "url": "fetch",
    "webseite": "fetch",
    "csv": "csv",
    "json": "json",
    "write": "write",
    "speichern": "write",
    "speichere": "write",
    "protokoll": "write",
    "notiz": "write",
}
_SUFFIX = {"python": ".py", "powershell": ".ps1", "shell": ".sh", "batch": ".bat"}
_SQL_TYPE = {
    "sqlite": {"text": "TEXT", "int": "INTEGER", "real": "REAL", "bool": "INTEGER", "date": "TEXT", "blob": "BLOB"},
    "postgresql": {"text": "TEXT", "int": "INTEGER", "real": "DOUBLE PRECISION", "bool": "BOOLEAN", "date": "DATE", "blob": "BYTEA"},
    "mysql": {"text": "VARCHAR(255)", "int": "INT", "real": "DOUBLE", "bool": "TINYINT(1)", "date": "DATE", "blob": "BLOB"},
}
_TYPE_WORD = {
    "text": "text",
    "string": "text",
    "zeichen": "text",
    "int": "int",
    "integer": "int",
    "zahl": "int",
    "real": "real",
    "float": "real",
    "double": "real",
    "bool": "bool",
    "boolean": "bool",
    "date": "date",
    "datum": "date",
    "datetime": "date",
    "blob": "blob",
}
_PRIMARY = {"pk", "primary", "schlüssel", "schluessel"}
_REQUIRED = {"pflicht", "required", "notnull", "nn"}
_UNIQUE = {"unique", "eindeutig"}
_ACTIONS = ("print", "sum", "list", "fetch", "csv", "json", "write")


def infer_action(text: str) -> str:
    tokens = set(re.findall(r"[a-z0-9äöüß]+", (text or "").lower()))
    for action in ("json", "csv", "fetch", "list", "sum", "write"):
        if any(word in tokens and _ACTION[word] == action for word in _ACTION):
            return action
    return "print"


def parse_prompt(text: str) -> dict:
    language = ""
    name = ""
    action = ""
    purpose: list[str] = []
    questions: list[str] = []
    for raw in (text or "").replace("\r", "").split("\n"):
        line = raw.strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith(("sprache:", "language:")):
            language = _language(line.split(":", 1)[1])
            continue
        if lower.startswith("name:"):
            name = line.split(":", 1)[1].strip()
            continue
        if lower.startswith(("aktion:", "action:")):
            action = _action_name(line.split(":", 1)[1].strip().lower())
            continue
        if lower.startswith(("aufgabe:", "zweck:", "purpose:")):
            purpose.append(line.split(":", 1)[1].strip())
            continue
        if lower.startswith(("frage:", "eingabe:", "question:")):
            questions.append(line.split(":", 1)[1].strip())
            continue
        purpose.append(line)
    blob = " ".join(purpose)
    if not language:
        language = _language_in_text(blob)
    if not action:
        action = infer_action(blob)
    if not name:
        match = re.search(r"\bnamens\s+([A-Za-z][A-Za-z0-9_-]{0,48})", blob, re.I)
        name = match.group(1) if match else ""
    return {
        "language": language,
        "name": name,
        "action": action,
        "purpose": " ".join(part for part in purpose if part).strip(),
        "questions": questions,
    }


def build_script(spec: dict) -> dict:
    try:
        normal = normalize(spec)
        content = render(normal)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return _built(normal, content, "local", "Skript lokal aus der Abfrage erzeugt.")


def model_messages(spec: dict) -> dict:
    try:
        normal = normalize(spec)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    lines = [
        f"Sprache: {normal['language']}",
        f"Dateiname: {normal['name']}{normal['suffix']}",
        f"Aufgabe: {normal['purpose']}",
        f"Aktion: {normal['action']}",
        "Eingaben, die das Skript interaktiv abfragt:",
    ]
    for item in normal["questions"]:
        lines.append(f"- {item['name']}: {item['label']} ({item['kind']})")
    if normal["prompt"]:
        lines.append("")
        lines.append("Prompt:")
        lines.append(normal["prompt"])
    system = (
        "Du schreibst genau ein lauffähiges Skript für ShatuIDE. "
        "Antworte nur mit einem Markdown-Codeblock in der verlangten Sprache. "
        "Keine Erklärung davor oder danach. "
        "Das Skript fragt jede genannte Eingabe interaktiv ab und führt die Aufgabe aus."
    )
    return {
        "ok": True,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": "\n".join(lines)},
        ],
        "language": normal["language"],
        "name": normal["name"],
        "suffix": normal["suffix"],
    }


def script_from_model(spec: dict, answer: str) -> dict:
    try:
        normal = normalize(spec)
        content = extract_script(answer)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return _built(normal, content, "model", "Skript aus dem Sprachmodell übernommen.")


def extract_script(text: str) -> str:
    match = re.search(r"```[^\n]*\n(.*?)```", text or "", re.S)
    code = match.group(1) if match else (text or "")
    code = code.strip("\n")
    if not code.strip():
        raise ValueError("Das Modell hat kein Skript geliefert.")
    if len(code.encode("utf-8")) > 200_000:
        raise ValueError("Die Modellantwort ist zu lang.")
    return code + "\n"


def create_database(workspace: Path, spec: dict) -> dict:
    try:
        plan = _database_plan(spec)
        root = Path(workspace).resolve()
        target = _place(root, plan["path"] or _default_relative(plan["engine"], plan["name"]))
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    if plan["engine"] == "mongodb":
        return _write_mongo(root, target, plan)
    sql = _sql_script(plan["name"], plan["tables"], plan["engine"])
    if plan["engine"] == "sqlite":
        sql_path = target.with_suffix(".sql") if target.suffix else target.with_name(target.name + ".sql")
        try:
            _ensure_parent(root, sql_path)
            _create_sqlite(target, plan["tables"], bool(plan["replace"]))
            sql_path.write_text(sql, encoding="utf-8")
        except sqlite3.DatabaseError:
            return {"ok": False, "error": "Die Datei ist keine SQLite-Datenbank."}
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
        return {
            "ok": True,
            "engine": "sqlite",
            "path": str(sql_path),
            "database": str(target),
            "tables": [item["name"] for item in plan["tables"]],
            "sample": f"SELECT * FROM {plan['tables'][0]['name']} LIMIT 50;",
            "applied": True,
            "message": f"SQLite-Datenbank {target.name} mit {len(plan['tables'])} Tabellen angelegt.",
        }
    try:
        _ensure_parent(root, target)
        target.write_text(sql, encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    applied = False
    note = f"SQL für {plan['engine']} geschrieben."
    if plan["apply"]:
        if not plan["dsn"]:
            note += " Verbindungszeichenkette fehlt, der Server wurde nicht verändert."
        else:
            result = _apply_sql(plan["engine"], plan["dsn"], _statements(plan["tables"], plan["engine"]))
            applied = bool(result.get("ok"))
            if applied:
                note += " Die Tabellen wurden auf dem Server angelegt."
            else:
                note += " Anlegen fehlgeschlagen: " + str(result.get("error") or "unbekannt")
    else:
        note += " Anlegen auf dem Server ist aus."
    return {
        "ok": True,
        "engine": plan["engine"],
        "path": str(target),
        "database": "",
        "tables": [item["name"] for item in plan["tables"]],
        "sample": f"SELECT * FROM {plan['tables'][0]['name']} LIMIT 50;",
        "applied": applied,
        "message": note,
    }


def parse_schema(text: str) -> list[dict]:
    if len(text or "") > 100_000:
        raise ValueError("Das Schema ist zu lang.")
    tables: list[dict] = []
    current: dict | None = None

    def finish() -> None:
        nonlocal current
        if current is None:
            return
        if not current["columns"]:
            raise ValueError(f"Tabelle {current['name']} hat keine Spalte.")
        tables.append(current)
        current = None

    for raw in (text or "").replace("\r", "").split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            finish()
            continue
        if ":" in line:
            head, rest = line.split(":", 1)
            if rest.strip():
                finish()
                current = {"name": _ident(head, "Tabelle"), "columns": []}
                for part in rest.split(","):
                    if part.strip():
                        current["columns"].append(_column(part))
                finish()
                continue
        tokens = line.split()
        if len(tokens) == 1 or tokens[1].lower() not in _TYPE_WORD:
            finish()
            current = {"name": _ident(tokens[0], "Tabelle"), "columns": []}
            continue
        if current is None:
            raise ValueError("Spalte ohne Tabelle: " + line)
        current["columns"].append(_column(line))
    finish()
    if not tables:
        raise ValueError("Mindestens eine Tabelle mit einer Spalte angeben.")
    if len(tables) > 30:
        raise ValueError("Höchstens 30 Tabellen.")
    seen = set()
    for table in tables:
        key = table["name"].lower()
        if key in seen:
            raise ValueError(f"Tabelle {table['name']} ist doppelt.")
        if key.startswith("sqlite_"):
            raise ValueError("Tabellennamen dürfen nicht mit sqlite_ beginnen.")
        if len(table["columns"]) > 40:
            raise ValueError(f"Tabelle {table['name']} hat mehr als 40 Spalten.")
        seen.add(key)
        columns = set()
        primaries = 0
        for column in table["columns"]:
            column_key = column["name"].lower()
            if column_key in columns:
                raise ValueError(f"Spalte {column['name']} ist in {table['name']} doppelt.")
            columns.add(column_key)
            primaries += 1 if column["primary"] else 0
        if primaries > 1:
            raise ValueError(f"Tabelle {table['name']} hat mehr als einen Primärschlüssel.")
    return tables


def normalize(spec: dict) -> dict:
    prompt = str(spec.get("prompt") or "")
    if len(prompt) > 8000:
        raise ValueError("Der Prompt ist zu lang.")
    parsed = parse_prompt(prompt) if prompt.strip() else {}
    language = _language(str(spec.get("language") or parsed.get("language") or "python"))
    if not language:
        raise ValueError("Sprache: python, powershell, shell oder batch.")
    name = safe_name(str(spec.get("name") or parsed.get("name") or "Skript"), "Skript")
    chosen = spec.get("script_action")
    if chosen in (None, ""):
        chosen = spec.get("action_name")
    if chosen in (None, ""):
        chosen = spec.get("action")
        if str(chosen or "") == "script":
            chosen = ""
    action = _action_name(str(chosen or parsed.get("action") or "auto"))
    purpose = str(spec.get("purpose") or parsed.get("purpose") or prompt or "Erzeugtes Skript").strip()
    if len(purpose) > 2000:
        raise ValueError("Die Aufgabe ist zu lang.")
    if action == "auto":
        action = infer_action(purpose)
    raw_questions = spec.get("questions")
    if raw_questions in (None, "", []):
        raw_questions = parsed.get("questions") or []
    questions = _questions(action, raw_questions)
    return {
        "language": language,
        "name": name,
        "suffix": _SUFFIX[language],
        "action": action,
        "purpose": purpose or "Erzeugtes Skript",
        "prompt": prompt.strip(),
        "questions": questions,
    }


def render(spec: dict) -> str:
    language = spec["language"]
    if language == "python":
        return _python(spec)
    if language == "powershell":
        return _powershell(spec)
    if language == "shell":
        return _shell(spec)
    return _batch(spec)


def _built(spec: dict, content: str, source: str, message: str) -> dict:
    return {
        "ok": True,
        "content": content if content.endswith("\n") else content + "\n",
        "name": spec["name"],
        "suffix": spec["suffix"],
        "language": spec["language"],
        "action": spec["action"],
        "source": source,
        "message": message,
    }


def _language(value: str) -> str:
    return _LANG.get(value.strip().lower(), "")


def _language_in_text(text: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    for token in tokens:
        if token in _LANG:
            return _LANG[token]
    return ""


def _action_name(value: str) -> str:
    text = value.strip().lower()
    if text in {"", "auto", "erkennen"}:
        return "auto"
    mapped = _ACTION.get(text, "")
    if mapped not in _ACTIONS:
        raise ValueError("Aktion nicht bekannt.")
    return mapped


def _ident(value: str, kind: str) -> str:
    text = (value or "").strip()
    if not _IDENT.match(text):
        raise ValueError(f"{kind}: Buchstabe oder Unterstrich, danach Buchstaben oder Ziffern, höchstens 41 Zeichen.")
    if text in keyword.kwlist or text.lower() in {"select", "table", "from", "where", "drop", "create"}:
        raise ValueError(f"{kind} {text} ist ein Schlüsselwort.")
    return text


def _questions(action: str, raw) -> list[dict]:
    items: list[dict] = []
    if isinstance(raw, str):
        raw = [line for line in raw.splitlines() if line.strip()]
    if not isinstance(raw, list):
        raise ValueError("Abfragen müssen eine Liste oder ein Text sein.")
    for entry in raw:
        if isinstance(entry, str):
            items.append(_question_line(entry))
        elif isinstance(entry, dict):
            items.append({
                "name": _ident(str(entry.get("name") or ""), "Eingabe"),
                "label": str(entry.get("label") or entry.get("prompt") or entry.get("name") or "Eingabe").strip()[:200],
                "kind": "number" if str(entry.get("kind") or "") == "number" else "text",
            })
        else:
            raise ValueError("Abfrage ist ungültig.")
    if len(items) > 12:
        raise ValueError("Höchstens 12 Abfragen.")
    seen = set()
    for item in items:
        key = item["name"].lower()
        if key in seen:
            raise ValueError(f"Eingabe {item['name']} ist doppelt.")
        seen.add(key)
    if items:
        if action == "sum":
            for item in items:
                item["kind"] = "number"
        return items
    defaults = {
        "print": [("Text", "Text", "text")],
        "sum": [("Zahl1", "Zahl 1", "number"), ("Zahl2", "Zahl 2", "number")],
        "list": [("Pfad", "Ordner", "text")],
        "fetch": [("Url", "Adresse", "text")],
        "csv": [("Datei", "CSV-Datei", "text"), ("Name", "Name", "text"), ("Wert", "Wert", "text")],
        "json": [("Pfad", "JSON-Datei", "text")],
        "write": [("Datei", "Datei", "text"), ("Text", "Text", "text")],
    }
    return [{"name": name, "label": label, "kind": kind} for name, label, kind in defaults[action]]


def _question_line(line: str) -> dict:
    text = line.strip()
    if ":" in text:
        name, label = text.split(":", 1)
    else:
        parts = text.split(None, 1)
        name = parts[0]
        label = parts[1] if len(parts) > 1 else parts[0]
    return {"name": _ident(name, "Eingabe"), "label": label.strip()[:200] or name.strip(), "kind": "text"}


def _batch_label(value: str) -> str:
    return "".join(" " if char in "%&|<>" else char for char in value)


def _comments(language: str, purpose: str) -> str:
    prefix = "REM " if language == "batch" else "# "
    lines = ["Erzeugt von ShatuIDE."]
    for line in purpose.replace("\r", "").split("\n")[:30]:
        cleaned = line.replace("\x00", "")[:180]
        if language == "batch":
            cleaned = "".join(" " if char in "%&|<>" else char for char in cleaned)
        lines.append(cleaned)
    return "\n".join(prefix + line for line in lines)


def _py(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _ps(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _sh(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def _python(spec: dict) -> str:
    questions = spec["questions"]
    action = spec["action"]
    lines = ["#!/usr/bin/env python3", _comments("python", spec["purpose"]), ""]
    if action == "list":
        lines.append("from pathlib import Path")
    elif action == "fetch":
        lines.append("from urllib.request import urlopen")
    elif action == "csv":
        lines += ["import csv", "from pathlib import Path"]
    elif action == "json":
        lines += ["import json", "from pathlib import Path"]
    elif action == "write":
        lines.append("from pathlib import Path")
    if any(item["kind"] == "number" for item in questions):
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
    for item in questions:
        label = _py(item["label"] + ": ")
        if item["kind"] == "number":
            lines.append(f"    {item['name']} = _zahl({label})")
        else:
            lines.append(f"    {item['name']} = input({label}).strip()")
    lines.extend(_python_body(action, questions))
    lines += ["", "", "if __name__ == '__main__':", "    main()", ""]
    return "\n".join(lines)


def _python_body(action: str, questions: list[dict]) -> list[str]:
    first = questions[0]["name"]
    if action == "sum":
        return ["    print(" + " + ".join(item["name"] for item in questions) + ")"]
    if action == "list":
        return [
            f"    ordner = Path({first} or '.')",
            "    if not ordner.is_dir():",
            "        raise SystemExit('Ordner nicht gefunden: ' + str(ordner))",
            "    for eintrag in sorted(ordner.iterdir()):",
            "        print(eintrag.name)",
        ]
    if action == "fetch":
        return [
            f"    if not {first}:",
            "        raise SystemExit('Adresse fehlt.')",
            f"    with urlopen({first}, timeout=20) as antwort:",
            "        print(antwort.read(4000).decode('utf-8', errors='replace'))",
        ]
    if action == "csv":
        fields = questions[1:] or questions
        names = ", ".join(_py(item["name"]) for item in fields)
        values = ", ".join(item["name"] for item in fields)
        return [
            f"    ziel = Path({first} or 'daten.csv')",
            "    neu = not ziel.exists()",
            "    with ziel.open('a', newline='', encoding='utf-8') as handle:",
            "        writer = csv.writer(handle)",
            "        if neu:",
            f"            writer.writerow([{names}])",
            f"        writer.writerow([{values}])",
            "    print(ziel)",
        ]
    if action == "json":
        return [
            f"    datei = Path({first})",
            "    daten = json.loads(datei.read_text(encoding='utf-8'))",
            "    print(json.dumps(daten, ensure_ascii=False, indent=2))",
        ]
    if action == "write":
        text = questions[1]["name"] if len(questions) > 1 else first
        return [
            f"    ziel = Path({first} or 'notiz.txt')",
            f"    ziel.write_text({text} + '\\n', encoding='utf-8')",
            "    print(ziel)",
        ]
    return [f"    print({_py(item['label'] + ': ')} + {item['name']})" for item in questions]


def _powershell(spec: dict) -> str:
    questions = spec["questions"]
    action = spec["action"]
    lines = [_comments("powershell", spec["purpose"]), ""]
    if any(item["kind"] == "number" for item in questions):
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
    for item in questions:
        label = _ps(item["label"])
        if item["kind"] == "number":
            lines.append(f"${item['name']} = Read-Zahl {label}")
        else:
            lines.append(f"${item['name']} = (Read-Host {label}).Trim()")
    lines.extend(_powershell_body(action, questions))
    lines.append("")
    return "\n".join(lines)


def _powershell_body(action: str, questions: list[dict]) -> list[str]:
    first = "$" + questions[0]["name"]
    if action == "sum":
        return ["Write-Output (" + " + ".join("$" + item["name"] for item in questions) + ")"]
    if action == "list":
        return [
            f"if (-not {first}) {{ {first} = '.' }}",
            f"Get-ChildItem -LiteralPath {first} | ForEach-Object {{ $_.Name }}",
        ]
    if action == "fetch":
        return [
            f"if (-not {first}) {{ throw 'Adresse fehlt.' }}",
            f"$antwort = Invoke-WebRequest -Uri {first} -UseBasicParsing -TimeoutSec 20",
            "Write-Output $antwort.Content.Substring(0, [Math]::Min(4000, $antwort.Content.Length))",
        ]
    if action == "csv":
        fields = questions[1:] or questions
        pairs = "; ".join(f"{item['name']} = ${item['name']}" for item in fields)
        return [
            f"if (-not {first}) {{ {first} = 'daten.csv' }}",
            f"$zeile = [pscustomobject]@{{ {pairs} }}",
            f"if (Test-Path -LiteralPath {first}) {{",
            f"    $zeile | Export-Csv -LiteralPath {first} -NoTypeInformation -Encoding utf8 -Append",
            "} else {",
            f"    $zeile | Export-Csv -LiteralPath {first} -NoTypeInformation -Encoding utf8",
            "}",
            f"Write-Output {first}",
        ]
    if action == "json":
        return [f"Get-Content -LiteralPath {first} -Raw | ConvertFrom-Json | ConvertTo-Json -Depth 8"]
    if action == "write":
        text = "$" + (questions[1]["name"] if len(questions) > 1 else questions[0]["name"])
        return [
            f"if (-not {first}) {{ {first} = 'notiz.txt' }}",
            f"Set-Content -LiteralPath {first} -Value {text} -Encoding utf8",
            f"Write-Output {first}",
        ]
    return [f"Write-Output ({_ps(item['label'] + ': ')} + ${item['name']})" for item in questions]


def _shell(spec: dict) -> str:
    questions = spec["questions"]
    action = spec["action"]
    lines = ["#!/usr/bin/env bash", _comments("shell", spec["purpose"]), ""]
    lines += [
        "ask() {",
        "    local value=\"\"",
        "    read -r -p \"$1: \" value",
        "    printf '%s' \"$value\"",
        "}",
        "",
    ]
    for item in questions:
        lines.append(f"{item['name']}=$(ask {_sh(item['label'])})")
        if item["kind"] == "number":
            lines.append(f"{item['name']}=${{{item['name']}//,/.}}")
    lines.extend(_shell_body(action, questions))
    lines.append("")
    return "\n".join(lines)


def _shell_body(action: str, questions: list[dict]) -> list[str]:
    first = questions[0]["name"]
    if action == "sum":
        args = " ".join(f"-v {item['name']}=\"${item['name']}\"" for item in questions)
        expr = "+".join(item["name"] for item in questions)
        return [f"awk {args} 'BEGIN {{ print {expr} }}'"]
    if action == "list":
        return [
            f"ordner=\"${{{first}:-.}}\"",
            "if [ ! -d \"$ordner\" ]; then",
            "    echo \"Ordner nicht gefunden: $ordner\" >&2",
            "    exit 1",
            "fi",
            "find \"$ordner\" -mindepth 1 -maxdepth 1 -exec basename {} \\;",
        ]
    if action == "fetch":
        return [
            f"if [ -z \"${first}\" ]; then",
            "    echo 'Adresse fehlt.' >&2",
            "    exit 1",
            "fi",
            f"curl -fsS --max-time 20 \"${first}\" | head -c 4000",
            "printf '\\n'",
        ]
    if action == "csv":
        fields = questions[1:] or questions
        header = ",".join(item["name"] for item in fields)
        formats = ",".join(["%s"] * len(fields))
        args = " ".join(f"\"${item['name']}\"" for item in fields)
        return [
            f"ziel=\"${{{first}:-daten.csv}}\"",
            "if [ ! -f \"$ziel\" ]; then",
            f"    printf '%s\\n' {_sh(header)} > \"$ziel\"",
            "fi",
            f"printf '{formats}\\n' {args} >> \"$ziel\"",
            "printf '%s\\n' \"$ziel\"",
        ]
    if action == "json":
        return [
            "python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1], encoding=\"utf-8\")), ensure_ascii=False, indent=2))' "
            f"\"${first}\""
        ]
    if action == "write":
        text = questions[1]["name"] if len(questions) > 1 else first
        return [
            f"ziel=\"${{{first}:-notiz.txt}}\"",
            f"printf '%s\\n' \"${text}\" > \"$ziel\"",
            "printf '%s\\n' \"$ziel\"",
        ]
    return [f"printf '%s: %s\\n' {_sh(item['label'])} \"${item['name']}\"" for item in questions]


def _batch(spec: dict) -> str:
    questions = spec["questions"]
    action = spec["action"]
    lines = ["@echo off", "setlocal", _comments("batch", spec["purpose"])]
    for item in questions:
        label = "".join(" " if char in "%&|<>" else char for char in item["label"])
        lines.append(f"set /p {item['name']}={label}: ")
    lines.extend(_batch_body(action, questions))
    lines.append("")
    return "\n".join(lines)


def _batch_body(action: str, questions: list[dict]) -> list[str]:
    first = questions[0]["name"]
    if action == "sum":
        expr = "+".join(f"%{item['name']}%" for item in questions)
        return [f"set /a Summe={expr}", "echo %Summe%"]
    if action == "list":
        return [f"if \"%{first}%\"==\"\" set {first}=.", f"dir /b \"%{first}%\""]
    if action == "fetch":
        return [f"curl -fsS --max-time 20 \"%{first}%\""]
    if action == "csv":
        fields = questions[1:] or questions
        header = ",".join(item["name"] for item in fields)
        values = ",".join(f"%{item['name']}%" for item in fields)
        return [
            f"if \"%{first}%\"==\"\" set {first}=daten.csv",
            f"if not exist \"%{first}%\" echo {header}> \"%{first}%\"",
            f"echo {values}>> \"%{first}%\"",
            f"echo %{first}%",
        ]
    if action == "json":
        return [
            f"set SHATU_JSON=%{first}%",
            "powershell -NoProfile -Command \"Get-Content -LiteralPath $env:SHATU_JSON -Raw | ConvertFrom-Json | ConvertTo-Json -Depth 8\"",
        ]
    if action == "write":
        text = questions[1]["name"] if len(questions) > 1 else first
        return [
            f"if \"%{first}%\"==\"\" set {first}=notiz.txt",
            f"(echo %{text}%)> \"%{first}%\"",
            f"echo %{first}%",
        ]
    return [f"echo {_batch_label(item['label'])}: %{item['name']}%" for item in questions]


def _column(text: str) -> dict:
    tokens = text.replace(",", " ").split()
    if len(tokens) < 2:
        raise ValueError("Spalte braucht Name und Typ.")
    name = _ident(tokens[0], "Spalte")
    type_name = _TYPE_WORD.get(tokens[1].lower(), "")
    if not type_name:
        raise ValueError(f"Unbekannter Typ {tokens[1]}. Erlaubt: text, int, real, bool, date, blob.")
    flags = [token.lower() for token in tokens[2:]]
    if "not" in flags and "null" in flags:
        flags = [token for token in flags if token not in {"not", "null"}]
        flags.append("pflicht")
    unknown = [token for token in flags if token not in _PRIMARY | _REQUIRED | _UNIQUE]
    if unknown:
        raise ValueError("Unbekanntes Merkmal: " + ", ".join(unknown))
    primary = any(token in _PRIMARY for token in flags)
    return {
        "name": name,
        "type": type_name,
        "primary": primary,
        "required": primary or any(token in _REQUIRED for token in flags),
        "unique": any(token in _UNIQUE for token in flags),
    }


def _database_plan(spec: dict) -> dict:
    engine = str(spec.get("engine") or "sqlite").strip().lower()
    if engine == "mongo":
        engine = "mongodb"
    if engine not in {"sqlite", "postgresql", "mysql", "mongodb"}:
        raise ValueError("Engine: sqlite, postgresql, mysql oder mongodb.")
    name = safe_name(str(spec.get("name") or "Datenbank"), "Datenbank")
    tables = spec.get("tables")
    if isinstance(tables, str) or tables is None:
        tables = parse_schema(str(spec.get("schema") or tables or ""))
    elif isinstance(tables, list):
        tables = parse_schema(_schema_from_tables(tables))
    else:
        raise ValueError("Tabellen fehlen.")
    return {
        "engine": engine,
        "name": name,
        "tables": tables,
        "path": str(spec.get("path") or "").strip(),
        "dsn": str(spec.get("dsn") or spec.get("uri") or "").strip(),
        "apply": bool(spec.get("apply")),
        "replace": bool(spec.get("replace")),
    }


def _schema_from_tables(tables: list) -> str:
    lines = []
    for table in tables:
        if not isinstance(table, dict):
            raise ValueError("Tabelle ist ungültig.")
        lines.append(str(table.get("name") or ""))
        for column in table.get("columns") or []:
            if isinstance(column, str):
                lines.append(column)
            elif isinstance(column, dict):
                flags = []
                if column.get("primary"):
                    flags.append("pk")
                if column.get("required"):
                    flags.append("pflicht")
                if column.get("unique"):
                    flags.append("unique")
                lines.append(" ".join([str(column.get("name") or ""), str(column.get("type") or "text"), *flags]))
        lines.append("")
    return "\n".join(lines)


def _default_relative(engine: str, name: str) -> str:
    if engine == "sqlite":
        return f"datenbanken/{name}.sqlite"
    if engine == "mongodb":
        return f"datenbanken/{name}.schema.json"
    return f"datenbanken/{name}.sql"


def _place(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    if resolved == root or not inside(root, resolved):
        raise ValueError("Schreiben nur im geöffneten Workspace.")
    if resolved.exists() and resolved.is_dir():
        raise ValueError("Der Pfad ist ein Ordner.")
    return resolved


def _ensure_parent(root: Path, path: Path) -> None:
    parent = path.parent
    if parent != root and not inside(root, parent):
        raise ValueError("Schreiben nur im geöffneten Workspace.")
    parent.mkdir(parents=True, exist_ok=True)


def _column_sql(column: dict, engine: str) -> str:
    sql_type = _SQL_TYPE[engine][column["type"]]
    if engine == "sqlite" and column["primary"] and column["type"] == "int":
        parts = [column["name"], "INTEGER", "PRIMARY KEY"]
    else:
        parts = [column["name"], sql_type]
        if column["primary"]:
            parts.append("PRIMARY KEY")
    if column["required"] and "PRIMARY KEY" not in parts:
        parts.append("NOT NULL")
    if column["unique"] and not column["primary"]:
        parts.append("UNIQUE")
    return " ".join(parts)


def _statements(tables: list[dict], engine: str) -> list[str]:
    statements = []
    for table in tables:
        columns = ",\n    ".join(_column_sql(column, engine) for column in table["columns"])
        statements.append(f"CREATE TABLE {table['name']} (\n    {columns}\n);")
    return statements


def _sql_script(name: str, tables: list[dict], engine: str) -> str:
    body = "\n\n".join(_statements(tables, engine))
    return f"-- Datenbank {name}, erzeugt von ShatuIDE ({engine})\n\n{body}\n"


def _create_sqlite(path: Path, tables: list[dict], replace: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as con:
        existing = {
            row[0]
            for row in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
        }
        for table in tables:
            if table["name"] in existing and not replace:
                raise ValueError(f"Tabelle {table['name']} existiert bereits.")
        if replace:
            for table in tables:
                con.execute(f"DROP TABLE IF EXISTS {table['name']}")
        for statement in _statements(tables, "sqlite"):
            con.execute(statement)
        con.commit()


def _apply_sql(engine: str, dsn: str, statements: list[str]) -> dict:
    from shatuide import database

    for statement in statements:
        result = database.query(engine, sql=statement, dsn=dsn)
        if not result.get("ok"):
            return result
    return {"ok": True}


def _write_mongo(root: Path, target: Path, plan: dict) -> dict:
    if target.suffix != ".json":
        target = target.with_suffix(".schema.json") if target.suffix == "" else target
    schema = {
        "database": plan["name"],
        "collections": [
            {
                "name": table["name"],
                "fields": [
                    {
                        "name": column["name"],
                        "type": column["type"],
                        "required": column["required"],
                        "primary": column["primary"],
                    }
                    for column in table["columns"]
                ],
            }
            for table in plan["tables"]
        ],
    }
    script_path = target.with_name(plan["name"] + ".mongo.py")
    schema_name = json.dumps(target.name, ensure_ascii=False)
    script = (
        "# MongoDB-Datenbank anlegen. Braucht pymongo und eine URI.\n"
        "import json\nimport sys\nfrom pathlib import Path\n\n"
        "try:\n    import pymongo\nexcept ImportError:\n"
        "    raise SystemExit(\"Treiber fehlt. Installiere das Paket pymongo.\")\n\n"
        "uri = sys.argv[1] if len(sys.argv) > 1 else \"\"\n"
        "if not uri:\n    raise SystemExit(\"URI fehlt. Aufruf: python dieses_skript mongodb://host\")\n"
        f"schema = json.loads((Path(__file__).resolve().parent / {schema_name}).read_text(encoding=\"utf-8\"))\n"
        "client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=4000)\n"
        "datenbank = client[schema[\"database\"]]\n"
        "vorhanden = set(datenbank.list_collection_names())\n"
        "for sammlung in schema[\"collections\"]:\n"
        "    if sammlung[\"name\"] not in vorhanden:\n"
        "        datenbank.create_collection(sammlung[\"name\"])\n"
        "    print(sammlung[\"name\"])\n"
    )
    try:
        _ensure_parent(root, target)
        _ensure_parent(root, script_path)
        target.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        script_path.write_text(script, encoding="utf-8")
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    applied = False
    note = "Schema und Python-Skript geschrieben."
    if plan["apply"]:
        if not plan["dsn"]:
            note += " URI fehlt, der Server wurde nicht verändert."
        else:
            result = _apply_mongo(plan["dsn"], plan["name"], plan["tables"])
            applied = bool(result.get("ok"))
            note += " Sammlungen angelegt." if applied else " Anlegen fehlgeschlagen: " + str(result.get("error") or "")
    else:
        note += " Anlegen auf dem Server braucht pymongo und eine URI."
    return {
        "ok": True,
        "engine": "mongodb",
        "path": str(target),
        "script": str(script_path),
        "database": "",
        "tables": [item["name"] for item in plan["tables"]],
        "sample": "",
        "applied": applied,
        "message": note,
    }


def _apply_mongo(uri: str, database_name: str, tables: list[dict]) -> dict:
    try:
        import pymongo
    except ImportError:
        return {"ok": False, "error": "Treiber fehlt. Installiere das Paket 'pymongo'."}
    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=4000)
        remote = client[database_name]
        present = set(remote.list_collection_names())
        for table in tables:
            if table["name"] not in present:
                remote.create_collection(table["name"])
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
