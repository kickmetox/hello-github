"""Umbrechendes Layout für Werkzeugleisten mit vielen Buttons — 2.6.52.

Ein ``QHBoxLayout`` mit ~85 Buttons erzwingt eine Mindestbreite von mehreren
tausend Pixeln. Das ``QMainWindow`` kann dann nicht schmaler als diese Leiste
werden: auf einem 1920-px-Monitor liegt die zentrierte PDF-Seite bei x≈3500 und
ist unsichtbar („weiße Hauptansicht“), Statusleiste und rechte Buttons sind
außerhalb des Bildschirms. ``FlowLayout`` bricht die Buttons stattdessen in
mehrere Zeilen um; die Mindestbreite entspricht nur dem breitesten Einzelbutton.

Portierung des Qt-Beispiels ``flowlayout`` (height-for-width).
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QLayoutItem, QSizePolicy, QStyle, QWidget


class FlowLayout(QLayout):
    """Zeilenumbruch-Layout; versteckte Widgets (``isEmpty()``) werden übersprungen."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        margin: int = -1,
        h_spacing: int = -1,
        v_spacing: int = -1,
        min_wrap_width: int = 640,
        preferred_width: int = 1100,
    ) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._h_space = int(h_spacing)
        self._v_space = int(v_spacing)
        # Qt fragt heightForWidth() auch mit der *Mindest*breite (ein Button) ab
        # und würde daraus eine Fenster-Mindesthöhe von >1500 px ableiten.
        # Unterhalb von min_wrap_width wird daher so umgebrochen, als wäre die
        # Leiste min_wrap_width breit (Überhang wird geclippt statt erzwungen).
        self._min_wrap_width = max(120, int(min_wrap_width))
        self._preferred_width = max(self._min_wrap_width, int(preferred_width))
        if margin >= 0:
            self.setContentsMargins(margin, margin, margin, margin)

    # --- QLayout API -----------------------------------------------------

    def __del__(self) -> None:  # pragma: no cover - Qt ownership cleanup
        try:
            while self.count():
                self.takeAt(0)
        except Exception:
            pass

    def addItem(self, item: QLayoutItem) -> None:  # noqa: N802
        self._items.append(item)

    def addStretch(self, stretch: int = 0) -> None:  # noqa: N802
        """Kompatibilität zu ``QBoxLayout.addStretch`` — im Flow ohne Wirkung."""
        return None

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:  # noqa: N802
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        w = max(int(width), self._min_wrap_width)
        return self._do_layout(QRect(0, 0, w, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:  # noqa: N802
        w = min(self._preferred_width, max(self.single_row_width(), self._min_wrap_width))
        return QSize(w, self.heightForWidth(w))

    def minimumSize(self) -> QSize:  # noqa: N802
        size = QSize()
        for item in self._items:
            if item.isEmpty():
                continue
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def single_row_width(self) -> int:
        """Breite, die alle sichtbaren Items in einer Zeile bräuchten."""
        total = 0
        n = 0
        for item in self._items:
            if item.isEmpty():
                continue
            total += item.sizeHint().width()
            n += 1
        if n > 1:
            total += (n - 1) * max(0, self.horizontal_spacing())
        m = self.contentsMargins()
        return total + m.left() + m.right()

    def row_height(self) -> int:
        """Höhe einer Zeile (höchstes sichtbares Item)."""
        h = 0
        for item in self._items:
            if item.isEmpty():
                continue
            h = max(h, item.sizeHint().height())
        return h

    def height_for_rows(self, rows: int) -> int:
        """Pixelhöhe für ``rows`` Zeilen inkl. Abständen/Rändern (Höhen-Deckel)."""
        rows = max(1, int(rows))
        m = self.contentsMargins()
        vs = max(0, self.vertical_spacing())
        return rows * self.row_height() + (rows - 1) * vs + m.top() + m.bottom()

    # --- helpers ---------------------------------------------------------

    def horizontal_spacing(self) -> int:
        if self._h_space >= 0:
            return self._h_space
        return self._smart_spacing(QStyle.PM_LayoutHorizontalSpacing)

    def vertical_spacing(self) -> int:
        if self._v_space >= 0:
            return self._v_space
        return self._smart_spacing(QStyle.PM_LayoutVerticalSpacing)

    def _smart_spacing(self, pm: QStyle.PixelMetric) -> int:
        parent = self.parent()
        if parent is None:
            return -1
        if isinstance(parent, QWidget):
            return parent.style().pixelMetric(pm, None, parent)
        if isinstance(parent, QLayout):
            return parent.spacing()
        return -1

    def _do_layout(self, rect: QRect, *, test_only: bool) -> int:
        m = self.contentsMargins()
        effective = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x = effective.x()
        y = effective.y()
        line_height = 0
        for item in self._items:
            if item.isEmpty():
                continue
            widget = item.widget()
            space_x = self.horizontal_spacing()
            space_y = self.vertical_spacing()
            if widget is not None:
                style = widget.style()
                if space_x == -1:
                    space_x = style.layoutSpacing(
                        QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal
                    )
                if space_y == -1:
                    space_y = style.layoutSpacing(
                        QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical
                    )
            if space_x < 0:
                space_x = 4
            if space_y < 0:
                space_y = 4
            hint = item.sizeHint()
            next_x = x + hint.width() + space_x
            if next_x - space_x > effective.right() + 1 and line_height > 0:
                x = effective.x()
                y = y + line_height + space_y
                next_x = x + hint.width() + space_x
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y() + m.bottom()
