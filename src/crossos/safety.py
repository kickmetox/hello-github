"""Gemeinsame Sicherheitsprüfungen.

Paketnamen und Pfade werden geprüft, bevor irgendeine Kommandozeile
zusammengesetzt wird. Bestätigung ist ein echtes JSON-Boolean.
"""

from __future__ import annotations

import re
from pathlib import Path

PACKAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+:_-]{0,127}$")
UNIT_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9@._+-]{0,80}\.(?:service|socket|mount|timer|target)$"
)
USER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$")
ACCENT_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,64}$")


class SafetyError(ValueError):
    """Eingabe verletzt eine Sicherheitsregel. Es wird kein Kommando erzeugt."""


def require_confirm(value: object) -> None:
    if value is not True:
        raise SafetyError("Bestätigung fehlt. confirm muss JSON-true sein.")


def validate_user(name: str | None, *, default: str = "user") -> str:
    if name is None or name == "":
        name = default
    if not isinstance(name, str) or not USER_RE.fullmatch(name):
        raise SafetyError("Benutzername enthält unzulässige Zeichen.")
    return name


def validate_package_name(name: object) -> str:
    """Strikt prüfen. Bei Fehler wird kein Shell-String erzeugt."""
    if not isinstance(name, str):
        raise SafetyError("Paketname muss eine Zeichenkette sein.")
    if name != name.strip():
        raise SafetyError("Paketname enthält führende oder folgende Leerzeichen.")
    if ".." in name or "/" in name or "\\" in name or name.startswith("-"):
        raise SafetyError("Paketname abgelehnt.")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
        raise SafetyError("Paketname enthält Steuerzeichen.")
    if not PACKAGE_RE.fullmatch(name):
        raise SafetyError("Paketname abgelehnt.")
    return name


def validate_unit_name(name: object) -> str:
    if not isinstance(name, str) or not UNIT_RE.fullmatch(name):
        raise SafetyError("Unit-Name abgelehnt.")
    if ".." in name or name.startswith("-"):
        raise SafetyError("Unit-Name abgelehnt.")
    return name


def validate_accent(value: object) -> str:
    if not isinstance(value, str) or not ACCENT_RE.fullmatch(value):
        raise SafetyError("Akzentfarbe muss #RRGGBB sein.")
    return value.lower()


def validate_theme_token(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not SAFE_TOKEN_RE.fullmatch(value):
        raise SafetyError(f"{field} enthält unzulässige Zeichen.")
    return value


def ensure_within(path: Path, root: Path) -> Path:
    """Pfad auflösen und Verzeichniswechsel nach oben ablehnen."""
    root_resolved = root.resolve()
    # Teile prüfen, bevor resolve Symlinks folgt: ".." ist immer verboten.
    if ".." in path.parts:
        raise SafetyError("Pfad enthält '..' und wurde abgelehnt.")
    candidate = path if path.is_absolute() else root_resolved / path
    resolved = candidate.resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise SafetyError("Pfad liegt außerhalb des erlaubten Wurzelverzeichnisses.")
    return resolved


def parse_bool_token(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"1", "true", "yes", "on"}:
        return True
    if isinstance(value, str) and value.lower() in {"0", "false", "no", "off"}:
        return False
    raise SafetyError("Boolescher Wert erwartet.")
