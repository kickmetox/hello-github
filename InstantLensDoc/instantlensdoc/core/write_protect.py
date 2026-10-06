"""Schreibschutz wie Word: DOCX documentProtection, PDF /Encrypt, TXT-Sidecar."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

REASON_WRITE_PROTECT = "Dokument ist schreibgeschützt"
SIDECAR_SUFFIX = ".ildprotect.json"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"
_PDF_OWNER_SENTINEL = "ild-write-protect"

ET.register_namespace("w", W_NS)


@dataclass(frozen=True)
class ProtectionInfo:
    protected: bool = False
    password_hash: str = ""
    source: str = ""  # sidecar | docx | pdf | ""


def sidecar_path_for(path: str | Path | None) -> Path | None:
    if not path:
        return None
    p = Path(path)
    return Path(str(p) + SIDECAR_SUFFIX)


def password_hash(password: str | None) -> str:
    raw = str(password or "")
    if raw == "":
        return ""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_password(stored_hash: str | None, password: str | None) -> bool:
    want = str(stored_hash or "")
    got = password_hash(password)
    if want == "":
        return got == ""
    return want == got


def load_sidecar(path: str | Path | None) -> dict[str, Any]:
    src = sidecar_path_for(path)
    if src is None or not src.is_file():
        return {}
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_sidecar(
    path: str | Path | None,
    *,
    protected: bool,
    password_hash_value: str = "",
) -> Path | None:
    src = sidecar_path_for(path)
    if src is None:
        return None
    if not protected:
        try:
            if src.is_file():
                src.unlink()
        except OSError:
            pass
        return None
    payload = {
        "schema": "ild-write-protect",
        "version": 1,
        "protected": True,
        "password_hash": str(password_hash_value or ""),
    }
    src.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return src


def detect_docx_protection(path: str | Path) -> bool:
    p = Path(path)
    if not p.is_file():
        return False
    try:
        with zipfile.ZipFile(p) as zf:
            raw = zf.read("word/settings.xml")
    except Exception:
        return False
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return False
    for el in root.iter(f"{W}documentProtection"):
        enf = (
            el.get(f"{W}enforcement")
            or el.get("w:enforcement")
            or el.get("enforcement")
            or ""
        )
        if str(enf).strip() in {"1", "true", "True"}:
            return True
    return False


def _rewrite_docx_member(path: Path, member: str, transform) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(path, "r") as zin:
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            found = False
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename == member:
                    found = True
                    data = transform(data)
                zout.writestr(info, data)
            if not found:
                zout.writestr(member, transform(b""))
    path.write_bytes(buf.getvalue())


def apply_docx_protection(path: str | Path) -> None:
    p = Path(path)
    if not p.is_file():
        return

    def _add(raw: bytes) -> bytes:
        if not raw:
            root = ET.Element(f"{W}settings")
        else:
            try:
                root = ET.fromstring(raw)
            except ET.ParseError:
                root = ET.Element(f"{W}settings")
        for el in list(root):
            if el.tag == f"{W}documentProtection":
                root.remove(el)
        prot = ET.Element(f"{W}documentProtection")
        prot.set(f"{W}edit", "readOnly")
        prot.set(f"{W}enforcement", "1")
        root.insert(0, prot)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    _rewrite_docx_member(p, "word/settings.xml", _add)


def remove_docx_protection(path: str | Path) -> None:
    p = Path(path)
    if not p.is_file():
        return

    def _drop(raw: bytes) -> bytes:
        if not raw:
            return raw
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            return raw
        changed = False
        for el in list(root):
            if el.tag == f"{W}documentProtection":
                root.remove(el)
                changed = True
        if not changed:
            return raw
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    try:
        _rewrite_docx_member(p, "word/settings.xml", _drop)
    except Exception:
        pass


def detect_pdf_encrypt(path: str | Path) -> bool:
    p = Path(path)
    if not p.is_file():
        return False
    try:
        from ild_pdf.security import needs_password

        return bool(needs_password(p))
    except Exception:
        pass
    try:
        data = p.read_bytes()[: 256 * 1024]
    except OSError:
        return False
    return b"/Encrypt" in data


def apply_pdf_encrypt(path: str | Path, password: str | None = None) -> bool:
    """PDF /Encrypt: öffnen ohne User-Passwort, Ändern gesperrt. Leeres Passwort ok."""
    p = Path(path)
    if not p.is_file():
        return False
    owner = str(password or "") or _PDF_OWNER_SENTINEL
    try:
        import pikepdf
        from ild_pdf.security import PdfPermissionFlags, _build_encryption
    except Exception:
        return False
    flags = PdfPermissionFlags(
        allow_printing=True,
        allow_print_highres=True,
        allow_modify=False,
        allow_modify_annotation=False,
        allow_modify_form=False,
        allow_modify_assembly=False,
        allow_extract=True,
        allow_accessibility=True,
    )
    try:
        enc = _build_encryption(
            user_password="",
            owner_password=owner,
            flags=flags,
        )
    except Exception:
        return False
    try:
        with pikepdf.open(p, allow_overwriting_input=True) as pdf:
            pdf.save(p, encryption=enc)
        return True
    except Exception:
        try:
            with pikepdf.open(p, password=owner, allow_overwriting_input=True) as pdf:
                pdf.save(p, encryption=enc)
            return True
        except Exception:
            return False


def remove_pdf_encrypt(path: str | Path, password: str | None = None) -> bool:
    p = Path(path)
    if not p.is_file():
        return False
    try:
        import pikepdf
    except Exception:
        return False
    owners = []
    if password:
        owners.append(str(password))
    owners.extend(["", _PDF_OWNER_SENTINEL])
    last = None
    for owner in owners:
        try:
            kw: dict[str, Any] = {"allow_overwriting_input": True}
            if owner:
                kw["password"] = owner
            with pikepdf.open(p, **kw) as pdf:
                pdf.save(p, encryption=False)
            return True
        except Exception as exc:
            last = exc
            continue
    return False


def detect_protection(path: str | Path | None) -> ProtectionInfo:
    if not path:
        return ProtectionInfo()
    p = Path(path)
    side = load_sidecar(p)
    side_on = bool(side.get("protected"))
    side_hash = str(side.get("password_hash") or "")
    if side_on:
        return ProtectionInfo(True, side_hash, "sidecar")
    suffix = p.suffix.lower()
    if suffix == ".docx" and detect_docx_protection(p):
        return ProtectionInfo(True, "", "docx")
    if suffix == ".pdf" and detect_pdf_encrypt(p):
        return ProtectionInfo(True, "", "pdf")
    return ProtectionInfo()


def persist_protection(
    path: str | Path | None,
    *,
    kind: str = "",
    protected: bool,
    password_hash_value: str = "",
    password: str | None = None,
) -> None:
    if not path:
        return
    p = Path(path)
    suffix = p.suffix.lower()
    kind_u = str(kind or "").upper()
    if protected:
        save_sidecar(p, protected=True, password_hash_value=password_hash_value)
        if suffix == ".docx" or kind_u == "DOCX":
            apply_docx_protection(p)
        elif suffix == ".pdf" or kind_u == "PDF":
            apply_pdf_encrypt(p, password)
    else:
        save_sidecar(p, protected=False)
        if suffix == ".docx" or kind_u == "DOCX":
            remove_docx_protection(p)
        elif suffix == ".pdf" or kind_u == "PDF":
            remove_pdf_encrypt(p, password)
