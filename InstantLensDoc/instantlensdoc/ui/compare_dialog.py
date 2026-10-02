"""Zwei PDFs Seite-nebeneinander vergleichen."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
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
    QWidget,
)

from ild_pdf.limits import clamp_render_scale, inspect_pdf
from ild_pdf.render import render_page


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
        self.setWindowTitle("PDF vergleichen (Seite neben Seite)")
        self.resize(1000, 700)
        self._left = left_pdf or ""
        self._right = right_pdf or ""
        self._left_pages = 0
        self._right_pages = 0
        self._scale = 1.0

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
        self.chk_sync = QPushButton("Seiten synchron")
        self.chk_sync.setCheckable(True)
        self.chk_sync.setChecked(True)
        btn_reload = QPushButton("Aktualisieren")
        btn_reload.clicked.connect(lambda: self._refresh())
        nav.addWidget(QLabel("Links Seite"))
        nav.addWidget(self.spin_left)
        nav.addWidget(QLabel("Rechts Seite"))
        nav.addWidget(self.spin_right)
        nav.addWidget(self.chk_sync)
        nav.addWidget(btn_reload)
        nav.addStretch()
        root.addLayout(nav)

        panes = QHBoxLayout()
        self.view_left = QLabel(alignment=Qt.AlignCenter)
        self.view_right = QLabel(alignment=Qt.AlignCenter)
        self.view_left.setText("Kein PDF")
        self.view_right.setText("Kein PDF")
        self.view_left.setMinimumSize(400, 500)
        self.view_right.setMinimumSize(400, 500)
        sl = QScrollArea()
        sr = QScrollArea()
        sl.setWidgetResizable(True)
        sr.setWidgetResizable(True)
        sl.setWidget(self.view_left)
        sr.setWidget(self.view_right)
        panes.addWidget(sl)
        panes.addWidget(sr)
        root.addLayout(panes, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        if self._left:
            self._load_meta(True)
        if self._right:
            self._load_meta(False)
        self._refresh()

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

    def _render_into(self, path: str, page_1based: int, label: QLabel):
        if not path:
            label.setText("Kein PDF")
            return
        try:
            from ild_pdf import PdfDocument

            idx = max(0, page_1based - 1)
            with PdfDocument(path) as doc:
                if idx >= len(doc):
                    label.setText("Seite außerhalb")
                    return
                pw, ph = doc.page_size(idx)
            scale, warn = clamp_render_scale(pw, ph, self._scale)
            img = render_page(path, idx, scale=scale)
            pm = _pil_to_qpixmap(img)
            # In Scroll-Viewport einpassen (Anzeige)
            label.setPixmap(
                pm.scaled(
                    max(label.parent().width() - 24, 200) if label.parent() else 450,
                    900,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
            if warn:
                label.setToolTip(warn)
        except Exception as e:
            label.setText(f"Fehler:\n{e}")

    def _refresh(self, side: str | None = None):
        if self.chk_sync.isChecked() and side == "left":
            self.spin_right.blockSignals(True)
            self.spin_right.setValue(min(self.spin_left.value(), max(self.spin_right.maximum(), 1)))
            self.spin_right.blockSignals(False)
        elif self.chk_sync.isChecked() and side == "right":
            self.spin_left.blockSignals(True)
            self.spin_left.setValue(min(self.spin_right.value(), max(self.spin_left.maximum(), 1)))
            self.spin_left.blockSignals(False)

        if side in (None, "left"):
            self._render_into(self._left, self.spin_left.value(), self.view_left)
        if side in (None, "right"):
            self._render_into(self._right, self.spin_right.value(), self.view_right)
