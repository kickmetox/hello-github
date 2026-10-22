import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

HEADER = {"X-DocMan": "1"}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin"}, headers=HEADER)
    assert response.status_code == 200
    assert response.json()["must_change_password"] is True
    return client


def test_login_requires_header_and_rejects_bad_password(client):
    missing = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert missing.status_code == 403
    wrong = client.post("/api/auth/login", json={"username": "admin", "password": "falsch"}, headers=HEADER)
    assert wrong.status_code == 401
    assert client.get("/api/documents").status_code == 401


def test_upload_search_update_download_and_delete(auth):
    created = auth.post(
        "/api/tags",
        json={"name": "Sonderakte", "color": "#3ee0b0"},
        headers=HEADER,
    )
    assert created.status_code == 201
    tag_id = created.json()["id"]
    uploaded = auth.post(
        "/api/documents",
        files={"files": ("notiz.txt", "alpha beta gamma".encode("utf-8"), "text/plain")},
        data={"title": "Interne Notiz", "tag_ids": str(tag_id)},
        headers=HEADER,
    )
    assert uploaded.status_code == 201, uploaded.text
    document = uploaded.json()["documents"][0]
    assert document["original_name"] == "notiz.txt"
    found = auth.get("/api/search", params={"q": "Sonderakte"})
    assert found.status_code == 200
    assert found.json()["results"][0]["document"]["id"] == document["id"]
    assert found.json()["results"][0]["score"] > 0

    changed = auth.patch(
        f"/api/documents/{document['id']}",
        json={
            "title": "Interne Notiz ergänzt",
            "notes": "Kündigung vormerken",
            "document_date": "2026-01-15",
            "reminder_date": None,
            "is_tax_relevant": True,
            "correspondent_id": None,
            "doctype_id": None,
            "tag_ids": [tag_id],
        },
        headers=HEADER,
    )
    assert changed.status_code == 200
    assert changed.json()["is_tax_relevant"] is True

    downloaded = auth.get(f"/api/documents/{document['id']}/file")
    assert downloaded.status_code == 200
    assert downloaded.content == "alpha beta gamma".encode("utf-8")

    hostile = auth.post(
        "/api/documents",
        files={"files": ("../../geheim.txt", b"nur lokal", "text/plain")},
        headers=HEADER,
    )
    assert hostile.status_code == 201
    assert hostile.json()["documents"][0]["original_name"] == "geheim.txt"
    stored = settings.files_dir / f"{hostile.json()['documents'][0]['id']}.txt"
    assert stored.is_file()
    assert ".." not in stored.name

    removed = auth.delete(f"/api/documents/{document['id']}", headers=HEADER)
    assert removed.status_code == 200
    assert auth.get(f"/api/documents/{document['id']}").status_code == 404
    assert not (settings.files_dir / f"{document['id']}.txt").exists()


def test_ranking_duplicate_and_rejected_type(auth):
    first = _upload(auth, "vertrag.txt", "Mietvertrag Kuendigung Frist Berlin Wohnung")
    second = _upload(auth, "rechnung.txt", "Umsatzsteuer Vorsteuer Rechnung Papier Toner")
    ranked = auth.get("/api/search", params={"q": "Kuendigung Mietvertrag"})
    assert ranked.json()["results"][0]["document"]["id"] == first["id"]
    invoice = auth.get("/api/search", params={"q": "Vorsteuer Umsatzsteuer"})
    assert invoice.json()["results"][0]["document"]["id"] == second["id"]
    filler = auth.get("/api/search", params={"q": "der die das"})
    assert filler.json()["terms"] == []
    assert filler.json()["results"] == []

    duplicate = auth.post(
        "/api/documents",
        files={"files": ("vertrag-kopie.txt", "Mietvertrag Kuendigung Frist Berlin Wohnung".encode("utf-8"), "text/plain")},
        headers=HEADER,
    )
    assert duplicate.status_code == 400
    assert "bereits" in duplicate.json()["detail"]

    blocked = auth.post(
        "/api/documents",
        files={"files": ("tool.exe", b"nope", "application/octet-stream")},
        headers=HEADER,
    )
    assert blocked.status_code == 400
    assert "nicht erlaubt" in blocked.json()["detail"]


def test_inbox_users_and_password(auth):
    inbox_file = settings.inbox_dir / "eingang.txt"
    inbox_file.write_text("Posteingang Protokoll Archiv", encoding="utf-8")
    scanned = auth.post("/api/inbox/scan", headers=HEADER)
    assert scanned.status_code == 200
    assert scanned.json()["imported"]
    assert not inbox_file.exists()

    created = auth.post(
        "/api/users",
        json={"username": "archiv", "display_name": "Archiv", "password": "geheim12", "is_admin": False},
        headers=HEADER,
    )
    assert created.status_code == 201
    forbidden = auth.post("/api/auth/login", json={"username": "archiv", "password": "geheim12"}, headers=HEADER)
    assert forbidden.status_code == 200
    denied = auth.post(
        "/api/users",
        json={"username": "nochwer", "password": "geheim12"},
        headers=HEADER,
    )
    assert denied.status_code == 403

    auth.post("/api/auth/logout", headers=HEADER)
    auth.post("/api/auth/login", json={"username": "admin", "password": "admin"}, headers=HEADER)
    changed = auth.post(
        "/api/auth/password",
        json={"current_password": "admin", "new_password": "neues-passwort"},
        headers=HEADER,
    )
    assert changed.status_code == 200
    assert changed.json()["must_change_password"] is False
    me = auth.get("/api/auth/me")
    assert me.json()["username"] == "admin"
    _restore_admin_password()


def test_dashboard_and_health(auth):
    health = auth.get("/api/health")
    assert health.json()["status"] == "ok"
    page = auth.get("/")
    assert page.status_code == 200
    assert "DocMan" in page.text
    style = auth.get("/static/styles.css")
    assert style.status_code == 200
    board = auth.get("/api/dashboard")
    assert board.status_code == 200
    assert "documents" in board.json()


def _restore_admin_password():
    from sqlalchemy import select

    from app.auth import hash_password
    from app.database import SessionLocal
    from app.models import User

    salt, digest = hash_password("admin")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == "admin"))
        user.password_salt = salt
        user.password_hash = digest
        user.must_change_password = True
        db.commit()


def _upload(client, name, text):
    response = client.post(
        "/api/documents",
        files={"files": (name, text.encode("utf-8"), "text/plain")},
        headers=HEADER,
    )
    assert response.status_code == 201, response.text
    return response.json()["documents"][0]
