"""Ereignisanzeigen-, journalctl- und dmesg-Text in Befunde zerlegen."""

from __future__ import annotations

import re

from crossos.diagnostics.codes import lookup
from crossos.diagnostics.conflicts import solve_text

_CODE_RE = re.compile(r"\b(0x[0-9A-Fa-f]{8})\b")
_EVENT_RE = re.compile(r"\b(?:Event ID|Ereignis-ID|Ereignis)\s*:\s*(\d+)\b", re.IGNORECASE)
_UNIT_RE = re.compile(r"\b([A-Za-z0-9][A-Za-z0-9@._+-]{0,80}\.(?:service|socket|mount|timer))\b")

_SIGNATURES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"segmentation fault", re.IGNORECASE), "segfault"),
    (re.compile(r"segfault at", re.IGNORECASE), "segfault"),
    (re.compile(r"cannot open shared object file|error while loading shared libraries", re.IGNORECASE), "missing-so"),
    (re.compile(r"\.dll (?:was |is )?not found|cannot proceed because .+\.dll|dll not found", re.IGNORECASE), "missing-dll"),
    (re.compile(r"unmet dependencies|broken packages|dpkg: error processing|packages have unmet|you have held broken", re.IGNORECASE), "apt-broken"),
    (re.compile(r"Failed with result|Failed to start|entered failed state|dependency failed", re.IGNORECASE), "systemd-failed"),
    (re.compile(r"out of memory: killed process|oom-kill|killed process .+\(oom", re.IGNORECASE), "oom"),
    (re.compile(r"i/o error|i/o error,", re.IGNORECASE), "io-error"),
    (re.compile(r"ext4-fs error|btrfs error|xfs .*error", re.IGNORECASE), "ext4-error"),
    (re.compile(r"read-only file system", re.IGNORECASE), "readonly-fs"),
    (re.compile(r"kernel panic", re.IGNORECASE), "kernel-panic"),
]


def parse_log(text: str) -> list[dict]:
    if not isinstance(text, str) or not text.strip():
        return []
    found: list[dict] = []
    seen: set[str] = set()

    def add(code: str, *, evidence: str, extra: dict | None = None) -> None:
        if code in seen:
            return
        record = lookup(code)
        if record is None and not code.startswith("event-"):
            return
        seen.add(code)
        item = {
            "code": code,
            "title": (record or {}).get("title", code),
            "plain_de": (record or {}).get("plain_de", ""),
            "likely": list((record or {}).get("likely", [])),
            "evidence": evidence.strip()[:500],
        }
        if extra:
            item.update(extra)
        found.append(item)

    for match in _CODE_RE.finditer(text):
        code = match.group(1).lower()
        if lookup(code):
            add(code, evidence=_line_of(text, match.start()))

    for match in _EVENT_RE.finditer(text):
        number = match.group(1)
        code = f"event-{number}"
        if lookup(code):
            add(code, evidence=_line_of(text, match.start()))

    for pattern, code in _SIGNATURES:
        match = pattern.search(text)
        if match:
            extra = {}
            if code == "systemd-failed":
                unit = _first_unit(text)
                if unit:
                    extra["unit"] = unit
            add(code, evidence=_line_of(text, match.start()), extra=extra)

    libraries = solve_text(text)
    if libraries and "missing-dll" not in seen and any(item["kind"] == "dll" for item in libraries):
        add("missing-dll", evidence=libraries[0]["name"], extra={"libraries": libraries})
    elif libraries and "missing-so" not in seen and any(item["kind"] == "so" for item in libraries):
        add("missing-so", evidence=libraries[0]["name"], extra={"libraries": libraries})
    for item in found:
        if item["code"] in {"missing-dll", "missing-so"} and "libraries" not in item:
            item["libraries"] = libraries
    return found


def _line_of(text: str, index: int) -> str:
    start = text.rfind("\n", 0, index) + 1
    end = text.find("\n", index)
    if end == -1:
        end = len(text)
    return text[start:end]


def _first_unit(text: str) -> str | None:
    match = _UNIT_RE.search(text)
    return match.group(1) if match else None
