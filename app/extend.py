"""Versionen, Verknüpfungen, Felder, Sichten, Regeln und Posteingangs-Wächter."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from datetime import date

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.config import ALLOWED_EXTENSIONS, settings
from app.database import SessionLocal
from app.extract import extension_of, extract_text, safe_original_name
from app.models import Document, DocumentLink, DocumentVersion, FieldDef, FieldValue, SavedView, Tag, User, WorkflowRule
from app.services import DocManError, audit, get_document, rebuild_index, scan_inbox
from app.timeutil import utcnow

logger = logging.getLogger("docman")

STATUSES = ("neu", "geprueft", "freigegeben", "bezahlt", "abgelegt")
FIELD_KINDS = ("text", "number", "date")
STATUS_LABELS = {
    "neu": "Neu",
    "geprueft": "Geprüft",
    "freigegeben": "Freigegeben",
    "bezahlt": "Bezahlt",
    "abgelegt": "Abgelegt",
}

_stop = threading.Event()
_thread: threading.Thread | None = None


def check_status(value: str) -> str:
    status = (value or "neu").strip()
    if status not in STATUSES:
        raise DocManError(422, "Unbekannter Status.")
    return status


def apply_rules(db: Session, doc: Document) -> None:
    rules = db.scalars(select(WorkflowRule).where(WorkflowRule.enabled.is_(True))).all()
    tag_ids = {tag.id for tag in doc.tags}
    for rule in rules:
        if not any((rule.correspondent_id, rule.doctype_id, rule.match_tag_id)):
            continue
        if rule.correspondent_id and doc.correspondent_id != rule.correspondent_id:
            continue
        if rule.doctype_id and doc.doctype_id != rule.doctype_id:
            continue
        if rule.match_tag_id and rule.match_tag_id not in tag_ids:
            continue
        if rule.set_status in STATUSES:
            doc.status = rule.set_status
        if rule.add_tag_id and rule.add_tag_id not in tag_ids:
            tag = db.get(Tag, rule.add_tag_id)
            if tag is not None:
                doc.tags.append(tag)
                tag_ids.add(tag.id)


def set_field_values(db: Session, doc: Document, items: list[dict]) -> None:
    db.execute(delete(FieldValue).where(FieldValue.document_id == doc.id))
    parts: list[str] = []
    seen: set[int] = set()
    for item in items:
        field = db.get(FieldDef, int(item["field_id"]))
        if field is None:
            raise DocManError(422, "Unbekanntes Feld.")
        if field.id in seen:
            continue
        seen.add(field.id)
        raw = str(item.get("value") or "").strip()
        if not raw:
            continue
        if field.kind == "number":
            try:
                float(raw.replace(",", "."))
            except ValueError as exc:
                raise DocManError(422, f"„{field.name}“ muss eine Zahl sein.") from exc
            raw = raw.replace(",", ".")
        elif field.kind == "date":
            try:
                date.fromisoformat(raw)
            except ValueError as exc:
                raise DocManError(422, f"„{field.name}“ braucht ein Datum JJJJ-MM-TT.") from exc
        value = raw[:500]
        db.add(FieldValue(document_id=doc.id, field_id=field.id, value=value))
        parts.append(f"{field.name} {value}")
    doc.field_text = "\n".join(parts)


def document_fields(db: Session, document_id: int) -> list[dict]:
    rows = db.execute(
        select(FieldValue, FieldDef)
        .join(FieldDef, FieldDef.id == FieldValue.field_id)
        .where(FieldValue.document_id == document_id)
        .order_by(FieldDef.name)
    ).all()
    return [
        {"field_id": field.id, "name": field.name, "kind": field.kind, "value": value.value}
        for value, field in rows
    ]


def document_versions(db: Session, document_id: int) -> list[dict]:
    rows = db.scalars(
        select(DocumentVersion).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.version_number.desc())
    ).all()
    return [
        {
            "id": row.id,
            "version_number": row.version_number,
            "original_name": row.original_name,
            "size": row.size,
            "created_at": row.created_at.isoformat(timespec="seconds") + "Z",
        }
        for row in rows
    ]


def document_links(db: Session, document_id: int) -> list[dict]:
    rows = db.scalars(
        select(DocumentLink).where(or_(DocumentLink.left_id == document_id, DocumentLink.right_id == document_id))
    ).all()
    linked = []
    for row in rows:
        other_id = row.right_id if row.left_id == document_id else row.left_id
        other = db.get(Document, other_id)
        if other is None:
            continue
        linked.append({"id": other.id, "title": other.title})
    linked.sort(key=lambda item: item["title"].lower())
    return linked


def add_version(db: Session, user: User, document_id: int, filename: str, data: bytes) -> Document:
    if not data:
        raise DocManError(422, "Die Datei ist leer.")
    if len(data) > settings.max_upload_bytes:
        raise DocManError(413, "Die Datei ist größer als 25 MB.")
    doc = get_document(db, document_id)
    original = safe_original_name(filename)
    ext = extension_of(original)
    if ext not in ALLOWED_EXTENSIONS:
        raise DocManError(415, "Dieser Dateityp ist nicht erlaubt.")
    digest = hashlib.sha256(data).hexdigest()
    if digest == doc.sha256:
        raise DocManError(409, "Das ist bereits die aktuelle Version.")
    other = db.scalar(select(Document).where(Document.sha256 == digest, Document.id != doc.id))
    if other is not None:
        raise DocManError(409, f"Die Datei liegt bereits als „{other.title}“ im Archiv.")
    current = settings.files_dir / doc.stored_name
    if not current.is_file():
        raise DocManError(404, "Die aktuelle Datei fehlt im Speicher.")
    archive_name = f"{doc.id}-v{doc.version_number}{doc.extension}"
    archive_path = settings.versions_dir / archive_name
    text, text_status = extract_text(original, data)
    new_stored = f"{doc.id}{ext}"
    new_path = settings.files_dir / new_stored
    temp_path = new_path.with_name(new_path.name + ".tmp")
    try:
        archive_path.write_bytes(current.read_bytes())
        temp_path.write_bytes(data)
        temp_path.replace(new_path)
    except OSError as exc:
        archive_path.unlink(missing_ok=True)
        temp_path.unlink(missing_ok=True)
        raise DocManError(500, "Die Version konnte nicht gespeichert werden.") from exc
    db.add(
        DocumentVersion(
            document_id=doc.id,
            version_number=doc.version_number,
            original_name=doc.original_name,
            stored_name=archive_name,
            mime=doc.mime,
            extension=doc.extension,
            size=doc.size,
            sha256=doc.sha256,
            full_text=doc.full_text or "",
            text_status=doc.text_status,
            created_at=utcnow(),
        )
    )
    if new_path != current and current.is_file():
        current.unlink()
    doc.original_name = original
    doc.stored_name = new_stored
    doc.mime = ALLOWED_EXTENSIONS[ext]
    doc.extension = ext
    doc.size = len(data)
    doc.sha256 = digest
    doc.full_text = text
    doc.text_status = text_status
    doc.version_number = int(doc.version_number or 1) + 1
    doc.updated_at = utcnow()
    audit(db, user, "version", f"Version {doc.version_number}: {doc.title}", doc.id)
    db.commit()
    rebuild_index(db)
    return get_document(db, doc.id)


def version_path(db: Session, document_id: int, version_id: int):
    row = db.get(DocumentVersion, version_id)
    if row is None or row.document_id != document_id:
        raise DocManError(404, "Version nicht gefunden.")
    path = (settings.versions_dir / row.stored_name).resolve()
    root = settings.versions_dir.resolve()
    if root not in path.parents or not path.is_file():
        raise DocManError(404, "Versionsdatei fehlt.")
    return row, path


def add_link(db: Session, user: User, document_id: int, other_id: int) -> None:
    if document_id == other_id:
        raise DocManError(422, "Ein Dokument kann nicht mit sich selbst verknüpft werden.")
    get_document(db, document_id)
    other = get_document(db, other_id)
    left, right = sorted((document_id, other_id))
    existing = db.scalar(select(DocumentLink).where(DocumentLink.left_id == left, DocumentLink.right_id == right))
    if existing is not None:
        return
    db.add(DocumentLink(left_id=left, right_id=right, created_at=utcnow()))
    audit(db, user, "link", f"Verknüpft mit {other.title}", document_id)
    db.commit()


def remove_link(db: Session, user: User, document_id: int, other_id: int) -> None:
    left, right = sorted((document_id, other_id))
    row = db.scalar(select(DocumentLink).where(DocumentLink.left_id == left, DocumentLink.right_id == right))
    if row is None:
        raise DocManError(404, "Verknüpfung nicht gefunden.")
    db.delete(row)
    audit(db, user, "unlink", f"Verknüpfung gelöst ({other_id})", document_id)
    db.commit()


def remove_version_files(db: Session, document_id: int) -> list:
    rows = db.scalars(select(DocumentVersion).where(DocumentVersion.document_id == document_id)).all()
    return [settings.versions_dir / row.stored_name for row in rows]


def create_field(db: Session, name: str, kind: str) -> FieldDef:
    from app.services import _clean_name

    clean = _clean_name(name, 80, "Feld")
    if kind not in FIELD_KINDS:
        raise DocManError(422, "Feldart ist text, number oder date.")
    existing = db.scalar(select(FieldDef).where(FieldDef.name == clean))
    if existing is not None:
        raise DocManError(409, "Dieses Feld gibt es schon.")
    row = FieldDef(name=clean, kind=kind, created_at=utcnow())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_field(db: Session, field_id: int) -> None:
    row = db.get(FieldDef, field_id)
    if row is None:
        raise DocManError(404, "Feld nicht gefunden.")
    doc_ids = list(db.scalars(select(FieldValue.document_id).where(FieldValue.field_id == field_id)).all())
    db.execute(delete(FieldValue).where(FieldValue.field_id == field_id))
    db.delete(row)
    db.flush()
    for doc_id in dict.fromkeys(doc_ids):
        doc = db.get(Document, doc_id)
        if doc is None:
            continue
        values = document_fields(db, doc_id)
        doc.field_text = "\n".join(f"{item['name']} {item['value']}" for item in values)
    db.commit()
    rebuild_index(db)


def create_view(db: Session, user: User, name: str, query: dict) -> SavedView:
    from app.services import _clean_name

    clean = _clean_name(name, 80, "Sicht")
    row = SavedView(user_id=user.id, name=clean, query_text=json.dumps(query, ensure_ascii=False), created_at=utcnow())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def view_dict(row: SavedView) -> dict:
    try:
        query = json.loads(row.query_text or "{}")
    except json.JSONDecodeError:
        query = {}
    return {"id": row.id, "name": row.name, "query": query}


def create_rule(db: Session, payload: dict) -> WorkflowRule:
    from app.models import Correspondent, DocType
    from app.services import _clean_name, _resolve_fk

    name = _clean_name(payload["name"], 120, "Regel")
    status = (payload.get("set_status") or "").strip()
    if status and status not in STATUSES:
        raise DocManError(422, "Unbekannter Status.")
    correspondent = _resolve_fk(db, Correspondent, payload.get("correspondent_id"), "Korrespondent")
    doctype = _resolve_fk(db, DocType, payload.get("doctype_id"), "Dokumenttyp")
    match_tag = _resolve_fk(db, Tag, payload.get("match_tag_id"), "Schlagwort")
    add_tag = _resolve_fk(db, Tag, payload.get("add_tag_id"), "Schlagwort")
    if not any((correspondent, doctype, match_tag)):
        raise DocManError(422, "Die Regel braucht mindestens Korrespondent, Dokumenttyp oder Schlagwort.")
    if not status and add_tag is None:
        raise DocManError(422, "Die Regel muss einen Status setzen oder ein Schlagwort hinzufügen.")
    row = WorkflowRule(
        name=name,
        correspondent_id=None if correspondent is None else correspondent.id,
        doctype_id=None if doctype is None else doctype.id,
        match_tag_id=None if match_tag is None else match_tag.id,
        set_status=status,
        add_tag_id=None if add_tag is None else add_tag.id,
        enabled=True,
        created_at=utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def rule_dict(row: WorkflowRule) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "correspondent_id": row.correspondent_id,
        "doctype_id": row.doctype_id,
        "match_tag_id": row.match_tag_id,
        "set_status": row.set_status,
        "add_tag_id": row.add_tag_id,
        "enabled": bool(row.enabled),
    }


def watch_once() -> dict:
    if not settings.inbox_dir.is_dir():
        return {"imported": [], "rejected": []}
    candidates = [path for path in settings.inbox_dir.iterdir() if path.is_file() and not path.name.startswith(".")]
    if not candidates:
        return {"imported": [], "rejected": []}
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.is_admin.is_(True)).order_by(User.id))
        if user is None:
            return {"imported": [], "rejected": []}
        return scan_inbox(db, user)


def _loop() -> None:
    while not _stop.wait(settings.watch_seconds):
        try:
            watch_once()
        except Exception:
            logger.exception("Posteingang")


def start_watcher() -> None:
    global _thread
    if not settings.watch or (_thread is not None and _thread.is_alive()):
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="docman-inbox", daemon=True)
    _thread.start()


def stop_watcher() -> None:
    _stop.set()
    if _thread is not None:
        _thread.join(timeout=2)
