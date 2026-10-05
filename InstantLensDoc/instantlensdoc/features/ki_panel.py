"""KI-Assistent-Panel (Dock/Dialog)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from instantlensdoc.features.ki_assistant import get_ki_settings, run_ki_action, set_ki_settings


class KiAssistantDialog(QDialog):
    def __init__(self, parent=None, *, selected_text: str = ""):
        super().__init__(parent)
        self.setObjectName("kiAssistantDialog")
        self.setWindowTitle("KI-Assistent")
        self.resize(560, 520)
        layout = QVBoxLayout(self)
        note = QLabel(
            "OpenAI-kompatibler Endpoint (URL + Schlüssel) in den Feldern unten "
            "oder unter Extras → Einstellungen. Ohne Schlüssel: Offline-Modus "
            "(Zusammenfassen/Keywords/Übersetzungsliste)."
        )
        note.setWordWrap(True)
        note.setObjectName("kiDegradedHint")
        layout.addWidget(note)

        cfg = get_ki_settings()
        form = QFormLayout()
        self.endpoint = QLineEdit(cfg["endpoint"])
        self.endpoint.setPlaceholderText("https://api.openai.com/v1")
        self.endpoint.setObjectName("kiEndpoint")
        form.addRow("Endpoint-URL", self.endpoint)
        self.api_key = QLineEdit(cfg["api_key"])
        self.api_key.setEchoMode(QLineEdit.Password)
        self.api_key.setObjectName("kiApiKey")
        form.addRow("API-Schlüssel", self.api_key)
        self.model = QLineEdit(cfg["model"])
        self.model.setObjectName("kiModel")
        form.addRow("Modell", self.model)
        layout.addLayout(form)

        self.input = QPlainTextEdit()
        self.input.setObjectName("kiInput")
        self.input.setPlaceholderText("Ausgewählten Text hier bearbeiten…")
        self.input.setPlainText(selected_text or "")
        layout.addWidget(self.input, 1)

        row = QHBoxLayout()
        self.action = QComboBox()
        self.action.setObjectName("kiAction")
        self.action.addItem("Zusammenfassen", "summarize")
        self.action.addItem("Umformulieren", "rewrite")
        self.action.addItem("Übersetzen (EN)", "translate")
        self.action.addItem("Inhaltsverzeichnis vorschlagen", "toc")
        row.addWidget(self.action)
        run = QPushButton("Ausführen")
        run.setObjectName("kiRunBtn")
        run.clicked.connect(self._run)
        row.addWidget(run)
        layout.addLayout(row)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setObjectName("kiOutput")
        layout.addWidget(self.output, 1)
        self.status = QLabel("")
        self.status.setObjectName("kiStatus")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._sync_degraded()
        self.api_key.textChanged.connect(lambda *_: self._sync_degraded())
        self.endpoint.textChanged.connect(lambda *_: self._sync_degraded())

    def _sync_degraded(self) -> None:
        degraded = not (self.api_key.text().strip() and self.endpoint.text().strip())
        self.status.setText(
            "Offline-Modus: kein Schlüssel/Endpoint — lokale Algorithmen."
            if degraded
            else "Remote-Backend bereit."
        )

    def _run(self) -> None:
        set_ki_settings(
            endpoint=self.endpoint.text(),
            api_key=self.api_key.text(),
            model=self.model.text(),
        )
        res = run_ki_action(
            str(self.action.currentData() or "summarize"),
            self.input.toPlainText(),
        )
        self.output.setPlainText(res.text)
        extra = ""
        if res.extra.get("keywords"):
            extra = " · Keywords: " + ", ".join(res.extra["keywords"])
        self.status.setText((res.message or ("OK · " + res.backend)) + extra)
