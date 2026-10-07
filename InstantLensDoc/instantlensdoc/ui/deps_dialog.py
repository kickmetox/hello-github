"""Dialog: Startup-Check Laufzeit-Abhängigkeiten."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc.core.deps_check import (
    DepStatus,
    check_runtime_dependencies,
    format_deps_summary,
    has_any_failure,
    has_critical_failure,
)


class DependencyCheckDialog(QDialog):
    """Zeigt Ergebnis der Startup-Prüfung (pypdfium2 / Tesseract)."""

    def __init__(self, statuses: list[DepStatus], parent: QWidget | None = None):
        super().__init__(parent)
        critical = has_critical_failure(statuses)
        self.setWindowTitle(
            "Abhängigkeiten — kritisch" if critical else "Abhängigkeiten prüfen"
        )
        self.resize(520, 360)
        layout = QVBoxLayout(self)
        headline = (
            "Kritische Abhängigkeit fehlt. PDF-Funktionen sind eingeschränkt."
            if critical
            else "Einige optionale Komponenten fehlen oder sind nicht bereit."
        )
        if not has_any_failure(statuses):
            headline = "Alle geprüften Abhängigkeiten sind verfügbar."
        layout.addWidget(QLabel(headline))
        body = QTextEdit()
        body.setReadOnly(True)
        body.setPlainText(format_deps_summary(statuses))
        layout.addWidget(body)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


def show_startup_dependency_dialog(
    parent: QWidget | None = None,
    *,
    only_if_issues: bool = True,
    statuses: list[DepStatus] | None = None,
) -> list[DepStatus]:
    """
    Startup-Check ausführen und bei Problemen (oder immer) Dialog zeigen.
    Rückgabe: geprüfte Statusliste.
    """
    items = list(statuses) if statuses is not None else check_runtime_dependencies()
    if only_if_issues and not has_any_failure(items):
        return items
    dlg = DependencyCheckDialog(items, parent)
    dlg.exec()
    return items


def warn_dependencies_messagebox(
    parent: QWidget | None,
    statuses: list[DepStatus] | None = None,
) -> list[DepStatus]:
    """Kompakte Alternative: QMessageBox statt Dialog."""
    items = list(statuses) if statuses is not None else check_runtime_dependencies()
    if not has_any_failure(items):
        return items
    icon = QMessageBox.Critical if has_critical_failure(items) else QMessageBox.Warning
    QMessageBox(
        icon,
        "Abhängigkeiten",
        format_deps_summary(items),
        QMessageBox.Ok,
        parent,
    ).exec()
    return items
