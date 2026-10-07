"""Formatvorlagen: Gallery, Pane, Anwenden auf QTextDocument, DOCX-Persistenz."""

from __future__ import annotations

import copy
from typing import Any, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

# QTextBlockFormat UserProperty: Style-ID überlebt toHtml als Meta, plus HeadingLevel.
STYLE_ID_PROPERTY = int(QTextFormat.UserProperty) + 61

BUILTIN_STYLES: tuple[dict[str, Any], ...] = (
    {
        "id": "normal",
        "label": "Normal",
        "aliases": ("body", "normal"),
        "size": 11.0,
        "bold": False,
        "italic": False,
        "align": "left",
        "indent": 0.0,
        "space_before": 0.0,
        "space_after": 8.0,
        "heading": 0,
        "color": "",
        "builtin": True,
    },
    {
        "id": "h1",
        "label": "Überschrift 1",
        "aliases": ("h1", "heading1", "überschrift 1"),
        "size": 18.0,
        "bold": True,
        "italic": False,
        "align": "left",
        "indent": 0.0,
        "space_before": 12.0,
        "space_after": 6.0,
        "heading": 1,
        "color": "",
        "builtin": True,
    },
    {
        "id": "h2",
        "label": "Überschrift 2",
        "aliases": ("h2", "heading2", "überschrift 2"),
        "size": 14.0,
        "bold": True,
        "italic": False,
        "align": "left",
        "indent": 0.0,
        "space_before": 10.0,
        "space_after": 4.0,
        "heading": 2,
        "color": "",
        "builtin": True,
    },
    {
        "id": "h3",
        "label": "Überschrift 3",
        "aliases": ("h3", "heading3", "überschrift 3"),
        "size": 12.0,
        "bold": True,
        "italic": True,
        "align": "left",
        "indent": 0.0,
        "space_before": 8.0,
        "space_after": 4.0,
        "heading": 3,
        "color": "",
        "builtin": True,
    },
    {
        "id": "title",
        "label": "Titel",
        "aliases": ("title", "titel"),
        "size": 26.0,
        "bold": True,
        "italic": False,
        "align": "center",
        "indent": 0.0,
        "space_before": 0.0,
        "space_after": 12.0,
        "heading": 1,
        "color": "#0B3D91",
        "builtin": True,
    },
    {
        "id": "quote",
        "label": "Zitat",
        "aliases": ("quote", "zitat"),
        "size": 11.0,
        "bold": False,
        "italic": True,
        "align": "left",
        "indent": 36.0,
        "space_before": 6.0,
        "space_after": 6.0,
        "heading": 0,
        "color": "#4B5563",
        "builtin": True,
    },
    {
        "id": "list",
        "label": "Liste",
        "aliases": ("list", "liste"),
        "size": 11.0,
        "bold": False,
        "italic": False,
        "align": "left",
        "indent": 24.0,
        "space_before": 0.0,
        "space_after": 2.0,
        "heading": 0,
        "color": "",
        "list": True,
        "builtin": True,
    },
)

_ALIGN = {
    "left": Qt.AlignLeft | Qt.AlignAbsolute,
    "center": Qt.AlignHCenter,
    "right": Qt.AlignRight | Qt.AlignAbsolute,
    "justify": Qt.AlignJustify,
}


def _builtin_by_id() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for spec in BUILTIN_STYLES:
        out[str(spec["id"])] = spec
        for alias in spec.get("aliases") or ():
            out[str(alias).strip().lower()] = spec
    return out


def load_custom_styles() -> list[dict[str, Any]]:
    from instantlensdoc.core.app_settings import load_settings

    raw = load_settings().get("custom_paragraph_styles") or []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict) and str(item.get("id") or "").strip():
            row = dict(item)
            row["builtin"] = False
            out.append(row)
    return out


def save_custom_styles(styles: list[dict[str, Any]]) -> None:
    from instantlensdoc.core.app_settings import save_settings

    cleaned: list[dict[str, Any]] = []
    for item in styles or []:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id") or "").strip()
        if not sid or sid in _builtin_by_id():
            continue
        cleaned.append(
            {
                "id": sid,
                "label": str(item.get("label") or sid),
                "size": float(item.get("size") or 11.0),
                "bold": bool(item.get("bold")),
                "italic": bool(item.get("italic")),
                "align": str(item.get("align") or "left"),
                "indent": float(item.get("indent") or 0.0),
                "space_before": float(item.get("space_before") or 0.0),
                "space_after": float(item.get("space_after") or 8.0),
                "heading": int(item.get("heading") or 0),
                "color": str(item.get("color") or ""),
                "builtin": False,
            }
        )
    save_settings({"custom_paragraph_styles": cleaned})


def all_styles() -> list[dict[str, Any]]:
    rows = [copy.deepcopy(s) for s in BUILTIN_STYLES]
    seen = {str(s["id"]) for s in rows}
    for custom in load_custom_styles():
        cid = str(custom.get("id") or "")
        if cid and cid not in seen:
            rows.append(custom)
            seen.add(cid)
    return rows


def resolve_style(style_id: str) -> dict[str, Any]:
    key = (style_id or "normal").strip().lower()
    mapping = _builtin_by_id()
    if key in mapping:
        return dict(mapping[key])
    for custom in load_custom_styles():
        if str(custom.get("id") or "").strip().lower() == key:
            return dict(custom)
        if str(custom.get("label") or "").strip().lower() == key:
            return dict(custom)
    return dict(mapping["normal"])


def apply_style_to_document(
    document: QTextDocument,
    style_id: str,
    *,
    cursor: QTextCursor | None = None,
    empty_means_document: bool = True,
) -> bool:
    """Absatzstil auf Auswahl, sonst ganzes Dokument — mutiert ``QTextDocument``."""
    if document is None:
        return False
    spec = resolve_style(style_id)
    sid = str(spec.get("id") or "normal")
    work = QTextCursor(cursor) if cursor is not None else QTextCursor(document)
    if empty_means_document and not work.hasSelection():
        work.select(QTextCursor.Document)
    char = QTextCharFormat()
    char.setFontPointSize(float(spec.get("size") or 11.0))
    char.setFontWeight(QFont.Bold if spec.get("bold") else QFont.Normal)
    char.setFontItalic(bool(spec.get("italic")))
    color = str(spec.get("color") or "").strip()
    if color:
        qcolor = QColor(color)
        if qcolor.isValid():
            char.setForeground(QBrush(qcolor))
    align = _ALIGN.get(str(spec.get("align") or "left"), Qt.AlignLeft)
    indent = float(spec.get("indent") or 0.0)
    before = float(spec.get("space_before") or 0.0)
    after = float(spec.get("space_after") or 0.0)
    heading = int(spec.get("heading") or 0)
    start = min(work.selectionStart(), work.selectionEnd())
    end = max(work.selectionStart(), work.selectionEnd())
    if end <= start:
        start = 0
        end = max(0, document.characterCount() - 1)
    work.beginEditBlock()
    try:
        block = document.findBlock(start)
        last = document.findBlock(max(start, end - 1) if end > start else start)
        while block.isValid() and block.blockNumber() <= last.blockNumber():
            bcur = QTextCursor(block)
            bcur.select(QTextCursor.BlockUnderCursor)
            bcur.mergeCharFormat(char)
            fmt = QTextBlockFormat(block.blockFormat())
            fmt.setAlignment(align)
            fmt.setLeftMargin(indent)
            fmt.setTopMargin(before)
            fmt.setBottomMargin(after)
            fmt.setProperty(STYLE_ID_PROPERTY, sid)
            try:
                fmt.setHeadingLevel(int(heading))
            except Exception:
                pass
            bcur.mergeBlockFormat(fmt)
            block = block.next()
    finally:
        work.endEditBlock()
    return True


def persist_styles_in_docx(path: str, html: str | None = None) -> None:
    """Word-Absatzstile + benutzerdefinierte Stile in die gespeicherte DOCX schreiben."""
    try:
        from docx import Document as DocxDocument
        from docx.enum.style import WD_STYLE_TYPE
        from docx.shared import Pt, RGBColor
    except ImportError:
        return
    from pathlib import Path

    p = Path(path)
    if not p.is_file():
        return
    try:
        d = DocxDocument(str(p))
    except Exception:
        return
    for spec in load_custom_styles():
        name = str(spec.get("label") or spec.get("id") or "").strip()
        if not name:
            continue
        try:
            try:
                st = d.styles[name]
            except KeyError:
                st = d.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
            font = st.font
            font.size = Pt(float(spec.get("size") or 11.0))
            font.bold = bool(spec.get("bold"))
            font.italic = bool(spec.get("italic"))
            color = str(spec.get("color") or "").lstrip("#")
            if len(color) == 6:
                font.color.rgb = RGBColor.from_string(color.upper())
        except Exception:
            continue
    if html:
        # Heading-Tags sind bereits über html_to_docx gemappt.
        _ = html
    try:
        d.save(str(p))
    except Exception:
        pass


class StyleGallery(QWidget):
    """Kompakte Formatvorlagen-Leiste für das Start-Ribbon."""

    style_chosen = Signal(str)
    pane_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ildStyleGallery")
        row = QHBoxLayout(self)
        row.setContentsMargins(2, 0, 2, 0)
        row.setSpacing(2)
        self._buttons: list[QToolButton] = []
        for spec in BUILTIN_STYLES:
            tb = QToolButton()
            tb.setObjectName(f"styleGallery_{spec['id']}")
            tb.setText(str(spec["label"]))
            tb.setToolTip(f"Formatvorlage: {spec['label']}")
            tb.setAutoRaise(False)
            tb.clicked.connect(lambda _=False, s=str(spec["id"]): self.style_chosen.emit(s))
            row.addWidget(tb)
            self._buttons.append(tb)
        more = QToolButton()
        more.setObjectName("styleGalleryMore")
        more.setText("Formatvorlagen…")
        more.setToolTip("Formatvorlagen-Bereich öffnen")
        more.clicked.connect(self.pane_requested.emit)
        row.addWidget(more)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)


class StylePane(QWidget):
    """Formatvorlagen-Bereich: anwenden, anlegen, ändern, löschen."""

    style_chosen = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        on_apply: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ildStylePane")
        self._on_apply = on_apply
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        title = QLabel("Formatvorlagen")
        title.setStyleSheet("font-weight: 600;")
        root.addWidget(title)
        self.list = QListWidget()
        self.list.setObjectName("stylePaneList")
        self.list.itemDoubleClicked.connect(self._apply_current)
        root.addWidget(self.list, 1)
        btns = QHBoxLayout()
        self.btn_apply = QPushButton("Übernehmen")
        self.btn_apply.setObjectName("stylePaneApply")
        self.btn_apply.clicked.connect(self._apply_current)
        self.btn_new = QPushButton("Neu…")
        self.btn_new.clicked.connect(self._create)
        self.btn_edit = QPushButton("Ändern…")
        self.btn_edit.clicked.connect(self._modify)
        self.btn_del = QPushButton("Löschen")
        self.btn_del.clicked.connect(self._delete)
        for b in (self.btn_apply, self.btn_new, self.btn_edit, self.btn_del):
            btns.addWidget(b)
        root.addLayout(btns)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        for spec in all_styles():
            item = QListWidgetItem(str(spec.get("label") or spec.get("id")))
            item.setData(Qt.UserRole, str(spec.get("id")))
            if spec.get("builtin"):
                item.setToolTip("Integrierte Formatvorlage")
            else:
                item.setToolTip("Benutzerdefinierte Formatvorlage")
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    def current_id(self) -> str:
        item = self.list.currentItem()
        if item is None:
            return ""
        return str(item.data(Qt.UserRole) or "")

    def _apply_current(self, *_args) -> None:
        sid = self.current_id()
        if not sid:
            return
        if self._on_apply is not None:
            self._on_apply(sid)
        self.style_chosen.emit(sid)

    def _create(self) -> None:
        name, ok = QInputDialog.getText(self, "Formatvorlage", "Name:")
        if not ok or not str(name).strip():
            return
        sid = str(name).strip()
        key = sid.lower().replace(" ", "_")
        customs = load_custom_styles()
        if any(str(c.get("id")) == key for c in customs) or key in _builtin_by_id():
            QMessageBox.information(self, "Formatvorlage", "Dieser Name existiert bereits.")
            return
        size, ok = QInputDialog.getDouble(self, "Formatvorlage", "Schriftgröße (pt):", 12.0, 6.0, 72.0, 1)
        if not ok:
            return
        customs.append(
            {
                "id": key,
                "label": sid,
                "size": float(size),
                "bold": False,
                "italic": False,
                "align": "left",
                "indent": 0.0,
                "space_before": 0.0,
                "space_after": 8.0,
                "heading": 0,
                "color": "",
            }
        )
        save_custom_styles(customs)
        self.refresh()

    def _modify(self) -> None:
        sid = self.current_id()
        spec = resolve_style(sid)
        if spec.get("builtin"):
            QMessageBox.information(
                self, "Formatvorlage", "Integrierte Vorlagen können nicht geändert werden."
            )
            return
        size, ok = QInputDialog.getDouble(
            self,
            "Formatvorlage ändern",
            "Schriftgröße (pt):",
            float(spec.get("size") or 11.0),
            6.0,
            72.0,
            1,
        )
        if not ok:
            return
        customs = load_custom_styles()
        for row in customs:
            if str(row.get("id")) == sid:
                row["size"] = float(size)
                break
        save_custom_styles(customs)
        self.refresh()

    def _delete(self) -> None:
        sid = self.current_id()
        spec = resolve_style(sid)
        if spec.get("builtin"):
            QMessageBox.information(
                self, "Formatvorlage", "Integrierte Vorlagen können nicht gelöscht werden."
            )
            return
        customs = [c for c in load_custom_styles() if str(c.get("id")) != sid]
        save_custom_styles(customs)
        self.refresh()
