"""Passwörter (PBKDF2) und undurchsichtige Sitzungscookies."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import timedelta

from fastapi import Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import SessionToken, User
from app.timeutil import utcnow


COOKIE = "docman_session"


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 200_000)
    return salt, digest.hex()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    _salt, digest = hash_password(password, salt)
    return hmac.compare_digest(digest, expected_hash)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db: Session, user: User) -> str:
    now = utcnow()
    db.execute(delete(SessionToken).where(SessionToken.expires_at < now))
    token = secrets.token_urlsafe(32)
    db.add(
        SessionToken(
            user_id=user.id,
            token_hash=_token_hash(token),
            expires_at=now + timedelta(days=settings.session_days),
            created_at=now,
        )
    )
    db.commit()
    return token


def user_from_request(request: Request, db: Session) -> User | None:
    raw = request.cookies.get(COOKIE)
    if not raw:
        return None
    row = db.scalar(select(SessionToken).where(SessionToken.token_hash == _token_hash(raw)))
    if row is None or row.expires_at < utcnow():
        return None
    return db.get(User, row.user_id)


def clear_session(request: Request, db: Session) -> None:
    raw = request.cookies.get(COOKIE)
    if not raw:
        return
    db.execute(delete(SessionToken).where(SessionToken.token_hash == _token_hash(raw)))
    db.commit()


def attach_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=settings.session_days * 24 * 3600,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")
