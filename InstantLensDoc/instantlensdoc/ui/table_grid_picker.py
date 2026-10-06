"""Word-ähnlicher Tabellen-Rasterwähler (Zeilen × Spalten)."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class TableGridPicker(QWidget):
    """Raster 8×8; Hover zeigt Größe, Klick emittiert (rows, cols)."""

    picked = Signal(int, int)

    def __init__(self, parent=None, *, max_rows: int = 8, max_cols: int = 8):
        super().__init__(parent)
        self.setObjectName("ildTableGridPicker")
        self._max_rows = max(1, int(max_rows))
        self._max_cols = max(1, int(max_cols))
        self._hover = (0, 0)
        self.setMouseTracking(True)
        self.setFixedSize(8 + self._max_cols * 18, 28 + self._max_rows * 18)
        self._label = QLabel("Tabelle einfügen", self)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setGeometry(0, self.height() - 20, self.width(), 18)

    def sizeHint(self):  # noqa: N802
        return self.size()

    def mouseMoveEvent(self, event):  # noqa: N802
        c = max(1, min(self._max_cols, int(event.position().x() // 18) + 1))
        r = max(1, min(self._max_rows, int(event.position().y() // 18) + 1))
        self._hover = (r, c)
        self._label.setText(f"{r} × {c} Tabelle")
        self.update()

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            r, c = self._hover
            if r > 0 and c > 0:
                self.picked.emit(r, c)

    def leaveEvent(self, event):  # noqa: N802
        self._hover = (0, 0)
        self._label.setText("Tabelle einfügen")
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#F8FAFC"))
        hr, hc = self._hover
        for r in range(self._max_rows):
            for c in range(self._max_cols):
                x = 4 + c * 18
                y = 4 + r * 18
                if r < hr and c < hc:
                    p.fillRect(x, y, 16, 16, QColor("#D9E6F8"))
                    p.setPen(QColor("#3B6DB5"))
                else:
                    p.fillRect(x, y, 16, 16, QColor("#FFFFFF"))
                    p.setPen(QColor("#C5CCD6"))
                p.drawRect(x, y, 15, 15)
        p.end()


class TableGridPopup(QWidget):
    """Popup-Host für den Rasterwähler."""

    picked = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setObjectName("ildTableGridPopup")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        self.picker = TableGridPicker(self)
        self.picker.picked.connect(self._on_pick)
        lay.addWidget(self.picker)

    def _on_pick(self, rows: int, cols: int) -> None:
        self.picked.emit(rows, cols)
        self.hide()

    def popup_at(self, global_pos: QPoint) -> None:
        self.move(global_pos)
        self.show()
        self.raise_()
        self.activateWindow()


class TableGridDialog(QDialog):
    """QDialog mit Rasterwähler — Ribbon und Pulldown teilen dieselbe QAction."""

    picked = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tabelle einfügen")
        self.setObjectName("ildTableGridDialog")
        self._rows = 0
        self._cols = 0
        lay = QVBoxLayout(self)
        self.picker = TableGridPicker(self)
        self.picker.picked.connect(self._on_pick)
        lay.addWidget(self.picker)
        btns = QDialogButtonBox()
        custom = QPushButton("Benutzerdefiniert…")
        custom.setObjectName("ildTableGridCustom")
        custom.clicked.connect(self._custom)
        btns.addButton(custom, QDialogButtonBox.ActionRole)
        btns.addButton(QDialogButtonBox.Cancel)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def chosen(self) -> tuple[int, int]:
        return self._rows, self._cols

    def _on_pick(self, rows: int, cols: int) -> None:
        self._rows, self._cols = int(rows), int(cols)
        self.picked.emit(self._rows, self._cols)
        self.accept()

    def _custom(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        rows, ok = QInputDialog.getInt(self, "Tabelle", "Zeilen:", 3, 1, 200)
        if not ok:
            return
        cols, ok = QInputDialog.getInt(self, "Tabelle", "Spalten:", 3, 1, 50)
        if not ok:
            return
        self._on_pick(rows, cols)
