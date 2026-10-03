"""Zwei PDFs Seite-nebeneinander vergleichen + Raster-Diff Overlay — 1.4.1."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
)

from ild_pdf.diff import raster_diff
from ild_pdf.limits import clamp_render_scale, inspect_pdf
from ild_pdf.render import render_page
from instantlensdoc.core.app_settings import (
    PDF_COMPARE_DIFF_THRESHOLD_MAX,
    PDF_COMPARE_DIFF_THRESHOLD_MIN,
    get_pdf_compare_diff_threshold,
    get_pdf_compare_page_sync,
    set_pdf_compare_diff_threshold,
    set_pdf_compare_page_sync,
)


def _pil_to_qpixmap(img) -> QPixmap:
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    data = img.tobytes("raw", img.mode)
    fmt = QImage.Format_RGBA8888 if img.mode == "RGBA" else QImage.Format_RGB888
    qimg = QImage(data, img.width, img.height, fmt).copy()
    return QPixmap.fromImage(qimg)


class PdfCompareDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        left_pdf: str | None = None,
        right_pdf: str | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("PDF vergleichen (Seite neben Seite + Diff)")
        self.resize(1100, 720)
        self._left = left_pdf or ""
        self._right = right_pdf or ""
        self._left_pages = 0
        self._right_pages = 0
        self._scale = 1.0
        self._left_img = None
        self._right_img = None
        self._diff_overlay = None  # PIL Image für PNG-Export — 1.4.1

        root = QVBoxLayout(self)
        pick = QHBoxLayout()
        self.btn_left = QPushButton("Linkes PDF…")
        self.btn_right = QPushButton("Rechtes PDF…")
        self.lbl_left_path = QLabel(self._left or "—")
        self.lbl_right_path = QLabel(self._right or "—")
        self.lbl_left_path.setWordWrap(True)
        self.lbl_right_path.setWordWrap(True)
        self.btn_left.clicked.connect(lambda: self._pick(True))
        self.btn_right.clicked.connect(lambda: self._pick(False))
        pick.addWidget(self.btn_left)
        pick.addWidget(self.lbl_left_path, 1)
        pick.addWidget(self.btn_right)
        pick.addWidget(self.lbl_right_path, 1)
        root.addLayout(pick)

        nav = QHBoxLayout()
        self.spin_left = QSpinBox()
        self.spin_right = QSpinBox()
        self.spin_left.setMinimum(1)
        self.spin_right.setMinimum(1)
        self.spin_left.valueChanged.connect(lambda _: self._refresh(side="left"))
        self.spin_right.valueChanged.connect(lambda _: self._refresh(side="right"))
        # Seitenwahl Sync / Entkoppelt — 1.4.1
        self.chk_sync = QCheckBox("Seiten Sync")
        self.chk_sync.setChecked(get_pdf_compare_page_sync())
        self.chk_sync.setToolTip(
            "An: Seitenwahl gekoppelt (Sync). Aus: Entkoppelt — "
            "Links/Rechts unabhängig — 1.4.1"
        )
        self.chk_sync.toggled.connect(self._on_sync_toggled)
        self.chk_diff = QCheckBox("Raster-Diff Overlay")
        self.chk_diff.setChecked(True)
        self.chk_diff.setToolTip(
            "Magenta-Overlay der Pixel-Unterschiede + Ähnlichkeit % — 1.4.0/1.4.1"
        )
        self.chk_diff.toggled.connect(lambda _: self._refresh())
        self.spin_threshold = QSpinBox()
        self.spin_threshold.setRange(
            PDF_COMPARE_DIFF_THRESHOLD_MIN, PDF_COMPARE_DIFF_THRESHOLD_MAX
        )
        self.spin_threshold.setValue(get_pdf_compare_diff_threshold())
        self.spin_threshold.setToolTip(
            "Diff-Schwelle 0–255 (Settings); niedriger = empfindlicher — 1.4.1"
        )
        self.spin_threshold.valueChanged.connect(self._on_threshold_changed)
        btn_export = QPushButton("Diff PNG…")
        btn_export.setToolTip("Aktuelles Diff-Overlay als PNG speichern — 1.4.1")
        btn_export.clicked.connect(self._export_diff_png)
        self.btn_export_diff = btn_export
        btn_reload = QPushButton("Aktualisieren")
        btn_reload.clicked.connect(lambda: self._refresh())
        nav.addWidget(QLabel("Links Seite"))
        nav.addWidget(self.spin_left)
        nav.addWidget(QLabel("Rechts Seite"))
        nav.addWidget(self.spin_right)
        nav.addWidget(self.chk_sync)
        nav.addWidget(self.chk_diff)
        nav.addWidget(QLabel("Schwelle"))
        nav.addWidget(self.spin_threshold)
        nav.addWidget(btn_export)
        nav.addWidget(btn_reload)
        nav.addStretch()
        root.addLayout(nav)

        self.lbl_similarity = QLabel("Ähnlichkeit: —")
        self.lbl_similarity.setToolTip(
            "Grobe Prozent-Ähnlichkeit nach Pixel-Schwellwert — 1.4.1"
        )
        self.lbl_sync_mode = QLabel("")
        self._update_sync_label()
        mode_row = QHBoxLayout()
        mode_row.addWidget(self.lbl_similarity, 1)
        mode_row.addWidget(self.lbl_sync_mode)
        root.addLayout(mode_row)

        panes = QHBoxLayout()
        self.view_left = QLabel(alignment=Qt.AlignCenter)
        self.view_right = QLabel(alignment=Qt.AlignCenter)
        self.view_diff = QLabel(alignment=Qt.AlignCenter)
        self.view_left.setText("Kein PDF")
        self.view_right.setText("Kein PDF")
        self.view_diff.setText("Diff")
        self.view_left.setMinimumSize(280, 420)
        self.view_right.setMinimumSize(280, 420)
        self.view_diff.setMinimumSize(280, 420)
        sl = QScrollArea()
        sr = QScrollArea()
        sd = QScrollArea()
        sl.setWidgetResizable(True)
        sr.setWidgetResizable(True)
        sd.setWidgetResizable(True)
        sl.setWidget(self.view_left)
        sr.setWidget(self.view_right)
        sd.setWidget(self.view_diff)
        panes.addWidget(sl)
        panes.addWidget(sr)
        panes.addWidget(sd)
        root.addLayout(panes, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        if self._left:
            self._load_meta(True)
        if self._right:
            self._load_meta(False)
        self._refresh()

    def _update_sync_label(self) -> None:
        if self.chk_sync.isChecked():
            self.lbl_sync_mode.setText("Modus: Sync — 1.4.1")
        else:
            self.lbl_sync_mode.setText("Modus: Entkoppelt — 1.4.1")

    def _on_sync_toggled(self, checked: bool = False) -> None:
        set_pdf_compare_page_sync(bool(checked))
        self._update_sync_label()
        if checked:
            # Sofort angleichen
            self._refresh(side="left")
        else:
            self._refresh()

    def _on_threshold_changed(self, value: int = 0) -> None:
        set_pdf_compare_diff_threshold(int(value))
        self._refresh()

    def _export_diff_png(self) -> None:
        """Aktuelles Diff-Overlay als PNG speichern — 1.4.1."""
        if self._diff_overlay is None:
            QMessageBox.information(
                self,
                "Diff PNG",
                "Kein Diff-Overlay vorhanden. Raster-Diff aktivieren und PDFs wählen.",
            )
            return
        default = "pdf-diff.png"
        if self._left and self._right:
            default = (
                f"{Path(self._left).stem}_vs_{Path(self._right).stem}"
                f"_p{self.spin_left.value()}-{self.spin_right.value()}_diff.png"
            )
        path, _ = QFileDialog.getSaveFileName(
            self, "Diff als PNG speichern", default, "PNG (*.png)"
        )
        if not path:
            return
        try:
            out = Path(path)
            if out.suffix.lower() != ".png":
                out = out.with_suffix(".png")
            self._diff_overlay.save(str(out), "PNG")
            QMessageBox.information(
                self, "Diff PNG", f"Gespeichert:\n{out}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Diff PNG", str(e))

    def _pick(self, left: bool):
        path, _ = QFileDialog.getOpenFileName(self, "PDF wählen", "", "PDF (*.pdf)")
        if not path:
            return
        if left:
            self._left = path
            self.lbl_left_path.setText(path)
            self._load_meta(True)
        else:
            self._right = path
            self.lbl_right_path.setText(path)
            self._load_meta(False)
        self._refresh()

    def _load_meta(self, left: bool):
        path = self._left if left else self._right
        try:
            health = inspect_pdf(path)
            if health.errors:
                QMessageBox.warning(self, "PDF", "\n".join(health.errors))
                return
            if health.warnings:
                QMessageBox.information(self, "Hinweis", "\n".join(health.warnings))
            if left:
                self._left_pages = health.page_count
                self.spin_left.blockSignals(True)
                self.spin_left.setMaximum(max(health.page_count, 1))
                self.spin_left.setValue(1)
                self.spin_left.blockSignals(False)
            else:
                self._right_pages = health.page_count
                self.spin_right.blockSignals(True)
                self.spin_right.setMaximum(max(health.page_count, 1))
                self.spin_right.setValue(1)
                self.spin_right.blockSignals(False)
        except Exception as e:
            QMessageBox.critical(self, "PDF", str(e))

    def _render_raw(self, path: str, page_1based: int):
        if not path:
            return None, "Kein PDF"
        try:
            from ild_pdf import PdfDocument

            idx = max(0, page_1based - 1)
            with PdfDocument(path) as doc:
                if idx >= len(doc):
                    return None, "Seite außerhalb"
                pw, ph = doc.page_size(idx)
            scale, warn = clamp_render_scale(pw, ph, self._scale)
            img = render_page(path, idx, scale=scale)
            return img, warn or ""
        except Exception as e:
            return None, f"Fehler:\n{e}"

    def _show_pixmap(self, label: QLabel, img, fallback: str = ""):
        if img is None:
            label.setPixmap(QPixmap())
            label.setText(fallback or "—")
            return
        pm = _pil_to_qpixmap(img)
        label.setPixmap(
            pm.scaled(
                max(label.parent().width() - 24, 200) if label.parent() else 320,
                900,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        label.setText("")

    def _refresh(self, side: str | None = None):
        if self.chk_sync.isChecked() and side == "left":
            self.spin_right.blockSignals(True)
            self.spin_right.setValue(
                min(self.spin_left.value(), max(self.spin_right.maximum(), 1))
            )
            self.spin_right.blockSignals(False)
        elif self.chk_sync.isChecked() and side == "right":
            self.spin_left.blockSignals(True)
            self.spin_left.setValue(
                min(self.spin_right.value(), max(self.spin_left.maximum(), 1))
            )
            self.spin_left.blockSignals(False)

        warn_l = warn_r = ""
        if side in (None, "left") or (
            self.chk_sync.isChecked() and side == "right"
        ):
            self._left_img, warn_l = self._render_raw(
                self._left, self.spin_left.value()
            )
            self._show_pixmap(self.view_left, self._left_img, warn_l or "Kein PDF")
            if warn_l:
                self.view_left.setToolTip(warn_l)
        if side in (None, "right") or (
            self.chk_sync.isChecked() and side == "left"
        ):
            self._right_img, warn_r = self._render_raw(
                self._right, self.spin_right.value()
            )
            self._show_pixmap(
                self.view_right, self._right_img, warn_r or "Kein PDF"
            )
            if warn_r:
                self.view_right.setToolTip(warn_r)

        # Raster-Diff Overlay + Ähnlichkeit — 1.4.0/1.4.1
        self._diff_overlay = None
        if (
            self.chk_diff.isChecked()
            and self._left_img is not None
            and self._right_img is not None
        ):
            try:
                thr = int(self.spin_threshold.value())
                result = raster_diff(
                    self._left_img, self._right_img, threshold=thr
                )
                self._diff_overlay = result.overlay
                self._show_pixmap(self.view_diff, result.overlay, "Diff")
                self.lbl_similarity.setText(
                    f"Ähnlichkeit: {result.similarity_percent:.1f} % "
                    f"({result.different_pixels} / {result.total_pixels} Pixel "
                    f"unterschiedlich, Schwelle {thr}) — 1.4.1"
                )
            except Exception as e:
                self.view_diff.setText(f"Diff-Fehler:\n{e}")
                self.lbl_similarity.setText("Ähnlichkeit: Fehler")
        else:
            self.view_diff.setPixmap(QPixmap())
            self.view_diff.setText(
                "Diff aus" if not self.chk_diff.isChecked() else "—"
            )
            self.lbl_similarity.setText("Ähnlichkeit: —")
