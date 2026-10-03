"""Druckvorschau: erste Seite als Thumbnail vor dem Druckjob — 1.0.6."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
)

from instantlensdoc.core.app_settings import get_print_preview, set_print_preview


class PrintPreviewDialog(QDialog):
    """Modaler Dialog: Thumbnail der ersten Druckseite + optionaler Toggle."""

    def __init__(
        self,
        pixmap: QPixmap | None,
        *,
        page_label: str = "Seite 1",
        page_count: int = 1,
        dpi: int = 150,
        grayscale: bool = False,
        parent=None,
        default_preview: bool | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Druckvorschau")
        self.setWindowModality(Qt.WindowModal)
        self.resize(420, 520)
        layout = QVBoxLayout(self)

        gray_lbl = ", Graustufen" if grayscale else ""
        info = QLabel(
            f"Vorschau der ersten Druckseite ({page_label})"
            f" — {page_count} Seite(n), {dpi} DPI{gray_lbl}"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignCenter)
        thumb = QLabel()
        thumb.setAlignment(Qt.AlignCenter)
        thumb.setMinimumSize(200, 260)
        thumb.setStyleSheet(
            "QLabel { background: #F5F5F5; border: 1px solid #CCC; }"
        )
        if pixmap is not None and not pixmap.isNull():
            scaled = pixmap.scaled(
                360,
                480,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            thumb.setPixmap(scaled)
            thumb.setToolTip("Erste Seite des gewählten Druckbereichs — 1.0.6")
        else:
            thumb.setText("(keine Vorschau verfügbar)")
        scroll.setWidget(thumb)
        layout.addWidget(scroll, 1)

        if default_preview is None:
            preview_on = bool(get_print_preview())
        else:
            preview_on = bool(default_preview)
        self.preview_check = QCheckBox("Druckvorschau vor dem Drucken anzeigen")
        self.preview_check.setChecked(preview_on)
        self.preview_check.setToolTip(
            "Optional: Vorschau-Dialog vor dem Druckerdialog — Einstellung wird gemerkt — 1.0.6"
        )
        layout.addWidget(self.preview_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Ok).setText("Drucken…")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def preview_enabled(self) -> bool:
        """Ob Vorschau künftig gezeigt werden soll."""
        return bool(self.preview_check.isChecked())

    def accept(self) -> None:  # noqa: D401
        try:
            set_print_preview(self.preview_enabled())
        except Exception:
            pass
        super().accept()
