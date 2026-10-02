"""Dialog: Wasserzeichen / Seitennummern auf PDF."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ild_pdf.watermark import apply_page_numbers, apply_watermark


class WatermarkDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        pdf_path: str | None = None,
        page_index: int = 0,
        page_count: int = 1,
    ):
        super().__init__(parent)
        self.setWindowTitle("Wasserzeichen / Seitennummern")
        self.resize(480, 360)
        self._initial = pdf_path or ""
        self._page_index = page_index
        self._page_count = max(page_count, 1)
        self.result_path: str | None = None

        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_wm_tab(), "Wasserzeichen")
        tabs.addTab(self._build_num_tab(), "Seitennummern")
        layout.addWidget(tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _path_row(self, initial: str) -> tuple[QLineEdit, QHBoxLayout]:
        edit = QLineEdit(initial)
        pick = QPushButton("PDF…")
        row = QHBoxLayout()
        row.addWidget(edit)
        row.addWidget(pick)

        def _pick():
            path, _ = QFileDialog.getOpenFileName(self, "PDF", "", "PDF (*.pdf)")
            if path:
                edit.setText(path)

        pick.clicked.connect(_pick)
        return edit, row

    def _build_wm_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.wm_src, src_row = self._path_row(self._initial)
        form.addRow("PDF", src_row)
        self.wm_text = QLineEdit("VERTRAULICH")
        form.addRow("Text", self.wm_text)
        self.wm_opacity = QDoubleSpinBox()
        self.wm_opacity.setRange(0.05, 1.0)
        self.wm_opacity.setSingleStep(0.05)
        self.wm_opacity.setValue(0.25)
        form.addRow("Deckkraft", self.wm_opacity)
        self.wm_angle = QDoubleSpinBox()
        self.wm_angle.setRange(-90, 90)
        self.wm_angle.setValue(45)
        form.addRow("Winkel °", self.wm_angle)
        self.wm_size = QDoubleSpinBox()
        self.wm_size.setRange(8, 120)
        self.wm_size.setValue(48)
        form.addRow("Schriftgröße", self.wm_size)
        self.wm_current = QCheckBox("Nur aktuelle Seite")
        form.addRow("", self.wm_current)
        self.wm_inplace = QCheckBox("Original überschreiben")
        self.wm_inplace.setChecked(True)
        form.addRow("", self.wm_inplace)
        run = QPushButton("Wasserzeichen anwenden")
        run.clicked.connect(self._run_wm)
        form.addRow(run)
        return w

    def _build_num_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.num_src, src_row = self._path_row(self._initial)
        form.addRow("PDF", src_row)
        self.num_tpl = QLineEdit("{n} / {total}")
        self.num_tpl.setToolTip("Platzhalter: {n}, {total}, {i}")
        form.addRow("Vorlage", self.num_tpl)
        self.num_pos = QComboBox()
        self.num_pos.addItems(
            ["bottom-center", "bottom-right", "bottom-left", "top-center"]
        )
        form.addRow("Position", self.num_pos)
        self.num_size = QDoubleSpinBox()
        self.num_size.setRange(6, 36)
        self.num_size.setValue(10)
        form.addRow("Schriftgröße", self.num_size)
        self.num_start = QSpinBox()
        self.num_start.setRange(0, 9999)
        self.num_start.setValue(1)
        form.addRow("Startnummer", self.num_start)
        self.num_inplace = QCheckBox("Original überschreiben")
        self.num_inplace.setChecked(True)
        form.addRow("", self.num_inplace)
        run = QPushButton("Seitennummern stempeln")
        run.clicked.connect(self._run_num)
        form.addRow(run)
        return w

    def _out_path(self, src: Path, inplace: bool, suffix: str) -> Path:
        if inplace:
            return src
        return src.with_name(f"{src.stem}_{suffix}{src.suffix}")

    def _run_wm(self):
        src = self.wm_src.text().strip()
        if not src:
            QMessageBox.warning(self, "Wasserzeichen", "PDF angeben.")
            return
        text = self.wm_text.text().strip()
        if not text:
            QMessageBox.warning(self, "Wasserzeichen", "Text angeben.")
            return
        try:
            path = Path(src)
            pages = [self._page_index] if self.wm_current.isChecked() else None
            out = self._out_path(path, self.wm_inplace.isChecked(), "wm")
            apply_watermark(
                path,
                text,
                out_path=out,
                pages=pages,
                opacity=self.wm_opacity.value(),
                angle_deg=self.wm_angle.value(),
                font_size=self.wm_size.value(),
            )
            self.result_path = str(out)
            QMessageBox.information(self, "Wasserzeichen", f"Gespeichert:\n{out}")
        except Exception as e:
            QMessageBox.critical(self, "Wasserzeichen", str(e))

    def _run_num(self):
        src = self.num_src.text().strip()
        if not src:
            QMessageBox.warning(self, "Seitennummern", "PDF angeben.")
            return
        try:
            path = Path(src)
            out = self._out_path(path, self.num_inplace.isChecked(), "pages")
            apply_page_numbers(
                path,
                out_path=out,
                template=self.num_tpl.text().strip() or "{n} / {total}",
                position=self.num_pos.currentText(),
                font_size=self.num_size.value(),
                start_at=self.num_start.value(),
            )
            self.result_path = str(out)
            QMessageBox.information(self, "Seitennummern", f"Gespeichert:\n{out}")
        except Exception as e:
            QMessageBox.critical(self, "Seitennummern", str(e))
