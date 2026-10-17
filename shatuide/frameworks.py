"""Erkennung von Django, Flask und FastAPI samt Startbefehl."""

from __future__ import annotations

from pathlib import Path


def detect(workspace: Path, python: str) -> list[dict]:
    workspace = Path(workspace)
    found: list[dict] = []
    if (workspace / "manage.py").is_file():
        found.append(
            {
                "id": "django",
                "label": "Django Entwicklungsserver",
                "argv": [python, "manage.py", "runserver"],
                "cwd": str(workspace),
            }
        )
    candidates = list(workspace.glob("*.py"))
    candidates += list(workspace.glob("app/*.py"))
    candidates += list(workspace.glob("src/*.py"))
    seen_flask = False
    seen_fastapi = False
    for path in candidates:
        if any(part in {".venv", "venv", "site-packages"} for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        module = path.stem
        if not seen_flask and "Flask(" in text:
            seen_flask = True
            found.append(
                {
                    "id": "flask",
                    "label": f"Flask ({path.name})",
                    "argv": [python, "-m", "flask", "--app", module, "run"],
                    "cwd": str(path.parent),
                }
            )
        if not seen_fastapi and "FastAPI(" in text:
            seen_fastapi = True
            found.append(
                {
                    "id": "fastapi",
                    "label": f"FastAPI / uvicorn ({path.name})",
                    "argv": [python, "-m", "uvicorn", f"{module}:app", "--reload"],
                    "cwd": str(path.parent),
                    "needs": "uvicorn",
                }
            )
    return found
