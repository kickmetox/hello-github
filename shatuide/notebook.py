"""Lesen und Schreiben von Jupyter-Notebooks (.ipynb). Ausführung übernimmt der Kernel."""

from __future__ import annotations

import json
from pathlib import Path


def load_notebook(path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cells = []
    for index, cell in enumerate(data.get("cells", [])):
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        cells.append(
            {
                "index": index,
                "type": cell.get("cell_type", "code"),
                "source": source,
            }
        )
    return {"ok": True, "cells": cells, "nbformat": data.get("nbformat", 4)}


def save_notebook(path: Path, cells: list[dict]) -> dict:
    path = Path(path)
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"}, "language_info": {"name": "python"}},
            "cells": [],
        }
    stored = []
    for cell in cells:
        source = cell.get("source", "")
        if isinstance(source, str):
            source = source.splitlines(keepends=True)
        stored.append(
            {
                "cell_type": cell.get("type", "code"),
                "metadata": {},
                "source": source,
                "outputs": [] if cell.get("type", "code") == "code" else None,
                "execution_count": None if cell.get("type", "code") == "code" else None,
            }
        )
        if stored[-1]["outputs"] is None:
            stored[-1].pop("outputs")
            stored[-1].pop("execution_count")
    data["cells"] = stored
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"ok": True, "path": str(path)}
