"""Gemeinsame Datei-Dialog-Helfer (Overwrite-Schutz bei Export)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from instantlensdoc.core.fs_path import native_fs_path

if TYPE_CHECKING:
    from instantlensdoc.core.documents import DocKind

# Dokument-Speichern (Text/Word-Suite) — 2.6.43
# Windows + python.exe hängt sonst bei namen ohne Endung oft *.py an.
DOC_SAVE_FILTER_ENTRIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ILD Dokument", (".ild",)),
    ("Text", (".txt",)),
    ("Markdown", (".md", ".markdown")),
    ("HTML", (".html", ".htm")),
    ("DOCX", (".docx",)),
    ("RTF", (".rtf",)),
    ("CSV", (".csv",)),
    ("Excel", (".xlsx", ".xls")),
    ("PDF", (".pdf",)),
)

_DOC_SAVE_KNOWN_EXTS = frozenset(
    ext for _label, exts in DOC_SAVE_FILTER_ENTRIES for ext in exts
) | frozenset({".markdown", ".htm"})


def picked_fs_path(path: str | Path | None) -> str:
    """QFileDialog/QUrl result: accept ``/`` and ``\\``, return native separators."""
    return native_fs_path(path) if path else ""


def get_open_file_name(
    parent: Any,
    caption: str,
    directory: str | Path = "",
    filter: str = "Alle Dateien (*)",  # noqa: A002
) -> tuple[str, str]:
    """``QFileDialog.getOpenFileName`` with native-separator result."""
    from PySide6.QtWidgets import QFileDialog

    start = native_fs_path(directory) if directory else ""
    path, selected = QFileDialog.getOpenFileName(parent, caption, start, filter)
    return picked_fs_path(path), selected


def get_open_file_names(
    parent: Any,
    caption: str,
    directory: str | Path = "",
    filter: str = "Alle Dateien (*)",  # noqa: A002
) -> tuple[list[str], str]:
    """``QFileDialog.getOpenFileNames`` with native-separator results."""
    from PySide6.QtWidgets import QFileDialog

    start = native_fs_path(directory) if directory else ""
    paths, selected = QFileDialog.getOpenFileNames(parent, caption, start, filter)
    return [picked_fs_path(p) for p in (paths or []) if p], selected


def get_save_file_name(
    parent: Any,
    caption: str,
    directory: str | Path = "",
    filter: str = "Alle Dateien (*)",  # noqa: A002
) -> tuple[str, str]:
    """``QFileDialog.getSaveFileName`` with native-separator result."""
    from PySide6.QtWidgets import QFileDialog

    start = native_fs_path(directory) if directory else ""
    path, selected = QFileDialog.getSaveFileName(parent, caption, start, filter)
    return picked_fs_path(path), selected


def get_existing_directory(
    parent: Any,
    caption: str,
    directory: str | Path = "",
) -> str:
    """``QFileDialog.getExistingDirectory`` with native-separator result."""
    from PySide6.QtWidgets import QFileDialog

    start = native_fs_path(directory) if directory else ""
    path = QFileDialog.getExistingDirectory(parent, caption, start)
    return picked_fs_path(path)


def document_save_name_filters() -> str:
    """Qt-Name-Filter für Speichern/Speichern unter (Dokumente, kein *.py)."""
    parts: list[str] = []
    for label, exts in DOC_SAVE_FILTER_ENTRIES:
        globs = " ".join(f"*{e}" for e in exts)
        parts.append(f"{label} ({globs})")
    parts.append("Alle Dateien (*)")
    return ";;".join(parts)


def document_open_name_filters() -> str:
    """Qt-Name-Filter für Datei ▸ Öffnen (MD/CSV/Excel inkl. .xls)."""
    return (
        "Dokumente (*.ild *.txt *.md *.markdown *.html *.htm *.docx *.rtf "
        "*.csv *.xls *.xlsx *.pdf *.png *.jpg *.jpeg);;"
        "Markdown (*.md *.markdown);;"
        "Excel (*.xlsx *.xls);;"
        "CSV (*.csv);;"
        "Alle (*.*)"
    )


def document_save_default_suffix(kind: "DocKind | str | None" = None) -> str:
    """Standard-Endung für unbenannte Dokumente (nie .py)."""
    from instantlensdoc.core.documents import DocKind

    if kind is None:
        return ".ild"
    key = kind.value if isinstance(kind, DocKind) else str(kind).strip().lower()
    return {
        DocKind.TEXT.value: ".ild",
        DocKind.MARKDOWN.value: ".md",
        DocKind.HTML.value: ".html",
        DocKind.DOCX.value: ".docx",
        DocKind.RTF.value: ".rtf",
        DocKind.CSV.value: ".csv",
        DocKind.XLSX.value: ".xlsx",
        DocKind.PDF.value: ".pdf",
    }.get(key, ".ild")


def document_save_suggested_name(
    display_name: str | None,
    *,
    kind: "DocKind | str | None" = None,
    path: str | Path | None = None,
) -> str:
    """Vorschlagsdateiname inkl. sinnvoller Endung (gegen Windows-.py-Default)."""
    if path is not None:
        p = Path(path)
        if p.name:
            return p.name
    raw = (display_name or "").strip() or "Unbenannt"
    stem_path = Path(raw)
    suf = stem_path.suffix.lower()
    if suf in _DOC_SAVE_KNOWN_EXTS:
        return stem_path.name
    # „Unbenannt.py“ / fremde Skript-Endungen → Dokument-Default
    if suf in {".py", ".pyw", ".pyc"}:
        return stem_path.stem + document_save_default_suffix(kind)
    if suf:
        # Unbekannte Endung belassen (Nutzer hat evtl. bewusst gewählt)
        return stem_path.name
    return stem_path.name + document_save_default_suffix(kind)


def document_save_ext_from_filter(selected_filter: str | None) -> str | None:
    """Erste Endung aus dem gewählten Qt-Filter, sonst None."""
    sel = (selected_filter or "").lower()
    if not sel or sel.startswith("alle dateien") or "(*)" in sel:
        return None
    for _label, exts in DOC_SAVE_FILTER_ENTRIES:
        for ext in exts:
            token = f"*{ext}"
            if token in sel:
                return ext
    return None


def ensure_document_save_extension(
    path: str | Path,
    selected_filter: str | None = None,
    *,
    default_suffix: str = ".ild",
) -> Path:
    """Endung aus Filter/Default setzen, wenn fehlend oder .py vom Host."""
    dest = Path(path)
    suf = dest.suffix.lower()
    wanted = document_save_ext_from_filter(selected_filter)
    if wanted is None:
        wanted = default_suffix if default_suffix.startswith(".") else f".{default_suffix}"
    if not suf or suf in {".py", ".pyw", ".pyc"}:
        return dest.with_suffix(wanted)
    return dest


def document_save_filters_are_safe(filter_str: str | None = None) -> bool:
    """True wenn Dokument-Filter die Pflichtformate hat und *.py nicht primär ist."""
    text = filter_str if filter_str is not None else document_save_name_filters()
    low = text.lower()
    required = (".ild", ".txt", ".docx", ".pdf", ".rtf", ".html")
    if any(ext not in low for ext in required):
        return False
    # Dedizierter Python-Filter oder *.py als erstes Glob → unzulässig für Docs
    first = text.split(";;", 1)[0].lower()
    if "*.py" in first or "python (" in first:
        return False
    if "python (*" in low:
        return False
    return True


def get_document_save_file_name(
    parent: Any,
    title: str,
    directory: str | Path,
    suggested_name: str,
    *,
    default_suffix: str = ".ild",
    name_filter: str | None = None,
) -> tuple[str, str]:
    """
    Speichern-unter-Dialog für Text/Word-Suite-Dokumente.
    Setzt DefaultSuffix + Vorschlagsname mit Endung (kein Windows-.py-Default).
    """
    from PySide6.QtWidgets import QFileDialog

    filt = name_filter or document_save_name_filters()
    suffix = (default_suffix or ".ild").lstrip(".") or "ild"
    # Qt accepts / and \\; start dir is native so the dialog shows Windows paths.
    start_dir = native_fs_path(directory) if directory else ""
    dlg = QFileDialog(parent, title, start_dir)
    dlg.setAcceptMode(QFileDialog.AcceptSave)
    dlg.setFileMode(QFileDialog.AnyFile)
    dlg.setNameFilters([p for p in filt.split(";;") if p.strip()])
    dlg.setDefaultSuffix(suffix)
    # Ersten Dokument-Filter wählen (ILD), nie „Alle Dateien“
    filters = dlg.nameFilters()
    if filters:
        dlg.selectNameFilter(filters[0])
    dlg.selectFile(suggested_name)
    if not dlg.exec():
        return "", ""
    files = dlg.selectedFiles()
    path = files[0] if files else ""
    selected = dlg.selectedNameFilter()
    if path:
        path = native_fs_path(
            ensure_document_save_extension(
                path, selected, default_suffix=f".{suffix}"
            )
        )
    return path, selected


def confirm_overwrite_export(
    dest: str | Path,
    parent: Any = None,
    *,
    title: str = "Datei überschreiben?",
) -> bool:
    """
    True wenn geschrieben werden darf.
    Existiert die Zieldatei nicht → True.
    Existiert sie → Ja/Nein-Dialog (Default: Nein).
    """
    from PySide6.QtWidgets import QMessageBox

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
    parent: Any = None,
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
    from PySide6.QtWidgets import QMessageBox

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
    parent: Any = None,
    *,
    dry_run_rows: list[dict] | None = None,
    conflict_titles: list[str] | None = None,
) -> Path | None:
    """Konfliktliste als TXT speichern (Dateidialog)."""
    from PySide6.QtWidgets import QMessageBox
    from instantlensdoc.core.app_settings import (
        dialog_start_dir,
        export_dry_run_conflict_list_txt,
        get_last_export_dir,
        set_last_export_dir,
    )

    start = dialog_start_dir(get_last_export_dir())
    path, _ = get_save_file_name(
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
