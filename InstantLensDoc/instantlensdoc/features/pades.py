"""PAdES-B-Signatur (PKCS#12) + Validierung. QES nur mit QTSP-Zertifikat.

Neues Modul — ild_pdf.esign (Sidecar-AES) bleibt unangetastet.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

QES_NOTE = (
    "Qualifizierte elektronische Signatur (QES) nach eIDAS erfordert ein "
    "qualifiziertes Zertifikat bzw. Token eines QTSP. InstantLens Doc erzeugt "
    "PAdES-B mit dem vorgelegten PKCS#12 — die rechtliche Qualifikation hängt "
    "vom Zertifikat ab, nicht von diesem Dialog."
)


def generate_self_signed_p12(
    dest: str | Path,
    *,
    password: str = "test",
    common_name: str = "InstantLens Doc Test",
) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    blob = pkcs12.serialize_key_and_certificates(
        name=b"ild-pades-test",
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode("utf-8")),
    )
    dest.write_bytes(blob)
    return dest


def _load_signer(p12_path: str | Path, password: str):
    from pyhanko.sign.signers import SimpleSigner

    return SimpleSigner.load_pkcs12(
        str(p12_path),
        passphrase=(password or "").encode("utf-8") or None,
    )


def sign_pades_b(
    pdf_path: str | Path,
    p12_path: str | Path,
    password: str,
    *,
    out_path: str | Path | None = None,
    field_name: str = "Signature1",
    box: tuple[int, int, int, int] = (50, 50, 250, 120),
    page: int = 0,
    reason: str = "PAdES-B",
    location: str = "",
    contact: str = "",
    name: str = "",
) -> dict[str, Any]:
    """Inkrementelle PAdES-B-Signatur mit sichtbarem Widget (pyhanko)."""
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import fields, signers
    from pyhanko.sign.fields import SigFieldSpec
    from pyhanko.stamp import TextStampStyle

    src = Path(pdf_path)
    dest = Path(out_path) if out_path else src.with_name(src.stem + "_pades.pdf")
    dest.parent.mkdir(parents=True, exist_ok=True)
    signer = _load_signer(p12_path, password)
    meta = signers.PdfSignatureMetadata(
        field_name=field_name,
        md_algorithm="sha256",
        reason=reason or "PAdES-B",
        location=location or None,
        contact_info=contact or None,
        name=name or None,
        subfilter=fields.SigSeedSubFilter.PADES,
        embed_validation_info=False,
        use_pades_lta=False,
    )
    spec = SigFieldSpec(sig_field_name=field_name, on_page=int(page), box=tuple(int(x) for x in box))
    style = TextStampStyle(
        stamp_text="Signiert (PAdES-B)\n%(ts)s",
    )
    with src.open("rb") as inf:
        w = IncrementalPdfFileWriter(inf)
        pdf_signer = signers.PdfSigner(
            meta, signer=signer, stamp_style=style, new_field_spec=spec
        )
        with dest.open("wb") as outf:
            pdf_signer.sign_pdf(w, output=outf)
    return {
        "ok": True,
        "out": str(dest),
        "field": field_name,
        "profile": "PAdES-B",
        "qes_note": QES_NOTE,
        "visible_widget": True,
    }


def validate_pades(
    pdf_path: str | Path,
    *,
    p12_path: str | Path | None = None,
    password: str = "",
) -> dict[str, Any]:
    """Signaturen lesen, Kette/Trust-Status (self-signed = trusted nur gegen eigenes Cert)."""
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature
    from pyhanko_certvalidator import ValidationContext

    trust_roots = []
    if p12_path:
        signer = _load_signer(p12_path, password)
        if signer and signer.signing_cert:
            trust_roots.append(signer.signing_cert)
    vc = ValidationContext(trust_roots=trust_roots) if trust_roots else ValidationContext()
    results = []
    with Path(pdf_path).open("rb") as inf:
        reader = PdfFileReader(inf)
        sigs = list(reader.embedded_signatures or [])
        if not sigs:
            return {
                "ok": False,
                "count": 0,
                "signatures": [],
                "message": "Keine eingebetteten PDF-Signaturen (ByteRange/PAdES).",
                "qes_note": QES_NOTE,
            }
        for sig in sigs:
            try:
                status = validate_pdf_signature(sig, signer_validation_context=vc, skip_diff=True)
                trusted = bool(getattr(status, "trusted", False))
                bottom = bool(getattr(status, "bottom_line", False))
                results.append(
                    {
                        "field": getattr(sig, "field_name", "") or "",
                        "trusted": trusted,
                        "bottom_line": bottom,
                        "summary": str(getattr(status, "summary", "") or ""),
                        "coverage": str(getattr(status, "coverage", "") or ""),
                        "revoked": bool(getattr(status, "revoked", False)),
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "field": getattr(sig, "field_name", "") or "",
                        "trusted": False,
                        "bottom_line": False,
                        "summary": str(exc),
                        "error": True,
                    }
                )
    ok = any(r.get("bottom_line") or r.get("trusted") for r in results) or any(
        not r.get("error") for r in results
    )
    return {
        "ok": bool(ok),
        "count": len(results),
        "signatures": results,
        "qes_note": QES_NOTE,
        "trust_roots": len(trust_roots),
        "message": "Kette gegen vorgelegtes PKCS#12 geprüft" if trust_roots else "Ohne Trust-Anker (self-signed erscheint untrusted — Zertifikat übergeben).",
    }


def make_blank_pdf(path: str | Path) -> Path:
    """Minimale eine-Seite-PDF (pikepdf, nicht ild_pdf-Writer)."""
    import pikepdf

    dest = Path(path)
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(595, 842))
    pdf.save(dest)
    return dest
