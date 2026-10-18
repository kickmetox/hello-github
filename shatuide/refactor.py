"""Umbenennen und Methode extrahieren."""

from __future__ import annotations

import ast
import builtins
import io
import tokenize

from shatuide.analysis import _target_names


def _identifier_spans(source: str, name: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return spans
    for tok in tokens:
        if tok.type == tokenize.NAME and tok.string == name:
            start = _pos(source, tok.start)
            end = _pos(source, tok.end)
            if start is not None and end is not None:
                spans.append((start, end))
    return spans


def _pos(source: str, point: tuple[int, int]) -> int | None:
    line, col = point
    current = 0
    for index, row in enumerate(source.splitlines(keepends=True), start=1):
        if index == line:
            if col > len(row):
                return None
            return current + col
        current += len(row)
    return None


def rename_source(source: str, old: str, new: str) -> dict:
    if not old.isidentifier() or not new.isidentifier():
        return {"ok": False, "error": "Alter und neuer Name müssen Bezeichner sein."}
    if keyword_clash(new):
        return {"ok": False, "error": f"'{new}' ist ein Schlüsselwort."}
    spans = _identifier_spans(source, old)
    if not spans:
        return {"ok": True, "content": source, "count": 0}
    updated = source
    for start, end in reversed(spans):
        updated = updated[:start] + new + updated[end:]
    return {"ok": True, "content": updated, "count": len(spans)}


def keyword_clash(name: str) -> bool:
    import keyword

    return keyword.iskeyword(name)


def rename_project(files: dict[str, str], old: str, new: str) -> dict:
    changed = []
    total = 0
    result_files = {}
    for path, source in files.items():
        if not str(path).endswith(".py"):
            continue
        renamed = rename_source(source, old, new)
        if not renamed.get("ok"):
            return renamed
        count = renamed["count"]
        if count:
            result_files[path] = renamed["content"]
            changed.append({"path": path, "count": count})
            total += count
    return {"ok": True, "files": result_files, "changed": changed, "count": total}


def _names_in_tree(tree: ast.AST) -> tuple[set[str], set[str]]:
    assigned: set[str] = set()
    used: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def visit_Name(self, node: ast.Name) -> None:
            if isinstance(node.ctx, ast.Load):
                used.add(node.id)
            else:
                assigned.add(node.id)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            assigned.add(node.name)
            self.generic_visit(node)

        visit_AsyncFunctionDef = visit_FunctionDef
        visit_ClassDef = visit_FunctionDef

        def visit_arg(self, node: ast.arg) -> None:
            assigned.add(node.arg)

        def visit_alias(self, node: ast.alias) -> None:
            assigned.add(node.asname or node.name.split(".")[0])

    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.For, ast.AsyncFor, ast.With, ast.AsyncWith)):
            pass
    Visitor().visit(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                assigned.update(_target_names(target))
        elif isinstance(node, ast.AnnAssign):
            assigned.update(_target_names(node.target))
        elif isinstance(node, ast.AugAssign):
            assigned.update(_target_names(node.target))
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            assigned.update(_target_names(node.target))
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars is not None:
                    assigned.update(_target_names(item.optional_vars))
    return assigned, used


def extract_method(source: str, start_line: int, end_line: int, name: str) -> dict:
    if not name.isidentifier() or keyword_clash(name):
        return {"ok": False, "error": "Ungültiger Methodenname."}
    lines = source.splitlines()
    if start_line < 1 or end_line < start_line or end_line > len(lines):
        return {"ok": False, "error": "Ungültiger Zeilenbereich."}
    selected = "\n".join(lines[start_line - 1 : end_line])
    if not selected.strip():
        return {"ok": False, "error": "Keine Zeilen markiert."}
    try:
        tree = ast.parse(selected)
    except SyntaxError as exc:
        return {"ok": False, "error": f"Auswahl ist kein gültiger Block: {exc.msg}"}
    assigned, used = _names_in_tree(tree)
    builtins_names = set(dir(builtins))
    args = sorted(used - assigned - builtins_names)
    returns = sorted(assigned & used)
    # Namen, die nur zugewiesen und danach im Rest der Datei gebraucht werden, zurückgeben.
    rest = "\n".join(lines[end_line:])
    rest_used = set()
    try:
        rest_tree = ast.parse(rest or "pass")
        _assigned_rest, rest_used = _names_in_tree(rest_tree)
    except SyntaxError:
        rest_used = set()
    returns = sorted((assigned - set(args)) & (rest_used | set(returns)))
    returns = sorted(set(returns) | (assigned & rest_used))
    indent = "    "
    body = "\n".join(indent + row if row.strip() else "" for row in selected.splitlines())
    signature = f"def {name}({', '.join(args)}):"
    func = signature + "\n" + body + "\n"
    if returns:
        func += f"{indent}return {', '.join(returns)}\n"
        call = f"{', '.join(returns)} = {name}({', '.join(args)})"
    else:
        call = f"{name}({', '.join(args)})"
    base_indent = len(lines[start_line - 1]) - len(lines[start_line - 1].lstrip(" "))
    call_line = " " * base_indent + call
    new_lines = lines[: start_line - 1] + [call_line] + lines[end_line:]
    # Funktion direkt davor einsetzen, eine Ebene weniger eingerückt.
    insert_at = start_line - 1
    func_lines = func.splitlines()
    new_lines[insert_at:insert_at] = ["", *func_lines, ""]
    return {"ok": True, "content": "\n".join(new_lines) + ("\n" if source.endswith("\n") else ""), "name": name}


def preview_rename(files: dict[str, str], old: str, new: str) -> dict:
    renamed = rename_project(files, old, new)
    if not renamed.get("ok"):
        return renamed
    return {"ok": True, "count": renamed["count"], "changed": renamed["changed"]}
