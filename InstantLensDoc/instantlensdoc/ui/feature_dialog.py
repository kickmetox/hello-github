"""Schließbare Funktionsdialoge — kein Stub, keine reine Info-Box."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class FeatureDialog(QDialog):
    """Echter, schließbarer Dialog mit Inhalt (nicht StubInfo / nicht QMessageBox)."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        title: str,
        body: str,
        object_name: str = "ildFeatureDialog",
    ):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(480, 280)
        layout = QVBoxLayout(self)
        lbl = QLabel(body)
        lbl.setObjectName("ildFeatureBody")
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(lbl)
        layout.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close_btn = buttons.button(QDialogButtonBox.Close)
        if close_btn is not None:
            close_btn.setText("Schließen")
        layout.addWidget(buttons)
        esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc.setContext(Qt.WindowShortcut)
        esc.activated.connect(self.reject)


class PathOpenDialog(QDialog):
    """Ordnerpfad anzeigen, optional im Dateimanager öffnen, immer schließbar."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        title: str,
        path,
        object_name: str = "ildPathOpenDialog",
    ):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(520, 180)
        self._path = str(path or "")
        layout = QVBoxLayout(self)
        lbl = QLabel(self._path or "(kein Pfad)")
        lbl.setObjectName("ildPathOpenBody")
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(lbl)
        row = QHBoxLayout()
        row.addStretch(1)
        open_btn = QPushButton("Ordner öffnen")
        open_btn.setObjectName("ildPathOpenButton")
        open_btn.clicked.connect(self._open_folder)
        close_btn = QPushButton("Schließen")
        close_btn.setObjectName("ildPathCloseButton")
        close_btn.clicked.connect(self.reject)
        row.addWidget(open_btn)
        row.addWidget(close_btn)
        layout.addLayout(row)
        esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc.setContext(Qt.WindowShortcut)
        esc.activated.connect(self.reject)

    def _open_folder(self) -> None:
        p = Path(self._path) if self._path else None
        if p is None:
            return
        try:
            p.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))


class SnippetEditDialog(QDialog):
    """Textbaustein anlegen oder überschreiben."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        index: int,
        text: str = "",
    ):
        super().__init__(parent)
        self.setObjectName("ildSnippetEditDialog")
        self.setWindowTitle(f"Textbaustein {int(index) + 1}")
        self.setModal(True)
        self.resize(480, 260)
        layout = QVBoxLayout(self)
        hint = QLabel("Text für diesen Baustein. Speichern übernimmt ihn an den Cursor.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self._edit = QPlainTextEdit()
        self._edit.setPlainText(text or "")
        layout.addWidget(self._edit, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def text(self) -> str:
        return self._edit.toPlainText()


class DetachedDocumentDialog(QDialog):
    """Schließbare Dokumentvorschau (separates Fenster)."""

    def __init__(self, parent: QWidget | None, *, path: str, body: str = ""):
        super().__init__(parent)
        self.setObjectName("ildDetachedDocumentDialog")
        p = Path(path)
        self.setWindowTitle(f"InstantLens Doc — {p.name}")
        self.setModal(True)
        self.resize(720, 520)
        layout = QVBoxLayout(self)
        hint = QLabel(f"<b>{p.name}</b><br>{p}")
        hint.setWordWrap(True)
        hint.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(hint)
        edit = QPlainTextEdit()
        edit.setReadOnly(True)
        edit.setPlainText(body or "(keine Vorschau)")
        layout.addWidget(edit, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close_btn = buttons.button(QDialogButtonBox.Close)
        if close_btn is not None:
            close_btn.setText("Schließen")
        layout.addWidget(buttons)
        esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc.setContext(Qt.WindowShortcut)
        esc.activated.connect(self.reject)
