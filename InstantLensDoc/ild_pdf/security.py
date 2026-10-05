"""PDF-Passwort öffnen / setzen / Rechte (pikepdf + pypdfium2) — 2.6.7."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Optional, Tuple

# AES-256 = PDF Revision 6 / V=5 / AESV3 (256 bit) — bevorzugt.
PREFERRED_ENCRYPTION_R = 6
FALLBACK_ENCRYPTION_R = 5  # AES-128 (AESV2); R=5 ist deprecated, nur Fallback


@dataclass(frozen=True)
class PdfPermissionFlags:
    """PDF-Rechte (Owner-Permissions). Default: restriktiv außer Barrierefreiheit."""

    allow_printing: bool = True  # print_lowres
    allow_print_highres: bool = True
    allow_modify: bool = False  # modify_other
    allow_modify_annotation: bool = False
    allow_modify_form: bool = False
    allow_modify_assembly: bool = False
    allow_extract: bool = False  # Kopieren / Extrahieren
    allow_accessibility: bool = True

    def to_dict(self) -> dict[str, bool]:
        return {f.name: bool(getattr(self, f.name)) for f in fields(self)}

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None) -> "PdfPermissionFlags":
        if not data:
            return cls()
        kwargs = {}
        for f in fields(cls):
            if f.name in data:
                kwargs[f.name] = bool(data[f.name])
        return cls(**kwargs)

    @classmethod
    def from_legacy(
        cls,
        *,
        allow_printing: bool = True,
        allow_modify: bool = False,
        allow_extract: bool = False,
    ) -> "PdfPermissionFlags":
        """Kompatibel zu set_password(allow_printing/modify/extract) — 1.6.x."""
        return cls(
            allow_printing=bool(allow_printing),
            allow_print_highres=bool(allow_printing),
            allow_modify=bool(allow_modify),
            allow_modify_annotation=bool(allow_modify),
            allow_modify_form=bool(allow_modify),
            allow_modify_assembly=bool(allow_modify),
            allow_extract=bool(allow_extract),
            allow_accessibility=True,
        )


@dataclass(frozen=True)
class EncryptionInfo:
    """Verschlüsselungsstatus eines PDFs — 2.6.7."""

    encrypted: bool
    algorithm: str  # "none" | "AES-256" | "AES-128" | "RC4" | "unknown"
    revision: int | None = None  # R
    bits: int | None = None
    permissions: PdfPermissionFlags | None = None
    needs_user_password: bool = False
    openable: bool = True  # ohne/mit geliefertem Passwort geöffnet

    def label_de(self) -> str:
        if not self.encrypted:
            return "Nicht verschlüsselt"
        parts = [self.algorithm or "unbekannt"]
        if self.bits:
            parts.append(f"{self.bits} bit")
        if self.revision is not None:
            parts.append(f"R={self.revision}")
        if self.needs_user_password and not self.openable:
            parts.append("Passwort erforderlich")
        return " · ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


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


def needs_password(
    path: str | Path,
    *,
    timeout_sec: float | None = None,
) -> bool:
    """True, wenn das PDF ohne Passwort nicht öffnet.

    Timeout (Default aus limits.PASSWORD_PROBE_TIMEOUT_SEC): bei Hang → False
    (Open versucht Seite 1; Passwort-Dialog bei Render-Fehler) — 2.6.45.
    """
    import threading

    path = Path(path)
    if timeout_sec is None:
        try:
            from .limits import PASSWORD_PROBE_TIMEOUT_SEC

            timeout_sec = float(PASSWORD_PROBE_TIMEOUT_SEC)
        except Exception:
            timeout_sec = 1.5

    box: dict = {}

    def _probe() -> None:
        try:
            import pikepdf
            from pikepdf import PasswordError

            try:
                with pikepdf.open(str(path)):
                    box["v"] = False
                    return
            except PasswordError:
                box["v"] = True
                return
            except Exception as e:
                msg = str(e).lower()
                box["v"] = (
                    "password" in msg or "passwd" in msg or "passwort" in msg
                )
                return
        except Exception:
            pass
        try:
            import pypdfium2 as pdfium

            doc = pdfium.PdfDocument(str(path))
            try:
                _ = len(doc)
            finally:
                doc.close()
            box["v"] = False
        except Exception as e:
            msg = str(e).lower()
            box["v"] = "password" in msg or "passwd" in msg

    t = threading.Thread(target=_probe, daemon=True, name="ild-pw-probe")
    t.start()
    t.join(max(0.05, float(timeout_sec)))
    if t.is_alive():
        # Hang → nicht blockieren; Open zeigt Passwort bei Bedarf
        return False
    return bool(box.get("v", False))


WRONG_PASSWORD_MSG_DE = "Falsches Passwort. Bitte erneut eingeben."


def is_wrong_password_error(message: str | Exception | None) -> bool:
    """Erkennt typische Passwort-Fehler (EN/DE) — 1.6.2."""
    msg = str(message or "").lower()
    if not msg:
        return False
    keys = (
        "password",
        "passwd",
        "passwort",
        "wrong password",
        "incorrect password",
        "invalid password",
        "authentication",
    )
    return any(k in msg for k in keys)


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
        if is_wrong_password_error(e):
            return False, WRONG_PASSWORD_MSG_DE
        return False, str(e)


def _permissions_to_pikepdf(flags: PdfPermissionFlags):
    import pikepdf

    # Highres impliziert Lowres (PDF/pikepdf); ohne Druck beide aus.
    print_low = bool(flags.allow_printing) or bool(flags.allow_print_highres)
    print_high = bool(flags.allow_print_highres) and print_low
    return pikepdf.Permissions(
        accessibility=bool(flags.allow_accessibility),
        extract=bool(flags.allow_extract),
        modify_annotation=bool(flags.allow_modify_annotation),
        modify_assembly=bool(flags.allow_modify_assembly),
        modify_form=bool(flags.allow_modify_form),
        modify_other=bool(flags.allow_modify),
        print_highres=print_high,
        print_lowres=print_low,
    )


def permissions_from_p(p_value: int) -> PdfPermissionFlags:
    """PDF /P Bitmaske → Flags (1-basierte Bits laut ISO 32000)."""

    def bit(n: int) -> bool:
        return bool(int(p_value) & (1 << (n - 1)))

    return PdfPermissionFlags(
        allow_printing=bit(3),
        allow_modify=bit(4),
        allow_extract=bit(5),
        allow_modify_annotation=bit(6),
        allow_modify_form=bit(9),
        allow_accessibility=bit(10),
        allow_modify_assembly=bit(11),
        allow_print_highres=bit(12),
    )


def algorithm_from_encryption(enc: Any) -> tuple[str, int | None, int | None]:
    """(algorithm_label, R, bits) aus pikepdf EncryptionInfo."""
    if enc is None:
        return "none", None, None
    r = getattr(enc, "R", None)
    bits = getattr(enc, "bits", None)
    method = getattr(enc, "stream_method", None)
    name = getattr(method, "name", str(method) if method is not None else "").lower()
    if "aesv3" in name or (bits == 256) or r == 6:
        return "AES-256", int(r) if r is not None else 6, int(bits) if bits else 256
    if "aesv2" in name or "aes" in name or r == 5 or bits == 128:
        return "AES-128", int(r) if r is not None else 5, int(bits) if bits else 128
    if "rc4" in name or (r is not None and int(r) <= 4):
        return "RC4", int(r) if r is not None else None, int(bits) if bits else None
    if bits == 256:
        return "AES-256", int(r) if r is not None else None, 256
    if bits == 128:
        return "AES-128", int(r) if r is not None else None, 128
    return "unknown", int(r) if r is not None else None, int(bits) if bits else None


def _probe_encrypt_hint(path: Path) -> tuple[str, int | None]:
    """Grobe Algorithmus-Erkennung ohne Entschlüsselung (Trailer-Heuristik)."""
    try:
        data = path.read_bytes()[:3_000_000]
    except Exception:
        return "unknown", None
    if b"/Encrypt" not in data and b"/Encrypt " not in data:
        # kann trotzdem verschlüsselt sein (xref); needs_password entscheidet
        pass
    if b"/AESV3" in data or b"/Length 256" in data:
        return "AES-256", 6
    if b"/AESV2" in data:
        return "AES-128", 5
    if b"/V 5" in data or b"/R 6" in data:
        return "AES-256", 6
    if b"/R 5" in data:
        return "AES-128", 5
    if b"/Standard" in data and (b"/Encrypt" in data or needs_password(path)):
        return "unknown", None
    return "unknown", None


def _flags_from_pikepdf_allow(allow) -> PdfPermissionFlags:
    """pikepdf.Permissions → PdfPermissionFlags."""
    return PdfPermissionFlags(
        allow_printing=bool(getattr(allow, "print_lowres", False)),
        allow_print_highres=bool(getattr(allow, "print_highres", False)),
        allow_modify=bool(getattr(allow, "modify_other", False)),
        allow_modify_annotation=bool(getattr(allow, "modify_annotation", False)),
        allow_modify_form=bool(getattr(allow, "modify_form", False)),
        allow_modify_assembly=bool(getattr(allow, "modify_assembly", False)),
        allow_extract=bool(getattr(allow, "extract", False)),
        allow_accessibility=bool(getattr(allow, "accessibility", True)),
    )


def get_encryption_info(
    path: str | Path,
    password: str | None = None,
) -> EncryptionInfo:
    """
    Verschlüsselungsstatus + Rechte lesen — 2.6.7.
    Ohne gültiges Passwort: encrypted/needs_user_password + Algorithmus-Hinweis.
    """
    import pikepdf

    path = Path(path)
    pw = password if password is not None else ""
    try:
        with pikepdf.open(path, password=pw or "") as pdf:
            if not bool(getattr(pdf, "is_encrypted", False)):
                return EncryptionInfo(
                    encrypted=False,
                    algorithm="none",
                    permissions=PdfPermissionFlags(
                        allow_printing=True,
                        allow_print_highres=True,
                        allow_modify=True,
                        allow_modify_annotation=True,
                        allow_modify_form=True,
                        allow_modify_assembly=True,
                        allow_extract=True,
                        allow_accessibility=True,
                    ),
                    needs_user_password=False,
                    openable=True,
                )
            enc = getattr(pdf, "encryption", None)
            algo, rev, bits = algorithm_from_encryption(enc)
            perms = None
            allow = getattr(pdf, "allow", None)
            if allow is not None:
                perms = _flags_from_pikepdf_allow(allow)
            elif enc is not None and getattr(enc, "P", None) is not None:
                perms = permissions_from_p(int(enc.P))
            return EncryptionInfo(
                encrypted=True,
                algorithm=algo,
                revision=rev,
                bits=bits,
                permissions=perms,
                needs_user_password=bool(needs_password(path)),
                openable=True,
            )
    except Exception as e:
        if needs_password(path) or is_wrong_password_error(e):
            algo, rev = _probe_encrypt_hint(path)
            return EncryptionInfo(
                encrypted=True,
                algorithm=algo,
                revision=rev,
                bits=256 if algo == "AES-256" else (128 if algo == "AES-128" else None),
                permissions=None,
                needs_user_password=True,
                openable=False,
            )
        raise


def get_permissions(
    path: str | Path,
    password: str | None = None,
) -> PdfPermissionFlags | None:
    """Aktuelle Permission-Flags oder None wenn nicht lesbar."""
    info = get_encryption_info(path, password=password)
    return info.permissions


def _build_encryption(
    *,
    user_password: str,
    owner_password: str,
    flags: PdfPermissionFlags,
    prefer_aes256: bool = True,
):
    import pikepdf

    allow = _permissions_to_pikepdf(flags)
    revisions = (
        (PREFERRED_ENCRYPTION_R, FALLBACK_ENCRYPTION_R)
        if prefer_aes256
        else (FALLBACK_ENCRYPTION_R, PREFERRED_ENCRYPTION_R)
    )
    last_err: Exception | None = None
    for r in revisions:
        try:
            return pikepdf.Encryption(
                owner=owner_password,
                user=user_password,
                R=r,  # type: ignore[arg-type]
                allow=allow,
                aes=True,
            )
        except Exception as e:
            last_err = e
            continue
    if last_err:
        raise last_err
    raise RuntimeError("Verschlüsselung konnte nicht erzeugt werden.")


def set_password(
    pdf_path: str | Path,
    *,
    user_password: str,
    owner_password: str | None = None,
    out_path: str | Path | None = None,
    allow_printing: bool = True,
    allow_modify: bool = False,
    allow_extract: bool = False,
    permissions: PdfPermissionFlags | dict[str, Any] | None = None,
    aes256: bool = True,
    open_password: str | None = None,
) -> Path:
    """
    Speichert das PDF mit User-/Owner-Passwort.
    Bevorzugt AES-256 (R=6 / AESV3); Fallback AES-128 (R=5) wenn nötig — 2.6.7.
    user_password: zum Öffnen. owner_password: optional (default = user).
    permissions: granulare Rechte; sonst Legacy allow_* Flags.
    open_password: falls Quell-PDF bereits geschützt.
    """
    import pikepdf

    pdf_path = Path(pdf_path)
    out_path = Path(out_path) if out_path else pdf_path
    owner = owner_password if owner_password is not None else user_password
    if not (user_password or "").strip():
        raise ValueError("User-Passwort darf nicht leer sein.")

    if isinstance(permissions, PdfPermissionFlags):
        flags = permissions
    elif isinstance(permissions, dict):
        flags = PdfPermissionFlags.from_mapping(permissions)
    else:
        flags = PdfPermissionFlags.from_legacy(
            allow_printing=allow_printing,
            allow_modify=allow_modify,
            allow_extract=allow_extract,
        )

    enc = _build_encryption(
        user_password=user_password,
        owner_password=owner,
        flags=flags,
        prefer_aes256=bool(aes256),
    )
    open_kw: dict[str, Any] = {
        "allow_overwriting_input": (out_path.resolve() == pdf_path.resolve()),
    }
    if open_password:
        open_kw["password"] = open_password
    with pikepdf.open(pdf_path, **open_kw) as pdf:
        pdf.save(out_path, encryption=enc)
    return out_path


def update_permissions(
    pdf_path: str | Path,
    *,
    user_password: str,
    owner_password: str,
    permissions: PdfPermissionFlags | dict[str, Any],
    out_path: str | Path | None = None,
    aes256: bool = True,
    open_password: str | None = None,
) -> Path:
    """
    Rechte an einem bereits geschützten PDF ändern (neu verschlüsseln) — 2.6.7.
    Owner- und User-Passwort erforderlich; open_password falls abweichend.
    """
    if isinstance(permissions, dict):
        flags = PdfPermissionFlags.from_mapping(permissions)
    else:
        flags = permissions
    if not (user_password or "").strip():
        raise ValueError("User-Passwort darf nicht leer sein.")
    if not (owner_password or "").strip():
        raise ValueError("Owner-Passwort darf nicht leer sein.")
    return set_password(
        pdf_path,
        user_password=user_password,
        owner_password=owner_password,
        out_path=out_path,
        permissions=flags,
        aes256=aes256,
        open_password=open_password or user_password or owner_password,
    )


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
