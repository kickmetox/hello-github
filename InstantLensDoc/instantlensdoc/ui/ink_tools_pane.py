"""Rechte Werkzeugspalte: Stifte, Pinsel, Farbe, Dicken, Füllungen, Stempel.

Dieselben QActions wie Menü/Ribbon — keine zweiten No-Op-Knöpfe.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc.ui.ink_input import (
    DEFAULT_INK_COLOR,
    DEFAULT_INK_WIDTH,
    FILL_NONE,
    INK_FILL_LABELS,
    INK_FILLS,
    INK_TOOL_LABELS,
    INK_TOOLS,
    INK_WIDTHS,
    STAMP_TOOL_LABELS,
    STAMP_TOOLS,
    TOOL_BALLPOINT,
    mm_to_pt,
    pt_to_mm,
)


def _swatch(color: str, size: int = 16) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    q = QColor(color)
    if not q.isValid():
        q = QColor(DEFAULT_INK_COLOR)
    p.setBrush(q)
    p.setPen(QColor("#333333"))
    p.drawRoundedRect(1, 1, size - 2, size - 2, 3, 3)
    p.end()
    return QIcon(pm)


class InkToolsPane(QWidget):
    """Rechte Spalte analog zur linken Navigation."""

    toolChosen = Signal(str)
    fillChosen = Signal(str)
    colorChosen = Signal(str)
    widthChosen = Signal(float)
    recognizeRequested = Signal()
    stampAction = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ildInkToolsPane")
        self.setMinimumWidth(188)
        self.setMaximumWidth(340)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._window = None
        self._locked = False
        self._width_unit = "pt"
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        head = QLabel("Werkzeuge")
        head.setObjectName("ildInkToolsHead")
        head.setStyleSheet("font-weight:600; padding:8px 10px 4px 10px;")
        root.addWidget(head)
        scroll = QScrollArea()
        scroll.setObjectName("ildInkToolsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        inner.setObjectName("ildInkToolsInner")
        self._col = QVBoxLayout(inner)
        self._col.setContentsMargins(8, 4, 8, 8)
        self._col.setSpacing(6)
        self._add_heading("Stifte")
        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)
        self._tool_btns: dict[str, QToolButton] = {}
        for key in INK_TOOLS:
            btn = QToolButton()
            btn.setObjectName(f"inkTool_{key}")
            btn.setText(INK_TOOL_LABELS[key])
            btn.setCheckable(True)
            btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(lambda _=False, k=key: self.toolChosen.emit(k))
            self._tool_group.addButton(btn)
            self._tool_btns[key] = btn
            self._col.addWidget(btn)
        self._tool_btns[TOOL_BALLPOINT].setChecked(True)
        self._add_heading("Farbe")
        self._color_btn = QPushButton("Farbe…")
        self._color_btn.setObjectName("inkTool_color")
        self._color_btn.clicked.connect(lambda: self.colorChosen.emit(""))
        self._col.addWidget(self._color_btn)
        chips = QHBoxLayout()
        chips.setSpacing(4)
        self._chip_btns: list[QToolButton] = []
        for i in range(8):
            chip = QToolButton()
            chip.setObjectName(f"inkColorChip_{i}")
            chip.setFixedSize(22, 22)
            chip.clicked.connect(lambda _=False, idx=i: self._emit_chip(idx))
            chips.addWidget(chip)
            self._chip_btns.append(chip)
        chips.addStretch(1)
        self._col.addLayout(chips)
        self._recent = [DEFAULT_INK_COLOR, "#C0392B", "#1A5276", "#F1C40F", "#148F77"]
        self._refresh_chips()
        self._add_heading("Dicken")
        unit_row = QHBoxLayout()
        self._unit_pt = QToolButton()
        self._unit_pt.setText("pt")
        self._unit_pt.setCheckable(True)
        self._unit_pt.setChecked(True)
        self._unit_pt.setObjectName("inkWidthUnitPt")
        self._unit_mm = QToolButton()
        self._unit_mm.setText("mm")
        self._unit_mm.setCheckable(True)
        self._unit_mm.setObjectName("inkWidthUnitMm")
        self._unit_pt.clicked.connect(lambda: self._set_unit("pt"))
        self._unit_mm.clicked.connect(lambda: self._set_unit("mm"))
        unit_row.addWidget(self._unit_pt)
        unit_row.addWidget(self._unit_mm)
        unit_row.addStretch(1)
        self._col.addLayout(unit_row)
        self._width_slider = QSlider(Qt.Horizontal)
        self._width_slider.setObjectName("inkWidthSlider")
        self._width_slider.setRange(10, 240)  # 1.0–24.0 pt * 10
        self._width_slider.setValue(int(DEFAULT_INK_WIDTH * 10))
        self._width_slider.valueChanged.connect(self._on_slider)
        self._col.addWidget(self._width_slider)
        self._width_label = QLabel(self._width_text(DEFAULT_INK_WIDTH))
        self._width_label.setObjectName("inkWidthLabel")
        self._col.addWidget(self._width_label)
        presets = QHBoxLayout()
        for w in INK_WIDTHS:
            b = QToolButton()
            b.setText(f"{w:g}")
            b.setObjectName(f"inkWidthPreset_{w:g}")
            b.clicked.connect(lambda _=False, val=w: self.widthChosen.emit(float(val)))
            presets.addWidget(b)
        presets.addStretch(1)
        self._col.addLayout(presets)
        self._add_heading("Füllungen")
        self._fill_group = QButtonGroup(self)
        self._fill_group.setExclusive(True)
        self._fill_btns: dict[str, QToolButton] = {}
        for key in INK_FILLS:
            btn = QToolButton()
            btn.setObjectName(f"inkFill_{key}")
            btn.setText(INK_FILL_LABELS[key])
            btn.setCheckable(True)
            btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(lambda _=False, k=key: self.fillChosen.emit(k))
            self._fill_group.addButton(btn)
            self._fill_btns[key] = btn
            self._col.addWidget(btn)
        self._fill_btns[FILL_NONE].setChecked(True)
        rec = QPushButton("Handschrift erkennen")
        rec.setObjectName("inkTool_recognize")
        rec.clicked.connect(self.recognizeRequested.emit)
        self._col.addWidget(rec)
        self._add_heading("Stempel")
        self._stamp_btns: dict[str, QPushButton] = {}
        for aid in STAMP_TOOLS:
            b = QPushButton(STAMP_TOOL_LABELS[aid])
            b.setObjectName(f"inkStamp_{aid}")
            b.clicked.connect(lambda _=False, k=aid: self.stampAction.emit(k))
            self._stamp_btns[aid] = b
            self._col.addWidget(b)
        self._col.addStretch(1)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)
        self.dtp_host = QWidget()
        self.dtp_host.setObjectName("ildInkToolsDtpHost")
        host_lay = QVBoxLayout(self.dtp_host)
        host_lay.setContentsMargins(0, 0, 0, 0)
        host_lay.setSpacing(0)
        self.dtp_host.hide()
        root.addWidget(self.dtp_host, 1)

    def _add_heading(self, text: str) -> None:
        lab = QLabel(text)
        lab.setStyleSheet("color:#555; font-size:11px; padding-top:6px;")
        self._col.addWidget(lab)

    def _set_unit(self, unit: str) -> None:
        self._width_unit = "mm" if unit == "mm" else "pt"
        self._unit_pt.setChecked(self._width_unit == "pt")
        self._unit_mm.setChecked(self._width_unit == "mm")
        pt = self._width_slider.value() / 10.0
        self._width_label.setText(self._width_text(pt))

    def _width_text(self, pt: float) -> str:
        if self._width_unit == "mm":
            return f"{pt_to_mm(pt):.2f} mm"
        return f"{pt:.1f} pt"

    def _on_slider(self, raw: int) -> None:
        pt = max(1.0, min(24.0, float(raw) / 10.0))
        self._width_label.setText(self._width_text(pt))
        self.widthChosen.emit(pt)

    def _emit_chip(self, idx: int) -> None:
        if 0 <= idx < len(self._recent):
            self.colorChosen.emit(self._recent[idx])

    def _refresh_chips(self) -> None:
        for i, btn in enumerate(self._chip_btns):
            if i < len(self._recent):
                btn.setIcon(_swatch(self._recent[i]))
                btn.setToolTip(self._recent[i])
                btn.setVisible(True)
            else:
                btn.setVisible(False)

    def _hook_action(self, btn, act) -> None:
        if btn is None or act is None:
            return
        try:
            btn.clicked.disconnect()
        except Exception:
            pass
        btn.clicked.connect(act.trigger)

    def bind_window(self, window) -> None:
        """Knöpfe lösen dieselben QActions aus wie Ansicht/Ribbon."""
        self._window = window
        pens = getattr(window, "_ink_pen_actions", None) or {}
        for key, btn in self._tool_btns.items():
            self._hook_action(btn, pens.get(key))
        fills = getattr(window, "_ink_fill_actions", None) or {}
        for key, btn in self._fill_btns.items():
            self._hook_action(btn, fills.get(key))
        self._hook_action(self._color_btn, getattr(window, "_act_ink_color", None))
        rec = self.findChild(QPushButton, "inkTool_recognize")
        self._hook_action(rec, getattr(window, "_act_recognize_handwriting", None))
        stamps = getattr(window, "_ink_stamp_actions", None) or {}
        for key, btn in self._stamp_btns.items():
            self._hook_action(btn, stamps.get(key))
        session = getattr(window, "_ink_session", None)
        if session is not None:
            self.sync_from_session(session)

    def sync_from_session(self, session) -> None:
        tool = getattr(session, "tool", TOOL_BALLPOINT)
        if tool in self._tool_btns:
            self._tool_btns[tool].setChecked(True)
        fill = getattr(session, "fill_mode", FILL_NONE)
        if fill in self._fill_btns:
            self._fill_btns[fill].setChecked(True)
        color = getattr(session, "color", DEFAULT_INK_COLOR)
        self._color_btn.setIcon(_swatch(color))
        rec = list(getattr(session, "recent_colors", None) or [])
        if rec:
            self._recent = rec[:8]
            self._refresh_chips()
        w = float(getattr(session, "width", DEFAULT_INK_WIDTH) or DEFAULT_INK_WIDTH)
        self._width_slider.blockSignals(True)
        self._width_slider.setValue(int(max(10, min(240, round(w * 10)))))
        self._width_slider.blockSignals(False)
        self._width_label.setText(self._width_text(w))
        unit = getattr(session, "width_unit", "pt")
        if unit in ("pt", "mm"):
            self._set_unit(unit)

    def set_locked(self, locked: bool) -> None:
        self._locked = bool(locked)
        enable = not self._locked
        for btn in self.findChildren(QToolButton) + self.findChildren(QPushButton):
            name = btn.objectName() or ""
            if name.startswith("inkWidthUnit"):
                continue
            btn.setEnabled(enable)
        self._width_slider.setEnabled(enable)

    def current_width_pt(self) -> float:
        return self._width_slider.value() / 10.0

    def slider_to_pt(self, displayed: float) -> float:
        if self._width_unit == "mm":
            return mm_to_pt(displayed)
        return float(displayed)
