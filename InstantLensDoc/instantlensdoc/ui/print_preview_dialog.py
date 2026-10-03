"""Druckvorschau: Tastatur PageUp/Down·Home/End + +/- Zoom — 1.0.9."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QPixmap, QWheelEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
)

from instantlensdoc.core.app_settings import get_print_preview, set_print_preview

# Basis-Anzeigegröße; Zoom skaliert relativ dazu — 1.0.7–1.0.9
_BASE_W = 360
_BASE_H = 480
_ZOOM_MIN = 0.5
_ZOOM_MAX = 3.0
_ZOOM_STEP = 0.25


class PrintPreviewDialog(QDialog):
    """Modaler Dialog: Thumbnail mit Fit-Page, Zoom +/- / Mausrad / Tastatur und Seitenwahl."""

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
        pages: list[int] | None = None,
        pixmap_provider: Callable[[int], QPixmap | None] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Druckvorschau")
        self.setWindowModality(Qt.WindowModal)
        self.resize(480, 580)

        self._pages = list(pages) if pages else [0]
        if not self._pages:
            self._pages = [0]
        self._page_count = max(1, int(page_count or len(self._pages)))
        self._pixmap_provider = pixmap_provider
        self._zoom = 1.0
        self._fit_page = False  # Fit-Page Toggle — 1.0.8
        self._index = 0  # Index in self._pages
        self._cache: dict[int, QPixmap] = {}
        if pixmap is not None and not pixmap.isNull():
            self._cache[self._pages[0]] = pixmap

        layout = QVBoxLayout(self)

        gray_lbl = ", Graustufen" if grayscale else ""
        self._info = QLabel(
            f"Druckvorschau ({page_label})"
            f" — {self._page_count} Seite(n), {dpi} DPI{gray_lbl}"
        )
        self._info.setWordWrap(True)
        layout.addWidget(self._info)

        # Zoom +/- , Fit-Page und ggf. Seitenwahl — 1.0.7–1.0.9
        ctrl = QHBoxLayout()
        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_out.setFixedWidth(32)
        self.btn_zoom_out.setToolTip(
            "Vorschau verkleinern (− / Mausrad) — 1.0.9"
        )
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        ctrl.addWidget(self.btn_zoom_out)
        self.zoom_label = QLabel("100 %")
        self.zoom_label.setMinimumWidth(48)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        self.zoom_label.setToolTip("Aktueller Zoom der Druckvorschau")
        ctrl.addWidget(self.zoom_label)
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedWidth(32)
        self.btn_zoom_in.setToolTip(
            "Vorschau vergrößern (+ / Mausrad) — 1.0.9"
        )
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        ctrl.addWidget(self.btn_zoom_in)
        self.fit_page_check = QCheckBox("Seite einpassen")
        self.fit_page_check.setToolTip(
            "Vorschau an sichtbaren Bereich anpassen (Fit-Page) — 1.0.8"
        )
        self.fit_page_check.toggled.connect(self._on_fit_page_toggled)
        ctrl.addWidget(self.fit_page_check)
        ctrl.addSpacing(16)

        multi = len(self._pages) > 1
        self.page_spin: QSpinBox | None = None
        self.btn_page_prev: QPushButton | None = None
        self.btn_page_next: QPushButton | None = None
        if multi:
            self.btn_page_prev = QPushButton("◀")
            self.btn_page_prev.setFixedWidth(32)
            self.btn_page_prev.setToolTip(
                "Vorherige Druckseite (PageUp) — 1.0.9"
            )
            self.btn_page_prev.clicked.connect(self._page_prev)
            ctrl.addWidget(self.btn_page_prev)
            self.page_spin = QSpinBox()
            self.page_spin.setRange(1, len(self._pages))
            self.page_spin.setValue(1)
            self.page_spin.setPrefix("Seite ")
            self.page_spin.setToolTip(
                "Seite wählen — PageUp/PageDown · Home/End — 1.0.9"
            )
            self.page_spin.valueChanged.connect(self._on_page_spin)
            ctrl.addWidget(self.page_spin)
            self.btn_page_next = QPushButton("▶")
            self.btn_page_next.setFixedWidth(32)
            self.btn_page_next.setToolTip(
                "Nächste Druckseite (PageDown) — 1.0.9"
            )
            self.btn_page_next.clicked.connect(self._page_next)
            ctrl.addWidget(self.btn_page_next)
            self._page_nav_label = QLabel(f"/ {len(self._pages)}")
            ctrl.addWidget(self._page_nav_label)
        ctrl.addStretch(1)
        layout.addLayout(ctrl)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setAlignment(Qt.AlignCenter)
        self._scroll.setToolTip(
            "Mausrad / +/- : Zoom; PageUp/Down · Home/End: Seiten — 1.0.9"
        )
        self._scroll.viewport().installEventFilter(self)
        self._thumb = QLabel()
        self._thumb.setAlignment(Qt.AlignCenter)
        self._thumb.setMinimumSize(200, 260)
        self._thumb.setStyleSheet(
            "QLabel { background: #F5F5F5; border: 1px solid #CCC; }"
        )
        self._scroll.setWidget(self._thumb)
        layout.addWidget(self._scroll, 1)

        if default_preview is None:
            preview_on = bool(get_print_preview())
        else:
            preview_on = bool(default_preview)
        self.preview_check = QCheckBox("Druckvorschau vor dem Drucken anzeigen")
        self.preview_check.setChecked(preview_on)
        self.preview_check.setToolTip(
            "Optional: Vorschau-Dialog vor dem Druckerdialog — Einstellung wird gemerkt — 1.0.9"
        )
        layout.addWidget(self.preview_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Ok).setText("Drucken…")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._refresh_view()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """PageUp/Down·Home/End: Seiten; +/- : Zoom — 1.0.9."""
        key = event.key()
        multi = len(self._pages) > 1
        if multi and key == Qt.Key_PageUp:
            self._page_prev()
            event.accept()
            return
        if multi and key == Qt.Key_PageDown:
            self._page_next()
            event.accept()
            return
        if multi and key == Qt.Key_Home:
            self._page_first()
            event.accept()
            return
        if multi and key == Qt.Key_End:
            self._page_last()
            event.accept()
            return
        if key in (Qt.Key_Plus, Qt.Key_Equal):
            self._zoom_in()
            event.accept()
            return
        if key in (Qt.Key_Minus, Qt.Key_Underscore):
            self._zoom_out()
            event.accept()
            return
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):  # noqa: N802
        """Mausrad über Vorschau → Zoom — 1.0.8."""
        if obj is self._scroll.viewport() and event.type() == QEvent.Type.Wheel:
            assert isinstance(event, QWheelEvent)
            delta = event.angleDelta().y()
            if delta == 0:
                delta = event.pixelDelta().y()
            if delta > 0:
                self._zoom_in()
            elif delta < 0:
                self._zoom_out()
            event.accept()
            return True
        return super().eventFilter(obj, event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._fit_page:
            self._refresh_view()

    def _current_page_index(self) -> int:
        return int(self._pages[self._index])

    def _get_pixmap(self, page_idx: int) -> QPixmap | None:
        cached = self._cache.get(page_idx)
        if cached is not None and not cached.isNull():
            return cached
        if self._pixmap_provider is not None:
            try:
                pm = self._pixmap_provider(page_idx)
            except Exception:
                pm = None
            if pm is not None and not pm.isNull():
                self._cache[page_idx] = pm
                return pm
        return None

    def _fit_target_size(self) -> tuple[int, int]:
        """Zielgröße für Fit-Page (Viewport minus Rand) — 1.0.8."""
        vp = self._scroll.viewport()
        if vp is not None:
            w = max(80, vp.width() - 16)
            h = max(100, vp.height() - 16)
            return w, h
        return _BASE_W, _BASE_H

    def _refresh_view(self) -> None:
        page_idx = self._current_page_index()
        pm = self._get_pixmap(page_idx)
        if self._fit_page:
            tw, th = self._fit_target_size()
            zoom_pct = "Fit"
        else:
            tw = max(80, int(_BASE_W * self._zoom))
            th = max(100, int(_BASE_H * self._zoom))
            zoom_pct = f"{int(round(self._zoom * 100))} %"
        if pm is not None and not pm.isNull():
            scaled = pm.scaled(
                tw,
                th,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self._thumb.setPixmap(scaled)
            self._thumb.setText("")
            self._thumb.setToolTip(
                f"Druckseite {page_idx + 1} — Zoom {zoom_pct} — 1.0.9"
            )
        else:
            self._thumb.clear()
            self._thumb.setText("(keine Vorschau verfügbar)")
            self._thumb.setToolTip("")
        if self._fit_page:
            self.zoom_label.setText("Fit")
            self.btn_zoom_out.setEnabled(True)
            self.btn_zoom_in.setEnabled(True)
        else:
            self.zoom_label.setText(f"{int(round(self._zoom * 100))} %")
            self.btn_zoom_out.setEnabled(self._zoom > _ZOOM_MIN + 1e-6)
            self.btn_zoom_in.setEnabled(self._zoom < _ZOOM_MAX - 1e-6)
        if self.page_spin is not None:
            self.page_spin.blockSignals(True)
            self.page_spin.setValue(self._index + 1)
            self.page_spin.blockSignals(False)
        if self.btn_page_prev is not None:
            self.btn_page_prev.setEnabled(self._index > 0)
        if self.btn_page_next is not None:
            self.btn_page_next.setEnabled(self._index < len(self._pages) - 1)
        # Info-Label aktualisieren
        base = self._info.text().split(" — ", 1)
        suffix = base[1] if len(base) > 1 else ""
        head = f"Druckvorschau (Seite {page_idx + 1})"
        self._info.setText(f"{head} — {suffix}" if suffix else head)

    def _clear_fit_page(self) -> None:
        """Manueller Zoom beendet Fit-Page — 1.0.8."""
        if not self._fit_page:
            return
        self._fit_page = False
        self.fit_page_check.blockSignals(True)
        self.fit_page_check.setChecked(False)
        self.fit_page_check.blockSignals(False)

    def _on_fit_page_toggled(self, checked: bool) -> None:
        self._fit_page = bool(checked)
        if self._fit_page:
            # Zoom-Faktor an Fit-Größe angleichen (für späteren +/-) — 1.0.8
            tw, th = self._fit_target_size()
            self._zoom = max(
                _ZOOM_MIN,
                min(_ZOOM_MAX, round(min(tw / _BASE_W, th / _BASE_H), 2)),
            )
        self._refresh_view()

    def _zoom_in(self) -> None:
        self._clear_fit_page()
        self._zoom = min(_ZOOM_MAX, round(self._zoom + _ZOOM_STEP, 2))
        self._refresh_view()

    def _zoom_out(self) -> None:
        self._clear_fit_page()
        self._zoom = max(_ZOOM_MIN, round(self._zoom - _ZOOM_STEP, 2))
        self._refresh_view()

    def _page_prev(self) -> None:
        if self._index > 0:
            self._index -= 1
            self._refresh_view()

    def _page_next(self) -> None:
        if self._index < len(self._pages) - 1:
            self._index += 1
            self._refresh_view()

    def _page_first(self) -> None:
        """Erste Seite im Druckbereich — 1.0.9."""
        if self._index != 0:
            self._index = 0
            self._refresh_view()

    def _page_last(self) -> None:
        """Letzte Seite im Druckbereich — 1.0.9."""
        last = len(self._pages) - 1
        if last >= 0 and self._index != last:
            self._index = last
            self._refresh_view()

    def _on_page_spin(self, value: int) -> None:
        idx = max(0, min(int(value) - 1, len(self._pages) - 1))
        if idx != self._index:
            self._index = idx
            self._refresh_view()

    def preview_enabled(self) -> bool:
        """Ob Vorschau künftig gezeigt werden soll."""
        return bool(self.preview_check.isChecked())

    def accept(self) -> None:  # noqa: D401
        try:
            set_print_preview(self.preview_enabled())
        except Exception:
            pass
        super().accept()
