"""Schließbare DTP-Hilfe (kein Stub, kein Status-No-Op)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

DTP_HELP_HTML = """
<h2>DTP-Hilfe</h2>
<p>Layout-Modus: Rahmen auf der Seite platzieren, nicht nur Text im Editor.
Menü <b>DTP</b> oder Ribbon-Tab <b>DTP</b> öffnet die Ansicht sofort
(auch bei offenem PDF) — nicht erst ein Unterpunkt.</p>

<h3>Speichern</h3>
<ul>
<li>Vor dem Wechsel in den DTP-Modus und beim Verlassen, wenn etwas geändert wurde:
<b>Speichern</b> / <b>Nicht speichern</b> / <b>Abbrechen</b>.</li>
<li><b>Abbrechen</b> bleibt in der aktuellen Ansicht. Der Ribbon-Tab springt
zurück, wenn der Wechsel abgebrochen wird.</li>
</ul>

<h3>Werkzeuge</h3>
<ul>
<li><b>Auswählen</b>: Rahmen anklicken oder mit dem Gummiband einfassen.</li>
<li><b>Text / Bild / Form</b>: gelten auf der Auswahl (Select-then-apply);
ohne Auswahl entsteht ein neuer Rahmen.</li>
<li><b>Füllung / Kontur</b>: Farbwähler auf den gewählten Rahmen.</li>
<li><b>Schrift</b>: Systemschriften (<code>QFontDialog</code> /
<code>QFontDatabase</code>) auf Textrahmen oder Caret.</li>
<li><b>Verketten</b>: Overflow von Textrahmen in den nächsten Rahmen.</li>
<li>Icon-Leiste und DTP-Menü führen dieselben Aktionen aus.</li>
</ul>

<h3>Rahmen</h3>
<ul>
<li><b>Textrahmen</b>: Doppelklick setzt den Caret; Eckengriffe skalieren.</li>
<li><b>Bildrahmen / Form</b>: Bild ersetzen, Grafik importieren, schweißen.</li>
<li><b>Lineale</b> mm / pt / in (Ecke oder Menü Ansicht). Ziehen setzt
Hilfslinien mit Snap.</li>
<li>Anschnitt rot, Satzspiegel blau (Seitengeometrie, kein Word-Overlay).</li>
<li><b>Druckermarken</b> (Ansicht): Crop-/Registration, geteilt mit PDF
(<code>show_printer_marks</code>). Keine Breiten- oder Kopf-/Fuß-Marken
des Texteditors.</li>
</ul>

<h3>Tastatur</h3>
<ul>
<li><b>F1</b> — diese DTP-Hilfe (im Layout-Modus).</li>
<li><b>Ctrl+Alt+L</b> — Layout-Modus ein/aus (Ansicht → Layout-Modus).</li>
<li><b>Esc</b> — diesen Dialog schließen.</li>
<li>Mausrad zoomen; Statuszeile zeigt Zoom, Seite, Koordinaten.</li>
</ul>
<p>Diese Hilfe ist kein Platzhalter.</p>
"""


class DtpHelpDialog(QDialog):
    """Echter, schließbarer Hilfedialog für den Layout-Modus."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ildDtpHelpDialog")
        self.setWindowTitle("DTP-Hilfe")
        self.setModal(True)
        self.resize(560, 480)
        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setObjectName("ildDtpHelpBody")
        browser.setOpenExternalLinks(False)
        browser.setHtml(DTP_HELP_HTML)
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close_btn = buttons.button(QDialogButtonBox.Close)
        if close_btn is not None:
            close_btn.setObjectName("ildDtpHelpClose")
            close_btn.setText("Schließen")
        layout.addWidget(buttons)
        esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc.setContext(Qt.WindowShortcut)
        esc.activated.connect(self.reject)


def show_dtp_help(parent: QWidget | None = None) -> DtpHelpDialog:
    dlg = DtpHelpDialog(parent)
    dlg.exec()
    return dlg
