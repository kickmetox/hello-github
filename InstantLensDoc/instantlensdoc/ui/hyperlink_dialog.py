"""Hyperlink einfügen/bearbeiten — URL oder Dokumentziel — 2.6.27. — 2.6.28."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from instantlensdoc.core.hyperlinks import (
    classify_target,
    list_heading_anchors,
    make_markdown_link,
    validate_hyperlink,
)


class HyperlinkDialog(QDialog):
    """Modal: Linktext + Ziel (URL / Anker / Zeile / Überschrift)."""

    def __init__(
        self,
        parent=None,
        *,
        initial_text: str = "",
        initial_target: str = "",
        document_text: str = "",
    ):
        super().__init__(parent)
        self.setWindowTitle("Hyperlink")
        self.setObjectName("hyperlinkDialog")
        self.setWindowModality(Qt.WindowModal)
        self.resize(460, 220)
        self._doc = document_text or ""
        self.result_snippet = ""
        self.result_target = ""
        self.result_text = ""

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.text_edit = QLineEdit(initial_text)
        self.text_edit.setObjectName("hyperlinkText")
        self.target_edit = QLineEdit(initial_target or "https://")
        self.target_edit.setObjectName("hyperlinkTarget")
        self.kind_combo = QComboBox()
        self.kind_combo.setObjectName("hyperlinkKind")
        self.kind_combo.addItem("Web-URL (http/https)", "url")
        self.kind_combo.addItem("Anker (#slug)", "anchor")
        self.kind_combo.addItem("Überschrift", "heading")
        self.kind_combo.addItem("Zeile (ild://line/N)", "line")
        form.addRow("Linktext:", self.text_edit)
        form.addRow("Ziel:", self.target_edit)
        form.addRow("Art:", self.kind_combo)
        layout.addLayout(form)

        self.anchor_combo = QComboBox()
        self.anchor_combo.setObjectName("hyperlinkAnchorPick")
        self.anchor_combo.addItem("— Überschrift wählen —", "")
        for h in list_heading_anchors(self._doc):
            self.anchor_combo.addItem(
                f"H{h['level']}: {h['title']}", h["anchor"]
            )
        self.anchor_combo.currentIndexChanged.connect(self._pick_anchor)
        layout.addWidget(QLabel("Schnellwahl Überschrift:"))
        layout.addWidget(self.anchor_combo)

        self.hint = QLabel(
            "Markdown: [Text](https://…) · Intern: #anker oder ild://line/12"
        )
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if initial_target:
            k = classify_target(initial_target)
            idx = self.kind_combo.findData(k)
            if idx >= 0:
                self.kind_combo.setCurrentIndex(idx)

    def _pick_anchor(self, _i: int = 0) -> None:
        val = self.anchor_combo.currentData()
        if val:
            self.target_edit.setText(str(val))
            idx = self.kind_combo.findData("anchor")
            if idx >= 0:
                self.kind_combo.setCurrentIndex(idx)

    def _accept(self) -> None:
        label = self.text_edit.text().strip()
        target = self.target_edit.text().strip()
        kind = self.kind_combo.currentData() or "url"
        if kind == "line" and not target.lower().startswith("ild://line/"):
            if target.isdigit():
                target = f"ild://line/{target}"
        if kind == "anchor" and target and not target.startswith("#") and "://" not in target:
            target = "#" + target.lstrip("#")
        if kind == "heading" and target and not target.lower().startswith("ild://"):
            if not target.startswith("#"):
                target = f"ild://heading/{target}"
        ok, norm, _k, err = validate_hyperlink(label, target)
        if not ok:
            QMessageBox.warning(self, "Hyperlink", err)
            return
        try:
            self.result_snippet = make_markdown_link(label, norm)
        except ValueError as e:
            QMessageBox.warning(self, "Hyperlink", str(e))
            return
        self.result_text = label
        self.result_target = norm
        self.accept()
