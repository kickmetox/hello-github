"""Ablage, Stammdaten und Suchindex."""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.timeutil import utcnow
from app.config import ALLOWED_EXTENSIONS, settings
from app.extract import extension_of, extract_text, safe_original_name
from app.models import AuditLog, Correspondent, DocType, Document, Tag, User
from app.search_engine import INDEX, INDEX_LOCK, snippet, tokenize


class DocManError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
USERNAME = re.compile(r"^[A-Za-z0-9._-]{3,40}$")


def audit(db: Session, user: User | None, action: str, message: str, document_id: int | None = None) -> None:
    db.add(
        AuditLog(
            user_id=None if user is None else user.id,
            username="" if user is None else user.username,
            action=action,
            message=message[:2000],
            document_id=document_id,
            created_at=utcnow(),
        )
    )


def iso_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat(timespec="seconds") + "Z"


def iso_date(value: date | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def document_query():
    return select(Document).options(
        selectinload(Document.tags),
        selectinload(Document.correspondent),
        selectinload(Document.doctype),
        selectinload(Document.uploaded_by),
    )


def to_dict(doc: Document, include_text: bool = False) -> dict:
    payload = {
        "id": doc.id,
        "title": doc.title,
        "original_name": doc.original_name,
        "mime": doc.mime,
        "extension": doc.extension,
        "size": doc.size,
        "sha256": doc.sha256,
        "text_status": doc.text_status,
        "notes": doc.notes or "",
        "document_date": iso_date(doc.document_date),
        "reminder_date": iso_date(doc.reminder_date),
        "is_tax_relevant": bool(doc.is_tax_relevant),
        "status": doc.status or "neu",
        "retain_until": iso_date(doc.retain_until),
        "version_number": int(doc.version_number or 1),
        "created_at": iso_dt(doc.created_at),
        "updated_at": iso_dt(doc.updated_at),
        "correspondent": None
        if doc.correspondent is None
        else {"id": doc.correspondent.id, "name": doc.correspondent.name, "email": doc.correspondent.email or ""},
        "doctype": None if doc.doctype is None else {"id": doc.doctype.id, "name": doc.doctype.name},
        "tags": [
            {"id": tag.id, "name": tag.name, "color": tag.color}
            for tag in sorted(doc.tags, key=lambda item: item.name.lower())
        ],
        "uploaded_by": None if doc.uploaded_by is None else doc.uploaded_by.display_name or doc.uploaded_by.username,
    }
    if include_text:
        payload["text"] = doc.full_text or ""
        from sqlalchemy.orm import object_session

        session = object_session(doc)
        if session is None:
            payload["versions"] = []
            payload["links"] = []
            payload["fields"] = []
        else:
            from app.extend import document_fields, document_links, document_versions

            payload["versions"] = document_versions(session, doc.id)
            payload["links"] = document_links(session, doc.id)
            payload["fields"] = document_fields(session, doc.id)
    return payload


def corpus(doc: Document) -> str:
    parts = [
        doc.title or "",
        doc.original_name or "",
        doc.notes or "",
        doc.full_text or "",
        "" if doc.correspondent is None else doc.correspondent.name,
        "" if doc.doctype is None else doc.doctype.name,
        " ".join(tag.name for tag in doc.tags),
        doc.field_text or "",
    ]
    from app.extend import STATUS_LABELS

    parts.append(doc.status or "")
    parts.append(STATUS_LABELS.get(doc.status or "", ""))
    return "\n".join(parts)


def rebuild_index(db: Session) -> int:
    rows = db.scalars(document_query().order_by(Document.id)).all()
    payload = [(row.id, corpus(row)) for row in rows]
    with INDEX_LOCK:
        INDEX.rebuild(payload)
    return len(payload)


def search_documents(db: Session, query: str, top_k: int = 20) -> tuple[list[dict], list[str]]:
    terms = tokenize(query)
    limit = max(1, min(int(top_k), 50))
    with INDEX_LOCK:
        ranked = list(INDEX.search(query, limit))
    if not ranked:
        return [], terms
    ids = [doc_id for doc_id, _score in ranked]
    rows = db.scalars(document_query().where(Document.id.in_(ids))).all()
    by_id = {row.id: row for row in rows}
    hits = []
    for doc_id, score in ranked:
        doc = by_id.get(doc_id)
        if doc is None:
            continue
        hits.append(
            {
                "score": round(score, 4),
                "snippet": snippet(corpus(doc), query),
                "terms": terms,
                "document": to_dict(doc),
            }
        )
    return hits, terms


def _clean_name(value: str, limit: int, label: str) -> str:
    name = " ".join((value or "").split())
    if not name:
        raise DocManError(422, f"{label} fehlt.")
    if len(name) > limit:
        raise DocManError(422, f"{label} ist zu lang.")
    return name


def _color(value: str) -> str:
    color = (value or "").strip()
    if not HEX_COLOR.match(color):
        return "#7c9cff"
    return color.lower()


def _like(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def list_documents(
    db: Session,
    q: str = "",
    tag_id: int | None = None,
    doctype_id: int | None = None,
    correspondent_id: int | None = None,
    tax_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    status: str = "",
) -> tuple[list[Document], int]:
    stmt = document_query()
    count_stmt = select(func.count()).select_from(Document)
    if q.strip():
        pattern = _like(q.strip()[:200])
        condition = or_(
            Document.title.like(pattern, escape="\\"),
            Document.original_name.like(pattern, escape="\\"),
            Document.notes.like(pattern, escape="\\"),
            Document.full_text.like(pattern, escape="\\"),
            Document.field_text.like(pattern, escape="\\"),
        )
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)
    if tag_id:
        stmt = stmt.where(Document.tags.any(Tag.id == tag_id))
        count_stmt = count_stmt.where(Document.tags.any(Tag.id == tag_id))
    if doctype_id:
        stmt = stmt.where(Document.doctype_id == doctype_id)
        count_stmt = count_stmt.where(Document.doctype_id == doctype_id)
    if correspondent_id:
        stmt = stmt.where(Document.correspondent_id == correspondent_id)
        count_stmt = count_stmt.where(Document.correspondent_id == correspondent_id)
    if tax_only:
        stmt = stmt.where(Document.is_tax_relevant.is_(True))
        count_stmt = count_stmt.where(Document.is_tax_relevant.is_(True))
    if status:
        stmt = stmt.where(Document.status == status)
        count_stmt = count_stmt.where(Document.status == status)
    total = int(db.scalar(count_stmt) or 0)
    rows = db.scalars(stmt.order_by(Document.created_at.desc(), Document.id.desc()).limit(limit).offset(offset)).all()
    return list(rows), total


def get_document(db: Session, document_id: int) -> Document:
    doc = db.scalar(document_query().where(Document.id == document_id))
    if doc is None:
        raise DocManError(404, "Dokument nicht gefunden.")
    return doc


def _resolve_tags(db: Session, tag_ids: list[int]) -> list[Tag]:
    if not tag_ids:
        return []
    unique = list(dict.fromkeys(tag_ids))
    rows = db.scalars(select(Tag).where(Tag.id.in_(unique))).all()
    if len(rows) != len(unique):
        raise DocManError(422, "Unbekanntes Schlagwort.")
    return list(rows)


def _resolve_fk(db: Session, model, row_id: int | None, label: str):
    if row_id is None:
        return None
    row = db.get(model, row_id)
    if row is None:
        raise DocManError(422, f"Unbekannter {label}.")
    return row


def create_document(
    db: Session,
    user: User | None,
    filename: str,
    data: bytes,
    title: str = "",
    notes: str = "",
    document_date: date | None = None,
    reminder_date: date | None = None,
    is_tax_relevant: bool = False,
    correspondent_id: int | None = None,
    doctype_id: int | None = None,
    tag_ids: list[int] | None = None,
    rebuild: bool = True,
    audit_message: str = "Dokument hochgeladen",
) -> Document:
    if not data:
        raise DocManError(422, "Die Datei ist leer.")
    if len(data) > settings.max_upload_bytes:
        raise DocManError(413, "Die Datei ist größer als 25 MB.")
    original = safe_original_name(filename)
    ext = extension_of(original)
    if ext not in ALLOWED_EXTENSIONS:
        raise DocManError(415, "Dieser Dateityp ist nicht erlaubt.")
    digest = hashlib.sha256(data).hexdigest()
    existing = db.scalar(select(Document).where(Document.sha256 == digest))
    if existing is not None:
        raise DocManError(409, f"Die Datei liegt bereits als „{existing.title}“ im Archiv.")
    text, status = extract_text(original, data)
    clean_title = _clean_name(title or PathStem(original), 300, "Titel")
    correspondent = _resolve_fk(db, Correspondent, correspondent_id, "Korrespondent")
    doctype = _resolve_fk(db, DocType, doctype_id, "Dokumenttyp")
    tags = _resolve_tags(db, tag_ids or [])
    now = utcnow()
    doc = Document(
        title=clean_title,
        original_name=original,
        stored_name="",
        mime=ALLOWED_EXTENSIONS[ext],
        extension=ext,
        size=len(data),
        sha256=digest,
        full_text=text,
        text_status=status,
        notes=(notes or "").strip()[:8000],
        document_date=document_date,
        reminder_date=reminder_date,
        is_tax_relevant=bool(is_tax_relevant),
        status="neu",
        retain_until=None,
        version_number=1,
        field_text="",
        correspondent_id=None if correspondent is None else correspondent.id,
        doctype_id=None if doctype is None else doctype.id,
        uploaded_by_id=None if user is None else user.id,
        created_at=now,
        updated_at=now,
    )
    doc.tags = tags
    db.add(doc)
    db.flush()
    stored = f"{doc.id}{ext}"
    target = settings.files_dir / stored
    try:
        target.write_bytes(data)
    except OSError as exc:
        db.rollback()
        raise DocManError(500, "Die Datei konnte nicht gespeichert werden.") from exc
    doc.stored_name = stored
    from app.extend import apply_rules

    apply_rules(db, doc)
    audit(db, user, "upload", audit_message + f": {clean_title}", doc.id)
    db.commit()
    db.refresh(doc)
    if rebuild:
        rebuild_index(db)
    return get_document(db, doc.id)


def PathStem(filename: str) -> str:
    name = safe_original_name(filename)
    dot = name.rfind(".")
    stem = name[:dot] if dot > 0 else name
    return stem.replace("_", " ").replace("-", " ")


def update_document(db: Session, user: User, document_id: int, payload: dict) -> Document:
    doc = get_document(db, document_id)
    doc.title = _clean_name(payload["title"], 300, "Titel")
    doc.notes = (payload.get("notes") or "").strip()[:8000]
    doc.document_date = payload.get("document_date")
    doc.reminder_date = payload.get("reminder_date")
    doc.is_tax_relevant = bool(payload.get("is_tax_relevant"))
    correspondent = _resolve_fk(db, Correspondent, payload.get("correspondent_id"), "Korrespondent")
    doctype = _resolve_fk(db, DocType, payload.get("doctype_id"), "Dokumenttyp")
    doc.correspondent_id = None if correspondent is None else correspondent.id
    doc.doctype_id = None if doctype is None else doctype.id
    doc.tags = _resolve_tags(db, payload.get("tag_ids") or [])
    if "status" in payload and payload["status"] is not None:
        from app.extend import check_status

        doc.status = check_status(payload["status"])
    if "retain_until" in payload:
        doc.retain_until = payload.get("retain_until")
    if "fields" in payload and payload["fields"] is not None:
        from app.extend import set_field_values

        set_field_values(db, doc, payload["fields"])
    from app.extend import apply_rules

    apply_rules(db, doc)
    doc.updated_at = utcnow()
    audit(db, user, "update", f"Metadaten geändert: {doc.title}", doc.id)
    db.commit()
    rebuild_index(db)
    return get_document(db, doc.id)


def delete_document(db: Session, user: User, document_id: int, force: bool = False) -> None:
    from sqlalchemy import delete as sql_delete

    from app.extend import remove_version_files
    from app.models import DocumentLink, FieldValue

    doc = get_document(db, document_id)
    today = date.today()
    if doc.retain_until is not None and doc.retain_until >= today:
        if not (force and user.is_admin):
            raise DocManError(409, f"Aufbewahrung bis {doc.retain_until.isoformat()}. Löschen ist gesperrt.")
    version_paths = remove_version_files(db, doc.id)
    stored = settings.files_dir / doc.stored_name
    title = doc.title
    db.execute(sql_delete(DocumentLink).where(or_(DocumentLink.left_id == doc.id, DocumentLink.right_id == doc.id)))
    db.execute(sql_delete(FieldValue).where(FieldValue.document_id == doc.id))
    audit(db, user, "delete", f"Dokument gelöscht: {title}", doc.id)
    db.delete(doc)
    db.commit()
    if stored.is_file():
        stored.unlink()
    for path in version_paths:
        if path.is_file():
            path.unlink()
    rebuild_index(db)


def stored_path(doc: Document):
    path = (settings.files_dir / doc.stored_name).resolve()
    root = settings.files_dir.resolve()
    if root not in path.parents or not path.is_file():
        raise DocManError(404, "Datei fehlt im Speicher.")
    return path


def create_tag(db: Session, name: str, color: str) -> Tag:
    clean = _clean_name(name, 80, "Schlagwort")
    existing = db.scalar(select(Tag).where(func.lower(Tag.name) == clean.lower()))
    if existing:
        raise DocManError(409, "Dieses Schlagwort gibt es schon.")
    row = Tag(name=clean, color=_color(color), created_at=utcnow())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_tag(db: Session, tag_id: int) -> None:
    row = db.get(Tag, tag_id)
    if row is None:
        raise DocManError(404, "Schlagwort nicht gefunden.")
    row.documents.clear()
    db.flush()
    db.delete(row)
    db.commit()
    rebuild_index(db)


def create_correspondent(db: Session, name: str, email: str = "", notes: str = "") -> Correspondent:
    clean = _clean_name(name, 120, "Korrespondent")
    existing = db.scalar(select(Correspondent).where(func.lower(Correspondent.name) == clean.lower()))
    if existing:
        raise DocManError(409, "Diesen Korrespondenten gibt es schon.")
    row = Correspondent(name=clean, email=(email or "").strip()[:200], notes=(notes or "").strip()[:4000], created_at=utcnow())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_correspondent(db: Session, row_id: int) -> None:
    row = db.get(Correspondent, row_id)
    if row is None:
        raise DocManError(404, "Korrespondent nicht gefunden.")
    for doc in list(row.documents):
        doc.correspondent_id = None
    db.flush()
    db.delete(row)
    db.commit()
    rebuild_index(db)


def create_doctype(db: Session, name: str, description: str = "") -> DocType:
    clean = _clean_name(name, 120, "Dokumenttyp")
    existing = db.scalar(select(DocType).where(func.lower(DocType.name) == clean.lower()))
    if existing:
        raise DocManError(409, "Diesen Dokumenttyp gibt es schon.")
    row = DocType(name=clean, description=(description or "").strip()[:4000], created_at=utcnow())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_doctype(db: Session, row_id: int) -> None:
    row = db.get(DocType, row_id)
    if row is None:
        raise DocManError(404, "Dokumenttyp nicht gefunden.")
    for doc in list(row.documents):
        doc.doctype_id = None
    db.flush()
    db.delete(row)
    db.commit()
    rebuild_index(db)


def parse_date(value: str | None) -> date | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise DocManError(422, "Datum muss im Format JJJJ-MM-TT sein.") from exc


def parse_id(value: str | int | None) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise DocManError(422, "Ungültige Auswahl.") from exc
    if number <= 0:
        raise DocManError(422, "Ungültige Auswahl.")
    return number


def parse_id_list(value) -> list[int]:
    if value is None:
        return []
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = str(value).replace(";", ",").split(",")
    result = []
    for item in raw_items:
        parsed = parse_id(item) if str(item).strip() else None
        if parsed is not None:
            result.append(parsed)
    return result


def dashboard(db: Session) -> dict:
    today = date.today()
    horizon = today + timedelta(days=30)
    reminders = db.scalars(
        document_query()
        .where(Document.reminder_date.is_not(None), Document.reminder_date <= horizon)
        .order_by(Document.reminder_date, Document.id)
        .limit(8)
    ).all()
    recent = db.scalars(document_query().order_by(Document.created_at.desc(), Document.id.desc()).limit(6)).all()
    storage = int(db.scalar(select(func.coalesce(func.sum(Document.size), 0))) or 0)
    return {
        "documents": int(db.scalar(select(func.count()).select_from(Document)) or 0),
        "tags": int(db.scalar(select(func.count()).select_from(Tag)) or 0),
        "correspondents": int(db.scalar(select(func.count()).select_from(Correspondent)) or 0),
        "doctypes": int(db.scalar(select(func.count()).select_from(DocType)) or 0),
        "tax_relevant": int(db.scalar(select(func.count()).select_from(Document).where(Document.is_tax_relevant.is_(True))) or 0),
        "storage_bytes": storage,
        "index_documents": len(INDEX._vectors),
        "recent": [to_dict(doc) for doc in recent],
        "reminders": [to_dict(doc) for doc in reminders],
    }


def scan_inbox(db: Session, user: User) -> dict:
    imported: list[int] = []
    rejected: list[dict] = []
    if not settings.inbox_dir.is_dir():
        return {"imported": imported, "rejected": rejected}
    candidates = [
        path
        for path in sorted(settings.inbox_dir.iterdir())
        if path.is_file() and not path.name.startswith(".")
    ]
    if not candidates:
        return {"imported": imported, "rejected": rejected}
    for path in candidates:
        try:
            data = path.read_bytes()
            doc = create_document(db, user, path.name, data, rebuild=False, audit_message="Aus dem Posteingang übernommen")
            imported.append(doc.id)
            path.unlink(missing_ok=True)
        except DocManError as exc:
            target = _unique_rejected(path.name)
            path.replace(target)
            rejected.append({"file": path.name, "detail": exc.detail})
        except OSError:
            rejected.append({"file": path.name, "detail": "Datei konnte nicht gelesen werden."})
    rebuild_index(db)
    audit(db, user, "inbox", f"Posteingang: {len(imported)} übernommen, {len(rejected)} abgelehnt")
    db.commit()
    return {"imported": imported, "rejected": rejected}


def _unique_rejected(filename: str) -> object:
    from pathlib import Path

    safe = safe_original_name(filename)
    candidate = settings.rejected_dir / safe
    if not candidate.exists():
        return candidate
    stem = Path(safe).stem
    suffix = Path(safe).suffix
    stamp = utcnow().strftime("%Y%m%d%H%M%S")
    return settings.rejected_dir / f"{stem}-{stamp}{suffix}"


def public_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "is_admin": bool(user.is_admin),
        "must_change_password": bool(user.must_change_password),
    }


def validate_username(username: str) -> str:
    name = (username or "").strip()
    if not USERNAME.match(name):
        raise DocManError(422, "Benutzername: 3–40 Zeichen, Buchstaben, Ziffern, Punkt, Unterstrich oder Bindestrich.")
    return name


def validate_new_password(password: str) -> str:
    if len(password or "") < 8:
        raise DocManError(422, "Das neue Passwort braucht mindestens 8 Zeichen.")
    if len(password) > 200:
        raise DocManError(422, "Das Passwort ist zu lang.")
    return password
