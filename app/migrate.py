"""Fehlende Spalten in bestehenden SQLite-Dateien nachziehen."""

from sqlalchemy import inspect, text

from app.database import engine


def upgrade_schema() -> None:
    inspector = inspect(engine)
    if "documents" not in inspector.get_table_names():
        return
    present = {column["name"] for column in inspector.get_columns("documents")}
    statements = []
    if "status" not in present:
        statements.append("ALTER TABLE documents ADD COLUMN status VARCHAR(40) DEFAULT 'neu'")
    if "retain_until" not in present:
        statements.append("ALTER TABLE documents ADD COLUMN retain_until DATE")
    if "version_number" not in present:
        statements.append("ALTER TABLE documents ADD COLUMN version_number INTEGER DEFAULT 1")
    if "field_text" not in present:
        statements.append("ALTER TABLE documents ADD COLUMN field_text TEXT DEFAULT ''")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
