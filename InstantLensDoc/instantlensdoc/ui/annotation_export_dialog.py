"""Annotation-Export: aktuelle Seite / Dokument als JSON (ildann-v4) + optional Flatten-PDF — 1.2.0/1.2.1."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class AnnotationExportOptions:
    """Ergebnis des Export-Dialogs."""

    scope: str  # "page" | "document"
    json_path: Path
    flatten: bool
    flatten_path: Path | None


class AnnotationExportDialog(QDialog):
    """
    Export-Dialog: Scope (aktuelle Seite / gesamtes Dokument),
    JSON Schema ildann-v4, optional Flatten-PDF.
    Zielordner wird gemerkt; Dateiname aus Settings-Template ({stem}_ann.json) — 1.2.1.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        pdf_path: str | Path | None = None,
        current_page: int = 0,
        page_count: int = 1,
        ann_count: int = 0,
        page_ann_count: int = 0,
    ):
        super().__init__(parent)
        self.setWindowTitle("Annotationen exportieren (JSON / Flatten)")
        self.resize(520, 300)
        self._pdf_path = Path(pdf_path) if pdf_path else None
        self._current_page = max(0, int(current_page))
        self._page_count = max(1, int(page_count))
        self.result_options: AnnotationExportOptions | None = None

        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                f"Schema <b>ildann-v4</b> · Seite {self._current_page + 1}/{self._page_count} · "
                f"{page_ann_count} Ann. auf Seite / {ann_count} gesamt"
            )
        )

        self.radio_page = QRadioButton(
            f"Aktuelle Seite ({self._current_page + 1}) — {page_ann_count} Annotation(en)"
        )
        self.radio_doc = QRadioButton(
            f"Gesamtes Dokument — {ann_count} Annotation(en)"
        )
        self.radio_doc.setChecked(True)
        self.radio_page.setToolTip("Nur Annotationen der aktuellen Seite als JSON — 1.2.0")
        self.radio_doc.setToolTip("Alle Annotationen des Dokuments als JSON — 1.2.0")
        root.addWidget(self.radio_page)
        root.addWidget(self.radio_doc)

        from instantlensdoc.core.app_settings import get_ann_export_filename_template

        tpl = get_ann_export_filename_template()
        root.addWidget(
            QLabel(
                f"Dateiname-Template (Einstellungen): <code>{tpl}</code><br>"
                "Platzhalter: <b>{stem}</b>, <b>{page}</b>, <b>{date}</b> (YYYY-MM-DD) — 1.2.2"
            )
        )

        form = QFormLayout()
        default_json, default_flat = self._default_paths()
        self.json_path = QLineEdit(default_json)
        btn_json = QPushButton("…")
        btn_json.setFixedWidth(32)
        btn_json.clicked.connect(self._pick_json)
        json_row = QHBoxLayout()
        json_row.addWidget(self.json_path, 1)
        json_row.addWidget(btn_json)
        form.addRow("JSON (ildann-v4)", json_row)

        self.chk_flatten = QCheckBox("Zusätzlich Flatten-PDF erzeugen")
        self.chk_flatten.setToolTip(
            "Seiten mit eingebrannten Annotationen als neues PDF speichern — 1.2.0"
        )
        self.chk_flatten.toggled.connect(self._sync_flatten_enabled)
        form.addRow(self.chk_flatten)

        self.flatten_path = QLineEdit(default_flat)
        btn_flat = QPushButton("…")
        btn_flat.setFixedWidth(32)
        btn_flat.clicked.connect(self._pick_flatten)
        flat_row = QHBoxLayout()
        flat_row.addWidget(self.flatten_path, 1)
        flat_row.addWidget(btn_flat)
        form.addRow("Flatten-PDF", flat_row)
        root.addLayout(form)

        self._flat_btn = btn_flat
        self._sync_flatten_enabled(False)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.radio_page.toggled.connect(self._update_defaults_for_scope)
        self.radio_doc.toggled.connect(self._update_defaults_for_scope)

    def _export_dir(self) -> Path:
        """Gemerkter Zielordner oder PDF-Ordner — 1.2.1."""
        from instantlensdoc.core.app_settings import get_last_ann_export_dir

        remembered = get_last_ann_export_dir()
        if remembered is not None:
            return remembered
        if self._pdf_path is not None:
            return self._pdf_path.parent
        return Path.cwd()

    def _default_paths(self) -> tuple[str, str]:
        from instantlensdoc.core.app_settings import (
            format_ann_export_filename,
            get_ann_export_filename_template,
        )

        if not self._pdf_path:
            return "", ""
        stem = self._pdf_path.stem
        parent = self._export_dir()
        page_scope = hasattr(self, "radio_page") and self.radio_page.isChecked()
        page = self._current_page + 1 if page_scope else None
        tpl = get_ann_export_filename_template()
        if page is not None:
            if "{page}" in tpl:
                fname = format_ann_export_filename(stem, page=page, template=tpl)
            else:
                # Standard-Template ohne {page}: Seiten-Suffix einfügen
                fname = format_ann_export_filename(stem, page=None, template=tpl)
                if fname.endswith("_ann.json"):
                    fname = f"{stem}_p{page}_ann.json"
                else:
                    fname = f"{Path(fname).stem}_p{page}.json"
        else:
            fname = format_ann_export_filename(stem, page=None, template=tpl)
        json_path = str(parent / fname)
        if page is not None:
            flat = str(parent / f"{stem}_p{page}_flattened.pdf")
        else:
            flat = str(parent / f"{stem}_flattened.pdf")
        return json_path, flat

    def _sync_flatten_enabled(self, checked: bool) -> None:
        self.flatten_path.setEnabled(bool(checked))
        self._flat_btn.setEnabled(bool(checked))

    def _update_defaults_for_scope(self, *_args) -> None:
        if not self._pdf_path:
            return
        j, f = self._default_paths()
        self.json_path.setText(j)
        self.flatten_path.setText(f)

    def _pick_json(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        from instantlensdoc.core.app_settings import dialog_start_dir, get_last_ann_export_dir

        start = dialog_start_dir(
            self.json_path.text().strip() or None,
            get_last_ann_export_dir(),
            self._pdf_path.parent if self._pdf_path else None,
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Annotationen JSON",
            start
            if not self.json_path.text().strip()
            else self.json_path.text().strip(),
            "JSON (*.json);;Annotation-Sidecar (*.ildann.json);;Alle (*.*)",
        )
        if path:
            if not path.lower().endswith(".json"):
                path += ".json"
            self.json_path.setText(path)

    def _pick_flatten(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        from instantlensdoc.core.app_settings import dialog_start_dir, get_last_ann_export_dir

        start = self.flatten_path.text().strip() or dialog_start_dir(
            get_last_ann_export_dir(),
            self._pdf_path.parent if self._pdf_path else None,
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Flatten-PDF",
            start,
            "PDF (*.pdf);;Alle (*.*)",
        )
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            self.flatten_path.setText(path)

    def _accept(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        from instantlensdoc.core.app_settings import (
            remember_recent_dir,
            set_last_ann_export_dir,
            set_last_export_dir,
        )

        j = self.json_path.text().strip()
        if not j:
            QMessageBox.warning(self, "Export", "Bitte JSON-Zielpfad angeben.")
            return
        jpath = Path(j)
        if jpath.suffix.lower() != ".json":
            jpath = jpath.with_suffix(".json")
        flatten = self.chk_flatten.isChecked()
        fpath: Path | None = None
        if flatten:
            f = self.flatten_path.text().strip()
            if not f:
                QMessageBox.warning(self, "Export", "Bitte Flatten-PDF-Ziel angeben.")
                return
            fpath = Path(f)
            if fpath.suffix.lower() != ".pdf":
                fpath = fpath.with_suffix(".pdf")
            if self._pdf_path and fpath.resolve() == self._pdf_path.resolve():
                QMessageBox.warning(
                    self,
                    "Export",
                    "Flatten-Ziel darf nicht die aktuelle PDF-Datei sein.",
                )
                return
        scope = "page" if self.radio_page.isChecked() else "document"
        # Zielordner merken — 1.2.1
        set_last_ann_export_dir(jpath.parent)
        set_last_export_dir(jpath.parent)
        remember_recent_dir(jpath.parent)
        self.result_options = AnnotationExportOptions(
            scope=scope,
            json_path=jpath,
            flatten=flatten,
            flatten_path=fpath,
        )
        self.accept()
