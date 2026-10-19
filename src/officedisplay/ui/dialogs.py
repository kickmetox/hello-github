from __future__ import annotations

import json

from PySide6.QtCore import QEvent, Qt, QUrl
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
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
    QStackedWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from officedisplay import __author__, __email__, __version__
from officedisplay.paths import icon_path


class SettingsDialog(QDialog):
    def __init__(self, parent, prefs: dict, secrets: dict) -> None:
        super().__init__(parent)
        self.setWindowTitle("Einstellungen – Online-KI und Canva")
        self.setMinimumWidth(720)
        form = QFormLayout()
        self.online = QCheckBox("Online-KI auf ausdrücklichen Klick erlauben")
        self.online.setChecked(bool(prefs.get("online_enabled")))
        self.base = QLineEdit(prefs.get("base_url") or "https://api.openai.com/v1")
        self.model = QLineEdit(prefs.get("model") or "gpt-4o-mini")
        self.image_model = QLineEdit(prefs.get("image_model") or "dall-e-3")
        self.images = QCheckBox("Bildgenerierung erlauben")
        self.images.setChecked(bool(prefs.get("allow_images")))
        self.key = QLineEdit(secrets.get("api_key") or "")
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.canva = QLineEdit(secrets.get("canva_token") or "")
        self.canva.setEchoMode(QLineEdit.EchoMode.Password)
        self.canva_base = QLineEdit(prefs.get("canva_base") or "https://api.canva.com/rest/v1")
        form.addRow(self.online)
        form.addRow("API-Basis (OpenAI-kompatibel)", self.base)
        form.addRow("Chat-Modell", self.model)
        form.addRow("Bild-Modell", self.image_model)
        form.addRow(self.images)
        form.addRow("API-Schlüssel", self.key)
        form.addRow("Canva-Token", self.canva)
        form.addRow("Canva-Basis", self.canva_base)
        for field in (self.base, self.model, self.image_model, self.key, self.canva, self.canva_base):
            field.setMinimumWidth(340)
            field.setCursorPosition(0)
        note = QLabel(
            "Ohne Haken verlässt nichts den Rechner. Schlüssel liegen unter ~/.config/officedisplay/secrets.json, Modus 600."
        )
        note.setWordWrap(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def values(self) -> tuple[dict, dict]:
        prefs = {
            "online_enabled": self.online.isChecked(),
            "base_url": self.base.text().strip(),
            "model": self.model.text().strip(),
            "image_model": self.image_model.text().strip(),
            "allow_images": self.images.isChecked(),
            "canva_base": self.canva_base.text().strip(),
        }
        secrets = {"api_key": self.key.text().strip(), "canva_token": self.canva.text().strip()}
        return prefs, secrets


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
            "Kein Tracking. Online-KI und Canva Connect nur nach Freigabe und nur auf Klick.</p>"
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
        online = QPushButton("Online erzeugen")
        run_cmd = QPushButton("Befehl anwenden")
        coach = QPushButton("Sprech-Coach")
        doc = QPushButton("Dokument umwandeln")
        rewrite = QPushButton("Markierten Text online umformulieren")
        image = QPushButton("Bild online erzeugen")
        inspect = QPushButton("Modell inspizieren")
        offline.clicked.connect(lambda: self.done_with("offline"))
        online.clicked.connect(lambda: self.done_with("online"))
        run_cmd.clicked.connect(lambda: self.done_with("command"))
        coach.clicked.connect(lambda: self.done_with("coach"))
        doc.clicked.connect(lambda: self.done_with("document"))
        rewrite.clicked.connect(lambda: self.done_with("rewrite"))
        image.clicked.connect(lambda: self.done_with("image"))
        inspect.clicked.connect(lambda: self.done_with("inspect"))
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Text-zu-Design, lokal oder per freigegebener Online-API"))
        layout.addWidget(self.prompt)
        row = QHBoxLayout()
        row.addWidget(offline)
        row.addWidget(online)
        layout.addLayout(row)
        layout.addWidget(QLabel("Inline-Befehl"))
        layout.addWidget(self.command)
        layout.addWidget(run_cmd)
        row2 = QHBoxLayout()
        for button in (coach, doc, rewrite, image, inspect):
            row2.addWidget(button)
        layout.addLayout(row2)
        layout.addWidget(self.output)
        self.action = ""

    def done_with(self, action: str) -> None:
        self.action = action
        if action in {"offline", "online", "command", "coach", "document", "rewrite", "image", "inspect"}:
            self.accept()


class LibraryDialog(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle("Studio und Canva Connect")
        self.resize(520, 520)
        self.templates = QListWidget()
        self.templates.addItems(["Pitch", "Unterricht", "Kennzahlen", "Zitat", "Vergleich", "Team", "Titel mit Fläche"])
        self.sizes = QComboBox()
        self.sizes.addItems(
            ["Präsentation 16:9", "Präsentation 4:3", "Quadrat", "Story 9:16", "Portrait 4:5", "A4", "LinkedIn", "Banner"]
        )
        self.elements = QComboBox()
        self.elements.addItems(["Rahmen", "Fläche", "Kreis", "Raute", "Stern", "Pfeil", "Badge"])
        self.template_id = QLineEdit()
        self.template_id.setPlaceholderText("Canva-Brand-Template-ID oder Design-ID")
        self.fields = QTextEdit()
        self.fields.setPlaceholderText('{"Titel": {"type": "text", "text": "Hallo"}}')
        self.action = ""
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Lokale Vorlagen, Größen und Formen."))
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
        layout.addWidget(QLabel("Canva Connect (nur mit Token, auf Klick)"))
        layout.addWidget(self.template_id)
        layout.addWidget(self.fields)
        row2 = QHBoxLayout()
        for name, action in (
            ("Markenvorlagen listen", "list"),
            ("Autofill starten", "autofill"),
            ("Export als PPTX holen", "export"),
        ):
            button = QPushButton(name)
            button.clicked.connect(lambda _=False, item=action: self.finish(item))
            row2.addWidget(button)
        layout.addLayout(row2)

    def finish(self, action: str) -> None:
        self.action = action
        self.accept()


class MagicDesignDialog(QDialog):
    """Satz zu Folien. Der Aufbau dieses Fensters ruft kein Netz auf."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Magic Design")
        self.resize(520, 220)
        self.action = ""
        self.sentence = QLineEdit()
        self.sentence.setPlaceholderText("Ein Satz, zum Beispiel Quartalszahlen Nord Süd")
        note = QLabel(
            "Lokal ohne Netz: Titelfolie mit vollflächigem Hintergrund, Inhaltsfolien, "
            "passende Vorlage. „Über Canva erzeugen“ sendet den Satz nur mit Token "
            "an POST /generations und zeigt die Design-ID."
        )
        note.setWordWrap(True)
        local = QPushButton("Lokal erzeugen")
        canva = QPushButton("Über Canva erzeugen")
        cancel = QPushButton("Abbrechen")
        local.clicked.connect(lambda: self._finish("local"))
        canva.clicked.connect(lambda: self._finish("canva"))
        cancel.clicked.connect(self.reject)
        row = QHBoxLayout()
        row.addWidget(local)
        row.addWidget(canva)
        row.addWidget(cancel)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Ein Satz für den Foliensatz"))
        layout.addWidget(self.sentence)
        layout.addWidget(note)
        layout.addLayout(row)

    def _finish(self, action: str) -> None:
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


class _FrameView(QWidget):
    """Folie oder Bild, seitenfüllend mit schwarzem Rand."""

    def __init__(self, owner: "PresenterDialog") -> None:
        super().__init__(owner)
        self.owner = owner
        self.image: QImage | None = None
        self.blank = ""
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        if self.blank == "white":
            painter.fillRect(self.rect(), QColor("#FFFFFF"))
            painter.end()
            return
        painter.fillRect(self.rect(), QColor("#000000"))
        if self.blank != "black" and self.image is not None and not self.image.isNull():
            scaled = self.image.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawImage(x, y, scaled)
        painter.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.owner.apply_key("click")
            return
        super().mousePressEvent(event)


class _PassiveText(QTextEdit):
    def __init__(self, owner: "PresenterDialog") -> None:
        super().__init__()
        self.owner = owner
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFrameStyle(0)

    def keyPressEvent(self, event) -> None:
        self.owner.keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.owner.apply_key("click")
            return
        super().mousePressEvent(event)


class PresenterDialog(QDialog):
    """Vollbild-Player für die Präsentation oder eine Slideshow."""

    def __init__(self, parent, window, slideshow=None) -> None:
        super().__init__(parent)
        self.window = window
        self.slideshow = slideshow
        self.index = 0 if slideshow is not None else window.canvas.slide_index
        self.blank = ""
        self.notes_visible = True
        self._player = None
        self._audio = None
        self._video = None
        self._fullscreen_set = False
        self.setWindowTitle("Slideshow" if slideshow is not None else "Präsentieren")
        self.resize(1280, 720)
        self.setStyleSheet(
            "QDialog { background:#000000; }"
            "QLabel#playerNotes { background:#1B1F2A; color:#FFFFFF; padding:8px 14px; font-size:15px; }"
            "QTextEdit { background:#F4F6FB; color:#1B1F2A; font-size:28px; padding:40px; }"
        )
        self.frame = _FrameView(self)
        self.text_page = QWidget()
        text_layout = QVBoxLayout(self.text_page)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)
        self.text_image = QLabel()
        self.text_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_image.setStyleSheet("background:#000000;")
        self.text_image.setMinimumHeight(180)
        self.text_view = _PassiveText(self)
        text_layout.addWidget(self.text_image, 2)
        text_layout.addWidget(self.text_view, 3)
        self.video_page = QWidget()
        self.video_page.setStyleSheet("background:#000000;")
        self.video_layout = QVBoxLayout(self.video_page)
        self.video_layout.setContentsMargins(0, 0, 0, 0)
        self.fallback = QLabel()
        self.fallback.setWordWrap(True)
        self.fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.fallback.setStyleSheet("background:#000000; color:#FFFFFF; font-size:22px; padding:48px;")
        self.fallback.mousePressEvent = lambda event: self.apply_key("click")  # type: ignore[method-assign]
        self.text_image.mousePressEvent = lambda event: self.apply_key("click")  # type: ignore[method-assign]
        self.stack = QStackedWidget()
        self.stack.addWidget(self.frame)
        self.stack.addWidget(self.text_page)
        self.stack.addWidget(self.video_page)
        self.stack.addWidget(self.fallback)
        self.bar = QLabel()
        self.bar.setObjectName("playerNotes")
        self.bar.setWordWrap(True)
        self.bar.setFixedHeight(56)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.stack, stretch=1)
        layout.addWidget(self.bar)
        if slideshow is None:
            self.window.dwell.enter(self.index)
        self.refresh()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._fullscreen_set:
            self._fullscreen_set = True
            self.showFullScreen()
        self.setFocus()

    def _count(self) -> int:
        if self.slideshow is not None:
            return len(self.slideshow.entries)
        return len(self.window.presentation.slides)

    def apply_key(self, key: str) -> None:
        from officedisplay.player_nav import navigate_player

        state = navigate_player(self.index, self._count(), self.blank, key)
        if state["exit"]:
            self.close()
            return
        if state["toggle_notes"]:
            self.notes_visible = not self.notes_visible
            if not self.blank:
                self.bar.setVisible(self.notes_visible)
            return
        self.blank = state["blank"]
        if state["run_click"] and self._run_click_action():
            return
        if state["run_click"]:
            state = navigate_player(self.index, self._count(), self.blank, "next")
            self.blank = state["blank"]
        if self.slideshow is None and state["index"] != self.index:
            self.window.dwell.enter(state["index"])
        self.index = state["index"]
        self.refresh()

    def _run_click_action(self) -> bool:
        if self.slideshow is not None or self.blank:
            return False
        slide = self.window.presentation.slides[self.index]
        for obj in slide.objects:
            action = obj.props.get("action") or {}
            if action.get("type") == "goto":
                self.index = max(0, min(len(self.window.presentation.slides) - 1, int(action.get("target") or 0)))
                self.window.dwell.enter(self.index)
                self.refresh()
                return True
            if action.get("type") == "popup":
                QMessageBox.information(self, "Info", str(action.get("text") or ""))
                return True
        return False

    def refresh(self) -> None:
        self._stop_media()
        count = self._count()
        if count <= 0:
            return
        self.index = max(0, min(self.index, count - 1))
        if self.blank in {"black", "white"}:
            self.frame.blank = self.blank
            self.frame.image = None
            self.stack.setCurrentWidget(self.frame)
            self.bar.setVisible(False)
            self.frame.update()
            return
        self.bar.setVisible(self.notes_visible)
        note = ""
        if self.slideshow is None:
            from officedisplay.ui.render import render_thumb

            slide = self.window.presentation.slides[self.index]
            note = slide.notes or ""
            width = max(1280, self.frame.width() or self.width() or 1280)
            self.frame.blank = ""
            self.frame.image = render_thumb(self.window.presentation, slide, width)
            self.stack.setCurrentWidget(self.frame)
            self.frame.update()
        else:
            entry = self.slideshow.entries[self.index]
            note = entry.title or ""
            if entry.text and entry.kind == "video":
                note = entry.text
            if entry.kind == "text":
                self._show_text(entry)
            elif entry.kind == "video":
                self._show_video(entry)
            else:
                self._show_image(entry.path or "", entry.title)
        self.bar.setText(f"{self.index + 1} / {count}    {note}".rstrip())

    def _show_image(self, path: str, title: str) -> None:
        image = QImage(path) if path else QImage()
        if image.isNull():
            self.fallback.setText(f"Bild nicht lesbar.\n{path or title}")
            self.stack.setCurrentWidget(self.fallback)
            return
        self.frame.blank = ""
        self.frame.image = image
        self.stack.setCurrentWidget(self.frame)
        self.frame.update()

    def _show_text(self, entry) -> None:
        image = QImage(entry.path) if entry.path else QImage()
        if not image.isNull():
            pixmap = QPixmap.fromImage(image).scaled(
                1200,
                420,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.text_image.setPixmap(pixmap)
            self.text_image.show()
        else:
            self.text_image.hide()
        self.text_view.setPlainText(entry.text or entry.title or "")
        self.stack.setCurrentWidget(self.text_page)

    def _show_video(self, entry) -> None:
        path = entry.path or ""
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
            from PySide6.QtMultimediaWidgets import QVideoWidget
        except Exception:
            self._show_video_fallback(path)
            return
        try:
            self._video = QVideoWidget(self.video_page)
            self._video.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._video.setStyleSheet("background:#000000;")
            self.video_layout.addWidget(self._video)
            self._player = QMediaPlayer(self)
            self._audio = QAudioOutput(self)
            self._audio.setVolume(1.0)
            self._player.setAudioOutput(self._audio)
            self._player.setVideoOutput(self._video)
            self._video.installEventFilter(self)
            self._player.errorOccurred.connect(lambda *_args, media=path: self._show_video_fallback(media))
            self._player.setSource(QUrl.fromLocalFile(path))
            if self._player is None or self._player.error() != QMediaPlayer.Error.NoError:
                self._show_video_fallback(path)
                return
            self.stack.setCurrentWidget(self.video_page)
            self._player.play()
        except Exception:
            self._show_video_fallback(path)

    def eventFilter(self, watched, event) -> bool:
        if watched is self._video and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self.apply_key("click")
            return True
        if watched is self._video and event.type() == QEvent.Type.KeyPress:
            self.keyPressEvent(event)
            return True
        return super().eventFilter(watched, event)

    def _show_video_fallback(self, path: str) -> None:
        if getattr(self, "_in_fallback", False):
            return
        self._in_fallback = True
        try:
            self._stop_media()
            self.fallback.setText(
                "Qt Multimedia kann dieses Format nicht abspielen.\n"
                f"{path}\n"
                "Die Datei bleibt als Pfad sichtbar."
            )
            self.stack.setCurrentWidget(self.fallback)
        finally:
            self._in_fallback = False

    def _stop_media(self) -> None:
        if self._player is not None:
            self._player.stop()
            try:
                self._player.setSource(QUrl())
            except Exception:
                pass
            self._player.deleteLater()
            self._player = None
        if self._audio is not None:
            self._audio.deleteLater()
            self._audio = None
        if self._video is not None:
            self.video_layout.removeWidget(self._video)
            self._video.hide()
            self._video.deleteLater()
            self._video = None

    def keyPressEvent(self, event) -> None:
        mapping = {
            Qt.Key.Key_Right: "right",
            Qt.Key.Key_Left: "left",
            Qt.Key.Key_Space: "space",
            Qt.Key.Key_PageDown: "pagedown",
            Qt.Key.Key_PageUp: "pageup",
            Qt.Key.Key_Home: "home",
            Qt.Key.Key_End: "end",
            Qt.Key.Key_Escape: "escape",
            Qt.Key.Key_N: "n",
            Qt.Key.Key_B: "b",
            Qt.Key.Key_W: "w",
            Qt.Key.Key_Period: "period",
        }
        command = mapping.get(event.key())
        if command is None and event.text() == ".":
            command = "period"
        if command is None:
            super().keyPressEvent(event)
            return
        self.apply_key(command)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.apply_key("click")
            return
        super().mousePressEvent(event)

    def closeEvent(self, event) -> None:
        self._stop_media()
        if self.slideshow is None:
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
