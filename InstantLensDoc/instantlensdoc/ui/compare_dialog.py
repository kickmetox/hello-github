"""Zwei PDFs Seite-nebeneinander vergleichen + Raster-Diff Overlay — 1.4.5."""

from __future__ import annotations

import html as _html
import re
from datetime import date as _date
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QImage, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
)

from ild_pdf.diff import (
    DIFF_FORMAT_SIDE_BY_SIDE,
    DIFF_FORMAT_UNIFIED,
    export_text_layer_diff_txt,
    raster_diff,
    text_layer_diff,
)
from ild_pdf.limits import clamp_render_scale, inspect_pdf
from ild_pdf.render import render_page
from instantlensdoc.core.app_settings import (
    DEFAULT_TEXTLAYER_DIFF_TXT_TEMPLATE,
    PDF_COMPARE_DIFF_THRESHOLD_MAX,
    PDF_COMPARE_DIFF_THRESHOLD_MIN,
    dialog_start_dir,
    find_invalid_textlayer_diff_txt_placeholders,
    format_textlayer_diff_txt_filename,
    get_last_pdf_diff_png_dir,
    get_pdf_compare_diff_threshold,
    get_pdf_compare_page_sync,
    get_textlayer_diff_side_by_side,
    get_textlayer_diff_txt_template,
    highlight_textlayer_diff_txt_template_html,
    set_last_pdf_diff_png_dir,
    set_pdf_compare_diff_threshold,
    set_pdf_compare_page_sync,
    set_textlayer_diff_side_by_side,
    set_textlayer_diff_txt_template,
)


DIFF_PNG_FILENAME_TEMPLATE = "{stemA}_vs_{stemB}_p{page}.png"
DIFF_TXT_FILENAME_TEMPLATE = DEFAULT_TEXTLAYER_DIFF_TXT_TEMPLATE
DIFF_PNG_KNOWN_PLACEHOLDERS = frozenset({"stemA", "stemB", "page", "date"})
_DIFF_PNG_PLACEHOLDER_RE = re.compile(r"\{(stemA|stemB|page|date)\}")
_DIFF_PNG_ANY_PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")


class DiffPngTemplateEdit(QLineEdit):
    """Diff-PNG-Template: Cursor merken + lokales Undo — 1.4.4."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_cursor = 0
        self._saved_sel_start = -1
        self._saved_sel_len = 0

    def focusOutEvent(self, event):
        self._saved_cursor = self.cursorPosition()
        self._saved_sel_start = self.selectionStart()
        self._saved_sel_len = self.selectionLength()
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Undo):
            if self.isUndoAvailable():
                self.undo()
            event.accept()
            return
        if event.matches(QKeySequence.Redo):
            if self.isRedoAvailable():
                self.redo()
            event.accept()
            return
        super().keyPressEvent(event)

    def restore_insert_position(self) -> None:
        if self.hasFocus():
            return
        if self._saved_sel_start >= 0 and self._saved_sel_len > 0:
            self.setSelection(self._saved_sel_start, self._saved_sel_len)
        else:
            pos = max(0, min(self._saved_cursor, len(self.text())))
            self.setCursorPosition(pos)


def find_invalid_diff_png_placeholders(template: str) -> list[str]:
    """
    Unbekannte ``{…}``-Platzhalter im Diff-PNG-Template (Reihenfolge, unique).
    Bekannt: stemA, stemB, page, date. — 1.4.3/1.4.4
    """
    seen: set[str] = set()
    out: list[str] = []
    for name in _DIFF_PNG_ANY_PLACEHOLDER_RE.findall(str(template or "")):
        key = name.strip()
        if not key or key in DIFF_PNG_KNOWN_PLACEHOLDERS or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def highlight_diff_png_template_html(template: str) -> str:
    """Template als HTML; ungültige Platzhalter rot markiert. — 1.4.3"""
    raw = str(template or "")
    parts: list[str] = []
    last = 0
    for m in _DIFF_PNG_ANY_PLACEHOLDER_RE.finditer(raw):
        parts.append(_html.escape(raw[last : m.start()]))
        name = m.group(1).strip()
        token = _html.escape(m.group(0))
        if name and name not in DIFF_PNG_KNOWN_PLACEHOLDERS:
            parts.append(
                f'<span style="color:#c62828;font-weight:600">{token}</span>'
            )
        else:
            parts.append(token)
        last = m.end()
    parts.append(_html.escape(raw[last:]))
    return "".join(parts) or _html.escape(raw)


def format_diff_png_filename(
    stem_a: str,
    stem_b: str,
    page: int,
    template: str | None = None,
    *,
    date: str | None = None,
) -> str:
    """
    Dateiname aus Template ``{stemA}_vs_{stemB}_p{page}.png``.
    Platzhalter: stemA, stemB, page, date (YYYY-MM-DD).
    Unbekannte bleiben unverändert (Live-Vorschau) — 1.4.2/1.4.3/1.4.4.
    """
    a = (stem_a or "a").strip() or "a"
    b = (stem_b or "b").strip() or "b"
    p = max(1, int(page))
    d = (date or "").strip() or _date.today().isoformat()
    tpl = (template or DIFF_PNG_FILENAME_TEMPLATE).strip() or DIFF_PNG_FILENAME_TEMPLATE
    mapping = {"stemA": a, "stemB": b, "page": str(p), "date": d}

    def _sub(m: re.Match) -> str:
        return mapping.get(m.group(1), m.group(0))

    return _DIFF_PNG_PLACEHOLDER_RE.sub(_sub, tpl)


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
        self._text_diff_result = None  # TextLayerDiffResult — 2.1.0

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
        self.chk_text_diff = QCheckBox("Textlayer-Diff")
        self.chk_text_diff.setChecked(False)
        self.chk_text_diff.setToolTip(
            "Textlayer (pypdfium2) zeilenweise vergleichen — Unified Diff im Diff-Panel — 2.1.0"
        )
        self.chk_text_diff.toggled.connect(lambda _: self._refresh())
        self.chk_ignore_ws = QCheckBox("Ignore-Whitespace")
        self.chk_ignore_ws.setChecked(False)
        self.chk_ignore_ws.setToolTip(
            "Whitespace beim Textlayer-Vergleich ignorieren — 2.1.1"
        )
        self.chk_ignore_ws.toggled.connect(lambda _: self._refresh())
        self.chk_only_diff = QCheckBox("Nur-Unterschiede")
        self.chk_only_diff.setChecked(False)
        self.chk_only_diff.setToolTip(
            "Nur geänderte Zeilen im Unified Diff (ohne Context) — 2.1.1"
        )
        self.chk_only_diff.toggled.connect(lambda _: self._refresh())
        self.chk_side_by_side = QCheckBox("Side-by-Side")
        self.chk_side_by_side.setChecked(get_textlayer_diff_side_by_side())
        self.chk_side_by_side.setToolTip(
            "Textlayer-Diff Side-by-Side statt Unified (Panel + TXT) — 2.1.2"
        )
        self.chk_side_by_side.toggled.connect(self._on_side_by_side_toggled)
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
        btn_export.setToolTip(
            "Diff-Overlay als PNG: Zielordner merken; "
            f"Template {DIFF_PNG_FILENAME_TEMPLATE}; "
            "Quick-Insert {stemA}/{stemB}/{page}/{date}; Reset-Template — 1.4.4"
        )
        btn_export.clicked.connect(self._export_diff_png)
        self.btn_export_diff = btn_export
        btn_export_txt = QPushButton("Diff TXT…")
        btn_export_txt.setToolTip(
            "Textlayer Diff als TXT (Unified/Side-by-Side) · "
            "Dateiname-Template {stemA}_vs_{stemB}_{mode}.txt · "
            "Quick-Insert · Reset Default · Live-Vorschau · "
            "ungültige Platzhalter rot — 2.1.4"
        )
        btn_export_txt.clicked.connect(self._export_text_diff_txt)
        self.btn_export_text_diff = btn_export_txt
        btn_reload = QPushButton("Aktualisieren")
        btn_reload.clicked.connect(lambda: self._refresh())
        nav.addWidget(QLabel("Links Seite"))
        nav.addWidget(self.spin_left)
        nav.addWidget(QLabel("Rechts Seite"))
        nav.addWidget(self.spin_right)
        nav.addWidget(self.chk_sync)
        nav.addWidget(self.chk_diff)
        nav.addWidget(self.chk_text_diff)
        nav.addWidget(self.chk_ignore_ws)
        nav.addWidget(self.chk_only_diff)
        nav.addWidget(self.chk_side_by_side)
        nav.addWidget(QLabel("Schwelle"))
        nav.addWidget(self.spin_threshold)
        nav.addWidget(btn_export)
        nav.addWidget(btn_export_txt)
        nav.addWidget(btn_reload)
        nav.addStretch()
        root.addLayout(nav)

        # Diff-PNG Template: Quick-Insert + Reset; Live-Vorschau — 1.4.3/1.4.4
        tpl_row = QHBoxLayout()
        tpl_row.addWidget(QLabel("PNG-Template"))
        self.png_template_edit = DiffPngTemplateEdit(DIFF_PNG_FILENAME_TEMPLATE)
        self.png_template_edit.setPlaceholderText(DIFF_PNG_FILENAME_TEMPLATE)
        self.png_template_edit.setToolTip(
            "Platzhalter: {stemA}, {stemB}, {page}, {date}. "
            "Quick-Insert an Cursor; lokales Undo (Ctrl+Z); "
            "Reset-Template auf Default — 1.4.4"
        )
        self.png_template_edit.textChanged.connect(self._update_png_template_preview)
        tpl_row.addWidget(self.png_template_edit, 1)
        for token in ("{stemA}", "{stemB}", "{page}", "{date}"):
            btn = QPushButton(token)
            btn.setAutoDefault(False)
            btn.setDefault(False)
            btn.setFocusPolicy(Qt.TabFocus)
            btn.setToolTip(
                f"Platzhalter {token} an Cursor-Position einfügen "
                "(lokales Undo: Ctrl+Z) — 1.4.4"
            )
            btn.clicked.connect(
                lambda _checked=False, t=token: self._insert_png_template_placeholder(t)
            )
            tpl_row.addWidget(btn)
        self.btn_reset_png_tpl = QPushButton("Reset-Template")
        self.btn_reset_png_tpl.setAutoDefault(False)
        self.btn_reset_png_tpl.setDefault(False)
        self.btn_reset_png_tpl.setFocusPolicy(Qt.TabFocus)
        self.btn_reset_png_tpl.setToolTip(
            f"Template auf Default zurücksetzen "
            f"({DIFF_PNG_FILENAME_TEMPLATE}); "
            "Bestätigung nur wenn Feld vom Default abweicht — 1.4.4"
        )
        self.btn_reset_png_tpl.clicked.connect(self._reset_png_template)
        tpl_row.addWidget(self.btn_reset_png_tpl)
        root.addLayout(tpl_row)
        self.png_template_preview = QLabel("")
        self.png_template_preview.setTextFormat(Qt.RichText)
        self.png_template_preview.setWordWrap(True)
        self.png_template_preview.setToolTip(
            "Live-Vorschau Diff-PNG-Dateiname; ungültige Platzhalter rot — 1.4.3/1.4.4"
        )
        root.addWidget(self.png_template_preview)

        # Textlayer Diff-TXT Template — Quick-Insert + Reset Default — 2.1.4
        txt_tpl_row = QHBoxLayout()
        txt_tpl_row.addWidget(QLabel("TXT-Template"))
        self.txt_template_edit = DiffPngTemplateEdit(get_textlayer_diff_txt_template())
        self.txt_template_edit.setPlaceholderText(DIFF_TXT_FILENAME_TEMPLATE)
        self.txt_template_edit.setToolTip(
            "Dateiname-Template für Diff TXT: {stemA}, {stemB}, {mode}, "
            "{page}, {date}. Quick-Insert an Cursor; lokales Undo (Ctrl+Z); "
            "Reset Default (Bestätigung nur bei Abweichung · Fokus+Selektion); "
            "ungültige Platzhalter rot — 2.1.4"
        )
        self.txt_template_edit.textChanged.connect(self._update_txt_template_preview)
        txt_tpl_row.addWidget(self.txt_template_edit, 1)
        for token in ("{stemA}", "{stemB}", "{mode}", "{page}", "{date}"):
            btn = QPushButton(token)
            btn.setAutoDefault(False)
            btn.setDefault(False)
            btn.setFocusPolicy(Qt.TabFocus)
            btn.setToolTip(
                f"Platzhalter {token} an Cursor-Position einfügen "
                "(lokales Undo: Ctrl+Z) — 2.1.4"
            )
            btn.clicked.connect(
                lambda _checked=False, t=token: self._insert_txt_template_placeholder(t)
            )
            txt_tpl_row.addWidget(btn)
        self.btn_reset_txt_tpl = QPushButton("Reset Default")
        self.btn_reset_txt_tpl.setAutoDefault(False)
        self.btn_reset_txt_tpl.setDefault(False)
        self.btn_reset_txt_tpl.setFocusPolicy(Qt.TabFocus)
        self.btn_reset_txt_tpl.setToolTip(
            f"Reset Default ({DIFF_TXT_FILENAME_TEMPLATE}); "
            "Bestätigung nur wenn Feld vom Default abweicht; "
            "danach Fokus+Selektion — 2.1.4"
        )
        self.btn_reset_txt_tpl.clicked.connect(self._reset_txt_template)
        txt_tpl_row.addWidget(self.btn_reset_txt_tpl)
        root.addLayout(txt_tpl_row)
        self.txt_template_preview = QLabel("")
        self.txt_template_preview.setTextFormat(Qt.RichText)
        self.txt_template_preview.setWordWrap(True)
        self.txt_template_preview.setToolTip(
            "Live-Vorschau Diff-TXT-Dateiname; ungültige Platzhalter rot — 2.1.4"
        )
        root.addWidget(self.txt_template_preview)

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
        # Diff-Panel: Raster-Bild oder Textlayer Unified Diff — 2.1.0
        self.diff_text = QPlainTextEdit()
        self.diff_text.setReadOnly(True)
        self.diff_text.setPlaceholderText(
            "Textlayer-Diff (Unified / Side-by-Side) — 2.1.0/2.1.2"
        )
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.Monospace)
        mono.setPointSize(10)
        self.diff_text.setFont(mono)
        self.diff_stack = QStackedWidget()
        sl_diff_img = QScrollArea()
        sl_diff_img.setWidgetResizable(True)
        sl_diff_img.setWidget(self.view_diff)
        self.diff_stack.addWidget(sl_diff_img)  # 0 = Raster
        self.diff_stack.addWidget(self.diff_text)  # 1 = Text
        sl = QScrollArea()
        sr = QScrollArea()
        sl.setWidgetResizable(True)
        sr.setWidgetResizable(True)
        sl.setWidget(self.view_left)
        sr.setWidget(self.view_right)
        panes.addWidget(sl)
        panes.addWidget(sr)
        panes.addWidget(self.diff_stack)
        root.addLayout(panes, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        if self._left:
            self._load_meta(True)
        if self._right:
            self._load_meta(False)
        self._refresh()
        self._update_png_template_preview()
        self._update_txt_template_preview()

    def _on_side_by_side_toggled(self, checked: bool) -> None:
        set_textlayer_diff_side_by_side(bool(checked))
        self._update_txt_template_preview()
        self._refresh()

    def _current_txt_template(self) -> str:
        return (
            self.txt_template_edit.text().strip() or DIFF_TXT_FILENAME_TEMPLATE
        )

    def _txt_mode_token(self) -> str:
        if hasattr(self, "chk_side_by_side") and self.chk_side_by_side.isChecked():
            return "sidebyside"
        return "unified"

    def _insert_txt_template_placeholder(self, token: str) -> None:
        """Quick-Insert Platzhalter an Cursor — 2.1.4."""
        edit = self.txt_template_edit
        if isinstance(edit, DiffPngTemplateEdit):
            edit.restore_insert_position()
        edit.insert(str(token or ""))
        edit.setFocus()
        if isinstance(edit, DiffPngTemplateEdit):
            edit._saved_cursor = edit.cursorPosition()
            edit._saved_sel_start = -1
            edit._saved_sel_len = 0
        set_textlayer_diff_txt_template(self._current_txt_template())
        self._update_txt_template_preview()

    def _focus_txt_template_select_all(self) -> None:
        """Fokus + Selektion ganzer Text (wie PNG/Ann.-Template) — 2.1.4."""
        edit = self.txt_template_edit
        edit.setFocus()
        edit.selectAll()
        if isinstance(edit, DiffPngTemplateEdit):
            edit._saved_cursor = 0
            edit._saved_sel_start = 0
            edit._saved_sel_len = len(edit.text() or "")

    def _reset_txt_template(self) -> None:
        """
        TXT-Template auf Default; Bestätigung nur bei Abweichung;
        danach Live-Vorschau + Fokus mit Selektion — 2.1.4.
        Leer/Whitespace gilt als Default (keine Bestätigung).
        """
        edit = self.txt_template_edit
        default = DIFF_TXT_FILENAME_TEMPLATE
        current = edit.text() or ""
        if current.strip() == "" or current == default:
            if current != default:
                edit.selectAll()
                edit.insert(default)
            set_textlayer_diff_txt_template(default)
            self._update_txt_template_preview()
            QTimer.singleShot(0, self._focus_txt_template_select_all)
            return
        reply = QMessageBox.question(
            self,
            "Reset Default",
            f"Diff-TXT-Template auf Default zurücksetzen?\n\n"
            f"Aktuell: {current}\n"
            f"Default: {default}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            QTimer.singleShot(0, self._focus_txt_template_select_all)
            return
        # selectAll + insert → ein Undo-Schritt (Ctrl+Z)
        edit.selectAll()
        edit.insert(default)
        if isinstance(edit, DiffPngTemplateEdit):
            edit._saved_cursor = edit.cursorPosition()
            edit._saved_sel_start = -1
            edit._saved_sel_len = 0
        set_textlayer_diff_txt_template(default)
        self._update_txt_template_preview()
        QTimer.singleShot(0, self._focus_txt_template_select_all)

    def _update_txt_template_preview(self) -> None:
        stem_a = Path(self._left).stem if self._left else "a"
        stem_b = Path(self._right).stem if self._right else "b"
        page = int(self.spin_left.value()) if hasattr(self, "spin_left") else 1
        tpl = self._current_txt_template()
        mode = self._txt_mode_token()
        name = format_textlayer_diff_txt_filename(
            stem_a, stem_b, template=tpl, page=page, mode=mode
        )
        invalid = find_invalid_textlayer_diff_txt_placeholders(tpl)
        html = highlight_textlayer_diff_txt_template_html(tpl)
        note = f" → <code>{_html.escape(name)}</code>"
        if invalid:
            note += f" · ungültig: {', '.join(invalid)}"
        self.txt_template_preview.setText(f"TXT: {html}{note}")
        set_textlayer_diff_txt_template(tpl)

    def _current_png_template(self) -> str:
        return (
            self.png_template_edit.text().strip() or DIFF_PNG_FILENAME_TEMPLATE
        )

    def _insert_png_template_placeholder(self, token: str) -> None:
        """Quick-Insert {stemA}/{stemB}/{page}/{date} an Cursor — 1.4.4."""
        edit = self.png_template_edit
        if isinstance(edit, DiffPngTemplateEdit):
            edit.restore_insert_position()
        edit.insert(str(token or ""))
        edit.setFocus()
        if isinstance(edit, DiffPngTemplateEdit):
            edit._saved_cursor = edit.cursorPosition()
            edit._saved_sel_start = -1
            edit._saved_sel_len = 0
        self._update_png_template_preview()

    def _focus_png_template_select_all(self) -> None:
        """Fokus + Selektion ganzer Text (wie Ann.-Export-Template) — 1.4.5."""
        edit = self.png_template_edit
        edit.setFocus()
        edit.selectAll()
        if isinstance(edit, DiffPngTemplateEdit):
            edit._saved_cursor = 0
            edit._saved_sel_start = 0
            edit._saved_sel_len = len(edit.text() or "")

    def _reset_png_template(self) -> None:
        """
        Template auf Default; Bestätigung nur bei Abweichung;
        danach Live-Vorschau + Fokus mit Selektion (wie Ann.-Template) — 1.4.5.
        """
        edit = self.png_template_edit
        default = DIFF_PNG_FILENAME_TEMPLATE
        current = edit.text() or ""
        if current == default:
            # Bereits Default — keine Bestätigung; Vorschau + Fokus + Selektion
            self._update_png_template_preview()
            QTimer.singleShot(0, self._focus_png_template_select_all)
            return
        reply = QMessageBox.question(
            self,
            "Reset-Template",
            f"Diff-PNG-Template auf Default zurücksetzen?\n\n"
            f"Aktuell: {current}\n"
            f"Default: {default}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            QTimer.singleShot(0, self._focus_png_template_select_all)
            return
        # selectAll + insert → ein Undo-Schritt (Ctrl+Z stellt vorherigen Text wieder her)
        edit.selectAll()
        edit.insert(default)
        if isinstance(edit, DiffPngTemplateEdit):
            edit._saved_cursor = edit.cursorPosition()
            edit._saved_sel_start = -1
            edit._saved_sel_len = 0
        # Live-Vorschau sofort; Fokus + Selektion ganzer Default-Text — 1.4.5
        self._update_png_template_preview()
        QTimer.singleShot(0, self._focus_png_template_select_all)

    def _update_png_template_preview(self, *_args) -> None:
        """Live-Vorschau Dateiname; ungültige Platzhalter rot — 1.4.3/1.4.4."""
        tpl = self._current_png_template()
        page = int(self.spin_left.value()) if hasattr(self, "spin_left") else 1
        stem_a = Path(self._left).stem if self._left else "a"
        stem_b = Path(self._right).stem if self._right else "b"
        sample = format_diff_png_filename(stem_a, stem_b, page, template=tpl)
        html_tpl = highlight_diff_png_template_html(tpl)
        invalid = find_invalid_diff_png_placeholders(tpl)
        parts = [html_tpl, f"→ {_html.escape(sample)}"]
        if invalid:
            listed = ", ".join(_html.escape("{" + n + "}") for n in invalid)
            parts.append(
                f'<span style="color:#c62828">Ungültige Platzhalter: {listed}</span>'
            )
        self.png_template_preview.setText("<br>".join(parts))

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
        """Diff-PNG: Zielordner merken + editierbares Template — 1.4.2/1.4.3."""
        if self._diff_overlay is None:
            QMessageBox.information(
                self,
                "Diff PNG",
                "Kein Diff-Overlay vorhanden. Raster-Diff aktivieren und PDFs wählen.",
            )
            return
        # Sync: gemeinsame Seite; Entkoppelt: linke Seite als {page}
        page = int(self.spin_left.value())
        if self.chk_sync.isChecked():
            page = int(self.spin_left.value())
        stem_a = Path(self._left).stem if self._left else "a"
        stem_b = Path(self._right).stem if self._right else "b"
        tpl = self._current_png_template()
        invalid = find_invalid_diff_png_placeholders(tpl)
        if invalid:
            listed = ", ".join("{" + n + "}" for n in invalid)
            reply = QMessageBox.warning(
                self,
                "Diff PNG",
                f"Ungültige Platzhalter: {listed}\n"
                "Trotzdem mit diesem Dateinamen speichern?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        fname = format_diff_png_filename(stem_a, stem_b, page, template=tpl)
        start_dir = dialog_start_dir(get_last_pdf_diff_png_dir())
        default = str(Path(start_dir) / fname)
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
            set_last_pdf_diff_png_dir(out.parent)
            QMessageBox.information(
                self, "Diff PNG", f"Gespeichert:\n{out}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Diff PNG", str(e))

    def _export_text_diff_txt(self) -> None:
        """Textlayer Diff als TXT · Template {stemA}_vs_{stemB}_{mode}.txt — 2.1.3."""
        if not self.chk_text_diff.isChecked():
            QMessageBox.information(
                self,
                "Diff TXT",
                "Bitte zuerst „Textlayer-Diff“ aktivieren und aktualisieren.",
            )
            return
        if self._text_diff_result is None:
            self._refresh()
        if self._text_diff_result is None:
            QMessageBox.information(
                self, "Diff TXT", "Kein Textlayer-Diff verfügbar (beide PDFs wählen)."
            )
            return
        stem_a = Path(self._left).stem if self._left else "a"
        stem_b = Path(self._right).stem if self._right else "b"
        page = int(self.spin_left.value())
        start_dir = dialog_start_dir(get_last_pdf_diff_png_dir())
        tpl = self._current_txt_template()
        set_textlayer_diff_txt_template(tpl)
        mode = self._txt_mode_token()
        fname = format_textlayer_diff_txt_filename(
            stem_a, stem_b, template=tpl, page=page, mode=mode
        )
        default = str(Path(start_dir) / fname)
        path, _ = QFileDialog.getSaveFileName(
            self, "Textlayer-Diff als TXT speichern", default, "Text (*.txt);;Alle (*.*)"
        )
        if not path:
            return
        try:
            out = Path(path)
            if out.suffix.lower() != ".txt":
                out = out.with_suffix(".txt")
            fmt = (
                DIFF_FORMAT_SIDE_BY_SIDE
                if self.chk_side_by_side.isChecked()
                else DIFF_FORMAT_UNIFIED
            )
            export_text_layer_diff_txt(
                self._text_diff_result, out, diff_format=fmt
            )
            set_last_pdf_diff_png_dir(out.parent)
            QMessageBox.information(
                self, "Diff TXT", f"Gespeichert ({fmt}):\n{out}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Diff TXT", str(e))

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
        self._update_png_template_preview()

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

        # Textlayer-Diff hat Vorrang im Diff-Panel wenn aktiv — 2.1.0/2.1.1
        self._diff_overlay = None
        self._text_diff_result = None
        if (
            self.chk_text_diff.isChecked()
            and self._left
            and self._right
        ):
            self.diff_stack.setCurrentIndex(1)
            try:
                side = bool(self.chk_side_by_side.isChecked())
                tresult = text_layer_diff(
                    self._left,
                    self._right,
                    left_page=max(0, int(self.spin_left.value()) - 1),
                    right_page=max(0, int(self.spin_right.value()) - 1),
                    ignore_whitespace=bool(self.chk_ignore_ws.isChecked()),
                    only_differences=bool(self.chk_only_diff.isChecked()),
                    diff_format=(
                        DIFF_FORMAT_SIDE_BY_SIDE if side else DIFF_FORMAT_UNIFIED
                    ),
                )
                self._text_diff_result = tresult
                if side:
                    body = (
                        tresult.side_by_side_diff
                        or "(identischer Textlayer — kein Diff)"
                    )
                else:
                    body = tresult.unified_diff or "(identischer Textlayer — kein Diff)"
                self.diff_text.setPlainText(body)
                flags = []
                if tresult.ignore_whitespace:
                    flags.append("Ignore-WS")
                if tresult.only_differences:
                    flags.append("Nur-Diff")
                flags.append("Side-by-Side" if side else "Unified")
                flag_s = f" · {', '.join(flags)}"
                self.lbl_similarity.setText(
                    f"Textlayer-Ähnlichkeit: {tresult.similarity_percent:.1f} % "
                    f"({tresult.left_lines}/{tresult.right_lines} Zeilen, "
                    f"{tresult.changed_hunks} Hunks{flag_s}) — 2.1.2"
                )
            except Exception as e:
                self.diff_text.setPlainText(f"Textlayer-Diff-Fehler:\n{e}")
                self.lbl_similarity.setText("Textlayer: Fehler")
        elif (
            self.chk_diff.isChecked()
            and self._left_img is not None
            and self._right_img is not None
        ):
            self.diff_stack.setCurrentIndex(0)
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
            self.diff_stack.setCurrentIndex(0)
            self.view_diff.setPixmap(QPixmap())
            self.view_diff.setText(
                "Diff aus"
                if not self.chk_diff.isChecked() and not self.chk_text_diff.isChecked()
                else "—"
            )
            self.lbl_similarity.setText("Ähnlichkeit: —")
        self._update_png_template_preview()
        self._update_txt_template_preview()


def _pil_to_qpixmap(img) -> QPixmap:
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    data = img.tobytes("raw", img.mode)
    fmt = QImage.Format_RGBA8888 if img.mode == "RGBA" else QImage.Format_RGB888
    qimg = QImage(data, img.width, img.height, fmt).copy()
    return QPixmap.fromImage(qimg)
