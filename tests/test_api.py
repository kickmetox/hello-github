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


def test_ocr_scan_is_searchable(auth):
    from app.ocr import engine_status
    from tests.test_extract import _font, _png

    if not engine_status()["available"] or _font() is None:
        pytest.skip("Tesseract oder Schrift fehlt")
    image = _png("QUARZSCAN")
    uploaded = auth.post(
        "/api/documents",
        files={"files": ("quarzscan.png", image, "image/png")},
        data={"title": "Scan Quarz"},
        headers=HEADER,
    )
    assert uploaded.status_code == 201, uploaded.text
    document = uploaded.json()["documents"][0]
    assert document["text_status"] == "ocr"
    detail = auth.get(f"/api/documents/{document['id']}")
    assert "QUARZSCAN" in detail.json()["text"].replace(" ", "")
    found = auth.get("/api/search", params={"q": "QUARZSCAN"})
    assert found.json()["results"][0]["document"]["id"] == document["id"]
    again = auth.post(f"/api/documents/{document['id']}/ocr", headers=HEADER)
    assert again.status_code == 200, again.text
    assert again.json()["text_status"] == "ocr"
    health = auth.get("/api/health")
    assert health.json()["ocr"]["available"] is True


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


def test_versions_links_fields_rules_retention_views_and_watch(auth):
    before = auth.get("/api/audit").json()
    empty = auth.post("/api/inbox/scan", headers=HEADER)
    assert empty.status_code == 200
    assert empty.json() == {"imported": [], "rejected": []}
    after_empty = auth.get("/api/audit").json()
    assert len(after_empty) == len(before)

    original = _upload(auth, "fassung-a.txt", "Xylophonvertrag Fassung eins")
    uploaded = auth.post(
        f"/api/documents/{original['id']}/versions",
        files={"file": ("fassung-b.txt", "Xylophonvertrag Fassung zwei".encode("utf-8"), "text/plain")},
        headers=HEADER,
    )
    assert uploaded.status_code == 200, uploaded.text
    current = uploaded.json()
    assert current["version_number"] == 2
    assert current["versions"][0]["version_number"] == 1
    old = auth.get(f"/api/documents/{original['id']}/versions/{current['versions'][0]['id']}/file")
    assert old.status_code == 200
    assert old.content == "Xylophonvertrag Fassung eins".encode("utf-8")
    fresh = auth.get(f"/api/documents/{original['id']}/file")
    assert fresh.content == "Xylophonvertrag Fassung zwei".encode("utf-8")
    same = auth.post(
        f"/api/documents/{original['id']}/versions",
        files={"file": ("fassung-c.txt", "Xylophonvertrag Fassung zwei".encode("utf-8"), "text/plain")},
        headers=HEADER,
    )
    assert same.status_code == 409

    other = _upload(auth, "quarz.txt", "Quarzrechnung Gegenstueck")
    linked = auth.post(
        f"/api/documents/{original['id']}/links",
        json={"document_id": other["id"]},
        headers=HEADER,
    )
    assert linked.status_code == 200
    assert linked.json()["links"][0]["id"] == other["id"]
    reverse = auth.get(f"/api/documents/{other['id']}")
    assert reverse.json()["links"][0]["id"] == original["id"]
    self_link = auth.post(
        f"/api/documents/{original['id']}/links",
        json={"document_id": original["id"]},
        headers=HEADER,
    )
    assert self_link.status_code == 422
    removed = auth.delete(f"/api/documents/{original['id']}/links/{other['id']}", headers=HEADER)
    assert removed.status_code == 200
    assert removed.json()["links"] == []

    tag = auth.post("/api/tags", json={"name": "WorkflowX", "color": "#e6c15a"}, headers=HEADER)
    assert tag.status_code == 201
    rule = auth.post(
        "/api/rules",
        json={"name": "WorkflowX bezahlt", "match_tag_id": tag.json()["id"], "set_status": "bezahlt"},
        headers=HEADER,
    )
    assert rule.status_code == 201, rule.text
    ruled = auth.post(
        "/api/documents",
        files={"files": ("regel.txt", "Regeltext WorkflowX".encode("utf-8"), "text/plain")},
        data={"title": "Regelakte", "tag_ids": str(tag.json()["id"])},
        headers=HEADER,
    )
    assert ruled.status_code == 201, ruled.text
    assert ruled.json()["documents"][0]["status"] == "bezahlt"
    empty_rule = auth.post("/api/rules", json={"name": "Leer", "set_status": "neu"}, headers=HEADER)
    assert empty_rule.status_code == 422

    field = auth.post("/api/fields", json={"name": "Rechnungsbetrag", "kind": "number"}, headers=HEADER)
    assert field.status_code == 201, field.text
    field_id = field.json()["id"]
    priced = auth.patch(
        f"/api/documents/{other['id']}",
        json=_meta("Quarzrechnung Gegenstueck", fields=[{"field_id": field_id, "value": "12,50"}]),
        headers=HEADER,
    )
    assert priced.status_code == 200, priced.text
    assert priced.json()["fields"][0]["value"] == "12.50"
    found = auth.get("/api/search", params={"q": "Rechnungsbetrag"})
    assert found.json()["results"][0]["document"]["id"] == other["id"]
    kept = auth.patch(
        f"/api/documents/{other['id']}",
        json=_meta("Quarzrechnung Gegenstueck", status="geprueft"),
        headers=HEADER,
    )
    assert kept.status_code == 200
    assert kept.json()["status"] == "geprueft"
    assert kept.json()["fields"][0]["value"] == "12.50"
    omitted = auth.patch(
        f"/api/documents/{other['id']}",
        json=_meta("Quarzrechnung Gegenstueck"),
        headers=HEADER,
    )
    assert omitted.json()["status"] == "geprueft"
    assert omitted.json()["fields"][0]["value"] == "12.50"

    exported = auth.get(f"/api/documents/{other['id']}/text")
    assert exported.status_code == 200
    assert "Quarzrechnung Gegenstueck" in exported.text
    assert exported.headers["content-type"].startswith("text/plain")

    locked = _upload(auth, "sperre.txt", "Aufbewahrungssperre allein")
    held = auth.patch(
        f"/api/documents/{locked['id']}",
        json=_meta("Aufbewahrungssperre allein", retain_until="2099-01-01"),
        headers=HEADER,
    )
    assert held.status_code == 200
    blocked = auth.delete(f"/api/documents/{locked['id']}", headers=HEADER)
    assert blocked.status_code == 409
    assert "Aufbewahrung" in blocked.json()["detail"]
    reader = auth.post(
        "/api/users",
        json={"username": "sperre", "display_name": "Sperre", "password": "geheim12", "is_admin": False},
        headers=HEADER,
    )
    assert reader.status_code == 201
    auth.post("/api/auth/login", json={"username": "sperre", "password": "geheim12"}, headers=HEADER)
    forced = auth.delete(f"/api/documents/{locked['id']}", params={"force": "true"}, headers=HEADER)
    assert forced.status_code == 409
    auth.post("/api/auth/login", json={"username": "admin", "password": "admin"}, headers=HEADER)
    released = auth.delete(f"/api/documents/{locked['id']}", params={"force": "true"}, headers=HEADER)
    assert released.status_code == 200
    assert auth.get(f"/api/documents/{locked['id']}").status_code == 404

    listed = auth.get("/api/documents", params={"status": "bezahlt"})
    assert listed.status_code == 200
    assert any(row["id"] == ruled.json()["documents"][0]["id"] for row in listed.json()["documents"])

    saved = auth.post(
        "/api/views",
        json={"name": "Nur bezahlt", "query": {"status": "bezahlt", "q": "", "tax_only": False}},
        headers=HEADER,
    )
    assert saved.status_code == 201, saved.text
    views = auth.get("/api/views")
    assert any(row["id"] == saved.json()["id"] and row["query"]["status"] == "bezahlt" for row in views.json())
    gone = auth.delete(f"/api/views/{saved.json()['id']}", headers=HEADER)
    assert gone.status_code == 200

    from app.extend import watch_once

    inbox_file = settings.inbox_dir / "waechter.txt"
    inbox_file.write_text("Waechter Posteingang automatisch", encoding="utf-8")
    watched = watch_once()
    assert watched["imported"]
    assert not inbox_file.exists()
    quiet = watch_once()
    assert quiet == {"imported": [], "rejected": []}


def _meta(title, **extra):
    payload = {
        "title": title,
        "notes": "",
        "document_date": None,
        "reminder_date": None,
        "is_tax_relevant": False,
        "correspondent_id": None,
        "doctype_id": None,
        "tag_ids": [],
    }
    payload.update(extra)
    return payload


def _upload(client, name, text):
    response = client.post(
        "/api/documents",
        files={"files": (name, text.encode("utf-8"), "text/plain")},
        headers=HEADER,
    )
    assert response.status_code == 201, response.text
    return response.json()["documents"][0]
