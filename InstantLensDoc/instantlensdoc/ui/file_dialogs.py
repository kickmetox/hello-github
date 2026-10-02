"""Gemeinsame Datei-Dialog-Helfer (Overwrite-Schutz bei Export)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QWidget


def confirm_overwrite_export(
    dest: str | Path,
    parent: QWidget | None = None,
    *,
    title: str = "Datei überschreiben?",
) -> bool:
    """
    True wenn geschrieben werden darf.
    Existiert die Zieldatei nicht → True.
    Existiert sie → Ja/Nein-Dialog (Default: Nein).
    """
    path = Path(dest)
    if not path.is_file():
        return True
    reply = QMessageBox.question(
        parent,
        title,
        f"Die Datei existiert bereits:\n{path.name}\n\nÜberschreiben?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    return reply == QMessageBox.Yes
