"""Kontextsensitive Vorschläge. Jedi wird benutzt, sobald es installiert ist."""

from __future__ import annotations

import ast
import builtins
import keyword
from typing import Iterable

from shatuide.analysis import definitions
from shatuide.snippets import matching

_ATTRS = {
    "str": [name for name in dir(str) if not name.startswith("_")],
    "list": [name for name in dir(list) if not name.startswith("_")],
    "dict": [name for name in dir(dict) if not name.startswith("_")],
    "set": [name for name in dir(set) if not name.startswith("_")],
    "tuple": [name for name in dir(tuple) if not name.startswith("_")],
    "int": [name for name in dir(int) if not name.startswith("_")],
    "float": [name for name in dir(float) if not name.startswith("_")],
    "bytes": [name for name in dir(bytes) if not name.startswith("_")],
    "path": [name for name in dir(__import__("pathlib").Path) if not name.startswith("_")],
}

_MODULES = {
    "os": ["path", "getcwd", "listdir", "environ", "makedirs", "remove", "rename", "walk", "name", "sep"],
    "sys": ["argv", "path", "exit", "stdin", "stdout", "stderr", "version", "executable", "modules", "platform"],
    "json": ["dumps", "loads", "dump", "load", "JSONDecodeError"],
    "re": ["compile", "search", "match", "fullmatch", "findall", "sub", "split", "escape", "IGNORECASE"],
    "math": ["sqrt", "floor", "ceil", "pow", "log", "sin", "cos", "pi", "inf"],
    "pathlib": ["Path", "PurePath", "PurePosixPath", "PureWindowsPath"],
    "datetime": ["date", "datetime", "time", "timedelta", "timezone"],
    "subprocess": ["run", "Popen", "PIPE", "STDOUT", "CalledProcessError"],
    "typing": ["Any", "Optional", "Union", "List", "Dict", "Tuple", "Callable", "Iterable", "Iterator"],
    "collections": ["deque", "Counter", "defaultdict", "OrderedDict", "namedtuple"],
    "itertools": ["chain", "islice", "groupby", "product", "permutations", "combinations", "count", "cycle"],
    "functools": ["lru_cache", "partial", "wraps", "reduce", "cache"],
    "dataclasses": ["dataclass", "field", "asdict", "astuple"],
    "enum": ["Enum", "IntEnum", "auto", "unique"],
    "argparse": ["ArgumentParser", "Namespace"],
    "logging": ["getLogger", "basicConfig", "DEBUG", "INFO", "WARNING", "ERROR"],
    "unittest": ["TestCase", "main", "skip", "expectedFailure"],
    "sqlite3": ["connect", "Row", "Connection", "Cursor"],
    "csv": ["reader", "writer", "DictReader", "DictWriter"],
    "hashlib": ["md5", "sha1", "sha256", "sha512"],
    "random": ["random", "randint", "choice", "shuffle", "seed", "uniform"],
    "textwrap": ["dedent", "indent", "fill", "shorten"],
    "shutil": ["copy", "copy2", "move", "rmtree", "which", "disk_usage"],
    "time": ["time", "sleep", "strftime", "localtime", "perf_counter"],
    "urllib": ["request", "parse", "error"],
}

_FRAMEWORK = [
    "Flask",
    "FastAPI",
    "APIRouter",
    "Request",
    "Response",
    "HTTPException",
    "Depends",
    "render",
    "redirect",
    "models",
    "path",
    "include",
    "JsonResponse",
    "QuerySet",
]


def _prefix(source: str, line: int, col: int) -> tuple[str, str, str | None]:
    rows = source.splitlines()
    if not rows or line < 1 or line > len(rows):
        return "", "", None
    text = rows[line - 1]
    col = max(0, min(col, len(text)))
    start = col
    while start > 0 and (text[start - 1].isalnum() or text[start - 1] in "._"):
        start -= 1
    token = text[start:col]
    if "." in token:
        receiver, _, partial = token.rpartition(".")
        return token, partial, receiver or None
    return token, token, None


def _assigned_types(source: str) -> dict[str, str]:
    types: dict[str, str] = {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return types
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = node.value
            if isinstance(value, ast.Constant):
                if isinstance(value.value, str):
                    types[node.targets[0].id] = "str"
                elif isinstance(value.value, bool):
                    types[node.targets[0].id] = "int"
                elif isinstance(value.value, int):
                    types[node.targets[0].id] = "int"
                elif isinstance(value.value, float):
                    types[node.targets[0].id] = "float"
            elif isinstance(value, ast.List):
                types[node.targets[0].id] = "list"
            elif isinstance(value, ast.Dict):
                types[node.targets[0].id] = "dict"
            elif isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "Path":
                types[node.targets[0].id] = "path"
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and isinstance(node.annotation, ast.Name):
            mapping = {"str": "str", "int": "int", "float": "float", "list": "list", "dict": "dict", "bytes": "bytes"}
            if node.annotation.id in mapping:
                types[node.target.id] = mapping[node.annotation.id]
    return types


def _imports(source: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return mapping
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mapping[alias.asname or alias.name.split(".")[0]] = alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                if alias.name == "*":
                    continue
                mapping[alias.asname or alias.name] = node.module.split(".")[0]
    return mapping


def _jedi(source: str, line: int, col: int) -> list[dict] | None:
    try:
        import jedi
    except Exception:
        return None
    try:
        script = jedi.Script(source)
        completions = script.complete(line, col)
    except Exception:
        return None
    items = []
    for comp in completions[:80]:
        items.append(
            {
                "label": comp.name,
                "kind": comp.type or "name",
                "insert": comp.name,
                "detail": comp.description or "",
            }
        )
    return items


def _local_names(source: str) -> list[str]:
    names = {item["name"] for item in definitions(source)}
    names.update(dir(builtins))
    names.update(keyword.kwlist)
    return sorted(names)


def completions(
    source: str,
    line: int,
    col: int,
    project_names: Iterable[str] | None = None,
) -> list[dict]:
    jedi_items = _jedi(source, line, col)
    if jedi_items:
        return jedi_items
    _token, partial, receiver = _prefix(source, line, col)
    items: list[dict] = []
    seen: set[str] = set()

    def add(label: str, kind: str, insert: str | None = None, detail: str = "") -> None:
        if not label.startswith(partial):
            return
        if label in seen:
            return
        seen.add(label)
        items.append({"label": label, "kind": kind, "insert": insert or label, "detail": detail})

    if receiver:
        types = _assigned_types(source)
        imports = _imports(source)
        pool: list[str] = []
        if receiver in types and types[receiver] in _ATTRS:
            pool = _ATTRS[types[receiver]]
        elif receiver in _MODULES:
            pool = _MODULES[receiver]
        elif receiver in imports and imports[receiver] in _MODULES:
            pool = _MODULES[imports[receiver]]
        elif receiver in {"app", "router"}:
            pool = ["get", "post", "put", "delete", "route", "include_router", "add_api_route"]
        for name in pool:
            add(name, "attribute", detail=receiver)
        items.sort(key=lambda item: item["label"])
        return items[:80]

    for snippet in matching(partial):
        add(snippet["trigger"], "snippet", snippet["code"], snippet["detail"])
    for name in keyword.kwlist:
        add(name, "keyword")
    for name in _local_names(source):
        add(name, "name")
    for name in project_names or []:
        add(name, "symbol")
    for name in _FRAMEWORK:
        add(name, "framework")
    items.sort(key=lambda item: ({"snippet": 0, "keyword": 1, "name": 2}.get(item["kind"], 3), item["label"]))
    return items[:80]
