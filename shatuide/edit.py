"""Suchen und Ersetzen im Workspace."""

from __future__ import annotations

import re
from pathlib import Path

from shatuide import history
from shatuide.paths import TEXT_SUFFIXES, inside


def compile_pattern(query: str, *, case: bool, word: bool, regex: bool) -> re.Pattern[str]:
    if not query:
        raise ValueError("Suchtext fehlt.")
    if len(query) > 500:
        raise ValueError("Suchtext ist zu lang.")
    pattern = query if regex else re.escape(query)
    if word:
        pattern = r"\b(?:" + pattern + r")\b"
    flags = 0 if case else re.IGNORECASE
    try:
        return re.compile(pattern, flags)
    except re.error as exc:
        raise ValueError(f"Ungültiges Suchmuster: {exc}") from exc


def replace_in_text(
    text: str,
    query: str,
    replacement: str,
    *,
    case: bool = False,
    word: bool = False,
    regex: bool = False,
) -> tuple[str, int]:
    pattern = compile_pattern(query, case=case, word=word, regex=regex)
    if regex:
        try:
            return pattern.subn(replacement, text)
        except re.error as exc:
            raise ValueError(f"Ungültiger Ersatztext: {exc}") from exc
    return pattern.subn(lambda _match: replacement, text)


def replace_project(
    workspace: str | Path,
    query: str,
    replacement: str,
    *,
    case: bool = False,
    word: bool = False,
    regex: bool = False,
    preview: bool = True,
    limit: int = 1000,
) -> dict:
    root = Path(workspace).resolve()
    if not root.is_dir():
        return {"ok": False, "error": "Workspace fehlt."}
    try:
        compile_pattern(query, case=case, word=word, regex=regex)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    files: list[dict] = []
    total = 0
    scanned = 0
    truncated = False
    for path in root.rglob("*"):
        if scanned >= limit:
            truncated = True
            break
        if not path.is_file():
            continue
        if any(part in {".git", "__pycache__", "node_modules", ".venv", "venv", "env", ".shatuide"} for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {".gitignore", "Dockerfile", ".bashrc", ".bash_profile", ".profile", ".zshrc"}:
            continue
        if not inside(root, path):
            continue
        try:
            if path.stat().st_size > 1_000_000:
                continue
            raw = path.read_bytes()
        except OSError:
            continue
        if b"\x00" in raw[:1024]:
            continue
        scanned += 1
        text = raw.decode("utf-8", "replace")
        try:
            updated, count = replace_in_text(
                text, query, replacement, case=case, word=word, regex=regex
            )
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        if count <= 0 or updated == text:
            continue
        samples = []
        for index, line in enumerate(updated.splitlines(), start=1):
            if query.lower() in line.lower() or (regex and _line_hit(line, query, case, word, regex)):
                samples.append({"line": index, "text": line.strip()[:180]})
            if len(samples) >= 8:
                break
        if not samples:
            for index, (old, new) in enumerate(zip(text.splitlines(), updated.splitlines()), start=1):
                if old != new:
                    samples.append({"line": index, "text": new.strip()[:180]})
                if len(samples) >= 8:
                    break
        files.append({"path": str(path), "count": count, "lines": samples})
        total += count
        if not preview:
            relative = str(path.relative_to(root))
            history.snapshot(root, relative, text)
            path.write_text(updated, encoding="utf-8")
        if len(files) >= 80 and preview:
            truncated = True
            break
    return {
        "ok": True,
        "preview": preview,
        "replacements": total,
        "files": files,
        "truncated": truncated,
    }


def _line_hit(line: str, query: str, case: bool, word: bool, regex: bool) -> bool:
    try:
        return compile_pattern(query, case=case, word=word, regex=regex).search(line) is not None
    except ValueError:
        return False
