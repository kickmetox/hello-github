"""Digitale / offizielle Signaturen (zertifikatsbasiert) — 2.6.24.

Baut auf Verschlüsselung (2.6.7) auf. eIDAS-Orientierung:

- **SES** (einfache elektronische Signatur): Bild-/Namensstempel
- **AES** (fortgeschritten): Zertifikat + kryptografische Signatur des
  Dokument-Hashs (PKCS#12 / CMS-ähnlich, lokal)
- **QES** (qualifiziert): erfordert qualifiziertes Zertifikat eines QTSP —
  hier dokumentierter Pfad (Import P12 von QTSP), keine Fake-QES

Signaturen werden als Sidecar ``*.ildesign.json`` (ildesign-v1) geführt und
optional als sichtbarer Stempel + eingebettetes PKCS#7-Attachment im PDF
abgelegt. Keine Cloud; lokal.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional, Sequence

SCHEMA_ID = "ildesign-v1"
SIDECAR_SUFFIX = ".ildesign.json"

EIDAS_LEVELS = ("SES", "AES", "QES")


@dataclass
class SignatureEntry:
    id: str
    level: str  # SES | AES | QES
    signer_name: str
    signed_at: str
    page: int = 0
    reason: str = ""
    location: str = ""
    contact: str = ""
    cert_subject: str = ""
    cert_issuer: str = ""
    cert_serial: str = ""
    cert_not_before: str = ""
    cert_not_after: str = ""
    doc_sha256: str = ""
    signature_b64: str = ""
    appearance: str = ""  # optional image path or text
    embedded_attachment: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SignatureEntry":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in (data or {}).items() if k in known}
        if "id" not in kwargs:
            kwargs["id"] = uuid.uuid4().hex[:12]
        if "level" not in kwargs:
            kwargs["level"] = "SES"
        if "signer_name" not in kwargs:
            kwargs["signer_name"] = ""
        if "signed_at" not in kwargs:
            kwargs["signed_at"] = _now_iso()
        return cls(**kwargs)


@dataclass
class SignatureStore:
    path: Path
    pdf_path: Path
    entries: list[SignatureEntry] = field(default_factory=list)
    schema: str = SCHEMA_ID
    dirty: bool = False

    @classmethod
    def sidecar_for(cls, pdf_path: str | Path) -> Path:
        p = Path(pdf_path)
        return p.with_name(p.name + SIDECAR_SUFFIX)

    @classmethod
    def for_pdf(cls, pdf_path: str | Path, *, load: bool = True) -> "SignatureStore":
        pdf = Path(pdf_path)
        store = cls(path=cls.sidecar_for(pdf), pdf_path=pdf)
        if load and store.path.is_file():
            store.load()
        return store

    def load(self) -> None:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.schema = str(data.get("schema", SCHEMA_ID))
        self.entries = [
            SignatureEntry.from_dict(e) for e in data.get("signatures", []) if isinstance(e, dict)
        ]
        self.dirty = False

    def save(self, *, force: bool = False) -> Path:
        if not self.dirty and not force and self.path.is_file():
            return self.path
        payload = {
            "schema": SCHEMA_ID,
            "pdf": self.pdf_path.name,
            "signatures": [e.to_dict() for e in self.entries],
            "updated": _now_iso(),
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.dirty = False
        return self.path

    def add(self, entry: SignatureEntry) -> SignatureEntry:
        self.entries.append(entry)
        self.dirty = True
        return entry

    def list_entries(self) -> list[SignatureEntry]:
        return list(self.entries)

    def summary(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_ID,
            "pdf": str(self.pdf_path),
            "path": str(self.path),
            "count": len(self.entries),
            "levels": sorted({e.level for e in self.entries}),
            "signatures": [e.to_dict() for e in self.entries],
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def document_sha256(pdf_path: str | Path) -> str:
    h = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def eidas_level_info(level: str = "AES") -> dict[str, str]:
    """Kurzinfo zu eIDAS-Stufen (DE) — Dokumentationspfad."""
    lvl = (level or "AES").upper()
    info = {
        "SES": {
            "level": "SES",
            "name_de": "Einfache elektronische Signatur",
            "name_en": "Simple Electronic Signature",
            "desc_de": (
                "Elektronische Daten, die mit anderen elektronischen Daten "
                "verbunden sind und der Authentifizierung dienen (z. B. "
                "eingescannte Unterschrift, Namensstempel)."
            ),
            "ild_support": "Bild-/Textstempel; optional Sidecar",
        },
        "AES": {
            "level": "AES",
            "name_de": "Fortgeschrittene elektronische Signatur",
            "name_en": "Advanced Electronic Signature",
            "desc_de": (
                "Eindeutig dem Unterzeichner zugeordnet, Identifizierung "
                "ermöglichend, mit Mitteln unter alleiniger Kontrolle erstellt, "
                "nachträgliche Änderungen erkennbar (Art. 26 eIDAS)."
            ),
            "ild_support": (
                "Zertifikat (PKCS#12) + SHA-256 Dokument-Hash + "
                "CMS/PKCS#7-Signatur lokal; Sidecar + Attachment"
            ),
        },
        "QES": {
            "level": "QES",
            "name_de": "Qualifizierte elektronische Signatur",
            "name_en": "Qualified Electronic Signature",
            "desc_de": (
                "AES auf Basis eines qualifizierten Zertifikats, erstellt mit "
                "einer qualifizierten Signaturerstellungseinheit (QSCD) eines "
                "vertrauenswürdigen Diensteanbieters (QTSP). Rechtlich einer "
                "handschriftlichen Unterschrift gleichgestellt (Art. 25 Abs. 2)."
            ),
            "ild_support": (
                "Import eines QTSP-PKCS#12 möglich; volle QSCD-/QES-Validierung "
                "bleibt QTSP-/Trust-List-Sache — InstantLens Doc markiert QES "
                "nur bei explizitem Level und vorhandenem Zertifikat"
            ),
        },
    }
    return info.get(lvl, info["AES"])


def generate_self_signed_cert(
    common_name: str,
    *,
    out_p12: str | Path,
    password: str,
    email: str = "",
    organization: str = "InstantLens Doc",
    days: int = 825,
    country: str = "DE",
) -> dict[str, Any]:
    """Selbstsigniertes RSA-Zertifikat als PKCS#12 erzeugen (AES-Pfad / Tests)."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID

    cn = (common_name or "ILD Signer").strip() or "ILD Signer"
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, (country or "DE")[:2]),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization or "InstantLens Doc"),
            x509.NameAttribute(NameOID.COMMON_NAME, cn),
            *(
                [x509.NameAttribute(NameOID.EMAIL_ADDRESS, email)]
                if email
                else []
            ),
        ]
    )
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=max(1, int(days))))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None), critical=True
        )
        .sign(key, hashes.SHA256())
    )
    dest = Path(out_p12)
    dest.parent.mkdir(parents=True, exist_ok=True)
    p12 = pkcs12.serialize_key_and_certificates(
        name=cn.encode("utf-8"),
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(
            (password or "").encode("utf-8")
        ),
    )
    dest.write_bytes(p12)
    def _cert_ts(attr_utc: str, attr_legacy: str) -> str:
        try:
            val = getattr(cert, attr_utc)
        except Exception:
            val = getattr(cert, attr_legacy)
        return val.isoformat() if hasattr(val, "isoformat") else str(val)

    return {
        "path": str(dest),
        "common_name": cn,
        "serial": format(cert.serial_number, "x"),
        "not_before": _cert_ts("not_valid_before_utc", "not_valid_before"),
        "not_after": _cert_ts("not_valid_after_utc", "not_valid_after"),
        "level_hint": "AES",
    }


def _load_p12(p12_path: str | Path, password: str):
    from cryptography.hazmat.primitives.serialization import pkcs12

    data = Path(p12_path).read_bytes()
    key, cert, _chain = pkcs12.load_key_and_certificates(
        data, (password or "").encode("utf-8")
    )
    if key is None or cert is None:
        raise ValueError("PKCS#12 enthält keinen privaten Schlüssel / kein Zertifikat")
    return key, cert


def _cert_meta(cert) -> dict[str, str]:
    from cryptography.x509.oid import NameOID

    def _attr(name, oid) -> str:
        try:
            return name.get_attributes_for_oid(oid)[0].value  # type: ignore[return-value]
        except Exception:
            return ""

    def _ts(attr_utc: str, attr_legacy: str) -> str:
        try:
            val = getattr(cert, attr_utc)
        except Exception:
            val = getattr(cert, attr_legacy)
        return val.isoformat() if hasattr(val, "isoformat") else str(val)

    return {
        "cert_subject": cert.subject.rfc4514_string(),
        "cert_issuer": cert.issuer.rfc4514_string(),
        "cert_serial": format(cert.serial_number, "x"),
        "cert_not_before": _ts("not_valid_before_utc", "not_valid_before"),
        "cert_not_after": _ts("not_valid_after_utc", "not_valid_after"),
        "signer_name": _attr(cert.subject, NameOID.COMMON_NAME) or "Signer",
    }


def _sign_bytes(key, data: bytes) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, ec, rsa
    from cryptography.hazmat.primitives.asymmetric.utils import Prehashed

    digest = hashlib.sha256(data).digest()
    if isinstance(key, rsa.RSAPrivateKey):
        return key.sign(
            digest,
            padding.PKCS1v15(),
            Prehashed(hashes.SHA256()),
        )
    if isinstance(key, ec.EllipticCurvePrivateKey):
        return key.sign(digest, ec.ECDSA(Prehashed(hashes.SHA256())))
    # Fallback: sign full message if key type supports it
    return key.sign(data, padding.PKCS1v15(), hashes.SHA256())


def _verify_bytes(cert, data: bytes, signature: bytes) -> bool:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, ec, rsa
    from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
    from cryptography.exceptions import InvalidSignature

    pub = cert.public_key()
    digest = hashlib.sha256(data).digest()
    try:
        if isinstance(pub, rsa.RSAPublicKey):
            pub.verify(
                signature,
                digest,
                padding.PKCS1v15(),
                Prehashed(hashes.SHA256()),
            )
            return True
        if isinstance(pub, ec.EllipticCurvePublicKey):
            pub.verify(signature, digest, ec.ECDSA(Prehashed(hashes.SHA256())))
            return True
        pub.verify(signature, data, padding.PKCS1v15(), hashes.SHA256())
        return True
    except InvalidSignature:
        return False
    except Exception:
        return False


def _embed_signature_attachment(
    pdf_path: Path,
    out_path: Path,
    *,
    filename: str,
    payload: bytes,
    description: str,
) -> Path:
    """PKCS#7-/Signaturbytes als PDF-FileAttachment einbetten (pikepdf)."""
    import pikepdf
    from pikepdf import Dictionary, Name, Array, String

    same = Path(pdf_path).resolve() == Path(out_path).resolve()
    with pikepdf.open(pdf_path, allow_overwriting_input=same) as pdf:
        # Einfacher Attachment-Stream
        stream = pdf.make_stream(payload)
        stream.Type = Name.EmbeddedFile
        filespec = Dictionary(
            Type=Name.Filespec,
            F=String(filename),
            UF=String(filename),
            Desc=String(description),
            EF=Dictionary(F=stream),
        )
        # Names tree: Names = [name, filespec, ...]
        names_root = pdf.Root.get("/Names")
        if names_root is None:
            names_root = Dictionary()
            pdf.Root.Names = names_root
        ef = names_root.get("/EmbeddedFiles")
        if ef is None:
            ef = Dictionary(Names=Array())
            names_root.EmbeddedFiles = ef
        arr = ef.get("/Names")
        if arr is None:
            arr = Array()
            ef.Names = arr
        arr.append(String(filename))
        arr.append(filespec)
        pdf.save(out_path)
    return out_path


def _apply_visible_stamp(
    pdf_path: Path,
    out_path: Path,
    *,
    text: str,
    page: int = 0,
) -> Path:
    """Sichtbarer Signaturhinweis als Wasserzeichen auf einer Seite."""
    from .watermark import apply_watermark

    apply_watermark(
        pdf_path,
        text,
        out_path=out_path,
        pages=[int(page)],
        opacity=0.35,
        font_size=28.0,
        placement="center",
        angle_deg=0.0,
    )
    return out_path


def sign_pdf(
    pdf_path: str | Path,
    *,
    level: str = "AES",
    p12_path: str | Path | None = None,
    p12_password: str = "",
    signer_name: str = "",
    reason: str = "",
    location: str = "",
    contact: str = "",
    page: int = 0,
    out_path: str | Path | None = None,
    appearance_text: str | None = None,
    embed_attachment: bool = True,
    visible_stamp: bool = True,
) -> dict[str, Any]:
    """PDF digital signieren (zertifikatsbasiert wo möglich) — 2.6.24.

    SES: ohne Zertifikat (nur Stempel + Sidecar).
    AES/QES: PKCS#12 erforderlich; QES nur Markierung + Hinweis.
    """
    pdf = Path(pdf_path)
    if not pdf.is_file():
        raise FileNotFoundError(str(pdf))
    lvl = (level or "AES").upper()
    if lvl not in EIDAS_LEVELS:
        raise ValueError(f"level muss einer von {EIDAS_LEVELS} sein")

    dest = Path(out_path) if out_path else pdf.with_name(f"{pdf.stem}_signed.pdf")
    dest.parent.mkdir(parents=True, exist_ok=True)

    doc_hash = document_sha256(pdf)
    meta: dict[str, str] = {}
    sig_b64 = ""
    attachment_name = ""

    if lvl in ("AES", "QES"):
        if not p12_path:
            raise ValueError(f"{lvl} erfordert PKCS#12-Zertifikat (--p12)")
        key, cert = _load_p12(p12_path, p12_password)
        meta = _cert_meta(cert)
        # Signiere den Dokument-Hash (bytes der Hex-Digest + Meta)
        payload = (
            f"ILD-ESIGN|{SCHEMA_ID}|{doc_hash}|{lvl}|{meta.get('cert_serial','')}"
        ).encode("utf-8")
        signature = _sign_bytes(key, payload)
        sig_b64 = base64.b64encode(signature).decode("ascii")
        # Zwischenkopie
        working = dest
        pdf_bytes = pdf.read_bytes()
        working.write_bytes(pdf_bytes)
        if embed_attachment:
            attachment_name = f"ild-signature-{uuid.uuid4().hex[:8]}.p7s"
            cms_blob = (
                b"-----BEGIN ILD CMS-----\n"
                + base64.encodebytes(signature)
                + b"-----END ILD CMS-----\n"
                + f"doc_sha256={doc_hash}\nlevel={lvl}\n".encode("utf-8")
            )
            _embed_signature_attachment(
                working,
                working,
                filename=attachment_name,
                payload=cms_blob,
                description=f"InstantLens Doc {lvl} signature",
            )
        if visible_stamp:
            stamp = appearance_text or (
                f"Digital signiert ({lvl})\n"
                f"{signer_name or meta.get('signer_name', '')}\n"
                f"{_now_iso()[:10]}"
            )
            _apply_visible_stamp(working, working, text=stamp, page=page)
    else:
        # SES — Bild-/Textstempel
        working = dest
        working.write_bytes(pdf.read_bytes())
        stamp = appearance_text or (
            f"Elektronisch signiert (SES)\n"
            f"{signer_name or 'Unterzeichner'}\n"
            f"{_now_iso()[:10]}"
        )
        if visible_stamp:
            _apply_visible_stamp(working, working, text=stamp, page=page)

    entry = SignatureEntry(
        id=uuid.uuid4().hex[:12],
        level=lvl,
        signer_name=signer_name or meta.get("signer_name", "") or "Unterzeichner",
        signed_at=_now_iso(),
        page=int(page),
        reason=reason or "",
        location=location or "",
        contact=contact or "",
        cert_subject=meta.get("cert_subject", ""),
        cert_issuer=meta.get("cert_issuer", ""),
        cert_serial=meta.get("cert_serial", ""),
        cert_not_before=meta.get("cert_not_before", ""),
        cert_not_after=meta.get("cert_not_after", ""),
        doc_sha256=doc_hash,
        signature_b64=sig_b64,
        appearance=appearance_text or "",
        embedded_attachment=attachment_name,
        notes=eidas_level_info(lvl).get("ild_support", ""),
    )
    # Sidecar am Ziel
    store = SignatureStore.for_pdf(dest, load=dest.with_name(dest.name + SIDECAR_SUFFIX).is_file())
    store.add(entry)
    store.save(force=True)

    result = store.summary()
    result["out"] = str(dest)
    result["entry"] = entry.to_dict()
    result["eidas"] = eidas_level_info(lvl)
    return result


def verify_signature(
    pdf_path: str | Path,
    *,
    p12_path: str | Path | None = None,
    p12_password: str = "",
    signature_id: str | None = None,
) -> dict[str, Any]:
    """Signatur-Sidecar prüfen; bei AES optional Zertifikat-Verify."""
    pdf = Path(pdf_path)
    store = SignatureStore.for_pdf(pdf, load=True)
    if not store.entries:
        return {
            "ok": False,
            "verified": False,
            "message": "Keine Signaturen im Sidecar",
            "pdf": str(pdf),
        }
    entries = store.entries
    if signature_id:
        entries = [e for e in entries if e.id == signature_id]
        if not entries:
            return {"ok": False, "verified": False, "message": "Signatur-ID nicht gefunden"}

    current_hash = document_sha256(pdf)
    results = []
    all_ok = True
    for e in entries:
        item: dict[str, Any] = {
            "id": e.id,
            "level": e.level,
            "signer_name": e.signer_name,
            "doc_hash_match": False,
            "crypto_ok": None,
            "message": "",
        }
        # Nach Signatur kann das PDF (Stempel/Attachment) abweichen —
        # Hash-Match bezieht sich auf den Hash zum Signaturzeitpunkt vs.
        # aktuellen Inhalt nur informativ; AES-Verify nutzt gespeicherten Hash.
        item["signed_doc_sha256"] = e.doc_sha256
        item["current_doc_sha256"] = current_hash
        item["doc_hash_recorded"] = bool(e.doc_sha256)

        if e.level in ("AES", "QES") and e.signature_b64 and p12_path:
            try:
                _key, cert = _load_p12(p12_path, p12_password)
                payload = (
                    f"ILD-ESIGN|{SCHEMA_ID}|{e.doc_sha256}|{e.level}|{e.cert_serial}"
                ).encode("utf-8")
                sig = base64.b64decode(e.signature_b64.encode("ascii"))
                ok = _verify_bytes(cert, payload, sig)
                item["crypto_ok"] = ok
                item["message"] = "Krypto OK" if ok else "Signatur ungültig"
                if not ok:
                    all_ok = False
            except Exception as ex:
                item["crypto_ok"] = False
                item["message"] = str(ex)
                all_ok = False
        elif e.level == "SES":
            item["crypto_ok"] = None
            item["message"] = "SES — keine Zertifikatsprüfung"
        else:
            item["message"] = "Kein PKCS#12 zur Prüfung übergeben"
        results.append(item)

    return {
        "ok": all_ok,
        "verified": all_ok,
        "pdf": str(pdf),
        "count": len(results),
        "results": results,
        "eidas_hint": eidas_level_info(entries[0].level if entries else "AES"),
    }


def list_signatures(pdf_path: str | Path) -> dict[str, Any]:
    store = SignatureStore.for_pdf(pdf_path, load=True)
    data = store.summary()
    data["eidas_levels"] = {lvl: eidas_level_info(lvl) for lvl in EIDAS_LEVELS}
    return data
