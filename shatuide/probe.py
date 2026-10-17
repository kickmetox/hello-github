"""Baut aus einer Zeile, einem Abschnitt oder einer Funktion ein getrennt lauffähiges Stück."""

from __future__ import annotations

import ast
import re
import textwrap

from shatuide.scripting import language_of


def prepare(source: str, path: str, start: int, end: int, selected: str, scope: str) -> dict:
    lang = language_of(path or "ausschnitt.py")
    start = max(1, int(start or 1))
    end = max(start, int(end or start))
    if lang == "json":
        return _prepare_json(source, path, selected)
    if lang == "shell":
        return _prepare_braces(source, path, start, selected, scope, "shell", r"^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(\))?\s*\{")
    if lang == "powershell":
        return _prepare_braces(source, path, start, selected, scope, "powershell", r"^\s*function\s+([A-Za-z_][\w-]*)\b[^{]*\{")
    if lang != "python":
        return _prepare_text(source, path, start, end, selected, lang)
    return _prepare_python(source, path, start, end, selected, scope)


def _prepare_json(source: str, path: str, selected: str) -> dict:
    fragment = selected.strip() or source
    if not fragment.strip():
        return {"ok": False, "error": "Nichts markiert."}
    title = "JSON-Abschnitt" if selected.strip() else "JSON-Datei"
    return {
        "ok": True,
        "title": title,
        "kind": "json",
        "language": "json",
        "mode": "check",
        "path": path or "ausschnitt.json",
        "code": fragment if fragment.endswith("\n") else fragment + "\n",
        "detail": "Der Ausschnitt wird geprüft und formatiert. Die Datei bleibt unverändert.",
    }


def _prepare_text(source: str, path: str, start: int, end: int, selected: str, lang: str) -> dict:
    body = _marked(source, start, end, selected)
    if body is None:
        return {"ok": False, "error": "Nichts markiert."}
    return {
        "ok": True,
        "title": _mark_title(start, end, selected),
        "kind": "line" if "\n" not in body.strip() else "section",
        "language": lang,
        "mode": "run",
        "path": path or "ausschnitt.txt",
        "code": body,
        "detail": "Der Ausschnitt läuft getrennt. Die Datei bleibt unverändert.",
    }


def _prepare_braces(source: str, path: str, start: int, selected: str, scope: str, lang: str, pattern: str) -> dict:
    if scope == "function":
        found = _brace_block(source, start, pattern)
        if found is None:
            return {"ok": False, "error": "Keine Funktion an dieser Stelle."}
        name, code = found
        return {
            "ok": True,
            "title": f"Funktion {name}",
            "kind": "function",
            "language": lang,
            "mode": "run",
            "path": path or ("ausschnitt.ps1" if lang == "powershell" else "ausschnitt.sh"),
            "code": code,
            "detail": "Die Funktion wird definiert und einmal aufgerufen. Die Datei bleibt unverändert.",
        }
    lines = source.splitlines()
    end = start
    body = _marked(source, start, end, selected)
    if body is None:
        return {"ok": False, "error": "Nichts markiert."}
    suffix = ".ps1" if lang == "powershell" else ".sh"
    return {
        "ok": True,
        "title": _mark_title(start, start if not selected.strip() else start + body.count("\n"), selected),
        "kind": "line" if "\n" not in body.strip() else "section",
        "language": lang,
        "mode": "run",
        "path": path or f"ausschnitt{suffix}",
        "code": body,
        "detail": "Der Ausschnitt läuft getrennt. Die Datei bleibt unverändert.",
    }


def _brace_block(source: str, line: int, pattern: str) -> tuple[str, str] | None:
    lines = source.splitlines()
    if not lines or line < 1 or line > len(lines):
        return None
    start = None
    name = ""
    for index in range(min(line, len(lines)), 0, -1):
        match = re.match(pattern, lines[index - 1])
        if match:
            start = index
            name = match.group(1)
            break
    if start is None:
        return None
    depth = 0
    end = None
    for index in range(start, len(lines) + 1):
        depth += lines[index - 1].count("{") - lines[index - 1].count("}")
        if depth <= 0:
            end = index
            break
    if end is None or not (start <= line <= end):
        return None
    body = "\n".join(lines[start - 1 : end]).rstrip() + "\n" + name + "\n"
    return name, body


def _prepare_python(source: str, path: str, start: int, end: int, selected: str, scope: str) -> dict:
    if scope == "function":
        return _python_symbol(source, path, start)
    body = _marked(source, start, end, selected)
    if body is None:
        return {"ok": False, "error": "Nichts markiert."}
    code = _with_imports(source, body)
    code, detail = _maybe_harness(code, None)
    return {
        "ok": True,
        "title": _mark_title(start, end, selected),
        "kind": "line" if "\n" not in body.strip() else "section",
        "language": "python",
        "mode": "run",
        "path": path or "ausschnitt.py",
        "code": code,
        "detail": detail,
    }


def _python_symbol(source: str, path: str, line: int) -> dict:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {"ok": False, "error": f"Zeile {exc.lineno}: {exc.msg}"}
    parents = _parents(tree)
    node = _innermost(tree, line, (ast.FunctionDef, ast.AsyncFunctionDef))
    if node is None:
        node = _innermost(tree, line, (ast.ClassDef,))
    if node is None:
        return {"ok": False, "error": "Keine Funktion oder Klasse an dieser Stelle."}
    support = _module_support(source, tree)
    if isinstance(node, ast.ClassDef):
        footer, detail = _class_footer(node)
        title = f"Klasse {node.name}"
        kind = "class"
    else:
        parent = parents.get(node)
        if isinstance(parent, ast.FunctionDef | ast.AsyncFunctionDef):
            footer = f"# {node.name} ist verschachtelt und wird nicht automatisch aufgerufen.\n"
            detail = "Verschachtelte Funktion. Der Aufruf kann im Fenster ergänzt werden."
            title = f"Funktion {node.name}"
            kind = "function"
        elif isinstance(parent, ast.ClassDef):
            footer, detail = _method_footer(parent, node)
            title = f"Methode {parent.name}.{node.name}"
            kind = "method"
        else:
            footer, detail = _function_footer(node)
            title = f"Funktion {node.name}"
            kind = "function"
    code = support.rstrip() + "\n\n" + footer
    return {
        "ok": True,
        "title": title,
        "kind": kind,
        "language": "python",
        "mode": "run",
        "path": path or "ausschnitt.py",
        "code": code if code.endswith("\n") else code + "\n",
        "detail": detail,
    }


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _innermost(tree: ast.AST, line: int, kinds: tuple[type, ...]) -> ast.AST | None:
    best: tuple[int, ast.AST] | None = None
    for node in ast.walk(tree):
        if not isinstance(node, kinds):
            continue
        start = _node_start(node)
        end = getattr(node, "end_lineno", None) or node.lineno
        if start <= line <= end:
            span = end - start
            if best is None or span < best[0]:
                best = (span, node)
    return None if best is None else best[1]


def _node_start(node: ast.AST) -> int:
    decorators = getattr(node, "decorator_list", None) or []
    if decorators:
        return min(item.lineno for item in decorators)
    return node.lineno


def _slice(source: str, node: ast.AST) -> str:
    lines = source.splitlines()
    start = _node_start(node)
    end = getattr(node, "end_lineno", None) or node.lineno
    return "\n".join(lines[start - 1 : end]).rstrip() + "\n"


def _module_support(source: str, tree: ast.AST) -> str:
    kept = (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    chunks = [_slice(source, node) for node in tree.body if isinstance(node, kept)]
    return "\n".join(chunks).rstrip() + "\n"


def _import_block(source: str) -> str:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    chunks = [_slice(source, node) for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    return "\n".join(chunks).rstrip()


def _with_imports(source: str, body: str) -> str:
    imports = _import_block(source)
    if imports and imports not in body:
        return imports + "\n\n" + body
    return body


def _marked(source: str, start: int, end: int, selected: str) -> str | None:
    if selected.strip():
        body = textwrap.dedent(selected).strip("\n")
    else:
        lines = source.splitlines()
        if start > len(lines):
            return None
        body = "\n".join(lines[start - 1 : end]).strip("\n")
    if not body.strip():
        return None
    return body + "\n"


def _mark_title(start: int, end: int, selected: str) -> str:
    if selected.strip() and "\n" in selected:
        return f"Abschnitt Zeile {start}–{end}"
    return f"Zeile {start}"


def _maybe_harness(code: str, node: ast.AST | None) -> tuple[str, str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code, "Der Ausschnitt läuft getrennt. Die Datei bleibt unverändert."
    definitions = [item for item in tree.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    statements = [item for item in tree.body if not isinstance(item, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Assign, ast.AnnAssign))]
    if statements or not definitions:
        return code, "Der Ausschnitt läuft getrennt. Die Datei bleibt unverändert."
    target = node if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else definitions[-1]
    if not isinstance(target, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return code, "Der Ausschnitt läuft getrennt. Die Datei bleibt unverändert."
    footer, detail = _function_footer(target)
    return code.rstrip() + "\n\n" + footer, detail


def _has_doctest(node: ast.AST) -> bool:
    doc = ast.get_docstring(node, clean=False) or ""
    return ">>>" in doc


def _required_positional(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    positional = list(node.args.posonlyargs) + list(node.args.args)
    return max(0, len(positional) - len(node.args.defaults))


def _kw_required(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(item is None for item in node.args.kw_defaults)


def _function_footer(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, str]:
    name = node.name
    if name.startswith("test_"):
        if isinstance(node, ast.AsyncFunctionDef):
            footer = (
                "if __name__ == '__main__':\n"
                "    import unittest\n"
                "    class _Probe(unittest.IsolatedAsyncioTestCase):\n"
                f"        async def test_probe(self):\n"
                f"            await {name}()\n"
                "    suite = unittest.defaultTestLoader.loadTestsFromTestCase(_Probe)\n"
                "    result = unittest.TextTestRunner(verbosity=2).run(suite)\n"
                "    raise SystemExit(0 if result.wasSuccessful() else 1)\n"
            )
        else:
            footer = (
                "if __name__ == '__main__':\n"
                "    import unittest\n"
                f"    result = unittest.TextTestRunner(verbosity=2).run(unittest.FunctionTestCase({name}))\n"
                "    raise SystemExit(0 if result.wasSuccessful() else 1)\n"
            )
        return footer, f"Test {name} läuft einzeln. Die Datei bleibt unverändert."
    if _has_doctest(node):
        footer = (
            "if __name__ == '__main__':\n"
            "    import doctest\n"
            "    finder = doctest.DocTestFinder()\n"
            "    runner = doctest.DocTestRunner(verbose=True)\n"
            f"    for test in finder.find({name}, {name!r}):\n"
            "        runner.run(test)\n"
            "    raise SystemExit(0 if runner.failures == 0 else 1)\n"
        )
        return footer, f"Doctest von {name}. Die Datei bleibt unverändert."
    if _required_positional(node) == 0 and not _kw_required(node):
        call = f"asyncio.run({name}())" if isinstance(node, ast.AsyncFunctionDef) else f"{name}()"
        imports = "    import asyncio\n" if isinstance(node, ast.AsyncFunctionDef) else ""
        footer = (
            "if __name__ == '__main__':\n"
            f"{imports}"
            f"    result = {call}\n"
            "    if result is not None:\n"
            "        print(repr(result))\n"
        )
        return footer, f"{name} wird ohne Argumente aufgerufen. Die Datei bleibt unverändert."
    footer = f"# Aufruf ergänzen, zum Beispiel:\n# print({name}(...))\n"
    return footer, f"{name} braucht Argumente. Der Aufruf kann im Fenster ergänzt werden."


def _is_test_class(node: ast.ClassDef) -> bool:
    if node.name.startswith("Test"):
        return True
    for base in node.bases:
        try:
            text = ast.unparse(base)
        except AttributeError:
            text = ""
        if text.endswith("TestCase"):
            return True
    return any(isinstance(item, ast.FunctionDef) and item.name.startswith("test_") for item in node.body)


def _unittest_footer(qual: str) -> str:
    return (
        "if __name__ == '__main__':\n"
        "    import sys\n"
        "    import unittest\n"
        f"    suite = unittest.defaultTestLoader.loadTestsFromName({qual!r}, module=sys.modules[__name__])\n"
        "    result = unittest.TextTestRunner(verbosity=2).run(suite)\n"
        "    raise SystemExit(0 if result.wasSuccessful() else 1)\n"
    )


def _class_footer(node: ast.ClassDef) -> tuple[str, str]:
    if _is_test_class(node):
        return _unittest_footer(node.name), f"Klasse {node.name} wird einzeln getestet. Die Datei bleibt unverändert."
    footer = f"# Beispiel:\n# obj = {node.name}()\n"
    return footer, f"Klasse {node.name} wird nur definiert. Ein Aufruf kann im Fenster ergänzt werden."


def _method_footer(parent: ast.ClassDef, node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, str]:
    qual = f"{parent.name}.{node.name}"
    if node.name.startswith("test_"):
        return _unittest_footer(qual), f"Test {qual} läuft einzeln. Die Datei bleibt unverändert."
    footer = f"# Beispiel:\n# obj = {parent.name}()\n# print(obj.{node.name}())\n"
    return footer, f"{qual} braucht eine Instanz. Der Aufruf kann im Fenster ergänzt werden."
