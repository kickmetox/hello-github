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
    QWidget,
)

from instantlensdoc.config import DISPLAY_NAME, icon_paths_for_qt
from instantlensdoc.core.documents import DocKind, Document, open_document, save_document
from instantlensdoc.core import ocr as ocr_mod
from instantlensdoc.core.layout import LayoutDocument
from instantlensdoc.license import LicenseManager
from instantlensdoc.ui.editor import TextEditor
from instantlensdoc.ui.form_builder import FormBuilderDialog
from instantlensdoc.ui.help_dialog import AboutDialog, HelpDialog
from instantlensdoc.ui.license_dialog import LicenseDialog
from instantlensdoc.ui.ocr_dialog import OcrDialog
from instantlensdoc.ui.pdf_view import PdfViewer
from instantlensdoc.ui.sidebar import Sidebar
from instantlensdoc.ui.stubs import show_planned


class MainWindow(QMainWindow):
    def __init__(self, license_manager: LicenseManager):
        super().__init__()
        self.license_manager = license_manager
        self.doc: Document | None = None
        self.layout_doc = LayoutDocument()
        self._editor_marks: list[str] = []

        self.setWindowTitle(DISPLAY_NAME)
        self.resize(1200, 800)
        icon = QIcon()
        for p in icon_paths_for_qt():
            icon.addFile(str(p))
        if not icon.isNull():
            self.setWindowIcon(icon)

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
        self.sidebar.search_next_requested.connect(self._on_search_next)
        self.sidebar.file_activated.connect(self.open_path)
        self.sidebar.mark_activated.connect(self._on_mark_activated)
        splitter.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.editor = TextEditor()
        self.editor.textChanged.connect(self._on_text_changed)
        self.pdf_view = PdfViewer()
        self.pdf_view.status.connect(self._set_status)
        self.pdf_view.annotations_changed.connect(self._refresh_pdf_marks)
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
        m_export = m_file.addMenu("Exportieren")
        for title, fmt in [
            ("Als HTML…", "html"),
            ("Als DOCX…", "docx"),
            ("Als PDF…", "pdf"),
        ]:
            a = QAction(title, self)
            a.triggered.connect(lambda checked=False, f=fmt: self._export_editor(f))
            m_export.addAction(a)
        m_file.addSeparator()
        act_quit = QAction("Beenden", self)
        act_quit.setShortcut(QKeySequence.Quit)
        act_quit.triggered.connect(self.close)
        m_file.addAction(act_quit)

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
        m_edit.addSeparator()
        act_find = QAction("Suchen…", self)
        act_find.setShortcut(QKeySequence.Find)
        act_find.triggered.connect(self._focus_search)
        m_edit.addAction(act_find)
        act_mark = QAction("Auswahl markieren", self)
        act_mark.setShortcut(QKeySequence("Ctrl+H"))
        act_mark.triggered.connect(self._mark_selection)
        m_edit.addAction(act_mark)
        act_clear_marks = QAction("Markierungen löschen", self)
        act_clear_marks.triggered.connect(self._clear_editor_marks)
        m_edit.addAction(act_clear_marks)

        m_view = mb.addMenu("&Ansicht")
        a = QAction("Seitenleiste", self)
        a.setCheckable(True)
        a.setChecked(True)
        a.toggled.connect(self.sidebar.setVisible)
        m_view.addAction(a)

        m_pdf = mb.addMenu("&PDF")
        for title, slot in [
            ("Annotationen speichern", lambda: self.pdf_view.save_annotations()),
            ("Annotationen laden", lambda: self.pdf_view.reload_annotations()),
            ("Seite drehen (90°)", lambda: self.pdf_view.rotate_current()),
            ("Seite löschen…", lambda: self.pdf_view.delete_current()),
            ("Seiten neu anordnen…", lambda: self.pdf_view.reorder_dialog()),
            ("Seite als Bild extrahieren…", lambda: self.pdf_view.extract_page_as_image()),
            ("Bild als neue Seite…", lambda: self.pdf_view.insert_image_page()),
            ("PDF-Text → Overlay…", lambda: self.pdf_view.import_text_overlays()),
            ("Text-Overlays einbrennen…", lambda: self.pdf_view.bake_overlays()),
        ]:
            a = QAction(title, self)
            a.triggered.connect(slot)
            m_pdf.addAction(a)

        m_ins = mb.addMenu("&Einfügen")
        a = QAction("Textrahmen", self)
        a.triggered.connect(self._add_text_frame)
        m_ins.addAction(a)
        a = QAction("Verketteten Textrahmen…", self)
        a.triggered.connect(self._add_chained_frame)
        m_ins.addAction(a)
        a = QAction("Bild einfügen…", self)
        a.triggered.connect(self._insert_image)
        m_ins.addAction(a)

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

    def _focus_search(self):
        self.sidebar.setVisible(True)
        self.sidebar.search.setFocus()
        self.sidebar.search.selectAll()

    def _on_search(self, query: str):
        if not query:
            self._set_status("Leere Suche")
            return
        if self.stack.currentWidget() is self.editor:
            n = self.editor.find_and_highlight(query)
            self._set_status(f"{n} Treffer für „{query}“")
            lines = [f"Suche: {query} → {n} Treffer"] + self._editor_marks
            self.sidebar.set_marks(lines)
            return
        if self.stack.currentWidget() is self.pdf_view:
            # Annotationen nach Text filtern + Hinweis
            hits = []
            if self.pdf_view.store:
                for a in self.pdf_view.store.annotations:
                    blob = f"{a.type.value} {a.text}".lower()
                    if query.lower() in blob:
                        hits.append(a)
            if hits:
                lines = [f"S{a.page + 1}: {a.type.value} {a.text[:40]}" for a in hits]
                self.sidebar.set_marks(lines, hits)
                self._set_status(f"{len(hits)} Annotation(en) zu „{query}“")
            else:
                self._set_status(
                    f"Keine Annotation zu „{query}“ — PDF-Volltextsuche benötigt OCR/eingebetteten Text"
                )
            return
        self._set_status("Suche: Editor oder PDF öffnen")

    def _on_search_next(self):
        q = self.sidebar.search.text().strip()
        if self.stack.currentWidget() is self.editor:
            if self.editor.find_next(q or None):
                self._set_status("Nächster Treffer")
            else:
                self._set_status("Keine weiteren Treffer")

    def _mark_selection(self):
        if self.stack.currentWidget() is not self.editor:
            QMessageBox.information(self, "Markieren", "Markieren funktioniert im Texteditor.")
            return
        if not self.editor.highlight_selection():
            QMessageBox.information(self, "Markieren", "Bitte Text auswählen.")
            return
        snip = self.editor.selected_snippet() or "Auswahl"
        label = f"Markierung: {snip}"
        self._editor_marks.append(label)
        self.sidebar.append_mark(label)
        self._set_status("Auswahl markiert")

    def _clear_editor_marks(self):
        self.editor.clear_extra_selections()
        self._editor_marks.clear()
        if self.stack.currentWidget() is self.pdf_view:
            self._refresh_pdf_marks()
        else:
            self.sidebar.set_marks([])
        self._set_status("Markierungen gelöscht")

    def _refresh_pdf_marks(self):
        if self.stack.currentWidget() is not self.pdf_view:
            return
        pairs = self.pdf_view.annotation_summaries()
        self.sidebar.set_marks([p[0] for p in pairs], [p[1] for p in pairs])

    def _on_mark_activated(self, index: int):
        payload = self.sidebar.mark_payload(index)
        if payload is not None and hasattr(payload, "page"):
            self.stack.setCurrentWidget(self.pdf_view)
            self.pdf_view.goto_page(int(payload.page))
            self._set_status(f"Annotation Seite {payload.page + 1}")

    def new_doc(self):
        self.doc = Document(kind=DocKind.TEXT, title="Unbenannt")
        self.editor.setPlainText("")
        self.editor.clear_extra_selections()
        self._editor_marks.clear()
        self.sidebar.set_marks([])
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
            self._refresh_pdf_marks()
        elif self.doc.kind == DocKind.IMAGE:
            from PySide6.QtGui import QPixmap

            self.stack.setCurrentWidget(self.image_label)
            pm = QPixmap(path)
            self.image_label.setPixmap(
                pm.scaled(900, 700, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            self.sidebar.set_marks([f"Bild: {Path(path).name}"])
        else:
            self.stack.setCurrentWidget(self.editor)
            self.editor.blockSignals(True)
            self.editor.setPlainText(self.doc.text)
            self.editor.blockSignals(False)
            self.editor.clear_extra_selections()
            self._editor_marks.clear()
            self.sidebar.set_marks([])
        self._set_status(f"Geöffnet: {path}")

    def save_doc(self):
        st = self.license_manager.status()
        if not st.allowed:
            QMessageBox.warning(self, "Lizenz", "Speichern nicht möglich — Lizenz/Trial abgelaufen.")
            return
        if not self.doc:
            return
        if self.doc.kind == DocKind.PDF:
            if self.pdf_view.save_annotations():
                self._set_status("PDF-Annotationen gespeichert")
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
        if self.doc.kind == DocKind.PDF:
            self.pdf_view.save_annotations()
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

    def _export_editor(self, fmt: str):
        """Editor-Inhalt nach HTML / DOCX / PDF exportieren."""
        text = ""
        title = "InstantLens Doc"
        if self.stack.currentWidget() is self.editor:
            text = self.editor.toPlainText()
            if self.doc:
                title = self.doc.title or self.doc.display_name
        elif self.doc and self.doc.kind in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML, DocKind.DOCX):
            text = self.doc.text or self.editor.toPlainText()
            title = self.doc.display_name
        else:
            QMessageBox.information(
                self,
                "Export",
                "Export gilt für den Texteditor.\nBitte TXT/MD/HTML/DOCX öffnen oder Text eingeben.",
            )
            return
        filters = {
            "html": ("HTML (*.html)", ".html"),
            "docx": ("DOCX (*.docx)", ".docx"),
            "pdf": ("PDF (*.pdf)", ".pdf"),
        }
        filt, ext = filters[fmt]
        default = (self.doc.display_name if self.doc else "export") + ext
        if "." in default and not default.lower().endswith(ext):
            default = Path(default).stem + ext
        path, _ = QFileDialog.getSaveFileName(self, f"Export {fmt.upper()}", default, filt)
        if not path:
            return
        try:
            from instantlensdoc.core import export as exp

            if fmt == "html":
                exp.export_html(text, path, title=title)
            elif fmt == "docx":
                exp.export_docx(text, path, title=title)
            else:
                exp.export_pdf(text, path, title=title)
            self._set_status(f"Exportiert: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export", str(e))

    def _add_text_frame(self):
        text = self.editor.toPlainText() if self.stack.currentWidget() is self.editor else ""
        frame = self.layout_doc.add_text_frame(text=text)
        flowed = self.layout_doc.flow_text(text or "Neuer Textrahmen", frame)
        if self.stack.currentWidget() is self.editor:
            self.editor.appendPlainText(f"\n--- Textrahmen {frame.id} ---\n{flowed}")
        self._set_status(f"Textrahmen {frame.id} hinzugefügt")

    def _add_chained_frame(self):
        """Verkettete Textrahmen: Overflow fließt in den nächsten Rahmen."""
        source = self.editor.toPlainText() if self.stack.currentWidget() is self.editor else ""
        if not source.strip():
            source = (
                "Dies ist ein Beispieltext für verkettete Textrahmen in InstantLens Doc. "
                "Der Text fließt automatisch in den nächsten Rahmen, sobald die Kapazität "
                "des ersten Rahmens erreicht ist. Weitere Wörter landen im Folgeahmen. "
            ) * 4
        # Zwei schmale Rahmen verkettet
        f1 = self.layout_doc.add_text_frame(
            text="", x=40, y=40, width=240, height=120, font_size=12
        )
        f2 = self.layout_doc.chain_new_frame(f1, x=40, y=180, width=240, height=120)
        filled = self.layout_doc.flow_text_chain(source, f1)
        overflow = filled.pop("__overflow__", "")
        if self.stack.currentWidget() is self.editor:
            lines = [
                f"\n=== Verkettete Rahmen {f1.id} → {f2.id} ===",
                f"--- Rahmen {f1.id} ---",
                f1.text,
                f"--- Rahmen {f2.id} (Fortsetzung) ---",
                f2.text,
            ]
            if overflow:
                lines.append(f"--- Overflow (kein weiterer Rahmen) ---\n{overflow[:400]}")
            self.editor.appendPlainText("\n".join(lines))
        self._set_status(f"Verkettung {f1.id}→{f2.id} ({len(filled)} Rahmen gefüllt)")

    def _insert_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Bild einfügen", "", "Bilder (*.png *.jpg *.jpeg *.bmp)"
        )
        if not path:
            return
        frame = self.layout_doc.add_image(path)
        if self.stack.currentWidget() is self.pdf_view and self.pdf_view.pdf_path:
            from PySide6.QtWidgets import QInputDialog

            choice, ok = QInputDialog.getItem(
                self,
                "Bild einfügen",
                "Ziel:",
                ["Layout-Rahmen (Editor-Hinweis)", "Als neue PDF-Seite", "Als Stempel-Annotation"],
                0,
                False,
            )
            if ok and choice == "Als neue PDF-Seite":
                try:
                    from ild_pdf import PdfDocument, insert_image_as_page

                    insert_image_as_page(self.pdf_view.pdf_path, path)
                    with PdfDocument(self.pdf_view.pdf_path) as doc:
                        self.pdf_view.page_count = len(doc)
                    self.pdf_view.page_index = self.pdf_view.page_count - 1
                    self.pdf_view.refresh()
                    self._set_status("Bild als PDF-Seite eingefügt")
                    return
                except Exception as e:
                    QMessageBox.warning(self, "Bild", str(e))
                    return
            if ok and choice == "Als Stempel-Annotation":
                try:
                    from ild_pdf import insert_image_stamp_overlay

                    insert_image_stamp_overlay(
                        self.pdf_view.pdf_path,
                        path,
                        page_index=self.pdf_view.page_index,
                    )
                    self.pdf_view.reload_annotations()
                    self._set_status("Bildstempel-Annotation gesetzt")
                    return
                except Exception as e:
                    QMessageBox.warning(self, "Bild", str(e))
                    return
        if self.stack.currentWidget() is self.editor:
            self.editor.appendPlainText(
                f"\n[Bild: {path} @ {frame.x},{frame.y} {frame.width}x{frame.height}]\n"
            )
        self._set_status(f"Bild eingefügt: {Path(path).name}")

    def _run_ocr(self):
        from PySide6.QtWidgets import QDialog

        ok, msg = ocr_mod.tesseract_available()
        need_file = not (
            self.doc and self.doc.path and self.doc.kind in (DocKind.IMAGE, DocKind.PDF)
        )
        dlg = OcrDialog(
            self,
            need_file=need_file,
            default_label=Path(self.doc.path).name if self.doc and self.doc.path else "",
        )
        if dlg.exec() != QDialog.Accepted:
            return

        if not ok:
            QMessageBox.information(self, "OCR — Tesseract fehlt", msg)
            self._set_status("OCR nicht verfügbar")
            return

        lang = dlg.lang_code()
        mode = dlg.output_mode()
        try:
            if self.doc and self.doc.kind == DocKind.IMAGE and self.doc.path:
                source_label = Path(self.doc.path).name
                result = ocr_mod.run_ocr(
                    self.doc.path,
                    lang=lang,
                    mode=mode,
                    out_dir=Path(self.doc.path).parent,
                    source_label=source_label,
                )
            elif self.doc and self.doc.kind == DocKind.PDF and self.doc.path:
                from ild_pdf import render_page

                source_label = f"{Path(self.doc.path).name} Seite {self.pdf_view.page_index + 1}"
                img = render_page(self.doc.path, self.pdf_view.page_index, scale=2.0)
                result = ocr_mod.run_ocr(
                    img,
                    lang=lang,
                    mode=mode,
                    out_dir=Path(self.doc.path).parent,
                    source_label=source_label,
                )
            else:
                path = dlg.selected_path
                if not path:
                    path, _ = QFileDialog.getOpenFileName(
                        self, "Bild für OCR", "", "Bilder (*.png *.jpg *.jpeg *.tif *.tiff)"
                    )
                if not path:
                    return
                source_label = Path(path).name
                result = ocr_mod.run_ocr(
                    path,
                    lang=lang,
                    mode=mode,
                    out_dir=Path(path).parent,
                    source_label=source_label,
                )
        except ocr_mod.OcrUnavailable as e:
            QMessageBox.information(self, "OCR — Tesseract fehlt", str(e))
            return
        except Exception as e:
            QMessageBox.warning(self, "OCR", str(e))
            return

        self.stack.setCurrentWidget(self.editor)
        self.editor.setPlainText(result.text)
        self.doc = Document(kind=DocKind.TEXT, title=f"OCR — {source_label}", text=result.text)
        self.setWindowTitle(f"{DISPLAY_NAME} — OCR — {source_label}")
        extra = ""
        if result.searchable_pdf:
            extra = f" · PDF {result.searchable_pdf.name}"
            if result.sidecar:
                extra += f" + {result.sidecar.name}"
        self._set_status(f"OCR ({result.lang}, {result.mode.value}){extra}")

    def _forms(self):
        FormBuilderDialog(self).exec()

    def _license(self):
        if LicenseDialog(self.license_manager, self).exec():
            self._update_license_status()
