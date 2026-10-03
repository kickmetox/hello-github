"""Dialog: Wasserzeichen (Text/Bild, diagonal/zentriert, Vorschau, Bake) / Seitennummern — 1.6.0."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ild_pdf.watermark import (
    apply_image_watermark,
    apply_page_numbers,
    apply_watermark,
    render_watermark_preview,
)


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
        self.resize(720, 560)
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
        self._refresh_preview()

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
                self._refresh_preview()

        pick.clicked.connect(_pick)
        edit.textChanged.connect(lambda *_: self._refresh_preview())
        return edit, row

    def _build_wm_tab(self) -> QWidget:
        w = QWidget()
        root = QHBoxLayout(w)
        form_host = QWidget()
        form = QFormLayout(form_host)
        self.wm_src, src_row = self._path_row(self._initial)
        form.addRow("PDF", src_row)

        mode_row = QHBoxLayout()
        self.wm_mode_text = QRadioButton("Text")
        self.wm_mode_image = QRadioButton("Bild")
        self.wm_mode_text.setChecked(True)
        mode_row.addWidget(self.wm_mode_text)
        mode_row.addWidget(self.wm_mode_image)
        mode_row.addStretch(1)
        form.addRow("Art", mode_row)
        self.wm_mode_text.toggled.connect(self._on_wm_mode)
        self.wm_mode_image.toggled.connect(self._on_wm_mode)

        self.wm_text = QLineEdit("VERTRAULICH")
        self.wm_text.textChanged.connect(lambda *_: self._refresh_preview())
        form.addRow("Text", self.wm_text)

        img_row = QHBoxLayout()
        self.wm_image = QLineEdit()
        self.wm_image.setPlaceholderText("PNG / JPEG…")
        btn_img = QPushButton("Bild…")
        btn_img.clicked.connect(self._pick_image)
        img_row.addWidget(self.wm_image)
        img_row.addWidget(btn_img)
        form.addRow("Bild", img_row)
        self.wm_image.textChanged.connect(lambda *_: self._refresh_preview())

        self.wm_placement = QComboBox()
        self.wm_placement.addItem("Diagonal", "diagonal")
        self.wm_placement.addItem("Zentriert", "center")
        self.wm_placement.currentIndexChanged.connect(lambda *_: self._refresh_preview())
        form.addRow("Position", self.wm_placement)

        self.wm_opacity = QDoubleSpinBox()
        self.wm_opacity.setRange(0.05, 1.0)
        self.wm_opacity.setSingleStep(0.05)
        self.wm_opacity.setValue(0.25)
        self.wm_opacity.valueChanged.connect(lambda *_: self._refresh_preview())
        form.addRow("Deckkraft", self.wm_opacity)

        self.wm_angle = QDoubleSpinBox()
        self.wm_angle.setRange(-90, 90)
        self.wm_angle.setValue(45)
        self.wm_angle.valueChanged.connect(lambda *_: self._refresh_preview())
        form.addRow("Winkel °", self.wm_angle)

        self.wm_size = QDoubleSpinBox()
        self.wm_size.setRange(8, 120)
        self.wm_size.setValue(48)
        self.wm_size.valueChanged.connect(lambda *_: self._refresh_preview())
        form.addRow("Schriftgröße", self.wm_size)

        self.wm_img_scale = QDoubleSpinBox()
        self.wm_img_scale.setRange(0.1, 1.0)
        self.wm_img_scale.setSingleStep(0.05)
        self.wm_img_scale.setValue(0.45)
        self.wm_img_scale.valueChanged.connect(lambda *_: self._refresh_preview())
        form.addRow("Bild-Skalierung", self.wm_img_scale)

        self.wm_current = QCheckBox("Nur aktuelle Seite")
        form.addRow("", self.wm_current)
        self.wm_inplace = QCheckBox("Original überschreiben")
        self.wm_inplace.setChecked(False)
        self.wm_inplace.setToolTip("Standard: neues PDF (*_wm.pdf) — Bake — 1.6.0")
        form.addRow("", self.wm_inplace)

        btn_prev = QPushButton("Vorschau aktualisieren")
        btn_prev.clicked.connect(self._refresh_preview)
        form.addRow(btn_prev)
        run = QPushButton("Wasserzeichen in PDF bakken")
        run.setToolTip("Schreibt Text- oder Bild-Wasserzeichen in ein neues PDF — 1.6.0")
        run.clicked.connect(self._run_wm)
        form.addRow(run)

        root.addWidget(form_host, 3)
        prev_col = QVBoxLayout()
        prev_col.addWidget(QLabel("Vorschau (aktuelle Seite)"))
        self.wm_preview = QLabel("—")
        self.wm_preview.setAlignment(Qt.AlignCenter)
        self.wm_preview.setMinimumSize(260, 340)
        self.wm_preview.setStyleSheet(
            "QLabel { background:#2a2a2a; border:1px solid #555; color:#aaa; }"
        )
        self.wm_preview.setScaledContents(False)
        prev_col.addWidget(self.wm_preview, 1)
        root.addLayout(prev_col, 2)
        self._on_wm_mode()
        return w

    def _on_wm_mode(self, *_):
        is_text = self.wm_mode_text.isChecked()
        self.wm_text.setEnabled(is_text)
        self.wm_size.setEnabled(is_text)
        self.wm_image.setEnabled(not is_text)
        self.wm_img_scale.setEnabled(not is_text)
        # Winkel nur bei Diagonal relevant
        self._refresh_preview()

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Wasserzeichen-Bild",
            "",
            "Bilder (*.png *.jpg *.jpeg *.webp *.bmp);;Alle (*.*)",
        )
        if path:
            self.wm_image.setText(path)
            self.wm_mode_image.setChecked(True)
            self._refresh_preview()

    def _placement(self) -> str:
        data = self.wm_placement.currentData()
        return str(data or "diagonal")

    def _refresh_preview(self):
        src = (self.wm_src.text() if hasattr(self, "wm_src") else "").strip()
        if not src or not Path(src).is_file():
            if hasattr(self, "wm_preview"):
                self.wm_preview.setText("PDF wählen…")
                self.wm_preview.setPixmap(QPixmap())
            return
        try:
            mode = "text" if self.wm_mode_text.isChecked() else "image"
            img = render_watermark_preview(
                src,
                page_index=self._page_index,
                mode=mode,
                text=self.wm_text.text().strip() or "VERTRAULICH",
                image=self.wm_image.text().strip() or None,
                opacity=self.wm_opacity.value(),
                angle_deg=self.wm_angle.value(),
                font_size=self.wm_size.value(),
                scale=self.wm_img_scale.value(),
                placement=self._placement(),
                render_scale=0.85,
            )
            data = img.tobytes("raw", "RGB")
            qimg = QImage(data, img.width, img.height, img.width * 3, QImage.Format_RGB888)
            pm = QPixmap.fromImage(qimg.copy())
            scaled = pm.scaled(
                self.wm_preview.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.wm_preview.setPixmap(scaled)
            self.wm_preview.setText("")
        except Exception as e:
            self.wm_preview.setPixmap(QPixmap())
            self.wm_preview.setText(f"Vorschau:\n{e}")

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
        pages = [self._page_index] if self.wm_current.isChecked() else None
        path = Path(src)
        out = self._out_path(path, self.wm_inplace.isChecked(), "wm")
        placement = self._placement()
        try:
            if self.wm_mode_image.isChecked():
                img = self.wm_image.text().strip()
                if not img or not Path(img).is_file():
                    QMessageBox.warning(self, "Wasserzeichen", "Bilddatei angeben.")
                    return
                apply_image_watermark(
                    path,
                    img,
                    out_path=out,
                    pages=pages,
                    opacity=self.wm_opacity.value(),
                    angle_deg=self.wm_angle.value(),
                    scale=self.wm_img_scale.value(),
                    placement=placement,
                )
            else:
                text = self.wm_text.text().strip()
                if not text:
                    QMessageBox.warning(self, "Wasserzeichen", "Text angeben.")
                    return
                apply_watermark(
                    path,
                    text,
                    out_path=out,
                    pages=pages,
                    opacity=self.wm_opacity.value(),
                    angle_deg=self.wm_angle.value(),
                    font_size=self.wm_size.value(),
                    placement=placement,
                )
            self.result_path = str(out)
            QMessageBox.information(
                self,
                "Wasserzeichen",
                f"Gebacken / gespeichert:\n{out}",
            )
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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "wm_preview") and self.wm_preview.pixmap() and not self.wm_preview.pixmap().isNull():
            self._refresh_preview()
