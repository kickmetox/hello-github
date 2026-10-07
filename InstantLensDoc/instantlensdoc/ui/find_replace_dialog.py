"""Editor: Suchen und Ersetzen."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from instantlensdoc.ui.editor import TextEditor


class FindReplaceDialog(QDialog):
    """Modaler Dialog: Find / Replace / Replace All im Texteditor."""

    def __init__(self, editor: TextEditor, parent=None, *, initial_find: str = ""):
        super().__init__(parent)
        self.editor = editor
        self.setWindowTitle("Suchen und Ersetzen")
        self.setWindowModality(Qt.WindowModal)
        self.resize(420, 180)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.find_edit = QLineEdit(initial_find or editor._last_query or "")
        self.replace_edit = QLineEdit()
        form.addRow("Suchen:", self.find_edit)
        form.addRow("Ersetzen:", self.replace_edit)
        self.case_sensitive = QCheckBox("Groß-/Kleinschreibung beachten")
        form.addRow("", self.case_sensitive)
        layout.addLayout(form)
        self.status = QLabel("")
        layout.addWidget(self.status)

        row = QHBoxLayout()
        btn_find = QPushButton("Weitersuchen")
        btn_find.clicked.connect(self._find_next)
        btn_repl = QPushButton("Ersetzen")
        btn_repl.clicked.connect(self._replace_one)
        btn_all = QPushButton("Alle ersetzen")
        btn_all.clicked.connect(self._replace_all)
        row.addWidget(btn_find)
        row.addWidget(btn_repl)
        row.addWidget(btn_all)
        layout.addLayout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.find_edit.returnPressed.connect(self._find_next)
        self.replace_edit.returnPressed.connect(self._replace_one)

    def _query(self) -> str:
        return self.find_edit.text()

    def _find_next(self) -> bool:
        q = self._query()
        if not q:
            self.status.setText("Suchbegriff eingeben.")
            return False
        ok = self.editor.find_next(
            q, case_sensitive=self.case_sensitive.isChecked()
        )
        self.status.setText("Treffer" if ok else "Kein weiterer Treffer")
        return ok

    def _replace_one(self):
        q = self._query()
        if not q:
            self.status.setText("Suchbegriff eingeben.")
            return
        n = self.editor.replace_one(
            q,
            self.replace_edit.text(),
            case_sensitive=self.case_sensitive.isChecked(),
        )
        if n:
            self.status.setText("Ersetzt")
            self._find_next()
        else:
            self.status.setText("Nichts zu ersetzen — Weitersuchen…")
            self._find_next()

    def _replace_all(self):
        q = self._query()
        if not q:
            self.status.setText("Suchbegriff eingeben.")
            return
        n = self.editor.replace_all(
            q,
            self.replace_edit.text(),
            case_sensitive=self.case_sensitive.isChecked(),
        )
        self.status.setText(f"{n} Ersetzung(en)")
        if n == 0:
            QMessageBox.information(self, "Ersetzen", "Keine Treffer.")
