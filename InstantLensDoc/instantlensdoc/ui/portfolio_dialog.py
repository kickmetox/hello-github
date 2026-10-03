"""PDF-Portfolio erstellen / öffnen (pikepdf Collection + Attachments) — 2.0.0."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ild_pdf.portfolio import (
    create_portfolio,
    extract_portfolio,
    open_portfolio,
)


class PortfolioDialog(QDialog):
    """Dialog: Portfolio erstellen (Dateien → Container-PDF) oder öffnen/extrahieren."""

    def __init__(self, parent: QWidget | None = None, *, start_dir: str = ""):
        super().__init__(parent)
        self.setObjectName("portfolioDialog")
        self.setWindowTitle("PDF-Portfolio — InstantLens Doc 2.0")
        self.setModal(True)
        self.resize(560, 420)
        self._start_dir = start_dir or ""
        self._created_path: str | None = None
        self._opened_path: str | None = None
        self._files: list[str] = []

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_create_tab(), "Erstellen")
        self.tabs.addTab(self._build_open_tab(), "Öffnen")
        layout.addWidget(self.tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        close_btn = buttons.button(QDialogButtonBox.Close)
        if close_btn is not None:
            close_btn.setText("Schließen")
        layout.addWidget(buttons)

        esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc.setContext(Qt.WindowShortcut)
        esc.activated.connect(self.reject)

    def _build_create_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(
            QLabel(
                "Mehrere Dateien in ein Container-PDF (Portfolio / Collection) "
                "packen — pikepdf Attachments + /Collection."
            )
        )
        form = QFormLayout()
        self.title_edit = QLineEdit("InstantLens Portfolio")
        self.title_edit.setObjectName("portfolioTitle")
        form.addRow("Titel", self.title_edit)
        layout.addLayout(form)

        self.file_list = QListWidget()
        self.file_list.setObjectName("portfolioFileList")
        self.file_list.setAccessibleName("Portfolio-Dateien")
        layout.addWidget(self.file_list, 1)

        row = QHBoxLayout()
        btn_add = QPushButton("Dateien hinzufügen…")
        btn_add.clicked.connect(self._add_files)
        btn_rm = QPushButton("Entfernen")
        btn_rm.clicked.connect(self._remove_selected)
        row.addWidget(btn_add)
        row.addWidget(btn_rm)
        row.addStretch(1)
        layout.addLayout(row)

        self.create_status = QLabel("")
        self.create_status.setObjectName("portfolioCreateStatus")
        layout.addWidget(self.create_status)

        btn_create = QPushButton("Portfolio speichern…")
        btn_create.setObjectName("portfolioCreateBtn")
        btn_create.setDefault(True)
        btn_create.clicked.connect(self._create)
        layout.addWidget(btn_create)
        return w

    def _build_open_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(
            QLabel(
                "Bestehendes Portfolio öffnen: Collection/Attachments listen "
                "und optional extrahieren."
            )
        )
        row = QHBoxLayout()
        self.open_path_edit = QLineEdit()
        self.open_path_edit.setObjectName("portfolioOpenPath")
        self.open_path_edit.setPlaceholderText("Pfad zum Portfolio-PDF…")
        btn_browse = QPushButton("Durchsuchen…")
        btn_browse.clicked.connect(self._browse_open)
        btn_inspect = QPushButton("Öffnen / Listen")
        btn_inspect.setObjectName("portfolioOpenBtn")
        btn_inspect.clicked.connect(self._inspect)
        row.addWidget(self.open_path_edit, 1)
        row.addWidget(btn_browse)
        row.addWidget(btn_inspect)
        layout.addLayout(row)

        self.entries_list = QListWidget()
        self.entries_list.setObjectName("portfolioEntries")
        self.entries_list.setAccessibleName("Portfolio-Einträge")
        layout.addWidget(self.entries_list, 1)

        self.open_status = QLabel("")
        self.open_status.setObjectName("portfolioOpenStatus")
        layout.addWidget(self.open_status)

        btn_extract = QPushButton("Alle extrahieren…")
        btn_extract.setObjectName("portfolioExtractBtn")
        btn_extract.clicked.connect(self._extract)
        layout.addWidget(btn_extract)
        return w

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Dateien für Portfolio",
            self._start_dir,
            "Alle Dateien (*.*)",
        )
        for p in paths:
            if p and p not in self._files:
                self._files.append(p)
                self.file_list.addItem(QListWidgetItem(Path(p).name))
        self.create_status.setText(f"{len(self._files)} Datei(en)")

    def _remove_selected(self) -> None:
        row = self.file_list.currentRow()
        if row < 0:
            return
        self.file_list.takeItem(row)
        if 0 <= row < len(self._files):
            del self._files[row]
        self.create_status.setText(f"{len(self._files)} Datei(en)")

    def _create(self) -> None:
        if not self._files:
            QMessageBox.warning(self, "Portfolio", "Bitte mindestens eine Datei hinzufügen.")
            return
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Portfolio speichern",
            str(Path(self._start_dir or ".") / "portfolio.pdf"),
            "PDF (*.pdf)",
        )
        if not dest:
            return
        try:
            info = create_portfolio(
                dest,
                self._files,
                title=(self.title_edit.text() or "InstantLens Portfolio").strip(),
            )
            self._created_path = info.path
            n = len(info.entries or [])
            self.create_status.setText(
                f"Portfolio gespeichert: {Path(info.path).name} · {n} Datei(en)"
            )
            QMessageBox.information(
                self,
                "Portfolio",
                f"Portfolio erstellt:\n{info.path}\n{n} eingebettete Datei(en).",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Portfolio", f"Erstellen fehlgeschlagen:\n{exc}")

    def _browse_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Portfolio öffnen",
            self._start_dir,
            "PDF (*.pdf)",
        )
        if path:
            self.open_path_edit.setText(path)

    def _inspect(self) -> None:
        path = (self.open_path_edit.text() or "").strip()
        if not path:
            QMessageBox.warning(self, "Portfolio", "Bitte Pfad wählen.")
            return
        try:
            info = open_portfolio(path)
            self._opened_path = info.path
            self.entries_list.clear()
            for e in info.entries or []:
                size_kb = (e.size / 1024.0) if e.size else 0
                label = f"{e.filename or e.name}"
                if size_kb:
                    label += f"  ({size_kb:.1f} KB)"
                item = QListWidgetItem(label)
                item.setToolTip(e.description or e.name)
                self.entries_list.addItem(item)
            kind = "Portfolio (Collection)" if info.is_portfolio else "PDF mit Anhängen"
            self.open_status.setText(
                f"{kind}: {info.title} · {len(info.entries or [])} Datei(en)"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Portfolio", f"Öffnen fehlgeschlagen:\n{exc}")

    def _extract(self) -> None:
        path = self._opened_path or (self.open_path_edit.text() or "").strip()
        if not path:
            QMessageBox.warning(self, "Portfolio", "Zuerst Portfolio öffnen.")
            return
        out = QFileDialog.getExistingDirectory(
            self, "Zielordner für Extraktion", self._start_dir or str(Path(path).parent)
        )
        if not out:
            return
        try:
            written = extract_portfolio(path, out_dir=out)
            self.open_status.setText(f"{len(written)} Datei(en) extrahiert → {out}")
            QMessageBox.information(
                self,
                "Portfolio",
                f"{len(written)} Datei(en) extrahiert nach:\n{out}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Portfolio", f"Extraktion fehlgeschlagen:\n{exc}")

    @property
    def created_path(self) -> str | None:
        return self._created_path

    @property
    def opened_path(self) -> str | None:
        return self._opened_path
