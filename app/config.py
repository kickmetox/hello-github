"""Laufzeitpfade und Grenzen. Alles bleibt relativ zum Projektordner."""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _data_dir() -> Path:
    raw = os.environ.get("DOCMAN_DATA", "data")
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


class Settings:
    def __init__(self) -> None:
        self.host = os.environ.get("DOCMAN_HOST", "127.0.0.1")
        self.port = int(os.environ.get("DOCMAN_PORT", "8000"))
        self.data_dir = _data_dir()
        self.files_dir = self.data_dir / "files"
        self.inbox_dir = self.data_dir / "inbox"
        self.rejected_dir = self.data_dir / "rejected"
        self.db_path = self.data_dir / "docman.db"
        self.seed = os.environ.get("DOCMAN_SEED", "1") != "0"
        self.max_upload_bytes = 25 * 1024 * 1024
        self.max_files_per_upload = 20
        self.session_days = 14

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path.as_posix()}"


settings = Settings()

ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".log": "text/plain; charset=utf-8",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

PREVIEW_INLINE = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".txt", ".md", ".csv", ".json", ".log"}
