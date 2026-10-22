"""HTTP-Schnittstelle des Archivs."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    attach_session_cookie,
    clear_session,
    clear_session_cookie,
    create_session,
    hash_password,
    user_from_request,
    verify_password,
)
from app.config import PREVIEW_INLINE, settings
from app.database import get_db
from app.extend import (
    add_link,
    add_version,
    create_field,
    create_rule,
    create_view,
    delete_field,
    document_links,
    rule_dict,
    version_path,
    view_dict,
)
from app.models import Correspondent, DocType, FieldDef, SavedView, Tag, User, WorkflowRule
from app.timeutil import utcnow
from app.services import (
    DocManError,
    audit,
    create_correspondent,
    create_doctype,
    create_document,
    create_tag,
    dashboard,
    delete_correspondent,
    delete_document,
    delete_doctype,
    delete_tag,
    get_document,
    list_documents,
    parse_date,
    parse_id,
    parse_id_list,
    public_user,
    rebuild_index,
    scan_inbox,
    search_documents,
    stored_path,
    to_dict,
    update_document,
    validate_new_password,
    validate_username,
)

router = APIRouter(prefix="/api")
HEADER = "x-docman"


class LoginBody(BaseModel):
    username: str
    password: str


class PasswordBody(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=200)


class UserBody(BaseModel):
    username: str
    display_name: str = ""
    password: str
    is_admin: bool = False


class TagBody(BaseModel):
    name: str
    color: str = "#7c9cff"


class CorrespondentBody(BaseModel):
    name: str
    email: str = ""
    notes: str = ""


class DocTypeBody(BaseModel):
    name: str
    description: str = ""


class FieldItem(BaseModel):
    field_id: int
    value: str = ""


class DocumentBody(BaseModel):
    title: str
    notes: str = ""
    document_date: str | None = None
    reminder_date: str | None = None
    is_tax_relevant: bool = False
    correspondent_id: int | None = None
    doctype_id: int | None = None
    tag_ids: list[int] = []
    status: str | None = None
    retain_until: str | None = None
    fields: list[FieldItem] | None = None


class LinkBody(BaseModel):
    document_id: int


class FieldBody(BaseModel):
    name: str
    kind: str = "text"


class ViewBody(BaseModel):
    name: str
    query: dict = {}


class RuleBody(BaseModel):
    name: str
    correspondent_id: int | None = None
    doctype_id: int | None = None
    match_tag_id: int | None = None
    set_status: str = ""
    add_tag_id: int | None = None


def _sent(body: BaseModel, name: str) -> bool:
    fields = getattr(body, "model_fields_set", None)
    if fields is None:
        fields = getattr(body, "__fields_set__", set())
    return name in fields


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = user_from_request(request, db)
    if user is None:
        raise _http(401, "Anmeldung erforderlich.")
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if not user.is_admin:
        raise _http(403, "Nur Administratoren dürfen das.")
    return user


def _http(status: int, detail: str):
    from fastapi import HTTPException

    return HTTPException(status_code=status, detail=detail)


def _guard(exc: DocManError):
    raise _http(exc.status, exc.detail)


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "name": "DocMan"}


@router.post("/auth/login")
def login(body: LoginBody, response: Response, db: Session = Depends(get_db)) -> dict:
    username = body.username.strip()
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(body.password, user.password_salt, user.password_hash):
        audit(db, None, "login_failed", f"Fehlgeschlagene Anmeldung für {username[:40]}")
        db.commit()
        raise _http(401, "Benutzername oder Passwort ist falsch.")
    token = create_session(db, user)
    audit(db, user, "login", "Angemeldet")
    db.commit()
    attach_session_cookie(response, token)
    return public_user(user)


@router.post("/auth/logout")
def logout(request: Request, response: Response, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    clear_session(request, db)
    audit(db, user, "logout", "Abgemeldet")
    db.commit()
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/auth/me")
def me(user: User = Depends(require_user)) -> dict:
    return public_user(user)


@router.post("/auth/password")
def change_password(body: PasswordBody, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    if not verify_password(body.current_password, user.password_salt, user.password_hash):
        raise _http(403, "Das aktuelle Passwort stimmt nicht.")
    password = validate_new_password(body.new_password)
    salt, digest = hash_password(password)
    user.password_salt = salt
    user.password_hash = digest
    user.must_change_password = False
    audit(db, user, "password", "Passwort geändert")
    db.commit()
    return public_user(user)


@router.get("/users")
def users(_admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(User).order_by(User.username)).all()
    return [public_user(row) for row in rows]


@router.post("/users", status_code=201)
def add_user(body: UserBody, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    try:
        username = validate_username(body.username)
        password = validate_new_password(body.password)
    except DocManError as exc:
        _guard(exc)
    existing = db.scalar(select(User).where(User.username == username))
    if existing:
        raise _http(409, "Diesen Benutzer gibt es schon.")
    salt, digest = hash_password(password)
    row = User(
        username=username,
        display_name=(body.display_name or username).strip()[:120],
        password_hash=digest,
        password_salt=salt,
        is_admin=bool(body.is_admin),
        must_change_password=False,
        created_at=utcnow(),
    )
    db.add(row)
    audit(db, admin, "user_create", f"Benutzer angelegt: {username}")
    db.commit()
    db.refresh(row)
    return public_user(row)


@router.get("/dashboard")
def dash(_user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    return dashboard(db)


@router.get("/documents")
def documents(
    q: str = "",
    tag_id: int | None = None,
    doctype_id: int | None = None,
    correspondent_id: int | None = None,
    tax_only: bool = False,
    status: str = "",
    limit: int = 50,
    offset: int = 0,
    _user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    rows, total = list_documents(db, q, tag_id, doctype_id, correspondent_id, tax_only, limit, offset, status)
    return {"total": total, "documents": [to_dict(row) for row in rows]}


@router.post("/documents", status_code=201)
async def upload(
    files: list[UploadFile] = File(...),
    title: str = Form(""),
    notes: str = Form(""),
    document_date: str = Form(""),
    reminder_date: str = Form(""),
    is_tax_relevant: str = Form(""),
    correspondent_id: str = Form(""),
    doctype_id: str = Form(""),
    tag_ids: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    if len(files) > settings.max_files_per_upload:
        raise _http(400, "Höchstens 20 Dateien auf einmal.")
    try:
        meta = {
            "notes": notes,
            "document_date": parse_date(document_date),
            "reminder_date": parse_date(reminder_date),
            "is_tax_relevant": str(is_tax_relevant).lower() in {"1", "true", "on", "yes", "ja"},
            "correspondent_id": parse_id(correspondent_id),
            "doctype_id": parse_id(doctype_id),
            "tag_ids": parse_id_list(tag_ids),
        }
    except DocManError as exc:
        _guard(exc)
    created = []
    errors = []
    for upload_file in files:
        data = await upload_file.read()
        item_title = title if len(files) == 1 else ""
        try:
            doc = create_document(
                db,
                user,
                upload_file.filename or "datei",
                data,
                title=item_title,
                rebuild=False,
                **meta,
            )
            created.append(to_dict(doc))
        except DocManError as exc:
            errors.append({"file": upload_file.filename or "datei", "detail": exc.detail})
    rebuild_index(db)
    if not created:
        detail = "; ".join(item["detail"] for item in errors) or "Keine Datei verarbeitet."
        raise _http(400, detail)
    return {"documents": created, "errors": errors}


@router.get("/documents/{document_id}")
def document_detail(document_id: int, _user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    try:
        return to_dict(get_document(db, document_id), include_text=True)
    except DocManError as exc:
        _guard(exc)


@router.patch("/documents/{document_id}")
def document_update(
    document_id: int,
    body: DocumentBody,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        payload = {
            "title": body.title,
            "notes": body.notes,
            "document_date": parse_date(body.document_date),
            "reminder_date": parse_date(body.reminder_date),
            "is_tax_relevant": body.is_tax_relevant,
            "correspondent_id": body.correspondent_id,
            "doctype_id": body.doctype_id,
            "tag_ids": body.tag_ids,
        }
        if _sent(body, "status"):
            payload["status"] = body.status
        if _sent(body, "retain_until"):
            payload["retain_until"] = parse_date(body.retain_until)
        if _sent(body, "fields"):
            payload["fields"] = [{"field_id": item.field_id, "value": item.value} for item in (body.fields or [])]
        doc = update_document(db, user, document_id, payload)
        return to_dict(doc, include_text=True)
    except DocManError as exc:
        _guard(exc)


@router.delete("/documents/{document_id}")
def document_delete(
    document_id: int,
    force: bool = False,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        delete_document(db, user, document_id, force=force)
    except DocManError as exc:
        _guard(exc)
    return {"ok": True}


@router.get("/documents/{document_id}/text")
def document_text(document_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    try:
        doc = get_document(db, document_id)
    except DocManError as exc:
        _guard(exc)
    audit(db, user, "export", f"Text exportiert: {doc.title}", doc.id)
    db.commit()
    filename = quote(f"{doc.title}.txt")
    return Response(
        content=(doc.full_text or "").encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.post("/documents/{document_id}/versions")
async def document_version(
    document_id: int,
    file: UploadFile = File(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    data = await file.read()
    try:
        doc = add_version(db, user, document_id, file.filename or "datei", data)
        return to_dict(doc, include_text=True)
    except DocManError as exc:
        _guard(exc)


@router.get("/documents/{document_id}/versions/{version_id}/file")
def document_version_file(
    document_id: int,
    version_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    try:
        row, path = version_path(db, document_id, version_id)
        doc = get_document(db, document_id)
    except DocManError as exc:
        _guard(exc)
    audit(db, user, "download", f"Version {row.version_number} geöffnet: {doc.title}", doc.id)
    db.commit()
    filename = quote(row.original_name)
    return FileResponse(
        path,
        media_type=row.mime.split(";")[0],
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.post("/documents/{document_id}/links")
def document_link(
    document_id: int,
    body: LinkBody,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        add_link(db, user, document_id, body.document_id)
        return {"links": document_links(db, document_id)}
    except DocManError as exc:
        _guard(exc)


@router.delete("/documents/{document_id}/links/{other_id}")
def document_unlink(
    document_id: int,
    other_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    from app.extend import remove_link

    try:
        remove_link(db, user, document_id, other_id)
        return {"links": document_links(db, document_id)}
    except DocManError as exc:
        _guard(exc)


@router.get("/documents/{document_id}/file")
def document_file(
    document_id: int,
    inline: int = 0,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    try:
        doc = get_document(db, document_id)
        path = stored_path(doc)
    except DocManError as exc:
        _guard(exc)
    audit(db, user, "download", f"Datei geöffnet: {doc.title}", doc.id)
    db.commit()
    disposition = "inline" if inline and doc.extension in PREVIEW_INLINE else "attachment"
    filename = quote(doc.original_name)
    return FileResponse(
        path,
        media_type=doc.mime.split(";")[0],
        headers={"Content-Disposition": f"{disposition}; filename*=UTF-8''{filename}"},
    )


@router.get("/search")
def search(q: str, limit: int = 20, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    query = (q or "").strip()
    if not query:
        raise _http(422, "Suchbegriff fehlt.")
    hits, terms = search_documents(db, query, limit)
    audit(db, user, "search", query[:300])
    db.commit()
    return {"query": query, "terms": terms, "results": hits}


@router.post("/search/reindex")
def reindex(user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    count = rebuild_index(db)
    audit(db, user, "reindex", f"Index neu aufgebaut ({count})")
    db.commit()
    return {"documents": count}


@router.post("/inbox/scan")
def inbox(user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    return scan_inbox(db, user)


@router.get("/fields")
def fields(_user: User = Depends(require_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(FieldDef).order_by(FieldDef.name)).all()
    return [{"id": row.id, "name": row.name, "kind": row.kind} for row in rows]


@router.post("/fields", status_code=201)
def add_field(body: FieldBody, _user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    try:
        row = create_field(db, body.name, body.kind)
    except DocManError as exc:
        _guard(exc)
    return {"id": row.id, "name": row.name, "kind": row.kind}


@router.delete("/fields/{field_id}")
def remove_field(field_id: int, _user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    try:
        delete_field(db, field_id)
    except DocManError as exc:
        _guard(exc)
    return {"ok": True}


@router.get("/views")
def views(user: User = Depends(require_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(SavedView).where(SavedView.user_id == user.id).order_by(SavedView.name)).all()
    return [view_dict(row) for row in rows]


@router.post("/views", status_code=201)
def add_view(body: ViewBody, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    try:
        row = create_view(db, user, body.name, body.query)
    except DocManError as exc:
        _guard(exc)
    return view_dict(row)


@router.delete("/views/{view_id}")
def remove_view(view_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    row = db.get(SavedView, view_id)
    if row is None or row.user_id != user.id:
        raise _http(404, "Sicht nicht gefunden.")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/rules")
def rules(_user: User = Depends(require_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(WorkflowRule).order_by(WorkflowRule.name)).all()
    return [rule_dict(row) for row in rows]


@router.post("/rules", status_code=201)
def add_rule(body: RuleBody, _user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    try:
        row = create_rule(
            db,
            {
                "name": body.name,
                "correspondent_id": body.correspondent_id,
                "doctype_id": body.doctype_id,
                "match_tag_id": body.match_tag_id,
                "set_status": body.set_status,
                "add_tag_id": body.add_tag_id,
            },
        )
    except DocManError as exc:
        _guard(exc)
    return rule_dict(row)


@router.delete("/rules/{rule_id}")
def remove_rule(rule_id: int, _user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    row = db.get(WorkflowRule, rule_id)
    if row is None:
        raise _http(404, "Regel nicht gefunden.")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/tags")
def tags(_user: User = Depends(require_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Tag).order_by(Tag.name)).all()
    return [{"id": row.id, "name": row.name, "color": row.color} for row in rows]


@router.post("/tags", status_code=201)
def add_tag(body: TagBody, _user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    try:
        row = create_tag(db, body.name, body.color)
    except DocManError as exc:
        _guard(exc)
    return {"id": row.id, "name": row.name, "color": row.color}


@router.delete("/tags/{tag_id}")
def remove_tag(tag_id: int, _user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    try:
        delete_tag(db, tag_id)
    except DocManError as exc:
        _guard(exc)
    return {"ok": True}


@router.get("/correspondents")
def correspondents(_user: User = Depends(require_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Correspondent).order_by(Correspondent.name)).all()
    return [{"id": row.id, "name": row.name, "email": row.email or "", "notes": row.notes or ""} for row in rows]


@router.post("/correspondents", status_code=201)
def add_correspondent(body: CorrespondentBody, _user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    try:
        row = create_correspondent(db, body.name, body.email, body.notes)
    except DocManError as exc:
        _guard(exc)
    return {"id": row.id, "name": row.name, "email": row.email, "notes": row.notes}


@router.delete("/correspondents/{row_id}")
def remove_correspondent(row_id: int, _user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    try:
        delete_correspondent(db, row_id)
    except DocManError as exc:
        _guard(exc)
    return {"ok": True}


@router.get("/doctypes")
def doctypes(_user: User = Depends(require_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(DocType).order_by(DocType.name)).all()
    return [{"id": row.id, "name": row.name, "description": row.description or ""} for row in rows]


@router.post("/doctypes", status_code=201)
def add_doctype(body: DocTypeBody, _user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    try:
        row = create_doctype(db, body.name, body.description)
    except DocManError as exc:
        _guard(exc)
    return {"id": row.id, "name": row.name, "description": row.description}


@router.delete("/doctypes/{row_id}")
def remove_doctype(row_id: int, _user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    try:
        delete_doctype(db, row_id)
    except DocManError as exc:
        _guard(exc)
    return {"ok": True}


@router.get("/audit")
def audit_log(_user: User = Depends(require_user), db: Session = Depends(get_db)) -> list[dict]:
    from app.models import AuditLog

    rows = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(200)).all()
    return [
        {
            "id": row.id,
            "username": row.username,
            "action": row.action,
            "message": row.message,
            "document_id": row.document_id,
            "created_at": row.created_at.isoformat(timespec="seconds") + "Z",
        }
        for row in rows
    ]
