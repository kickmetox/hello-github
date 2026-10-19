from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from officedisplay import __author__, __email__, __version__
from officedisplay.paths import icon_path


class HelpDialog(QDialog):
    def __init__(self, parent, markdown: str) -> None:
        super().__init__(parent)
        self.setWindowTitle("Hilfe – Office Display")
        self.resize(760, 640)
        browser = QTextBrowser()
        browser.setMarkdown(markdown)
        layout = QVBoxLayout(self)
        layout.addWidget(browser)


class AboutDialog(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle("Info")
        layout = QVBoxLayout(self)
        if icon_path().is_file():
            label = QLabel()
            label.setPixmap(QPixmap(str(icon_path())).scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignHCenter)
        text = QLabel(
            f"<h2>Office Display {__version__}</h2>"
            f"<p>{__author__}<br>{__email__}</p>"
            "<p>Lokale Präsentationen für PowerPoint, OpenOffice, OnlyOffice und SoftMaker. "
            "Kein Netz, kein Tracking, keine Cloud-Dienste.</p>"
        )
        text.setWordWrap(True)
        layout.addWidget(text)


class AiDialog(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle("KI")
        self.resize(560, 420)
        self.prompt = QLineEdit()
        self.prompt.setPlaceholderText("Ein Satz für den Foliensatz")
        self.command = QLineEdit()
        self.command.setPlaceholderText("Befehl für die aktuelle Folie, z. B. zwei spalten")
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        offline = QPushButton("Lokal erzeugen")
        run_cmd = QPushButton("Befehl anwenden")
        coach = QPushButton("Sprech-Coach")
        doc = QPushButton("Dokument umwandeln")
        inspect = QPushButton("Modell inspizieren")
        offline.clicked.connect(lambda: self.done_with("offline"))
        run_cmd.clicked.connect(lambda: self.done_with("command"))
        coach.clicked.connect(lambda: self.done_with("coach"))
        doc.clicked.connect(lambda: self.done_with("document"))
        inspect.clicked.connect(lambda: self.done_with("inspect"))
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Text-zu-Design, nur aus dem eingegebenen Satz"))
        layout.addWidget(self.prompt)
        layout.addWidget(offline)
        layout.addWidget(QLabel("Inline-Befehl"))
        layout.addWidget(self.command)
        layout.addWidget(run_cmd)
        row2 = QHBoxLayout()
        for button in (coach, doc, inspect):
            row2.addWidget(button)
        layout.addLayout(row2)
        layout.addWidget(self.output)
        self.action = ""

    def done_with(self, action: str) -> None:
        self.action = action
        if action in {"offline", "command", "coach", "document", "inspect"}:
            self.accept()


class LibraryDialog(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle("Bibliothek")
        self.resize(480, 360)
        self.templates = QListWidget()
        self.templates.addItems(["Pitch", "Unterricht", "Kennzahlen", "Zitat", "Vergleich", "Team", "Titel mit Fläche"])
        self.sizes = QComboBox()
        self.sizes.addItems(
            ["Präsentation 16:9", "Präsentation 4:3", "Quadrat", "Story 9:16", "Portrait 4:5", "A4", "LinkedIn", "Banner"]
        )
        self.elements = QComboBox()
        self.elements.addItems(["Rahmen", "Fläche", "Kreis", "Raute", "Stern", "Pfeil", "Badge"])
        self.action = ""
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Lokale Vorlagen, Größen und Formen. Kein Cloud-Katalog."))
        layout.addWidget(self.templates)
        layout.addWidget(self.sizes)
        layout.addWidget(self.elements)
        row = QHBoxLayout()
        for name, action in (
            ("Vorlage anwenden", "template"),
            ("Größe anpassen", "resize"),
            ("Element einfügen", "element"),
        ):
            button = QPushButton(name)
            button.clicked.connect(lambda _=False, item=action: self.finish(item))
            row.addWidget(button)
        layout.addLayout(row)

    def finish(self, action: str) -> None:
        self.action = action
        self.accept()


class BrandDialog(QDialog):
    def __init__(self, parent, brand: dict) -> None:
        super().__init__(parent)
        self.setWindowTitle("Marke")
        self.locked = QCheckBox("Schriften und Farben sperren")
        self.locked.setChecked(bool(brand.get("locked")))
        self.heading = QLineEdit(brand.get("heading_font") or "Segoe UI")
        self.body = QLineEdit(brand.get("body_font") or "Segoe UI")
        self.colors = QLineEdit(", ".join(brand.get("colors") or []))
        self.logo = QLineEdit(brand.get("logo") or "")
        browse = QPushButton("Logo…")
        browse.clicked.connect(self._browse)
        form = QFormLayout()
        form.addRow(self.locked)
        form.addRow("Überschrift", self.heading)
        form.addRow("Text", self.body)
        form.addRow("Farben", self.colors)
        row = QHBoxLayout()
        row.addWidget(self.logo)
        row.addWidget(browse)
        form.addRow("Logo", row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Logo", "", "Bilder (*.png *.jpg *.jpeg *.webp)")
        if path:
            self.logo.setText(path)

    def value(self) -> dict:
        return {
            "locked": self.locked.isChecked(),
            "heading_font": self.heading.text().strip() or "Segoe UI",
            "body_font": self.body.text().strip() or "Segoe UI",
            "colors": [item.strip() for item in self.colors.text().split(",") if item.strip()],
            "logo": self.logo.text().strip() or None,
        }


class DataDialog(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle("Tabelle verbinden")
        self.path = QLineEdit()
        self.sheet = QLineEdit()
        browse = QPushButton("Datei…")
        browse.clicked.connect(self._browse)
        form = QFormLayout()
        row = QHBoxLayout()
        row.addWidget(self.path)
        row.addWidget(browse)
        form.addRow("Datei", row)
        form.addRow("Blatt (optional)", self.sheet)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Tabelle", "", "Tabellen (*.xlsx *.csv)")
        if path:
            self.path.setText(path)


class ThreeDialog(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle("3D")
        self.kind = QComboBox()
        self.kind.addItems(["cube", "pyramid"])
        self.obj = QLineEdit()
        browse = QPushButton("OBJ…")
        browse.clicked.connect(self._browse)
        self.preview = QLabel("Vorschau erscheint nach dem Rendern.")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(200)
        render = QPushButton("Rendern und einfügen")
        render.clicked.connect(self.accept)
        layout = QVBoxLayout(self)
        layout.addWidget(self.kind)
        row = QHBoxLayout()
        row.addWidget(self.obj)
        row.addWidget(browse)
        layout.addLayout(row)
        layout.addWidget(self.preview)
        layout.addWidget(render)
        self.action = "insert"

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "OBJ", "", "OBJ (*.obj)")
        if path:
            self.obj.setText(path)


class PresenterDialog(QDialog):
    def __init__(self, parent, window) -> None:
        super().__init__(parent)
        self.setWindowTitle("Präsentieren")
        self.resize(980, 680)
        self.window = window
        self.index = window.canvas.slide_index
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notes = QTextEdit()
        self.notes.setReadOnly(True)
        self.notes.setMaximumHeight(120)
        buttons = QHBoxLayout()
        prev = QPushButton("Zurück")
        nxt = QPushButton("Weiter")
        prev.clicked.connect(lambda: self.go(-1))
        nxt.clicked.connect(lambda: self.go(1))
        buttons.addWidget(prev)
        buttons.addWidget(nxt)
        layout = QVBoxLayout(self)
        layout.addWidget(self.label, stretch=1)
        layout.addWidget(self.notes)
        layout.addLayout(buttons)
        self.window.dwell.enter(self.index)
        self.refresh()

    def go(self, step: int) -> None:
        slides = self.window.presentation.slides
        self.index = max(0, min(len(slides) - 1, self.index + step))
        self.window.dwell.enter(self.index)
        self.refresh()

    def refresh(self) -> None:
        from officedisplay.ui.render import render_thumb

        slide = self.window.presentation.slides[self.index]
        image = render_thumb(self.window.presentation, slide, 900)
        self.label.setPixmap(QPixmap.fromImage(image))
        self.notes.setPlainText(slide.notes or "")

    def mousePressEvent(self, event) -> None:
        slide = self.window.presentation.slides[self.index]
        # Klickbare Aktionen liegen in den Objekt-Eigenschaften.
        for obj in slide.objects:
            action = obj.props.get("action") or {}
            if action.get("type") == "goto":
                self.index = max(0, min(len(self.window.presentation.slides) - 1, int(action.get("target") or 0)))
                self.window.dwell.enter(self.index)
                self.refresh()
                return
            if action.get("type") == "popup":
                QMessageBox.information(self, "Info", str(action.get("text") or ""))
                return
        self.go(1)

    def closeEvent(self, event) -> None:
        self.window.dwell.leave()
        super().closeEvent(event)


class ZuiDialog(QDialog):
    def __init__(self, parent, window) -> None:
        super().__init__(parent)
        self.setWindowTitle("Leinwand")
        self.resize(1000, 700)
        self.window = window
        self.scale = 0.18
        self.chosen = window.canvas.slide_index
        self.setMouseTracking(True)

    def paintEvent(self, _event) -> None:
        from PySide6.QtGui import QPainter

        from officedisplay.ui.render import render_thumb

        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().window())
        x, y = 24, 24
        for index, slide in enumerate(self.window.presentation.slides):
            image = render_thumb(self.window.presentation, slide, int(1600 * self.scale))
            painter.drawImage(x, y, image)
            painter.drawText(x, y + image.height() + 16, slide.name)
            x += image.width() + 24
            if x > self.width() - 200:
                x = 24
                y += image.height() + 48
        painter.end()

    def wheelEvent(self, event) -> None:
        self.scale = max(0.08, min(0.5, self.scale * (1.1 if event.angleDelta().y() > 0 else 0.9)))
        self.update()

    def mousePressEvent(self, event) -> None:
        from officedisplay.ui.render import render_thumb

        x, y = 24, 24
        for index, slide in enumerate(self.window.presentation.slides):
            image = render_thumb(self.window.presentation, slide, int(1600 * self.scale))
            if x <= event.position().x() <= x + image.width() and y <= event.position().y() <= y + image.height():
                self.chosen = index
                self.accept()
                return
            x += image.width() + 24
            if x > self.width() - 200:
                x = 24
                y += image.height() + 48


def show_text(parent, title: str, text: str) -> None:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text[:4000])
    box.exec()


def parse_json_field(text: str) -> dict:
    if not text.strip():
        return {}
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("JSON-Objekt erwartet")
    return data
