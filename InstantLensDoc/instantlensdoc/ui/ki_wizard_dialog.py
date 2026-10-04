"""Geführter KI-Dokument-Wizard (isoliert, kein freier Chat) — 2.6.16."""

from __future__ import annotations

from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc.core.ki_wizards import (
    COMPANY_FIELD_KEYS,
    COMPANY_FIELD_LABELS,
    WIZARD_KINDS,
    generate_ki_document,
    llm_hook_available,
    wizard_field_specs,
)


class KiDocumentWizardDialog(QDialog):
    """Wizard: Typ wählen → Felder → generieren → editierbares Dokument."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("kiDocumentWizardDialog")
        self.setWindowTitle("Dokument erstellen… (KI-Wizard)")
        self.setModal(True)
        self.resize(640, 620)
        self._result_doc = None
        self._field_edits: dict[str, QLineEdit | QPlainTextEdit] = {}
        self._company_edits: dict[str, QLineEdit] = {}

        root = QVBoxLayout(self)

        intro = QLabel(
            "Geführte Standardabläufe — <b>kein</b> freier KI-Chat. "
            "Ausgabe als editierbares InstantLens-Doc / Word-Suite-Dokument."
        )
        intro.setObjectName("kiWizardIntro")
        intro.setWordWrap(True)
        root.addWidget(intro)

        form_top = QFormLayout()
        self.kind_combo = QComboBox()
        self.kind_combo.setObjectName("kiWizardKind")
        for kid, label in WIZARD_KINDS.items():
            self.kind_combo.addItem(label, kid)
        self.kind_combo.currentIndexChanged.connect(self._rebuild_fields)
        form_top.addRow("Dokumenttyp", self.kind_combo)

        self.title_edit = QLineEdit()
        self.title_edit.setObjectName("kiWizardTitle")
        self.title_edit.setPlaceholderText("Optionaler Dokumenttitel")
        form_top.addRow("Titel (optional)", self.title_edit)
        root.addLayout(form_top)

        self.company_cb = QCheckBox("Unternehmensbezogen (Firma, Adresse, USt-Id …)")
        self.company_cb.setObjectName("kiWizardCompanyMode")
        self.company_cb.toggled.connect(self._toggle_company)
        root.addWidget(self.company_cb)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("kiWizardScroll")
        host = QWidget()
        self._fields_host = QVBoxLayout(host)

        self.fields_box = QGroupBox("Angaben")
        self.fields_box.setObjectName("kiWizardFields")
        self.fields_form = QFormLayout(self.fields_box)
        self._fields_host.addWidget(self.fields_box)

        self.company_box = QGroupBox("Unternehmen")
        self.company_box.setObjectName("kiWizardCompany")
        self.company_form = QFormLayout(self.company_box)
        for key in COMPANY_FIELD_KEYS:
            edit = QLineEdit()
            edit.setObjectName(f"kiWizardCompany_{key}")
            edit.setPlaceholderText(COMPANY_FIELD_LABELS[key])
            self._company_edits[key] = edit
            self.company_form.addRow(COMPANY_FIELD_LABELS[key], edit)
        self.company_box.setVisible(False)
        self._fields_host.addWidget(self.company_box)
        self._fields_host.addStretch(1)
        scroll.setWidget(host)
        root.addWidget(scroll, 1)

        llm_row = QHBoxLayout()
        self.llm_cb = QCheckBox("Optionalen LLM-Hook nutzen (nur Wizard)")
        self.llm_cb.setObjectName("kiWizardUseLlm")
        available = llm_hook_available()
        self.llm_cb.setEnabled(available)
        self.llm_cb.setChecked(False)
        if not available:
            self.llm_cb.setToolTip(
                "Kein LLM-Hook registriert — lokale Template-Generierung. "
                "Hook: instantlensdoc.core.ki_wizards.register_llm_hook"
            )
        else:
            self.llm_cb.setToolTip("LLM-Hook registriert — Ausgabe bleibt Wizard-isoliert.")
        llm_row.addWidget(self.llm_cb)
        llm_row.addStretch(1)
        root.addLayout(llm_row)

        self.preview = QPlainTextEdit()
        self.preview.setObjectName("kiWizardPreview")
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("Vorschau erscheint nach „Vorschau“ oder „Erzeugen“.")
        self.preview.setMaximumHeight(140)
        root.addWidget(QLabel("Vorschau"))
        root.addWidget(self.preview)

        btn_row = QHBoxLayout()
        preview_btn = QPushButton("Vorschau")
        preview_btn.setObjectName("kiWizardPreviewBtn")
        preview_btn.clicked.connect(self._preview)
        btn_row.addWidget(preview_btn)
        btn_row.addStretch(1)
        root.addLayout(btn_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        ok = buttons.button(QDialogButtonBox.Ok)
        ok.setText("Erzeugen & öffnen")
        ok.setObjectName("kiWizardGenerateBtn")
        buttons.accepted.connect(self._generate_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._rebuild_fields()

    def result_document(self):
        return self._result_doc

    def _toggle_company(self, on: bool) -> None:
        self.company_box.setVisible(bool(on))

    def _current_kind(self) -> str:
        return str(self.kind_combo.currentData() or "anschreiben")

    def _rebuild_fields(self) -> None:
        while self.fields_form.rowCount():
            self.fields_form.removeRow(0)
        self._field_edits.clear()
        kind = self._current_kind()
        for spec in wizard_field_specs(kind):
            if spec.key in ("anliegen", "beschreibung", "gegenstand", "leistung"):
                edit: QLineEdit | QPlainTextEdit = QPlainTextEdit()
                edit.setObjectName(f"kiWizardField_{spec.key}")
                edit.setPlaceholderText(spec.placeholder)
                edit.setMaximumHeight(72)
                if spec.placeholder:
                    edit.setPlainText(spec.placeholder)
            else:
                edit = QLineEdit()
                edit.setObjectName(f"kiWizardField_{spec.key}")
                edit.setPlaceholderText(spec.placeholder)
                if spec.placeholder:
                    edit.setText(spec.placeholder)
            self._field_edits[spec.key] = edit
            label = spec.label + (" *" if spec.required else "")
            self.fields_form.addRow(label, edit)

    def _collect_fields(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for key, edit in self._field_edits.items():
            if isinstance(edit, QPlainTextEdit):
                val = edit.toPlainText().strip()
            else:
                val = edit.text().strip()
            if val:
                out[key] = val
        return out

    def _collect_company(self) -> dict[str, str]:
        if not self.company_cb.isChecked():
            return {}
        out: dict[str, str] = {}
        for key, edit in self._company_edits.items():
            val = edit.text().strip()
            if val:
                out[key] = val
        return out

    def _build_doc(self):
        return generate_ki_document(
            self._current_kind(),
            fields=self._collect_fields(),
            company=self._collect_company(),
            company_mode=self.company_cb.isChecked(),
            title=self.title_edit.text().strip() or None,
            use_llm=bool(self.llm_cb.isChecked()),
        )

    def _preview(self) -> None:
        try:
            doc = self._build_doc()
        except Exception as e:
            QMessageBox.warning(self, "KI-Wizard", f"Vorschau fehlgeschlagen:\n{e}")
            return
        self.preview.setPlainText(doc.text)

    def _generate_accept(self) -> None:
        try:
            doc = self._build_doc()
        except Exception as e:
            QMessageBox.warning(self, "KI-Wizard", f"Erzeugen fehlgeschlagen:\n{e}")
            return
        self._result_doc = doc
        self.preview.setPlainText(doc.text)
        self.accept()


def run_ki_document_wizard(parent: QWidget | None = None) -> Optional[Any]:
    """Dialog ausführen; bei OK: KiWizardDocument, sonst None."""
    dlg = KiDocumentWizardDialog(parent)
    if dlg.exec() != QDialog.Accepted:
        return None
    return dlg.result_document()
