"""Linting, Gliederung, Type Hints, TODOs, Dubletten, Gehe-zu-Definition."""

from __future__ import annotations

import ast
import builtins
import io
import re
import tokenize
from typing import Iterable

from shatuide.paths import SKIP_DIRS, TEXT_SUFFIXES

BUILTIN_NAMES = set(dir(builtins))
TODO_RE = re.compile(r"(?i)#\s*(TODO|FIXME|XXX|HACK)\b[:\-]?\s*(.*)$")
LINE_LIMIT = 88


def _problem(
    line: int,
    message: str,
    severity: str = "warning",
    code: str = "W000",
    col: int = 0,
    end_line: int | None = None,
    end_col: int | None = None,
) -> dict:
    return {
        "line": line or 1,
        "col": col or 0,
        "end_line": end_line or line or 1,
        "end_col": end_col or 0,
        "severity": severity,
        "message": message,
        "code": code,
    }


def _target_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        names: list[str] = []
        for elt in node.elts:
            names.extend(_target_names(elt))
        return names
    if isinstance(node, ast.Starred):
        return _target_names(node.value)
    return []


def _import_names(stmt: ast.stmt) -> list[str]:
    names: list[str] = []
    if isinstance(stmt, ast.Import):
        for alias in stmt.names:
            names.append(alias.asname or alias.name.split(".")[0])
    elif isinstance(stmt, ast.ImportFrom):
        for alias in stmt.names:
            if alias.name == "*":
                names.append("*")
            else:
                names.append(alias.asname or alias.name)
    return names


def _collect_assigned(stmts: Iterable[ast.stmt], bag: set[str]) -> bool:
    """Sammelt zugewiesene Namen. Gibt True zurück, wenn ein Stern-Import vorkommt."""
    star = False
    for stmt in stmts:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bag.add(stmt.name)
            if isinstance(stmt, ast.ClassDef):
                star = _collect_assigned(stmt.body, bag) or star
            continue
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            imported = _import_names(stmt)
            if "*" in imported:
                star = True
            bag.update(name for name in imported if name != "*")
            continue
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                bag.update(_target_names(target))
        elif isinstance(stmt, ast.AnnAssign):
            bag.update(_target_names(stmt.target))
        elif isinstance(stmt, ast.AugAssign):
            bag.update(_target_names(stmt.target))
        elif isinstance(stmt, ast.NamedExpr):
            bag.update(_target_names(stmt.target))
        elif isinstance(stmt, (ast.For, ast.AsyncFor)):
            bag.update(_target_names(stmt.target))
            star = _collect_assigned(stmt.body, bag) or star
            star = _collect_assigned(stmt.orelse, bag) or star
        elif isinstance(stmt, ast.While):
            star = _collect_assigned(stmt.body, bag) or star
            star = _collect_assigned(stmt.orelse, bag) or star
        elif isinstance(stmt, ast.If):
            star = _collect_assigned(stmt.body, bag) or star
            star = _collect_assigned(stmt.orelse, bag) or star
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            for item in stmt.items:
                if item.optional_vars is not None:
                    bag.update(_target_names(item.optional_vars))
            star = _collect_assigned(stmt.body, bag) or star
        elif isinstance(stmt, ast.Try):
            for handler in stmt.handlers:
                if handler.name:
                    bag.add(handler.name)
                star = _collect_assigned(handler.body, bag) or star
            star = _collect_assigned(stmt.body, bag) or star
            star = _collect_assigned(stmt.orelse, bag) or star
            star = _collect_assigned(stmt.finalbody, bag) or star
        elif isinstance(stmt, ast.Match):
            for case in stmt.cases:
                bag.update(_pattern_names(case.pattern))
                star = _collect_assigned(case.body, bag) or star
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bag.add(stmt.name)
    return star


def _pattern_names(pattern: ast.AST) -> list[str]:
    names: list[str] = []
    if isinstance(pattern, ast.MatchAs):
        if pattern.name:
            names.append(pattern.name)
        if pattern.pattern is not None:
            names.extend(_pattern_names(pattern.pattern))
    elif isinstance(pattern, ast.MatchMapping):
        for inner in pattern.patterns:
            names.extend(_pattern_names(inner))
        if pattern.rest:
            names.append(pattern.rest)
    elif isinstance(pattern, (ast.MatchSequence, ast.MatchOr, ast.MatchClass)):
        children = getattr(pattern, "patterns", None) or []
        for inner in children:
            names.extend(_pattern_names(inner))
    elif isinstance(pattern, ast.MatchStar) and pattern.name:
        names.append(pattern.name)
    return names


def _arg_names(node: ast.AST) -> set[str]:
    args = getattr(node, "args", None)
    if args is None:
        return set()
    names = {arg.arg for arg in [*args.args, *args.posonlyargs, *args.kwonlyargs]}
    if args.vararg:
        names.add(args.vararg.arg)
    if args.kwarg:
        names.add(args.kwarg.arg)
    return names


class _UndefinedVisitor(ast.NodeVisitor):
    def __init__(self, module_names: set[str]):
        self.scopes: list[set[str]] = [set(module_names) | BUILTIN_NAMES]
        self.problems: list[dict] = []

    def _defined(self, name: str) -> bool:
        return any(name in scope for scope in self.scopes)

    def _push_function(self, node: ast.AST) -> None:
        local: set[str] = set(_arg_names(node))
        _collect_assigned(getattr(node, "body", []), local)
        self.scopes.append(local)
        for stmt in getattr(node, "body", []):
            self.visit(stmt)
        self.scopes.pop()

    def _visit_signature(self, node: ast.AST) -> None:
        for deco in getattr(node, "decorator_list", []):
            self.visit(deco)
        returns = getattr(node, "returns", None)
        if returns is not None:
            self.visit(returns)
        args = getattr(node, "args", None)
        if args is None:
            return
        for arg in [*args.args, *args.posonlyargs, *args.kwonlyargs]:
            if arg.annotation is not None:
                self.visit(arg.annotation)
        for default in [*args.defaults, *args.kw_defaults]:
            if default is not None:
                self.visit(default)
        if args.vararg and args.vararg.annotation is not None:
            self.visit(args.vararg.annotation)
        if args.kwarg and args.kwarg.annotation is not None:
            self.visit(args.kwarg.annotation)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.scopes[-1].add(node.name)
        self._visit_signature(node)
        self._push_function(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scopes[-1].add(node.name)
        for base in node.bases:
            self.visit(base)
        for deco in node.decorator_list:
            self.visit(deco)
        local: set[str] = set()
        _collect_assigned(node.body, local)
        self.scopes.append(local)
        for stmt in node.body:
            self.visit(stmt)
        self.scopes.pop()

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self.scopes.append(set(_arg_names(node)))
        self.visit(node.body)
        self.scopes.pop()

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._comp(node)

    visit_SetComp = visit_ListComp
    visit_DictComp = visit_ListComp
    visit_GeneratorExp = visit_ListComp

    def _comp(self, node: ast.AST) -> None:
        names: set[str] = set()
        for gen in getattr(node, "generators", []):
            names.update(_target_names(gen.target))
        self.scopes.append(names)
        self.generic_visit(node)
        self.scopes.pop()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load) and not self._defined(node.id):
            self.problems.append(
                _problem(
                    node.lineno,
                    f"Name '{node.id}' ist nicht definiert",
                    "warning",
                    "F821",
                    node.col_offset,
                    node.end_lineno,
                    node.end_col_offset,
                )
            )


def _unused_imports(tree: ast.AST) -> list[dict]:
    imported: list[tuple[str, int, int]] = []

    class Collector(ast.NodeVisitor):
        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                imported.append((alias.asname or alias.name.split(".")[0], node.lineno, node.col_offset))

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            if node.module == "__future__":
                return
            for alias in node.names:
                if alias.name == "*":
                    continue
                imported.append((alias.asname or alias.name, node.lineno, node.col_offset))

    class Used(ast.NodeVisitor):
        def __init__(self) -> None:
            self.names: set[str] = set()

        def visit_Import(self, node: ast.Import) -> None:
            return

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            return

        def visit_Name(self, node: ast.Name) -> None:
            if isinstance(node.ctx, ast.Load):
                self.names.add(node.id)

    Collector().visit(tree)
    used = Used()
    used.visit(tree)
    problems = []
    for name, line, col in imported:
        if name not in used.names:
            problems.append(_problem(line, f"Import '{name}' wird nicht verwendet", "warning", "F401", col))
    return problems


def _ann_base(node: ast.AST | None) -> str | tuple | None:
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.split("[", 1)[0].strip()
    if isinstance(node, ast.Subscript):
        return _ann_base(node.value)
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return (_ann_base(node.left), _ann_base(node.right))
    return None


def _literal_type(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant):
        if node.value is None:
            return "None"
        if isinstance(node.value, bool):
            return "bool"
        if isinstance(node.value, int):
            return "int"
        if isinstance(node.value, float):
            return "float"
        if isinstance(node.value, str):
            return "str"
        return None
    return {
        ast.List: "list",
        ast.Dict: "dict",
        ast.Set: "set",
        ast.Tuple: "tuple",
    }.get(type(node))


def _compatible(ann: str | tuple | None, value_type: str | None) -> bool:
    if ann is None or value_type is None:
        return True
    if isinstance(ann, tuple):
        return any(_compatible(part, value_type) for part in ann if part is not None)
    if ann in {"Any", "object"}:
        return True
    if value_type == "None":
        return ann in {"None", "NoneType"}
    if ann == "float" and value_type == "int":
        return True
    if ann == "bool" and value_type == "int":
        return False
    return ann == value_type


def _type_problems(tree: ast.AST) -> list[dict]:
    problems: list[dict] = []
    functions: dict[str, list] = {}
    returns: dict[str, str | tuple | None] = {}

    for node in tree.body if isinstance(tree, ast.Module) else []:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            anns = []
            for arg in [*node.args.args, *node.args.posonlyargs]:
                anns.append(_ann_base(arg.annotation))
            functions[node.name] = anns
            returns[node.name] = _ann_base(node.returns)

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.stack: list[str | tuple | None] = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.stack.append(_ann_base(node.returns))
            self.generic_visit(node)
            self.stack.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            if node.value is not None:
                actual = _literal_type(node.value)
                ann = _ann_base(node.annotation)
                if actual and not _compatible(ann, actual):
                    problems.append(
                        _problem(
                            node.lineno,
                            f"Typkonflikt: erwartet {ann}, Literal ist {actual}",
                            "warning",
                            "TYPE",
                            node.col_offset,
                        )
                    )
            self.generic_visit(node)

        def visit_Return(self, node: ast.Return) -> None:
            if node.value is not None and self.stack:
                actual = _literal_type(node.value)
                ann = self.stack[-1]
                if actual and not _compatible(ann, actual):
                    problems.append(
                        _problem(
                            node.lineno,
                            f"Rückgabetyp: erwartet {ann}, Literal ist {actual}",
                            "warning",
                            "TYPE",
                            node.col_offset,
                        )
                    )
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Name) and node.func.id in functions:
                anns = functions[node.func.id]
                for ann, arg in zip(anns, node.args):
                    actual = _literal_type(arg)
                    if actual and not _compatible(ann, actual):
                        problems.append(
                            _problem(
                                arg.lineno,
                                f"Argumenttyp: erwartet {ann}, Literal ist {actual}",
                                "warning",
                                "TYPE",
                                arg.col_offset,
                            )
                        )
            self.generic_visit(node)

    Visitor().visit(tree)
    return problems


def _style_problems(source: str) -> list[dict]:
    problems: list[dict] = []
    lines = source.splitlines()
    saw_tab = False
    saw_space_indent = False
    for index, line in enumerate(lines, start=1):
        if line.rstrip("\n").endswith((" ", "\t")):
            problems.append(_problem(index, "Leerzeichen am Zeilenende", "info", "W291"))
        if len(line.rstrip("\n")) > LINE_LIMIT:
            problems.append(
                _problem(index, f"Zeile länger als {LINE_LIMIT} Zeichen", "info", "E501", LINE_LIMIT)
            )
        indent = line[: len(line) - len(line.lstrip(" \t"))]
        if "\t" in indent:
            saw_tab = True
        if indent.startswith(" "):
            saw_space_indent = True
        if "\t" in indent and " " in indent:
            problems.append(_problem(index, "Einrückung mischt Tabulatoren und Leerzeichen", "warning", "E101"))
    if saw_tab and saw_space_indent:
        problems.append(_problem(1, "Datei mischt Tabulatoren und Leerzeichen bei der Einrückung", "warning", "W191"))
    if source and not source.endswith("\n"):
        problems.append(_problem(max(1, len(lines)), "Datei endet ohne Zeilenumbruch", "info", "W292"))
    return problems


def lint_source(source: str, filename: str = "<memory>") -> list[dict]:
    problems = _style_problems(source)
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        problems.append(
            _problem(
                exc.lineno or 1,
                f"Syntax: {exc.msg}",
                "error",
                "E999",
                max(0, (exc.offset or 1) - 1),
            )
        )
        return problems
    problems.extend(_unused_imports(tree))
    problems.extend(_type_problems(tree))
    module_names: set[str] = set()
    star = _collect_assigned(tree.body, module_names)
    if not star:
        visitor = _UndefinedVisitor(module_names)
        for stmt in tree.body:
            visitor.visit(stmt)
        problems.extend(visitor.problems)
    problems.sort(key=lambda item: (item["line"], item["col"], item["code"]))
    return problems


def outline(source: str) -> list[dict]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    items: list[dict] = []

    def add(node: ast.AST, kind: str, name: str, parent: str = "") -> None:
        items.append(
            {
                "name": name,
                "kind": kind,
                "line": getattr(node, "lineno", 1),
                "end_line": getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                "parent": parent,
            }
        )

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add(node, "function", node.name)
        elif isinstance(node, ast.ClassDef):
            add(node, "class", node.name)
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    add(child, "method", child.name, node.name)
    return items


def todos_in_source(source: str, path: str = "") -> list[dict]:
    found = []
    for index, line in enumerate(source.splitlines(), start=1):
        match = TODO_RE.search(line)
        if match:
            found.append(
                {
                    "path": path,
                    "line": index,
                    "tag": match.group(1).upper(),
                    "text": match.group(2).strip() or match.group(1).upper(),
                }
            )
    return found


def definitions(source: str) -> list[dict]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    found: list[dict] = []

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            found.append({"name": node.name, "line": node.lineno, "col": node.col_offset, "kind": "function"})
            self.generic_visit(node)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            found.append({"name": node.name, "line": node.lineno, "col": node.col_offset, "kind": "class"})
            self.generic_visit(node)

        def visit_Assign(self, node: ast.Assign) -> None:
            for target in node.targets:
                for name in _target_names(target):
                    found.append({"name": name, "line": node.lineno, "col": node.col_offset, "kind": "variable"})
            self.generic_visit(node)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            for name in _target_names(node.target):
                found.append({"name": name, "line": node.lineno, "col": node.col_offset, "kind": "variable"})
            self.generic_visit(node)

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                found.append({"name": name, "line": node.lineno, "col": node.col_offset, "kind": "import"})

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            for alias in node.names:
                if alias.name == "*":
                    continue
                name = alias.asname or alias.name
                found.append({"name": name, "line": node.lineno, "col": node.col_offset, "kind": "import"})

    Visitor().visit(tree)
    return found


def name_at(source: str, line: int, col: int) -> str:
    """Name unter dem Cursor. line ist 1-basiert, col 0-basiert."""
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for tok in tokens:
            if tok.type != tokenize.NAME:
                continue
            (sl, sc), (el, ec) = tok.start, tok.end
            if sl == line and sc <= col <= ec:
                return tok.string
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    rows = source.splitlines()
    if line < 1 or line > len(rows):
        return ""
    text = rows[line - 1]
    if col < 0:
        return ""
    end = min(col, len(text))
    start = end
    while start > 0 and (text[start - 1].isalnum() or text[start - 1] == "_"):
        start -= 1
    stop = end
    while stop < len(text) and (text[stop].isalnum() or text[stop] == "_"):
        stop += 1
    return text[start:stop]


def external_file(source: str, ident: str) -> str | None:
    """Sucht die Quelldatei eines importierten Namens in installierten Bibliotheken."""
    if not ident:
        return None
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                if local == ident:
                    modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                local = alias.asname or alias.name
                if local == ident or alias.name == ident:
                    modules.append(node.module if local != ident else node.module)
                    if alias.name == ident:
                        modules.append(node.module)
    import importlib.util

    seen: set[str] = set()
    for module in modules:
        if module in seen:
            continue
        seen.add(module)
        try:
            spec = importlib.util.find_spec(module)
        except (ImportError, ValueError, AttributeError):
            continue
        origin = getattr(spec, "origin", None) if spec else None
        if origin and origin not in {"built-in", "frozen"} and str(origin).endswith(".py"):
            return str(origin)
    return None


def goto_definition(source: str, line: int, col: int, project: dict[str, str] | None = None, current_path: str = "") -> list[dict]:
    ident = name_at(source, line, col)
    if not ident:
        return []
    hits: list[dict] = []
    for item in definitions(source):
        if item["name"] == ident:
            hits.append({**item, "path": current_path})
    if project:
        for path, text in project.items():
            if path == current_path:
                continue
            if not path.endswith(".py"):
                continue
            for item in definitions(text):
                if item["name"] == ident and item["kind"] in {"function", "class"}:
                    hits.append({**item, "path": path})
    hits.sort(key=lambda item: (item.get("path") != current_path, item["line"]))
    return hits[:40]


def duplicates(files: dict[str, str], window: int = 6) -> list[dict]:
    buckets: dict[tuple[str, ...], list[dict]] = {}
    for path, text in files.items():
        normalized: list[tuple[int, str]] = []
        for index, line in enumerate(text.splitlines(), start=1):
            stripped = " ".join(line.split())
            if not stripped or stripped.startswith("#"):
                continue
            normalized.append((index, stripped))
        if len(normalized) < window:
            continue
        for start in range(0, len(normalized) - window + 1):
            chunk = tuple(item[1] for item in normalized[start : start + window])
            if len(set(chunk)) < 3:
                continue
            buckets.setdefault(chunk, []).append(
                {"path": path, "line": normalized[start][0], "preview": chunk[0][:120]}
            )
    groups = []
    for chunk, places in buckets.items():
        unique = {(item["path"], item["line"]): item for item in places}
        items = list(unique.values())
        if len(items) < 2:
            continue
        # Aufeinanderfolgende Fenster derselben Stelle nicht als eigene Dublette werten.
        spread = {(item["path"], item["line"] // window) for item in items}
        if len(spread) < 2 and len({item["path"] for item in items}) < 2:
            continue
        groups.append({"count": len(items), "preview": chunk[0][:120], "places": items[:12]})
    groups.sort(key=lambda item: item["count"], reverse=True)
    return groups[:80]


def iter_project_files(root, limit: int = 4000):
    from pathlib import Path

    root_path = Path(root)
    count = 0
    if not root_path.is_dir():
        return
    for path in root_path.rglob("*"):
        if count >= limit:
            return
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {".gitignore", "Dockerfile"}:
            continue
        count += 1
        yield path
