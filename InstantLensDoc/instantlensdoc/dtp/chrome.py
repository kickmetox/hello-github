"""Scribus-ähnliches DTP-Chrome: Menü, Icon-Leiste, mm-Lineale, Status."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QSize, Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QKeySequence, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMenuBar,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from instantlensdoc.dtp.geometry import (
    mm_to_pt,
    normalize_unit,
)

PASTEBOARD = "#E8E8E8"
RULER_BG = "#F3F3F3"
BLEED_RED = "#E30613"
MARGIN_BLUE = "#1A4DB3"
MENU_TITLES = (
    "Datei",
    "Bearbeiten",
    "Objekt",
    "Einfügen",
    "Seite",
    "Tabelle",
    "Ansicht",
    "Extras",
    "Fenster",
    "Script",
    "Hilfe",
)


def scribus_icon(kind: str, size: int = 18) -> QIcon:
    """Kompakte Werkzeug-Iconfaces, unabhängig vom Desktop-Theme."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(QPen(QColor("#333333"), 1.1))
    k = (kind or "").lower()
    if k == "new":
        p.setBrush(QColor("#ffffff"))
        p.drawRect(3, 2, 11, 14)
        p.drawLine(10, 2, 14, 6)
        p.drawLine(10, 2, 10, 6)
        p.drawLine(10, 6, 14, 6)
    elif k == "save":
        p.setBrush(QColor("#3D7EA6"))
        p.drawRect(2, 3, 14, 12)
        p.setBrush(QColor("#ddd"))
        p.drawRect(5, 3, 8, 5)
        p.setBrush(QColor("#f4d03f"))
        p.drawRect(6, 10, 6, 4)
    elif k == "pdf":
        p.setBrush(QColor("#C0392B"))
        p.drawRoundedRect(2, 2, 14, 14, 2, 2)
        p.setPen(QColor("#fff"))
        p.setFont(QFont("Sans", 6, QFont.Bold))
        p.drawText(pm.rect(), Qt.AlignCenter, "P")
    elif k == "text":
        p.setBrush(Qt.NoBrush)
        p.drawRect(2, 3, 14, 12)
        p.setFont(QFont("Serif", 10, QFont.Bold))
        p.drawText(pm.rect(), Qt.AlignCenter, "T")
    elif k == "image":
        p.setBrush(QColor("#d5e8f5"))
        p.drawRect(2, 3, 14, 12)
        p.setBrush(QColor("#27AE60"))
        p.drawEllipse(4, 5, 4, 4)
        p.drawLine(3, 13, 8, 8)
        p.drawLine(8, 8, 16, 13)
    elif k == "shape":
        p.setBrush(QColor("#AED6F1"))
        p.drawRect(3, 4, 12, 10)
    elif k == "select":
        p.setBrush(QColor("#222"))
        p.drawPolygon(QPolygonF([QPointF(4, 3), QPointF(4, 15), QPointF(8, 12), QPointF(11, 16), QPointF(13, 14), QPointF(10, 11), QPointF(14, 10)]))
    elif k == "link":
        p.drawLine(4, 12, 8, 6)
        p.drawLine(10, 12, 14, 6)
        p.drawEllipse(2, 10, 5, 5)
        p.drawEllipse(11, 3, 5, 5)
    elif k == "align":
        p.drawLine(3, 4, 3, 14)
        p.drawRect(4, 6, 10, 3)
        p.drawRect(4, 11, 7, 3)
    elif k == "weld":
        p.setBrush(QColor("#5DADE2"))
        p.drawRect(3, 5, 8, 8)
        p.setBrush(QColor("#F5B041"))
        p.drawEllipse(7, 4, 8, 8)
    elif k == "zoom-in":
        p.drawEllipse(3, 3, 10, 10)
        p.drawLine(13, 13, 16, 16)
        p.drawLine(6, 8, 10, 8)
        p.drawLine(8, 6, 8, 10)
    elif k == "zoom-out":
        p.drawEllipse(3, 3, 10, 10)
        p.drawLine(13, 13, 16, 16)
        p.drawLine(6, 8, 10, 8)
    elif k == "preflight":
        p.setBrush(QColor("#F4D03F"))
        p.drawEllipse(2, 2, 14, 14)
        p.drawText(pm.rect(), Qt.AlignCenter, "!")
    elif k == "page":
        p.setBrush(QColor("#fff"))
        p.drawRect(4, 2, 10, 14)
        p.drawLine(6, 6, 12, 6)
        p.drawLine(6, 9, 12, 9)
    elif k == "grid":
        for x in (4, 9, 14):
            p.drawLine(x, 3, x, 15)
        for y in (4, 9, 14):
            p.drawLine(3, y, 15, y)
    elif k == "fill":
        p.setBrush(QColor("#E74C3C"))
        p.drawRect(3, 8, 12, 8)
        p.setBrush(QColor("#F4D03F"))
        p.drawEllipse(6, 2, 6, 7)
    elif k == "stroke":
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor("#1A5276"), 2.0))
        p.drawRect(3, 4, 12, 10)
    elif k == "font":
        p.setFont(QFont("Serif", 11, QFont.Bold))
        p.drawText(pm.rect(), Qt.AlignCenter, "A")
    else:
        p.setBrush(QColor("#bbb"))
        p.drawRect(3, 3, 12, 12)
    p.end()
    return QIcon(pm)


class MmRuler(QWidget):
    """Nutzbares Lineal: mm/pt/in, Ziehen setzt Hilfslinie, 0 am Seitenursprung."""

    guideRequested = Signal(str, float)
    guidePreview = Signal(str, float)
    unitChanged = Signal(str)

    def __init__(self, orientation: str, *, thickness: int = 20):
        super().__init__()
        self.setObjectName("dtpHRuler" if orientation == "h" else "dtpVRuler")
        self.orientation = orientation  # h | v
        self._scale = 1.0
        self._origin_px = 40.0
        self._length_pt = 595.0
        self._unit = "mm"
        self._dragging = False
        self.setMouseTracking(True)
        self._refresh_tip()
        if orientation == "h":
            self.setFixedHeight(thickness)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        else:
            self.setFixedWidth(thickness)
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

    def _refresh_tip(self) -> None:
        self.setToolTip(
            f"Lineal ({self._unit}) — Ziehen setzt Hilfslinie, Rechtsklick wechselt mm/pt/in"
        )

    def unit(self) -> str:
        return self._unit

    def set_unit(self, unit: str) -> None:
        u = normalize_unit(unit)
        if u == self._unit:
            return
        self._unit = u
        self._refresh_tip()
        self.update()
        self.unitChanged.emit(u)

    def cycle_unit(self) -> str:
        order = ("mm", "pt", "in")
        nxt = order[(order.index(self._unit) + 1) % len(order)]
        self.set_unit(nxt)
        return nxt

    def set_metrics(self, scale: float, origin_px: float, length_pt: float) -> None:
        self._scale = max(0.05, float(scale))
        self._origin_px = float(origin_px)
        self._length_pt = float(length_pt)
        self.update()

    def _px_to_pt(self, px: float) -> float:
        return (float(px) - self._origin_px) / max(self._scale, 0.01)

    def _event_pt(self, event) -> float:
        if self.orientation == "h":
            return self._px_to_pt(event.position().x())
        return self._px_to_pt(event.position().y())

    def _orientation_name(self) -> str:
        return "vertical" if self.orientation == "h" else "horizontal"

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(RULER_BG))
        p.setPen(QColor("#B0B0B0"))
        if self.orientation == "h":
            p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
        else:
            p.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        p.setPen(QColor("#222"))
        p.setFont(QFont("Sans Serif", 7))
        span = self.width() if self.orientation == "h" else self.height()
        unit = self._unit
        if unit == "in":
            step_pt = 72.0 / 16.0
            px_per = step_pt * self._scale
            if px_per < 0.4:
                p.end()
                return
            lo = int((0 - self._origin_px) / px_per) - 2
            hi = int((span - self._origin_px) / px_per) + 2
            for n in range(lo, hi + 1):
                pos = int(round(self._origin_px + n * px_per))
                if n % 16 == 0:
                    self._tick(p, pos, 12, str(n // 16))
                elif n % 8 == 0:
                    self._tick(p, pos, 9)
                elif n % 4 == 0:
                    self._tick(p, pos, 6)
                else:
                    self._tick(p, pos, 4)
        elif unit == "pt":
            px_per = self._scale
            if px_per < 0.25:
                p.end()
                return
            minor = 10 if px_per < 1.2 else 1
            lo = int((0 - self._origin_px) / px_per) - 2
            hi = int((span - self._origin_px) / px_per) + 2
            for n in range(lo, hi + 1):
                if n % minor:
                    continue
                pos = int(round(self._origin_px + n * px_per))
                if n % 50 == 0:
                    self._tick(p, pos, 12, str(n))
                elif n % 10 == 0:
                    self._tick(p, pos, 8)
                else:
                    self._tick(p, pos, 4)
        else:
            px_per = mm_to_pt(1.0) * self._scale
            if px_per < 0.4:
                p.end()
                return
            lo = int((0 - self._origin_px) / px_per) - 2
            hi = int((span - self._origin_px) / px_per) + 2
            for n in range(lo, hi + 1):
                pos = int(round(self._origin_px + n * px_per))
                if n % 10 == 0:
                    self._tick(p, pos, 12, str(n))
                elif n % 5 == 0:
                    self._tick(p, pos, 8)
                else:
                    self._tick(p, pos, 4)
        p.end()

    def _tick(self, p: QPainter, pos: int, length: int, label: str = "") -> None:
        if self.orientation == "h":
            p.drawLine(pos, self.height() - length, pos, self.height())
            if label:
                p.drawText(pos + 2, 10, label)
        else:
            p.drawLine(self.width() - length, pos, self.width(), pos)
            if label:
                p.save()
                p.translate(9, pos + 11)
                p.rotate(-90)
                p.drawText(0, 0, label)
                p.restore()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.RightButton:
            self.cycle_unit()
            event.accept()
            return
        if event.button() != Qt.LeftButton:
            return
        self._dragging = True
        self.guidePreview.emit(self._orientation_name(), self._event_pt(event))
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if not self._dragging:
            return
        self.guidePreview.emit(self._orientation_name(), self._event_pt(event))
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if not self._dragging or event.button() != Qt.LeftButton:
            return
        self._dragging = False
        self.guideRequested.emit(self._orientation_name(), self._event_pt(event))
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        self.cycle_unit()
        event.accept()


def build_menu_bar(pane: QWidget) -> QMenuBar:
    bar = QMenuBar(pane)
    bar.setObjectName("dtpMenuBar")
    bar.setNativeMenuBar(False)
    m_datei = bar.addMenu("&Datei")
    m_datei.addAction("Neu", pane._chrome_new)
    m_datei.addAction("Grafik importieren…", pane.import_graphic)
    m_datei.addAction("Text importieren…", pane.import_text)
    m_datei.addSeparator()
    m_datei.addAction("Als SLA speichern…", pane.export_sla_dialog)
    m_datei.addAction("PDF exportieren…", pane.export_pdf_dialog)
    m_datei.addAction("PDF/X-3 exportieren…", pane.export_pdfx_dialog)
    m_datei.addAction("Preflight…", pane.run_preflight)
    m_bearb = bar.addMenu("&Bearbeiten")
    m_bearb.addAction("Links ausrichten", lambda: pane.align("left"))
    m_bearb.addAction("Mitte ausrichten", lambda: pane.align("center"))
    m_bearb.addAction("Verteilen", lambda: pane.distribute("h"))
    m_bearb.addSeparator()
    m_bearb.addAction("Füllen…", lambda: pane.apply_fill(dialog=True))
    m_bearb.addAction("Kontur…", lambda: pane.apply_stroke(dialog=True))
    m_bearb.addAction("Schrift…", lambda: pane.apply_font(dialog=True))
    m_obj = bar.addMenu("&Objekt")
    m_obj.addAction("Schweißen", pane.weld_selected)
    m_obj.addAction("Symbol aus Auswahl", pane.symbol_from_selection)
    m_obj.addAction("Envelope Distort", pane.apply_envelope)
    m_obj.addAction("3D-Extrusion", pane.apply_extrude)
    m_obj.addAction("Schnittmaske", pane.apply_clip_mask)
    m_obj.addAction("Text auf Pfad", pane.apply_text_on_path)
    m_obj.addAction("In Pfade umwandeln", pane.convert_to_outlines)
    m_ins = bar.addMenu("&Einfügen")
    m_ins.addAction("Textrahmen", pane.add_text_frame)
    m_ins.addAction("Bildrahmen", pane.add_image_frame)
    m_ins.addAction("Form", pane.add_shape)
    m_ins.addAction("Glyphen…", pane.show_glyph_palette)
    m_ins.addAction("Spalten", pane.make_columns)
    m_seite = bar.addMenu("&Seite")
    m_seite.addAction("Vorherige Seite", pane.prev_page)
    m_seite.addAction("Nächste Seite", pane.next_page)
    m_seite.addAction("Seite hinzufügen", pane.add_page)
    m_tab = bar.addMenu("&Tabelle")
    m_tab.addAction("Textrahmen-Tabelle 2×3", pane.insert_text_table)
    m_ans = bar.addMenu("&Ansicht")
    m_ans.addAction("Raster", pane.toggle_grid)
    m_ans.addAction("Ebenen", pane.toggle_layers)
    m_ans.addAction("Zoom 100 %", lambda: pane.set_zoom(100.0))
    m_ans.addAction("Seite einpassen", pane.zoom_fit)
    m_units = m_ans.addMenu("Linealeinheit")
    m_units.addAction("Millimeter", lambda: pane.set_ruler_unit("mm"))
    m_units.addAction("Punkt (pt)", lambda: pane.set_ruler_unit("pt"))
    m_units.addAction("Zoll (in)", lambda: pane.set_ruler_unit("in"))
    m_ex = bar.addMenu("&Extras")
    m_ex.addAction("Preflight…", pane.run_preflight)
    m_ex.addAction("Live-Füllung", pane.apply_live_fill)
    m_win = bar.addMenu("&Fenster")
    m_win.addAction("Ebenen", pane.toggle_layers)
    m_scr = bar.addMenu("&Script")
    m_scr.addAction("Plugin-Hooks…", pane._chrome_script)
    m_hlp = bar.addMenu("&Hilfe")
    m_hlp.setObjectName("dtpHelpMenu")
    act_help = QAction("Hilfe…", pane)
    act_help.setObjectName("dtpHelpAction")
    act_help.setShortcut(QKeySequence("F1"))
    act_help.setShortcutContext(Qt.WidgetWithChildrenShortcut)
    act_help.setToolTip("DTP-Hilfe: Werkzeuge, Rahmen, Speichern, Tastatur (F1)")
    act_help.triggered.connect(pane._chrome_help)
    m_hlp.addAction(act_help)
    pane.addAction(act_help)
    return bar


def build_icon_bar(pane: QWidget) -> QWidget:
    bar = QWidget()
    bar.setObjectName("dtpIconBar")
    bar.setFixedHeight(28)
    lay = QHBoxLayout(bar)
    lay.setContentsMargins(4, 2, 4, 2)
    lay.setSpacing(1)

    def add_btn(kind: str, slot, tip: str, *, checkable: bool = False) -> QToolButton:
        btn = QToolButton()
        btn.setIcon(scribus_icon(kind))
        btn.setAutoRaise(True)
        btn.setIconSize(QSize(18, 18))
        btn.setFixedSize(24, 24)
        btn.setToolTip(tip)
        btn.setCheckable(checkable)
        btn.clicked.connect(slot)
        lay.addWidget(btn)
        return btn

    add_btn("new", pane._chrome_new, "Neu")
    add_btn("save", pane.export_sla_dialog, "SLA speichern")
    add_btn("pdf", pane.export_pdf_dialog, "PDF")
    sep = QWidget()
    sep.setFixedWidth(6)
    lay.addWidget(sep)
    pane._tool_buttons = {}
    pane._tool_group = QButtonGroup(bar)
    pane._tool_group.setExclusive(True)

    def add_tool(kind: str, name: str, tip: str) -> QToolButton:
        btn = add_btn(kind, lambda _=False, n=name: pane.set_tool(n), tip, checkable=True)
        btn.setObjectName(f"dtpTool_{name}")
        pane._tool_group.addButton(btn)
        pane._tool_buttons[name] = btn
        return btn

    add_tool("select", "select", "Auswählen")
    add_tool("text", "text", "Textrahmen — gilt auf Auswahl")
    add_tool("image", "image", "Bildrahmen — gilt auf Auswahl")
    add_tool("shape", "shape", "Form — gilt auf Auswahl")
    pane._tool_buttons["select"].setChecked(True)
    add_btn("link", pane.link_selected, "Verketten")
    sep2 = QWidget()
    sep2.setFixedWidth(6)
    lay.addWidget(sep2)
    add_btn("fill", lambda: pane.apply_fill(dialog=True), "Füllfarbe auf Auswahl")
    pane._fill_chip = QLabel()
    pane._fill_chip.setObjectName("dtpFillChip")
    pane._fill_chip.setFixedSize(14, 12)
    pane._fill_chip.setToolTip("Aktuelle Füllfarbe")
    pane._fill_chip.setStyleSheet("background:#D0E8FF; border:1px solid #333;")
    pane._fill_chip.mousePressEvent = lambda e: pane.apply_fill(dialog=True)  # type: ignore[method-assign]
    lay.addWidget(pane._fill_chip)
    add_btn("stroke", lambda: pane.apply_stroke(dialog=True), "Kontur auf Auswahl")
    pane._stroke_chip = QLabel()
    pane._stroke_chip.setObjectName("dtpStrokeChip")
    pane._stroke_chip.setFixedSize(14, 12)
    pane._stroke_chip.setToolTip("Aktuelle Konturfarbe")
    pane._stroke_chip.setStyleSheet("background:#1A5276; border:1px solid #333;")
    pane._stroke_chip.mousePressEvent = lambda e: pane.apply_stroke(dialog=True)  # type: ignore[method-assign]
    lay.addWidget(pane._stroke_chip)
    add_btn("font", lambda: pane.apply_font(dialog=True), "Schrift (QFontDialog) auf Auswahl/Caret")
    pane.font_combo.setMaximumHeight(22)
    pane.font_combo.setMaximumWidth(140)
    pane.font_combo.setObjectName("dtpFontCombo")
    pane.font_combo.setToolTip("Systemschriften (Windows: QFontDatabase)")
    lay.addWidget(pane.font_combo)
    add_btn("align", lambda: pane.align("left"), "Ausrichten")
    add_btn("weld", pane.weld_selected, "Schweißen")
    add_btn("grid", pane.toggle_grid, "Raster")
    add_btn("preflight", pane.run_preflight, "Preflight")
    lay.addSpacing(8)
    pane.preset_combo.setMaximumHeight(22)
    pane.preset_combo.setMaximumWidth(100)
    lay.addWidget(pane.preset_combo)
    pane.style_combo.setMaximumHeight(22)
    pane.style_combo.setMaximumWidth(120)
    lay.addWidget(pane.style_combo)
    pane.wrap_combo.setMaximumHeight(22)
    pane.wrap_combo.setMaximumWidth(110)
    lay.addWidget(pane.wrap_combo)
    pane.master_combo.setMaximumHeight(22)
    pane.master_combo.setMaximumWidth(100)
    lay.addWidget(pane.master_combo)
    pane._ink_btn = QToolButton()
    pane._ink_btn.setText("✎")
    pane._ink_btn.setCheckable(True)
    pane._ink_btn.setAutoRaise(True)
    pane._ink_btn.setFixedSize(24, 24)
    pane._ink_btn.setToolTip("Drucksensitiver Stift")
    pane._ink_btn.clicked.connect(pane.toggle_ink)
    lay.addWidget(pane._ink_btn)
    help_btn = QToolButton()
    help_btn.setObjectName("dtpHelpBtn")
    help_btn.setText("?")
    help_btn.setAutoRaise(True)
    help_btn.setFixedSize(24, 24)
    help_btn.setToolTip("Hilfe (F1) — Werkzeuge, Rahmen, Speichern, Tastatur")
    help_btn.clicked.connect(pane._chrome_help)
    lay.addWidget(help_btn)
    lay.addStretch(1)
    return bar


def build_status_bar(pane: QWidget) -> QWidget:
    wrap = QWidget()
    wrap.setObjectName("dtpStatusBar")
    wrap.setFixedHeight(26)
    lay = QHBoxLayout(wrap)
    lay.setContentsMargins(6, 1, 6, 1)
    lay.setSpacing(8)
    pane._info = QLabel("")
    pane._info.setObjectName("dtpInfo")
    lay.addWidget(pane._info, 1)
    pane._coord_label = QLabel("0,0 mm")
    pane._coord_label.setObjectName("dtpCoordLabel")
    pane._coord_label.setFixedWidth(120)
    lay.addWidget(pane._coord_label)
    pane._zoom_label = QLabel("100.00 %")
    pane._zoom_label.setObjectName("dtpZoomLabel")
    pane._zoom_label.setFixedWidth(64)
    lay.addWidget(pane._zoom_label)
    z_out = QToolButton()
    z_out.setIcon(scribus_icon("zoom-out"))
    z_out.setAutoRaise(True)
    z_out.setToolTip("Verkleinern")
    z_out.clicked.connect(lambda: pane.set_zoom(pane._zoom * 0.9))
    z_in = QToolButton()
    z_in.setIcon(scribus_icon("zoom-in"))
    z_in.setAutoRaise(True)
    z_in.setToolTip("Vergrößern")
    z_in.clicked.connect(lambda: pane.set_zoom(pane._zoom * 1.1))
    lay.addWidget(z_out)
    lay.addWidget(z_in)
    prev = QToolButton()
    prev.setText("◀")
    prev.setAutoRaise(True)
    prev.setToolTip("Vorherige Seite")
    prev.clicked.connect(pane.prev_page)
    nxt = QToolButton()
    nxt.setText("▶")
    nxt.setAutoRaise(True)
    nxt.setToolTip("Nächste Seite")
    nxt.clicked.connect(pane.next_page)
    pane._page_label = QLabel("1 von 1")
    pane._page_label.setObjectName("dtpPageLabel")
    lay.addWidget(prev)
    lay.addWidget(pane._page_label)
    lay.addWidget(nxt)
    bg = QToolButton()
    bg.setObjectName("dtpBackgroundBtn")
    bg.setText("  Hintergrund")
    bg.setToolTip("Pasteboard-Farbe")
    bg.setAutoRaise(True)
    bg.setStyleSheet("QToolButton { padding-left: 4px; }")
    chip = QLabel()
    chip.setObjectName("dtpBgChip")
    chip.setFixedSize(14, 12)
    chip.setStyleSheet(f"background:{PASTEBOARD}; border:1px solid #333;")
    pane._bg_chip = chip
    bg.clicked.connect(pane.pick_background)
    inner = QHBoxLayout()
    inner.setContentsMargins(0, 0, 0, 0)
    inner.setSpacing(4)
    holder = QWidget()
    hlay = QHBoxLayout(holder)
    hlay.setContentsMargins(0, 0, 4, 0)
    hlay.setSpacing(4)
    hlay.addWidget(chip)
    hlay.addWidget(QLabel("Hintergrund"))
    holder.mousePressEvent = lambda e: pane.pick_background()  # type: ignore[method-assign]
    lay.addWidget(holder)
    wrap.setStyleSheet(
        f"#dtpStatusBar {{ background:#ECECEC; border-top:1px solid #C4C4C4; }}"
    )
    return wrap
