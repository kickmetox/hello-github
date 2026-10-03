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


def resolve_template_zip_conflicts(
    conflict_titles: list[str],
    parent: QWidget | None = None,
) -> str:
    """
    Konflikt-Dialog beim Vorlagen-Zip-Import.
    Rückgabe: 'overwrite' | 'skip' | 'cancel'.
    """
    titles = [str(t).strip() for t in conflict_titles if str(t).strip()]
    if not titles:
        return "overwrite"
    sample = ", ".join(titles[:8])
    if len(titles) > 8:
        sample += f" … (+{len(titles) - 8})"
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle("Vorlagen-Import — Konflikte")
    box.setText(
        f"{len(titles)} Vorlage(n) mit gleichem Titel existieren bereits.\n\n"
        f"{sample}"
    )
    box.setInformativeText(
        "Überschreiben: lokale Vorlagen ersetzen.\n"
        "Überspringen: Konflikte behalten, nur neue importieren.\n"
        "Abbrechen: nichts importieren."
    )
    btn_over = box.addButton("Überschreiben", QMessageBox.AcceptRole)
    btn_skip = box.addButton("Überspringen", QMessageBox.ActionRole)
    btn_cancel = box.addButton("Abbrechen", QMessageBox.RejectRole)
    box.setDefaultButton(btn_skip)
    box.exec()
    clicked = box.clickedButton()
    if clicked is btn_over:
        return "overwrite"
    if clicked is btn_skip:
        return "skip"
    return "cancel"
