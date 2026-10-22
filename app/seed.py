"""Erstes Administratorkonto und Beispieldokumente aus samples/."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.timeutil import utcnow
from app.config import ROOT, settings
from app.models import Correspondent, DocType, Document, Tag, User


INITIAL_USERNAME = "admin"
INITIAL_PASSWORD = "admin"

SAMPLES = [
    {
        "file": "mietvertrag.txt",
        "title": "Mietvertrag Wohnung Berlin",
        "doctype": "Vertrag",
        "correspondent": "Hausverwaltung Nord",
        "email": "verwaltung@example.local",
        "tags": [("Wohnung", "#7c9cff"), ("Vertrag", "#c4b5fd")],
        "document_date": date(2024, 4, 1),
        "tax": False,
        "notes": "Fiktiver Mustervertrag für die lokale Suche.",
    },
    {
        "file": "rechnung-buero.txt",
        "title": "Rechnung Büromaterial März 2026",
        "doctype": "Rechnung",
        "correspondent": "Bürobedarf Keller",
        "email": "rechnung@example.local",
        "tags": [("Finanzen", "#f0c36a"), ("Steuer", "#ffb020")],
        "document_date": date(2026, 3, 18),
        "tax": True,
        "notes": "Vorsteuer ausweisen und zur Buchhaltung legen.",
    },
    {
        "file": "projektnotiz-suchindex.txt",
        "title": "Projektnotiz Suchindex TF-IDF",
        "doctype": "Notiz",
        "correspondent": "Intern",
        "email": "",
        "tags": [("Projekt", "#3ee0b0")],
        "document_date": date(2026, 10, 2),
        "tax": False,
        "notes": "Erläutert Termfrequenz, inverse Dokumenthäufigkeit und Kosinusähnlichkeit.",
    },
    {
        "file": "versicherung-hausrat.txt",
        "title": "Versicherungspolice Hausrat",
        "doctype": "Vertrag",
        "correspondent": "Nordlicht Versicherung",
        "email": "police@example.local",
        "tags": [("Versicherung", "#7dd3fc")],
        "document_date": date(2025, 11, 1),
        "tax": False,
        "notes": "Wiedervorlage vor dem nächsten Zahltermin.",
        "reminder_in_days": 21,
    },
    {
        "file": "protokoll-q1.txt",
        "title": "Besprechungsprotokoll Archiv Q1",
        "doctype": "Protokoll",
        "correspondent": "Intern",
        "email": "",
        "tags": [("Projekt", "#3ee0b0"), ("Protokoll", "#fb7185")],
        "document_date": date(2026, 3, 31),
        "tax": False,
        "notes": "Beschlüsse zur Ablage von Verträgen und Rechnungen.",
    },
]


def ensure_admin(db: Session) -> None:
    exists = db.scalar(select(func.count()).select_from(User))
    if exists:
        return
    salt, digest = hash_password(INITIAL_PASSWORD)
    db.add(
        User(
            username=INITIAL_USERNAME,
            display_name="Administrator",
            password_hash=digest,
            password_salt=salt,
            is_admin=True,
            must_change_password=True,
            created_at=utcnow(),
        )
    )
    db.commit()


def _get_or_create_correspondent(db: Session, name: str, email: str) -> Correspondent:
    row = db.scalar(select(Correspondent).where(func.lower(Correspondent.name) == name.lower()))
    if row:
        return row
    row = Correspondent(name=name, email=email, created_at=utcnow())
    db.add(row)
    db.flush()
    return row


def _get_or_create_doctype(db: Session, name: str) -> DocType:
    row = db.scalar(select(DocType).where(func.lower(DocType.name) == name.lower()))
    if row:
        return row
    row = DocType(name=name, description="", created_at=utcnow())
    db.add(row)
    db.flush()
    return row


def _get_or_create_tag(db: Session, name: str, color: str) -> Tag:
    row = db.scalar(select(Tag).where(func.lower(Tag.name) == name.lower()))
    if row:
        return row
    row = Tag(name=name, color=color, created_at=utcnow())
    db.add(row)
    db.flush()
    return row


def ensure_samples(db: Session) -> None:
    if not settings.seed:
        return
    count = db.scalar(select(func.count()).select_from(Document))
    if count:
        return
    from app.services import create_document

    admin = db.scalar(select(User).where(User.username == INITIAL_USERNAME))
    folder = ROOT / "samples"
    for spec in SAMPLES:
        path = folder / spec["file"]
        if not path.is_file():
            continue
        correspondent = _get_or_create_correspondent(db, spec["correspondent"], spec["email"])
        doctype = _get_or_create_doctype(db, spec["doctype"])
        tags = [_get_or_create_tag(db, name, color) for name, color in spec["tags"]]
        reminder = None
        if spec.get("reminder_in_days") is not None:
            reminder = date.today() + timedelta(days=int(spec["reminder_in_days"]))
        create_document(
            db,
            admin,
            spec["file"],
            path.read_bytes(),
            title=spec["title"],
            notes=spec["notes"],
            document_date=spec["document_date"],
            reminder_date=reminder,
            is_tax_relevant=spec["tax"],
            correspondent_id=correspondent.id,
            doctype_id=doctype.id,
            tag_ids=[tag.id for tag in tags],
            rebuild=False,
            audit_message="Beispieldokument angelegt",
        )
