from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDockWidget,
    QFileDialog,
    QFontComboBox,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSpinBox,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from officedisplay.ai.canva_api import CanvaAPIError, CanvaClient
from officedisplay.ai.commands import apply_command
from officedisplay.ai.doc_transform import read_text_file, slides_from_text
from officedisplay.ai.layout_model import inspect_model
from officedisplay.ai.offline_design import generate_deck
from officedisplay.ai.online_ai import OnlineAIError, OnlineAISettings, draft_deck, generate_image, rewrite_text
from officedisplay.ai.speech_coach import analyze_speech
from officedisplay.analytics import DwellLog
from officedisplay.design.animate import morph_slide
from officedisplay.design.palette import dotnet_palette
from officedisplay.design.photo import adjust, color_filter, knockout_corners
from officedisplay.design.resize import RESIZE_PRESETS, align_objects, magic_resize
from officedisplay.design.templates import apply_template, element
from officedisplay.design.threed import render_png
from officedisplay.io.data_bind import bind_chart, refresh_bindings
from officedisplay.io.incoming import classify, place_on_slide
from officedisplay.io.native_io import load_odisp, save_odisp
from officedisplay.io.odp_io import export_odp, import_odp
from officedisplay.io.pptx_io import export_pptx, import_pptx
from officedisplay.macros_runner import MacroError, run_macro
from officedisplay.model.presentation import (
    Presentation,
    Slide,
    SlideObject,
    blank_presentation,
    duplicate_objects,
    find_object,
    group_objects,
    move_object_to_slide,
    new_id,
    ungroup,
)
from officedisplay.paths import help_path, icon_path
from officedisplay.settings_store import load_secrets, media_folder, save_secrets
from officedisplay.ui.canvas import SlideCanvas
from officedisplay.ui.dialogs import (
    AboutDialog,
    AiDialog,
    BrandDialog,
    DataDialog,
    HelpDialog,
    LibraryDialog,
    PresenterDialog,
    SettingsDialog,
    ThreeDialog,
    ZuiDialog,
    parse_json_field,
    show_text,
)
from officedisplay.ui.render import clear_image_cache, render_thumb
from officedisplay.ui.theme import stylesheet
from officedisplay.design.palette import constrain_color, constrain_font


class SlideStrip(QListWidget):
    def __init__(self, owner: "MainWindow") -> None:
        super().__init__()
        self.owner = owner
        self.setIconSize(QSize(200, 120))
        self.setSpacing(8)
        self.setAcceptDrops(True)
        self.setMinimumWidth(230)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat("application/x-officedisplay-object"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat("application/x-officedisplay-object"):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        if not event.mimeData().hasFormat("application/x-officedisplay-object"):
            return
        item = self.itemAt(event.position().toPoint())
        index = self.row(item) if item is not None else self.currentRow()
        object_id = bytes(event.mimeData().data("application/x-officedisplay-object")).decode("utf-8")
        self.owner.move_selection_to(index, object_id)
        event.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Office Display")
        self.resize(1360, 860)
        if icon_path().is_file():
            self.setWindowIcon(QIcon(str(icon_path())))
        self.presentation = blank_presentation()
        self.path: Path | None = None
        self.undo: list[dict] = []
        self.redo: list[dict] = []
        self._before = None
        self.dwell = DwellLog()
        self.settings = QSettings("Sellerbach", "OfficeDisplay")
        self.prefs = self._load_prefs()
        self.secrets = load_secrets()
        self.canvas = SlideCanvas()
        self.canvas.set_presentation(self.presentation, 0)
        self.canvas.gestureStarted.connect(self._remember)
        self.canvas.changed.connect(self._after_change)
        self.canvas.selectionChanged.connect(self._sync_format)
        self.canvas.pointerKindChanged.connect(self._pointer)
        self.canvas.filesDropped.connect(self._drop_files)
        self.canvas.textDropped.connect(self._drop_text)
        self.canvas.statusMessage.connect(self._video_message)
        self.setCentralWidget(self.canvas)
        self.strip = SlideStrip(self)
        self.strip.currentRowChanged.connect(self._thumb_clicked)
        dock = QDockWidget("Folien", self)
        dock.setWidget(self.strip)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self._build_actions()
        self._build_toolbar()
        self.apply_theme(self.prefs.get("theme") or "farbe")
        self.refresh_thumbs()
        self.statusBar().showMessage("Andreas Meyer · ame@sellerbach.de · Zeiger: Maus · Offline · kein Tracking")

    def _load_prefs(self) -> dict:
        raw = self.settings.value("prefs", "")
        if not raw:
            return {"theme": "farbe"}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"theme": "farbe"}

    def _save_prefs(self) -> None:
        self.settings.setValue("prefs", json.dumps(self.prefs))

    def _build_actions(self) -> None:
        file_menu = self.menuBar().addMenu("Datei")
        edit_menu = self.menuBar().addMenu("Bearbeiten")
        insert_menu = self.menuBar().addMenu("Einfügen")
        design_menu = self.menuBar().addMenu("Gestalten")
        ai_menu = self.menuBar().addMenu("KI")
        library_menu = self.menuBar().addMenu("Canva")
        show_menu = self.menuBar().addMenu("Präsentieren")
        help_menu = self.menuBar().addMenu("Hilfe")
        self._add(file_menu, "Neu", self.new_file, "Ctrl+N")
        self._add(file_menu, "Öffnen…", self.open_file, "Ctrl+O")
        self._add(file_menu, "Speichern", self.save_file, "Ctrl+S")
        self._add(file_menu, "Speichern unter…", self.save_file_as)
        file_menu.addSeparator()
        self._add(file_menu, "Import PPTX…", self.import_pptx_file)
        self._add(file_menu, "Import ODP…", self.import_odp_file)
        self._add(file_menu, "Export PPTX…", self.export_pptx_file)
        self._add(file_menu, "Export ODP…", self.export_odp_file)
        self._add(file_menu, "Tabelle verbinden…", self.bind_data)
        self._add(file_menu, "Daten aktualisieren", self.refresh_data)
        self._add(file_menu, "Makro ausführen…", self.run_macro_file)
        self._add(edit_menu, "Rückgängig", self.undo_change, "Ctrl+Z")
        self._add(edit_menu, "Wiederholen", self.redo_change, "Ctrl+Y")
        self._add(edit_menu, "Gruppieren", self.group_selected, "Ctrl+G")
        self._add(edit_menu, "Gruppierung aufheben", self.ungroup_selected, "Ctrl+Shift+G")
        self._add(edit_menu, "Duplizieren", self.duplicate_selected, "Ctrl+D")
        self._add(edit_menu, "Löschen", self.delete_selected, "Del")
        self._add(edit_menu, "Auf Folie verschieben…", self.move_selected_dialog)
        self._add(insert_menu, "Bild…", self.insert_image)
        self._add(insert_menu, "Video…", self.insert_video)
        self._add(insert_menu, "Text- oder PDF-Datei…", self.insert_document)
        self._add(insert_menu, "3D-Modell…", self.insert_3d)
        self._add(insert_menu, "Kommentar", self.add_comment)
        self._add(design_menu, "Hintergrundfarbe", self.background_color)
        self._add(design_menu, "Verlauf", self.background_gradient)
        self._add(design_menu, "Hintergrundbild…", self.background_image)
        self._add(design_menu, "Bild aufhellen", lambda: self.filter_image("bright"))
        self._add(design_menu, "Graustufen", lambda: self.filter_image("gray"))
        self._add(design_menu, "Weichzeichnen", lambda: self.filter_image("blur"))
        self._add(design_menu, "Schärfen", lambda: self.filter_image("sharpen"))
        self._add(design_menu, "Spiegeln", lambda: self.filter_image("flip"))
        self._add(design_menu, "Eckfarbe freistellen", lambda: self.filter_image("knockout"))
        design_menu.addSeparator()
        self._add(design_menu, "Links ausrichten", lambda: self.align("left"))
        self._add(design_menu, "Zentrieren", lambda: self.align("hcenter"))
        self._add(design_menu, "Oben ausrichten", lambda: self.align("top"))
        self._add(design_menu, "Markenführung…", self.edit_brand)
        self._add(design_menu, "Farbreihe aus Marke", self.apply_palette)
        self._add(ai_menu, "Text zu Folien…", self.open_ai)
        self._add(ai_menu, "Modell inspizieren", self.inspect_model)
        self._add(ai_menu, "Sprech-Coach", self.speech_coach)
        self._add(ai_menu, "Einstellungen Online-KI / Canva", self.open_settings)
        self._add(library_menu, "Studio und Connect", self.open_library)
        self._add(show_menu, "Präsentieren", self.present)
        self._add(show_menu, "Leinwand (ZUI)", self.open_zui)
        self._add(show_menu, "Morph-Vorschau", self.preview_morph)
        self._add(show_menu, "Eingangseffekt abspielen", self.preview_entrance)
        self._add(show_menu, "Kamera-Einblendung", self.open_camera)
        self._add(show_menu, "Verweildauer speichern", self.save_analytics)
        self._add(show_menu, "Lokaler Ordner-Sync…", self.enable_sync)
        self._add(design_menu, "Deckkraft Hintergrund…", self.background_opacity)
        self._add(design_menu, "Bildanpassung cover/contain…", self.background_fit)
        self._add(edit_menu, "Text links", lambda: self._align_text("left"))
        self._add(edit_menu, "Text zentriert", lambda: self._align_text("center"))
        self._add(edit_menu, "Text rechts", lambda: self._align_text("right"))
        self._add(edit_menu, "Eingang: Einblenden", lambda: self._set_entrance("fade"))
        self._add(edit_menu, "Eingang: Einfliegen", lambda: self._set_entrance("fly"))
        self._add(edit_menu, "Eingang: Zoom", lambda: self._set_entrance("zoom"))
        self._add(edit_menu, "Sprechernotiz…", self.edit_notes)
        self._add(edit_menu, "Aktion beim Klick…", self.edit_action)
        self._add(help_menu, "Hilfe", self.open_help, "F1")
        self._add(help_menu, "Info", self.open_about)

    def _add(self, menu, title, slot, shortcut: str | None = None) -> None:
        action = QAction(title, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        menu.addAction(action)

    def _build_toolbar(self) -> None:
        bar = QToolBar("Werkzeuge")
        bar.setMovable(False)
        self.addToolBar(bar)
        self.tool_buttons = {}
        for key, label in (
            ("select", "Auswahl"),
            ("text", "Text"),
            ("rect", "Rechteck"),
            ("ellipse", "Ellipse"),
            ("roundrect", "Rahmen"),
            ("arrow", "Pfeil"),
            ("star", "Stern"),
            ("line", "Linie"),
            ("pen", "Stift"),
            ("highlighter", "Marker"),
            ("eraser", "Radierer"),
            ("chart", "Diagramm"),
            ("pan", "Verschieben"),
        ):
            action = QAction(label, self)
            action.setCheckable(True)
            action.triggered.connect(lambda _checked=False, name=key: self.set_tool(name))
            bar.addAction(action)
            self.tool_buttons[key] = action
        self.tool_buttons["select"].setChecked(True)
        for label, slot in (("Bild", self.insert_image), ("Video", self.insert_video), ("3D", self.insert_3d)):
            extra = QAction(label, self)
            extra.triggered.connect(slot)
            bar.addAction(extra)
        self.font_box = QFontComboBox()
        self.font_box.currentFontChanged.connect(self.apply_font)
        self.size_box = QSpinBox()
        self.size_box.setRange(8, 120)
        self.size_box.setValue(28)
        self.size_box.valueChanged.connect(self.apply_size)
        bar.addWidget(self.font_box)
        bar.addWidget(self.size_box)
        for label, slot in (("Fett", self.toggle_bold), ("Kursiv", self.toggle_italic), ("Unterstrichen", self.toggle_underline), ("Farbe", self.pick_color)):
            button = QAction(label, self)
            button.triggered.connect(slot)
            bar.addAction(button)
        self.theme_box = QComboBox()
        self.theme_box.addItems(["hell", "dunkel", "farbe", "graustufen"])
        self.theme_box.setCurrentText(self.prefs.get("theme") or "farbe")
        self.theme_box.currentTextChanged.connect(self.apply_theme)
        bar.addWidget(self.theme_box)
        self.touch_box = QComboBox()
        self.touch_box.addItems(["Touch: verschieben", "Touch: zeichnen"])
        self.touch_box.currentIndexChanged.connect(self._touch_mode)
        bar.addWidget(self.touch_box)
        self.pen_width = QSpinBox()
        self.pen_width.setRange(1, 48)
        self.pen_width.setValue(6)
        self.pen_width.valueChanged.connect(self._pen)
        self.pen_curve = QSpinBox()
        self.pen_curve.setRange(2, 40)
        self.pen_curve.setValue(10)
        self.pen_curve.valueChanged.connect(self._pen)
        self.pen_smooth = QSpinBox()
        self.pen_smooth.setRange(0, 4)
        self.pen_smooth.setValue(1)
        self.pen_smooth.valueChanged.connect(self._pen)
        bar.addWidget(QLabel("Stärke"))
        bar.addWidget(self.pen_width)
        bar.addWidget(QLabel("Druck"))
        bar.addWidget(self.pen_curve)
        bar.addWidget(QLabel("Glättung"))
        bar.addWidget(self.pen_smooth)
        side = QWidget()
        layout = QVBoxLayout(side)
        layout.setContentsMargins(8, 8, 8, 8)
        for label, slot in (("Folie +", self.add_slide), ("Folie −", self.delete_slide), ("Nach oben", lambda: self.move_slide(-1)), ("Nach unten", lambda: self.move_slide(1))):
            from PySide6.QtWidgets import QPushButton

            button = QPushButton(label)
            button.clicked.connect(slot)
            layout.addWidget(button)
        layout.addStretch(1)
        dock = QDockWidget("Folienaktionen", self)
        dock.setWidget(side)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def apply_theme(self, name: str) -> None:
        self.setStyleSheet(stylesheet(name))
        self.prefs["theme"] = name
        self._save_prefs()

    def set_tool(self, name: str) -> None:
        self.canvas.tool = name
        self.canvas.highlighter = name == "highlighter"
        for key, action in self.tool_buttons.items():
            action.setChecked(key == name)

    def _touch_mode(self) -> None:
        self.canvas.touch_mode = "draw" if self.touch_box.currentIndex() == 1 else "pan"

    def _pen(self) -> None:
        self.canvas.pen_width = float(self.pen_width.value())
        self.canvas.pen_curve = max(0.2, self.pen_curve.value() / 10.0)
        self.canvas.pen_smooth = int(self.pen_smooth.value())

    def _pointer(self, name: str) -> None:
        online = "Online an" if self.prefs.get("online_enabled") else "Offline"
        self.statusBar().showMessage(f"Andreas Meyer · ame@sellerbach.de · Zeiger: {name} · {online} · kein Tracking")

    def _remember(self) -> None:
        self._before = self.presentation.to_dict()

    def _after_change(self) -> None:
        current = self.presentation.to_dict()
        if self._before and self._before != current:
            self.undo.append(self._before)
            self.redo.clear()
        self._before = None
        self.refresh_thumbs()

    def refresh_thumbs(self) -> None:
        row = self.canvas.slide_index
        self.strip.blockSignals(True)
        self.strip.clear()
        for index, slide in enumerate(self.presentation.slides):
            item = QListWidgetItem(f"{index + 1}  {slide.name}  ·  {slide.status}")
            item.setIcon(QIcon(QPixmap.fromImage(render_thumb(self.presentation, slide, 200))))
            self.strip.addItem(item)
        if self.presentation.slides:
            self.strip.setCurrentRow(max(0, min(row, len(self.presentation.slides) - 1)))
        self.strip.blockSignals(False)
        self.canvas.update()

    def _thumb_clicked(self, row: int) -> None:
        if row < 0:
            return
        self.canvas.set_index(row)

    def current_slide(self) -> Slide:
        return self.presentation.slides[self.canvas.slide_index]

    def selected_objects(self):
        found = []
        for object_id in self.canvas.selected:
            obj, _parent, _container = find_object(self.current_slide(), object_id)
            if obj is not None:
                found.append(obj)
        return found

    def _push(self) -> None:
        self.undo.append(self.presentation.to_dict())
        self.redo.clear()

    def undo_change(self) -> None:
        if not self.undo:
            return
        self.redo.append(self.presentation.to_dict())
        self.presentation = Presentation.from_dict(self.undo.pop())
        self.canvas.set_presentation(self.presentation, min(self.canvas.slide_index, len(self.presentation.slides) - 1))
        self.refresh_thumbs()

    def redo_change(self) -> None:
        if not self.redo:
            return
        self.undo.append(self.presentation.to_dict())
        self.presentation = Presentation.from_dict(self.redo.pop())
        self.canvas.set_presentation(self.presentation, min(self.canvas.slide_index, len(self.presentation.slides) - 1))
        self.refresh_thumbs()

    def new_file(self) -> None:
        self.presentation = blank_presentation()
        self.path = None
        self.canvas.set_presentation(self.presentation, 0)
        self.refresh_thumbs()

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Öffnen", "", "Office Display (*.odisp);;PowerPoint (*.pptx);;OpenDocument (*.odp)")
        if not path:
            return
        self.load_path(Path(path))

    def load_path(self, path: Path) -> None:
        if path.suffix.lower() == ".pptx":
            self.presentation = import_pptx(path)
        elif path.suffix.lower() == ".odp":
            self.presentation = import_odp(path)
        else:
            self.presentation = load_odisp(path)
        self.path = path if path.suffix.lower() == ".odisp" else None
        self.canvas.set_presentation(self.presentation, 0)
        self.refresh_thumbs()

    def save_file(self) -> None:
        if self.path is None:
            self.save_file_as()
            return
        save_odisp(self.presentation, self.path)

    def save_file_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Speichern", "praesentation.odisp", "Office Display (*.odisp)")
        if not path:
            return
        if not path.endswith(".odisp"):
            path += ".odisp"
        self.path = Path(path)
        save_odisp(self.presentation, self.path)

    def import_pptx_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "PPTX", "", "PowerPoint (*.pptx)")
        if path:
            self.load_path(Path(path))

    def import_odp_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "ODP", "", "OpenDocument (*.odp)")
        if path:
            self.load_path(Path(path))

    def export_pptx_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "PPTX exportieren", "praesentation.pptx", "PowerPoint (*.pptx)")
        if path:
            export_pptx(self.presentation, path)

    def export_odp_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "ODP exportieren", "praesentation.odp", "OpenDocument (*.odp)")
        if path:
            export_odp(self.presentation, path)

    def add_slide(self) -> None:
        self._push()
        self.presentation.slides.append(Slide(id=new_id(), name=f"Folie {len(self.presentation.slides) + 1}"))
        self.canvas.set_index(len(self.presentation.slides) - 1)
        self.refresh_thumbs()

    def delete_slide(self) -> None:
        if len(self.presentation.slides) <= 1:
            return
        self._push()
        del self.presentation.slides[self.canvas.slide_index]
        self.canvas.set_index(max(0, self.canvas.slide_index - 1))
        self.refresh_thumbs()

    def move_slide(self, step: int) -> None:
        index = self.canvas.slide_index
        target = index + step
        if target < 0 or target >= len(self.presentation.slides):
            return
        self._push()
        slides = self.presentation.slides
        slides[index], slides[target] = slides[target], slides[index]
        self.canvas.set_index(target)
        self.refresh_thumbs()

    def group_selected(self) -> None:
        if len(self.canvas.selected) < 2:
            return
        self._push()
        group = group_objects(self.current_slide(), list(self.canvas.selected))
        if group:
            self.canvas.selected = [group.id]
        self.refresh_thumbs()

    def ungroup_selected(self) -> None:
        if len(self.canvas.selected) != 1:
            return
        self._push()
        released = ungroup(self.current_slide(), self.canvas.selected[0])
        self.canvas.selected = [obj.id for obj in released]
        self.refresh_thumbs()

    def duplicate_selected(self) -> None:
        self._push()
        copies = duplicate_objects(self.current_slide(), list(self.canvas.selected))
        self.canvas.selected = [obj.id for obj in copies]
        self.refresh_thumbs()

    def delete_selected(self) -> None:
        self._push()
        for object_id in list(self.canvas.selected):
            obj, _parent, container = find_object(self.current_slide(), object_id)
            if obj is not None and container is not None:
                container.remove(obj)
        self.canvas.selected = []
        self.refresh_thumbs()

    def move_selected_dialog(self) -> None:
        if not self.canvas.selected:
            return
        index, ok = QInputDialog.getInt(self, "Folie", "Zielindex (1 = erste Folie)", 1, 1, len(self.presentation.slides))
        if ok:
            self.move_selection_to(index - 1, self.canvas.selected[0])

    def move_selection_to(self, index: int, object_id: str) -> None:
        if index < 0 or index >= len(self.presentation.slides):
            return
        source = self.current_slide()
        target = self.presentation.slides[index]
        self._push()
        if move_object_to_slide(source, target, object_id):
            self.canvas.selected = []
            self.canvas.set_index(index)
            self.refresh_thumbs()

    def _sync_format(self, _ids) -> None:
        objects = self.selected_objects()
        if len(objects) == 1 and objects[0].kind == "text":
            self.size_box.blockSignals(True)
            self.size_box.setValue(int(objects[0].props.get("font_size") or 28))
            self.size_box.blockSignals(False)

    def _mutate_text(self, fn) -> None:
        objects = [obj for obj in self.selected_objects() if obj.kind == "text"]
        if not objects:
            return
        self._push()
        brand = self.presentation.brand
        for obj in objects:
            fn(obj, brand)
        self.canvas.update()

    def apply_font(self, font) -> None:
        def change(obj, brand):
            obj.props["font_family"] = constrain_font(brand, font.family(), "body")

        self._mutate_text(change)

    def apply_size(self, value: int) -> None:
        self._mutate_text(lambda obj, _brand: obj.props.__setitem__("font_size", int(value)))

    def toggle_bold(self) -> None:
        self._mutate_text(lambda obj, _brand: obj.props.__setitem__("bold", not obj.props.get("bold")))

    def toggle_italic(self) -> None:
        self._mutate_text(lambda obj, _brand: obj.props.__setitem__("italic", not obj.props.get("italic")))

    def toggle_underline(self) -> None:
        self._mutate_text(lambda obj, _brand: obj.props.__setitem__("underline", not obj.props.get("underline")))

    def pick_color(self) -> None:
        color = QColorDialog.getColor(parent=self)
        if not color.isValid():
            return
        chosen = color.name()

        def change(obj, brand):
            obj.props["color"] = constrain_color(brand, chosen)

        self._mutate_text(change)

    def background_color(self) -> None:
        color = QColorDialog.getColor(parent=self)
        if not color.isValid():
            return
        self._push()
        slide = self.current_slide()
        slide.background.mode = "solid"
        slide.background.color = constrain_color(self.presentation.brand, color.name())
        self.refresh_thumbs()

    def background_gradient(self) -> None:
        self._push()
        slide = self.current_slide()
        slide.background.mode = "gradient"
        slide.background.color = "#0B63E5"
        slide.background.color2 = "#F28C28"
        self.refresh_thumbs()

    def background_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Hintergrund", "", "Bilder (*.png *.jpg *.jpeg *.webp)")
        if not path:
            return
        self._push()
        slide = self.current_slide()
        slide.background.mode = "image"
        slide.background.image = path
        slide.background.fit = "cover"
        slide.background.opacity = 1
        self.refresh_thumbs()

    def insert_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Bild", "", "Bilder (*.png *.jpg *.jpeg *.webp *.bmp)")
        if path:
            self._push()
            place_on_slide(self.current_slide(), path, 0.1, 0.1)
            self.refresh_thumbs()

    def insert_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Video", "", "Video (*.mp4 *.mov *.webm *.mkv)")
        if path:
            self._push()
            place_on_slide(self.current_slide(), path, 0.12, 0.12)
            self.refresh_thumbs()

    def insert_document(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Dokument", "", "Text (*.txt *.md *.pdf)")
        if not path:
            return
        self._push()
        text = read_text_file(path)
        generated = slides_from_text(text, Path(path).stem)
        self.presentation.slides.extend(generated.slides)
        self.refresh_thumbs()

    def _drop_files(self, paths: list, x: float, y: float) -> None:
        self._push()
        for path in paths:
            kind = classify(path)
            if kind == "pptx":
                imported = import_pptx(path)
                self.presentation.slides.extend(imported.slides)
            elif kind == "odp":
                imported = import_odp(path)
                self.presentation.slides.extend(imported.slides)
            elif kind == "text" and Path(path).stat().st_size > 800:
                text = read_text_file(path)
                self.presentation.slides.extend(slides_from_text(text, Path(path).stem).slides)
            elif kind == "table":
                obj = SlideObject(id=new_id(), kind="chart", x=x, y=y, w=0.6, h=0.45, name="diagramm", props={})
                bind_chart(obj, path)
                self.current_slide().objects.append(obj)
            elif kind == "obj":
                png = render_png(obj_text=Path(path).read_text(encoding="utf-8", errors="replace"))
                self._insert_png(png, "modell")
            else:
                place_on_slide(self.current_slide(), path, x, y)
        self.refresh_thumbs()

    def _drop_text(self, text: str, x: float, y: float) -> None:
        self._push()
        if len(text) > 600:
            self.presentation.slides.extend(slides_from_text(text, "Text").slides)
        else:
            self.current_slide().objects.append(
                SlideObject(
                    id=new_id(),
                    kind="text",
                    x=x,
                    y=y,
                    w=0.4,
                    h=0.2,
                    name="text",
                    props={"text": text, "font_size": 20, "color": "#1B1F2A", "font_family": "Segoe UI"},
                )
            )
        self.refresh_thumbs()

    def _video_message(self, message: str) -> None:
        if message.startswith("video:"):
            show_text(self, "Video", "Datei: " + message[6:] + "\nDie Wiedergabe nutzt den Systemplayer, sobald Qt Multimedia verfügbar ist.")

    def filter_image(self, mode: str) -> None:
        objects = [obj for obj in self.selected_objects() if obj.kind == "image" and obj.props.get("path")]
        if not objects:
            return
        self._push()
        folder = media_folder(self.path)
        for obj in objects:
            source = obj.props.get("render_path") or obj.props["path"]
            if mode == "bright":
                data = adjust(source, brightness=0.08, contrast=1.05)
            elif mode == "knockout":
                data = knockout_corners(source)
            elif mode == "gray":
                data = adjust(source, grayscale=True)
            else:
                data = color_filter(source, mode)
            target = folder / f"{new_id()}.png"
            target.write_bytes(data)
            clear_image_cache(obj.props.get("render_path"))
            obj.props["render_path"] = str(target)
        self.refresh_thumbs()

    def align(self, mode: str) -> None:
        objects = self.selected_objects()
        if len(objects) < 2:
            return
        self._push()
        align_objects(objects, mode)
        self.refresh_thumbs()

    def edit_brand(self) -> None:
        dialog = BrandDialog(self, self.presentation.brand)
        if dialog.exec():
            self._push()
            self.presentation.brand = dialog.value()

    def apply_palette(self) -> None:
        seed = (self.presentation.brand.get("colors") or ["#0B63E5"])[0]
        colors = dotnet_palette(seed)
        self._push()
        self.presentation.brand["colors"] = colors
        show_text(self, "Farbreihe", "\n".join(colors))

    def bind_data(self) -> None:
        dialog = DataDialog(self)
        if not dialog.exec() or not dialog.path.text().strip():
            return
        self._push()
        obj = SlideObject(id=new_id(), kind="chart", x=0.1, y=0.25, w=0.8, h=0.55, name="diagramm", props={})
        bind_chart(obj, dialog.path.text().strip(), dialog.sheet.text().strip() or None)
        self.current_slide().objects.append(obj)
        self.refresh_thumbs()

    def refresh_data(self) -> None:
        self._push()
        count = refresh_bindings(self.presentation)
        self.refresh_thumbs()
        self.statusBar().showMessage(f"{count} Diagramme aktualisiert")

    def run_macro_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Makro", "", "Python (*.py)")
        if not path:
            return
        answer = QMessageBox.question(self, "Makro", "Lokales Makro ausführen? Es sieht nur die Präsentation, nicht das Dateisystem.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._push()
        try:
            message = run_macro(path, self.presentation)
        except MacroError as exc:
            show_text(self, "Makro", str(exc))
            return
        self.refresh_thumbs()
        show_text(self, "Makro", message)

    def add_comment(self) -> None:
        text, ok = QInputDialog.getMultiLineText(self, "Kommentar", "Kommentar zur Folie")
        if ok and text.strip():
            from officedisplay.model.presentation import Comment

            self._push()
            self.current_slide().comments.append(Comment(id=new_id(), text=text.strip()))
            self.statusBar().showMessage(f"{len(self.current_slide().comments)} Kommentare")

    def insert_3d(self) -> None:
        dialog = ThreeDialog(self)
        if not dialog.exec():
            return
        obj_text = None
        if dialog.obj.text().strip():
            obj_text = Path(dialog.obj.text().strip()).read_text(encoding="utf-8", errors="replace")
        png = render_png(dialog.kind.currentText(), obj_text=obj_text)
        self._push()
        self._insert_png(png, "modell3d")
        self.refresh_thumbs()

    def _insert_png(self, data: bytes, name: str) -> None:
        folder = media_folder(self.path)
        target = folder / f"{new_id()}.png"
        target.write_bytes(data)
        self.current_slide().objects.append(
            SlideObject(id=new_id(), kind="model3d", x=0.3, y=0.25, w=0.4, h=0.4, name=name, props={"path": str(target)})
        )

    def open_ai(self) -> None:
        dialog = AiDialog(self)
        if not dialog.exec():
            return
        action = dialog.action
        try:
            if action == "offline":
                self._push()
                self.presentation = generate_deck(dialog.prompt.text())
                self.canvas.set_presentation(self.presentation, 0)
            elif action == "command":
                self._push()
                message = apply_command(self.presentation, self.current_slide(), dialog.command.text())
                show_text(self, "Befehl", message)
            elif action == "coach":
                self.speech_coach()
            elif action == "document":
                path, _ = QFileDialog.getOpenFileName(self, "Quelle", "", "Dokumente (*.txt *.md *.pdf)")
                if path:
                    self._push()
                    generated = slides_from_text(read_text_file(path), Path(path).stem)
                    self.presentation = generated
                    self.canvas.set_presentation(self.presentation, 0)
            elif action == "inspect":
                self.inspect_model()
            elif action == "online":
                data = draft_deck(self._online_settings(), dialog.prompt.text())
                from officedisplay.ai.offline_design import deck_from_outline

                self._push()
                self.presentation = deck_from_outline(data["slides"], dialog.prompt.text()[:80] or "Online")
                self.canvas.set_presentation(self.presentation, 0)
            elif action == "rewrite":
                objects = [obj for obj in self.selected_objects() if obj.kind == "text"]
                if objects:
                    text = rewrite_text(
                        self._online_settings(),
                        str(objects[0].props.get("text") or ""),
                        dialog.command.text() or "kürzer",
                    )
                    self._push()
                    objects[0].props["text"] = text.strip()
            elif action == "image":
                self._store_generated_image(generate_image(self._online_settings(), dialog.prompt.text()))
        except (OnlineAIError, OSError, ValueError, KeyError) as exc:
            show_text(self, "KI", str(exc))
        self.refresh_thumbs()

    def _online_settings(self) -> OnlineAISettings:
        return OnlineAISettings(
            enabled=bool(self.prefs.get("online_enabled")),
            base_url=self.prefs.get("base_url") or "https://api.openai.com/v1",
            api_key=self.secrets.get("api_key") or "",
            model=self.prefs.get("model") or "gpt-4o-mini",
            image_model=self.prefs.get("image_model") or "dall-e-3",
            allow_images=bool(self.prefs.get("allow_images")),
        )

    def open_settings(self) -> None:
        dialog = SettingsDialog(self, self.prefs, self.secrets)
        if dialog.exec():
            prefs, secrets = dialog.values()
            self.prefs.update(prefs)
            self.secrets.update(secrets)
            self._save_prefs()
            save_secrets(self.secrets)
            self._pointer("Maus")

    def _store_generated_image(self, payload: dict) -> None:
        import base64
        import urllib.request

        data = (payload.get("data") or [{}])[0]
        raw = None
        if data.get("b64_json"):
            raw = base64.b64decode(data["b64_json"])
        elif data.get("url"):
            url = str(data["url"])
            if not url.startswith("https://"):
                raise OnlineAIError("Bild-URL ist nicht HTTPS.")
            with urllib.request.urlopen(url, timeout=60) as response:
                raw = response.read()
        if not raw:
            raise OnlineAIError("Keine Bilddaten in der Antwort.")
        self._push()
        folder = media_folder(self.path)
        target = folder / f"{new_id()}.png"
        target.write_bytes(raw)
        place_on_slide(self.current_slide(), str(target), 0.15, 0.15)

    def inspect_model(self) -> None:
        show_text(self, "Modell inspizieren", inspect_model())

    def speech_coach(self) -> None:
        minutes, ok = QInputDialog.getDouble(self, "Sprech-Coach", "Dauer in Minuten (0 = nur Textschätzung)", 0, 0, 180, 1)
        report = analyze_speech(self.current_slide().notes, None if not ok or minutes <= 0 else minutes * 60)
        lines = [
            f"Wörter: {report['words']}",
            f"Wörter pro Minute: {report['wpm']}",
            f"Geschätzte Dauer bei 130 WPM: {report['minutes']} min",
            f"Füllwörter ({report['filler_count']}): {', '.join(report['fillers']) or '–'}",
            f"Satzlängen: {report['sentence_lengths']}",
            f"Variation: {report['length_variation']}",
            "",
            *report["tips"],
        ]
        show_text(self, "Sprech-Coach", "\n".join(lines))

    def _align_text(self, align: str) -> None:
        self._mutate_text(lambda obj, _brand: obj.props.__setitem__("align", align))

    def _set_entrance(self, effect: str) -> None:
        objects = self.selected_objects()
        if not objects:
            return
        self._push()
        for obj in objects:
            obj.props["entrance"] = effect
        self.statusBar().showMessage(f"Eingangseffekt: {effect}")

    def edit_notes(self) -> None:
        text, ok = QInputDialog.getMultiLineText(self, "Sprechernotiz", "Notiz", self.current_slide().notes)
        if ok:
            self._push()
            self.current_slide().notes = text

    def edit_action(self) -> None:
        objects = self.selected_objects()
        if len(objects) != 1:
            show_text(self, "Aktion", "Bitte genau ein Objekt auswählen.")
            return
        kind, ok = QInputDialog.getItem(self, "Aktion", "Beim Klick in der Präsentation", ["keine", "gehe zu Folie", "Hinweis"], 0, False)
        if not ok or kind == "keine":
            if ok:
                objects[0].props.pop("action", None)
            return
        if kind == "gehe zu Folie":
            index, ok_index = QInputDialog.getInt(self, "Folie", "Ziel (1 = erste Folie)", 1, 1, len(self.presentation.slides))
            if ok_index:
                objects[0].props["action"] = {"type": "goto", "target": index - 1}
        else:
            text, ok_text = QInputDialog.getText(self, "Hinweis", "Text")
            if ok_text:
                objects[0].props["action"] = {"type": "popup", "text": text}

    def background_opacity(self) -> None:
        value, ok = QInputDialog.getInt(self, "Deckkraft", "Prozent", int(self.current_slide().background.opacity * 100), 5, 100)
        if ok:
            self._push()
            self.current_slide().background.opacity = value / 100
            self.refresh_thumbs()

    def background_fit(self) -> None:
        fit, ok = QInputDialog.getItem(self, "Hintergrundbild", "Anpassung", ["cover", "contain", "tile"], 0, False)
        if ok:
            self._push()
            self.current_slide().background.fit = fit
            self.refresh_thumbs()

    def enable_sync(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Lokaler Ordner für den JSON-Abgleich")
        if not folder:
            return
        from PySide6.QtCore import QTimer

        self.sync_dir = Path(folder)
        self._sync_publish()
        timer = getattr(self, "sync_timer", None)
        if timer is None:
            self.sync_timer = QTimer(self)
            self.sync_timer.timeout.connect(self._sync_poll)
            self.sync_timer.start(2000)
        self.statusBar().showMessage(f"Lokaler Sync: {folder}")

    def _sync_publish(self) -> None:
        folder = getattr(self, "sync_dir", None)
        if not folder:
            return
        path = Path(folder) / "deck.json"
        path.write_text(json.dumps(self.presentation.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        self._sync_mtime = path.stat().st_mtime

    def _sync_poll(self) -> None:
        folder = getattr(self, "sync_dir", None)
        if not folder:
            return
        path = Path(folder) / "deck.json"
        if not path.is_file():
            return
        mtime = path.stat().st_mtime
        if mtime <= getattr(self, "_sync_mtime", 0) + 0.001:
            return
        self.presentation = Presentation.from_dict(json.loads(path.read_text(encoding="utf-8")))
        self._sync_mtime = mtime
        self.canvas.set_presentation(self.presentation, min(self.canvas.slide_index, len(self.presentation.slides) - 1))
        self.refresh_thumbs()

    def open_camera(self) -> None:
        try:
            from PySide6.QtMultimedia import QCamera, QMediaCaptureSession, QMediaDevices
            from PySide6.QtMultimediaWidgets import QVideoWidget
            from PySide6.QtWidgets import QDialog

            cameras = QMediaDevices.videoInputs()
            if not cameras:
                raise RuntimeError("kein Gerät")
            dialog = QDialog(self)
            dialog.setWindowTitle("Kamera")
            view = QVideoWidget(dialog)
            camera = QCamera(cameras[0])
            session = QMediaCaptureSession(dialog)
            session.setCamera(camera)
            session.setVideoOutput(view)
            layout = QVBoxLayout(dialog)
            layout.addWidget(view)
            camera.start()
            dialog.exec()
            camera.stop()
        except Exception:
            show_text(
                self,
                "Kamera",
                "Keine Kamera verfügbar. Offline-Fallback: Qt findet kein Aufnahmegerät. "
                "Einen Cloud-Videochat gibt es in Office Display nicht.",
            )

    def preview_entrance(self) -> None:
        from PySide6.QtCore import QTimer
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import QDialog, QLabel

        from officedisplay.design.animate import apply_entrance

        dialog = QDialog(self)
        dialog.setWindowTitle("Eingang")
        label = QLabel()
        layout = QVBoxLayout(dialog)
        layout.addWidget(label)
        state = {"t": 0.0}
        source = self.current_slide()

        def tick():
            state["t"] += 0.08
            if state["t"] >= 1:
                timer.stop()
            slide = apply_entrance(source, min(1.0, state["t"]))
            label.setPixmap(QPixmap.fromImage(render_thumb(self.presentation, slide, 800)))

        timer = QTimer(dialog)
        timer.timeout.connect(tick)
        timer.start(40)
        tick()
        dialog.exec()

    def open_library(self) -> None:
        dialog = LibraryDialog(self)
        if not dialog.exec():
            return
        action = dialog.action
        if action == "template":
            item = dialog.templates.currentItem()
            if item is None:
                return
            self._push()
            apply_template(self.presentation, item.text())
            self.canvas.set_presentation(self.presentation, 0)
        elif action == "resize":
            size = RESIZE_PRESETS[dialog.sizes.currentText()]
            self._push()
            magic_resize(self.presentation, size[0], size[1])
        elif action == "element":
            self._push()
            self.current_slide().objects.append(element(dialog.elements.currentText()))
        else:
            try:
                client = CanvaClient(
                    self.secrets.get("canva_token") or "",
                    self.prefs.get("canva_base") or "https://api.canva.com/rest/v1",
                )
                if action == "list":
                    show_text(self, "Canva", json.dumps(client.list_brand_templates(), ensure_ascii=False, indent=2)[:4000])
                elif action == "autofill":
                    fields = parse_json_field(dialog.fields.toPlainText())
                    job = client.create_autofill(dialog.template_id.text().strip(), fields, self.presentation.title)
                    show_text(self, "Canva Autofill", json.dumps(job, ensure_ascii=False, indent=2)[:4000])
                elif action == "export":
                    job = client.create_export(dialog.template_id.text().strip(), "pptx")
                    show_text(
                        self,
                        "Canva Export",
                        json.dumps(job, ensure_ascii=False, indent=2)[:2000]
                        + "\n\nFertige PPTX danach über Datei → Import PPTX laden.",
                    )
            except (CanvaAPIError, ValueError, json.JSONDecodeError) as exc:
                show_text(self, "Canva", str(exc))
        self.refresh_thumbs()

    def present(self) -> None:
        PresenterDialog(self, self).exec()

    def open_zui(self) -> None:
        dialog = ZuiDialog(self, self)
        if dialog.exec():
            self.canvas.set_index(dialog.chosen)
            self.refresh_thumbs()

    def preview_morph(self) -> None:
        index = self.canvas.slide_index
        if index + 1 >= len(self.presentation.slides):
            show_text(self, "Morph", "Es braucht eine folgende Folie. Gleich benannte Objekte wandern.")
            return
        from PySide6.QtCore import QTimer
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import QDialog, QLabel

        dialog = QDialog(self)
        dialog.setWindowTitle("Morph")
        label = QLabel()
        layout = QVBoxLayout(dialog)
        layout.addWidget(label)
        state = {"t": 0.0}

        def tick():
            state["t"] += 0.08
            if state["t"] >= 1:
                timer.stop()
            slide = morph_slide(self.presentation.slides[index], self.presentation.slides[index + 1], min(1, state["t"]))
            image = render_thumb(self.presentation, slide, 800)
            label.setPixmap(QPixmap.fromImage(image))

        timer = QTimer(dialog)
        timer.timeout.connect(tick)
        timer.start(40)
        tick()
        dialog.exec()

    def save_analytics(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Verweildauer", "verweildauer.json", "JSON (*.json)")
        if path:
            self.dwell.save(path)

    def open_help(self) -> None:
        text = help_path().read_text(encoding="utf-8") if help_path().is_file() else "Hilfe-Datei fehlt."
        HelpDialog(self, text).exec()

    def open_about(self) -> None:
        AboutDialog(self).exec()
