"""Gemeinsame Datei-Dialog-Helfer (Overwrite-Schutz bei Export)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget


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
    *,
    dry_run_rows: list[dict] | None = None,
) -> str:
    """
    Konflikt-Dialog beim Vorlagen-Zip-Import inkl. Dry-Run-Liste.
    Rückgabe: 'overwrite' | 'skip' | 'cancel'.
    dry_run_rows: optionale Zeilen aus dry_run_user_templates_zip_import
      (action overwrite/add) — zeigt was überschrieben würde.
    Optional: Konfliktliste als TXT exportieren.
    """
    titles = [str(t).strip() for t in conflict_titles if str(t).strip()]
    if not titles and not dry_run_rows:
        return "overwrite"

    overwrite_titles: list[str] = []
    add_titles: list[str] = []
    if dry_run_rows:
        for row in dry_run_rows:
            t = str(row.get("title") or "").strip()
            if not t:
                continue
            if str(row.get("action") or "") == "overwrite":
                overwrite_titles.append(t)
            else:
                add_titles.append(t)
    if not overwrite_titles:
        overwrite_titles = list(titles)

    def _sample(items: list[str], limit: int = 12) -> str:
        sample = ", ".join(items[:limit])
        if len(items) > limit:
            sample += f" … (+{len(items) - limit})"
        return sample

    over_n = len(overwrite_titles)
    add_n = len(add_titles)
    lines = [
        f"Dry-Run: {over_n} Vorlage(n) würden überschrieben.",
    ]
    if overwrite_titles:
        lines.append(f"Überschreiben: {_sample(overwrite_titles)}")
    if add_titles:
        lines.append(f"Neu: {_sample(add_titles)} ({add_n})")

    while True:
        box = QMessageBox(parent)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Vorlagen-Import — Dry-Run / Konflikte")
        box.setText("\n".join(lines))
        box.setInformativeText(
            "Überschreiben: lokale Vorlagen ersetzen.\n"
            "Überspringen: Konflikte behalten, nur neue importieren.\n"
            "Liste als TXT: Konfliktliste speichern.\n"
            "Abbrechen: nichts importieren."
        )
        btn_over = box.addButton("Überschreiben", QMessageBox.AcceptRole)
        btn_skip = box.addButton("Überspringen", QMessageBox.ActionRole)
        btn_txt = box.addButton("Liste als TXT…", QMessageBox.ActionRole)
        btn_cancel = box.addButton("Abbrechen", QMessageBox.RejectRole)
        box.setDefaultButton(btn_skip)
        box.exec()
        clicked = box.clickedButton()
        if clicked is btn_txt:
            _export_dry_run_conflict_txt(
                parent,
                dry_run_rows=dry_run_rows,
                conflict_titles=overwrite_titles,
            )
            continue
        if clicked is btn_over:
            return "overwrite"
        if clicked is btn_skip:
            return "skip"
        return "cancel"


def _export_dry_run_conflict_txt(
    parent: QWidget | None,
    *,
    dry_run_rows: list[dict] | None = None,
    conflict_titles: list[str] | None = None,
) -> Path | None:
    """Konfliktliste als TXT speichern (Dateidialog)."""
    from instantlensdoc.core.app_settings import (
        dialog_start_dir,
        export_dry_run_conflict_list_txt,
        get_last_export_dir,
        set_last_export_dir,
    )

    start = dialog_start_dir(get_last_export_dir())
    path, _ = QFileDialog.getSaveFileName(
        parent,
        "Konfliktliste als TXT speichern",
        str(Path(start) / "ild-templates-dry-run.txt"),
        "Textdatei (*.txt);;Alle Dateien (*)",
    )
    if not path:
        return None
    if not path.lower().endswith(".txt"):
        path = path + ".txt"
    try:
        dest = export_dry_run_conflict_list_txt(
            path,
            dry_run_rows,
            conflict_titles=conflict_titles,
        )
    except Exception as exc:
        QMessageBox.warning(
            parent,
            "Konfliktliste exportieren",
            f"TXT-Export fehlgeschlagen:\n{exc}",
        )
        return None
    set_last_export_dir(Path(dest).parent)
    QMessageBox.information(
        parent,
        "Konfliktliste exportieren",
        f"Gespeichert:\n{dest}",
    )
    return dest
