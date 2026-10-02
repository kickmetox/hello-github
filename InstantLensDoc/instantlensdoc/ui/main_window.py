"""Hauptfenster: Menüleiste, Seitenleiste, Editor, Statusleiste."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc.config import DISPLAY_NAME, icon_path
from instantlensdoc.core.documents import DocKind, Document, open_document, save_document
from instantlensdoc.core import ocr as ocr_mod
from instantlensdoc.core.layout import LayoutDocument
from instantlensdoc.license import LicenseManager
from instantlensdoc.ui.editor import TextEditor
from instantlensdoc.ui.form_builder import FormBuilderDialog
from instantlensdoc.ui.help_dialog import AboutDialog, HelpDialog
from instantlensdoc.ui.license_dialog import LicenseDialog
from instantlensdoc.ui.pdf_view import PdfViewer
from instantlensdoc.ui.sidebar import Sidebar
from instantlensdoc.ui.stubs import show_planned


class MainWindow(QMainWindow):
    def __init__(self, license_manager: LicenseManager):
        super().__init__()
        self.license_manager = license_manager
        self.doc: Document | None = None
        self.layout_doc = LayoutDocument()

        self.setWindowTitle(DISPLAY_NAME)
        self.resize(1200, 800)
        ic = icon_path()
        if ic:
            self.setWindowIcon(QIcon(str(ic)))

        self._build_ui()
        self._build_menus()
        self._update_license_status()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)
        self.sidebar = Sidebar()
        self.sidebar.search_requested.connect(self._on_search)
        self.sidebar.file_activated.connect(self.open_path)
        splitter.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.editor = TextEditor()
        self.editor.textChanged.connect(self._on_text_changed)
        self.pdf_view = PdfViewer()
        self.pdf_view.status.connect(self._set_status)
        self.image_label = QLabel(alignment=Qt.AlignCenter)
        self.image_label.setText("Bildvorschau")
        self.stack.addWidget(self.editor)  # 0
        self.stack.addWidget(self.pdf_view)  # 1
        self.stack.addWidget(self.image_label)  # 2
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter)

        sb = QStatusBar()
        self.setStatusBar(sb)
        self.license_label = QLabel()
        sb.addPermanentWidget(self.license_label)

    def _build_menus(self):
        mb = self.menuBar()

        # Datei
        m_file = mb.addMenu("&Datei")
        act_new = QAction("Neu", self)
        act_new.setShortcut(QKeySequence.New)
        act_new.triggered.connect(self.new_doc)
        m_file.addAction(act_new)

        act_open = QAction("Öffnen…", self)
        act_open.setShortcut(QKeySequence.Open)
        act_open.triggered.connect(self.open_dialog)
        m_file.addAction(act_open)

        act_save = QAction("Speichern", self)
        act_save.setShortcut(QKeySequence.Save)
        act_save.triggered.connect(self.save_doc)
        m_file.addAction(act_save)

        act_save_as = QAction("Speichern unter…", self)
        act_save_as.triggered.connect(self.save_as)
        m_file.addAction(act_save_as)
        m_file.addSeparator()
        act_quit = QAction("Beenden", self)
        act_quit.setShortcut(QKeySequence.Quit)
        act_quit.triggered.connect(self.close)
        m_file.addAction(act_quit)

        # Bearbeiten
        m_edit = mb.addMenu("&Bearbeiten")
        for name, slot in [
            ("Rückgängig", self.editor.undo),
            ("Wiederholen", self.editor.redo),
            ("Ausschneiden", self.editor.cut),
            ("Kopieren", self.editor.copy),
            ("Einfügen", self.editor.paste),
        ]:
            a = QAction(name, self)
            a.triggered.connect(slot)
            m_edit.addAction(a)

        # Ansicht
        m_view = mb.addMenu("&Ansicht")
        a = QAction("Seitenleiste", self)
        a.setCheckable(True)
        a.setChecked(True)
        a.toggled.connect(self.sidebar.setVisible)
        m_view.addAction(a)

        # Einfügen / Layout
        m_ins = mb.addMenu("&Einfügen")
        a = QAction("Textrahmen", self)
        a.triggered.connect(self._add_text_frame)
        m_ins.addAction(a)
        a = QAction("Bild einfügen…", self)
        a.triggered.connect(self._insert_image)
        m_ins.addAction(a)

        # Extras
        m_extra = mb.addMenu("E&xtras")
        a = QAction("OCR (Bild/PDF-Seite)…", self)
        a.triggered.connect(self._run_ocr)
        m_extra.addAction(a)
        a = QAction("Formulargenerator…", self)
        a.triggered.connect(self._forms)
        m_extra.addAction(a)
        m_extra.addSeparator()
        for key, title in [
            ("ki", "KI-Assistent (geplant)"),
            ("cloud", "Cloud-Sync (geplant)"),
            ("stylus", "Stylus / Palm Rejection (geplant)"),
            ("shapes_ai", "Intelligente Formerkennung (geplant)"),
            ("extrude3d", "3D-Extrusion (geplant)"),
            ("varfonts", "Variable Fonts (geplant)"),
            ("envelope", "Envelope Distort (geplant)"),
            ("esign", "E-Signatur (geplant)"),
        ]:
            a = QAction(title, self)
            a.triggered.connect(lambda checked=False, k=key: show_planned(self, k))
            m_extra.addAction(a)

        # Hilfe
        m_help = mb.addMenu("&Hilfe")
        a = QAction("Hilfe…", self)
        a.triggered.connect(lambda: HelpDialog(self).exec())
        m_help.addAction(a)
        a = QAction("Lizenz…", self)
        a.triggered.connect(self._license)
        m_help.addAction(a)
        a = QAction("Info…", self)
        a.triggered.connect(lambda: AboutDialog(self).exec())
        m_help.addAction(a)

    def _set_status(self, msg: str):
        self.statusBar().showMessage(msg, 5000)

    def _update_license_status(self):
        st = self.license_manager.status()
        self.license_label.setText(f"Lizenz: {st.mode} ({st.days_remaining}d)")
        if not st.allowed:
            QMessageBox.warning(
                self,
                "Lizenz abgelaufen",
                st.message + "\n\nDie App bleibt geöffnet, Speichern kann eingeschränkt sein.",
            )

    def _on_text_changed(self):
        if self.doc and self.doc.kind in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML, DocKind.DOCX):
            self.doc.text = self.editor.toPlainText()
            self.doc.dirty = True

    def _on_search(self, query: str):
        if self.stack.currentWidget() is self.editor:
            n = self.editor.find_and_highlight(query)
            self._set_status(f"{n} Treffer für „{query}“")
            self.sidebar.set_marks([f"Suche: {query} → {n} Treffer"])

    def new_doc(self):
        self.doc = Document(kind=DocKind.TEXT, title="Unbenannt")
        self.editor.setPlainText("")
        self.stack.setCurrentWidget(self.editor)
        self.setWindowTitle(f"{DISPLAY_NAME} — Unbenannt")
        self._set_status("Neues Dokument")

    def open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Öffnen",
            "",
            "Dokumente (*.txt *.md *.html *.htm *.docx *.pdf *.png *.jpg *.jpeg);;Alle (*.*)",
        )
        if path:
            self.open_path(path)

    def open_path(self, path: str):
        try:
            self.doc = open_document(path)
        except Exception as e:
            QMessageBox.critical(self, "Öffnen", str(e))
            return

        self.sidebar.add_document(path)
        self.setWindowTitle(f"{DISPLAY_NAME} — {self.doc.display_name}")

        if self.doc.kind == DocKind.PDF:
            self.stack.setCurrentWidget(self.pdf_view)
            self.pdf_view.load(path)
            if self.pdf_view.store:
                marks = [
                    f"S{a.page + 1}: {a.type.value} {a.text[:30]}"
                    for a in self.pdf_view.store.annotations
                ]
                self.sidebar.set_marks(marks)
        elif self.doc.kind == DocKind.IMAGE:
            from PySide6.QtGui import QPixmap

            self.stack.setCurrentWidget(self.image_label)
            pm = QPixmap(path)
            self.image_label.setPixmap(pm.scaled(900, 700, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.stack.setCurrentWidget(self.editor)
            self.editor.blockSignals(True)
            self.editor.setPlainText(self.doc.text)
            self.editor.blockSignals(False)
        self._set_status(f"Geöffnet: {path}")

    def save_doc(self):
        st = self.license_manager.status()
        if not st.allowed:
            QMessageBox.warning(self, "Lizenz", "Speichern nicht möglich — Lizenz/Trial abgelaufen.")
            return
        if not self.doc:
            return
        if not self.doc.path:
            self.save_as()
            return
        if self.doc.kind in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML, DocKind.DOCX):
            self.doc.text = self.editor.toPlainText()
        try:
            save_document(self.doc)
            self._set_status(f"Gespeichert: {self.doc.path}")
        except Exception as e:
            QMessageBox.critical(self, "Speichern", str(e))

    def save_as(self):
        if not self.doc:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Speichern unter",
            self.doc.display_name,
            "Text (*.txt);;Markdown (*.md);;HTML (*.html);;DOCX (*.docx);;Alle (*.*)",
        )
        if not path:
            return
        if self.doc.kind in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML, DocKind.DOCX):
            self.doc.text = self.editor.toPlainText()
        try:
            save_document(self.doc, Path(path))
            self.sidebar.add_document(path)
            self.setWindowTitle(f"{DISPLAY_NAME} — {self.doc.display_name}")
            self._set_status(f"Gespeichert: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Speichern", str(e))

    def _add_text_frame(self):
        text = self.editor.toPlainText() if self.stack.currentWidget() is self.editor else ""
        frame = self.layout_doc.add_text_frame(text=text)
        flowed = self.layout_doc.flow_text(text or "Neuer Textrahmen", frame)
        if self.stack.currentWidget() is self.editor:
            self.editor.appendPlainText(f"\n--- Textrahmen {frame.id} ---\n{flowed}")
        self._set_status(f"Textrahmen {frame.id} hinzugefügt")

    def _insert_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Bild einfügen", "", "Bilder (*.png *.jpg *.jpeg *.bmp)"
        )
        if not path:
            return
        frame = self.layout_doc.add_image(path)
        if self.stack.currentWidget() is self.editor:
            self.editor.appendPlainText(f"\n[Bild: {path} @ {frame.x},{frame.y} {frame.width}x{frame.height}]\n")
        self._set_status(f"Bild eingefügt: {Path(path).name}")

    def _run_ocr(self):
        ok, msg = ocr_mod.tesseract_available()
        if not ok:
            QMessageBox.information(self, "OCR", msg)
            return
        if self.doc and self.doc.kind == DocKind.IMAGE and self.doc.path:
            try:
                text = ocr_mod.ocr_image(self.doc.path)
                self.stack.setCurrentWidget(self.editor)
                self.editor.setPlainText(text)
                self._set_status("OCR abgeschlossen")
            except Exception as e:
                QMessageBox.warning(self, "OCR", str(e))
            return
        if self.doc and self.doc.kind == DocKind.PDF and self.doc.path:
            try:
                text = ocr_mod.ocr_pdf_page(self.doc.path, self.pdf_view.page_index)
                self.stack.setCurrentWidget(self.editor)
                self.editor.setPlainText(text)
                self._set_status("OCR (PDF-Seite) abgeschlossen")
            except Exception as e:
                QMessageBox.warning(self, "OCR", str(e))
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Bild für OCR", "", "Bilder (*.png *.jpg *.jpeg *.tif *.tiff)"
        )
        if path:
            try:
                text = ocr_mod.ocr_image(path)
                self.stack.setCurrentWidget(self.editor)
                self.editor.setPlainText(text)
            except Exception as e:
                QMessageBox.warning(self, "OCR", str(e))

    def _forms(self):
        FormBuilderDialog(self).exec()

    def _license(self):
        if LicenseDialog(self.license_manager, self).exec():
            self._update_license_status()
