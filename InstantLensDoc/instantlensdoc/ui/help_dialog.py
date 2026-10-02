"""Hilfe- und About-Dialoge."""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
)

from instantlensdoc import __version__
from instantlensdoc.config import CONTACT_EMAIL, DISPLAY_NAME, ROOT, VENDOR, icon_paths_for_qt
from instantlensdoc.core.logging_setup import log_dir


HELP_HTML = f"""
<h2>InstantLens Doc — Hilfe</h2>
<p>Moderne Textverarbeitung mit PDF-Annotator, OCR-Bridge und Formulargenerator.</p>
<h3>Erste Schritte</h3>
<ul>
<li><b>Datei → Öffnen</b>: TXT, MD, HTML, DOCX, PDF, Bilder</li>
<li><b>Extras → Einstellungen</b>: Theme, <b>UI-Sprache DE/EN</b>, OCR, Export-Qualität,
    <b>Standard-Zoom</b>, <b>Autosave-Intervall</b>, Soft-Wrap, <b>Sonderzeichen anzeigen</b>,
    optional <b>Trailing Whitespace trimmen</b>, optional <b>Whitespace trim on paste</b>,
    optional <b>Bracket-Match Highlight</b>,
    optional <b>Minimieren in System-Tray</b>,
    optional <b>Backup .bak beim Speichern</b>, <b>Seitengröße-Einheit mm/inch</b>,
    optional <b>letzte Session beim Start</b>, <b>PDF-Toolbar-Gruppen</b> ein-/ausblenden,
    optional <b>PDF Zwei-Seiten-Ansicht (Spread)</b>, optional <b>PDF Continuous Scroll</b>,
    Update-Hinweis (nur wenn aktiv), Pfade;
    <b>Auf Standard zurücksetzen</b></li>
<li><b>Datei → Zuletzt geöffnet</b>: Menü + Seitenleiste (persistiert)</li>
<li><b>Datei → Speichern unter</b> (Ctrl+Shift+S): Text → Dokument; PDF → Annotation-Sidecar wählen (PDF unverändert)</li>
<li><b>Datei → Alles speichern</b> (Ctrl+Alt+Shift+S): aktuelles Doc + PDF-Sidecars offener Tabs</li>
<li><b>Datei → Als Kopie speichern</b> (Ctrl+Alt+S): PDF + Sidecar kopieren (Doc bleibt offen); Editor → Speichern unter</li>
<li><b>Datei → Arbeitsverzeichnis öffnen</b> (Ctrl+Shift+E): Ordner der aktuellen Datei bzw. Prozess-CWD</li>
<li><b>Datei → Projekt-Ordner</b>: Workspace wählen (letzte 5); Dialoge starten im aktiven Ordner</li>
<li><b>Datei → Exportieren</b>: Editor-Inhalt als HTML, DOCX oder PDF (zuletzt genutzter Ordner wird gemerkt);
    <b>Export-Profil</b> speichern/anwenden (DPI / Format / Ziel)</li>
<li><b>Datei → Drucken</b> (Ctrl+P): Editor oder aktuelle PDF-Seite (Qt Print)</li>
<li><b>Seitenleiste</b>: Suche (inkl. letzte Suchbegriffe), „Alle Docs“-Volltext, Zuletzt geöffnet, Dokumente,
    Lesezeichen/Outline (+/− hinzufügen/löschen), <b>Annotationen</b> (klickbar, <b>nach Seite gruppiert</b>,
    <b>Filter nach Typ</b>, <b>Textsuche in der Liste</b> (optional <b>Regex</b>), <b>Statistik je Typ</b>,
    <b>Farben-Chips klickbar filtern</b>, <b>Zeitstempel</b>,
    <b>Filter nur aktuelle Seite</b>), Markierungen/Treffer</li>
<li><b>Bearbeiten → Rückgängig/Wiederholen</b>: Editor-Text <i>oder</i> PDF-Annotationen/Overlay-Text (Ctrl+Z / Ctrl+Y);
    Statusleisten-Hint „Ctrl+Z · Letzte Aktion rückgängig“</li>
<li><b>Bearbeiten → Suchen und Ersetzen</b> (Ctrl+R): Find/Replace im Texteditor</li>
<li><b>Bearbeiten → Gehe zu Zeile / Seite</b> (Ctrl+G): Editor → Zeile; PDF → Seite (auch PDF → Gehe zu Seite…, Ctrl+Shift+G)</li>
<li><b>Datei → Tab duplizieren</b> (Ctrl+Shift+T): Editor-Inhalt als neues Dokument klonen;
    <b>Dateien vergleichen</b> (Ctrl+Alt+D): zwei Tabs Side-by-Side (Zeilen-Diff);
    <b>Erneut öffnen</b> (Ctrl+Alt+Shift+O): Datei vom Datenträger neu laden</li>
<li><b>Bearbeiten → Zeile duplizieren</b> (Ctrl+D): aktuelle Zeile / Auswahl darunter kopieren</li>
<li><b>Bearbeiten → Zeile verschieben</b> (Alt+Up / Alt+Down)</li>
<li><b>Bearbeiten → Zeilen sortieren (A–Z)</b> (Ctrl+Shift+O): Auswahl alphabetisch</li>
<li><b>Bearbeiten → Auswahl markieren</b> (Ctrl+H): Markierung im Editor + Eintrag in der Seitenleiste</li>
<li><b>Bearbeiten → Groß-/Kleinschreibung umschalten</b> (Ctrl+Shift+U): Auswahl GROSS → klein → Titel</li>
<li><b>Bearbeiten → Alles groß-/kleinschreiben</b> (Ctrl+Alt+Shift+U / L): gesamte Datei</li>
<li><b>Bearbeiten → Textbausteine</b>: 3 gespeicherte Snippets (Einfügen Ctrl+Alt+1..3; Auswahl → Slot)</li>
<li><b>Bearbeiten → Zwischenablage-Verlauf</b>: letzte 3 eingefügten Textschnipsel erneut einfügen</li>
<li><b>Datei → Neu</b>: leeres Dokument oder Vorlage <b>Brief</b> / <b>Notiz</b></li>
<li><b>Bearbeiten → Einrückung erhöhen/verringern</b> (Ctrl+] / Ctrl+[; Tab / Shift+Tab Block)</li>
<li><b>Ansicht</b>: Zoom +/−, Seite einpassen (Ctrl+0), Breite (Ctrl+9), Höhe (Ctrl+8), 100&nbsp;% (Ctrl+1);
    <b>Präsentationsmodus</b> (F5 Vollbild, Pfeiltasten); <b>Hell/Dunkel</b>-Design umschalten; optionale <b>Zeilennummern</b>; <b>Markdown-Vorschau</b> (Split, Ctrl+Shift+M);
    <b>Soft-Wrap</b>; <b>Sonderzeichen anzeigen</b> (Ctrl+Shift+.);
    <b>PDF Graustufen</b>; <b>PDF Nachtmodus</b> (Invert-Ansicht, nur Darstellung);
    <b>Zwei-Seiten-Ansicht (Spread)</b> (Ctrl+2 / Toolbar 2S);
    <b>Continuous Scroll</b> (Ctrl+3 / Toolbar CS — Seiten untereinander, schließt Spread aus);
    <b>Seitenlabels</b> (römisch/arabisch) in Status/Toolbar wenn im PDF vorhanden;
    <b>Annotation-Layer</b> ein/aus (Ctrl+Shift+A);
    <b>Annotationen sperren</b> (Ctrl+Shift+L — nicht verschiebbar);
    <b>Seitenrahmen / CropBox</b> Overlay (Ctrl+Shift+B);
    <b>Druckermarken</b> Overlay (Ctrl+Alt+M)</li>
<li><b>Datei → Öffnen/Speichern mit Encoding</b>: UTF-8 oder Latin-1 für Textdateien (Standard in Einstellungen)</li>
<li><b>Drag &amp; Drop</b>: eine oder mehrere Dateien auf das Fenster ziehen → mehrere Tabs</li>
<li><b>Autosave</b>: Textdokumente (mit Pfad) und PDF-Annotationen — Intervall in Einstellungen</li>
<li><b>PDF</b>: Blättern, Zoom/Fit (debounced + Cache), <b>⟲/⟳ drehen</b> / <b>↔/↕ spiegeln</b> (speichert),
    <b>Graustufen</b> (Ansicht + Bild-Export), <b>Nachtmodus</b> (nur Ansicht, nicht speichern),
    <b>leere Seite / duplizieren</b>, Seite löschen, Seiten neu anordnen;
    <b>PDF-Links (http/https)</b> per Auswahl-Werkzeug / Ctrl+Klick öffnen;
    Annotationen: Highlight (Drag, <b>Selection→Highlight</b> über Text) + <b>Farben-Picker HL/Stift</b> + <b>3 Favoriten</b> + <b>Deckkraft α</b>, <b>Schwärzen/Redaction</b> (Drag + Preview „REDACT“ + Einbrennen-Dialog), Unterstreichen, Notiz, <b>Text-Overlay</b>,
    <b>Stempel-Bibliothek</b> (GENEHMIGT/ENTWURF/VERTRAULICH + Datum, <b>Rotation 90°</b>), Callout,
    <b>Rechteck / Linie / Pfeil / Lineal</b> —
    Sidecar <code>*.ildann.json</code> (v4 / <code>ildann-v4</code>, Auto-Save, Undo/Redo);
    JSON-Export PDF-Highlight-kompatibel (rects/quadPoints/colorRGB); CSV Export;
    JSON Import mit Schema-v4-Validierung (klare Fehlermeldung);
    <b>Textsuche</b> highlightet Treffer auf der aktuellen Seite;
    Doppelklick / Strg+Klick / <b>Ctrl+E</b> auf Notiz/Overlay zum Bearbeiten;
    <b>Ctrl+Alt+T</b> Annotation-Tags (frei, Sidebar-Filter);
    <b>Ctrl+Shift+D</b> Auswahl duplizieren; <b>Ctrl+Alt+C/V</b> Annotationen kopieren/einfügen (auch seitenübergreifend);
    Auswahl-Werkzeug: Annotationen per Drag verschieben (wenn nicht gesperrt);
    PDF → Text→Overlay / Overlay einbrennen / <b>Text Seite/alles → Editor</b> /
    <b>Seitenbild(er) → Editor</b>;
    Flatten/Bake mit Fortschrittsdialog (Abbrechen);
    <b>Signaturfeld</b> (Platzhalter) und <b>Signatur (Bild)</b> einfügen;
    <b>PDFs zusammenführen / teilen / Seitenbereich</b>;
    <b>Wasserzeichen / Seitennummern</b>;
    <b>Zwei PDFs vergleichen</b> (Seite neben Seite);
    <b>Passwort setzen/öffnen</b>; <b>Bildkompression</b> (Seiten neu als JPEG);
    <b>Metadaten bearbeiten</b>; <b>PDF bereinigen</b> (optional Metadaten strippen);
    <b>AcroForm-Formularfelder ausfüllen</b>; <b>Anhänge</b> auflisten/extrahieren;
    <b>Seitengröße / Zuschneiden</b> (Anzeige mm/inch, Statusleiste klickbar / Ctrl+Alt+U);
    Seite/Seiten als PNG/JPEG exportieren / Bild als neue Seite / Seite drucken; Annotation löschen (Auswahl/letzte, Entf); Statusleiste Seite/Größe/Zoom/Dateiname/Wörter; Thumbnails per Drag neu ordnen (<b>Lazy-Load</b>, Größe in Einstellungen);
    PDF als Kopie speichern; <b>Seitenbereich extrahieren</b> (von–bis → neues PDF);
    große PDFs: Warnung / Limits;
    <b>Seiten-Thumbnails</b> in der Sidebar</li>
<li><b>Datei → Schließen</b>: Speichern-Dialog bei ungespeicherten Änderungen</li>
<li><b>Hilfe → Auf Updates prüfen</b>: lokal immer; Online optional (offline OK)</li>
<li><b>Hilfe → Über InstantLens Doc</b>: Feature-Kurzliste + Link zu FEATURES.md</li>
<li><b>Hilfe → Logordner öffnen</b>: Crash-/App-Logs im Dateimanager</li>
<li><b>Zwischenablage</b>: Bild einfügen (Editor Ctrl+Shift+V / PDF Strg+V) — Stempel oder neue Seite</li>
<li><b>Session</b>: Offene Dokumente (Sidebar-Liste) werden beim Beenden gespeichert;
    Wiederherstellung beim Start optional in den Einstellungen</li>
<li><b>Logging</b>: Datei unter <code>%APPDATA%/InstantLensDoc/logs/</code> (Windows) bzw. <code>~/.config/InstantLensDoc/logs/</code></li>
<li><b>Tastaturhilfe</b>: Hilfe → Tastaturhilfe (F1); Cheat-Sheet als PDF exportieren</li>
<li><b>Extras → Batch-Konvertierung</b>: Ordner → PDF oder OCR</li>
<li><b>Einfügen → Verketteter Textrahmen</b>: Overflow fließt in den Folgeahmen</li>
<li><b>OCR</b>: Extras → OCR (Seite/Bild) oder <b>OCR gesamtes PDF</b> (Batch mit Fortschritt/Abbrechen) —
    Sprach-Presets + Modus „editierbarer Text“ oder
    „durchsuchbares Bild“ (PDF + <code>*.ildocr.txt</code>); Tabellen-Heuristik als Markdown wo möglich.
    Ohne Tesseract: Install-Hinweis mit Link
    (<a href="https://github.com/UB-Mannheim/tesseract/wiki">UB-Mannheim Wiki</a>,
    <code>winget install UB-Mannheim.TesseractOCR</code>)</li>
<li><b>Formulare</b>: Extras → Formulargenerator — mehr Feldtypen, Definition speichern/laden
    (<code>*.ildform.json</code>), Live-Vorschau, Export HTML/PDF</li>
<li><b>Build (Windows)</b>: <code>build-windows.ps1</code> — PyInstaller App + Keygen</li>
<li><b>Installer</b>: Desktop-Verknüpfung + Startmenü-Gruppe (siehe Inno-Hinweis)</li>
<li><b>Lizenz</b>: Statusleiste (farbig; bei &lt;7 Tagen Restlaufzeit prominent) + Hilfe → Lizenz — Trial 4 Wochen, Keys 30+2 Tage</li>
<li><b>Keygen</b>: <code>run-keygen.bat</code> / <code>python -m keygen --gui</code>;
    Installer-EXE: <code>{{app}}/InstantLensKeygen.exe</code> (siehe <code>keygen/README.md</code>)</li>
</ul>
<h3>PDF-Modul</h3>
<p>Das Paket <code>ild_pdf</code> kann von anderen Programmen genutzt werden (pypdfium2, kein Poppler).
Beispiel: <code>examples/ild_pdf_demo.py</code>. API: <code>ild_pdf/README.md</code>.</p>
<h3>Sync / Update</h3>
<p>Windows: Repo-Skript <code>scripts/sync-ild.ps1</code> bzw. Store <code>docs/sync-ild.ps1</code> — Branch oder Zip nach
<code>D:\\AI_Temp\\InstantLensDoc</code>, pip, optional Start. Eigenes Icon in <code>assets</code> bleibt erhalten.</p>
<h3>Geplante Features</h3>
<p>KI-Assistent, Cloud-Sync, Stylus/Palm Rejection, 3D u. a. sind im Menü als „Geplant“ markiert
(Stub {__version__}) — siehe FEATURES.md.</p>
"""


def open_log_folder(parent=None) -> bool:
    """Logordner im Dateimanager öffnen; True bei Erfolg."""
    path = log_dir()
    ok = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    if not ok and parent is not None:
        QMessageBox.information(
            parent,
            "Logordner",
            f"Logordner konnte nicht geöffnet werden.\nPfad:\n{path}",
        )
    return bool(ok)


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hilfe")
        self.resize(580, 480)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        browser = QTextBrowser()
        browser.setHtml(HELP_HTML)
        tabs.addTab(browser, "Bedienung")

        features_path = ROOT / "FEATURES.md"
        feat = QTextBrowser()
        if features_path.exists():
            feat.setPlainText(features_path.read_text(encoding="utf-8"))
        else:
            feat.setPlainText("FEATURES.md nicht gefunden.")
        tabs.addTab(feat, "Features")
        layout.addWidget(tabs)

        btn_row = QHBoxLayout()
        btn_logs = QPushButton("Logordner öffnen")
        btn_logs.setToolTip("Crash-/App-Logordner im Dateimanager öffnen")
        btn_logs.clicked.connect(lambda: open_log_folder(self))
        btn_row.addWidget(btn_logs)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.clicked.connect(self.accept)
        layout.addWidget(buttons)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{DISPLAY_NAME} {__version__}")
        icon = QIcon()
        for p in icon_paths_for_qt():
            icon.addFile(str(p))
        if not icon.isNull():
            self.setWindowIcon(icon)
        layout = QVBoxLayout(self)
        icon_lbl = QLabel()
        if not icon.isNull():
            icon_lbl.setPixmap(icon.pixmap(64, 64))
            layout.addWidget(icon_lbl)
        layout.addWidget(
            QLabel(
                f"<h2>{DISPLAY_NAME} {__version__}</h2>"
                f"<p>Version {__version__}<br>"
                f"Hersteller: {VENDOR}<br>"
                f"Kontakt: {CONTACT_EMAIL}</p>"
                f"<p>PDF-Engine: pypdfium2 / PDFium (lizenzfreundlich)</p>"
                f"<p>Icon: assets/app.ico · assets/icon.png</p>"
            )
        )
        # Keygen-Hinweis bei aktiver Trial-Lizenz
        trial_hint = ""
        try:
            from instantlensdoc.license import LicenseManager

            st = LicenseManager().status()
            if st.mode == "trial":
                rem = st.days_remaining
                trial_hint = (
                    f"<p style='background:#FFF3CD;padding:8px;border:1px solid #E0C36A;'>"
                    f"<b>Testversion</b> — noch {rem} Tag(e).<br>"
                    f"Lizenzschlüssel erzeugen: <code>run-keygen.bat</code> bzw. "
                    f"<code>python -m keygen --gui</code> "
                    f"(Installer: <code>InstantLensKeygen.exe</code>).<br>"
                    f"Neuen Key anfordern: <a href='mailto:{CONTACT_EMAIL}'>{CONTACT_EMAIL}</a>"
                    f"</p>"
                )
        except Exception:
            trial_hint = ""
        if trial_hint:
            hint_lbl = QLabel(trial_hint)
            hint_lbl.setWordWrap(True)
            hint_lbl.setOpenExternalLinks(True)
            layout.addWidget(hint_lbl)
        features_short = QLabel(
            "<h3>Features (Kurz)</h3>"
            "<ul>"
            "<li>PDF lesen/annotieren (Highlight, Notiz, Stempel, Formen) · Sidecar v4</li>"
            "<li>Seitenlabels (römisch/arabisch), Continuous Scroll, Spread, CropBox</li>"
            "<li>Editor: Find/Replace, Snippets, Bracket-Match, Zwischenablage-Verlauf, Minimap</li>"
            "<li>OCR-Bridge (Seite + gesamtes PDF), Formulargenerator, Batch, Export</li>"
            "<li>Annotation-Tags, Kommentar-Bericht TXT/MD, Farbe Palette-Zyklus</li>"
            "<li>Selection→Highlight, Ann.-Regex, Datei-Vergleich, Export-Profil</li>"
            "<li>Lizenz Trial/Keys · Stubs: KI, Cloud, Stylus, 3D</li>"
            "</ul>"
            "<p>Vollständige Liste: FEATURES.md</p>"
        )
        features_short.setWordWrap(True)
        features_short.setOpenExternalLinks(False)
        layout.addWidget(features_short)

        btn_row = QHBoxLayout()
        btn_features = QPushButton("FEATURES.md öffnen…")
        btn_features.setToolTip("FEATURE-Liste im Standard-Editor / Dateimanager öffnen")
        btn_features.clicked.connect(self._open_features_md)
        btn_row.addWidget(btn_features)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _open_features_md(self) -> None:
        path = ROOT / "FEATURES.md"
        if not path.is_file():
            QMessageBox.information(
                self,
                "FEATURES.md",
                f"FEATURES.md nicht gefunden:\n{path}",
            )
            return
        ok = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        if not ok:
            QMessageBox.information(
                self,
                "FEATURES.md",
                f"Konnte FEATURES.md nicht öffnen.\nPfad:\n{path}",
            )
