"""Begrenzter 3D-Extrusions-Viewer — 2.6.27."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc.core.extrude3d import (
    ExtrudeParams,
    SCOPE_DE,
    extrude_faces,
    extrude3d_info,
)


class ExtrudePreview(QWidget):
    """QPainter-Isometrie-Vorschau."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("extrude3dPreview")
        self.setMinimumSize(320, 240)
        self._faces: dict | None = None
        self._color = QColor("#4A90D9")

    def set_faces(self, faces: dict | None, color: str = "#4A90D9") -> None:
        self._faces = faces
        self._color = QColor(color or "#4A90D9")
        self.update()

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#1a1f24"))
        if not self._faces:
            painter.setPen(QColor("#8899aa"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Keine Vorschau")
            painter.end()
            return

        # Bounding box der projizierten Punkte
        pts_all: list[tuple[float, float]] = []
        for key in ("front", "back"):
            pts_all.extend(self._faces.get(key) or [])
        for side in self._faces.get("sides") or []:
            pts_all.extend(side)
        if not pts_all:
            painter.end()
            return
        xs = [p[0] for p in pts_all]
        ys = [p[1] for p in pts_all]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        bw = max(1.0, max_x - min_x)
        bh = max(1.0, max_y - min_y)
        margin = 24.0
        scale = min(
            (self.width() - 2 * margin) / bw,
            (self.height() - 2 * margin) / bh,
        )
        cx = self.width() / 2
        cy = self.height() / 2
        mid_x = (min_x + max_x) / 2
        mid_y = (min_y + max_y) / 2

        def map_pt(p):
            return QPointF(
                cx + (p[0] - mid_x) * scale,
                cy + (p[1] - mid_y) * scale,
            )

        # Seiten (dunkler)
        side_color = QColor(self._color)
        side_color = side_color.darker(140)
        side_color.setAlpha(200)
        painter.setBrush(side_color)
        painter.setPen(QPen(QColor("#0d1114"), 1))
        for side in self._faces.get("sides") or []:
            poly = QPolygonF([map_pt(p) for p in side])
            painter.drawPolygon(poly)

        # Rückseite
        back_c = QColor(self._color).darker(160)
        back_c.setAlpha(160)
        painter.setBrush(back_c)
        painter.drawPolygon(QPolygonF([map_pt(p) for p in self._faces.get("back") or []]))

        # Vorderseite
        front_c = QColor(self._color)
        front_c.setAlpha(230)
        painter.setBrush(front_c)
        painter.setPen(QPen(QColor("#ffffff"), 1.2))
        painter.drawPolygon(QPolygonF([map_pt(p) for p in self._faces.get("front") or []]))
        painter.end()


class Extrude3DDialog(QDialog):
    """Limited 3D Extrusion Viewer mit dokumentiertem Scope."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("extrude3dDialog")
        self.setWindowTitle("3D-Extrusion (begrenzt)")
        self.setModal(True)
        self.resize(560, 420)

        layout = QVBoxLayout(self)
        info = extrude3d_info()
        scope = QLabel(SCOPE_DE)
        scope.setObjectName("extrude3dScope")
        scope.setWordWrap(True)
        scope.setStyleSheet("color:#555;margin-bottom:6px;")
        scope.setToolTip(info.get("message") or SCOPE_DE)
        layout.addWidget(scope)

        badge = QLabel("Limited Viewer · kein Mesh-Import · kein OpenGL")
        badge.setObjectName("extrude3dBadge")
        badge.setStyleSheet(
            "background:#e8f0fe;color:#1a4a8a;border:1px solid #8ab4f8;"
            "border-radius:4px;padding:2px 8px;font-weight:600;"
        )
        layout.addWidget(badge)

        body = QHBoxLayout()
        form = QFormLayout()
        self.shape = QComboBox()
        self.shape.setObjectName("extrude3dShape")
        self.shape.addItem("Rechteck", "rectangle")
        self.shape.addItem("Ellipse", "ellipse")
        self.shape.addItem("Dreieck", "triangle")
        form.addRow("Form", self.shape)

        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(8, 400)
        self.width_spin.setValue(120)
        self.width_spin.setObjectName("extrude3dWidth")
        form.addRow("Breite", self.width_spin)

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(8, 400)
        self.height_spin.setValue(80)
        self.height_spin.setObjectName("extrude3dHeight")
        form.addRow("Höhe", self.height_spin)

        self.depth_spin = QDoubleSpinBox()
        self.depth_spin.setRange(4, 200)
        self.depth_spin.setValue(40)
        self.depth_spin.setObjectName("extrude3dDepth")
        form.addRow("Tiefe", self.depth_spin)

        self.angle_spin = QDoubleSpinBox()
        self.angle_spin.setRange(10, 45)
        self.angle_spin.setValue(30)
        self.angle_spin.setObjectName("extrude3dAngle")
        form.addRow("Winkel °", self.angle_spin)

        left = QWidget()
        left.setLayout(form)
        body.addWidget(left)

        self.preview = ExtrudePreview()
        body.addWidget(self.preview, 1)
        layout.addLayout(body)

        for w in (
            self.shape,
            self.width_spin,
            self.height_spin,
            self.depth_spin,
            self.angle_spin,
        ):
            if hasattr(w, "currentIndexChanged"):
                w.currentIndexChanged.connect(self._refresh)
            if hasattr(w, "valueChanged"):
                w.valueChanged.connect(self._refresh)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        self._refresh()

    def _refresh(self) -> None:
        params = ExtrudeParams(
            shape=str(self.shape.currentData() or "rectangle"),
            width=float(self.width_spin.value()),
            height=float(self.height_spin.value()),
            depth=float(self.depth_spin.value()),
            angle_deg=float(self.angle_spin.value()),
        )
        faces = extrude_faces(params)
        self.preview.set_faces(faces, params.color)
