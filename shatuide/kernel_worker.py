"""Persistenter Python-Kernel für REPL, Notebooks, Variablen und Plots."""

from __future__ import annotations

import ast
import io
import json
import os
import sys
import traceback


def _summarize(name: str, value):
    if name.startswith("_"):
        return None
    try:
        import pandas as pd

        if isinstance(value, pd.DataFrame):
            frame = value.head(30).astype(str)
            return {
                "name": name,
                "kind": "dataframe",
                "shape": [int(value.shape[0]), int(value.shape[1])],
                "columns": [str(col) for col in list(value.columns)[:40]],
                "rows": frame.to_dict(orient="records"),
            }
    except Exception:
        pass
    try:
        import numpy as np

        if isinstance(value, np.ndarray):
            return {
                "name": name,
                "kind": "ndarray",
                "shape": list(value.shape),
                "repr": repr(value[:20])[:800],
            }
    except Exception:
        pass
    if isinstance(value, (int, float, str, bool)) or value is None:
        return {"name": name, "kind": type(value).__name__, "repr": repr(value)[:400]}
    return {"name": name, "kind": type(value).__name__, "repr": repr(value)[:400]}


def _plots(plot_dir: str) -> list[str]:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return []
    names = []
    os.makedirs(plot_dir, exist_ok=True)
    for number in list(plt.get_fignums()):
        figure = plt.figure(number)
        filename = f"plot_{number}_{len(os.listdir(plot_dir)) + 1}.png"
        figure.savefig(os.path.join(plot_dir, filename))
        names.append(filename)
    plt.close("all")
    return names


def main() -> None:
    plot_dir = os.environ.get("SHATU_PLOT_DIR", "")
    os.environ.setdefault("MPLBACKEND", "Agg")
    real_stdout = sys.stdout
    globs: dict = {"__name__": "__main__"}
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if message.get("cmd") == "shutdown":
            break
        code = message.get("code") or ""
        stdout = io.StringIO()
        stderr = io.StringIO()
        result = ""
        error = ""
        sys.stdout = stdout
        sys.stderr = stderr
        try:
            parsed = ast.parse(code)
            if parsed.body and isinstance(parsed.body[-1], ast.Expr):
                body = parsed.body[:-1]
                last = ast.Expression(parsed.body[-1].value)
                ast.fix_missing_locations(last)
                if body:
                    module = ast.fix_missing_locations(ast.Module(body=body, type_ignores=[]))
                    exec(compile(module, "<repl>", "exec"), globs, globs)
                result_value = eval(compile(last, "<repl>", "eval"), globs, globs)
                if result_value is not None:
                    result = repr(result_value)[:4000]
                    globs["_"] = result_value
            else:
                exec(compile(code, "<repl>", "exec"), globs, globs)
        except SyntaxError as exc:
            error = f"Syntax: {exc.msg} (Zeile {exc.lineno})"
        except Exception:
            error = traceback.format_exc()[-4000:]
        finally:
            sys.stdout = real_stdout
            sys.stderr = sys.__stderr__
        variables = []
        for key, value in list(globs.items()):
            if key in {"__name__", "__builtins__"}:
                continue
            item = _summarize(key, value)
            if item:
                variables.append(item)
        images = _plots(plot_dir) if plot_dir else []
        reply = {
            "id": message.get("id"),
            "stdout": stdout.getvalue()[-20000:],
            "stderr": stderr.getvalue()[-8000:],
            "result": result,
            "error": error,
            "variables": variables[:200],
            "images": images,
        }
        real_stdout.write(json.dumps(reply, default=str) + "\n")
        real_stdout.flush()


if __name__ == "__main__":
    main()
