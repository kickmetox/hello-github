"""PDF-Passwort öffnen / setzen (pikepdf + pypdfium2)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Tuple


def password_strength(password: str) -> tuple[str, int]:
    """
    Passwort-Stärke-Hinweis — 1.6.1.
    Rückgabe: (Label DE, Score 0–4). Leeres Passwort → („leer“, 0).
    """
    pw = password or ""
    if not pw:
        return "leer", 0
    score = 0
    if len(pw) >= 8:
        score += 1
    if len(pw) >= 12:
        score += 1
    if re.search(r"[a-z]", pw) and re.search(r"[A-Z]", pw):
        score += 1
    if re.search(r"\d", pw) and re.search(r"[^A-Za-z0-9]", pw):
        score += 1
    labels = {
        0: "sehr schwach",
        1: "schwach",
        2: "mittel",
        3: "gut",
        4: "stark",
    }
    # unter 8 Zeichen höchstens „schwach“
    if len(pw) < 8:
        score = min(score, 1)
        if score == 0:
            return "sehr schwach", 0
    return labels.get(score, "schwach"), score


def needs_password(path: str | Path) -> bool:
    """True, wenn das PDF ohne Passwort nicht öffnet."""
    path = Path(path)
    try:
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(str(path))
        try:
            _ = len(doc)
        finally:
            doc.close()
        return False
    except Exception as e:
        msg = str(e).lower()
        return "password" in msg or "passwd" in msg


def try_open_password(path: str | Path, password: str | None) -> Tuple[bool, str]:
    """Prüft, ob path mit password geöffnet werden kann."""
    path = Path(path)
    try:
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(str(path), password=password or None)
        try:
            n = len(doc)
        finally:
            doc.close()
        if n <= 0:
            return False, "PDF enthält keine Seiten."
        return True, ""
    except Exception as e:
        return False, str(e)


def set_password(
    pdf_path: str | Path,
    *,
    user_password: str,
    owner_password: str | None = None,
    out_path: str | Path | None = None,
    allow_printing: bool = True,
    allow_modify: bool = False,
    allow_extract: bool = False,
) -> Path:
    """
    Speichert das PDF mit User-/Owner-Passwort (AES, R=6 wenn möglich).
    user_password: zum Öffnen. owner_password: optional (default = user).
    """
    import pikepdf

    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path
    owner = owner_password if owner_password is not None else user_password
    if not (user_password or "").strip():
        raise ValueError("User-Passwort darf nicht leer sein.")

    perms = pikepdf.Permissions(
        accessibility=True,
        extract=allow_extract,
        modify_annotation=allow_modify,
        modify_assembly=allow_modify,
        modify_form=allow_modify,
        modify_other=allow_modify,
        print_highres=allow_printing,
        print_lowres=allow_printing,
    )
    enc = pikepdf.Encryption(
        owner=owner,
        user=user_password,
        R=6,
        allow=perms,
    )
    with pikepdf.open(pdf_path, allow_overwriting_input=(out_path.resolve() == pdf_path.resolve())) as pdf:
        pdf.save(out_path, encryption=enc)
    return out_path


def remove_password(
    pdf_path: str | Path,
    password: str,
    *,
    out_path: str | Path | None = None,
) -> Path:
    """Entfernt die Verschlüsselung (Passwort muss gültig sein)."""
    import pikepdf

    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path
    with pikepdf.open(
        pdf_path,
        password=password,
        allow_overwriting_input=(out_path.resolve() == pdf_path.resolve()),
    ) as pdf:
        pdf.save(out_path)
    return out_path
