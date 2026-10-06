## 2.6.59 - Release: Word-Suite, PDF-Menü, OCR, DTP, Ribbon

Pack `InstantLensDoc-2.6.59-pack.zip`; VERSION **2.6.59**. HEAD `8f01af3` (Ersatzzeichen) auf Chrome/Klick `d1e74c6`. Nach 2.6.58-Pack (`db9ef25`).

- **Windows-Pfade:** Copy Path / Status / Recent / Split-Log nutzen native `\\` (`D:\\AI_Temp\\file.pdf`); Öffnen/Speichern akzeptieren `/` und `\\`. Linux unverändert. Kein Versionsbump.
- **PDF-Menü live:** Klick eine Spalte; Einträge enabled bei offenem PDF-Tab oder Geschwister-PDF; jeder Slot Dialog oder Dateiänderung (`_bind_pdf_action` / `_pdf_menu_call`).
- **OCR Word-Suite:** Absätze/Ausrichtung/Listen, Seitenlayout, Kopf/Fuß nicht im Body, Feld-Tokens, Formatvorlagen und Tabellen ohne Steuerzeichen.
- **DTP:** Lineale mm/pt/in mit Hilfslinien; Werkzeuge/Füllung/Kontur/Systemschriften auf der Auswahl; **Schriftfarbe** (`QColorDialog`) auf Textauswahl oder Textrahmen. Ribbon-Tab/Menü **DTP** schaltet Lineale/Rahmen **im selben Dokumentfenster** ein (keine zweite DTP-Bühne; Word-Menüs und Ribbon **Start / Einfügen / Layout** bleiben). DTP-Eigenschaften (Werkzeuge/Farbe/Ebenen/Hilfe) in der **rechten Werkzeugspalte** mit Stiften/Pinsel. **DTP-Hilfe** über Hilfe-Menü, F1 und rechte Spalte (schließbares Fenster). Bei geänderten Layouts **Speichern / Nicht speichern / Abbrechen**. Druckermarken (Crop/Registration) teilen `show_printer_marks` mit PDF; Satzspiegel bleibt blaue Seitengeometrie — keine Word-Breiten-/Kopf-/Fuß-Overlays. **Overlays/Formen/Stempel** wählbar, per Ziehen verschiebbar, 8 Griffe zur Größe, Doppelklick zum Editieren (Text/Eigenschaften); Gummiband auf leerer Fläche; Undo/Redo; Schreibschutz sperrt sie. Textstempel mit/ohne Rahmen, nur Schrift, Schatten, Outline (PDF-Vektor + DTP-Rahmen, nicht nur Bitmap).
- **Word-Chrome:** Klassisch (Pull-down) / Ribbon / Kombiniert ohne Dokumentverlust; Ribbon-Overflow und Chrome-Modi klicken dieselben Pulldown-QActions.
- **Absatz / Seitenlayout / Kopf / Fuß / Ersatzzeichen:** echte Dialoge auf den bestehenden Menüs `menuAbsatz` / `menuSeitenlayout`; Builtin-Tokens plus frei definierbare Felder.
- **Formatvorlagen, Tabellen, Serienbrief:** Ribbon und Pulldown teilen QActions; Tabellen-Dialog; Seriendruck-Dialog.

Windows-Rebuild (Andreas Meyer), wie 2.6.58:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\sync-ild.ps1 -LocalPack D:\AI_Temp\InstantLensDoc-2.6.59-pack.zip -Dest D:\AI_Temp\InstantLensDoc-2659 -Swap -SkipStart
cd D:\AI_Temp\InstantLensDoc
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\install-ild.ps1
```

## 2.6.58 - Release: Auswahl-Gummiband per Mausziehen

Pack `InstantLensDoc-2.6.58-pack.zip`; VERSION **2.6.58**. HEAD `56d90a4` (Auswahl-Gummiband per Mausziehen). Nach 2.6.57-Pack (`42eebb7`).

- **Gummiband:** Leere Fläche ziehen selektiert alle sich schneidenden Annotationen (`rubber_band_finished` / `_on_rubber_band`); bereits ausgewähltes Objekt ziehen verschiebt. Klick bleibt Hit-Test. Test 7c ohne Fallback-Aufruf von `_on_rubber_band`.
- **DTP Layout-Modus:** Lineale mm/pt/in mit ziehbaren Hilfslinien; Werkzeuge Auswählen/Text/Bild/Form auf der Auswahl; Füllung/Kontur-Farbwähler; Schrift `QFontComboBox`/`QFontDialog`/`QFontDatabase` (kein Vorab-Enum im Dialog). Tests `test_dtp_2660.py`. Kein Versionsbump.

## 2.6.57 - Release: Scan-Timeout/eSCL-first, Bearbeiten-Klick, Strich auf aktuelles Objekt

Pack `InstantLensDoc-2.6.57-pack.zip`; VERSION **2.6.57**. HEAD `d7e0ad7` (Merge `cursor/scan-timeout-c22f` inkl. `6722fdf` / `51b66a7` / `39deb09`) plus `4a62b9a` Bearbeiten-Klick und `94f11d1` Strich auf aktuelles Objekt. Nach 2.6.56-Pack (`d617265`).

- **Scan-Timeout / Cache / eSCL-first:** Geräte-I/O im Worker (Watchdog 10 s, WIA 12 s); Menü **Geräte** sofort aus `device_cache.json`; Netzwerk/ECOSYS → eSCL/ScanTuxio zuerst, **kein** WIA-CommonDialog/`ShowAcquireImage`/Vorschau für Netzwerk-MFP.
- **WIA-Waisen:** `reap_orphan_scan_children` tötet `wiaacmgr` bei Timeout, Abbrechen, Quit, `atexit` und nächstem Start (auch ohne PID-Datei).
- **Bearbeiten-Klick:** Format/Bearbeiten eine Spalte (`SH_Menu_Scrollable`, kein `maxHeight`-Schnitt); Mausklick löst denselben Slot wie das Kürzel (`menu_click.py`).
- **Strich auf aktuelles Objekt:** Style-Ziele nur Live-Canvas-IDs der sichtbaren Seite (`_live_canvas_selected_ids` / `_prune_selection_to_visible_page`); Seitenwechsel leert alte Auswahl.

## 2.6.56 - Release: Menü-Audit 0 FAIL (DOCX/OCR/PDF)

Pack `InstantLensDoc-2.6.56-pack.zip`; VERSION **2.6.56**. HEAD nach 2.6.55-Pack (`2e87d56`) inkl. Menü-Audit `f5bca42` (0 FAIL auf DOCX/OCR/PDF).

- **Menü-Audit 0 FAIL:** Walk Datei…Hilfe + Ribbon/Kontext in DOCX, OCR-Text und PDF — PASS nur bei Dialog oder sichtbarem Effekt (`docs/instantlensdoc-menu-test-2655.md`).
- **Leere Voraussetzung:** Messwerte, Tabs, Zoom, Suche, Align, Extract, Bookmarks, OCR, Raster → FeatureDialog / `QMessageBox.question` statt Status-No-Op.
- **Enablement pro Zeile:** Audit-Walk synchronisiert Enablement vor jedem Trigger; Alles speichern und Tabs-links immer Dialog.

## 2.6.55 - Release: Select-then-tool, Bearbeiten-Formate, OCR-Word-Suite, DTP/Scribus, Menü-Audit

Pack `InstantLensDoc-2.6.55-pack.zip`; VERSION **2.6.55**. Arbeitspakete nach 2.6.54 (HEAD inkl. Menü-Audit `246a9e8`).

- **PDF-Objekte:** auswählbar; Werkzeug gilt auf der Auswahl (select-then-tool).
- **Bearbeiten:** echte Formate (nativ verdrahtet; Schriftart ohne blockierendes QFontDialog; ohne Auswahl auf das ganze Dokument).
- **OCR = Word-Suite:** OCR-/PDF-Text im gleichen Editor als rich `QTextDocument`; Auswahl oder gesamter Text.
- **DTP:** Spec Layout/Typo/Prepress/IO plus Scribus-Chrome (Menü, Icon-Leiste, mm-Lineale, Anschnitt rot / Satzspiegel blau).
- **Menütest:** PASS nur bei echtem Dialog oder sichtbarem Effekt (`docs/instantlensdoc-menu-test-2655.md`); `QAction.trigger()` allein zählt nicht.

## 2.6.54 - Release: PDF-Export/Minimap, Scan, Tabs, Annotationen, DTP, Menü-Audit

Sechs auf dem Branch gelandete Arbeitspakete. Pack `InstantLensDoc-2.6.54-pack.zip`; VERSION **2.6.54**.

- **PDF-Export / Diagnose / Minimap:** Speichern unter `.pdf` schreibt echte PDFs (`export_pdf` / `QPdfWriter` / `text_to_pdf`), nie DOCX-Bytes unter PDF-Namen. Header-Sniff (`ild_pdf/pdf_sniff.py`); Diagnose `scripts/pdf_doctor.py`; Minimap Standard aus; Ribbon-Undo-Pfeile im Editor.
- **Scan-Übertragung:** ein Scan-Dialog, konfigurierbares Backend, WIA/NAPS2/eSCL nach ScanTuxio-Ablauf — das Bild landet im Dokument (`core/scan_transfer.py`).
- **Tab / Nav / Recents / Editor-Guard:** Tab-X nicht-blockierend, Welcome-Sync, per-Tab-Navigation, Recents leerbar, Mausrad blättert, Editor-Aktionen no-op auf PDF. PDF-Open-Timer stiehlt den Stack nach DOCX-Open nicht mehr.
- **Annotationen:** Highlight/Stift/Objekte bleiben (PDF-Punkte), native `/Annots`, `QUndoStack`, Stift ≠ Highlight.
- **DTP / (geplant):** Layout-Modus (`instantlensdoc/dtp/` + `features/dtp_spec.py`). Scribus-Chrome (Menü Datei…Hilfe, Icon-Leiste, Lineale mm/pt/in mit ziehbaren Hilfslinien, Pasteboard, Anschnitt rot / Satzspiegel blau, Status Zoom/Seite/Hintergrund). Werkzeuge Auswählen/Text/Bild/Form gelten auf der Auswahl (Select-then-apply); Füllung/Kontur per Farbwähler; Schrift via `QFontDialog`/`QFontDatabase`. Rahmenarten getrennt (Text/Bild/Render); Musterseiten + Asset-Bibliothek/Symbole; Align/Distribute + Snap in mm; Ebenen mit Blend/Deckkraft; Schweißen (Boolean, keine Gruppe). Absatz-/Zeichenstile, Kerning, Grundlinienraster, Witwen/Waisen-Hilfe, Fuß-/Endnoten, Variablen, Querverweise, CJK/Bengali/Devanagari/Thai-Ziffern. RGB/CMYK/Lab/Spot + ICC wenn Profile da; Preflight vor PDF/X-3; Multi-Version-PDF; interaktive Felder; Import AI/IDML/EPS/SVG/PSD/TIFF/Krita; `.sla` (Scribus-Teilmenge). Tests `tests/test_dtp_2654.py`–`test_dtp_2660.py` (offscreen).
- **Menü-Audit:** Enablement (701 Einträge), 131 Editor-Aktionen bei PDF aus; Telemetrie ohne Stub-Dialog (`QMessageBox`); Outline-Vorlesen disabled ohne `show_planned`.

Neuer **Layout-Modus** und Umsetzung der Extras-Einträge, die bisher `(geplant)` / `(Hinweis)` / `(begrenzt)` waren.

- **DTP-Canvas** `instantlensdoc/dtp/`: Seiten-/Musterseitenmodell, Textrahmen/Bildrahmen/Formen frei platzierbar, Verkettung, Lineal mit ziehbaren Guides, Raster/Snap, Spalten/Stege, Bleed/Satzspiegel, Align/Distribute, Ebenen, Absatz-/Objektstile, Buchpresets (Taschenbuch/A5/Roman/Sachbuch/A4/Quadrat). Ribbon-Tab **DTP**, Ansicht → **Layout-Modus**.
- **Export:** Vektor-PDF über **QPdfWriter/QPainter** (nicht `ild_pdf`-Writer), plus DOCX/ODT.
- **KI-Assistent:** OpenAI-kompatibler Endpoint + Schlüssel in Einstellungen; ohne Schlüssel Offline-Modus.
- **Formerkennung:** Tinte → Rechteck/Ellipse/Linie/Pfeil/Dreieck; Hook `recognize_ink_as_shape` für die Annotationsschicht.
- **Variable Fonts, Envelope Distort, 3D-Extrusion, Stylus (QTabletEvent)** auf dem DTP-Canvas.
- **Text auf Pfad / Text in Pfade, Schnittmasken, Live-Füllungen** (Verlauf/Deckkraft/Schatten), **Glyphen-Palette**.
- **PAdES-B** (`features/pades.py`, pyhanko) mit sichtbarem Widget + Validierung; QES-Hinweis (QTSP).
- **Plugin-Hooks:** Aliase `on_open` / `on_save` / `on_scan`, Menü-Plugins, Beispiel `examples/ild_dtp_sample_plugin.py`.
- Tests: `tests/test_dtp_2654.py`, `tests/test_features_2654.py` (offscreen).

## 2.6.53 - PDFium „Data format error“ (Windows), DOCX-Umbruch/-Schrift, Seitenlayout

Nach dem Toolbar-Fix 2.6.52 wurde der eigentliche Ladefehler in der Hauptansicht sichtbar: `PDF-Öffnung fehlgeschlagen: Failed to load document (PDFium: Data format error)` — obwohl Textsuche/pikepdf dieselbe Datei lesen. Außerdem DOCX überbreit (eine Zeile pro Absatz, horizontaler Scroll) und Fließtext in Editor-Monospace. End-to-End-Test `scripts/test_ui_audit_2653.py` (offscreen) reproduziert alle Punkte.

- **Robustes PDF-Öffnen — `ild_pdf/pdfium_open.open_pdfium`** mit Fallback-Kette **Bytes → str-Pfad → pikepdf-Reparatur**: 1) Datei in Python lesen und als Bytes an `FPDF_LoadMemDocument64` geben (unabhängig von Windows-Pfad-Encoding `CreateFileA`/Umlauten, Share-Mode/Locks; Bytes werden pro Datei gecacht und von Render/Thumbs/Zählung geteilt), 2) klassischer Pfad, 3) pikepdf öffnet tolerant (qpdf-Recovery) und schreibt normalisiert in den Speicher — beschädigte/unvollständige PDFs (abgeschnittener Trailer, Müll vor `%PDF`), die PDFium mit „Data format error“ ablehnt, öffnen damit. Statushinweis „PDF repariert geladen (pikepdf)“. Alle PDFium-Open-Stellen (Render, Textsuche, Volltext, OCR, Batch, Export, Formulare, Objekt-/Textbearbeitung) nutzen die Kette.
- **PDFium ist nicht threadsicher — Worker-Threads nutzen kein PDFium mehr.** Passwort-Probe (`needs_password`) und Seitenanzahl-Refresh (2.6.45) öffneten PDFium im `threading.Thread` **parallel** zum Render im GUI-Thread; zwei gleichzeitige PDFium-Aufrufe korrumpieren den Parser (Linux reproduzierbar „double free“, Windows „Data format error“/graue Thumbs/„Seite 1/1“). Jetzt: Worker nur pikepdf (+ `/Encrypt`-Heuristik), PDFium-Fallback im GUI-Slot, globaler `PDFIUM_LOCK` um Open+Render.
- **Diagnose-Banner**: nennt jeden Fallback-Schritt mit exakter Exception, Datei sowie `pypdfium2`-/PDFium-/pikepdf-Version (`pdfium_version_info()`, auch im Start-Log). Altes Seitenbild wird vor dem Öffnen einer neuen Datei verworfen (zählte sonst als „Canvas hat Bild“ → kein Banner, falsche Seite).
- **Packaging**: `collect_all("pypdfium2_raw")` + `pikepdf` in Spec und `build-windows.ps1` (pdfium.dll liegt in `pypdfium2_raw`), Build-Guard prüft `pypdfium2_raw\pdfium.dll` + `version.json`; `requirements.txt` pinnt `pypdfium2==5.14.0`.
- **DOCX/Rich-Text im Editor**: Rich-Dokumente brechen **immer** am Spaltenrand um (auch bei „Wortumbruch“ aus), horizontaler Scroll = 0 — inkl. Qt-Eigenheit, dass `QPlainTextDocumentLayout` nach Rand-Änderung während `show()` die alte Textbreite behält (synthetischer Resize). Proportionale Standardschrift aus dem DOCX (Normal-Stil/docDefaults, Fallback Calibri 11) statt Consolas; Run-Schriftarten (`font-family`) werden importiert und beim Speichern zurückgeschrieben. TXT danach wieder Monospace + Einstellung.
- **Seitenlayout für den Texteditor** (Menü Ansicht → Seitenlayout…, Ribbon Ansicht/Bearbeiten, Ctrl+K): DTP-Presets (A4/A5/A6/US Letter/Legal/A3/Taschenbuch/Roman/Sachbuch/Quadrat), Hoch-/Querformat, Ränder mm/inch, **Satzspiegel-Vorschlag** aus `ild_pdf.page_layout`, Geltung (Word-/DOCX-Dokumente | alle | aus). Der Editor setzt `QTextDocument.pageSize` und rendert die Textspalte zentriert in Seitenbreite (Viewport-Ränder, grauer Hintergrund) — Text bricht wie auf einer Seite um; persistiert in den Einstellungen (`editor_page_layout`).

## 2.6.52 - Voll-Audit: PDF-Ansicht off-screen, Seitenanzahl, B/I/U, Textmarker, DOCX

End-to-End-Audit (offscreen + Xvfb 1920×1080) statt weiterer Render-Patches. Alle „Fix“-Behauptungen 2.6.40–2.6.51 wurden als unverifiziert behandelt und mit echten MainWindow-Tests nachgestellt (`scripts/test_ui_audit_2652.py`, schlägt auf 2.6.51 reproduzierbar fehl).

- **PDF „weiße Hauptansicht“ — eigentliche Ursache gefunden**: Die PDF-Werkzeugleiste war ein einzeiliges `QHBoxLayout` mit ~85 Buttons → `PdfViewer.minimumSizeHint()` **7041 px**, Hauptfenster-Mindestgröße **7286×2175 px** (Sidebar ohne Scroll ≈ 2000 px hoch). Qt kann das Fenster nicht kleiner machen; die zentrierte Seite lag bei x≈3500 px — auf einem 1920-px-Monitor unsichtbar, Statusleiste ebenfalls off-screen. Rendering/PDFium war nie das Problem (Thumbs links waren sichtbar). Fix: **`ui/flow_layout.FlowLayout`** (umbrechende Leiste, Höhen-Deckel), **Sidebar in `QScrollArea`**, Ribbon-Seiten `QSizePolicy.Ignored`, Statusleiste ohne Mindestbreite. Fenster-Minimum jetzt **1046×632 px**.
- **Mehrseitige PDFs: Seitenanzahl blieb 1** (seit 2.6.45 Fast-Open): `QTimer.singleShot` aus einem `threading.Thread` feuert nie (kein Event-Loop) → „Seite 1/1“, ▶ tot, nur ein Thumb. Fix: Signal `_page_count_ready` (Queued Connection) → `_on_page_count_ready`.
- **Fett/Kursiv/Unterstrichen überschrieben sich**: `toggle_char_format` rief nach `mergeCharFormat` zusätzlich `setCurrentCharFormat(teilformat)` → `QTextCursor.setCharFormat` ersetzt bei Auswahl das komplette Format. Fix: `mergeCurrentCharFormat`.
- **Textmarker (Markieren) im Editor** jetzt persistentes Zeichenformat (`background`) statt flüchtiger ExtraSelection — bleibt beim Tab-Wechsel, wird nach **DOCX (Highlight YELLOW)**/HTML gespeichert, erneutes Markieren hebt auf, „Markierungen löschen“ entfernt Hintergründe; im PDF aktiviert der Befehl das Highlight-Werkzeug.
- **DOCX-Import**: Formate aus **Zeichen-/Absatzstilen** (Strong, Emphasis, Heading…) via `base_style`-Kette; **Hyperlink-Runs** (vorher komplett verloren); Schriftgröße/Farbe/Word-Highlight; Body-Reihenfolge Absätze/Tabellen; Fehler pro Absatz geloggt statt stilles Plaintext-Fallback (`meta.rich_text_error`). Export: Farbe/Größe/Highlight zurück nach DOCX.
- **Format-Erbe**: `TextEditor.setPlainText` setzt das Cursor-Zeichenformat zurück (nach fettem DOCX war die nächste TXT komplett fett).
- **„wurde geändert“ direkt nach Öffnen**: `open_path` wechselte den Stack **vor** dem Laden → `_current_is_dirty` verglich alten Editor-Text mit neuem Dokument und setzte `dirty` dauerhaft (Beenden-Dialog, Zähler). Fix: Inhalt zuerst laden, `_loading_document`-Guard.
- Geräte/Scan (2.6.51) verifiziert: Menü **Geräte** (4 Aktionen), Ribbon-Tab, Toolbar **Scan…**, ScanDialog/Geräte-Dialog öffnen offscreen ohne Absturz.
- Tests: `scripts/test_ui_audit_2652.py` (Mindestgröße, Open via MainWindow, Canvas im Viewport, Seitenanzahl, ▶/goto, Thumbs mit Tinte, B/I/U/Marker, DOCX inkl. Roundtrip, Geräte). Pack `InstantLensDoc-2.6.52-pack.zip`; VERSION **2.6.52**.

## 2.6.51 - Geräte/Scan-UI wiederhergestellt (Menü + Discovery)

Patch nach **2.6.50** (PDF-Canvas-Härtung) auf Tip inkl. **2.6.49** DOCX Rich-Text: Nutzerbericht — **Geräte**/Scan-Erkennung „nicht mehr vorhanden“ (Menüs/Features weg oder tot). Audit: Menü **Geräte** hing hinter dem riesigen PDF-Menü; Toolbar-**Scan…** ohne Toolbar-Gruppe; ScanDialog hart an `scantuxio_ui`→`ocr`/PIL; Ribbon ohne Geräte; PyInstaller ohne ScanTuxio-Hidden-Imports; Menüleiste nach `restoreState` nicht erzwungen sichtbar.

Fix: `_ensure_devices_menu` früh (vor PDF) + idempotent; Menüleiste nach Build/Geometry sichtbar; Ribbon-Tab **Geräte**; Toolbar-Gruppe `scan`; ScanDialog/ScanTuxio-UI-Bridge resilient; Discovery unverändert nie werfend; Pack `InstantLensDoc-2.6.51-pack.zip`; VERSION **2.6.51**.

## 2.6.50 - PDF-Hauptansicht weiter weiß: harter Detach + PDFium-Packaging

Feldbericht nach **2.6.48/2.6.49**: PDFs in der Hauptansicht **weiter nicht sichtbar** (vermutlich kein Rebuild und/oder Fix unvollständig). Nachschärfung:

- **`ild_pdf.render`**: nach `to_pil()` **`Image.frombytes(...tobytes())`** + undurchsichtiges **RGB** (nicht nur `.copy()`); opaker `fill_color`
- **`image_qt`**: PIL→Qt über **RGB888→RGB32** (kein Alpha-Ghost); adaptive Ink-Erkennung inkl. hellgrauer Thumb-Placeholder
- Canvas/`update_thumb`: Convert ohne Tinte → Fail (kein stilles Weiß/Grau)
- **PyInstaller**: Spec `collect_all("pypdfium2")`; `build-windows.ps1` bricht ab wenn **pdfium.dll** fehlt
- **deps_check**: Mini-Render-Probe (nicht nur Import)
- Offscreen-Test multipage + `grab()` nicht all-white

Pack `InstantLensDoc-2.6.50-pack.zip`; VERSION **2.6.50**.

## 2.6.49 - Word-Suite/DOCX: echte Rich-Text-Formate (kein Markdown)

Patch nach **2.6.48** (PDFium-Buffer): Nutzerbericht — DOCX öffnete als Plaintext ohne Fett/Kursiv/Absätze; Toolbar Fett/Kursiv setzte `**`/`*`-Marker; Unterstreichen wirkte nur auf Lücken/`__`. Fix: **`richtext_docx`** lädt DOCX via python-docx → HTML mit `<b>/<i>/<u>`; Editor **`QTextCharFormat`** (fontWeight/italic/underline) statt Markdown-Wrapper; Underline auf Buchstaben; Speichern DOCX/HTML/RTF erhält Formate aus `meta.html`. Smoke `scripts/test_docx_richtext.py`. Pack `InstantLensDoc-2.6.49-pack.zip`; VERSION **2.6.49**.

## 2.6.48 - Weiße Hauptansicht/Thumbs: PDFium-Buffer detach + sichtbarer Paint

Patch nach **2.6.47** (sichtbarer Fallback): Feldbericht — Text geladen, zentrale Ansicht **weiter weiß**, Schnellvorschau-Thumb grau, **kein** Fallback-Banner. Ursache: `bitmap.to_pil()` teilt bei RGBA/BGRA den PDFium-Buffer; nach `page`/`doc`/`bitmap.close()` Use-after-free → oft weißes Ghost-Pixmap, das als „Erfolg“ zählte (`_canvas_has_page_image` nur internes `_pixmap`). Thumbs blieben Platzhalter.

Fix: **`ild_pdf.render.render_page`** detacht PIL immer mit `.copy()` + `bitmap.close()`; gemeinsame **`image_qt.pil_to_qpixmap`** (tiefe QImage-Kopie) für Canvas + Thumbs; Canvas-Erfolg nur bei **sichtbarem** Label-Pixmap mit Tinte; `QScrollArea.setWidgetResizable(False)`; Show/Resize-`_schedule_paint_retry`; Offscreen-Test `scripts/test_pdf_canvas_not_blank.py`. Pack `InstantLensDoc-2.6.48-pack.zip`; VERSION **2.6.48**.

## 2.6.47 - Hauptansicht: sichtbarer Render-Fallback (kein stilles Weiß)

Patch nach **2.6.46** (ScanTuxio-UI Launch): Restlücke aus Blank-View — wenn `_ensure_page_painted(warn=False)` scheitert, blieb die zentrale Ansicht **still weiß** (Thumbs funktionierten). Fix: **`PdfCanvas.show_render_fallback`** (gelbes Banner + Hinweis), Status/Log immer; `refresh` gilt nur bei echtem Canvas-Pixmap; Thumb-Klick erzwingt Paint; provisional `page_count` blockiert Goto nicht; nach BG-Seitenanzahl `document_changed` für Thumbs. Pack `InstantLensDoc-2.6.47-pack.zip`; VERSION **2.6.47**.

## 2.6.46 - ScanTuxio-UI als Scan-Einstieg + WIA-Busy-Hinweis

Patch nach **2.6.45** (Open-Preflight async): Nutzer-Scan zeigte „Kein Bild vom Scanner“ / „Das WIA-Gerät ist ausgelastet“ in einem zweiten Modal. Primär startet **Geräte → Scanner / Scannen…** jetzt das **ScanTuxio-Hauptfenster** (`D:\AI_Temp\ScanTuxio Win`, neben ILD, `vendor\ScanTuxio`, PATH). Handshake: Übergabeordner + neue PDF/Bilder in `~\Scans`; „Scan übernehmen“ fügt Seiten ein (OCR/Word-Suite wie bisher). Fehlt ScanTuxio: DE-Hinweis mit erwartetem Pfad + Bilder importieren — ohne gestapelte Fehlerdialoge; Geräteliste + **Erneut versuchen**. WIA/NAPS2 nur sekundär; bei WIA busy andere ScanTuxio-Backends (NAPS2/TWAIN/eSCL) und Hinweis ScanTuxio / Windows Fax und Scan / vorherigen ILD-Scan schließen. Pack `InstantLensDoc-2.6.46-pack.zip`; VERSION **2.6.46**.

## 2.6.45 - PDF-Open: „PDF wird geprüft“ nie UI-blockierend

Patch nach **2.6.44** (Non-PDF-Toolbar): Nutzerbericht — Open hängt bei **„PDF wird geprüft…“** auch bei kurzen PDFs. Ursache: Preflight rief synchron `inspect_pdf`/`needs_password` (PDFium-`len(doc)` / pikepdf) auf dem UI-Thread auf.

Fix: Open-Fast-Path nur **Dateigröße** synchron (`size_only_health`); Passwort-Probe mit **Timeout** im Worker; **keine** Katalog-/PDFium-Wartezeit vor Seite 1; provisional `page_count=1`, `_schedule_page_count_refresh` im Hintergrund; AcroForm-Vollscan beim Open ab `FORM_SCAN_PAGE_THRESHOLD` übersprungen. Nach Open: **PDF-Stack** + **`_ensure_page_painted`** (auch nach Fit/Session-Zoom), damit die zentrale Ansicht nicht weiß bleibt während Thumbs funktionieren. Progress abbrechbar. Pack `InstantLensDoc-2.6.45-pack.zip`; VERSION **2.6.45**.

## 2.6.44 - Bearbeitungsleiste für Nicht-PDF / Word-Suite

Patch nach **2.6.43** (Speichern-unter Dokumentfilter): Nutzerbericht — bei Text/DOCX/Word-Suite fehlte die Bearbeitungsleiste von **Auswahl** bis **Markierungen** (bei PDF sichtbar). Ursache: Toolbar lebte nur in ``PdfViewer``; ``EditorPane`` hatte keine eigene Leiste. Fix: **``ildEditorToolbar``** in ``EditorPane`` mit textrelevanten Werkzeugen (Auswahl, Text bearbeiten, Markierungen, Unterstreichen, Fett/Kursiv, Markierungen löschen, Suchen) — ohne PDF-only (Schwärzen/Objekt/Formular). Tab-Wechsel PDF↔Text synchronisiert Toolbar (``_sync_editor_toolbar_for_stack`` / ``_on_editor_toolbar_action``). Pack `InstantLensDoc-2.6.44-pack.zip`; VERSION **2.6.44**.

## 2.6.43 - Speichern unter: Dokumentformate statt .py-Default

Patch nach **2.6.42** (Tesseract-Runtime): Nutzerbericht — neu eingegebener Text ließ sich unter Windows oft nur als ``*.py`` speichern (Save/Speichern unter). Ursache: Vorschlagsname ``Unbenannt`` ohne Endung; unter ``python.exe`` setzt der native Windows-Dialog dann die Host-Endung ``.py``.

Fix: gemeinsame Helfer in ``file_dialogs.py`` — Dokument-Filter (``.ild``/nativ, ``.txt``, ``.md``, ``.html``, ``.docx``, ``.rtf``, ``.pdf``, ``.xlsx``), ``setDefaultSuffix``, Vorschlagsname mit Endung, kein dedizierter Python-Filter; ``save_as`` nutzt den Dialog; Text→PDF über Export; ``detect_kind`` erkennt ``.ild``. Smoke prüft Filter ohne ``*.py`` als Primärformat. Pack `InstantLensDoc-2.6.43-pack.zip`; VERSION **2.6.43**.

## 2.6.42 - ScanTuxio Tesseract-Runtime für OCR (ohne Extra-Install)

Patch nach **2.6.41**: OCR/Scan braucht kein separates Tesseract, wenn die Runtime in **ScanTuxio Win** liegt. `docs/ScanTuxio-Win.zip` ist Quellcode (keine `tesseract.exe`). Lookup wie ScanTuxio `bundled_tool_dir("tesseract")` + `ocr._tesseract_path`: **1)** `{app}/vendor/tesseract/tesseract.exe` **2)** `{app}/tesseract/tesseract.exe` (neben InstantLensDoc.exe) **3)** `D:\AI_Temp\ScanTuxio Win\tesseract|vendor\tesseract|bin\tesseract.exe` **4)** Program Files / PATH. `pytesseract.tesseract_cmd` + `TESSDATA_PREFIX=<exe-dir>\tessdata`. Erwartet: `tesseract.exe`, `tessdata\deu.traineddata`, `tessdata\eng.traineddata`. `build-windows.ps1` kopiert die Runtime wenn vorhanden; sonst **build-keygen Copy-Hint** (`xcopy` nach `vendor\tesseract`). Pack `InstantLensDoc-2.6.42-pack.zip`; VERSION **2.6.42**.

## 2.6.41 - ScanTuxio Scan/Print-Module portiert + Geräte-UX

Patch nach **2.6.40** (Blank-View/Build Guard enthalten): Nutzer auf **2.6.36** ohne Menü **Geräte**; ScanTuxio-Quellen nachgeliefert (`docs/ScanTuxio-Win.zip` → `scantuxio/`). **Vendored** unter `instantlensdoc/core/scantuxio/`: `discovery`, `scanner`, `scanner_naps2`, `scanner_escl`, `printing`, `printing_windows`, `platform_utils`. Discovery/Acquire nutzen ScanTuxio ``list_devices_all`` / ``scan_single_page_dispatch`` (NAPS2 WIA/TWAIN, native-eSCL/zeroconf, SANE); Drucker via ScanTuxio-Qt/CUPS + bestehende Winspool/Get-Printer. UI-Einstiege: Menü **Geräte → Scanner / Scannen…**, PDF → Scannen / Import…, Toolbar **Scan…**, Welcome **Scannen…**, Ctrl+Alt+Shift+I, Status `SCAN_START_HINT_DE`, leere Geräteliste mit DE-Hinweis. Pack `InstantLensDoc-2.6.41-pack.zip`; VERSION **2.6.41**.

## 2.6.40 - Blank PDF View + Windows Build Guard

Patch nach **2.6.39**: Nutzerbericht — Setup nur ~2.9 MB (statt ~49 MB), `dist\InstantLensDoc\InstantLensDoc.exe` fehlt; PDF-Hauptansicht weiss trotz Schnellvorschau-Thumbs, Klick auf Thumbs zeigt keine Seite.

Fix Hauptansicht: **`_ensure_page_painted`** rendert die aktuelle Seite mit Zoom-Fallback (bildlastige Seiten); `refresh()` liefert Erfolg/Fehler; Open ignoriert spurioses Progress-Cancel nach Nesting-Modal; Thumb-Klick wechselt immer zur PDF-Ansicht und erzwingt Paint; Virtual-Thumb-Token bleibt fuer Prefetch erhalten.

Fix Build: Root cause kleines Setup — Pack **2.6.39** enthielt **`run_instantlensdoc.py` nicht** (PyInstaller-Entry) → kein EXE, Inno fiel auf Python-Layout (~2–3 MB). Pack inkl. Entry; **`pack-windows-runnable.py` INCLUDE_TOP**; **`build-windows.ps1`** bricht ohne gueltige EXE ab; Installer-Preflight verlangt EXE (kein stiller Python-Fallback); Setup < 15 MB bei EXE-Layout = Fehler. Pack `InstantLensDoc-2.6.40-pack.zip`; VERSION **2.6.40**.

## 2.6.39 - Large-PDF Open/Edit Performance

Patch nach **2.6.38**: Nutzerbericht — 536-Seiten-PDF oeffnet mit Dialog "Grosses PDF", haengt danach beim Laden/Bearbeiten. Ursachen: UI-Thread blockiert durch Voll-Scan PageLabels, 536× Thumbnail-Platzhalter mit eigenen Pixmaps, Lazy-Queue rendert alle Seiten im Hintergrund, Doppel-Refresh Thumbs/Outline nach Open, Volltext-Extraktion ohne Cap.

Fix: **cancelbarer Open** mit Progress-Dialog (1. Seite sofort); **PageLabels-Scan** fuer grosse Docs uebersprungen; **Thumbnails virtualisiert** (Shared-Placeholder, Chunked Add, Viewport±Prefetch ohne Rest-Queue ab `THUMB_VIRTUAL_THRESHOLD`); **Edit/Text page-scoped** (Warn-Dialog ab Soft-Warn, Cancel, Doc-Stats Sample); Open-Generation bricht veraltete Folgearbeit ab. Pack `InstantLensDoc-2.6.39-pack.zip`; VERSION **2.6.39**.

## 2.6.38 - Scanner/Drucker-Erkennung Windows-Haertung

Patch nach **2.6.36**: Nutzer meldete fehlendes Scanner-Modul sowie kaputte Geraete-/Drucker-Erkennung trotz startender App. Fix: **Windows-Discovery** haertet Drucker (Qt + Winspool + Get-Printer + win32print) und Scanner (WIA + PnP + TWAIN-Quellen); PowerShell ohne Konsolenfenster, robustes JSON/ERR-Parsing; klare DE-Hinweise wenn Treiber fehlen. **Scan-Acquire** crasht nicht ohne Geraet (`last_acquire_error`); Tesseract sucht Standard-Windows-Pfade. UI: Menue **Geraete** (Scanner / Drucker / Erkennen); PyInstaller hidden-imports fuer PrintSupport/devices/scan/ocr. Pack `InstantLensDoc-2.6.38-pack.zip`; VERSION **2.6.38**.

## 2.6.36 - EXE Relative-Import / PyInstaller Entry-Fix

Patch nach **2.6.35**: Installiertes `InstantLensDoc.exe` startete nicht — Unhandled exception `attempted relative import with no known parent package` in gefrorenem `__main__.py` (`from .app import main`). Ursache: PyInstaller startet den Entry als Top-Level-Skript ohne Package-Parent. Fix: duenner Entry **`run_instantlensdoc.py`** mit absolutem Import `from instantlensdoc.app import main`; **`instantlensdoc/__main__.py`** ebenfalls absolut; **`build-windows.ps1`** / **`instantlensdoc.spec`** nutzen den neuen Entry plus `--hidden-import instantlensdoc.app` und `--collect-submodules instantlensdoc`. Smoke: Entry ohne Relative-Imports + Import-Smoke. Pack `InstantLensDoc-2.6.36-pack.zip`; VERSION **2.6.36**.

## 2.6.35 - Sync Ordner-Sperre / Fresh-Dest / PyInstaller-Probe

Patch nach **2.6.34**: Windows-Sync scheiterte wenn `D:\AI_Temp\InstantLensDoc` (oft `InstantLensDoc-keygen`) durch `python.exe`/`cmd.exe` gesperrt war; ForceClean/Rename brach ab; gemischte Baeume (z. B. 2.6.32) ohne `scripts\build-windows-installer.ps1`. Fix: **`scripts/sync-ild.ps1`** erkennt gesperrte Pfade, loescht Kinder einzeln mit Retry, Keygen-Unterordner skip-or-retry, klare DE-Hinweise (`taskkill`/`handle`, Keygen-Fenster schliessen); **`-Dest`** (Alias) fuer frischen Ordner z. B. `D:\AI_Temp\InstantLensDoc-2635` plus optional **`-Swap`**; Sync verlangt `scripts\build-windows-installer.ps1`. **`build-windows.ps1`**: PyInstaller-Import ohne opaken NativeCommandError; bei Fehlen klares `pip install pyinstaller` + echte Import-Fehlertexte. Pack `InstantLensDoc-2.6.35-pack.zip` inkl. Installer-Skript; VERSION **2.6.35**.

## 2.6.34 - Keygen PYTHONPATH / nested+standalone Import-Fix

Patch nach **2.6.33**: Store-/Nested-Keygen (`InstantLensDoc-keygen` unter App-Root) und Standalone-Zip scheiterten mit `ModuleNotFoundError: No module named 'instantlensdoc'`, weil `sys.path` nur den Keygen-Ordner enthielt. Fix: **`run-keygen.bat` / `run-keygen.ps1`** setzen `PYTHONPATH` auf Keygen-Ordner **und** Parent; klare DE-Fehlermeldung wenn Paket fehlt; **`keygen/__main__.py`** sucht App-Root (Parent) + vendored `instantlensdoc`; History-Fallback ohne `config`; Standalone-Zip mit Minimal-Vendor `instantlensdoc.license`. Pack `InstantLensDoc-2.6.34-pack.zip` + Store-Keygen aktualisiert.

## 2.6.33 - Installer/run.bat cmd-Loop-Fix

Patch nach **2.6.32**: Windows-Installer post-install startete `run.bat`, das **UTF-8 ohne BOM** mit Em-Dash/Ellipsis/Smart-Quotes enthielt. cmd.exe las das als CP1252 → Mojibake `â€"` (eingebettete `"`) → deutsche Hilfe-/Prosa-Fragmente als Befehle (`Deutsch`, `vorhanden`, `hon.exe`, …) in Endlosschleife. Fix: **`run.bat` / `run-ild.bat` / `run-keygen.bat`** pure ASCII, Help per `goto` (keine unescaped `(` in IF-Blöcken), **`installer/build-installer.ps1`** bevorzugt nach `build-windows.ps1` das **EXE-Layout** (`UsePythonLauncher=0`, Post-Install = `InstantLensDoc.exe`), ISS/`installer-hinweis.txt` ASCII. Pack `InstantLensDoc-2.6.33-pack.zip` + Store-Kopie aktualisiert.

## 2.6.32 - Build-Skripte Windows-Parser/Encoding-Fix

Patch nach **2.6.31**: **`build-windows.ps1`**, **`scripts/build-windows-installer.ps1`**, **`installer/build-installer.ps1`** und weitere Pack-`.ps1` parsen unter Windows PowerShell 5.1 wieder (UTF-8 ohne BOM + Em-Dash/Ellipsis/Pfeile in Strings erzeugten Mojibake und Folgefehler um Klammern/`else`). Fancy Unicode durch ASCII ersetzt; Dateien UTF-8 **mit BOM**. Pack `InstantLensDoc-2.6.32-pack.zip` + Store-Kopie aktualisiert.

## 2.6.31 - Sync-Skript Windows-Parser/Encoding-Fix

Patch nach **2.6.30**: **`scripts/sync-ild.ps1`** parst unter Windows PowerShell 5.1 wieder (UTF-8 ohne BOM + Em-Dash/Smart-Quotes in Strings erzeugten Mojibake `â€"` und Folgefehler Try/Catch/Klammern). Fancy Unicode durch ASCII ersetzt; Datei UTF-8 **mit BOM**. Pack `InstantLensDoc-2.6.31-pack.zip` + Store-Kopie aktualisiert.

## 2.6.30 — Sync LocalPack flat/nested + ForceClean

Patch nach **2.6.29**: **`scripts/sync-ild.ps1`** erkennt Pack-Root per Marker (`VERSION.txt` / `build-windows.ps1` / `requirements.txt`) — flat am Zip-Root **oder** nested `InstantLensDoc/` — und verwechselt unter Windows nicht mehr mit dem Python-Paketordner `instantlensdoc\` (case-insensitive). Default **ForceClean** leert das Ziel vor Copy (Nutzer-Icons bleiben); Ziel gesperrt/in use → klare DE-Meldung (`cd D:\AI_Temp`). Pack neu nested unter `InstantLensDoc/`. Docs/Store-Kopien aktualisiert.

## 2.6.29 — Silbentrennung Menü/Palette (9 Sprachen)

Minor nach **2.6.28**: **Silbentrennung-UI** für alle 9 UI-Sprachen (DE/EN/FR/RU/ES/ZH/PT/AR/IT) im Bearbeiten-Menü und der Command-Palette; Engine/Hook unverändert aus **2.6.28** (ZH/AR no-break). FEATURES: Signieren-Zeile an eIDAS-Trust-Pfad angeglichen; veraltete „Mehrsprach-UI DE/EN teilweise“-Zeile bereinigt. Pack/Docs aktualisiert.

## 2.6.28 — Audit-Closure Word-Suite / DTP / Mausrad

Minor nach **2.6.27**: Schließt die offenen Word-/DTP-Audit-Lücken. **Mausrad:** Default-Einzelseiten-PDF blättert per Rad (bei Zoom-Overflow natives Scrollen); Frame/Canvas-Wheel; Continuous/1S/Editor/`apply_wheel_scroll` (**2.6.27**) unverändert. **Abbildungs- & Stichwortverzeichnis** auto wie TOC (`ILD-LOF-*` / `ILD-IDX-*`). **F12 Speichern unter** + Ribbon Save-as + Alt+1…6. **`.pptx`** Export/Import. **Abschnittsumbrüche** (`ildsections-v1`) + Spalten-Pagination. **Grammatik** DE/EN (`grammar_check`). **Silbentrennung** 9 UI-Sprachen. **Pantone-ähnlich/Spot**, Web-PDF, Print-Preview. **eIDAS Trust-Pfad** ohne bezahlte TSA. **Echtzeit-Hub** lokal (CRDT-lite). **Handschrift** Multi-PSM + Preprocess. Freier KI-Chat-Stub und Outline-TTS bleiben. Gehostete Cloud/QES-TSA = externe Abhängigkeit.

## 2.6.27 — Polish / Installer im Sync-Flow / Mausrad-Scroll

Minor nach **2.6.26**: Keine großen neuen Produktflächen. **Installer in den Windows-Sync/Install-Flow verdrahtet** — `scripts/sync-ild.ps1` mit optionalem `-BuildInstaller` (ruft `build-windows-installer.ps1` nach Sync) und klaren DE-Hinweisen für `install-ild.ps1` / Setup.exe / Keygen / Scripting; `install-ild.ps1` nennt post-sync Setup-Einzeiler. **Hilfe/Info-Vollständigkeit** für Installer + Keygen + Scripting (DE primary, neue i18n-Keys). **Robustes Mausrad-Scrollen** in Text-/Dokument-/Word-Suite-Views (`apply_wheel_scroll`: pixelDelta/angleDelta, Shift→horizontal, Forward von Zeilennummern/Minimap, Viewport-Filter; Markdown-Vorschau & RichPreview; PDF Seite-für-Seite Trackpad). Kleine Korrektur: Hilfe/About markiert Plugin-Hooks als produktiv. Runnable-/Installer-Pack und Docs aktualisiert. Setup.exe weiterhin auf Windows x64 mit Inno Setup 6: `powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1` → `dist\InstantLensDoc-Setup-2.6.27.exe`. Freier KI-Chat-Stub und Outline-TTS bleiben.

## 2.6.26 — Polish / Installer-Konsolidierung

Minor nach **2.6.25**: Keine großen neuen Produktflächen. **Windows-Installer gehärtet** — `scripts/build-windows-installer.ps1` + `installer/build-installer.ps1` lesen Version aus `VERSION.txt`, Preflight (run.bat/EXE, ISS-Vollständigkeit), ISCC `/DMyAppVersion=`, CustomMessages DE/EN für Desktop/Startmenü/Launch; ISS mit AppMutex, MinVersion, ArchitecturesAllowed, UsePreviousTasks. **Konsolidierung** der Serie 2.6.20–2.6.25 (Spell/Review/Batch/Share/Hyperlinks/EPUB/Stylus/Outline/Hooks/Telemetrie/3D). Docs/FEATURES/INFO/i18n + Runnable-/Installer-Pack aktualisiert. Setup.exe weiterhin auf Windows x64 mit Inno Setup 6: `powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1` → `dist\InstantLensDoc-Setup-2.6.26.exe`. Freier KI-Chat-Stub und Outline-TTS bleiben.

## 2.6.25 — Stylus, Outline, Hooks, Telemetrie, 3D

Minor nach **2.6.24**: Verbleibende Stubs durch nutzbare Features ersetzt. **Stylus:** Tablet/Stift-Eingabe für Annotationen mit Druck→Strichstärke und Palm-Rejection (sonst verbesserte Freihand-Integration). **Outline:** Dokumentstruktur-Pane jenseits TOC — Überschriften, PDF-Lesezeichen, Favoriten, Filter, Navigation. **Hooks:** User-/Script-Hooks für `document.opened` / `saved` / `exported` / `ocr.finished` (+ Bus) — Python/PowerShell `ild`. **Telemetrie:** optionale lokale Diagnostik, Opt-in Default aus, kein Netzwerk, kein PII. **3D:** Limited Viewer (isometrische Extrusion einfacher Formen; kein Mesh/OpenGL) statt leerem Stub. Freier KI-Chat-Stub und Outline-TTS bleiben. **ild API** `hooks_*` / `document_outline_api` / `stylus_status` / `telemetry_*` / `extrude3d_preview`. **Windows-Installer:** Inno Setup-Projekt (`installer/instantlensdoc.iss`) + `scripts/build-windows-installer.ps1` → `InstantLensDoc-Setup-2.6.25.exe` (Startmenü, optional Desktop, Uninstall, 64-Bit); Setup.exe auf Windows x64 bauen.

## 2.6.24 — Hyperlinks, Grafiken/Medien, EPUB

Minor nach **2.6.23**: **Hyperlinks** verknüpfen Text mit URLs oder Dokumentzielen (`#anker`, `ild://line/N`, Überschrift); Markdown/HTML; Dialog Ctrl+Shift+K; Sidecar `*.ildlinks.json`. **Grafiken & Medien:** Bild skalieren/zuschneiden, Formen, Online-Video-Platzhalter (URL); Textumfluss bleibt. **EPUB-Export** (EPUB 2, Kapitel aus H1) inkl. Import-Text. **ild API** `insert_hyperlink` / `extract_hyperlinks` / `layout_scale_image` / `layout_crop_image` / `layout_add_shape_frame` / `layout_add_video_placeholder` / `export_epub_api` · CLI · PS. Stubs Stylus/3D/Hooks/Outline/Telemetrie/freier KI-Chat unverändert.

## 2.6.23 — Gemeinsames Review / Cloud-Ordner-Kollaboration

Minor nach **2.6.22**: **Gemeinsames Review** ersetzt den Cloud-Stub. Notizen, Markierungen, Stempel und Kommentare sind zwischen Nutzern austauschbar über einen **lokalen Freigabeordner** (`session.ildshare.json` / ildshare-v1) und optional einen **einfachen HTTP-Endpoint** (GET/PUT JSON). Integriert Review/Kommentare (**2.6.21**) und Annotationen/Stempel (**2.6.9**). UI zum Starten/Beitreten inkl. dokumentierter Einschränkungen; Polling wo sinnvoll. **ild API** `shared_review_*` · CLI `share-*` · PS `Start-/Join-/Sync-IldSharedReview`. Offline bleibt nutzbar. Freier KI-Chat-Stub unverändert; kein gehosteter Cloud-Dienst / kein CRDT.

## 2.6.22 — Stapelverarbeitung, Digitale Signaturen (eIDAS), Seriendruck-Polish

Minor nach **2.6.21**: **Stapelverarbeitung** für viele PDFs in einem Job — Konvertieren (→PNG), Wasserzeichen, Komprimieren, Verschlüsseln (AES-256); UI + `ild.run_batch_job` / CLI `batch` / PS `Invoke-IldBatch`. **Digitale Signaturen** (eIDAS-Pfad): SES-Stempel, AES mit PKCS#12 (Dokument-Hash + Attachment + Sidecar `*.ildesign.json`), QES als QTSP-Import-Pfad; baut auf Verschlüsselung **2.6.7**. **Seriendruck-Polish**: Vorschau, fehlende Felder, Delimiter, HTML/DOCX, kombinierte Datei. Cloud-Echtzeit-Kollaboration bleibt Stub (→ 2.6.23). Freier KI-Chat-Stub unverändert.

- `run_pdf_batch` / BatchMode PDF_CONVERT/WATERMARK/COMPRESS/ENCRYPT + Pipeline
- `ild_pdf.esign` — Zertifikat, Sign/Verify/List, eIDAS-Info; UI `ESignDialog`
- Seriendruck-Dialog mit Preview; `mail_merge_preview` / fmt/combined/strict
- ild-API/CLI/PowerShell; Docs/i18n; Version **2.6.22**
- Smoke: 2.6.22 CLI+Qt (batch/esign/mail-merge-polish)

## 2.6.21 — Review/Track Changes, Kommentare, Versionsverlauf, Seriendruck

Minor nach **2.6.20**: Lokale **Zusammenarbeit** zuerst — **Änderungen nachverfolgen (Review)** mit Autor/Accept/Reject; **Kommentare** an Textstellen ohne Body-Änderung; **Versionsverlauf** speichern/wiederherstellen (``*.ildversions/``); Basis-**Seriendruck** (CSV/Excel → Briefe mit ``{{Feld}}``). Cloud-Echtzeit-Kollaboration und freier KI-Chat bleiben Stubs. eIDAS/rechtssichere Signaturen warten. Scripting: `ild.review_*` / `comment_*` / `version_*` / `mail_merge_run` · CLI · PS `Enable-IldReview` / `Add-IldComment` / `Save-IldVersion` / `Invoke-IldMailMerge`. Ribbon-Tab **Review**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert.

- Review-Sidecar `*.ildreview.json` (ildreview-v1); Diff-Protokoll Insert/Delete
- Kommentar-Sidecar `*.ildcomments.json` (ildcomments-v1); Resolve/Delete
- Versionsstore `*.ildversions/` (ildversions-v1); Save/Restore/Delete
- Seriendruck-Basis CSV/XLSX; Platzhalter `{{Name}}` / `«Name»`
- ild-API/CLI/PowerShell; Ribbon Review; Docs/i18n; Version **2.6.21**
- Smoke: 2.6.21 CLI+Qt (review/comments/versions/mail-merge)

## 2.6.20 — Spellcheck/Suggestions, Autocorrect/Bausteine, Ribbon/Tabs, Undo

Minor nach **2.6.19**: **Rechtschreibprüfung** mit **Korrekturvorschlägen** (Edit-Distanz) und leichten **Grammatik-Hinweisen**; Builtin-Wortliste der **UI-Sprache** (+ optionale User-Wortliste). **Autokorrektur** und **Textbaustein-Kürzel** beim Tippen; Editor-Bausteine **9 Slots**. **Ribbon/Workspace-Polish:** Tabs Bearbeiten/Fenster, Drag-Reorder der Dokument-Tabs, optionales **separates Fenster**. **Undo/Redo** vertieft (Annotation-History + Seiten-Ops unbegrenzt, Editor `undoLimit=0`). Scripting: `ild.spellcheck` / `suggest_word` / `autocorrect_text` / `list_snippets` · CLI `spellcheck`/`suggest`/`autocorrect`/`snippets` · PS `Invoke-IldSpellcheck` / `Invoke-IldAutocorrect` / `Get-IldSnippets`. Freier KI-Chat-Stub unverändert. Keine Cloud-Echtzeit-Kollaboration; eIDAS-Signaturen warten. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert.

### Neu
- `spellcheck_with_suggestions` / Grammar-Hints; F7 + Shift+F7 Vorschlagsdialog
- `autocorrect` + Baustein-Kürzel (UI-Sprache); Settings Toggle
- Ribbon: Bearbeiten/Fenster; Tabs Drag + Separates Fenster
- ild-API/CLI/PowerShell: `spellcheck` / `suggest` / `autocorrect` / `snippets`

### Geändert
- Undo-Stacks praktisch unbegrenzt; Textbausteine 3→9; Docs/Version **2.6.20**; i18n-Keys

### Tests / Qualität
- Version **2.6.20** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.20 CLI+Qt (spell/autocorrect/ribbon/undo)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.6.19 — Document Comparison, Book Layout, Page-Scroll, Ribbon/Tabs

Minor nach **2.6.18**: **Document Comparison** — Side-by-Side-PDF-Vergleich mit **Drag-and-Drop**, **Sync-Scroll** der Panes, Raster-/Textlayer-Diff-Highlight; **ild.compare_pdfs** / CLI `compare` / PowerShell `Invoke-IldCompare`. **Enhanced Viewing:** **Buch-Layout** (Cover allein, danach Doppelseiten) und **Seite-für-Seite-Scroll** (Mausrad blättert). **Workspace (partiell):** horizontale **Dokument-Tabs** + leichte **Ribbon-Chrome** (Start/Ansicht/PDF). Keine volle Cloud-Kollaboration. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert.

### Neu
- `ild_pdf.diff.compare_pdf_pages` + `ild.compare_pdfs` / CLI `compare` / PS `Invoke-IldCompare`
- Compare-Dialog: Drag-and-Drop, Sync-Scroll, Diff-Highlight
- PDF-Viewer: Buch-Layout, Seite-für-Seite; Toolbar/Menü/Palette
- UI: `DocumentTabBar`, `RibbonBar` (partiell)

### Geändert
- Docs/Version **2.6.19**; FEATURES/INFO/README; i18n-Keys Compare/Book/Tabs/Ribbon

### Tests / Qualität
- Version **2.6.19** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.19 CLI+Qt (compare/book-layout/page-by-page/tabs/ribbon)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.6.18 — Farbmanagement, Bleed, Ebenen, Preflight, PDF/X

Minor nach **2.6.17**: **Druck-/DTP-Ausgabe** — **RGB/CMYK-Farbmanagement** inkl. Custom-Paletten und Spot-Hinweisen, **Bleed/Anschnitt**-Einstellungen (TrimBox/BleedBox), **Dokument-Ebenen** (Hintergrund/Bilder/Text) für Rahmen-Organisation, **Preflight** (fehlende/nicht eingebettete Schriften, niedrige Bildauflösung, Bleed-Hinweise) und **PDF/X** bzw. print-ready Export neben dem bestehenden PDF-Export. Scripting: `ild.list_color_palettes` / `convert_color_api` / `apply_bleed` / `preflight` / `export_pdfx` / `layout_set_layer` · CLI `palettes` / `convert-color` / `apply-bleed` / `preflight` / `export-pdfx` / `layers` · PowerShell `Get-IldColorPalettes` / `Invoke-IldBleed` / `Invoke-IldPreflight` / `Export-IldPdfX`. UI: Datei→Export PDF/X; PDF→Preflight/Bleed/Ebenen; Command-Palette. i18n-Keys für Preflight/Bleed/Ebenen/PDF/X. Freier KI-Chat-Stub unverändert. Kein volles PDF-Compare, kein Ribbon-Overhaul. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert.

### Neu
- `ild_pdf.print_prep` — RGB↔CMYK, Paletten, BleedSettings, Ebenen, Preflight, `export_pdfx` / print-ready
- Layout: Rahmen-Feld `layer` + `set_frame_layer` / `frames_by_layer`
- UI: Export PDF/X · Preflight · Anschnitt · Dokument-Ebenen; Palette-Commands
- ild-API/CLI/PowerShell: `palettes` / `convert-color` / `apply-bleed` / `preflight` / `export-pdfx` / `layers`

### Geändert
- Docs/Version **2.6.18**; FEATURES/INFO/README; i18n-Katalog-Keys

### Tests / Qualität
- Version **2.6.18** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.18 CLI+Qt (color/bleed/layers/preflight/pdfx)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.6.17 — Volles InstantLens Doc i18n (+ Handschrift-Hook)

Minor nach **2.6.16**: **Gesamtes InstantLens Doc** umschaltbar in den Einstellungen: **Deutsch, English, Français, Русский, Español, 中文, Português, العربية, Italiano**. Betrifft Module/UI (Viewer, OCR, Scan, Annotationen, Formulare, Export, Assistenten, Einstellungen) inkl. **Hilfe** und **Info**. Phrase-Retranslate + Katalog (`locales/catalog.json`); **Arabisch RTL** wo praktikabel; Sprache **persistiert**. Externe Hilfe/Info/Feature-Docs unter Project-Store `docs/i18n/{lang}/`. **Basis-Handschriftenerkennung** (Tesseract-PSM-Hook) in OCR-Dialog/Menü/ild. Freier KI-Chat-Stub unverändert. Kein CMYK/Bleed/Preflight/PDF/X, kein PDF-Compare. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert.

### Neu
- `instantlensdoc.core.i18n` — 9 Sprachen, RTL, `apply_ui_language` / `retranslate_tree` / `help_html`
- `instantlensdoc/locales/` — `catalog.json`, `{lang}.json`, `help/{lang}.html`
- OCR: `ocr_image_handwriting` / Handschrift-PSM im OCR-Dialog; Menü/Palette
- ild-API/CLI/PowerShell: `ui-langs` / `set-ui-lang` / `tr` / `ocr-handwriting`

### Geändert
- Settings-Sprachwahl 9 Einträge; Hilfe/About lokalisiert; Docs/Version **2.6.17**

### Tests / Qualität
- Version **2.6.17** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.17 CLI+Qt (full-i18n + handwriting-hook)
- Stubs: freier KI-Assistent unverändert getrennt

## 2.6.16 — Isolierte KI-Dokument-Wizards

Minor nach **2.6.15**: **Geführte KI-Standardabläufe** als isolierte User-Abfragen (kein freier Chat): **Formular**, **Anschreiben**, **Kaufvertrag**, **Rechnungsformular** — generisch oder unternehmensbezogen (Firma, Adresse, USt-Id, IBAN …). Ausgabe als editierbares InstantLens-Doc / Word-Suite-Dokument. Lokal template-/regelbasiert; optionaler LLM-Hook nur hinter dem Wizard. UI: Extras → **Dokument erstellen… (KI-Wizard)** (Ctrl+Alt+Shift+Q); Palette `ki_document_wizard`. Scripting: `ild.generate_ki_document` / `run_ki_wizard` / `list_ki_wizards` · CLI `ki-wizard` / `ki-wizards` · PowerShell `Invoke-IldKiWizard` / `New-IldDocumentWizard` / `Get-IldKiWizards`. Freier KI-Assistent-Stub unverändert getrennt. Kein CMYK/Bleed/Preflight/PDF/X, kein volles i18n, kein PDF-Compare. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert.

### Neu
- `instantlensdoc.core.ki_wizards` — Template-Generierung + optionaler `register_llm_hook`
- UI: `KiDocumentWizardDialog`; Menü/Palette Ctrl+Alt+Shift+Q
- ild-API/CLI/PowerShell: `ki-wizard` / `ki-wizards`

### Geändert
- Docs/Version **2.6.16**; Hilfe/Cheat-Sheet/FEATURES

### Tests / Qualität
- Version **2.6.16** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.16 CLI+Qt (ki-document-wizards)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert (freier Chat bleibt Stub)

## 2.6.15 — OCR → Word-Suite Handoff

Minor nach **2.6.14**: **OCR-/Layout-OCR-Ergebnisse** (Tesseract, `*.ildocr.txt` / hOCR / TSV) als **editierbares Word-Suite-Dokument** übernehmen — nicht nur Sidecar-Anzeige. Lesereihenfolge/Blöcke bleiben so weit praktikabel erhalten; anschließend Formatierung/Export mit den Tools aus 2.6.10–2.6.14. UI: Extras → **In Word-Suite öffnen/übernehmen…** (Ctrl+Alt+Shift+W), Checkbox im OCR- und Scan-Dialog. Scripting: `ild.ocr_to_word_suite` / `import_ildocr` / `handoff_ocr_to_word_suite` · CLI `ocr-word-suite` / `import-ildocr` · PowerShell `Invoke-IldOcrWordSuite` / `Import-IldOcr`. Kein CMYK/Bleed/Preflight/PDF/X, kein volles i18n, keine KI-Wizards, kein PDF-Compare. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert.

### Neu
- `instantlensdoc.core.ocr_word_suite` — Sidecar-Parse, Block→Absätze, Auto-Format-Handoff
- UI: OCR/Scan → Word-Suite; Palette `ocr_word_suite`; Menü Ctrl+Alt+Shift+W
- ild-API/CLI/PowerShell: `ocr-word-suite` / `import-ildocr`

### Geändert
- Docs/Version **2.6.15**; OCR-Dialog + Scan-Dialog Handoff-Checkbox

### Tests / Qualität
- Version **2.6.15** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.15 CLI+Qt (ocr-word-suite/ildocr-handoff)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.6.14 — Tabellen, Daten-Import, Office Speichern/Export/Import

Minor nach **2.6.13**: **Dokument-Tabellen** erstellen, formatieren und sortieren (Markdown/`ild-table`-Marker), **Zahlen/Daten-Import** aus CSV und Excel/`.xlsx` in Tabellen, **Speichern/Export/Import** gängiger Formate inkl. Office: `.docx`, `.xlsx`, `.pdf`, `.txt`, `.rtf` sowie HTML/JPG. Scripting: `ild.create_table` / `format_table` / `sort_table` / `import_table_csv` / `import_table_xlsx` / `export_table` / `save_document` / `import_document` / `list_io_formats` · CLI `table-create` / `table-format` / `table-sort` / `table-import-csv` / `table-import-xlsx` / `save` / `import-doc` · PowerShell `New-IldTable` / `Format-IldTable` / `Sort-IldTable` / `Import-IldTableCsv` / `Import-IldTableXlsx` / `Save-IldDocument` / `Import-IldDocument`. Kein CMYK/Bleed/Preflight/PDF/X, kein volles i18n, keine KI-Wizards, kein PDF-Compare. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert.

### Neu
- `ild_pdf.tables` — create/format/sort, CSV/XLSX-Import, Markdown-/HTML-Darstellung
- `instantlensdoc.core.export` — RTF/TXT/XLSX/JPG + unified `export_document` / `import_document_text`
- UI: Einfügen → Tabelle / formatieren / sortieren / Daten importieren; Export-Menü XLSX/TXT/RTF/JPG; Ctrl+Alt+Shift+T

### Geändert
- Docs/Version **2.6.14**; ild-API/CLI/PowerShell erweitert; Speichern-unter-Filter inkl. RTF/XLSX/PDF

### Tests / Qualität
- Version **2.6.14** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.14 CLI+Qt (tables/csv-xlsx/office-io)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.6.13 — Erweiterte Typografie, Textumfluss, Silbentrennung, Drop Caps

Minor nach **2.6.12**: **Erweiterte Typografie** (Tracking, Kerning, Leading; Absatz-/Zeichenstile auf 2.6.10 Presets), **Textumfluss** um Bild-/Formrahmen (`bounding_box` / `contour` / `jump_object`), intelligente **Silbentrennung** (DE/EN + `register_hyphenation_language`-Hook), **Drop Caps**/Initiale. Scripting: `ild.apply_typography` / `apply_drop_cap` / `hyphenate` / `list_character_styles` / `list_typography_styles` / `layout_set_text_wrap` / `layout_flow_text_wrap` · CLI `typography` / `drop-cap` / `hyphenate` / `character-styles` / `layout-text-wrap` / `layout-flow-wrap` · PowerShell `Invoke-IldTypography` / `Invoke-IldDropCap` / `Invoke-IldHyphenate` / `Set-IldTextWrap` / `Invoke-IldLayoutFlowWrap`. Kein CMYK/Bleed/Preflight/PDF/X, kein volles i18n, keine KI-Wizards, kein PDF-Compare. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert.

### Neu
- `ild_pdf.typography` — Tracking/Kerning/Leading-Marker, Zeichenstile, Silbentrennung DE/EN + Hook, Drop Caps
- `instantlensdoc.core.layout` — `text_wrap` an Bildrahmen, `flow_text_around` / `set_text_wrap`
- UI: Bearbeiten → Tracking/Leading/Drop Cap/Silbentrennung; Einfügen → Textumfluss; Ctrl+Alt+Shift+D/H

### Geändert
- Docs/Version **2.6.13**; ild-API/CLI/PowerShell erweitert; Style-Presets mit Typo-Defaults

### Tests / Qualität
- Version **2.6.13** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.13 CLI+Qt (typography/wrap/hyphenation/dropcaps)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.6.12 — Frames/Boxes, Textrahmen-Verkettung, Musterseiten, Satzspiegel

Minor nach **2.6.11**: **Frames/Boxes** (bewegliche, skalierbare Text- und Bildrahmen), **Textrahmen-Verkettung** (Overflow in nächste Spalte/Seite), **Musterseiten** (wiederkehrende Kopf-/Fußzeilen + Seitenzahlen über Seiten, auf 2.6.11 HF), **Satzspiegel**-Basics (Ränder an Seitenformat-Presets gebunden, Overlay). Scripting: `ild.satzspiegel` / `list_master_pages` / `apply_master_page` / `layout_*` · CLI `satzspiegel` / `master-pages` / `apply-master` / `layout-flow` / `layout-move` / `layout-resize` · PowerShell `Get-IldSatzspiegel` / `Get-IldMasterPages` / `Invoke-IldMasterPage` / `Invoke-IldLayoutFlow` / `Move-IldFrame` / `Resize-IldFrame`. Kein CMYK/Bleed/Preflight/PDF/X, kein volles i18n, keine KI-Wizards, kein PDF-Compare. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert.

### Neu
- `instantlensdoc.core.layout` — Move/Resize, Spalten-/Seiten-Ketten, page/column/locked
- `ild_pdf.page_layout` — `Satzspiegel`, `MasterPage`, `apply_master_page`, Presets
- UI: Toolbar **Satzspiegel**; Einfügen → Spalten-Rahmen / Rahmen verschieben·skalieren / Musterseite; Ctrl+Alt+S

### Geändert
- Docs/Version **2.6.12**; ild-API/CLI/PowerShell erweitert

### Tests / Qualität
- Version **2.6.12** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.12 CLI+Qt (frames/chain/master/satzspiegel)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.6.11 — Lineal, Raster, Kopf/Fuß, Buchformate, Absatzformat

Minor nach **2.6.10**: **Lineal** (horizontal/vertikal, mm/inch), **Ausrichtungsraster + Guides**, **Kopf-/Fußzeilen** mit Seitenzahlen, Titel und **Ersteller/Autor** (`{title}`/`{author}`/`{creator}`), **Seitenformate-Presets** US Letter / DIN-A / Buch (Taschenbuch 125×190, DINA5, Roman 135×215, Sachbuch 170×240, DINA4, Quadrat 210×210 mm), **Absatzformatierung** (Ausrichtung links/zentriert/rechts/Blocksatz, Zeilenabstand) an Style-Presets aus 2.6.10. Scripting: `ild.list_page_formats` / `set_page_format` / `apply_header_footer` / `apply_paragraph_format` / `list_paragraph_styles` · CLI `page-formats` / `set-page-format` / `header-footer` / `paragraph-format` · PowerShell `Get-IldPageFormats` / `Set-IldPageFormat` / `Invoke-IldHeaderFooter` / `Invoke-IldParagraphFormat`. Kein volles DTP (Musterseiten/CMYK/Frames), kein i18n-Pack, keine KI-Wizards, kein PDF-Compare-Ausbau. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert.

### Neu
- `ild_pdf.page_layout` — Buchformate, Lineal-Ticks, Raster/Guides, Absatz-Marker, HF mit Metadaten
- UI: Toolbar **Lineal** / **Raster**; Ansicht Ctrl+Alt+R/G; Editor Ctrl+L/E/R/J Ausrichtung
- Kopf-/Fußzeile-Platzhalter `{title}` `{author}` `{creator}` (Metadaten)

### Geändert
- Docs/Version **2.6.11**; `PAGE_SIZE_PRESETS` um Buch-/DIN-Formate; Style-Presets mit alignment/line_spacing
- Ctrl+R = Absatz rechts (Ersetzen bleibt Ctrl+H)

### Tests / Qualität
- Version **2.6.11** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.11 CLI+Qt (lineal/raster/page-formats/header-footer/paragraph)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.6.10 — Auto-Format, TOC, Word-Shortcuts, Fonts

Minor nach **2.6.9**: **Automatische Formatierung** (Style-Presets Heading 1–3 / Fließtext / Zitat + Heuristik), **automatisches Inhaltsverzeichnis** aus Überschriften (Editor-Markdown bzw. PDF-Outline → Sidebar), **Word-/InDesign-ähnliche Tastaturkürzel** (Ctrl+B/I/U, Ctrl+H Ersetzen, Ctrl+S/F/Z/Y/C/V/P — dokumentiert in Hilfe/F1), **Suchen/Ersetzen** (Ctrl+H + Ctrl+R), **Windows-Systemschriften** im Font-Picker. Scripting: `ild.auto_format_text` / `auto_format_pdf` / `generate_toc` / `list_system_fonts` / `find_replace` · CLI `auto-format` / `toc` / `fonts` / `find-replace` · PowerShell `Invoke-IldAutoFormat` / `Update-IldToc` / `Get-IldSystemFonts` / `Invoke-IldFindReplace`. Kein volles DTP (Musterseiten/CMYK), kein i18n-Pack, keine KI-Wizards. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert.

### Neu
- `ild_pdf.auto_format` — Presets, Heuristik, TOC-Outline, Systemfonts, Find/Replace
- UI: Auto-Format / TOC-Menü · Ctrl+B/I/U · Ctrl+H Find/Replace · Inline-`QFontComboBox`
- Hilfe/Cheat-Sheet: Word-/InDesign-Shortcut-Liste

### Geändert
- Docs/Version **2.6.10**; „Auswahl markieren“ → Ctrl+Shift+H (Ctrl+H = Ersetzen)
- Scripting-API / `ild.ps1` / Beispiele erweitert

### Tests / Qualität
- Version **2.6.10** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.10 CLI+Qt (auto-format/TOC/fonts/find-replace + Shortcuts)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.6.9 — Annotationen ausbauen

Minor nach **2.6.8**: **Annotationen** — einstellbare **Pinsel-/Stiftstärke**, **Color-Picker** für Strich und Füllung, **Formen** (Kreis/Ellipse gefüllt und Outline, Rechteck, Dreieck, Rundrect), **definierbare Stempel** Paid / Bezahlt / Rechnung / Datum plus **benutzerdefinierte** Text-Stempel (`ildstamps-v1`), **Absatz-Highlight** ganzer Textabschnitte (nicht nur Freihand). Scripting: `ild.add_shape` / `add_stamp` / `add_ink` / `highlight_paragraphs` / `list_stamps` · CLI `ann-shape` / `ann-stamp` / `ann-highlight-para`. Keine Word-Suite / i18n / Ribbon / Compare / DTP-Masterpages / Auto-Format / Auto-TOC / Word-InDesign-Shortcuts. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert.

### Neu
- AnnotationType `ellipse` / `triangle` / `rounded_rect`; Toolbar Kreis/Dreieck/Rundrect; Toggle **Füllen** (Outline vs. Fläche)
- Stempel-Presets **Paid**, **Bezahlt**, **Rechnung**, **Datum**; „Als Stempel speichern“ für Custom-Texte
- Toolbar **Absatz** + Menü/Palette Ctrl+Alt+Shift+H: Highlight ganzer Absätze unter der Auswahl
- `selection_to_paragraph_highlight_rects` / `extract_text_paragraphs`

### Geändert
- Docs/Version **2.6.9**; Pinsel-Slider/Color-Picker-Tooltips; Scripting-API erweitert

### Tests / Qualität
- Version **2.6.9** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.9 CLI+Qt (shapes/stamps/paragraph-highlight + ild API)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.6.8 — Windows-Build + Keygen + Scripting

Minor nach **2.6.7**: **runnable Windows-Build-Pfad**, **Keygenerator** (HMAC/Trial) und **headless Scripting** (Python `ild` + PowerShell `ild.ps1`). `build-windows.ps1` erzwingt **64-Bit-Python** (optional `-Allow32Bit`), packt App + `InstantLensKeygen.exe`; `scripts/pack-windows-runnable.py` erzeugt ein startbares Python-Layout-Zip; `install-ild.ps1` legt optional einen **Keygen-Startmenü-Shortcut** an. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert; keine Annotationen-/Word-Suite-/i18n-Features.

### Neu
- `scripts/pack-windows-runnable.py` / `.ps1` — Windows-Runnable-Zip inkl. `WINDOWS-START.md`
- `build-windows.ps1` — 64-Bit-Check · `Allow32Bit` · VERSION.txt im Dist · Keygen in App-Dist
- `install-ild.ps1` — Startmenü-Shortcut „Keygenerator“ (`run-keygen.bat` / `InstantLensKeygen.exe`), `-SkipKeygen`
- Scripting-API `ild` · CLI `python -m ild` · `run-ild.bat` · `scripts/ild.ps1` (open, OCR, Export, Schwärzen, Seiten, Lizenz/Keygen, Encrypt)

### Geändert
- Docs/Version **2.6.8**; Keygen-README (DE); In-App-Hilfe Scripting-Hinweis

### Tests / Qualität
- Version **2.6.8** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.8 CLI (build/pack/keygen HMAC + ild CLI) + Qt (Keygen-Pfade); 2.6.7-Verschlüsselung als Regression
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.6.7 — Verschlüsselung & Rechte

Minor-Feature nach **2.6.6** (Zusatzanforderungen #8): **Verschlüsselung & Rechte** — Passwortschutz mit **AES-256** (pikepdf/qpdf R=6 / AESV3, Fallback AES-128), granulare Owner-Rechte (Druck, Kopieren/Extrahieren, Ändern, Formulare, Zusammenstellen, Annotationen, Barrierefreiheit), Dialog **Verschlüsselung & Rechte…** (Status, setzen, entfernen, Rechte aktualisieren), Öffnen verschlüsselter PDFs mit Passwort-Dialog. Kein Batch, Office-Export, E-Signatur, KI/Cloud, voller Windows-Installer. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert.

### Neu
- `ild_pdf.security` — `EncryptionInfo` · `PdfPermissionFlags` · `get_encryption_info` · `get_permissions` · `update_permissions` · AES-256-bevorzugtes `set_password` · `permissions_from_p` / `algorithm_from_encryption`
- UI: `PdfSecurityDialog` · erweiterter `SetPasswordDialog` (AES-256, Rechte-Checkboxen) · PDF-Menü / Palette `pdf_security` · Shortcut Ctrl+Alt+Shift+P

### Geändert
- Docs/Version **2.6.7**; bestehende Verschlüsseln/Entschlüsseln-Menüpunkte bleiben (nutzen gemeinsame Apply-Pfade)

### Tests / Qualität
- Version **2.6.7** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.7 CLI + Qt (encrypt AES-256 / permissions update/remove + UI-Pfad)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.6.6 — Interaktive Formularerstellung

Minor-Feature nach **2.6.5** (Zusatzanforderungen #7): **Interaktive Formularerstellung** — ausfüllbare AcroForm-Felder (Text, Checkbox, Dropdown) erkennen und erstellen; bestehende Felder ausfüllen/bearbeiten. UI: Toolbar **Formular** (Rechteck ziehen → Feld anlegen), Dialog **Formularfelder…** (ausfüllen, hinzu, löschen, erkennen), PDF-Menü / Palette, Shortcut Ctrl+Alt+Shift+K. Keine Verschlüsselung, E-Signatur, Office-Export, KI/Cloud. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert.

### Neu
- `ild_pdf.acroform` — `create_form_field` · `update_form_field` · `delete_form_field` · `detect_form_candidates` · `apply_form_candidates` · `viewer_rect_to_pdf` / `pdf_rect_to_viewer` · `FormFieldCandidate` / `FormCreateResult`
- Viewer: Werkzeug **Formular** · `FormFieldEditDialog` · erweiterter `FormFieldsDialog` (Checkbox/Dropdown ausfüllen)
- PDF-Menü / Palette `form_fields` · `form_field_create` · `form_field_detect` · Shortcut Ctrl+Alt+Shift+K

### Geändert
- Docs/Version **2.6.6**; Formularfelder-Dialog auch ohne vorhandenes AcroForm

### Tests / Qualität
- Version **2.6.6** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.6 CLI + Qt (form create/detect/fill + UI-Pfad)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.6.5 — Objektmanipulation (Bilder/Vektoren/Tabellen)

Minor-Feature nach **2.6.4** (Zusatzanforderungen #6): **Objektmanipulation** — Bilder, Vektorgrafiken und Tabellen im Dokument verschieben, skalieren, spiegeln oder ersetzen, soweit praktisch mit dem pypdfium2/pikepdf-Stack (PageObjects transformieren + `gen_content`, Bildersatz via Jpeg/Bitmap). UI im Viewer: Werkzeug **Objekt**, Auswahlrahmen mit Handles, Ziehen = Verschieben, Ecken = Skalieren, Dialog für Flip/Ersetzen. Keine Formulare, Verschlüsselung, Office-Export, KI/Cloud. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert.

### Neu
- `ild_pdf.object_edit` — `list_page_objects` · `hit_test_object` · `move_object` · `resize_object` · `flip_object` · `replace_image_object` · `set_object_rect` · `DocumentObject` / `ObjectEditResult`
- Viewer: Werkzeug **Objekt** · `ObjectTransformDialog` · Auswahlrahmen/Handles
- PDF-Menü / Palette `object_edit` · Shortcut Ctrl+Alt+Shift+O

### Geändert
- Docs/Version **2.6.5**

### Tests / Qualität
- Version **2.6.5** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.5 CLI + Qt (object-edit move/resize/flip/replace + UI-Pfad)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.6.4 — Inline-Textbearbeitung + Schriftart-/Formatabgleich

Minor-Feature nach **2.6.3** (Zusatzanforderungen #5): **Inline-Textbearbeitung** — Text direkt im Dokument ändern, löschen oder hinzufügen; praktischer Reflow (Zeilenumbruch in Box-Breite) mit pypdfium2/pikepdf. **Schriftart- & Formatabgleich** erkennt Familie, Größe und Farbe des bestehenden Textes (PDFium) und mappt auf Standard-14 beim Schreiben. UI: Toolbar **Text bearbeiten**, PDF-Menü, Palette, Doppelklick auf Text (Auswahl-Modus), Auswahl → Text bearbeiten. Keine Objektmanipulation, Formulare, Verschlüsselung, Office-Export, KI/Cloud. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert.

### Neu
- `ild_pdf.text_edit` — `hit_test_text` · `detect_text_style_at` · `text_span_from_selection` · `reflow_lines` · `apply_inline_text_edit` · `insert_text_at` · `TextStyle` / `EditableTextSpan`
- Viewer: Werkzeug **Text bearbeiten** · `InlineTextEditDialog` · Doppelklick → Edit
- PDF-Menü / Palette `inline_text_edit` / `selection_text_edit` · Shortcut Ctrl+Alt+Shift+E

### Geändert
- Docs/Version **2.6.4**

### Tests / Qualität
- Version **2.6.4** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.4 CLI + Qt (inline-text-edit + font-match + UI-Pfad)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.6.3 — Erweiterte OCR mit Layout-Erhalt

Minor-Feature nach **2.6.2** (Zusatzanforderungen #4): **Erweiterte OCR** — Scans/Fotos → durchsuchbarer und besser editierbarer Text mit **Layout-Erhalt** (Tesseract-Blöcke, Lesereihenfolge top→bottom/left→right). Ausgabe-Modus **Text mit Layout-Erhalt**; Sidecars `*.ildocr.txt` (Absätze + Block-Metadaten) sowie optional **hOCR** / **TSV**. Integriert in OCR-Dialog (Default) und Scan-/Import-Flow (Default Layout-OCR + hOCR/TSV-Checkboxen). Kein Inline-Textedit, keine Formulare/Verschlüsselung/Office-Export/KI/Cloud. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert.

### Neu
- `OcrOutputMode.LAYOUT_PRESERVE` · `ocr_image_layout` · `OcrLayoutBlock` / `OcrLayoutPage` · `write_layout_sidecars`
- OCR-Dialog: Modus **Text mit Layout-Erhalt** (Default) · Checkboxen hOCR/TSV
- Scan/Import: Layout-OCR Default · hOCR/TSV-Optionen · Sidecars `*.pN.ildocr.{txt,hocr,tsv}`

### Geändert
- Scan-Pipeline Default-OCR von searchable_image → layout_preserve
- Docs/Version **2.6.3**

### Tests / Qualität
- Version **2.6.3** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.3 CLI + Qt (layout-OCR + hOCR/TSV + Scan/OCR-UI)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.6.2 — Scannen mit Tesseract + Drucker-/Scannererkennung

Minor-Feature nach **2.6.1** (Zusatzanforderungen #2): **Scannen / Import** — Seitenbilder vom Scanner (WIA/SANE) oder per Datei-Import in die aktuelle Session; **OCR über Tesseract** (pytesseract) → durchsuchbarer Text / Sidecar `*.ildocr.txt`. **Geräteerkennung** lokal + Netzwerk: Systemdrucker (Qt/Winspool) und Scanner (WIA/PnP bzw. SANE); UI mit Aktualisieren/Neu suchen; Scanner für Scan-Flow, Drucker für Druckziel-Liste. UI **PDF → Scannen / Import…** (Ctrl+Alt+Shift+I) · **Drucker & Scanner…** · Palette · Toolbar „Scan…“. Windows-Deps in Docs (Tesseract winget, WIA). Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert.

### Neu
- `instantlensdoc.core.devices` — `discover_devices` / `list_printers` / `list_scanners` (lokal + Netzwerk)
- `instantlensdoc.core.scan` — Acquire/Import → `insert_scan_pages_into_pdf` + Tesseract-OCR-Bridge
- Dialog **Scannen / Import** · **Drucker & Scanner** · Command-Palette `scan_import` / `devices`
- PDF-Menü · Toolbar „Scan…“ · Shortcut Ctrl+Alt+Shift+I
- Docs: Windows-Install Tesseract (`winget install UB-Mannheim.TesseractOCR`) + WIA-Hinweis

### Geändert
- Bestehende OCR-Pfade (Seite/Region/Batch) unverändert; Scan nutzt dieselbe Tesseract-Bridge
- Qt-Druckdialog bleibt; Druckernamen zusätzlich über Geräte-Dialog listbar
- Docs/Version **2.6.2**

### Tests / Qualität
- Version **2.6.2** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.2 CLI + Qt (scan/import + devices + Tesseract-Pfad)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.6.1 — Seitenmanagement + Schnellvorschau / Inhaltsverzeichnis

Minor-Feature nach **2.6.0** (Zusatzanforderungen #3; Scan übersprungen): **Seitenmanagement** — Seiten per Drag-and-Drop neu anordnen, einfügen, drehen, löschen und Seiten aus anderen PDFs einfügen/zusammenfügen. Sidebar: **Schnellvorschau** (Seitenminiaturen) und klickbares **Inhaltsverzeichnis** (PDF-Outline → Seite). UI **PDF → Seitenmanagement…** (Ctrl+Shift+M) · Palette · Toolbar „Seiten…“; API `ild_pdf.insert_pages_from_pdf`. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert; Scan/OCR folgt separat.

### Neu
- `ild_pdf.insert_pages_from_pdf` / `page_count` — Seiten aus anderem PDF an Position einfügen
- Dialog **Seitenmanagement** (Drag-Reorder · ▲▼ · drehen · leere Seite · duplizieren · löschen · aus PDF einfügen)
- PDF-Menü **Seitenmanagement…** · Command-Palette `page_manage` · Toolbar-Button · Shortcut Ctrl+Shift+M
- Sidebar **Schnellvorschau** (Thumbnails) · **Inhaltsverzeichnis** (Klick/Enter → Seite)

### Geändert
- Bestehende Einzelaktionen (drehen/löschen/reorder/merge-Dialog) bleiben; zentrales Seitenmanagement bündelt sie
- Outline-Label/Navigation: Klick springt zur Seite (neben Doppelklick/Enter)
- Docs/Version **2.6.1**

### Tests / Qualität
- Version **2.6.1** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.1 CLI + Qt (page-manage + insert-from-pdf + Schnellvorschau/TOC + UI-Pfad)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.6.0 — Echtes Schwärzen (Redaktion) + Metadaten-Bereinigung

Minor-Feature nach **2.5.20** (Zusatzanforderungen #1): **Echtes Schwärzen** entfernt ausgewählte Inhalte unwiderruflich aus dem PDF-Content-Stream (Seite→Bild mit schwarzen Zonen; Textschicht weg) — nicht nur Overlay-Balken; optional **Metadaten-Bereinigung** (DocInfo/XMP); UI **Echt schwärzen…** / **Auswahl → Schwärzung** / Palette; Overlay-Bake „Redactions anwenden“ bleibt. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie unverändert; Seitenmanagement **2.6.1**.

### Neu
- `ild_pdf.apply_true_redactions` / `TrueRedactionResult` — irreversibles Schwärzen + optional Meta-Strip
- PDF-Menü **Echt schwärzen…** · **Auswahl → Schwärzung** · Command-Palette
- Settings: Echt-schwärzen DPI · Metadaten bereinigen (Default an)

### Geändert
- `bake_redactions` bleibt Overlay-Modus (Hinweis auf echtes Schwärzen)
- Docs/Version Serie **2.6**

### Tests / Qualität
- Version **2.6.0** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.6**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.6.0 CLI + Qt (true-redact + meta-strip + UI-Pfad)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.20 — OCR Open-Fail-A11y, Theme Ctrl+Shift+C·HexAll-Fail, ildtags Tag−/Clear-Fail-A11y, Export Summary-Fail-A11y

Post-Release-Polish nach **2.5.19**: **OCR-Region** Status-**Open Fail-Path A11y** (Tab/Ordner/Datei ohne Pfad · Open-Exception); **Farben-Themes** Swatch-**Ctrl+Shift+C alle Hex** · **Hex-All Fail-A11y**; **ildtags** **Tag−/Clear Fail-A11y** · Pfad-Copy Fail-A11y; **Export-Presets** **Summary-Copy Fail-A11y**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: Fail-Path A11y bei Öffnen (Pfad fehlt · Open-Exception Tab/Ordner/Datei)
- Farben-Themes: Swatch Ctrl+Shift+C alle Hex · Hex-All Fail-A11y · Menü/Tooltip 2.5.20
- Dokument-Tags: Tag entfernen / Alle Tags entfernen Fail-Path A11y · Pfad-Copy Fail-A11y
- Export-Presets: Summary kopieren Zwischenablage-Fail → A11y Announce

### Tests / Qualität
- Version **2.5.20** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.20 CLI + Qt (OCR Open-Fail-A11y, Theme Ctrl+Shift+C·HexAll-Fail, ildtags Tag−/Clear-Fail-A11y, Export Summary-Fail-A11y)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.19 — OCR Text-Clip-Fail-A11y, Theme Shift+←/→, ildtags Tags-Fail-A11y, Export Pfad/Apply-Fail-A11y

Post-Release-Polish nach **2.5.18**: **OCR-Region** Status-**Text-Copy Clip-Fail A11y**; **Farben-Themes** Swatch-**Shift+←/→ ±2** · **Hex-Copy Fail-A11y**; **ildtags** **Tags-Copy/Paste Fail-A11y**; **Export-Presets** **Pfad-Copy / Apply-fehlt Fail-A11y**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: Fail-Path A11y bei Text kopieren (fehlt/Zwischenablage)
- Farben-Themes: Swatch Shift+←/→ (±2) · Hex-Copy Fail-A11y · Tooltip/A11y 2.5.19
- Dokument-Tags: Tags kopieren/einfügen Fail-Path A11y (leer/bereits vorhanden)
- Export-Presets: Pfad kopieren ohne Ziel · Apply fehlt → A11y Announce

### Tests / Qualität
- Version **2.5.19** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.19 CLI + Qt (OCR Text-Clip-Fail-A11y, Theme Shift+←/→, ildtags Tags-Fail-A11y, Export Pfad/Apply-Fail-A11y)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.18 — OCR Pfad-Fail-A11y, Theme PgUp/Dn·Ctrl+C, ildtags Öffnen⏎, Export JSON-A11y

Post-Release-Polish nach **2.5.17**: **OCR-Region** Status-**Pfad-Copy Fail-Path A11y**; **Farben-Themes** Swatch-**PageUp/PageDown** · **Ctrl+C Hex**; **ildtags** **Öffnen⏎Enter** · Fail-A11y; **Export-Presets** **JSON Imp/Exp A11y** · Ordner-fehlt Fail-A11y. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: Fail-Path A11y bei Pfad kopieren (fehlt/leer/Zwischenablage)
- Farben-Themes: Swatch PageUp/PageDown (±3) · Menü/Tooltip C/Ctrl+C · 2.5.18
- Dokument-Tags: Menü Öffnen\tEnter · `_open_recent_in_app` Fail-A11y
- Export-Presets: JSON Export/Import A11y Announce · Zielordner-fehlt Fail-A11y

### Tests / Qualität
- Version **2.5.18** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.18 CLI + Qt (OCR Pfad-Fail-A11y, Theme PgUp/Dn, ildtags Öffnen⏎, Export JSON-A11y)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.17 — OCR Text-Fail-A11y, Theme Digits 1–6, ildtags F5-Datei, Export CRUD-A11y

Post-Release-Polish nach **2.5.16**: **OCR-Region** Status-**Text-Copy Fail-Path A11y**; **Farben-Themes** Swatch-**Ziffern 1–6**; **ildtags** **F5 → Datei** · **Menü Entf**; **Export-Presets** **CRUD A11y** (Duplizieren/Umbenennen/Löschen). Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: Fail-Path A11y bei Text kopieren (Ergebnis fehlt/leer)
- Farben-Themes: Swatch-Tasten 1–6 → Fokus Swatch · Tooltip/A11y 2.5.17
- Dokument-Tags: F5 Datei öffnen (Recent · Menü) · Entfernen\tEntf
- Export-Presets: Duplizieren/Umbenennen/Löschen → A11y Announce

### Tests / Qualität
- Version **2.5.17** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.17 CLI + Qt (OCR Text-Fail-A11y, Theme Digits, ildtags F5-Datei, Export CRUD-A11y)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.16 — OCR Fail-A11y, Theme Home/End·RMB-Hints, ildtags Tag±-A11y, Export Reorder-A11y

Post-Release-Polish nach **2.5.15**: **OCR-Region** Status-**Fail-Path A11y** (Ergebnis fehlt); **Farben-Themes** Swatch-**Home/End** · **RMB Mid/Dbl-Hinweise**; **ildtags** **Tag± Status/A11y**; **Export-Presets** **Reorder A11y** · **Menü Anwenden⏎**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: Fail-Path A11y wenn Ergebnisdatei fehlt (Tab/Datei öffnen)
- Farben-Themes: Swatch Home/End · RMB-Menü Mid/Dbl/Shift-Hinweise · Tooltip 2.5.16
- Dokument-Tags: Tag hinzufügen/entfernen → Status + A11y Announce
- Export-Presets: Reorder Ctrl+↑↓/Home/End → A11y Announce · Menü Anwenden⏎Enter

### Tests / Qualität
- Version **2.5.16** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.16 CLI + Qt (OCR Fail-A11y, Theme Home/End·RMB, ildtags Tag±-A11y, Export Reorder-A11y)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.15 — OCR F5-Datei, Theme Swatch-Keys, ildtags F4-Ordner, Export F4-Ordner

Post-Release-Polish nach **2.5.14**: **OCR-Region** Status-**F5 → Datei**; **Farben-Themes** Swatch-**Tastatur Space/H/P/N/C · ←/→ · AccessibleName**; **ildtags** **F4 → Ordner**; **Export-Presets** **F4 → Zielordner**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: F5 → Ergebnisdatei öffnen (Status aktiv · Menü-Hinweis Esc/Enter/Ctrl+C/F5)
- Farben-Themes: Swatch fokusierbar · Space/H→HL · P→Stift · N→Notiz · C→Hex · ←/→ · A11y
- Dokument-Tags: F4 Ordner öffnen (Recent · Menü · Status/A11y)
- Export-Presets: F4 Zielordner öffnen (Liste fokussiert · Menü)

### Tests / Qualität
- Version **2.5.15** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.15 CLI + Qt (OCR F5-Datei, Theme Swatch-Keys, ildtags F4-Ordner, Export F4-Ordner)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.14 — OCR F4-Ordner, Theme Dbl-Stift/Notiz, ildtags Pfad, Export Ctrl+Home/End

Post-Release-Polish nach **2.5.13**: **OCR-Region** Status-**F4 → Ordner**; **Farben-Themes** Swatch-**Shift+Doppelklick → Stift** · **Ctrl+Doppelklick → Notiz**; **ildtags** **Ctrl+Shift+C Pfad kopieren**; **Export-Presets** **Ctrl+Home/End Anfang/Ende**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: F4 → Ergebnis-Ordner öffnen (Status aktiv · Menü-Hinweis)
- Farben-Themes: Shift+Doppelklick → Stift · Ctrl+Doppelklick → Notiz
- Dokument-Tags: Ctrl+Shift+C Pfad kopieren (Recent)
- Export-Presets: Ctrl+Home/End an Anfang/Ende verschieben

### Tests / Qualität
- Version **2.5.14** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.14 CLI + Qt (OCR F4-Ordner, Theme Dbl-Stift/Notiz, ildtags Pfad, Export Ctrl+Home/End)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.13 — OCR Ctrl+C/Pfad, Theme Dbl-HL, ildtags F3, Export Ctrl+↑↓

Post-Release-Polish nach **2.5.12**: **OCR-Region** Status-**Ctrl+C Text** · **Ctrl+Shift+C Pfad**; **Farben-Themes** Swatch-**Doppelklick → Highlight**; **ildtags** **F3 Tag entfernen**; **Export-Presets** **Ctrl+↑/↓ Reihenfolge**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: Ctrl+C → Text kopieren · Ctrl+Shift+C → Pfad (Status aktiv)
- Farben-Themes: Doppelklick Swatch → Highlight-Farbe setzen
- Dokument-Tags: F3 Tag entfernen (Recent)
- Export-Presets: Ctrl+↑/↓ Reihenfolge verschieben

### Tests / Qualität
- Version **2.5.13** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.13 CLI + Qt (OCR Ctrl+C/Pfad, Theme Dbl-HL, ildtags F3, Export Ctrl+↑↓)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.12 — OCR Enter→Tab, Theme Mid-Stift/Notiz, ildtags F2, Export Ctrl+Enter

Post-Release-Polish nach **2.5.11**: **OCR-Region** Status-**Enter → Ergebnis-Tab**; **Farben-Themes** Swatch-**Shift+Mittelklick → Stift** · **Ctrl+Mittelklick → Notiz**; **ildtags** **F2 Tag hinzufügen**; **Export-Presets** **Ctrl+Enter Anwenden ohne Schließen**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: Enter → Ergebnis-Tab fokussieren
- Farben-Themes: Shift+Mittelklick → Stift · Ctrl+Mittelklick → Notiz
- Dokument-Tags: F2 Tag hinzufügen (Recent)
- Export-Presets: Ctrl+Enter Anwenden ohne Schließen

### Tests / Qualität
- Version **2.5.12** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.12 CLI + Qt (OCR Enter-Tab, Theme Mid-Stift/Notiz, ildtags F2, Export Ctrl+Enter)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.11 — OCR Esc-Dismiss, Theme Swatch-Mittelklick, ildtags Shift+Entf, Export Ctrl+D

Post-Release-Polish nach **2.5.10**: **OCR-Region** Status-**Esc / Menü „Status schließen“**; **Farben-Themes** Swatch-**Mittelklick → Highlight**; **ildtags** **Shift+Entf** Alle Tags entfernen; **Export-Presets** **Ctrl+D Duplizieren**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: Esc / Menü → Status schließen
- Farben-Themes: Swatch-Mittelklick → Highlight-Farbe setzen
- Dokument-Tags: Shift+Entf/Backspace → Alle Tags entfernen
- Export-Presets: Ctrl+D Duplizieren

### Tests / Qualität
- Version **2.5.11** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.11 CLI + Qt (OCR Esc-Dismiss, Theme Mid-HL, ildtags Shift+Entf, Export Ctrl+D)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.10 — OCR-Region Status-Menü, Theme Swatch→HL/Stift/Notiz, ildtags Ctrl+X, Export F2

Post-Release-Polish nach **2.5.9**: **OCR-Region** Status-**Rechtsklick-Kontextmenü** (Tab/Ordner/Pfad/Text/Datei); **Farben-Themes** Swatch-**RMB → Highlight/Stift/Notiz setzen**; **ildtags** **Ctrl+X** Tags ausschneiden · **Alle Tags entfernen**; **Export-Presets** **F2 Umbenennen**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: Status-Rechtsklick → Kontextmenü (Tab · Ordner · Pfad · Text · Datei)
- Farben-Themes: Swatch-RMB → als Highlight-/Stift-/Notizfarbe setzen
- Dokument-Tags: Ctrl+X Tags ausschneiden · „Alle Tags entfernen“
- Export-Presets: F2 Umbenennen

### Tests / Qualität
- Version **2.5.10** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.10 CLI + Qt (OCR Status-Menü, Theme Swatch-Tool, ildtags Cut, Export F2)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.9 — OCR-Region Alt→Datei·Vorschau, Theme Swatch-Hex, ildtags Ctrl+C/V, Export Pfad kopieren

Post-Release-Polish nach **2.5.8**: **OCR-Region** Status-**Alt+Klick öffnet Ergebnisdatei** und **Tooltip mit Textvorschau**; **Farben-Themes** **Swatch-Klick kopiert einzelne Hex**; **ildtags** **Ctrl+C/Ctrl+V** Tags kopieren/einfügen; **Export-Presets** **Pfad kopieren** (Rechtsklick · Ctrl+Shift+C). Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: Alt+Klick → Ergebnisdatei öffnen · Tooltip Textvorschau
- Farben-Themes: Swatch-Klick → einzelne Hex-Farbe kopieren
- Dokument-Tags: Ctrl+C/Ctrl+V Tags kopieren/einfügen (Recent)
- Export-Presets: Pfad kopieren (RMB · Ctrl+Shift+C)

### Tests / Qualität
- Version **2.5.9** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.9 CLI + Qt (OCR Alt-Open/Preview, Theme Swatch-Hex, ildtags Ctrl+C/V, Export Path-Copy)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.8 — OCR-Region Text kopieren, Theme Hex kopieren, ildtags Tags einfügen, Export Summary kopieren

Post-Release-Polish nach **2.5.7**: **OCR-Region** Status-**Shift+Klick kopiert Ergebnistext** (ohne Fehlerabschnitt); **Farben-Themes** Button **„Hex kopieren“**; **ildtags** Kontextmenü **Tags einfügen** aus Zwischenablage; **Export-Presets** **Summary kopieren** (Rechtsklick · Ctrl+C). Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: Shift+Klick → Ergebnistext kopieren (Fehlerabschnitt ausgelassen)
- Farben-Themes: „Hex kopieren“ → 6 Hex-Farben in Zwischenablage
- Dokument-Tags: Kontextmenü „Tags einfügen“ (Komma/;/Zeilen)
- Export-Presets: Summary kopieren (RMB · Ctrl+C)

### Tests / Qualität
- Version **2.5.8** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.8 CLI + Qt (OCR Text-Copy, Theme Hex-Copy, ildtags Paste, Export Summary-Copy)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.7 — OCR-Region Pfad kopieren, Theme Hex-Tooltip·Custom N/20, ildtags Tags kopieren, Export RMB Ordner·Entf

Post-Release-Polish nach **2.5.6**: **OCR-Region** Status-**Mittelklick/Ctrl+Klick kopiert Ergebnis-Pfad** (Tooltip mit vollem Pfad); **Farben-Themes** Combo-**Tooltip mit 6 Hex-Farben** und **Custom-Zähler N/20**; **ildtags** Kontextmenü **Tags kopieren**; **Export-Presets** **Rechtsklick → Zielordner öffnen** und **Entf löschen**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: Mittelklick/Ctrl+Klick → Ergebnis-Pfad kopieren · Tooltip mit Pfad
- Farben-Themes: Combo-Tooltip 6 Hex · Custom-Zähler N/20
- Dokument-Tags: Kontextmenü „Tags kopieren“ (Zwischenablage)
- Export-Presets: Rechtsklick → Zielordner · Entf/Backspace löschen

### Tests / Qualität
- Version **2.5.7** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.7 CLI + Qt (OCR Pfad-Copy, Theme Hex/N20, ildtags Tags-Copy, Export RMB/Entf)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.6 — OCR-Region Status-Rechtsklick→Ordner, Theme Custom duplizieren, ildtags Sort A–Z/Häufigkeit, Export Tooltip·Apply A11y

Post-Release-Polish nach **2.5.5**: **OCR-Region** Status-**Rechtsklick öffnet Ergebnis-Ordner** (Linksklick bleibt Tab); **Farben-Themes** **Custom duplizieren**; **ildtags** Quick-Tag **Sort A–Z ↔ Häufigkeit** (persistiert); **Export-Presets** **Listen-Tooltip Summary** und **Apply A11y Announcement**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: Status-Rechtsklick → Ordner öffnen (Linksklick → Tab)
- Farben-Themes: Custom duplizieren (Builtins geschützt)
- Dokument-Tags: Quick-Tag Sort A–Z / Häufigkeit (persistiert)
- Export-Presets: Listen-Tooltip DPI·Format·Pfad · Apply A11y

### Tests / Qualität
- Version **2.5.6** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.6 CLI + Qt (OCR Ordner-RMB, Theme Dup, ildtags Sort, Export Tooltip/A11y)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.5 — OCR-Region Status-Klick→Tab, Theme Custom umbenennen, ildtags Tag-Anzahl A–Z, Export ★ aktiv·Duplizieren

Post-Release-Polish nach **2.5.4**: **OCR-Region** **Status-Klick fokussiert Ergebnis-Tab**; **Farben-Themes** **Custom umbenennen**; **ildtags** Quick-Tag **A–Z mit Doc-Anzahl (N)**; **Export-Presets** **★ aktiv** in der Liste und **Duplizieren**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: Status-Klick → Ergebnis-Tab fokussieren
- Farben-Themes: Custom umbenennen (Builtins geschützt)
- Dokument-Tags: Quick-Tag A–Z · Tag-Anzahl (N Docs)
- Export-Presets: ★ aktiv in Liste · Duplizieren

### Tests / Qualität
- Version **2.5.5** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.5 CLI + Qt (OCR Status-Klick, Theme Rename, ildtags Counts, Export ★/Dup)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.4 — OCR-Region Wörter/Zeichen·A11y, Theme Custom löschen·★ Default, ildtags Vorschläge·Quick-Tag, Export-Presets Umbenennen·Doppelklick

Post-Release-Polish nach **2.5.3**: **OCR-Region** Status mit **Wörter/Zeichen** und **A11y Announcement**; **Farben-Themes** **Custom löschen** und **★ Default** in der Combo; **ildtags** **Tag-Vorschläge** beim Hinzufügen und **Quick-Tag-Filter**; **Export-Presets** **Umbenennen** und **Doppelklick Anwenden**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: Wörter/Zeichen im Status · A11y Announcement nach Erfolg
- Farben-Themes: Custom löschen (Builtins geschützt) · ★ Default in Combo
- Dokument-Tags: Tag-Vorschläge (Recent/Index) · Quick-Tag-Filter Combo
- Export-Presets: Umbenennen · Doppelklick/Enter Anwenden

### Tests / Qualität
- Version **2.5.4** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.4 CLI + Qt (OCR Stats/A11y, Theme Delete/★, ildtags Suggest/Quick-Tag, Export Rename/DblClick)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.3 — OCR-Region Ellipsis·Tooltip·Fehlerabschnitt, Theme Merge skip/rename·Import-Log, ildtags Esc-Fokus·Treffer A11y, Export-Presets Live-Pfad·ungültige zählen

Post-Release-Polish nach **2.5.2**: **OCR-Region** Tab-Titel mit **Ellipsis** und **Tooltip voll**, **Fehlerabschnitt wie Batch-OCR**; **Farben-Theme Merge** mit **Kollisionsstrategie skip/rename (_2)** und **Import-Log**; **ildtags** Esc setzt **Fokus zurück auf Liste**, **Trefferanzahl A11y**; **Export-Presets JSON** mit **Live-Pfad-Vorschau**, **ungültige Einträge überspringen + zählen**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: Tab-Titel Ellipsis + Tooltip voll · Fehlerabschnitt wie Batch-OCR (`--- OCR-Fehler ---`)
- Farben-Themes: Merge Kollision skip/rename (`_2`) · Import-Log (kopieren/als TXT)
- Dokument-Tags-Filter: Esc → Fokus Liste · Trefferanzahl AccessibleName/Description
- Export-Presets: Live-Pfad-Vorschau · ungültige JSON-Einträge überspringen + zählen

### Tests / Qualität
- Version **2.5.3** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.3 CLI + Qt (OCR Ellipsis/Fehlerabschnitt, Theme skip/rename/Log, ildtags Esc/A11y, Export Live-Pfad/skip-count)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.2 — OCR-Region Fortschritt·Tab-Titel·Fehler-Toggle, Theme ildcolors-theme-v1 Merge/Ersetzen, ildtags Treffer·Esc·fehlende grau, Export-Presets Duplikat·JSON

Post-Release-Polish nach **2.5.1**: **OCR-Region** mit **bestimmtem Fortschritt**, **Ergebnis-Tab-Titel Seite/Region**, **Fehler anhängen Toggle**; **Farben-Theme JSON** Schema **ildcolors-theme-v1**, **ungültig klar DE**, **Merge vs Ersetzen**; **ildtags-Filter** mit **Trefferanzahl**, **Esc leert Filter**, **fehlende getaggte Recent grau**; **Export-Presets** **Duplikat-Namen ablehnen**, **Export/Import aller Presets JSON** (`ildexportpresets-v1`). Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: Fortschritt (Schritte) · Ergebnis-Tab Titel mit Seite/Region · Fehler anhängen Toggle (persistiert)
- Farben-Themes: Schema `ildcolors-theme-v1` · ungültig klar DE · Import Merge vs Ersetzen
- Dokument-Tags-Filter: Trefferanzahl · Esc leert Filter · fehlende getaggte Recent grau
- Export-Presets: Duplikat-Namen ablehnen · Export/Import aller Presets JSON (`ildexportpresets-v1`)

### Tests / Qualität
- Version **2.5.2** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.2 CLI + Qt (OCR Fortschritt/Titel/Fehler-Toggle, Theme Schema/Merge, ildtags Treffer/Esc/grau, Export Duplikat/JSON)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.1 — OCR-Region Defaults·Abbruch·leer, Theme-Swatches·Default·JSON, ildtags Recent·Clear·Persistenz, Export-Presets max 10

Post-Release-Polish nach **2.5.0**: **OCR-Region** nutzt **DPI/Sprache aus Defaults**, **Abbruch** (Esc/Progress) und **Hinweis bei leerem Ergebnis**; **Farben-Themes** mit **Vorschau-Swatches**, **Als Default speichern**, **Import/Export JSON**; **ildtags** Tag hinzufügen/entfernen am Recent, **Filter Clear**, **Persistenz**; **Export-Presets** benannt **max. 10**, **Anwenden/Löschen**, **Live-Zusammenfassung**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- OCR-Region: DPI/Sprache aus Defaults · Abbruch Esc/Progress · Hinweis bei leerem Ergebnis
- Farben-Themes: Vorschau-Swatches · Als Default speichern · Theme Import/Export JSON (`ildcolors-v1`)
- Dokument-Tags: Tag hinzufügen/entfernen am Recent · Filter Clear · Filter-Persistenz
- Export-Presets: benannte Presets max. 10 · Anwenden/Löschen · Live-Zusammenfassung DPI/Format/Pfad

### Tests / Qualität
- Version **2.5.1** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.1 CLI + Qt (OCR Defaults/Cancel/leer, Theme Swatches/Default/JSON, ildtags Recent/Clear/Persist, Export max10/Apply/Delete/Summary)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.5.0 — PDF-OCR-Region, Annotation-Farben-Themes, Dokument-Tags ildtags-v1, Export-Preset Zuletzt

Minor-Bump nach **2.4.5**: **PDF-OCR-Region** Rechteck wählen → nur Region OCR → Text-Tab; **Annotation-Farben-Themes** vordefinierte Paletten Markieren/Corporate laden; **Dokument-Tags global** Schema **ildtags-v1** über Docs hinweg filterbar in Willkommen/Recent; **Export-Preset** letzte Export-Einstellungen (DPI/Format/Pfad) als Preset **„Zuletzt“** speichern. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Neu / verbessert
- PDF-OCR-Region: Extras → OCR Region (Rechteck)… · Rechteck auf Seite · nur Region OCR · Text-Tab `-ocr-region.txt` · Esc abbricht
- Annotation-Farben-Themes: Markieren / Corporate → 6 Color-Presets (`ildcolors-v1`) · Settings + Toolbar-RMB
- Dokument-Tags: Sidecar `*.ildtags.json` Schema **ildtags-v1** · Welcome/Recent filtert Pfad oder Tag · Anzeige in Liste
- Export-Preset „Zuletzt“: nach Seiten→Bilder / Seite-als-Bild DPI/Format/Pfad speichern · Vorbefüllung nächster Export

### Tests / Qualität
- Version **2.5.0** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.5**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.5.0 CLI + Qt (OCR-Region, Farben-Themes, ildtags-v1, Export Zuletzt)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.4.5 — Auto-Prune Toast OCR-Dauer·Klick erneut, Apply abgebrochen A11y·Vorlagenname, Sync AccessibleName live an/aus, F1 Reset gemeinsamer Helper

Post-Release-Polish nach **2.4.4**: **Thumbnail Auto-Prune** Toast-**Dauer aus OCR-Toast-Settings**, **Klick kopiert Status erneut**; **Quick-Apply Esc** mit **A11y Announcement** und **letztem Template-Namen** im Status; **Sync-Scroll AccessibleName** aktualisiert **live bei Toggle** (**an/aus** im Namen); **F1 TXT Reset Default** über **gemeinsamen Helper** (`template_reset`) wie andere Template-Resets. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- Thumb Auto-Prune: Toast Dauer OCR-Toast-Settings · Klick kopiert Status erneut
- Annotation-Vorlagen: Esc → „Apply abgebrochen“ + Vorlagenname · A11y Announcement
- Sync-Scroll: AccessibleName live bei Toggle (an/aus im Namen)
- F1 Cheat-Sheet TXT: Reset Default über gemeinsamen Helper (`template_reset`)

### Tests / Qualität
- Version **2.4.5** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.4**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.4.5 CLI + Qt (Prune OCR-Dauer/Re-Copy, Apply A11y/Name, Sync live Name, F1 Helper)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.4.4 — Auto-Prune Status kopierbar·Toast optional, Quick-Apply Esc „Apply abgebrochen“, Sync Announcement·AccessibleName, F1 Reset Bestätigung·Fokus+Selektion

Post-Release-Polish nach **2.4.3**: **Thumbnail Auto-Prune** Status **kopierbar** (Klick → Zwischenablage), **Toast optional** in Settings; **Quick-Apply Esc** setzt Status **„Apply abgebrochen“** und **Fokus Toolbar**; **Sync-Scroll** mit **Announcement bei Toggle** und **AccessibleName** am Status-Widget; **F1 TXT Reset Default** mit **Bestätigung nur bei Abweichung** und **Fokus+Selektion**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- Thumb Auto-Prune: Status kopierbar · Toast optional Settings
- Annotation-Vorlagen: Esc → Status „Apply abgebrochen“ · Fokus Toolbar
- Sync-Scroll: Announcement bei Toggle · AccessibleName Status-Widget
- F1 Cheat-Sheet TXT: Reset Default Bestätigung nur bei Abweichung · Fokus+Selektion

### Tests / Qualität
- Version **2.4.4** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.4**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.4.4 CLI + Qt (Prune copy/toast, Apply Esc, Sync A11y, F1 Reset)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.4.3 — Thumb Auto-Prune Status·Intervall/on-write, Quick-Apply Rechtsklick·Esc, Sync-Scroll Tooltip Zustand·A11y, F1 Live·{date}·Reset

Post-Release-Polish nach **2.4.2**: **Thumbnail Auto-Prune** meldet **„N Dateien / X MB entfernt“** in Log/Status und Settings wählt **Intervall oder on-write**; **Annotation Quick-Apply** per **Rechtsklick Vorlage wählen**, **Esc** bricht Apply-Modus ab; **Sync-Scroll** Tooltip zeigt **Zustand an/aus** inkl. **A11y**; **F1 TXT** mit **Live-Vorschau**, **Quick-Insert `{date}`** und **Reset Default**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- Thumb Auto-Prune: Status/Log „N Dateien / X MB entfernt“ · Settings Intervall oder on-write
- Annotation-Vorlagen: Quick-Apply Rechtsklick wählen · Esc bricht Apply-Modus ab
- Sync-Scroll: Tooltip aktueller Zustand an/aus · AccessibleName/Description
- F1 Cheat-Sheet TXT: Live-Vorschau Dateiname · Quick-Insert `{date}` · Reset Default

### Tests / Qualität
- Version **2.4.3** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.4**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.4.3 CLI + Qt (Prune Status/Mode, Quick-Apply RMB/Esc, Sync Tooltip A11y, F1 Live/Insert/Reset)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.4.2 — Thumb-Cache freigegebene MB·Auto-Prune, Templates Quick-Apply·zuletzt, Sync-Scroll Klick-Toggle, F1 TXT {date}_shortcuts.txt

Post-Release-Polish nach **2.4.1**: **Thumbnail Disk-Cache** leeren mit Bestätigung und **freigegebenen MB** in der Statusleiste, **Auto-Prune bei Limit**; **Annotation-Templates** Standard/zuletzt verwendet per Toolbar **Quick-Apply**; **Sync-Scroll** Statusleisten-Klick toggled inkl. Tooltip-Shortcut; **F1 Export TXT** merkt Zielordner und nutzt Template **`{date}_shortcuts.txt`**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- Thumb-Cache: Bestätigung · freigegebene MB Status · Auto-Prune bei Entry-/MB-Limit
- Annotation-Vorlagen: Toolbar Quick-Apply ★ · zuletzt verwendet merken
- Sync-Scroll: Status-Klick toggled · Tooltip mit Shortcut Ctrl+Alt+\
- F1 Cheat-Sheet TXT: Zielordner merken · Template `{date}_shortcuts.txt`

### Tests / Qualität
- Version **2.4.2** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.4**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.4.2 CLI + Qt (Thumb freed-MB/Auto-Prune, Templates Quick/Last, Sync-Klick, F1 TXT dir/template)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.4.1 — Thumb-Cache max MB·leeren·Hit/Miss, Templates Umbenennen/Vorschau/★, Sync-Scroll Status·nur PDF↔PDF, F1 Suche·Drucken·TXT

Post-Release-Polish nach **2.4.0**: **Thumbnail Disk-Cache** max. Größe MB in Settings, „Cache leeren“, optional Hit/Miss Debug in Statusleiste; **Annotation-Templates** Umbenennen/Löschen, Style-Vorschau, Standard-Vorlage ★; **Sync-Scroll** Statusleisten-Indikator an/aus und nur noch **PDF↔PDF**; **F1 Cheat-Sheet** Suche/Filter, Drucken, Export TXT. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- Thumb-Cache: max MB Settings · Cache leeren · Hit/Miss Status optional Debug
- Annotation-Vorlagen: Umbenennen/Löschen · Farb-Vorschau · Standard ★ (`default_id` in ildtmpl-v1)
- Sync-Scroll: Statusleisten-Indikator an/aus · aktiv nur PDF↔PDF
- F1 Cheat-Sheet: Suche/Filter Shortcuts · Drucken · Export TXT (+ PDF)

### Tests / Qualität
- Version **2.4.1** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.4**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.4.1 CLI + Qt (Thumb-Cache MB/Clear/HitMiss, Templates Rename/Preview/★, Sync PDF↔PDF+Status, F1 Filter/Print/TXT)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.4.0 — Thumbnail Disk-Cache, Annotation-Templates ildtmpl-v1, Split-View Sync-Scroll PDF-Tabs, Tastatur-Cheat-Sheet F1

Minor-Bump nach **2.3.5**: **PDF-Seiten-Thumbnail Disk-Cache** (mtime-invalidiert, spürbar bei großen Docs); **Annotation-Templates** Stempel/Highlight-Styles speichern/laden (**ildtmpl-v1**); **Split-View Sync-Scroll** Toggle für zwei PDF-Tabs nebeneinander (Scroll + Seiten-Sync); **Tastatur-Cheat-Sheet** F1 / Hilfe mit Shortcut-Liste DE. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Neu / verbessert
- Thumbnail Disk-Cache: PNG unter `config/thumb_cache/` · Key inkl. mtime/scale · Auto-Invalidierung bei Dateiänderung
- Annotation-Vorlagen: Dialog PDF → Annotation-Vorlagen… · Highlight/Stempel-Styles · Export/Import `ildtmpl-v1`
- Sync-Scroll Split: bei zwei PDF-Tabs Scroll-Ratio + Seiten-Sync (Ctrl+Alt+\); Menü „Sync-Scroll (PDF-Tabs / Split)“
- Tastatur-Cheat-Sheet: F1 / Hilfe → Shortcut-Liste DE · optional PDF-Export

### Tests / Qualität
- Version **2.4.0** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.4**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.4.0 CLI + Qt (Thumb-Cache, ildtmpl-v1, PDF Sync-Scroll, F1 Cheat-Sheet)
- Stubs: KI/Cloud/Stylus/3D/Hooks/Outline/Telemetrie unverändert markiert

## 2.3.5 — Kompression A11y·Status-% announced, Links Reset Bestätigung·Fokus+Selektion, Palette Pin-ersetzen mit Namen, Telemetrie Stubs öffnen Fokus erste Zeile

Post-Release-Polish nach **2.3.4**: **PDF-Kompression** Toggle **AccessibleName/Description** und **Status Ersparnis-% announced**; **URL-Links TXT** Template-**Reset Bestätigung nur bei Abweichung** inkl. **Fokus+Selektion**; **Command Palette** Pin-ersetzen-**Bestätigungsdialog mit Namen** des zu ersetzenden Pins; **Telemetrie-Stub** „Stubs öffnen“ → **Fokus erste Stub-Zeile**, Dialog schließt. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- PDF-Kompression: Toggle AccessibleName/Description · Status-% Screenreader-Announcement
- Links TXT: Reset Default Bestätigung nur bei Abweichung · Fokus+Selektion
- Command Palette: Pin-ersetzen-Dialog mit Namen des zu ersetzenden Pins
- Telemetrie-Stub: „Stubs öffnen“ Fokus erste Stub-Zeile · Dialog schließt · weiter no-op
- Version **2.3.5** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.3**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.3.5 CLI + Qt (Kompression A11y/Status-%, Links Reset Fokus, Palette Pin-Name, Stubs Fokus)
- Stubs: Telemetrie Fokus erste Zeile; KI/Cloud/Stylus/3D/Hooks/Outline unverändert markiert

## 2.3.4 — Kompression Label·A11y, Links TXT Live·Quick-Insert·Reset, Palette Pin-Overflow·ältesten ersetzen, Telemetrie Esc·Stubs öffnen

Post-Release-Polish nach **2.3.3**: **PDF-Kompression** Toggle-Label klar **„Ergebnis nach Kompression öffnen“** inkl. **A11y** (AccessibleName/Description); **URL-Links TXT** **Live-Vorschau Dateiname**, **Quick-Insert `{stem}`/`{date}`**, **Reset Default**; **Command Palette** **Overflow-Hinweis** bei Pin-Limit und Option **ältesten Pin ersetzen**; **Telemetrie-Stub** Info-Dialog **Esc schließt** und Button **„Stubs öffnen“**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Geändert
- PDF-Kompression: Label „Ergebnis nach Kompression öffnen“ · AccessibleName/Description (Dialog + Settings)
- Links TXT: Live-Vorschau Dateiname · Quick-Insert {stem}/{date} · Reset Default (ungültige rot)
- Command Palette: Overflow-Hinweis bei max Pins · Option ältesten Pin ersetzen (Bestätigung)
- Telemetrie-Stub: Esc schließt Info · Button „Stubs öffnen“ · weiter no-op / Toggle disabled
- Version **2.3.4** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.3**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.3.4 CLI + Qt (Kompression Label/A11y, Links Live/Quick/Reset, Palette Overflow/Replace, Telemetrie Esc/Stubs öffnen)
- Stubs: Telemetrie Esc + Stubs öffnen; KI/Cloud/Stylus/3D/Hooks/Outline unverändert markiert

## 2.3.3 — Kompression Toggle Settings·Status-% bei Fehler, Links TXT Template·Zielordner·BOM, Palette Pin Persistenz·Unpin·max Pins, Telemetrie warum Stub + Stubs-Tab

Post-Release-Polish nach **2.3.2**: **PDF-Kompression** **Toggle in Settings merken** und bei Fehler **trotzdem Status mit Ersparnis-%**; **URL-Links TXT-Export** mit Template **`{stem}_links.txt`**, **Zielordner merken** und **UTF-8-BOM Option**; **Command Palette** **Pin-Persistenz**, **Unpin** und Settings **max Pins 3/5/10**; **Telemetrie-Stub** Info kurz **„warum Stub“** plus **Verweis Tab Stubs**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Neu / verbessert
- PDF komprimieren: Öffnen-Toggle Settings merken · Status mit % auch bei Fehler/Öffnen-Fail
- Links TXT: Template `{stem}_links.txt` · Zielordner merken · UTF-8-BOM
- Schnellaktionen Ctrl+K: Pin Persistenz · Unpin · max Pins 3/5/10 Settings
- Telemetrie-Stub: kurz warum Stub · Verweis Settings-Tab Stubs · weiter no-op

### Tests / Qualität
- Version **2.3.3** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.3**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.3.3 CLI + Qt (Kompression Settings/Status-%, Links Template/dir/BOM, Palette Pin-Max/Unpin, Telemetrie why+Stubs)
- Stubs: Telemetrie warum + Stubs-Tab; KI/Cloud/Stylus/3D/Hooks/Outline unverändert markiert

## 2.3.2 — Kompression öffnen·Ersparnis-%, Links Filter·Doppelklick·TXT, Palette Pin·Recent 5/10/20, Telemetrie Toggle disabled·Info-Dialog

Post-Release-Polish nach **2.3.1**: **PDF-Kompression** optional **neues File öffnen** und **Größenersparnis-%** in der Statuszeile; **URL-Links-Sidebar** mit **Suche/Filter**, **Doppelklick springt zur Seite**, **Export URL-Liste TXT**; **Command Palette** mit **Pin** für häufige Befehle und Settings **Recent-Anzahl 5/10/20**; **Telemetrie-Stub** mit **disabled Toggle** (bleibt aus) und **Info-Dialog warum Stub**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Neu / verbessert
- PDF komprimieren: optional neues File öffnen · Ersparnis-% Status
- Links Sidebar: Suche/Filter · Doppelklick → Seite · URL-Liste TXT exportieren
- Schnellaktionen Ctrl+K: Pin häufige Befehle · Recent 5/10/20 Settings
- Telemetrie-Stub: Toggle disabled bleibt · Info-Dialog warum Stub · weiter no-op

### Tests / Qualität
- Version **2.3.2** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.3**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.3.2 CLI + Qt (Kompression open/Ersparnis, Links Filter/Export, Palette Pin/Recent-Max, Telemetrie disabled/Info)
- Stubs: Telemetrie Toggle disabled + Info; KI/Cloud/Stylus/3D/Hooks/Outline unverändert markiert

## 2.3.1 — Kompression Vorher/Nachher·Abbruch·DPI/Q-Presets, Links Validierung·Tooltip·Sidebar Edit/Löschen, Palette Fuzzy·Recent·Esc·Kategorien, Telemetrie-Warntext „keine Datenübertragung“

Post-Release-Polish nach **2.3.0**: **PDF-Kompression** mit **Vorher/Nachher-Größenanzeige**, **Abbruch** im Fortschrittsdialog und **DPI/Qualität-Presets** (Bildschirm/E-Book/Druck); **URL-Links** mit **Live-Validierung**, **Hover-Tooltip**, **Sidebar-Liste** sowie **Bearbeiten/Löschen**; **Command Palette** mit **Fuzzy-Filter**, **letzten Befehlen**, **Esc schließt** und **Kategorien**; **Telemetrie-Stub** Settings-**Warntext „keine Datenübertragung“** (bleibt no-op). Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Neu / verbessert
- PDF komprimieren: Vorher/Nachher-Größe · Abbruch · Presets 72/150/300 DPI · Q50/70/85
- Links: URL Live-Validierung · Hover-Tooltip · Sidebar Liste · Bearbeiten/Löschen
- Schnellaktionen Ctrl+K: Fuzzy-Filter · letzte Befehle · Esc · Kategorie-Gruppen
- Telemetrie-Stub: Settings-Warntext „keine Datenübertragung“ · weiter no-op

### Tests / Qualität
- Version **2.3.1** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.3**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.3.1 CLI + Qt (Kompression size/cancel/presets, Links validate/sidebar, Palette fuzzy/recent/esc, Telemetrie-Warntext)
- Stubs: Telemetrie-Hinweis geschärft; KI/Cloud/Stylus/3D/Hooks/Outline unverändert markiert

## 2.3.0 — PDF-Kompression/Downsample, Link-Annotationen Sidecar+Bake, Ctrl+K Command Palette, Telemetrie-Stub opt-in no-op

Minor-Bump nach **2.2.5**: **PDF-Kompression/Optimierung** mit Qualitäts-Dialog und optionalem **Bilder-Downsample** (pypdfium2-Raster + pikepdf-Replace) → immer **neues File**; **URL-Link-Annotationen** (Rechteck + URI im Sidecar, Klick öffnet Browser, optional Bake als native PDF-Link-Annotation); **Schnellaktionen-Palette** Ctrl+K für häufige Befehle (öffnen, suchen, OCR, export…); **Telemetrie-Stub** klar opt-in Settings „anonym Nutzung melden“ (Default aus, immer no-op). Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert / nicht produktiv (Ink ≠ Stylus).

### Neu / verbessert
- PDF komprimieren / Downsample: Dialog JPEG-Q · Max-Kante · Render-Scale · Downsample-Toggle · Ausgabe neues File
- Link-Werkzeug: Rechteck ziehen → URL (http/https) · Sidecar `type=link` · Klick öffnet Browser · Menü „Link-Annotationen in PDF backen…“
- Schnellaktionen: Ctrl+K Command Palette (filterbar) · Bearbeiten-Menü
- Telemetrie-Stub: Settings-Checkbox opt-in · `report_anonymous_usage` no-op · Stubs-Seite Eintrag

### Packaging / Docs
- Version **2.3.0** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.3**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.3.0 CLI + Qt (Kompression/Downsample, Links/Bake, Palette Ctrl+K, Telemetrie-Stub)
- Stubs: Telemetrie ergänzt; KI/Cloud/Stylus/3D/Hooks/Outline unverändert markiert

## 2.2.5 — PageLabels TXT Live-Vorschau·Quick-Insert {stem}/{date}·Reset Default, Ink Toast Klick→Ink-Tool·A11y wie OCR, Historie Undo Clear Redo·klarer DE-Hinweis, CONTRIBUTING Sync Windows·-NoStart

Post-Release-Polish nach **2.2.4**: **Seitenbeschriftungen** TXT-Export mit **Live-Vorschau Dateiname**, **Quick-Insert `{stem}`/`{date}`** und **Reset Default**; **Ink/Freihand Status-Toast** **Klick fokussiert Ink-Tool**, Announcement **gleicher Pfad wie OCR**; **Dokument-Historie** **Redo nach Undo Clear** und **klarer DE-Hinweis** wenn kein Undo möglich; CONTRIBUTING Sync-Zeile erwähnt **Windows** und optional **`-NoStart`**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert / nicht produktiv (Ink ≠ Stylus).

### Neu / verbessert
- Seitenbeschriftungen: Live-Vorschau Dateiname · Quick-Insert `{stem}`/`{date}` · Reset Default
- Freihand (Ink): Toast-Klick fokussiert Ink-Tool · Announcement wie OCR
- Dokument-Historie: Redo nach Undo Clear · klarer DE-Hinweis ohne Undo
- CONTRIBUTING: Sync Windows · optional `-NoStart`

### Tests / Qualität
- Version **2.2.5** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.2**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.2.5 CLI + Qt (TXT Live/Quick/Reset, Ink Toast-Klick/A11y, Historie Redo/Hinweis, CONTRIBUTING -NoStart)
- Stubs unverändert (nur Versionsmarker)

## 2.2.4 — PageLabels TXT Template {stem}_labels.txt·Zielordner·BOM, Ink Status-Toast Dauer Settings·A11y, Historie Clear-Zähler·Undo Clear, CONTRIBUTING Sync copy-ready Einzeiler

Post-Release-Polish nach **2.2.3**: **Seitenbeschriftungen** TXT-Export mit Template **`{stem}_labels.txt`**, **Zielordner merken** und **UTF-8-BOM Option**; **Ink/Freihand Glättungs-Status** mit **Toast-Dauer aus Settings** und **A11y Announcement**; **Dokument-Historie** nach Clear mit Zähler **„N Einträge entfernt“** und **Undo Clear** (Session-Snapshot, sonst Hinweis); CONTRIBUTING **Sync-Befehl als eine Zeile copy-ready**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert / nicht produktiv (Ink ≠ Stylus).

### Neu / verbessert
- Seitenbeschriftungen: TXT-Template `{stem}_labels.txt` · Zielordner merken · UTF-8-BOM
- Freihand (Ink): Status „Glättung angewandt“ Toast-Dauer Settings · A11y
- Dokument-Historie: Clear-Zähler „N Einträge entfernt“ · Undo Clear (Session) bzw. Hinweis
- CONTRIBUTING: Sync copy-ready Einzeiler

### Tests / Qualität
- Version **2.2.4** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.2**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.2.4 CLI + Qt (TXT template/dir/BOM, Ink toast/A11y, Historie Clear-Zähler/Undo, CONTRIBUTING Sync)
- Stubs unverändert (nur Versionsmarker)

## 2.2.3 — PageLabels Vorschau Scroll-Liste 20·Export TXT, Ink Undo-Glätten Redo·Status „Glättung angewandt“, Historie Clear optional Filter·Export gefilterte Sicht, CONTRIBUTING Exitcode-Tabelle kurz + Link smoke_ild.py

Post-Release-Polish nach **2.2.2**: **Seitenbeschriftungen** mit **Scroll-Liste der ersten 20 Labels** und **Export Labels als TXT**; **Ink/Freihand Glätten** mit **Redo ok** nach Undo und Status **„Glättung angewandt“**; **Dokument-Historie** **Clear optional nur aktuellen Filter** und **Export gefilterte Sicht**; CONTRIBUTING **Exitcode-Tabelle kurz** + Link zu [`scripts/smoke_ild.py`](scripts/smoke_ild.py). Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert / nicht produktiv (Ink ≠ Stylus).

### Neu / verbessert
- Seitenbeschriftungen: Scroll-Liste erste 20 · Labels als TXT exportieren
- Freihand (Ink): Redo nach Glätten ok · Status „Glättung angewandt“
- Dokument-Historie: Clear optional nur Filter · Export gefilterte Sicht
- CONTRIBUTING: Exitcode-Tabelle kurz · Link `scripts/smoke_ild.py`

### Tests / Qualität
- Version **2.2.3** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.2**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.2.3 CLI + Qt (Preview-Scroll/TXT, Ink redo/status, Historie Clear-Filter/Export, CONTRIBUTING)
- Stubs unverändert (nur Versionsmarker)

## 2.2.2 — PageLabels Range-Überlappung DE·Vorschau erste Labels, Ink Glättungsstärke·Undo eigener Stack-Eintrag, Historie Doppelklick→Seite·Clear Bestätigung, CONTRIBUTING Sync-Einzeiler=sync-ild.ps1 + smoke Beispiel

Post-Release-Polish nach **2.2.1**: **Seitenbeschriftungen** Range-Editor mit **Validierung überlappender Ranges (DE)** und **Vorschau erste Labels**; **Ink/Freihand Glätten** mit **Strength Settings** (leicht/mittel/stark) und **Undo nach Glätten als eigener Stack-Eintrag**; **Dokument-Historie** **Doppelklick springt zur Seite** (wenn `page` im Eintrag) und **Leeren mit Bestätigung**; CONTRIBUTING **Sync-Einzeiler = sync-ild.ps1-Pfad** + **Smoke-Beispielkommando**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert / nicht produktiv (Ink ≠ Stylus).

### Neu / verbessert
- Seitenbeschriftungen: Überlappungs-Validierung DE · Live-Vorschau erste Labels
- Freihand (Ink): Glättungsstärke leicht/mittel/stark · Glätten = eigener Undo-Eintrag
- Dokument-Historie: Doppelklick → Seite · Clear mit Bestätigung
- CONTRIBUTING: Sync-Einzeiler = `sync-ild.ps1`-Pfad · Smoke-Beispiel `python scripts\smoke_ild.py --json`

### Tests / Qualität
- Version **2.2.2** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.2**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.2.2 CLI + Qt (Range-Overlap/Preview, Ink strength/undo-smooth, Historie Doppelklick/Clear, CONTRIBUTING)
- Stubs unverändert (nur Versionsmarker)

## 2.2.1 — PageLabels Range-Editor·PDF-Import·Reset arabisch 1…, Ink Strichstärke/Farbe·letzter Strich·Glätten, Historie-Panel 50·Filter·Export JSON, smoke Stub manual-only + CONTRIBUTING Sync

Post-Release-Polish nach **2.2.0**: **Seitenbeschriftungen** Dialog mit **Range-Editor**, **Import aus PDF**, **Reset arabisch 1…**; **Ink/Freihand** nutzt **Strichstärke/Farbe**, **Löschen letzter Strich**, optional leichte **Glättung**; **Dokument-Historie** als Panel (**letzte 50**, Filter Aktionstyp, **Export JSON**); Workflow-Stub klar **manual only**; CONTRIBUTING **Sync-Einzeiler**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert / nicht produktiv (Ink ≠ Stylus).

### Neu / verbessert
- Seitenbeschriftungen: Range-Editor · Aus PDF importieren · Reset arabisch 1…
- Freihand (Ink): Strichstärke/Farbe · Ink− letzter Strich · Glätten optional leicht
- Dokument-Historie: Panel letzte 50 · Filter Aktionstyp · Export JSON
- `.github/workflows/smoke-ild.yml`: klarer **manual only**-Kommentar; CONTRIBUTING Sync-Einzeiler

### Tests / Qualität
- Version **2.2.1** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.2**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.2.1 CLI + Qt (Range/Import/Reset, Ink stroke/delete/smooth, Historie-Panel, workflow manual-only)
- Stubs unverändert (nur Versionsmarker)

## 2.2.0 — Seitenbeschriftungen (Sidecar+PageLabels), Freihand-Ink Polyline+Undo, Dokument-Historie ildhist-v1, smoke_ild CONTRIBUTING/CI-Stub

Minor-Bump nach **2.1.5**: **PDF-Seitenbeschriftungen** benutzerdefinierte Labels (i, ii, 1…) in Sidecar speichern/anzeigen, optional **PDF PageLabels** via pikepdf; **Ink/Freihand** einfache Maus-Polyline-Annotation (Sidecar + Undo, kein Stylus); **Dokument-Historie** lokale Änderungslog-Datei pro Doc (**ildhist-v1**) mit Zeitstempeln; **CI-Liste** `smoke_ild` in CONTRIBUTING/Docs, optional GitHub-Actions-Workflow-Stub (nur lokal dokumentiert). Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert / nicht produktiv (Ink ≠ drucksensitiver Stylus).

### Neu / verbessert
- Seitenbeschriftungen: Dialog PDF → „Seitenbeschriftungen…“ · Sidecar-Meta `page_labels` · optional `/PageLabels` schreiben
- Freihand (Ink): Toolbar-Werkzeug · Polyline Maus · Sidecar `points` · Undo über AnnotationStore
- Dokument-Historie: `*.ildhist.json` Schema **ildhist-v1** · Menü „Dokument-Historie…“
- CONTRIBUTING.md + `.github/workflows/smoke-ild.yml` Stub (lokal / manuell)

### Packaging / Docs
- Version **2.2.0** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.2**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.2.0 CLI + Qt (Labels/Ink/ildhist/CONTRIBUTING)
- Stubs unverändert (nur Versionsmarker)

## 2.1.5 — Import-Copy Toast OCR-Dauer·Klick Status/Log, Mess/Diff-Reset Helper·Esc verwirft, smoke Fail-error max 200…, FEATURES.md lokal Sync in Info

Post-Release-Polish nach **2.1.4**: **Import-Status-Toast** Dauer aus **OCR-Toast-Settings**, **Klick fokussiert Statusleiste/Log** falls vorhanden; **Mess-CSV Reset** und **Diff-TXT Reset** nutzen **gemeinsamen Helper** (`template_reset`), **Esc im Feld verwirft Edit** (nicht speichern); **smoke_ild.py `--json`** Fail-`error` **max 200 Zeichen** mit **…**, Docs-Beispiel Fail; **INFO** Hinweis **FEATURES.md lokal sync**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert / nicht produktiv.

### Neu / verbessert
- Import-Copy Toast: Dauer OCR-Settings · Klick → Statusleiste/Log fokussieren
- Mess-Reset + Diff-Reset: gemeinsamer Helper · Esc im Feld verwirft Edit
- `scripts/smoke_ild.py`: Fail-`error` Truncate max 200… · Docs Fail-Beispiel
- INFO: FEATURES.md lokal sync Hinweis (Version 2.1.5)

### Tests / Qualität
- Version **2.1.5** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.1**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.1.5 CLI + Qt (Import-Toast-Klick, Mess/Diff Esc+Helper, smoke_ild truncate, FEATURES lokal)
- Stubs unverändert

## 2.1.4 — Import-Status Clipboard·Toast·A11y, Mess-Template Reset Bestätigung≠Default·Fokus+Selektion, Diff-TXT Quick-Insert·Reset Default, smoke_ild --json Fail checks[].error·Exit=ok

Post-Release-Polish nach **2.1.3**: **PDF-Kommentar-Import** „Status kopieren“ schreibt in die **Zwischenablage** und zeigt **Toast + A11y Announcement** (OCR/HC-Pipeline); **Mess-CSV Reset Default** mit **Bestätigung nur bei Abweichung** und **Fokus+Selektion**; **Diff-TXT Template** mit **Quick-Insert-Buttons** und **Reset Default** (Bestätigung nur bei Abweichung · Fokus+Selektion); **smoke_ild.py `--json`** bei Fail liefert **`checks[].error` Text**, **Exitcode spiegelt `ok`**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert / nicht produktiv.

### Neu / verbessert
- Kommentar-Import Status kopieren: Clipboard + Toast (OCR-Dauer) + A11y Announcement
- Mess-CSV: Reset Default · Bestätigung nur bei Abweichung (Leer≡Default) · Fokus+Selektion
- Diff-TXT: Quick-Insert `{stemA}`/`{stemB}`/`{mode}`/`{page}`/`{date}` · Reset Default · Fokus+Selektion
- `scripts/smoke_ild.py`: Fail-JSON `checks[]` mit `{name,error}` · Exit 0↔ok=true / 1↔ok=false

### Tests / Qualität
- Version **2.1.4** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.1**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.1.4 CLI + Qt (Import-Toast-A11y, Mess-Reset-Confirm/Focus, Diff-TXT Quick-Insert/Reset, smoke_ild JSON-error/exit)
- Stubs unverändert

## 2.1.3 — Kommentar-Import Status ersetzt/übersprungen/neu·kopierbar, Mess-CSV Live-Template {stem}_measures.csv·Quick-Insert, Diff-TXT {stemA}_vs_{stemB}_{mode}.txt Live·ungültige rot, smoke_ild --json Schema+Beispiel

Post-Release-Polish nach **2.1.2**: **PDF-Kommentar-Import** Status detailliert **„ersetzt X, übersprungen Y, neu Z“** mit **kopierbarem Text** (Status kopieren); **Messwerte-CSV** Live-Dateiname-Template **`{stem}_measures.csv`** inkl. **Quick-Insert** `{stem}`/`{date}` und ungültige Platzhalter rot; **Textlayer Diff-TXT** Default-Template **`{stemA}_vs_{stemB}_{mode}.txt`** mit **Live-Vorschau** und **ungültigen Platzhaltern rot**; **smoke_ild.py `--json`** Felder **`ok`**, **`checks[]`**, **`duration_ms`**, **`version`** inkl. **Beispiel in Hilfe/Docs**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert / nicht produktiv.

### Neu / verbessert
- Kommentar-Import: Status **ersetzt / übersprungen / neu** · Dialog **Status kopieren** (Dry-Run + Ergebnis)
- Mess-CSV: Live-Template `{stem}_measures.csv` · Quick-Insert · ungültige rot · Reset
- Diff-TXT: Template `{stemA}_vs_{stemB}_{mode}.txt` · Quick-Insert `{mode}` · Live-Vorschau · ungültige rot
- `scripts/smoke_ild.py`: `--json` Schema `ok`/`checks`/`duration_ms`/`version` · Beispiel in Hilfe + INFO

### Tests / Qualität
- Version **2.1.3** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.1**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.1.3 CLI + Qt (Status-Copyable, Mess-CSV-Template, Diff-TXT-Mode, smoke_ild JSON-Schema)
- Stubs unverändert

## 2.1.2 — Kommentar-Import Sidecar-Toggle·Status N/M, Mess-CSV Typ/Seite/Wert/Einheit·Ordner·BOM, Textlayer Side-by-Side·TXT-Template, smoke_ild --json·ms

Post-Release-Polish nach **2.1.1**: **PDF-Kommentar-Import** mit Toggle **„Nach Import Sidecar speichern“** und Status **„N importiert, M übersprungen“**; **Messwerte-CSV** Spalten **Typ,Seite,Wert,Einheit**, **Zielordner merken**, **UTF-8-BOM Option**; **Textlayer-Diff TXT** mit **Unified/Side-by-Side Toggle** und **Dateiname-Template**; **smoke_ild.py** **`--json` Summary**, **Laufzeit ms**, in Docs erwähnt. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert / nicht produktiv.

### Kommentar-Import / Messung
- Dry-Run-Dialog: Checkbox Sidecar speichern (persistiert); Statuszeile „N importiert, M übersprungen“
- Mess-CSV: Spalten Typ,Seite,Wert,Einheit; letzter Zielordner; BOM-Checkbox vor Speichern

### Vergleich / CI
- Textlayer: Side-by-Side Toggle (Panel + TXT); TXT-Dateiname-Template `{stemA}_vs_{stemB}_p{page}_text.diff.txt`
- `scripts/smoke_ild.py`: `--json` (ok/version/duration_ms/checks) · Laufzeit ms · Docs (INFO/FEATURES)

### Packaging / Docs
- Version **2.1.2** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.1**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.1.2 CLI + Qt (Sidecar-Toggle/Status, Mess-CSV Spalten/BOM/Ordner, Side-by-Side/Template, smoke_ild --json)

---

## 2.1.1 — Kommentar-Import Dry-Run·Duplikate·Fortschritt, Messung Snap·Labels·CSV, Textlayer Ignore-WS·Nur-Diff·TXT, smoke_ild Exit/--qt

Post-Release-Polish nach **2.1.0**: **PDF-Kommentar-Import** mit **Dry-Run-Zählern**, **Duplikat-Strategie** (keep/skip/replace), **Fortschrittsdialog** und **Abbruch**; **Messung** mit optionalem **Snap-to-Annotation**, **persistenter Label-Anzeige** (bei mm/px-Toggle) und **Messwerte-CSV-Export**; **Textlayer-Diff** mit **Ignore-Whitespace**, **Nur-Unterschiede** und **Export Unified Diff TXT**; **smoke_ild.py** Exit-Codes **0/1/2**, optional **`--qt`/`--skip-qt`**, kurze **DE-Hilfe**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert / nicht produktiv.

### Kommentar-Import / Messung
- Dry-Run vor Import (Kandidaten/Duplikate/übersprungen/Seiten); Duplikat-Dialog keep/skip/replace; QProgressDialog + Abbrechen
- Snap-Toolbar-Toggle; Labels bei Einheit-Wechsel aktualisieren; Menü „Messwerte als CSV exportieren…“

### Vergleich / CI
- Textlayer: Checkboxen Ignore-Whitespace + Nur-Unterschiede; Button „Diff TXT…“
- `scripts/smoke_ild.py`: Exit 0/1/2 · `--qt` / `--skip-qt` · `-h` DE-Hilfe

### Packaging / Docs
- Version **2.1.1** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.1**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.1.1 CLI + Qt (Dry-Run/Snap/CSV/Ignore-WS/TXT/smoke_ild)

---

## 2.1.0 — PDF-Kommentar-Import, Messung Fläche+Winkel·mm/px, Textlayer-Diff, Nightly-Smoke

Minor-Bump nach **2.0.5**: **native PDF-Markup → Sidecar** (pikepdf, grob); **Messwerkzeug Fläche (Rechteck) + Winkel (zwei Linien)** mit Anzeige-Einheit **mm/px Toggle**; **PDF-Vergleich Textlayer-Diff** (nicht nur Raster) im Diff-Panel; **Nightly-Smoke** `scripts/smoke_ild.py` (CLI+Import). Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert / nicht produktiv.

### Annotationen / Messung
- PDF-Kommentare importieren (native): Highlight/Underline/Text/FreeText/Stamp/Square/Line/Ink… → Sidecar; Link/Widget übersprungen; Menü PDF
- Messwerkzeug: **Fläche** (Rechteck, mm²/px²) + **Winkel** (erster Strahl ziehen, zweiter Endpunkt klicken); Toolbar **Maß:mm/px** Toggle

### Vergleich / CI
- PDF vergleichen: Checkbox **Textlayer-Diff** → Unified Diff im Diff-Panel (pypdfium2 + difflib)
- `scripts/smoke_ild.py`: Version/Imports/CLI/--version/Measure/Textlayer/Native-Import/CHANGELOG

### Packaging / Docs
- Version **2.1.0** (App / `ild_pdf` / ISS / Smoke / Docs); Serie **2.1**; `docs/VERSION` + `VERSION.txt`
- Smoke: 2.1.0 CLI + Qt (Import/Messung/Textlayer/smoke_ild)

---

## 2.0.5 — Multi-Doc Reset Bestätigung≠Default·Fokus+Selektion, Portfolio Footer-Filter übersprungen·leer bei 0, HC-Toast A11y wie OCR, install-ild -Quiet Summary·Exit 0

Post-Release-Polish nach 2.0.4: **Multi-Dokument-Suche Reset Default** mit **Bestätigung nur bei Abweichung** und **Fokus+Selektion**; **Portfolio-Extrakt** Footer-**Klick filtert übersprungene** (Toggle), **leerer Footer bei Zähler 0**; High-Contrast Toast nutzt **gleiche Announcement-Pipeline wie OCR-Toast** (AccessibleName + Clear nach Timeout); **install-ild.ps1 -Uninstall -Quiet**: **Exit 0 auch wenn nichts zu entfernen**, **Kurz-Summary auf stdout**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert / nicht produktiv.

### Multi-Doc / Portfolio
- Multi-Doc-CSV Reset Default: Bestätigung nur bei Abweichung (Leer≡Default); Fokus+Selektion wie Ann.-Template
- Portfolio-Extrakt: Footer-Klick → Filter übersprungene (Toggle); Footer leer wenn extrahiert=0 und übersprungen=0

### Accessibility / Installer
- High-Contrast Ctrl+Alt+H: `_show_hc_toast` / `_announce_hc_toast` wie OCR-Defaults-Toast-Pipeline
- `scripts/install-ild.ps1`: `-Quiet -Uninstall` Kurz-Summary `entfernt=N fehlend=M Exit=0`; nichts zu entfernen = Exit 0

### Packaging / Docs
- Version **2.0.5** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- About Serie **2.0**; Smoke: Multi-Doc Reset-Confirm/Focus, Portfolio Footer-Filter/leer, HC OCR-Pipeline, Quiet-Summary (CLI + Qt)

---

## 2.0.4 — Multi-Doc Template Quick-Insert {date}/{query}·ungültige rot·Reset Default, Portfolio Footer extrahiert/übersprungen·Ordner öffnen, HC-Toast Dauer OCR·A11y, install-ild Log-Pfad·-Quiet

Post-Release-Polish nach 2.0.3: **Multi-Dokument-Suche CSV-Template** mit **Quick-Insert `{date}`/`{query}`**, **ungültige Platzhalter rot**, Button **Reset Default**; **Portfolio-Extrakt** Footer **„extrahiert X, übersprungen Y“** und Button **Ordner öffnen**; High-Contrast Toast **Dauer aus OCR-Toast-Settings** + **Accessibility-Announcement**; **install-ild.ps1 -Uninstall** gibt **Log-Datei-Pfad** aus, **-Quiet** unterdrückt Prompts. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert / nicht produktiv.

### Suche / Portfolio
- Multi-Doc-CSV: Quick-Insert `{date}`/`{query}`; ungültige Platzhalter rot in Live-Vorschau; Reset Default
- Portfolio-Extrakt: Footer „extrahiert X, übersprungen Y“; Button „Ordner öffnen“

### Accessibility / Installer
- High-Contrast Ctrl+Alt+H: Toast-Dauer aus OCR-Defaults-Toast (Settings 1/2/3 s) + A11y-Announcement
- `scripts/install-ild.ps1`: `-Uninstall` schreibt Log und gibt Pfad aus; `-Quiet` ohne Prompt

### Version / Docs
- Version **2.0.4** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- About Serie **2.0**; Smoke: Multi-Doc Quick-Insert/Invalid/Reset, Portfolio Footer/Ordner, HC Toast Dauer/A11y, install-ild Log/Quiet (CLI + Qt)

## 2.0.3 — Multi-Doc CSV Zielordner·Live-Template, Portfolio Extrakt Abbruch·Teilergebnis·Status, HC-Toast·UI-Reset≠100, install-ild fehlende Shortcuts ok

Post-Release-Polish nach 2.0.2: **Multi-Dokument-Suche CSV** merkt **Zielordner**, Live-Dateiname-Template **`{date}_multisearch.csv`**; **Portfolio-Extrakt** mit **Abbruch**, **Teilergebnis behalten** und **Statuszählung**; High-Contrast Shortcut Toast **„High-Contrast an/aus“**; UI-Skala Reset **Bestätigung nur bei ≠100 %**; **install-ild.ps1 -Uninstall**: fehlende Shortcuts **kein Fehler** (Log-Zeile, Exit 0). Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert / nicht produktiv.

### Suche / Portfolio
- Multi-Doc-CSV: Zielordner merken; Live-Template `{date}_multisearch.csv` mit Vorschau
- Portfolio-Extrakt: Abbruch möglich; Teilergebnis behalten; Statuszählung extrahiert/umbenannt/abgebrochen

### Accessibility / Installer
- High-Contrast Ctrl+Alt+H: Toast „High-Contrast an“ / „High-Contrast aus“
- UI-Skala Reset 100 %: Bestätigung nur wenn aktuell ≠ 100 %
- `scripts/install-ild.ps1`: `-Uninstall` — fehlende Shortcuts Log-Zeile, kein Fehler

### Version / Docs
- Version **2.0.3** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- About Serie **2.0**; Smoke: Multi-Doc CSV-Ordner/Template, Portfolio Cancel/Teilergebnis/Status, HC-Toast, Scale-Reset-Confirm, install-ild missing-ok (CLI + Qt)

## 2.0.2 — Multi-Doc CSV Doc/Seite/Snippet/Match·BOM·Regex-Status, Portfolio Extrakt Ordner/Rename/Fortschritt, UI-Skala Reset 100 %·HC Ctrl+Alt+H, install-ild -Uninstall

Post-Release-Polish nach 2.0.1: **Multi-Dokument-Suche CSV** mit Spalten **Doc,Seite,Snippet,Match**, Option **UTF-8 BOM**, klarer **Regex-Fehlerstatus**; **Portfolio-Extrakt** merkt **Zielordner**, **Namenskollision → Umbenennen** (_2/_3), **Fortschrittsanzeige**; **UI-Schrift Skala** Button **Reset 100 %**; High-Contrast Shortcut **Ctrl+Alt+H**; **install-ild.ps1** Schalter **-Uninstall** entfernt Shortcuts, **Exit-Codes dokumentiert**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert / nicht produktiv.

### Suche / Portfolio
- Multi-Doc-CSV: Spalten Doc,Seite,Snippet,Match; BOM an/aus; Regex-Fehler im Status
- Portfolio-Extrakt: letzter Zielordner; Kollision umbenennen; Fortschritt ≥2 Dateien

### Accessibility / Installer
- UI-Skala: Button „Reset 100 %“ (Settings, Live)
- High-Contrast: Shortcut **Ctrl+Alt+H** (statt Ctrl+Alt+Shift+H)
- `scripts/install-ild.ps1`: `-Uninstall` entfernt Startmenü+Desktop; Exit 0/1 dokumentiert

### Version / Docs
- Version **2.0.2** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- About Serie **2.0**; Smoke: Multi-Doc CSV/BOM/Regex-Status, Portfolio Extrakt/Rename/Fortschritt, Scale-Reset, HC Ctrl+Alt+H, install-ild Uninstall (CLI + Qt)

## 2.0.1 — Multi-Doc Case/Regex/CSV·Fortschritt, Portfolio Sidebar·Auswahl·leer, High-Contrast Persistenz·UI-Skala live, install-ild Idempotenz

Post-Release-Polish nach 2.0.0: **Multi-Dokument-Suche** Optionen **Aa / Wort / Regex**, **Treffer-CSV-Export**, **Fortschrittsanzeige** bei vielen Docs; **PDF-Portfolios** **Inhaltsliste in der Sidebar**, **Auswahl extrahieren**, Hinweis bei **leerer Collection**; **High-Contrast** sofort persistieren; **UI-Schrift Skala 100/125/150 %** mit **Live-Vorschau** in Settings; **install-ild.ps1** Schalter **-NoDesktop**, **Idempotenz** (Verknüpfungen aktualisieren), DE-Meldungen, Hinweis auf **sync-ild.ps1**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert / nicht produktiv.

### Suche / Portfolio
- Multi-Dokument-Suche: Case / Whole-word / Regex; Treffer CSV; Fortschritt ≥3 PDFs
- Portfolio: Sidebar-Inhaltsliste; Auswahl extrahieren; leere Collection-Hinweis

### Accessibility / Installer
- High-Contrast Toggle speichert und wendet sofort an
- UI-Schrift Skala 100/125/150 % Live-Vorschau (Settings)
- `scripts/install-ild.ps1`: `-NoDesktop`, idempotent, DE, sync-ild.ps1-Hinweis

### Packaging / Docs
- Version **2.0.1** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- About Serie **2.0**; Smoke: Multi-Doc-Optionen/CSV/Fortschritt, Portfolio Sidebar/Auswahl/leer, Font-Skala, install-ild (CLI + Qt)

---

## 2.0.0 — Multi-Dokument-Suche, PDF-Portfolios, Accessibility High-Contrast·UI-Schrift, install-ild.ps1

Major-Release nach 1.9.5: **Multi-Dokument-Suche** Volltext (Textlayer) über alle offenen PDFs mit **zentraler Trefferliste** (Ctrl+Shift+F); **PDF-Portfolios** erstellen/öffnen/extrahieren (pikepdf Attachments + `/Collection`); **Accessibility** High-Contrast Theme Toggle + größere UI-Schrift in Settings (Document Outline Vorlesen bleibt Stub); **install-ild.ps1** legt Startmenü-Shortcut + optional Desktop-Link an (User-Profil, ohne Admin). About zeigt Serie **„2.0“**. Stubs KI/Cloud/Stylus/3D/Plugin-Hooks unverändert klar markiert / nicht produktiv.

### Suche / Portfolio
- Multi-Dokument-Suche: zentrale Trefferliste über offene PDFs; Sprung per Doppelklick
- PDF-Portfolio-Dialog: Dateien → Container-PDF; Öffnen/Listen/Extrahieren

### Accessibility / Installer
- High-Contrast Theme (Ansicht + Settings); UI-Schriftgröße 9–20 pt
- Outline-Vorlesen-Button bleibt Stub (Geplant / keine Aktion)
- `scripts/install-ild.ps1`: Startmenü + optional Desktop (ohne Admin)

### Packaging / Docs
- Version **2.0.0** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- About Serie **2.0**; Smoke: Multi-Doc-Suche, Portfolio, High-Contrast/UI-Font, install-ild (CLI + Qt)

---

## 1.9.5 — Anhänge Footer-Filter, Quick-Stempel Esc→Toolbar·Ctrl+Shift+S, CSV Combobox-Reset·A11y, Stubs Geplant-Badge

Post-Release-Polish nach 1.9.4: **PDF-Anhänge** Footer-Klick filtert Liste auf **umbenannt/übersprungen** (Toggle), **leerer Footer wenn Zähler 0**; **Quick-Stempel** Esc → **Fokus Toolbar**, Shortcut **Ctrl+Shift+S** = **Standard-Stempel ★** (Speichern unter → Ctrl+Alt+Shift+U); **Tabellen-CSV** Abbruch setzt **Trennzeichen-Combobox synchron** zurück, **A11y-Announcement beim Speichern**; **Settings-Stubs** Info-Dialog mit **Kurzbeschreibung** + Badge **„Geplant“**, **Esc schließt**. Stubs klar markiert / nicht produktiv.

### PDF / Anhänge / Stempel
- Anhänge: Footer-Klick → Filter umbenannt/übersprungen (Toggle); Footer leer wenn alle Zähler 0
- Quick-Stempel: Esc → Fokus Quick-Stempel-Button; Ctrl+Shift+S → Standard-Stempel ★

### OCR / Stubs
- Tabellen-CSV-Vorschau: Combobox bei Abbruch/Esc synchron zurück; Speichern mit A11y-Announcement
- Settings-Tab „Stubs“: Info-Dialog Kurzbeschreibung + Badge „Geplant“; Esc schließt

### Packaging / Docs
- Version **1.9.5** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- Smoke: Anhänge Footer-Filter/leer, Quick Esc-Fokus·Ctrl+Shift+S, CSV Combobox-Reset·A11y, Stubs Geplant-Badge (CLI + Qt)

---

## 1.9.4 — Anhänge Status-Footer kopierbar, Quick-Stempel Esc·Zoom/Opacity, CSV Delim Persistenz/Reset, Stubs FEATURES-Status·Doppelklick

Post-Release-Polish nach 1.9.3: **PDF-Anhänge** Statuszählung als **Footer** „hinzugefügt X, umbenannt Y, übersprungen Z“ **kopierbar**; **Quick-Stempel Esc** → Status **„Platzieren abgebrochen“**, **Zoom/Opacity** wie Signatur merken falls vorhanden; **Tabellen-CSV** Live-Trennzeichen **Persistenz erst bei Speichern**, **Vorschau-Reset bei Abbruch**; **Settings-Stubs** FEATURES-Link bei fehlender Datei → **Statushinweis** statt Crash, **Doppelklick Stub = Info-Dialog**. Stubs klar markiert / nicht produktiv.

### PDF / Anhänge / Stempel
- Anhänge: Footer-Statuszählung „hinzugefügt X, umbenannt Y, übersprungen Z“; Text markierbar + Kopieren
- Quick-Stempel: Esc → „Platzieren abgebrochen“; Zoom/Opacity persistieren (wie Signatur) falls vorhanden

### OCR / Stubs
- Tabellen-CSV-Vorschau: Trennzeichen live nur Vorschau; Speichern persistiert; Abbruch/Esc setzt Vorschau zurück
- Settings-Tab „Stubs“: FEATURES.md fehlt → Statushinweis (kein Crash); Doppelklick Stub → Info-Dialog

### Packaging / Docs
- Version **1.9.4** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- Smoke: Anhänge Footer/kopierbar, Quick Esc·Zoom/Opacity, CSV Persistenz/Reset, Stubs Status·Doppelklick (CLI + Qt)

---

## 1.9.3 — Anhänge „Für alle“·Statuszählung, Quick-Stempel Rechtsklick·Esc, CSV-Zähler·Trennzeichen live, Stubs A–Z·Features-Link

Post-Release-Polish nach 1.9.2: **PDF-Anhänge** Duplikat-Dialog mit Checkbox **„Für alle anwenden“** und **Statuszählung** (hinzugefügt/umbenannt/übersprungen/abgebrochen); **Quick-Stempel** per **Rechtsklick Bibliothek** wählen, **Esc** bricht Platzieren ab; **Tabellen-CSV-Vorschau** mit **Zeilen/Spalten-Zähler** und **Trennzeichen live umschaltbar**; **Settings-Seite „Stubs“** sortiert **A–Z**, klar **„keine Aktion“**, Link zu **FEATURES.md**. Stubs klar markiert / nicht produktiv.

### PDF / Anhänge / Stempel
- Anhänge: Duplikat-Dialog Checkbox „Für alle anwenden“ (Umbenennen/Überspringen für Rest); Statuszählung am Ende
- Quick-Stempel: Rechtsklick → Bildbibliothek/Text-Presets; Esc → „Platzieren abgebrochen“

### OCR / Stubs
- Tabellen-CSV-Vorschau: Zeilen/Spalten-Zähler; Trennzeichen-Combo live (Rohvorschau + Speichern)
- Settings-Tab „Stubs“: A–Z, „keine Aktion“-Hinweis, Button FEATURES.md öffnen

### Packaging / Docs
- Version **1.9.3** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- Smoke: Anhänge Für-alle/Status, Quick-Stempel Rechtsklick/Esc, CSV-Zähler/Delim-live, Stubs A–Z/Features (CLI + Qt)

---

## 1.9.2 — Anhänge Mehrfach-DnD·Duplikat-Warnung, Quick-Stempel, CSV 5-Zeilen-Vorschau, Settings-Seite Stubs

Post-Release-Polish nach 1.9.1: **PDF-Anhänge** mit **Mehrfach-Drag&Drop**, **Duplikat-Namen Warnung + Umbenennen**; **Quick-Stempel** in der Toolbar (Standard ★ / zuletzt verwendet merken); **Tabellen-OCR→CSV** mit **Vorschau der ersten 5 Zeilen** vor Speichern und **Abbruch**; **Settings-Seite „Stubs“** listet KI/Cloud/Stylus/3D/Plugin-Hooks mit Status. Stubs klar markiert / nicht produktiv.

### PDF / Anhänge / Stempel
- Anhänge: Mehrfachdateien per DnD/Dialog; bei Namenskollision Warnung → Umbenennen / Überspringen / Abbrechen
- Quick-Stempel-Button in PDF-Toolbar; zuletzt verwendeter Stempel wird gemerkt (Fallback: Standard-Bild ★ / GENEHMIGT)

### OCR / Hooks
- Tabellen-CSV: Dialog-Vorschau erste 5 Zeilen; Speichern oder Abbrechen (kein Schreiben bei Abbruch)
- Settings-Tab „Stubs“: Status-Tabelle KI / Cloud / Stylus / 3D / Plugin-Hooks + Event-Liste

### Packaging / Docs
- Version **1.9.2** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- Smoke: Anhänge Duplikat-Warnung, Quick-Stempel, CSV-Vorschau, Settings-Stubs (CLI + Qt)

---

## 1.9.1 — Anhänge Größe/Typ·Doppelklick·DnD, Stempel Rename/Vorschau/Standard, CSV-Trennzeichen·BOM·Ordner, Hooks „nicht produktiv“

Post-Release-Polish nach 1.9.0: **PDF-Anhänge** mit klaren Spalten **Größe/Typ**, **Doppelklick extrahieren**, **Drag&Drop hinzufügen**; **Stempel-Bildbibliothek** mit **Umbenennen/Löschen**, **Vorschau**, **Standard-Stempel ★**; **Tabellen-OCR→CSV** mit **Trennzeichen** (`;`/`,`/Tab) in Settings/Dialog, **Zielordner merken**, **UTF-8-BOM Option**; **Plugin-Hooks Stub** About-Hinweis **„nicht produktiv“** + Event-Namen-Liste in Docs. Stubs KI/Cloud/Stylus/3D + Plugin-Hooks klar als Stub.

### PDF / Anhänge / Stempel
- Anhänge: Spalten Größe + Typ (MIME/Extension); Doppelklick → Extrahieren; Dateien per Drag&Drop hinzufügen
- Stempel-Bibliothek: Umbenennen, Löschen, Bildvorschau, Standard-Stempel markieren (★, Settings)

### OCR / Hooks
- Tabellen-CSV: Trennzeichen Settings/Dialog; letzter Zielordner; BOM an/aus (`format_rows_as_csv(utf8_bom=…)`)
- Plugin-Hooks Stub: About „nicht produktiv“; dokumentierte Events `app.started` / `document.opened` / `document.saved` / `annotation.changed` / `ocr.finished`

### Packaging / Docs
- Version **1.9.1** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- Smoke: Anhänge DnD/Doppelklick, Stempel Rename/Default/Vorschau, CSV-Delimiter·BOM·Dir, Hooks About (CLI + Qt)

---

## 1.9.0 — PDF-Anhänge hinzufügen, Stempel-Bildbibliothek, Tabellen-OCR→CSV, Plugin-Hooks Stub

Minor-Release mit neuen Kernfeatures (Basis **1.8.5**): **PDF-Anhänge** listen/extrahieren/**hinzufügen** (pikepdf Attachments, inkl. Entfernen); **Stempel-Bildbibliothek** unter `config/stamps/` mit Sidecar-Stempel (`img:…`); **Tabellen-OCR** mit grober Heuristik → **CSV** (UTF-8 BOM, `;`); **Plugin-Hooks Stub** mit internem Event-Bus und **no-op Loader** (kein echtes Plugin-System). Stubs KI/Cloud/Stylus/3D bleiben Stubs; Plugin-Hooks zusätzlich als Stub.

### PDF / Anhänge / Stempel
- Anhänge: `add_attachment` / `remove_attachment`; Dialog „Hinzufügen…“ / „Auswahl entfernen“; Menü öffnet auch leere Anhänge-Liste
- Stempel-Bildbibliothek: Ordner verwalten, Bilder hinzufügen/entfernen, als Sidecar-Stempel setzen (PDF-Menü + Stempel-Dialog)

### OCR / Hooks
- OCR-Ausgabe „Tabelle als CSV (heuristisch)“; `ocr_image_to_csv` / `format_rows_as_csv` / `OcrOutputMode.TABLE_CSV`
- Plugin-Hooks Stub: `instantlensdoc.core.plugin_hooks` — Event-Bus + `load_plugins()` no-op; Menü „Plugin-Hooks (Stub)“; `app.started` / `ocr.finished`

### Packaging / Docs
- Version **1.9.0** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- Smoke: Anhänge add/remove, Stempel-Bibliothek, Tabellen-CSV, Plugin-Hooks Stub (CLI + Qt)

---

## 1.8.5 — Batch Blink aus=Status einmalig, HF Fit-Zoom nur Vorschau, Layer A11y Alle ein/aus, Recovery Mehrfach-Verwerfen

Post-Release-Polish nach 1.8.4: **Batch Status-Blink „aus“** zeigt **einmaligen Status ohne Blink** (wie Pending-Status-Blink); **HF Fit-/Zoom-Persistenz** klar **nur Vorschau** — **irrelevant für Bake / „Auf alle“**; **Layer Alle ein/aus** mit **Accessibility-Announcement**; **Crash-Recovery** mit **Mehrfachauswahl Verwerfen** und **„Alle verwerfen“ inkl. Bestätigung**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Seiten
- Batch Status-Blink: Modus aus = einmaliger Status-Hinweis ohne Blink (Status-Text bleibt/wird erneut gezeigt)
- Kopf-/Fußzeile: Fit-Page/Zoom-Persistenz nur für Vorschau; Bake und „Auf alle Seiten anwenden“ unberührt

### Annotationen / Recovery
- Annotation-Typen „Alle ein/aus“: Accessibility-Announcement (Screenreader) bei Status
- Crash-Recovery: Orphan-Liste mit ExtendedSelection; Auswahl verwerfen; „Alle verwerfen“ mit Bestätigung

### Packaging / Docs
- Version **1.8.5** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- Smoke: Batch Blink-aus Status, HF Fit nur Vorschau, Layer A11y, Orphan Mehrfach-Verwerfen (CLI + Qt)

---

## 1.8.4 — Batch Status-Blink Settings, HF Esc-Fokus·Fit merken, Layer Redo·Status, Recovery Orphan-Liste älteste zuerst

Post-Release-Polish nach 1.8.3: **Batch Status-Blink** nutzt **Status-Blink Settings (kurz/aus)**; **Kopf-/Fußzeile-Vorschau** mit **Esc → Fokus zurück auf Dialog** und **Fit-Page speichert Zoom-Modus** für die nächste Vorschau; **Layer Alle ein/aus** mit **Redo (Ctrl+Y)** und Status **„Layer: alle ein/aus“**; **Crash-Recovery** listet **mehrere Orphans** (nummeriert), **älteste zuerst**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Seiten
- Batch Status-Blink: Modus/Dauer wie Einstellungen Status-Blink (kurz = Blink, aus = kein Blink)
- Kopf-/Fußzeile: Esc schließt große Vorschau und setzt Fokus zurück; Fit-Page-Modus bleibt für nächste Vorschau

### Annotationen / Recovery
- Annotation-Typen „Alle ein/aus“: Redo nach Undo; Status „Layer: alle ein“ / „Layer: alle aus“
- Crash-Recovery: mehrere Orphans als Liste (älteste zuerst), nummeriert bei >1

### Packaging / Docs
- Version **1.8.4** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- Smoke: Batch Blink-Settings, HF Esc-Fokus·Fit merken, Layer Redo·Status, Orphan-Liste älteste zuerst (CLI + Qt)

---

## 1.8.3 — Batch Undo DE-Verben·Status-Blink, HF Fit-Page·Mausrad·Esc, Layer Alle ein/aus Undo+Shortcuts, Recovery `_recovered`

Post-Release-Polish nach 1.8.2: **Batch Drehen/Spiegeln** mit **einheitlichen DE-Verben** („gedreht“ / „gespiegelt“) und **Statusleisten-Blink** bei Abschluss; **Kopf-/Fußzeile-Vorschau** mit **Fit-Page**, **Mausrad-Zoom**, **Esc schließt Vorschau-Fenster**; **Layer „Alle ein/aus“** als **ein Undo-Stack-Eintrag** inkl. Shortcuts **Ctrl+Alt+0** / **Ctrl+Alt+Shift+0**; **Crash-Recovery-Kopie** mit Suffix **`_recovered`**, Original-Orphan bleibt bis **Verwerfen**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Seiten
- Batch Undo-Text: „N Seiten gedreht“ / „N Seiten gespiegelt“ (Historie ebenfalls); Statusleiste blinkt kurz bei Batch-Abschluss
- Kopf-/Fußzeile: Fit-Page in Vorschau; Mausrad-Zoom; Vorschau-Fenster (Esc schließt)

### Annotationen / Recovery
- Annotation-Typen „Alle ein/aus“: vorherige Sichtbarkeit als ein Undo-Eintrag (Ctrl+Z); Shortcuts Ctrl+Alt+0 / Ctrl+Alt+Shift+0
- Crash-Recovery „Als Kopie“: Dateiname `*_recovered`; Orphan bleibt bis Verwerfen

### Packaging / Docs
- Version **1.8.3** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- Smoke: Batch DE-Verben·Blink, HF Fit-Page·Wheel·Esc, Layer Undo·Shortcuts, Recovery `_recovered`·Orphan bleibt (CLI + Qt)

---

## 1.8.2 — Batch Flip-Remap·Undo „gedreht/gespiegelt“, HF Zoom·Auf alle/Bereich, Layer Zähler-Filter·Alle ein/aus, Recovery Alter·Als Kopie

Post-Release-Polish nach 1.8.1: **Batch Spiegeln H/V** remappt **Ann.-Koordinaten** (+ Undo); Status/Historie **„N Seiten gedreht/gespiegelt“**; **Kopf-/Fußzeile** **Vorschau-Zoom**, **„Auf alle anwenden“** vs. **Seitenbereich** klar getrennt; **Layer-Zähler** per Klick **filtert Ann.-Liste**, Menü **„Alle ein“ / „Alle aus“**; **Crash-Recovery** zeigt **Snapshot-Alter**, Option **„Als Kopie öffnen“**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Seiten
- Batch Spiegel H/V: Ann.-BBox Remap (+ Undo); Status/Historie „1 Seite“ / „N Seiten gedreht/gespiegelt“
- Kopf-/Fußzeile: Vorschau-Zoom 50–250 %; Radio „Auf alle Seiten anwenden“ vs. Seitenbereich

### Annotationen / Recovery
- Annotation-Typen: Zähler je Typ im Menü; Klick filtert Sidebar-Liste; „Alle ein“ / „Alle aus“ / Listenfilter zurücksetzen
- Crash-Recovery: lesbares Alter (Min./Std./Tage); Button „Als Kopie öffnen“ (`*_recovery`)

### Packaging / Docs
- Version **1.8.2** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- Smoke: Flip-Remap·Undo-Text, HF Zoom·Scope, Layer Filter·Alle ein/aus, Recovery Age·Copy (CLI + Qt)

---

## 1.8.1 — Batch-Shortcuts·Ann-Remap, HF Schrift/Rand·Vorschau·Seitenbereich, Layer Session·Shortcuts·Zähler, Recovery Meta·Verwerfen sauber

Post-Release-Polish nach 1.8.0: **Batch Drehen/Spiegeln** mit **Shortcuts** (Ctrl+Alt+←/→/↑/H/Shift+V), Status **„N Seiten“**, **Ann.-Koordinaten Remap** bei 90°/180° (+ Undo); **Kopf-/Fußzeile** **Schriftgröße/Rand Settings**, **Vorschau erste Seite**, **Seitenbereich**; **Layer-Toggles** **Session-Persistenz**, **Shortcut-Menü** Ctrl+Alt+1…4, **Zähler sichtbarer Ann.**; **Crash-Recovery** **Snapshot-Metadaten-Vorschau**, **Verwerfen** löscht Orphan (Meta+Payload) sauber. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Seiten
- Thumbnails/Menü: Batch-Shortcuts; Status „1 Seite“ / „N Seiten“; Ann.-BBox Remap bei Drehung 90/180/−90
- Kopf-/Fußzeile: Schriftgröße/Rand Settings merken; Text+Thumbnail-Vorschau Seite 1; Seitenbereich (leer=alle)

### Annotationen / Recovery
- Annotation-Typen: Session-Persistenz; Shortcuts Ctrl+Alt+1…4; Menü-Titel mit Zähler sichtbar/gesamt
- Crash-Recovery: Dialog zeigt Meta (Art/Größe/Zeit/Pfad/Text-Snippet); Verwerfen löscht Meta+Payload orphan-sauber

### Packaging / Docs
- Version **1.8.1** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- Smoke: Batch-Shortcuts·Ann-Remap·Status N Seiten, HF Preview·Range, Layer Session·Count, Recovery Meta·Discard (CLI + Qt)

---

## 1.8.0 — Seiten drehen/spiegeln Batch+Undo, Kopf-/Fußzeile Bake, Ann.-Typ-Layer, Crash-Recovery

Minor-Release mit neuen Kernfeatures (Basis **1.7.5**): **PDF-Seiten Batch drehen/spiegeln** (Auswahl + 90°/180°/Spiegel H/V) mit **Undo**; **Kopf-/Fußzeile** inkl. Seitenzahl und benutzerdefiniertem Text als **pikepdf Content-Bake**; **Annotation-Layer Typ-Toggles** (Highlight/Note/Shape/Redaction) global; **Crash-Recovery** mit Autosave-Snapshot und Wiederherstellen-Dialog beim Start bei dirty Orphans. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Seiten
- Thumbnails: Mehrfachauswahl 90°/180° drehen · Spiegeln horizontal/vertikal; Undo Ctrl+Z (flip involutorisch)
- Kopf-/Fußzeile: Tab in Wasserzeichen-Dialog; Bake Text + Seitenzahl (`{n}`/`{total}`/`{page}`/`{stem}`/`{date}`)

### Annotationen / Recovery
- Annotation-Layer: globale Typ-Toggles Ansicht → Annotation-Typen (Highlight/Note/Shape/Redaction)
- Crash-Recovery: Autosave schreibt Snapshots unter `config/recovery/`; Start-Dialog Wiederherstellen/Verwerfen

### Packaging / Docs
- Version **1.8.0** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- Smoke: rotate/flip Batch+Undo, apply_header_footer, Ann-Typ-Layer, Crash-Recovery Orphans (CLI + Qt)

---

## 1.7.5 — Countdown Defaults Bestätigung·Live-Vorschau, Favoriten Enter leer→Dateiname, Text→PDF Ordner Neu anlegen, Update Status-Klick VERSION

Post-Release-Polish nach 1.7.4: **Countdown Defaults-Reset** mit **Bestätigung nur bei Abweichung** und **Live-Vorschau sofort**; **Favoriten Enter** bei **leerem Edit** setzt **Dateiname ohne extra Schritt**; **Text → PDF Ordner-Klick** bei fehlendem Ordner → **Dialog mit Neu anlegen**; **Update-Status-Klick** öffnet **VERSION.txt / docs/VERSION** im Editor falls lokal vorhanden. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Präsentation
- Präsentation: Countdown Defaults-Reset Bestätigung nur bei Abweichung; Live-Vorschau sofort
- Globale Favoriten: Enter bei leerem Edit setzt Dateiname ohne extra Schritt

### Editor / Export
- Text → PDF Status: fehlender Ordner → Dialog mit Option „Neu anlegen“

### Update / Packaging
- Update-Hinweis: Status-Klick öffnet lokale `VERSION.txt` / `docs/VERSION` im Editor
- Version **1.7.5** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- Smoke: Countdown Defaults-Confirm·Preview, Favoriten Enter-leer→Dateiname, text_pdf Ordner-mkdir, update Status-Klick VERSION (CLI + Qt)

---

## 1.7.4 — Countdown Live-Vorschau·Defaults, Favoriten Esc-Fokus·Enter, Text→PDF Status-Klick·A11y, Update Zeitstempel TT.MM.JJJJ HH:MM·Quellen-Tooltip

Post-Release-Polish nach 1.7.3: **Countdown-Settings** mit **Live-Vorschau Mini-Widget** und **Defaults-Reset**; **Favoriten-Label** Esc stellt **Fokus zurück auf Liste**, **Enter bestätigt Edit**; **Text → PDF Status** **Klick öffnet Ordner** inkl. **A11y-Announcement**; **Update-Zeitstempel** Format **TT.MM.JJJJ HH:MM** mit **Tooltip Quelle** (`docs/VERSION` / `VERSION.txt`). Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Präsentation
- Präsentation: Countdown Live-Vorschau Mini-Widget in Settings; Defaults-Reset (Position unten-rechts, Farbe dunkel)
- Globale Favoriten: Esc → Fokus zurück auf Liste; Enter bestätigt Label-Edit

### Editor / Export
- Text → PDF Status: Klick öffnet Zielordner; Accessible-Announcement

### Update / Packaging
- Update-Hinweis: Zeitstempel TT.MM.JJJJ HH:MM; Tooltip mit Quelle (VERSION.txt / docs/VERSION)
- Version **1.7.4** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- Smoke: Countdown Preview·Defaults, Favoriten Esc-Fokus/Enter, text_pdf Status-Klick·A11y, update timestamp·source-tooltip (CLI + Qt)

---

## 1.7.3 — Präsentation Countdown Position·Farbe, Favoriten Doppelklick·Esc·leer, Text→PDF öffnen ohne Sidecar·Status-Pfad, Update Offline·Zeitstempel

Post-Release-Polish nach 1.7.2: **Countdown-Overlay** mit Settings **Position** (unten-rechts/mitte) und **Farbe** (hell/dunkel); **Favoriten-Label** per **Doppelklick**, **Esc bricht ab**, **leerer Label → Dateiname**; **Text → PDF öffnen** legt **kein Sidecar** an und zeigt **Status mit Pfad**; **Update Offline** mit Status **„offline / nicht geprüft“** und **letztem Check-Zeitstempel**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Präsentation
- Präsentation: Countdown-Position unten-rechts|mitte; Countdown-Farbe hell|dunkel (Settings)
- Globale Favoriten: Doppelklick Label editieren; Esc bricht ab; leerer Label → Dateiname

### Editor / Export
- Text → PDF öffnen: kein leeres `.ildann.json`-Sidecar; Statusleiste mit vollem Pfad

### Update / Packaging
- Update-Hinweis: Status „offline / nicht geprüft“; letzter Check-Zeitstempel (persistiert)
- Version **1.7.3** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- Smoke: Countdown Pos·Farbe, Favoriten Doppelklick/Esc/leer, text_pdf open ohne Sidecar·Pfad, update offline·timestamp (CLI + Qt)

---

## 1.7.2 — Präsentation Pause·Countdown·Intervalle, Favoriten Label·Tab·Duplikat-Pfade, Text→PDF Ordner·öffnen, Update Status·Offline

Post-Release-Polish nach 1.7.1: **Präsentation-Timer** mit **Space = Pause**, **Countdown-Overlay** und festen Intervallen **3/5/10/30 s**; **Lesezeichen-Leiste** mit **Label bearbeiten**, **„In neuem Tab öffnen“** und **Duplikat-Pfad-Schutz**; **Text → PDF** merkt **Zielordner** und öffnet optional nach Export; **Update-Prüfung** mit Status **aktuell / neuer Build Hinweis** und **Offline-Fallback ohne Fehlerdialog**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Präsentation
- Präsentation: Space pausiert/fortsetzt Auto-Advance; Countdown-Overlay; Intervalle aus|3|5|10|30 s
- Globale Favoriten: Label editieren; In neuem Tab öffnen; ein Eintrag pro Pfad (Duplikate verhindert)

### Editor / Export
- Text → PDF: Zielordner merken (`last_text_pdf_dir`); optional nach Export öffnen (Settings)

### Update / Packaging
- Update-Hinweis: Status „aktuell“ / „neuer Build Hinweis“; Offline-Fallback ohne Fehlerdialog
- Version **1.7.2** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- Smoke: Präsentation Pause·Countdown·Intervalle, Favoriten Label/Tab/Dup-Pfad, text_pdf Ordner·öffnen, update status·offline (CLI + Qt)

---

## 1.7.1 — Präsentation Timer·schwarz·Seitennummer, Favoriten Drag·fehlend·Export/Import, Text→PDF Schrift/Rand·Vorschau, Update Dismiss·Jetzt prüfen

Post-Release-Polish nach 1.7.0: **Präsentation** mit optionalem **Timer-Autoadvance**, **schwarzem Hintergrund** und **Seitennummer-Overlay-Toggle** (Taste N); **Lesezeichen-Leiste** mit **Drag-Reorder**, **fehlende Dateien grau + Entfernen**, **Export/Import ildfav-v1**; **Text → PDF** mit **Schriftgröße/Ränder** in Settings und **Seitenvorschau**; **Update-Hinweis** **Dismiss bis nächste Version** und Menüpunkt **„Jetzt prüfen…“**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Präsentation
- Präsentation: Auto-Advance (0=aus); schwarzer Hintergrund; Seitennummer-Overlay Toggle (Settings + Taste N)
- Globale Favoriten: Drag-Umsortieren; fehlende Pfade grau + Entfernen; Export/Import `ildfav-v1`

### Editor / Export
- Text → PDF: Schriftgröße/Rand in Einstellungen; Seitenvorschau (Anzahl) vor Speichern

### Update / Packaging
- Update-Hinweis: Dismiss bis nächste Referenzversion; Hilfe → „Jetzt prüfen…“
- Version **1.7.1** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- Smoke: Präsentation Timer·schwarz·Nr., Favoriten reorder/missing/export, text_pdf font/margin·preview, update dismiss (CLI + Qt)

---

## 1.7.0 — Präsentationsmodus Ann.-Overlay, Lesezeichen-Leiste ildfav-v1, Text→PDF, Update-Hinweis lokal

Minor-Release mit neuen Kernfeatures (Basis **1.6.5**): **Präsentationsmodus** Vollbild-PDF mit Pfeiltasten/Esc und optional **Annotation-Overlay aus**; **Lesezeichen-Leiste** für globale Favoriten (Schema **`ildfav-v1`**, Schnelljump über Docs); **Text → PDF** exportiert den aktuellen Text-Tab als einfaches Mehrseiten-PDF (`ild_pdf.text_to_pdf`, pikepdf Seiten); **Update-Hinweis** vergleicht lokal gegen **`docs/VERSION`** oder eingebettete **`VERSION.txt`** (nur Hinweis, kein Auto-Download). Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Präsentation
- Präsentationsmodus (F5): Vollbild; ←/→/Leertaste; Esc beendet; Setting „Ann.-Overlay ausblenden“ (Default an)
- Globale Favoriten-Leiste: aktuelle Seite hinzufügen (Ctrl+Shift+B); Jump öffnet Doc+Seite; Persistenz `global_favorites.ildfav.json`

### Editor / Export
- Text → PDF… (Ctrl+Shift+P): aktueller Text-Tab → einfaches PDF via pikepdf `add_blank_page`

### Update / Packaging
- Update-Hinweis: lokaler Versionsvergleich `docs/VERSION` / `VERSION.txt`; optional Online; kein Auto-Download
- Version **1.7.0** (App / `ild_pdf` / ISS / Smoke / Docs); `docs/VERSION` + `VERSION.txt`
- Smoke: Präsentation Ann-hide, globale Favoriten-Leiste, text_to_pdf, lokaler Update-Check (CLI + Qt)

---

## 1.6.5 — WM Reset-Template·Fokus/Selektion, Crypto Prefill Toast, Stats Quick-Insert·ungültige rot, Layouts Import-Log kopieren/TXT·Zusammenfassung

Post-Release-Polish nach 1.6.4: **Wasserzeichen-Template** mit **Reset-Template**-Button und **Fokus/Selektion** wie Ann.-Template; **Crypto „jetzt ausschalten“** speichert sofort und zeigt **Toast-Bestätigung**; **Dokument-Statistik** Template **Quick-Insert `{stem}`/`{date}`** und **ungültige Platzhalter rot**; **Layouts Import-Log** mit **Zusammenfassung** (importiert/übersprungen/umbenannt) sowie **kopieren** / **als TXT**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Wasserzeichen: Template Reset-Template + Fokus/Selektion (wie Ann.-Template); Quick-Insert `{stem}`/`{date}` bleibt
- Verschlüsseln/Entschlüsseln: Prefill „jetzt ausschalten“ → sofort speichern + Toast-Bestätigung
- Dokument-Statistik: JSON-Dateiname Quick-Insert `{stem}`/`{date}`; ungültige Platzhalter rot

### UI / Workspace
- Workspace-Layouts: Import-Log Zusammenfassung importiert/übersprungen/umbenannt; Log kopieren / als TXT

### Packaging / Docs
- Version **1.6.5** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: WM Reset-Template·Fokus, Crypto disable-toast, Stats Quick-Insert·invalid-red, Layouts Import-Log copy/TXT·summary (CLI + Qt)

---

## 1.6.4 — WM Template Quick-Insert·ungültige rot, Crypto Prefill „jetzt ausschalten“, Stats Dateiname-Template Live-Vorschau, Layouts Merge Kollision skip/rename·Import-Log

Post-Release-Polish nach 1.6.3: **Wasserzeichen-Template** mit **Quick-Insert `{stem}`/`{date}`** und **ungültigen Platzhaltern rot**; **Crypto-Prefill-Warnung** mit Link/Button **„jetzt ausschalten“**; **Dokument-Statistik JSON** **Dateiname-Template** `{stem}_stats.json` **Live-Vorschau**; **Layouts-Merge** **Kollisionsstrategie** pro Name (**überspringen** / **umbenennen `_2`**) inkl. **Import-Log**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Wasserzeichen: Template Quick-Insert `{stem}`/`{date}`; ungültige Platzhalter rot; `{date}` im Ausgabe-Pfad
- Verschlüsseln/Entschlüsseln: Prefill-Warnung mit Button „jetzt ausschalten“ (sofort speichern)
- Dokument-Statistik: JSON-Dateiname-Template `{stem}_stats.json` Live-Vorschau (+ `{date}`)

### UI / Workspace
- Workspace-Layouts: Merge-Kollision überspringen oder umbenennen (`_2`); Import-Log im Ergebnisdialog

### Packaging / Docs
- Version **1.6.4** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: WM Quick-Insert·invalid-red, Crypto disable-now, Stats filename-preview, Layouts skip/rename·import-log (CLI + Qt)

---

## 1.6.3 — WM Bake Teilergebnis·Template-Live-Vorschau, Crypto Prefill-Warnung·keine PW-Logs, Stats Zielordner·UTF-8, Layouts Merge/Ersetzen·Schema DE

Post-Release-Polish nach 1.6.2: **Wasserzeichen-Bake Abbruch** mit **Teilergebnis-Hinweis** (X/Y Seiten gespeichert) und **Template Live-Vorschau Dateiname**; **Crypto-Prefill** **Warnhinweis in Settings** wenn an, **Passwort nie in Logs**; **Dokument-Statistik JSON** **Zielordner merken**, Encoding **UTF-8 ohne BOM**; **Layouts-Import** Dialog **Merge vs. Ersetzen**, **ungültiges Schema klar DE**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Wasserzeichen: Bake-Abbruch → Teilergebnis-Hinweis; Template Live-Vorschau Dateiname
- Verschlüsseln/Entschlüsseln: Prefill-Warnhinweis in Settings wenn an; Passwort nie in Logs
- Dokument-Statistik: JSON-Export Zielordner merken; UTF-8 ohne BOM (`ildstats-v1`)

### UI / Workspace
- Workspace-Layouts: Import-Dialog Merge vs. Ersetzen; ungültiges Schema klar DE (`ildlayouts-v1`)

### Packaging / Docs
- Version **1.6.3** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: WM Teilergebnis·Live-Vorschau, Crypto Settings-Warn·Redact, Stats Zielordner·no-BOM, Layouts Merge/Replace·Schema-DE (CLI + Qt)

---

## 1.6.2 — Wasserzeichen Bake Fortschritt·Abbruch·Template, Crypto Prefill·PW-Fehler, Stats Copy·ildstats-v1, Layouts Export/Import·Duplikate

Post-Release-Polish nach 1.6.1: **Wasserzeichen-Bake** mit **Fortschritt + Abbruch** und **Ausgabe-Pfad-Template** in Settings (`{stem}_wm`); **Crypto-Reload** optional **Passwort vorausfüllen** (unsicher, default aus) und klarer **DE-Fehler bei falschem Passwort**; **Dokument-Statistik** **Copy-as-Text** + Export JSON **`ildstats-v1`**; **Workspace-Layouts** Export/Import JSON **`ildlayouts-v1`**, **Duplikat-Namen ablehnen**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Wasserzeichen: Bake-Fortschritt + Abbruch; Ausgabe-Template Settings (`{stem}_wm`)
- Verschlüsseln/Entschlüsseln: Prefill-Toggle für Reload (unsicher, default aus); falsches PW klar DE
- Dokument-Statistik: Als Text kopieren; JSON-Export `ildstats-v1`

### UI / Workspace
- Workspace-Layouts: Export/Import JSON `ildlayouts-v1`; Duplikat-Namen abgelehnt

### Packaging / Docs
- Version **1.6.2** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: WM Bake progress·cancel·template, Crypto prefill·wrong-PW, Stats copy·ildstats-v1, Layouts export/import·dup-reject (CLI + Qt)

---

## 1.6.1 — Wasserzeichen Settings·Seitenbereich·Merken, Crypto Stärke·Reload, Stats Refresh·Auto, Layouts Rename·Default·max20

Post-Release-Polish nach 1.6.0: **Wasserzeichen** persistiert Opacity/Größe/Winkel in Settings, **Seitenbereich** (alle/aktuell/1-3,5) und merkt zuletzt Text/Bild; **Verschlüsselung** mit **Stärke-Hinweis**, leeres Passwort ablehnen, nach Erfolg Option **Datei neu laden**; **Dokument-Statistik** mit Refresh-Button, **Auto-Update bei Doc-Wechsel**, Wörter nur bei Textschicht sonst „—“; **Workspace-Layouts** Umbenennen/Löschen, **Default markieren (★)**, max. **20**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Wasserzeichen: Opacity/Größe/Winkel Settings; Seitenbereich; zuletzt Text/Bild merken
- Verschlüsseln: Stärke-Hinweis live; leeres User-Passwort abgelehnt; nach Erfolg neu laden
- Entschlüsseln: leeres Passwort abgelehnt; nach Erfolg neu laden
- Dokument-Statistik: Refresh; Auto-Update bei Doc-Wechsel; Wörter „—“ ohne Textschicht

### UI / Workspace
- Workspace-Layouts: Umbenennen; Als Standard markieren (★); max. 20 Layouts

### Packaging / Docs
- Version **1.6.1** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: WM Settings·Range·Merken, Crypto Stärke·leer·Reload, Stats Refresh·Auto·Wörter—, Layouts Rename·Default·max20 (CLI + Qt)

---

## 1.6.0 — Wasserzeichen Text/Bild·Vorschau·Bake, PDF verschlüsseln/entschlüsseln, Dokument-Statistik, Workspace-Layouts

Minor-Release mit neuen Kernfeatures: **Wasserzeichen** als Text oder Bild, Position **diagonal** oder **zentriert**, Live-**Vorschau** und **Bake** in ein neues PDF; **PDF verschlüsseln/entschlüsseln** (User-Passwort setzen/entfernen via pikepdf, Owner optional); **Dokument-Statistik**-Panel (Seiten, Wörter aus Text-PDF, Annotationen, Dateigröße); **Workspace-Layouts** speichern/laden (Name + Panel-Sichtbarkeit Thumb/Ann/Bookmark + Splitter). Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Wasserzeichen: Text oder Bild; diagonal/zentriert; Vorschau; Bake → neues PDF (`*_wm.pdf`)
- Verschlüsseln: User-Passwort setzen, Owner optional (pikepdf AES)
- Entschlüsseln: Passwortschutz entfernen → `*_unlocked.pdf` (oder Original)
- Dokument-Statistik: Seiten, Wörter (Text-PDF), Ann.-Anzahl, Dateigröße (nicht-modales Panel)

### UI / Workspace
- Workspace-Layouts: Ansicht → Layout speichern/laden/löschen (Panels + Splitter)

### Packaging / Docs
- Version **1.6.0** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Wasserzeichen Bild·Placement·Preview·Bake, Encrypt/Decrypt, Doc-Stats, Workspace-Layouts (CLI + Qt)

---

## 1.5.5 — Metadaten Toast Fokus, Seiten→Bilder Filter-Badge, Signatur Zoom Settings·Reset, CLI list-pages --json

Post-Release-Polish nach 1.5.4: **Metadaten-Toast-Klick** öffnet den Dialog **nur wenn nicht schon offen** (sonst **Fokus/raise**); **Seiten→Bilder**-Footer zeigt Badge **„Filter: übersprungen“** wenn der Filter aktiv ist; **Signatur-Vorschau-Zoom** wird in **Settings persistiert** inkl. **Reset-Zoom**-Button; **CLI** `--list-pages FILE --json` liefert `{pages,path}`, Exit **2** bei fehlender Datei. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Metadaten: Toast-Klick nur wenn Dialog zu; sonst Fokus/raise
- Seiten → Bilder: Badge „Filter: übersprungen“ am Footer wenn Filter aktiv
- Signatur (Bild): Zoom in Settings persistieren; Reset-Zoom in Vorschau

### CLI / Start
- `python -m instantlensdoc --list-pages FILE [--json]` → Zahl bzw. `{pages,path}`; Exit **2** bei fehlender Datei
- `--json` in `--help`

### Packaging / Docs
- Version **1.5.5** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Metadaten Toast Fokus/raise, Seiten→Bilder Filter-Badge, Signatur Zoom Settings·Reset, CLI list-pages --json (CLI + Qt)

---

## 1.5.4 — Metadaten Toast Klick·A11y, Seiten→Bilder Footer-Filter, Signatur Esc-Status·Zoom, CLI --list-pages

Post-Release-Polish nach 1.5.3: **Metadaten-Toast** per **Klick** öffnet den Dialog erneut inkl. **Accessibility-Announcement**; **Seiten→Bilder**-Footer filtert Log auf **übersprungene** (Toggle, analog Split-Log); **Signatur Esc** setzt Status **„Platzieren abgebrochen“** und merkt den **letzten Vorschau-Zoom**; **CLI** `--list-pages FILE` gibt die **Seitenzahl** headless aus (in `--help`). Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Metadaten: Toast-Klick öffnet Dialog erneut; Accessibility-Announcement (wie OCR-Toast)
- Seiten → Bilder: Footer klickbar → Log-Filter übersprungene (Toggle, analog Split-Log)
- Signatur (Bild): Esc → Status „Platzieren abgebrochen“; letzter Vorschau-Zoom merken

### CLI / Start
- `python -m instantlensdoc --list-pages FILE` (Seitenzahl, headless); in `--help`
- Exitcodes: **0** OK · **1** Fehler · **2** Datei fehlt

### Packaging / Docs
- Version **1.5.4** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Metadaten Toast-Klick·A11y, Seiten→Bilder Footer-Filter, Signatur Esc-Status·Zoom, CLI --list-pages (CLI + Qt)

---

## 1.5.3 — Metadaten Toast Dauer·max3, Seiten→Bilder Footer·Ordner, Signatur Zoom·Esc, CLI --dpi/--format

Post-Release-Polish nach 1.5.2: **Metadaten-Toast** nutzt **OCR-Toast-Dauer** aus Settings und zeigt **max. 3 Felder** + „…“; **Seiten→Bilder** zeigt Footer **„geschrieben X, übersprungen Y“** und Button **Ordner öffnen**; **Signatur-Vorschau** mit **Mausrad-Zoom** und **Esc bricht Platzieren ab**; **CLI** `--export-page` mit **`--dpi`** und **`--format png|jpeg`**, Exitcodes dokumentiert. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Metadaten: Erfolgs-Toast-Dauer wie OCR-Defaults-Toast (1/2/3 s); Felder-Kurzinfo max. 3 + „…“
- Seiten → Bilder: Footer „geschrieben X, übersprungen Y“; Button Ordner öffnen
- Signatur (Bild): Vorschau Mausrad-Zoom; Esc bricht Platzieren ab

### CLI / Start
- `python -m instantlensdoc … --export-page N --out PATH [--dpi 72|150|300] [--format png|jpeg]`
- Exitcodes dokumentiert: **0** OK · **1** Fehler · **2** Datei fehlt

### Packaging / Docs
- Version **1.5.3** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Metadaten Toast-Dauer·max3, Seiten→Bilder Footer·Ordner, Signatur Zoom·Esc, CLI dpi/format (CLI + Qt)

---

## 1.5.2 — Metadaten Backup·Toast, Seiten→Bilder Abbruch·JPEG-Q, Signatur Aspect-Lock·Vorschau, CLI --export-page

Post-Release-Polish nach 1.5.1: **Metadaten-Speichern** erzeugt optional **Backup `.ildbak`** (Toggle) und zeigt **Erfolgs-Toast** mit Felder-Kurzinfo; **Seiten→Bilder** behält bei **Abbruch** bereits geschriebene Dateien inkl. **Statuszählung**, **JPEG-Qualität** aus Settings wählbar; **Signatur** mit **Aspect-Ratio Lock** und **Vorschau vor Platzieren**; **CLI** `--export-page N --out PATH` als **One-Shot ohne GUI** (headless ok). Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Metadaten: Toggle Backup `.ildbak` vor Speichern; Erfolgs-Toast mit Felder-Kurzinfo (Titel/Autor/…)
- Seiten → Bilder: Abbruch behält geschriebene Dateien + Zählung `n/total`; JPEG-Qualität Settings
- Signatur (Bild): Aspect-Ratio Lock Toggle; Live-Vorschau vor Platzieren

### CLI / Start
- `python -m instantlensdoc DATEI --export-page N --out PATH` (One-Shot, kein Qt); Exit 0/1/2

### Packaging / Docs
- Version **1.5.2** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Metadaten Backup·Toast, Seiten→Bilder Cancel-Keep·JPEG-Q, Signatur Aspect-Lock·Preview, CLI export-page (CLI + Qt)

---

## 1.5.1 — Metadaten Dirty·Reset·UTF-8·leere Felder, Seiten→Bilder Ordner·Template·Fortschritt, Signatur Größe·Opacity, CLI Help DE·multi-open·Exitcodes

Post-Release-Polish nach 1.5.0: **Metadaten-Dialog** mit **Dirty-Markierung** (*), **Zurücksetzen**, **UTF-8-sicheren** Werten (NFC) und Toggle **„Leere Felder beim Speichern löschen“**; **Seiten→Bilder** merkt **Zielordner**, Dateiname-Template **`{stem}_p{page}`**, **Fortschrittsdialog** bei Bereich/Mehrseiten (Abbrechen); **Signatur** mit **Größe-/Deckkraft-Slider** und **zuletzt verwendetes Bild** merken; **CLI** `--help` auf Deutsch, **mehrere `--open`**, **Exitcode 2** bei fehlender Datei. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Metadaten: Dirty-Markierung + Reset; UTF-8 (NFC/Surrogate-safe); Toggle leere Felder löschen (DocInfo+XMP)
- Seiten → Bilder: Zielordner merken; Template `{stem}_p{page}`; Fortschritt + Abbruch bei Bereich
- Signatur (Bild): Größen- und Opacity-Slider; letztes Signatur-Bild merken

### CLI / Start
- `python -m instantlensdoc --help` (DE); mehrfach `--open DATEI`; Exit **2** wenn Datei fehlt (stderr)

### Packaging / Docs
- Version **1.5.1** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Metadaten Dirty·Reset·UTF-8·delete-empty, Seiten→Bilder Template·Progress, Signatur Size·Opacity·Remember, CLI help-DE·multi-open·exit2 (CLI + Qt)

---

## 1.5.0 — PDF-Metadaten-Editor, Seiten→Bilder Bereich·DPI, Signatur-Bildstempel·Flatten, CLI --open/--version

Minor-Release mit neuen Kernfeatures: **PDF-Metadaten-Editor** (Titel/Autor/Betreff/Keywords lesen+schreiben via pikepdf, Dialog + Speichern); **Seiten als Bild exportieren** (aktuelle Seite / Seitenbereich `1-3,5` / alle → PNG/JPEG, DPI 72/150/300); **Signatur-Platzhalter** als Bildstempel aus Datei (Sidecar + optional Flatten-PDF); **Kommandozeile** `python -m instantlensdoc --open FILE` und `--version`. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Metadaten-Dialog: Titel/Autor/Betreff/Keywords (+ Ersteller/Produzent) DocInfo+XMP; Speichern schreibt in die PDF
- Seiten → Bilder: Scope aktuell / Seitenbereich / alle; Format PNG/JPEG; DPI-Settings
- Signatur (Bild): Sidecar-Platzhalter; optional Flatten der Seite in neues PDF

### CLI / Start
- `python -m instantlensdoc --version` (−V); `--open FILE`; positional Datei bleibt kompatibel

### Packaging / Docs
- Version **1.5.0** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Metadaten Editor, Seiten→Bilder Bereich·DPI, Signatur Flatten, CLI --open/--version (CLI + Qt)

---

## 1.4.5 — Diff-PNG Reset Confirm·Fokus, Rename-Undo Skip-Detail, Ann.-CSV Rescan-Progress, Theme-Toast

Post-Release-Polish nach 1.4.4: **Diff-PNG Reset** bestätigt **nur bei Abweichung** und setzt **Fokus+Selektion** wie Ann.-Template; **Batch-Undo** meldet detailliert **„rückgängig X, übersprungen Y“** mit **kopierbarem Text**; **Annotation-Suche CSV Neu-Scan** zeigt bei vielen Docs einen **Fortschrittsdialog** mit **Abbruch**; **Theme-Zyklus** zeigt kurzen Status-Toast **„Theme: …“** und Shortcut in **Hilfe/About**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Vergleich Diff-PNG: Reset-Bestätigung nur bei Abweichung; Fokus + Selektion wie Ann.-Template

### Dateien / Tabs
- Batch-Umbenennen Undo: Meldung „rückgängig X, übersprungen Y“; Text kopierbar (Selektion + Kopieren)

### Annotationen
- Suche-Treffer-CSV Neu-Scan: Fortschrittsdialog bei vielen Docs; Abbrechen möglich

### UI / Theme
- Theme-Zyklus Ctrl+Shift+T: kurzer Status-Toast „Theme: …“; Shortcut in Hilfe/About

### Packaging / Docs
- Version **1.4.5** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Diff-PNG Reset Confirm·Fokus, Rename-Undo Skip-Detail, Ann.-CSV Rescan-Progress, Theme-Toast (CLI + Qt)

---

## 1.4.4 — Diff-PNG Quick-Insert·Reset, Rename-Undo Skip·Invalidate, Ann.-CSV Scope, Theme-Zyklus

Post-Release-Polish nach 1.4.3: **Diff-PNG-Template** mit **Quick-Insert** `{stemA}`/`{stemB}`/`{page}`/`{date}` und **Reset-Template** auf Default; **Batch-Undo** zählt **übersprungene Dateien** und **invalidiert** das Undo-Log danach; **Annotation-Suche CSV** wählbar **„nur aktuelle Trefferliste“** vs. **„alle Docs neu scannen“**; **Theme-Schnellmenü** zusätzlich per **Ctrl+Shift+T** zyklisch System→Hell→Dunkel→System. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Vergleich Diff-PNG: Quick-Insert-Buttons `{stemA}` `{stemB}` `{page}` `{date}`; Reset-Template auf Default

### Dateien / Tabs
- Batch-Umbenennen Undo: übersprungene Dateien zählen und melden; Log-Eintrag danach invalidieren

### Annotationen
- Suche-Treffer-CSV: Option „nur aktuelle Trefferliste“ vs. „alle Docs neu scannen“

### UI / Theme
- Theme-Schnellmenü: Shortcut Ctrl+Shift+T zyklisch System→Hell→Dunkel→System (Tab duplizieren → Ctrl+Alt+Shift+T)

### Packaging / Docs
- Version **1.4.4** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Diff-PNG Quick-Insert·Reset, Rename-Undo Skip·Invalidate, Ann.-CSV Scope, Theme-Zyklus (CLI + Qt)

---

## 1.4.3 — Diff-PNG Live-Vorschau, Rename-Undo Bestätigung·Filter, Ann.-CSV Spalten+BOM, Theme-Schnellmenü

Post-Release-Polish nach 1.4.2: **Diff-PNG-Template** mit **Live-Vorschau** des Dateinamens und **ungültigen Platzhaltern in Rot**; **Batch-Undo** mit **Bestätigung inkl. Anzahl** und greift **nur Dateien, die noch dem neuen Namen entsprechen**; **Annotation-Suche CSV** mit Spalten **Doc,Seite,Typ,Text,Snippet** und **UTF-8 BOM**; **Theme-Indicator** öffnet per Klick ein **Schnellmenü** (System / Hell / Dunkel). Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Vergleich Diff-PNG: editierbares Template; Live-Vorschau Dateiname; ungültige Platzhalter rot

### Dateien / Tabs
- Batch-Umbenennen: Undo-Bestätigung mit Anzahl; nur Dateien unter dem neuen Namen

### Annotationen
- Suche-Treffer-CSV: Spalten Doc,Seite,Typ,Text,Snippet; UTF-8 BOM

### UI / Theme
- Statusleisten-Indicator: Klick → Theme-Schnellmenü System / Hell / Dunkel

### Packaging / Docs
- Version **1.4.3** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Diff-PNG Live-Vorschau·Platzhalter, Rename-Undo Anzahl·Filter, Ann.-CSV Spalten+BOM, Theme-Schnellmenü (CLI + Qt)

---

## 1.4.2 — PDF-Diff PNG Zielordner·Template, Rename Undo-TXT·Rückgängig, Ann. Regex-Fehler·CSV, Theme-Status

Post-Release-Polish nach 1.4.1: **Diff-PNG** merkt **Zielordner** und nutzt Dateiname-Template **`{stemA}_vs_{stemB}_p{page}.png`**; **Batch-Umbenennen** speichert Undo-Log als **TXT** und bietet **„Rückgängig letzte Batch“**; **Annotation-Suche** zeigt bei ungültigem Regex denselben **Fehlerstatus wie PDF-Suche** (`Regex-Fehler: …`) und exportiert Treffer als **CSV**; **Theme folgen** mit Indicator in der **Statusleiste** (System / Manuell dunkel / Manuell hell). Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Vergleich Diff-PNG: Zielordner merken; Template `{stemA}_vs_{stemB}_p{page}.png`

### Dateien / Tabs
- Batch-Umbenennen: Undo-Log als TXT; Button „Rückgängig letzte Batch“

### Annotationen
- Suche offene Docs: Regex-Fehlerstatus wie PDF-Suche; Treffer-Export CSV

### UI / Theme
- Statusleiste: Theme-Indicator System / Manuell dunkel / Manuell hell

### Packaging / Docs
- Version **1.4.2** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Diff-PNG Ordner·Template, Rename Undo-TXT·Rückgängig, Ann. Regex-Fehler·CSV, Theme-Status (CLI + Qt)

---

## 1.4.1 — PDF-Diff Sync/Schwelle/PNG, Rename Dry-Run·Kollision·Undo, Ann.-Suche Klick·Case/Regex, Theme live

Post-Release-Polish nach 1.4.0: **PDF-Vergleich** Seitenwahl **Sync/Entkoppelt** (Settings), **Diff-Schwelle** in Settings/Dialog, **Diff-Overlay als PNG** exportieren; **Batch-Umbenennen** mit **Dry-Run-Liste**, **Kollisionswarnung** und **Undo-Log** der alten Namen; **Annotation-Suche** Treffer **klickbar** (Doc+Seite), Toggles **Case** und **Regex**; **System-Theme** bei OS-Wechsel **live nachziehen** wenn „folgen“ aktiv. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Vergleich: Seiten Sync/Entkoppelt; Diff-Schwelle Settings; Diff-PNG-Export

### Dateien / Tabs
- Batch-Umbenennen: Dry-Run-Liste speichern; Kollisionswarnung; Undo-Log (`ildrename-undo-v1`)

### Annotationen
- Suche offene Docs: Treffer klickbar (Doc+Seite); Case- und Regex-Toggles

### UI / Theme
- System folgen: live bei OS-`colorSchemeChanged`

### Packaging / Docs
- Version **1.4.1** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: PDF-Diff Sync/Schwelle/PNG, Rename Dry-Run·Kollision·Undo, Ann. Klick·Case/Regex, Theme live (CLI + Qt)

---

## 1.4.0 — PDF-Vergleich Raster-Diff, Batch-Umbenennen, Annotation-Suche offen, Theme System+Override

Minor-Release nach 1.3.6: **PDF-Vergleich** Seite-für-Seite mit **Raster-Diff Overlay** (Magenta) und grober **Ähnlichkeit in Prozent**; **Batch-Umbenennen** offener Tabs/Dateiliste mit Template **`{stem}_{n}`** und Live-Vorschau (Sidecars mitumbenennen); **Annotation-Suche** Volltext über Sidecar-Notizen/Highlights quer durch geöffnete Docs; **Dark/Light** mit **System-Theme folgen** und manuellem Override. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Vergleich: Raster-Diff Overlay + Ähnlichkeit % (Seite neben Seite)

### Dateien / Tabs
- Batch-Umbenennen: Template `{stem}_{n}` / `{ext}` / `{name}`; Vorschau; Sidecars `.ildann.json` u. a.

### Annotationen
- Suche über offene Docs: Notizen, Highlights, Tags (Sidecar `*.ildann.json`); Sprung zu Seite

### UI / Theme
- Design: **System folgen** (Toggle) + manuell Hell/Dunkel Override; Settings + Session

### Packaging / Docs
- Version **1.4.0** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: PDF-Diff, Batch-Rename, Ann.-Suche, Theme System (CLI + Qt)

---

## 1.3.6 — Forms CSV Esc/Enter, Redaction Sidecar übersprungen+Settings, Outlines Versuch k/3, Prefetch Lazy-Farbe

Post-Release-Polish nach 1.3.5: **Forms-CSV** Dialog **Esc** schließt ohne Export, **Enter** startet Export wenn Fokus auf **OK**; **Redactions** bei fortgesetztem Bake Status **„Sidecar übersprungen“**, Fortsetzen-Option in **Settings** merken; **Outlines-Export** Fehlerdialog mit Retry-Zähler **„Versuch k/3“**; Prefetch Live-Label **grau** wenn Lazy aus (Dokument unter Schwellwert), sonst **aktiv**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### Formulare
- Feldliste CSV: **Esc** schließt ohne Export; **Enter** auf OK startet Export

### PDF / Redaction
- Bake-Fortsetzung: Status **„Sidecar übersprungen“**; Option in **Settings** merken

### Bookmarks / Outlines
- Fehlerdialog Retry-Zähler **„Versuch k/3“**

### Performance
- Prefetch Live-Label: **grau** wenn Lazy aus (unter Schwellwert), sonst aktiv

### Packaging / Docs
- Version **1.3.6** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Forms CSV Esc/Enter, Redaction Sidecar übersprungen+Settings, Outlines Versuch k/3, Prefetch Lazy-Farbe (CLI + Qt)

---

## 1.3.5 — Forms CSV Zähler+Default, Redaction Sidecar-Warnung, Outlines Retry max-3, Prefetch Live ohne Apply

Post-Release-Polish nach 1.3.4: **Forms-CSV** Dialog mit Zähler **„N von M Zeilen“** und **persistiertem Default** „nur sichtbar“; **Redactions** bei Sidecar-Schreibfehler **Warnung** mit Option **PDF-Bake fortsetzen**; **Outlines-Export** Retry **max. 3 wie Backup**, danach **Abbruch-Hinweis**; Prefetch Live-Label aktualisiert **sofort bei Slider/Combo ohne Apply**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### Formulare
- Feldliste CSV: Zähler **N von M Zeilen** im Dialog; Default „nur sichtbare“ **persistiert**

### PDF / Redaction
- Sidecar-Write fehlschlägt → **Warnung** + Option **PDF-Bake fortsetzen**

### Bookmarks / Outlines
- Schreibfehler-Retry: **max. 3** wie Backup; danach **Abbruch-Hinweis**

### Performance
- Prefetch Live-Label: **sofort** bei Änderung, **ohne Übernehmen/Apply**

### Packaging / Docs
- Version **1.3.5** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Forms CSV Zähler+Default, Redaction Sidecar-Warnung, Outlines Retry max-3, Prefetch Live ohne Apply (CLI + Qt)

---

## 1.3.4 — Forms CSV BOM+Filter, Redaction Sidecar-Checkbox, Outlines Ordner-Klick+Retry, Prefetch Live-Label

Post-Release-Polish nach 1.3.3: **Forms-CSV** mit **UTF-8 BOM** und Option **nur sichtbare/gefilterte Zeilen**; **Redactions anwenden** Bestätigung mit Checkbox **„Auch Sidecar speichern“** (Default an); **Outlines-Export** Status-**Klick öffnet Zielordner**, Fehlerdialog **Retry**; Prefetch-Settings **Live-Label „aktuell N ms / ±N“**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### Formulare
- Feldliste CSV: **UTF-8 BOM** (Excel); Export-Option **nur sichtbare/gefilterte Zeilen**

### PDF / Redaction
- Bestätigung „Redactions anwenden“: Checkbox **Auch Sidecar speichern** (Default an)

### Bookmarks / Outlines
- Status nach Export: **Klick öffnet Export-Zielordner**; Schreibfehler → **Retry-Dialog**

### Performance
- Prefetch Settings: **Live-Label** „aktuell N ms / ±N“

### Packaging / Docs
- Version **1.3.4** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Forms CSV BOM+Filter, Redaction Sidecar-Checkbox, Outlines Ordner-Klick+Retry, Prefetch Live-Label (CLI + Qt)

---

## 1.3.3 — Forms CSV Spalten+Zielordner, Redaction Undo+Zähler, Outlines fehlende Datei, Prefetch Settings

Post-Release-Polish nach 1.3.2: **Forms-CSV** mit Spalten **Name,Typ,Wert,Seite,ReadOnly** und **Zielordner merken**; **Redaction Batch-Löschen** als **ein Undo-Stack-Eintrag** mit **Zähler im Bestätigungsdialog**; **Outlines-Export „anderes PDF“** fängt **fehlende Datei** ab, Status danach mit **Pfad**; **Lazy Prefetch ±N** und **Cancel-Debounce ms** in den **Einstellungen** (1/2/3 bzw. ms-Stufen). Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### Formulare
- Feldliste CSV: Spalten **Name, Typ, Wert, Seite, ReadOnly**; Export-**Zielordner merken**

### PDF / Redaction
- Mehrfachauswahl löschen: **ein Undo-Stack-Eintrag**; Bestätigungsdialog mit **Zähler N**

### Bookmarks / Outlines
- Export „Anderes PDF…“: **fehlende Datei** abfangen; nach Export Status mit **Pfad**

### Performance
- Thumbnail-Prefetch: Radius **±1 / ±2 / ±3** Settings; **Cancel-Debounce ms** Settings

### Packaging / Docs
- Version **1.3.3** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Forms CSV Spalten+Zielordner, Redaction Undo+Zähler, Outlines fehlende Datei, Prefetch Settings (CLI + Qt)

---

## 1.3.2 — Forms CSV·Checkbox/Choice, Redaction Multi+Undo, Outlines Ziel-PDF, Lazy Prefetch±2

Post-Release-Polish nach 1.3.1: **AcroForm-Feldliste CSV-Export**; **Checkbox/Choice-Werte** in Sidebar/Dialog sichtbar, **Edit nur Text**; **Redaction-Liste** mit **Mehrfachauswahl löschen** + **Undo** sowie **Doppelklick → Seite**; **Outlines-Export** mit Dialog **aktuelles / anderes Ziel-PDF** und Hinweis bei **leeren Outlines**; **Thumbnail-Lazy Prefetch ±2** um Viewport, **Cancel bei schnellem Scroll**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### Formulare
- Feldliste **CSV-Export** (Sidebar + Dialog); Checkbox/Choice **Werte anzeigen**; Edit nur Textfelder

### PDF / Redaction
- Sidebar: **Mehrfachauswahl** löschen (eine Undo-Stufe); **Doppelklick** springt zur Seite

### Bookmarks / Outlines
- Export-Dialog: Ziel **aktuelles PDF** oder **anderes PDF**; Hinweis bei leeren Outlines/Favoriten

### Performance
- Thumbnail-Lazy: **Prefetch ±2** um Viewport; Queue-**Cancel** bei schnellem Scroll

### Packaging / Docs
- Version **1.3.2** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Forms CSV·Checkbox/Choice, Redaction Multi+Undo, Outlines Ziel-PDF, Lazy Prefetch±2 (CLI + Qt)

---

## 1.3.1 — Forms Filter/RO/dirty, Redaction-Liste+Opacity, Outlines Duplikat-Dialog, Lazy-Threshold

Post-Release-Polish nach 1.3.0: **AcroForm** mit **Name-Filter**, **Read-only-Markierung** und Speichern nur **dirty** Felder; **Redaction-Liste** in der Sidebar mit **einzelnem Löschen** sowie **Preview-Deckkraft** in den Einstellungen; **Outlines→Bookmarks-Import** mit Dialog **Duplikate überspringen / Ersetzen**; **Thumbnail-Lazy-Schwellwert** wählbar (**25 / 50 / 100** Seiten) statt hart 50. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### Formulare
- Sidebar/Dialog: **Filter nach Name**; Read-only als **[RO]**/grau; Speichern nur geänderte Felder

### PDF / Redaction
- Sidebar-Liste der Schwärzungen; **einzeln löschen**; Preview-Deckkraft Settings

### Bookmarks / Outlines
- Import: bei bestehenden Favoriten Dialog **Duplikate überspringen** oder **Ersetzen**

### Performance
- Thumbnail-Lazy-Load: Schwellwert Settings **25 / 50 / 100** (Default 50)

### Packaging / Docs
- Version **1.3.1** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Forms Filter/RO/dirty, Redaction-Liste+Opacity, Outlines Duplikat-Dialog, Lazy-Threshold (CLI + Qt)

---

## 1.3.0 — AcroForm-Sidebar, Redactions→neues PDF, Bookmarks↔Outlines, Thumb Lazy >50

Minor-Release nach 1.2.9: **AcroForm-Feldliste** in der Sidebar (Name/Typ/Wert) mit Sprung zum Feld und einfacher Textfeld-Wert-Editierung via **pikepdf**; **Redactions anwenden** erzeugt ein **neues PDF** mit eingebrannten schwarzen Flächen (Rechteck-Werkzeug → Sidecar); **Bookmarks** aus PDF-Outlines importieren und als PDF-Outlines exportieren; **Thumbnail-Lazy-Load** für große PDFs (**>50 Seiten**) mit Platzhaltern für alle Seiten. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### Formulare
- Sidebar **AcroForm-Feldliste** (Name/Typ/Wert); Klick → Seite; Textfeld-Wert speichern via pikepdf

### PDF / Redaction
- Rechteck-Werkzeug speichert Schwärzung im Sidecar; **Redactions anwenden…** → neues PDF (schwarze Füllung bake)

### Bookmarks / Outlines
- **Bookmarks aus PDF-Outlines importieren** (→ Seiten-Favoriten); **Bookmarks als PDF-Outlines exportieren** (`write_outline`)

### Performance
- Thumbnail-Lazy-Load: bei **>50 Seiten** Platzhalter für alle Seiten + Nachladen (kein 40-Seiten-Cap)

### Packaging / Docs
- Version **1.3.0** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: AcroForm-Sidebar, Redactions→neues PDF, Bookmarks↔Outlines, Thumb Lazy >50 (CLI + Qt)

---

## 1.2.9 — Split-Log Footer Filter übersprungen, Ann. Reset Selektion, Diff Wrap-Blink lang/Beep, run.bat --version

Post-Release-Polish nach 1.2.8: **PDF-Split Log-Footer** ist **klickbar** und filtert die Liste auf **übersprungene** Einträge (Toggle); **Ann.-Export Reset-Template** setzt den **Fokus mit Selektion des ganzen Default-Texts** für schnelles Überschreiben; **Text-Diff Wrap-Blink** mit Dauer-Option **lang** und Sound klar als **System-Beep vs. stumm**; **`run.bat`** zeigt in der **gefunden**-Zeile kurz auch **`python --version`**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Split: Log-Footer **klickbar** → Filter Liste auf übersprungene Einträge (Toggle)

### Annotationen
- Export-Template: **Reset-Template** — Fokus + Selektion ganzer Default-Text

### Editor
- Text-Diff: Wrap-Blink Dauer **lang** (≈1200 ms); Sound **System-Beep vs. stumm**

### Packaging / Start
- **`run.bat`**: **gefunden**-Zeile inkl. kurz **`python --version`**; in `--help` dokumentiert

### Packaging / Docs
- Version **1.2.9** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Split-Log Footer Filter, Ann. Reset Selektion, Diff Wrap-Blink lang/Beep, run.bat --version (CLI + Qt)

---

## 1.2.8 — Split-Log Status geöffnet/übersprungen, Ann. Reset Vorschau+Fokus, Diff Wrap-Blink Dauer/Sound, run.bat gefunden

Post-Release-Polish nach 1.2.7: **PDF-Split „In Tabs öffnen“** meldet detailliert **geöffnet X, übersprungen Y** in **Statusleiste** und **Log-Footer**; **Ann.-Export Reset-Template** aktualisiert die **Live-Vorschau sofort** und setzt den **Fokus zurück ins Feld**; **Text-Diff Wrap-Blink** mit **Dauer Settings (kurz/mittel)** und optional **Sound aus**; **`run.bat`** gibt die gewählte Python-Binary als **`gefunden: …`** aus. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Split: Statuszählung detailliert **geöffnet X, übersprungen Y** in Statusleiste + Log-Footer

### Annotationen
- Export-Template: **Reset-Template** — Live-Vorschau sofort aktualisieren; Fokus zurück ins Feld

### Editor
- Text-Diff: Wrap-Blink **Dauer Settings (kurz/mittel)**; optional **Sound aus**

### Packaging / Start
- **`run.bat`**: gewählte Python-Binary in Konsolenzeile **`gefunden: …`**; in `--help` dokumentiert

### Packaging / Docs
- Version **1.2.8** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Split-Log Status geöffnet/übersprungen, Ann. Reset Vorschau+Fokus, Diff Wrap-Blink Dauer/Sound, run.bat gefunden (CLI + Qt)

---

## 1.2.7 — Split-Log Tabs Statuszählung, Ann. Reset-Bestätigung, Diff Wrap-Blink, run.bat py→python→python3

Post-Release-Polish nach 1.2.6: **PDF-Split „In Tabs öffnen“** überspringt fehlende Dateien und meldet **Statuszählung** (geöffnet/übersprungen); **Ann.-Export Reset-Template** fragt **nur bei Abweichung vom Default** nach Bestätigung; **Text-Diff Wrap-around** blinkt bei Sprung Anfang↔Ende **einmal akustisch und visuell**; **`run.bat`** bei ungültigem/leerem **`%ILD_PYTHON%`** versucht Fallback **`py -3` → `python` → `python3`**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Split: „In Tabs öffnen“ — fehlende Dateien **überspringen** + Statuszählung (geöffnet/übersprungen)

### Annotationen
- Export-Template: **Reset-Template** — Bestätigung **nur wenn Feld vom Default abweicht**

### Editor
- Text-Diff: Wrap-around bei Sprung Anfang↔Ende **einmal akustisch/visuell blinken**

### Packaging / Start
- **`run.bat`**: bei ungültigem/leerem **`%ILD_PYTHON%`** Fallback **`py -3` → `python` → `python3`** (nach `.venv`); in `--help` dokumentiert

### Packaging / Docs
- Version **1.2.7** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Split-Log Tabs Statuszählung, Ann. Reset-Bestätigung, Diff Wrap-Blink, run.bat py→python→python3 (CLI + Qt)

---

## 1.2.6 — Split-Log Pfad kopieren·Tabs, Ann. Undo lokal·Reset, Diff Status·Wrap, run.bat ILD_PYTHON-Fallback

Post-Release-Polish nach 1.2.5: **PDF-Split Pfad-Log Kontextmenü** mit **„Pfad kopieren“** und **„In Tabs öffnen“** für die Auswahl; **Ann.-Export-Template** mit **lokalem Undo (Ctrl+Z)** im Feld und Button **Reset-Template** auf Default; **Text-Diff** Status **„Änderung i/n“** und **Wrap-around** Toggle in Settings/Dialog; **`run.bat`** bei ungültigem **`%ILD_PYTHON%`** mit klarer DE-Fehlermeldung und Fallback-Hinweis (`.venv`/PATH). Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Split: Pfad-Log Kontextmenü **„Pfad kopieren“** + **„In Tabs öffnen“** (Auswahl)

### Annotationen
- Export-Template: **Ctrl+Z lokal** im Feld; Button **Reset-Template** → Default `{stem}_ann.json`

### Editor
- Text-Diff: Status **„Änderung i/n“**; Toggle **Wrap-around** (Settings + Dialog, persistiert)

### Packaging / Start
- **`run.bat`**: ungültiges **`%ILD_PYTHON%`** → klare DE-Fehlermeldung + Fallback-Hinweis (`.venv`/PATH); in `--help` dokumentiert

### Packaging / Docs
- Version **1.2.6** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Split-Log Pfad kopieren·Tabs, Ann. Undo lokal·Reset, Diff Status·Wrap, run.bat ILD_PYTHON-Fallback (CLI + Qt)

---

## 1.2.5 — Split-Log Mehrfachauswahl, Ann. Cursor/Undo, Diff Nav F7, run.bat ILD_PYTHON

Post-Release-Polish nach 1.2.4: **PDF-Split Pfad-Log** mit **Mehrfachauswahl**, Button **„Ordner der Auswahl öffnen“** und **Kontextmenü**; **Ann.-Export Quick-Insert** fügt an der **Cursor-Position** ein und unterstützt **Undo (Ctrl+Z)** im Template-Feld; **Text-Diff** mit Buttons **Nächste/Vorherige Änderung** (**F7** / **Shift+F7**); **`run.bat`** nutzt und dokumentiert Env-Override **`%ILD_PYTHON%`**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Split: Pfad-Log **Mehrfachauswahl**; **„Ordner der Auswahl öffnen“**; **Kontextmenü** (Öffnen / Ordner / Auswahl / Kopieren)

### Annotationen
- Export-Template: Quick-Insert an **Cursor-Position**; **Undo** im Template-Feld (Ctrl+Z)

### Editor
- Text-Diff: Buttons **Nächste/Vorherige Änderung**; Tasten **F7** / **Shift+F7**

### Packaging / Start
- **`run.bat`**: Env-Override **`%ILD_PYTHON%`** (höchste Priorität vor `.venv`/PATH); in `--help` dokumentiert

### Packaging / Docs
- Version **1.2.5** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Split-Log Mehrfachauswahl·Ordner·Kontextmenü, Ann. Cursor/Undo, Diff Nav F7, run.bat ILD_PYTHON (CLI + Qt)

---

## 1.2.4 — Split-Log Doppelklick, Ann. Quick-Insert, Diff Sync-Scroll Settings, run.bat Python-Download

Post-Release-Polish nach 1.2.3: **PDF-Split Pfad-Log** öffnet per **Doppelklick** Datei/Ordner und zeigt bei **leerem Log** einen Hinweis; **Ann.-Export-Template** mit Quick-Insert-Buttons **`{stem}`** / **`{page}`** / **`{date}`**; **Text-Diff Sync-Scroll** als Toggle in **Settings**; **Ignore-Whitespace** wird **persistiert**; **`run.bat`** bei fehlendem Python mit kurzem Download-Hinweis **Microsoft Store** / **python.org**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Split: Pfad-Log **Doppelklick** öffnet Datei bzw. Ordner; Hinweis bei **leerem Log**

### Annotationen
- Export-Template: Quick-Insert-Buttons **`{stem}`** / **`{page}`** / **`{date}`** neben dem Feld

### Editor
- Text-Diff: **Sync-Scroll** Toggle in Settings; **Ignore-Whitespace** persistiert (Dialog ↔ Settings)

### Packaging / Start
- **`run.bat`**: bei fehlendem Python kurzer DE-Hinweis — Microsoft Store / python.org

### Packaging / Docs
- Version **1.2.4** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Split-Log Doppelklick·leer, Ann. Quick-Insert, Diff Sync-Scroll Settings·Ignore-WS Persistenz, run.bat Python-Download (CLI + Qt)

---

## 1.2.3 — Split-Log kopieren/TXT·Tabs persistieren, Ann. ungültige Platzhalter, Diff Ignore-WS·Sync-Scroll, run.bat --help

Post-Release-Polish nach 1.2.2: **PDF-Split Pfad-Log** kann **kopiert** bzw. **als TXT gespeichert** werden; Checkbox **„in Tabs öffnen“** wird **persistiert**; **Ann.-Export Live-Vorschau** markiert **ungültige Platzhalter rot**; **Text-Diff** mit **Ignore-Whitespace** und **Sync-Scroll** im Side-by-Side; **`run.bat --help`** auf Deutsch sowie **Hinweis bei lokaler .venv**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Split: Pfad-Log **kopieren** / **als TXT speichern**; Checkbox **Erzeugte Dateien in Tabs öffnen** persistiert

### Annotationen
- Export-Template Live-Vorschau: **ungültige Platzhalter** (nicht `{stem}`/`{page}`/`{date}`) **rot** markiert

### Editor
- Text-Diff: Toggle **Ignore-Whitespace**; **Sync-Scroll** Side-by-Side

### Packaging / Start
- **`run.bat --help` / `-h` / `/?`**: deutsche Hilfe; Hinweis wenn lokale **`.venv`** vorhanden aber unvollständig

### Packaging / Docs
- Version **1.2.3** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Split-Log kopieren/TXT·Tabs-Persistenz, Ann. ungültige Platzhalter, Diff Ignore-WS·Sync-Scroll, run.bat --help (CLI + Qt)

---

## 1.2.2 — PDF-Split Tabs·Pfad-Log, Ann.-Template {page}/{date}, Diff Unified·Wort-HL, run.bat --yes

Post-Release-Polish nach 1.2.1: **PDF-Split** kann erzeugte Dateien optional in **Tabs öffnen** und zeigt ein **Pfad-Log**; **Ann.-Export-Template** dokumentiert Platzhalter **`{page}`** / **`{date}`** mit **Live-Vorschau**; **Text-Diff** mit Toggle **Side-by-Side / Unified** und einfachem **Wort-Highlight**; **`run.bat --yes`** für non-interactive pip inkl. dokumentierter **Exit-Codes**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Split: Checkbox **Erzeugte Dateien in Tabs öffnen**; **Pfad-Log** der erzeugten Dateien

### Annotationen
- Export-Template: Platzhalter **`{page}`**, **`{date}`** (YYYY-MM-DD) dokumentiert; Settings-**Live-Vorschau** Dateiname

### Editor
- Text-Diff: Toggle **Unified** vs. Side-by-Side; **Wort-Highlight** in geänderten Zeilen

### Packaging / Start
- **`run.bat --yes` / `-y`**: non-interactive `pip install -r requirements.txt`; Exit-Codes dokumentiert (0 OK · 1 Fehler)

### Packaging / Docs
- Version **1.2.2** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Split Tabs·Log, Ann.-Template {page}/{date}·Vorschau, Diff Unified·Wort-HL, run.bat --yes (CLI + Qt)

---

## 1.2.1 — PDF-Split Validierung·Vorschau, Ann.-Export Template, Diff Toggle·TXT, run.bat pip

Post-Release-Polish nach 1.2.0: **PDF-Split/Extrakt** validiert fehlerhafte Bereiche mit klaren **DE-Meldungen** und zeigt **Seitenanzahl-Vorschau**; **Ann.-Export** merkt den **Zielordner** und nutzt ein Dateiname-Template aus Settings (`{stem}_ann.json`); **Text-Diff** mit Toggle **Nur Unterschiede** + **Zeilennummern** sowie **Diff als TXT**; **`run.bat`** bietet optional `python -m pip install -r requirements.txt` per **J/N**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Split/Extrakt: klare deutsche Fehlermeldungen bei ungültigen Bereichen; Live-**Vorschau Seitenanzahl**

### Annotationen
- Export: **Zielordner merken**; Dateiname-Template in Settings (**`{stem}_ann.json`**, optional `{page}`)

### Editor
- Text-Diff: Toggle **Nur Unterschiede** + **Zeilennummern**; **Diff als TXT** exportieren

### Packaging / Start
- **`run.bat`**: bei fehlenden Deps optional **`python -m pip install -r requirements.txt`** (J/N)

### Packaging / Docs
- Version **1.2.1** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: PDF-Split Validierung·Vorschau, Ann.-Export Template/Ordner, Diff Toggle·TXT, run.bat pip (CLI + Qt)

---

## 1.2.0 — PDF Split Bereiche, Ann.-Export JSON/Flatten, Text-Diff Panel, run.bat Deps

Minor-Release nach 1.1.9: **PDF-Split/Extrakt** mit Seitenbereichen `1-3,5,8-10` → neue Datei(en); **Annotation-Export** aktuelle Seite oder Dokument als JSON (**ildann-v4**) inkl. optionalem **Flatten-PDF**; **Text-Diff Panel** vergleicht zwei offene Text-Tabs; Windows **`run.bat`** prüft Python/Abhängigkeiten mit klaren DE-Meldungen. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF
- Seitenbereiche **`1-3,5,8-10`** extrahieren (eine Datei oder eine Datei pro Bereich); Split-Tab Bereiche 1-basiert

### Annotationen
- Export-Dialog: **aktuelle Seite / Dokument** → JSON **ildann-v4** + optional **Flatten-PDF**

### Editor
- **Text-Diff Panel**: zwei offene Text-Tabs (Ctrl+Alt+D), nicht-modales Zeilen-Diff Panel

### Packaging / Start
- **`run.bat`**: Python ≥3.10 + PySide6/pypdfium2/pikepdf/Pillow prüfen, klare deutsche Fehlermeldungen

### Packaging / Docs
- Version **1.2.0** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: PDF Split-Bereiche, Ann.-Export JSON/Flatten, Text-Diff Panel, run.bat Deps (CLI + Qt)

---

## 1.1.9 — OCR Toast Dauer·A11y, Merge Tooltip Settings, Ann. Sticky Undo/Redo, Keygen Pause-Tooltip

Post-Release-Polish nach 1.1.8: OCR-Toast **„OCR-Defaults gespeichert“** mit einstellbarer Dauer **1/2/3 s** und **Accessibility-Announcement**; Merge-**Readonly-schließen**-Checkbox in Settings trägt denselben Persistenz-Tooltip wie der Merge-Dialog; Annotationen-Sticky-Status wird zusätzlich bei **Undo/Redo** geleert; Keygen-Countdown-Tooltip bei Pause: **„Countdown pausiert (Fenster ohne Fokus)“**. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### OCR / Batch
- Toast-Dauer in Settings **1 / 2 / 3 s** (Default 2) + Screenreader-**Announcement**

### PDF
- **Zusammenführen**: Settings-Checkbox **Readonly schließen** mit **identischem Tooltip** wie Merge-Dialog

### Annotationen
- Sticky 0-Treffer-Status: **Clear** zusätzlich bei Annotationen-**Undo/Redo**

### Keygen
- Countdown pausiert: Tooltip **„Countdown pausiert (Fenster ohne Fokus)“**

### Packaging / Docs
- Version **1.1.9** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: OCR Toast Dauer·A11y, Merge Tooltip Settings, Ann. Sticky Undo/Redo, Keygen Pause-Tooltip (CLI + Qt)

---

## 1.1.8 — OCR Defaults Toast·Highlight, Merge-Toggle Tooltips, Ann. Sticky Clear, Keygen „pausiert“

Post-Release-Polish nach 1.1.7: OCR-Button **„Als Defaults speichern“** zeigt Toast/Status **„OCR-Defaults gespeichert“** und kurz hervorgehobene Felder; Merge-Dialog-Toggle erklärt per Tooltip die **Settings-Persistenz**; Annotationen-Sticky-Status wird bei **Seiten- und Dokumentwechsel** geleert; Keygen-Countdown zeigt am Label **„pausiert“** bei Fokusverlust. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### OCR / Batch
- Toast/Status **„OCR-Defaults gespeichert“** + Kurz-Highlight von Sprach-/DPI-Feldern

### PDF
- **Zusammenführen**: Toggle-Tooltip erklärt Persistenz in Settings (beidseitiger Sync)

### Annotationen
- Sticky 0-Treffer-Status: **Clear** bei Seitenwechsel und Dokumentwechsel

### Keygen
- Countdown-Label zeigt **„pausiert“** bei Fokusverlust (Zahl bleibt stehen)

### Packaging / Docs
- Version **1.1.8** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: OCR Defaults Toast·Highlight, Merge-Toggle Tooltips, Ann. Sticky Clear, Keygen „pausiert“ (CLI + Qt)

---

## 1.1.7 — OCR Defaults-Button, Merge-Toggle im Dialog, Ann. Sticky-Status, Keygen Countdown-Pause

Post-Release-Polish nach 1.1.6: OCR-Dialog mit Button **„Als Defaults speichern“** neben DPI/Sprache; Merge-Dialog zeigt denselben **Readonly-schließen**-Toggle wie Settings (sofort synchron); Annotationen-**0-Treffer**-Status bleibt **dauerhaft in der Statusleiste** bis zur nächsten Ann.-Aktion; Keygen-Countdown **pausiert bei Fokusverlust** und setzt bei Fokus fort. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### OCR / Batch
- Button **„Als Defaults speichern“** neben Sprach-Preset/DPI (sofort Settings, ohne Dialog schließen)

### PDF
- **Zusammenführen**: Toggle **„Readonly-Vorschau … schließen“** auch im Merge-Dialog (Sync mit Settings)

### Annotationen
- Status bei **0 Treffern**: dauerhaft in Statusleiste (Label + Message) bis nächste Ann.-Aktion

### Keygen
- Reveal-Countdown: **Pause** bei Fenster/App inaktiv; **Fortsetzen** bei Fokus

### Packaging / Docs
- Version **1.1.7** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: OCR Defaults-Button, Merge-Dialog-Toggle, Ann. Sticky-Status, Keygen Countdown-Pause (CLI + Qt)

---

## 1.1.6 — OCR DPI·Preset-Defaults, Merge Vorschau schließen, Ann. 0-Treffer i18n, Keygen Auto-Hide 5/10/30

Post-Release-Polish nach 1.1.5: OCR-Dialog speichert **DPI** und **Sprach-Preset** als Settings-Defaults und belegt sie vor; Merge **„Zum Bearbeiten öffnen“** kann den Readonly-Tab per Settings-Toggle schließen; Annotationen-Status bei **0 gefilterten Treffern** nutzt einen einheitlichen i18n-String (DE); Keygen-Reveal Auto-Hide wählbar **5/10/30 s** mit Countdown neben Reveal. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### OCR / Batch
- **DPI** + **Sprach-Preset** als Defaults in Settings persistiert; Dialog vorbelegt und speichert bei OK

### PDF
- **Zusammenführen**: **„Zum Bearbeiten öffnen“** schließt Readonly-Tab optional (Settings-Toggle)

### Annotationen
- Status bei **0 Treffern**: einheitlicher String `Keine gefilterten Treffer auf Seite {page}` (i18n DE)

### Keygen
- Reveal Auto-Hide: Intervall **5 / 10 / 30 s** (Settings) + **Countdown** neben Reveal

### Packaging / Docs
- Version **1.1.6** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: OCR Defaults, Merge close-preview, Ann. i18n-0-Treffer, Keygen Auto-Hide (CLI + Qt)

---

## 1.1.5 — OCR Fehler-Persistenz, Merge Preview-Banner, Ann. Menü-No-op, Keygen Reveal-Timer

Post-Release-Polish nach 1.1.4: OCR-Toggle **„Fehler anhängen“** wird in den Einstellungen persistiert (Dialog + Settings); Merge-Readonly-Vorschau zeigt Banner **„Vorschau“** mit Button **„Zum Bearbeiten öffnen“**; gefiltertes Annotationen-Löschen bei 0 Treffern: Menü/Aktion ebenfalls no-op mit Statushinweis; Keygen-Reveal Auto-Hide nach 10 s, Esc maskiert wieder. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### OCR / Batch
- Toggle **„Fehler anhängen“** in **Settings persistiert** (`ocr_attach_errors`, Default an); Dialog übernimmt den Wert

### PDF
- **Zusammenführen**: Readonly-Vorschau-Tab mit Banner **„Vorschau“** + **„Zum Bearbeiten öffnen“** (echtes Dokument)

### Annotationen
- Gefiltertes Löschen: bei **0 Treffern** auch Menü/Aktion **no-op mit Status** (kein Dialog)

### Keygen
- Reveal: **Auto-Hide nach 10 s**; **Esc** maskiert History wieder

### Packaging / Docs
- Version **1.1.5** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: OCR Persistenz, Merge Preview-Banner, Ann. Menü-No-op, Keygen Reveal-Timer (CLI + Qt)

---

## 1.1.4 — OCR Fehler-Toggle, Merge-Preview-Tab, Ann. 0-Treffer, Keygen Mask/Copy

Post-Release-Polish nach 1.1.3: OCR-Batch-Dialog mit Toggle **„Fehler anhängen“** (Standard an); Merge-Vorschau-Thumbnail per Klick öffnet die Datei als Readonly-Vorschau in neuem Tab; gefiltertes Annotationen-Löschen bei 0 Treffern mit disabled Button + Statushinweis; Keygen-History maskiert Keys (nur letzte 4), Reveal/Hover zeigt Klartext, Doppelklick kopiert. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### OCR / Batch
- Dialog-Toggle **„Fehler anhängen“** (Default an) steuert den Abschnitt **„OCR-Fehler“** im Ergebnis-TXT

### PDF
- **Zusammenführen**: Thumbnail-**Klick** öffnet Datei als **Readonly-Vorschau** (neuer Tab)

### Annotationen
- Gefiltertes Löschen: bei **0 Treffern** Yes-Button disabled + Statushinweis

### Keygen
- History: **Maskierung** (nur letzte 4 sichtbar) bis Hover/Reveal; **Doppelklick kopiert** Key

### Packaging / Docs
- Version **1.1.4** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: OCR Fehler-Toggle, Merge Preview-Tab, Ann. 0-Treffer, Keygen Mask/Copy (CLI + Qt)

---

## 1.1.3 — OCR Seitenfehler·Teilergebnis, Merge-Vorschau, Ann. Undo gefiltert, Keygen-History

Post-Release-Polish nach 1.1.2: OCR-Batch sammelt Fehler pro Seite und hängt sie als Abschnitt an das Ergebnis-TXT; Abbruch behält Teilergebnis; PDF-Zusammenführen zeigt Vorschau-Thumbnail der markierten Datei (erste Seite); gefiltertes Annotationen-Löschen mit Undo-Text „N Annotationen (gefiltert)“; Keygen speichert lokal die letzten 10 Keys inkl. Clear History (ohne Secrets in Logs). Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### OCR / Batch
- **Seitenfehler** werden gesammelt und am Ende als Abschnitt **„OCR-Fehler“** im Ergebnis-TXT
- **Abbruch** behält **Teilergebnis** (bisherige Seiten + Fehlerliste)

### PDF
- **Zusammenführen**: **Vorschau-Thumbnail** der markierten Datei (erste Seite)

### Annotationen
- Gefiltertes Löschen: Undo-Text **„N Annotationen (gefiltert)“**

### Keygen
- GUI/CLI: lokale **History der letzten 10 Keys**; Button **Clear History** (keine Secrets in Logs)

### Packaging / Docs
- Version **1.1.3** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: OCR page_errors·Teilergebnis, Merge-Vorschau, Ann. Undo gefiltert, Keygen-History (CLI + Qt)

---

## 1.1.2 — OCR DPI·Seitenbereich, Merge DnD·Duplikat, Ann. Filter-Löschen, Keygen .txt/--days

Post-Release-Polish nach 1.1.1: OCR-Batch mit DPI-Auswahl 150/300 und optionalem Seitenbereich von–bis; PDF-Zusammenführen nimmt Dateien per Drag&Drop in die Liste und warnt bei Duplikaten; „Alle Annotationen auf Seite löschen“ mit Option nur sichtbare/gefilterte; Keygen speichert als .txt, CLI `--days` bleibt kompatibel. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### OCR / Batch
- **DPI**-Einstellungen **150 / 300** im OCR-Dialog; optionaler **Seitenbereich von–bis**

### PDF
- **Zusammenführen**: Dateien per **Drag&Drop** in die Liste; **Duplikat-Warnung** (übersprungen)

### Annotationen
- **Alle auf Seite löschen…**: Option **nur sichtbare/gefilterte** Annotationen

### Keygen
- GUI: **Speichern als .txt…**; CLI **`--days`** (ohne Flag unverändert / kompatibel)

### Packaging / Docs
- Version **1.1.2** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: OCR DPI·Range, Merge DnD·Duplikat, Ann. Filter-Option, Keygen .txt/--days (CLI + Qt)

---

## 1.1.1 — OCR Sprach-Preset/Pfad, Merge Doppelklick·Summe, Ann.-Zähler, Keygen Gültigkeit

Post-Release-Polish nach 1.1.0: OCR-Batch mit klarer Sprach-Preset-Combobox und Tesseract-Hinweis inkl. Wiki-Link sowie Windows-Pfad-Hilfe; PDF-Zusammenführen mit Doppelklick-Entfernen, „Alle entfernen“ und Seitenzahl-Summe; Bestätigungsdialog „Alle Annotationen auf Seite löschen“ mit Zähler „N Annotationen“; Keygen zeigt Gültigkeitstage neben dem generierten Key. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### OCR / Batch
- **Sprach-Preset**-Combobox im OCR-Dialog (Batch-Titel); fehlendes Tesseract: Hinweis mit **Link** (UB-Mannheim Wiki) + **Pfad-Hilfe** (`C:\Program Files\Tesseract-OCR\…`)

### PDF
- **Zusammenführen**: **Doppelklick** entfernt Eintrag; Button **Alle entfernen**; Label **Seiten gesamt** (Summe)

### Annotationen
- **Alle auf Seite löschen…**: Bestätigung mit explizitem Zähler (**N Annotation** / **N Annotationen**)

### Keygen
- GUI: **Gültigkeit: X Tage** neben generiertem Key (Label neben Ausgabe)

### Packaging / Docs
- Version **1.1.1** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: OCR Preset·Pfad, Merge Doppelklick·Alle·Summe, Ann.-Zähler, Keygen Gültigkeit (CLI + Qt)

---

## 1.1.0 — OCR-Batch Text-Tab, PDF-Merge Drag, Ann. Seite löschen, Keygen Copy

Minor-Release nach 1.0.9: OCR gesamtes PDF schreibt Ergebnis in eine neue Textdatei-Tab (`*-ocr.txt`) bei Fortschrittsdialog mit Abbruch; PDF-Zusammenführen mit Mehrfachauswahl und Drag-Reihenfolge; „Alle Annotationen auf Seite löschen“ mit Bestätigung und einem Undo-Schritt; Keygen-GUI Klartext ohne QR plus Kopieren-Button. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### OCR / Batch
- **OCR gesamtes PDF**: Fortschritt + Abbrechen; Ergebnis als **neue Textdatei-Tab** (PDF-Tab bleibt)

### PDF
- **Zusammenführen**: Mehrfachauswahl beim Hinzufügen; **Drag-InternalMove** für Reihenfolge (▲/▼ bleiben); Ziel speichern

### Annotationen
- **Alle auf Seite löschen…**: Bestätigung; ein Undo-Schritt via `AnnotationStore.clear_page` / `atomic`

### Keygen
- GUI: Ausgabe **Klartext (ohne QR)**; Button **Kopieren** → Zwischenablage

### Packaging / Docs
- Version **1.1.0** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: OCR-Tab, Merge-Drag, clear_page Confirm·Undo, Keygen Copy (CLI + Qt)

---

## 1.0.9 — Druckvorschau Tastatur, Banner Fokus·Enter, Backup-Sort, Weiter disabled

Post-Release-Polish nach 1.0.8: Druckvorschau mit Tastatur PageUp/PageDown·Home/End für Seiten und +/- für Zoom; Lizenz-Banner mit sichtbarem Fokus-Ring und Enter öffnet Aktivierung; Backup-Log Sortier-Toggle „Neueste zuerst“ plus Hinweistext bei leerer Liste; Willkommen „Weiterarbeiten“ deaktiviert mit Tooltip wenn Session-Datei fehlt oder leer. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### Willkommen / Start
- **Weiterarbeiten**: bei fehlender/leerer Session-Datei **deaktiviert** + Tooltip (`_session_file_status`); sichtbar wenn Restore aus

### PDF / Druck
- **Druckvorschau**: Tastatur **PageUp/PageDown** + **Home/End** für Seiten; **+/-** Zoom (`keyPressEvent`)

### About / Lizenz
- Banner: **Fokus-Ring** (`:focus`-Stylesheet); **Enter** öffnet About/Aktivierung; Fokus beim Einblenden

### Backup
- Einstellungen: Toggle **„Neueste zuerst“** (`sort_backup_log`); **Hinweistext** bei leerer Liste / leerem Filter

### Packaging / Docs
- Version **1.0.9** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Preview Keys, Banner Focus·Enter, Backup Sort·Empty, Welcome Disabled (CLI + Qt)

---

## 1.0.8 — Druckvorschau Fit-Page/Mausrad, Banner Esc·a11y, Backup-Log BOM, Weiter-Tooltip

Post-Release-Polish nach 1.0.7: Druckvorschau mit Fit-Page-Toggle und Mausrad-Zoom; Lizenz-Banner schließt mit Esc und setzt Screenreader-AccessibleName; Backup-Log-TXT mit Zeitstempel im Dateinamen und UTF-8-BOM für Excel; Willkommen-Tooltip „Weiterarbeiten“ mit Tab-Anzahl und Pfad-Snippet der ersten Datei. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### Willkommen / Start
- **Weiterarbeiten**-Tooltip: **Anzahl Tabs** + **Pfad-Snippet** der ersten Session-Datei (`_path_snippet`)

### PDF / Druck
- **Druckvorschau**: **Fit-Page**-Toggle („Seite einpassen“) + **Mausrad-Zoom** über dem Vorschaubereich (Zoom beendet Fit-Page)

### About / Lizenz
- Banner: **Esc** schließt (Dismiss bis morgen); **AccessibleName** für Banner/Icon/Buttons (i18n)

### Backup
- Log-Export: Standardname **`backup-log-YYYYMMDD-HHMMSS.txt`**; Schreibweise **UTF-8 mit BOM** (`utf8_bom`, Excel)

### Packaging / Docs
- Version **1.0.8** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Preview Fit/Wheel, Banner Esc·a11y, Backup BOM·Timestamp, Welcome Tooltip (CLI + Qt)

---

## 1.0.7 — Druckvorschau Zoom/Seiten, Banner Icon·X, Backup-Filter·Export, Weiterarbeiten

Post-Release-Polish nach 1.0.6: Druckvorschau mit Zoom +/- und Seitenwahl bei Mehrseiten-Bereich; Lizenz-Banner mit Icon, Dismiss-Button und Schließen-X (Persistenz `dismiss_date`); Backup-Log Filter Erfolg/Fehler plus TXT-Export; Willkommen-Button „Weiterarbeiten“ für letzte Session-Tabs wenn Session-Restore aus. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### Willkommen / Start
- **Weiterarbeiten**-Button: öffnet letzte Session-Tabs wenn „Offene Tabs wiederherstellen“ aus und Session vorhanden (`continue_session_requested` / `_restore_session(force=True)`)

### PDF / Druck
- **Druckvorschau**: **Zoom +/-** (50–300 %); bei **Mehrseiten-Bereich** Seitenwahl (Spin/◀▶) mit Lazy-Render der gewählten Seite

### About / Lizenz
- Banner: **Warn-Icon** + Text-Button **Dismiss** + **Schließen-X** daneben; Persistenz **`dismiss_date`** (Kompatibilität `expiry_warn_day`)

### Backup
- Einstellungen: Log-**Filter** Alle / Nur Erfolg / Nur Fehler; **Log exportieren…** als TXT (`export_backup_log_txt`)

### Packaging / Docs
- Version **1.0.7** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Preview Zoom/Pages, Banner Icon·X·dismiss_date, Backup Filter·Export, Welcome Continue (CLI + Qt)

---

## 1.0.6 — Filter Esc, Druckvorschau, Banner i18n/Farben, Backup-Log Doppelklick

Post-Release-Polish nach 1.0.5: Willkommen-Filter Esc leert und Fokus zurück auf Liste; Dokumentdruck mit optionalem Vorschau-Dialog (Thumbnail erste Seite, Toggle in Dialog/Settings); Lizenz-Banner Text über i18n (DE) mit getrennten Farben für Warnung vs. abgelaufen; Backup-Log Doppelklick öffnet Backup-Datei bzw. Ordner wenn Datei fehlt. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### Willkommen / Start
- Filter: **Esc** leert den Filter und setzt den Fokus zurück auf die Recent-Liste (`_escape_recent_filter`)

### PDF / Druck
- **Dokument drucken…**: optionaler **Vorschau-Dialog** mit Thumbnail der ersten Druckseite vor dem Druckjob; Toggle in Seitenbereich-Dialog und Einstellungen (`print_preview`, Standard an)

### About / Lizenz
- Banner-Text **i18n-klar** (DE/EN über `tr`); Farbe **Warnung** (gelb) vs. **abgelaufen** (rot); Abgelaufen zeigt ebenfalls Banner (Dismiss bis morgen)

### Backup
- Einstellungen: **Doppelklick** auf Log-Eintrag öffnet Backup-Datei bzw. Ordner wenn Datei fehlt

### Packaging / Docs
- Version **1.0.6** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Filter Esc, Print Preview, Banner i18n/Colors, Backup-Log Doppelklick (CLI + Qt)

---

## 1.0.5 — Filter Clear/Treffer, Druck-Abbruch Cleanup, Warnung Klick/Dismiss, Backup-Log Copy/Clear

Post-Release-Polish nach 1.0.4: Willkommen-Filter mit explizitem Clear-Button und Trefferanzahl-Label; Mehrseiten-Druck-Abbruch verwirft den Job sauber (`printer.abort`) mit Status „Druck abgebrochen“; Lizenz-Ablaufwarnung als Banner — Klick öffnet About/Aktivierung, Dismiss speichert bis morgen; Backup-Log Eintrag kopieren und Log leeren in Einstellungen. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### Willkommen / Start
- Filter: **Clear-Button** („Filter leeren“) + **Trefferanzahl**-Label (`n Treffer` / `n / m Treffer`)

### PDF / Druck
- **Dokument drucken…**: Abbruch → **sauberes Cleanup** ohne halben Druckauftrag (`painter.end` + `printer.abort`); Status **„Druck abgebrochen“**

### About / Lizenz
- Ablaufwarnung ≤3 Tage: **Banner** (nicht modal); **Klick → Info/Aktivierung**; **Dismiss (×) speichert bis morgen**

### Backup
- Einstellungen: **Eintrag kopieren** (Zwischenablage) + **Log leeren** (`clear_backup_log`)

### Packaging / Docs
- Version **1.0.5** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Filter Clear/Hits, Print Abort Cleanup, Expiry Click/Dismiss, Backup-Log Copy/Clear (CLI + Qt)

---

## 1.0.4 — Willkommen Recent-Filter, Druck-Fortschritt, Ablauf-Warnung 3d, Backup-Log

Post-Release-Polish nach 1.0.3: Willkommen-Recent mit Live-Suchfilter; Mehrseiten-Dokumentdruck mit abbrechenbarem Fortschrittsdialog; Lizenz-Warnung ≤3 Tage vor Ablauf einmalig pro Tag (Status/Tray, nicht modal); Backup-Log der letzten 20 Vorgänge in den Einstellungen. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### Willkommen / Start
- **Live-Suchfilter** über die Recent-Liste (Dateiname/Pfad, sofort beim Tippen)

### PDF / Druck
- **Dokument drucken…**: bei **Mehrseiten**-Druck Fortschrittsdialog mit **Abbrechen** (`processEvents`); Einzelseite ohne Dialog

### About / Lizenz
- Warnung **≤3 Tage** vor Ablauf: einmalig pro Kalendertag, Statusleisten-Hinweis (+ Tray falls aktiv), **nicht modal**

### Backup
- Log der letzten **20** manuellen Backup-Vorgänge in **Einstellungen** lesbar (`backup_log.json`)

### Packaging / Docs
- Version **1.0.4** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Welcome-Filter, Print-Progress-Cancel, Expiry-Warn, Backup-Log (CLI + Qt)

---

## 1.0.3 — Willkommen Enter/Delete, Druck-Graustufen, Ablauf TT.MM.JJJJ, Backup max. 3

Post-Release-Polish nach 1.0.2: Willkommen-Recent per Enter öffnen und Delete entfernen; Dokumentdruck mit Graustufen-Toggle (Settings + Druckdialog); Lizenz-Ablaufdatum einheitlich TT.MM.JJJJ in About und Status; Backup-Retry max. 3 Versuche dann Abbruch-Hinweis. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### Willkommen / Start
- **Enter** / Return öffnet den ausgewählten Recent-Eintrag
- **Entf** / Backspace entfernt den ausgewählten Recent-Eintrag

### PDF / Druck
- **Dokument drucken…**: Graustufen-Toggle im Seitenbereich-Dialog; Einstellung auch in **Einstellungen** („Dokumentdruck in Graustufen“); wird gemerkt

### About / Lizenz
- Ablaufdatum als **TT.MM.JJJJ** in About, Statusleiste und Lizenzdialog (`format_ablaufdatum`)

### Backup
- Bei Schreibfehler: max. **3 Versuche**, danach Abbruch-Hinweis (kein weiteres Retry)

### Packaging / Docs
- Version **1.0.3** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Welcome Enter/Delete, Print Graustufen, Ablaufdatum, Backup max-3 (CLI + Qt)

---

## 1.0.2 — Willkommen Drag&Drop/Clear-Recent, Druck-DPI, Trial-Resttage, Backup-Retry

Post-Release-Polish nach 1.0.1: Willkommen mit Drag&Drop zum Öffnen und Button „Recent leeren“; PDF-Dokumentdruck mit DPI-Auswahl 72/150/300 für Raster; Trial-Resttage in Statusleiste und About einheitlich („noch X Tage“); Backup-Schreibfehler mit Retry-Dialog. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### Willkommen / Start
- **Drag & Drop** Dateien auf die Startseite → öffnen
- Button **Recent leeren** (wie Menü „Liste leeren“)

### PDF / Druck
- **Dokument drucken…**: DPI-Auswahl **72 / 150 / 300** im Seitenbereich-Dialog; Raster-Scale = DPI/72; zuletzt genutzte DPI wird gemerkt

### About / Lizenz
- Trial-/Lizenz-**Resttage** Statusleiste + About (+ Lizenzdialog) über gemeinsame `resttage_phrase()` / `format_resttage()`

### Backup
- Bei **Schreibfehler** (OSError): Fehlerdialog mit **Retry** / Abbrechen

### Packaging / Docs
- Version **1.0.2** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Welcome Drag&Drop/Clear-Recent, Print DPI, Resttage-Konsistenz, Backup-Retry (CLI + Qt)

---

## 1.0.1 — Willkommen-Kontextmenü, Druck-Seitenbereich, Lizenz aktivieren, Backup-Pfad

Post-Release-Polish nach 1.0.0: Willkommen-Recent mit Rechtsklick Entfernen/Ordner öffnen und grauen fehlenden Pfaden; PDF-Dokumentdruck mit Seitenbereich von–bis vor QPrintDialog; About mit „Lizenz aktivieren…“ bei Trial/ungültig; Backup-Statusmeldung mit Pfad der letzten Backup-Datei. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### Willkommen / Start
- Recent-Liste: **Rechtsklick → Entfernen** / **Ordner öffnen**; fehlende Pfade grau („fehlt“)

### PDF / Druck
- **Dokument drucken…**: Dialog **Seitenbereich (von–bis)** vor QPrintDialog; nur gewählte Seiten gerastert

### About / Lizenz
- Button **Lizenz aktivieren…** wenn Trial, abgelaufen oder ungültig

### Backup
- Statusleiste zeigt **vollen Pfad** der letzten Backup-Datei (`_last_backup_path`)

### Packaging / Docs
- Version **1.0.1** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Welcome-Kontextmenü, PrintRangeDialog, About-Aktivieren, Backup-Pfad (CLI + Qt)

---

## 1.0.0 — About/Lizenz/Changelog, Backup jetzt, PDF-Dokumentdruck, Willkommen

Major-Release nach 0.9.9: About zeigt Version, Lizenzstatus und Kontakt ame@sellerbach.de plus Changelog-Kurzliste; manuelles „Backup jetzt“ und Backup-Ordner öffnen; PDF-Dokumentdruck (alle Seiten) via QPrintDialog und Raster (pypdfium2); Willkommens-Startseite mit Recent-Liste und „Dokument öffnen“ / „Leeres Text“ wenn keine Tabs. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### About / Hilfe
- **About**: Version, **Lizenzstatus** (Trial/lizenziert/abgelaufen + Resttage), Kontakt **ame@sellerbach.de**, Changelog-Kurzliste aus CHANGELOG.md
- Buttons FEATURES.md / CHANGELOG.md öffnen

### Backup
- Datei → **Backup jetzt**: aktuelles Dokument (Datei + Sidecar bzw. ungespeicherter Text) nach Config/`backups/`
- Datei → **Backup-Ordner öffnen…**

### PDF / Druck
- PDF → **Dokument drucken…**: alle Seiten gerastert (pypdfium2) über QPrintDialog; Ctrl+P bleibt aktuelle Seite
- Seite drucken unverändert (Annotationen)

### Willkommen / Start
- Startseite wenn keine Tabs: Recent-Liste, **Dokument öffnen…**, **Leeres Text**

### Packaging / Docs
- Version **1.0.0** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: About-Lizenz/Changelog, Backup jetzt/Ordner, print_document, WelcomePage (CLI + Qt)

---

## 0.9.9 — Autosave-.ildbak, HL-Tag-Combobox, Factory-Confirm/Undo, Session Fill/Stroke

Nach 0.9.8: Autosave kann vor Überschreiben rotierende `.ildbak`-Backups anlegen (Toggle + max. 1–10); PDF-Suche→Highlight schlägt zuletzt genutzte Tags per Combobox vor; Color-Presets „Werksstandard“ mit Bestätigung und Rückgängig; Session stellt Fill- und Stroke-Farb-Defaults wieder her. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **HL-Batch Tag-Combobox**: Vorschläge aus zuletzt genutzten Tags (`recent_tags.json`); editierbar; leer = ohne Tag; Abbrechen stoppt
- **Color-Presets Factory Confirm + Undo**: „Werksstandard“ mit Bestätigungsdialog; Button „Rückgängig“ stellt vorherige Felder wieder her

### Editor / Session / Tabs
- Autosave: optional **Backup `.ildbak` vor Überschreiben** (Toggle) + **max. Backups 1–10** (Rotation); gilt für Editor und Sidecar
- Session: letzte **Fill-Color** und **Stroke-Color** Defaults speichern/wiederherstellen

### Packaging / Docs
- Version **0.9.9** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Autosave-.ildbak, HL-Tag-Combobox, Factory-Confirm/Undo, Session Fill/Stroke (CLI + Qt)

---

## 0.9.8 — Autosave-Modal-Pause, HL-Tag, Preset-Factory, Session Opacity/Stroke

Nach 0.9.7: Autosave pausiert bei modalen Dialogen (Ctrl+S bleibt), Status blinkt kurz bei Autosave-Fehler; PDF-Suche→Highlight fragt optionalen Tag ab; Color-Presets „Alle zurücksetzen…“ + Werksstandard (Factory) in Einstellungen; Session stellt Ann.-Opacity und Stroke-Width wieder her. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **HL-Batch optionaler Tag**: Input-Dialog vor Anlegen; leerer Tag = ohne; Abbrechen stoppt den Batch
- **Color-Presets Reset-all + Factory**: Einstellungen „Alle zurücksetzen…“ (Bestätigung) und „Werksstandard“ (Factory-Defaults in Felder); API `factory_ann_color_presets()` / `ANN_COLOR_PRESET_FACTORY`

### Editor / Session / Tabs
- Autosave: **Pause bei Modal-Dialogen**; **Ctrl+S** unverändert; Status **kurz blinken** bei Fehler
- Session: letzte **Ann.-Opacity** und **Stroke-Width** speichern/wiederherstellen

### Packaging / Docs
- Version **0.9.8** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Autosave-Modal/Error-Blink, HL-Tag, Factory-Presets, Session Opacity/Stroke (CLI + Qt)

---

## 0.9.7 — Autosave-Intervall/Status, HL-Batch alle Seiten, Preset JSON, Session-Werkzeug

Nach 0.9.6: Autosave-Intervall fest auf 15/30/60/120 s wählbar, Statuszeile zeigt nach Autosave „Gespeichert HH:MM:SS“; PDF-Suche→Highlight auch für alle Seiten (Checkbox / Menü) mit einem Undo-Stack-Eintrag; Color-Presets Export/Import als JSON (`ildcolors-v1`); Session stellt das zuletzt genutzte Annotations-Werkzeug wieder her. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **PDF-Suche → Highlight-Batch alle Seiten**: Checkbox „alle Seiten“ + Menü „Treffer als Highlight (alle Seiten)“; Commit + **ein Undo** für den gesamten Batch
- **Color-Presets Export/Import**: JSON-Schema `ildcolors-v1` (Einstellungen: Export… / Import…, optional Merge)

### Editor / Session / Tabs
- Einstellungen: **Autosave-Intervall** als Auswahl 15 / 30 / 60 / 120 s
- Autosave-Status: **„Gespeichert HH:MM:SS“** in der Statusleiste
- Session: **Ann.-Werkzeug** (`ann_tool`) speichern/wiederherstellen

### Packaging / Docs
- Version **0.9.7** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Autosave-Intervalle+Status, HL-Batch alle Seiten+Undo, ildcolors-v1, Session-Werkzeug (CLI + Qt)

---

## 0.9.6 — Tab Dirty/Autosave, PDF-Suche→Highlight, Preset Save/Reset, Session-Suche

Nach 0.9.5: Dokument-Tabs zeigen `*` bei ungespeicherten Änderungen (inkl. Custom-Label/Pin); Autosave Ein/Aus in Einstellungen; PDF-Suchtreffer der aktuellen Seite als Highlight-Annotationen (Batch, ein Undo); Color-Presets per Rechtsklick speichern oder auf Standard zurücksetzen (User-Presets auch in Settings); Session stellt Suchfilter Aa/Wort/Regex wieder her. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **PDF-Suche → Highlight-Batch**: Button `HL` / Menü „Treffer als Highlight (Seite)“ legt Annotationen für alle Treffer der aktuellen Seite an (Commit + Undo)
- **Color-Presets Rechtsklick**: Kontextmenü „Preset speichern…“ / „Preset zurücksetzen“; 6 User-Presets in Einstellungen editierbar + Reset

### Editor / Session / Tabs
- Dokument-Tabs: **Dirty-Indikator (*)** inkl. Custom-Label und Pin; Tooltip „Ungespeicherte Änderungen“
- Einstellungen: **Autosave aktiv** Toggle (Intervall nur wenn an)
- Session: **Suchfilter Aa / Wort / Regex** speichern/wiederherstellen

### Packaging / Docs
- Version **0.9.6** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Tab-Dirty+Autosave-Toggle, PDF-Suche→HL Batch, Preset Save/Reset, Session-Suche (CLI + Qt)

---

## 0.9.5 — Tab Originaltitel, PDF-JSON-Offset, Color-Presets, Session-Panels

Nach 0.9.4: Dokument-Tabs Kontextmenü „Originaltitel“ setzt das Anzeige-Label zurück (Tooltip zeigt immer den vollen Pfad), PDF-Suchtreffer als JSON (`ildsearch-v1` kompatibel mit Seite/Offset/Snippet), Color-Presets Quick-Bar mit 6 Farben für Stroke/Fill inkl. Undo, Session stellt Panel-Sichtbarkeit Thumb/Ann/Bookmark wieder her. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **PDF-Suche Treffer-Export JSON**: `ildsearch-v1` mit Feldern Seite, Offset, Snippet (`fields` + Hits)
- **Color-Presets Quick-Bar**: 6 Farben — Auswahl: Klick=Strich · Shift=Füllung (Commit + Undo); ohne Auswahl: Highlight/Stift/Notiz

### Editor / Session / Tabs
- Dokument-Tabs: Kontext **„Originaltitel“** → Label zurücksetzen; Tooltip = voller Pfad
- Session: **Panel-Sichtbarkeit** Thumbnails / Annotationsliste / Lesezeichen speichern/wiederherstellen

### Packaging / Docs
- Version **0.9.5** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Tab-Originaltitel+Tooltip, PDF-JSON Offset, Color-Presets Undo, Session-Panels (CLI + Qt)

---

## 0.9.4 — Tab-Rename, PDF-CSV-Offset, Stroke-Color, Session-Theme

Nach 0.9.3: Dokument-Tabs per Doppelklick umbenennen (Anzeige-Label, nicht Dateiname) mit Persistenz in der Session, PDF-Suchtreffer als CSV mit Seite/Offset/Snippet, Stroke-Color-Picker getrennt von Fill (Commit + Undo), Session stellt Theme (dark/light) und aktiven Tab-Index wieder her. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **PDF-Suche Treffer-Export CSV**: Spalten Seite, Offset (Zeichen im Seiten-Volltext), Snippet
- **Stroke-Color Picker**: Toolbar „Strich…“ setzt Strichfarbe getrennt von „Füllung…“; Sidecar + Undo in einem Schritt

### Editor / Session / Tabs
- Dokument-Tabs: **Doppelklick / Kontext „Umbenennen…“** → Anzeige-Label; `label` in `session.json`
- Session: **Theme** (`dark`/`light`) + **aktiver Tab-Index** speichern/wiederherstellen

### Packaging / Docs
- Version **0.9.4** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Tab-Rename+Session-Label, PDF-CSV Offset, Stroke-Color Undo, Session-Theme/Active (CLI + Qt)

---

## 0.9.3 — Tab Drag-Reorder, PDF-Regex, Fill-Color, Session-Splitter

Nach 0.9.2: Dokument-Tabs per Drag neu ordnen mit Persistenz der Reihenfolge in der Session, PDF-Suche mit Regex-Toggle (ungültige Ausdrücke → Fehlerstatus in der Statusleiste), Fill-Color-Picker für ausgewähltes Shape (Commit + Undo), Session stellt Sidebar/Viewer-Splitter-Größen wieder her. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **PDF-Suche Regex**: Suchleisten-Toggle `.*` für reguläre Ausdrücke; bei Syntaxfehler Statusleiste „Regex-Fehler: …“
- **Fill-Color Picker**: Toolbar „Füllung…“ setzt `fill_color` des ausgewählten Shapes; Sidecar + Undo in einem Schritt

### Editor / Session / Tabs
- Dokument-Tabs: **Drag-Reorder** (InternalMove) + API `reorder_documents`; Reihenfolge mit `order` in `session.json`
- Session: **Splitter-Größen** Sidebar/Viewer speichern/wiederherstellen (`splitter_sizes`)

### Packaging / Docs
- Version **0.9.3** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Tab-Reorder+Session-Order, PDF-Regex-Fehlerstatus, Fill-Color Undo, Session-Splitter (CLI + Qt)

---

## 0.9.2 — Tab-Pin, PDF Case/Wort-Suche, Stroke-Slider, Session-Zoom

Nach 0.9.1: Dokument-Tabs anheften/lösen (geschützt vor „Alle schließen“ + Pin-Indikator), PDF-Suche mit Case-sensitive- und Whole-word-Toggles in der Suchleiste, Stroke-Width-Slider für ausgewähltes Shape (Commit on release + Undo), Session stellt Zoom-Level pro Tab wieder her. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **PDF-Suche Aa / Wort**: Suchleisten-Toggles Case-sensitive und Whole-word für Highlight, Trefferliste und F3-Navigation
- **Stroke-Width Slider**: Toolbar-Slider 1–12 px steuert Strichstärke des ausgewählten Shapes; Undo erst beim Loslassen (Commit on release); Live-Vorschau während Drag

### Editor / Session / Tabs
- Dokument-Tabs: **Anheften / Lösen** (Rechtsklick); angeheftete Tabs bleiben bei **Alle schließen** offen; visueller Pin-Indikator 📌
- Session: **Zoom-Level** pro Tab speichern/wiederherstellen (neben Last-Page und Scroll; Vorrang vor Fit/Default-Zoom)

### Packaging / Docs
- Version **0.9.2** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Tab-Pin, PDF Case/Wort, Stroke Commit-on-Release, Session-Zoom (CLI + Qt)

---

## 0.9.1 — Tabs Alle/Links/Rechts, PDF-Trefferliste, Opacity-Undo, Session Last-Page/Scroll

Nach 0.9.0: Dokument-Tabs Kontextmenü „Alle / Links / Rechts schließen“, PDF-Suche mit klickbarer Trefferliste (Seite + Snippet), Opacity-Slider mit Undo erst beim Loslassen (Commit on release), Session stellt Last-Page und Scroll-Position pro Tab wieder her. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **PDF-Trefferliste**: Sidebar zeigt Seite + Snippet je Texttreffer; Klick springt zur Seite und aktiviert den Treffer
- **Opacity-Slider Undo**: Slider-Drag schreibt eine Undo-Stufe erst beim Loslassen (Commit on release); Live-Vorschau während des Ziehens

### Editor / Session / Tabs
- Dokument-Tabs Kontextmenü: **Alle schließen**, **Links schließen**, **Rechts schließen** (zusätzlich Schließen / Andere)
- Session: **Last-Page** + **Scroll-Position** pro Tab speichern/wiederherstellen (Tab-Wechsel und Start)

### Packaging / Docs
- Version **0.9.1** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Tab Alle/Links/Rechts, PDF-Trefferliste, Opacity Commit-on-Release, Session Scroll/Page (CLI + Qt)

---

## 0.9.0 — Tab Mittelklick/Andere schließen, PDF-Suche F3, Opacity-Slider, Session-Toggles

Nach 0.8.9: Dokument-Tabs per Mittelklick und Kontextmenü „Andere schließen“, PDF-Suchtreffer auf der Seite highlighten mit F3/Shift+F3 (auch seitenübergreifend), Opacity-Slider steuert ausgewähltes Annotationsobjekt, getrennte Toggles für Fenstergeometrie und offene Tabs. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **PDF-Suche Highlight + F3**: Treffer auf der Seite markiert (aktiver Treffer orange); Menü Bearbeiten → Weitersuchen/Rückwärtssuchen (**F3** / **Shift+F3**); Navigation auch über Seitengrenzen
- **Opacity-Slider Auswahl**: Toolbar-Slider/Spin ändert bei Auswahl nur die ausgewählten Annotationen; ohne Auswahl weiterhin Standard-Deckkraft

### Editor / Session / Tabs
- Dokument-Tabs: **Mittelklick** schließt Tab; Rechtsklick → **Schließen** / **Andere schließen**
- Session-Toggles in Einstellungen: **Fenstergeometrie wiederherstellen** + **Offene Tabs wiederherstellen** (getrennt)

### Packaging / Docs
- Version **0.9.0** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Tab-Mittelklick/Andere, PDF-Suche F3/Highlight, Opacity-Auswahl, Session-Geometry-Toggle (CLI + Qt)

---

## 0.8.9 — Ann.-Gruppen Filter/JSON, Thumb Tab-Open, Overlay-Edges, Zeilen-Highlight

Nach 0.8.8: Ann.-Gruppen in der Liste filtern („nur diese Gruppe“) + Gruppe als JSON exportieren, Thumbnail-Auswahl als neues Dokument in neuem Tab öffnen, Seitennummer-Overlay Ausschluss erste/letzte Seite, Editor aktuelle Zeile hervorheben. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **Ann.-Gruppen Filter**: Rechtsklick auf Gruppenmitglied → „Nur diese Gruppe“; Aufheben-Button
- **Gruppe als JSON**: Export der Mitglieder + `ann_groups`-Meta (Schema v4)
- Thumbnail-**Batch als neues Dokument**: Kontextmenü → speichern und in neuem Tab öffnen
- **Seitennummer-Overlay Edges**: Toggle „Erste/letzte Seite ohne Overlay“ in Einstellungen

### Editor / Settings
- Editor-**Aktuelle Zeile hervorheben**: Toggle Ansicht/Einstellungen (ExtraSelection)

### Packaging / Docs
- Version **0.8.9** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Group-Filter/JSON, Thumb Tab-Open, Overlay-Edges, Current-Line-HL (CLI + Qt)

---

## 0.8.8 — Ann.-Gruppen Rename/Farbe, Thumb PDF-Extrakt, Overlay-Start, Indent-Guides

Nach 0.8.7: Temporäre Ann.-Gruppen umbenennen + Farbe der Sidecar-Markierung, Thumbnail-Auswahl als neues PDF extrahieren, Seitennummer-Overlay Start-Offset, Editor Einrückungs-Guides Toggle. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **Ann.-Gruppen Rename/Farbe**: Toolbar/Menü — Name + Farbe in Sidecar-Meta (`ann_groups`); farbige Markierung in der Annotationsliste
- Thumbnail-**Batch als PDF extrahieren**: Kontextmenü bei Auswahl → neues PDF (auch nicht zusammenhängend)
- **Seitennummer-Overlay Start**: Setting für erste Nummer ≠ 1 (`{page}`/`{pages}` berücksichtigen Offset)

### Editor / Settings
- Editor-**Einrückungs-Guides**: Toggle Ansicht/Einstellungen — vertikale Linien an Tab-Stops bei führender Einrückung

### Packaging / Docs
- Version **0.8.8** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Group-Rename/Farbe, Thumb Extract-PDF, Overlay-Start, Indent-Guides (CLI + Qt)

---

## 0.8.7 — Ann.-Gruppen Select/Lock, Thumb Batch-Drehen, Overlay-Format, Mehrzeilen-Indent

Nach 0.8.6: Gruppenauswahl klickt alle Mitglieder + Lock-Toggle, Thumbnail-Batch-Drehen L/R mit Undo, Seitennummer-Overlay Format-String (`{page}`/`{pages}`), Editor Tab/Shift+Tab für Mehrzeilen. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **Gruppen-Auswahl**: Klick auf ein Gruppenmitglied wählt alle Mitglieder; Shift+Klick toggelt die ganze Gruppe
- **Gruppen-Sperre**: Toolbar/Menü Toggle — gesperrte Mitglieder nicht verschiebbar (`locked` im Sidecar)
- Thumbnail-**Batch-Drehen** L/R bei Mehrfachauswahl (Undo Ctrl+Z je Seite)
- **Seitennummer-Overlay Format**: Setting mit Platzhaltern `{page}` / `{pages}` (Aliase `{n}` / `{total}`, optional `{label}`)

### Editor / Settings
- Editor-**Mehrzeilen-Indent**: Tab/Shift+Tab rückt Auswahl (ein-/mehrzeilig) ein/aus; ohne Auswahl Tab einfügen (Soft-Tabs)

### Packaging / Docs
- Version **0.8.7** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Group-Select/Lock, Thumb Batch-Rotate, Overlay-Format, Mehrzeilen-Indent (CLI + Qt)

---

## 0.8.6 — Ann.-Gruppieren, Thumb Multi-Select, Overlay-Position, Soft-Tabs

Nach 0.8.5: Annotation-Auswahl gruppieren/entgruppieren (temporäre `group_id` im Sidecar), Thumbnail-Mehrfachauswahl mit Batch-Löschen/Duplizieren, Seitennummer-Overlay-Position, Soft-Tabs vs. echte Tabs. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **Gruppieren / Entgruppieren**: Mehrfachauswahl (≥2) erhält gemeinsame temporäre `group_id` im Sidecar; Toolbar + Menü Bearbeiten → Auswahl ausrichten
- Thumbnail-**Mehrfachauswahl**: **Shift+Klick**; Kontextmenü **Batch-Duplizieren** / **Batch-Löschen** (Undo Ctrl+Z)
- **Seitennummer-Overlay Position**: unten-mitte / oben-mitte in Einstellungen

### Editor / Settings
- Editor-**Soft-Tabs**: Toggle Soft-Tabs (Leerzeichen) vs. echte Tabulatorzeichen in Einstellungen

### Packaging / Docs
- Version **0.8.6** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Group/Ungroup, Thumb-Batch, Overlay-Position, Soft-Tabs (CLI + Qt)

---

## 0.8.5 — Ann.-Align/Distribute V, Thumb-Duplizieren, Overlay-Font, Tab-Breite

Nach 0.8.4: Annotation-Auswahl vertikal ausrichten und verteilen, Thumbnail-Seiten duplizieren mit Undo, Seitennummer-Overlay-Schriftgröße, Editor-Tab-Breite. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **Auswahl ausrichten**: oben / mittig / unten (≥2); Toolbar + Menü Bearbeiten
- **Vertikal verteilen**: gleichmäßige Abstände (≥3); Toolbar + Menü
- Thumbnail-**Kontextmenü**: **Seite duplizieren** mit Undo (Ctrl+Z)
- **Seitennummer-Overlay Schriftgröße**: Setting in Einstellungen (8–36 pt)

### Editor / Settings
- Editor-**Tab-Breite**: 2 / 4 / 8 Zeichen in Einstellungen

### Packaging / Docs
- Version **0.8.5** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Align/Distribute V, Thumb-Duplicate+Undo, Overlay-Font, Tab-Breite (CLI + Qt)

---

## 0.8.4 — Ann.-Align/Distribute, Thumb-Löschen, Overlay-Opacity, Wortumbruch

Nach 0.8.3: Annotation-Auswahl ausrichten und horizontal verteilen, Thumbnail-Seiten löschen mit Bestätigung und Undo, Seitennummer-Overlay-Deckkraft, Wortumbruch-Toggle persistiert. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **Auswahl ausrichten**: links / mittig / rechts (≥2); Toolbar + Menü Bearbeiten
- **Horizontal verteilen**: gleichmäßige Abstände (≥3); Toolbar + Menü
- Thumbnail-**Kontextmenü**: **Seite löschen…** mit Bestätigung und Undo (Ctrl+Z)
- **Seitennummer-Overlay Deckkraft**: Setting / Toolbar „Nr α“ / Einstellungen

### Editor / Settings
- Editor-**Wortumbruch**: Ansicht-Toggle speichert in Settings (Round-Trip wie Zeilennummern)

### Packaging / Docs
- Version **0.8.4** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Align/Distribute, Thumb-Delete+Undo, Overlay-Opacity, Wortumbruch-Persistenz (CLI + Qt)

---

## 0.8.3 — Ann.-Multi-Select, Thumb-Drehen, Seitennummer-Overlay, Zeilennummern

Nach 0.8.2: Annotation-Mehrfachauswahl mit gemeinsamer Verschiebung, Thumbnail-Drehen mit Undo, Seitennummer-Overlay in Einstellungen, Zeilennummern-Toggle persistiert. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **Annotation Mehrfachauswahl**: **Shift+Klick** schaltet Auswahl um; Drag verschiebt alle ausgewählten gemeinsam
- Thumbnail-**Kontextmenü**: **Drehen 90° links/rechts** (Undo Ctrl+Z)
- **Seitennummer-Overlay**: Toggle in Einstellungen / Ansicht / Toolbar „Nr.“ (persistiert)

### Editor / Settings
- Editor-**Zeilennummern**: Ansicht-Toggle speichert in Settings und bleibt nach Neustart

### Packaging / Docs
- Version **0.8.3** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Ann.-Multi-Select/Move, Thumb-Rotate+Undo, Seitennummer-Overlay, Zeilennummern-Persistenz (CLI + Qt)

---

## 0.8.2 — Thumbnail-Undo, Fit-Zoom, Ann.-Ctrl+D, Standard-Zoom

Nach 0.8.1: Thumbnail-Seitenreihenfolge rückgängig, Fit-Zoom-Shortcuts/Modus, Annotation per Ctrl+D, Standard-Zoom speichern. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- Thumbnail-**Drag-Reorder**: **Undo** (Ctrl+Z) stellt Seitenreihenfolge + Ann.-Remap wieder her
- **Fit-Width** (Ctrl+9) / **Fit-Page** (Ctrl+0): Menü-/Toolbar-Tooltips; als **Standard-Zoom-Modus** wählbar
- **Annotation duplizieren**: im PDF auch **Ctrl+D** (Editor weiterhin Zeile duplizieren); Ctrl+Shift+D bleibt

### Editor / Settings
- Einstellungen: **Standard-Zoom-Modus** Prozent / Fit-Width / Fit-Page + **Aktuell speichern**
- Ansicht: **Aktuellen Zoom als Standard speichern** (Ctrl+Shift+0)

### Packaging / Docs
- Version **0.8.2** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Thumbnail-Undo, Fit-Zoom-Modus, Ann.-Ctrl+D, Standard-Zoom speichern (CLI + Qt)

---

## 0.8.1 — Bookmark-Drag, Tag-Cloud-Sort, Recent-Fehlend, Zoom-%

Nach 0.8.0: Bookmark-Liste umsortieren, Tag-Cloud sortieren, fehlende Recent-Dateien handhaben, Zoom in der Statusleiste. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- Tag-Cloud **Sortierung**: Toggle **Häufigkeit** / **A–Z** (persistiert)
- Statusleiste: **Zoom n%** bei aktiver PDF-Ansicht

### Editor / Settings
- Editor-**Lesezeichen-Liste**: **Drag-Reorder** + Persistenz als Sidecar `*.ildbm.json` (Reihenfolge in ildbm-v1)
- **Zuletzt geöffnet**: fehlende Dateien **grau** („fehlt“); Rechtsklick **Entfernen**

### Packaging / Docs
- Version **0.8.1** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Bookmark-Reorder/Sidecar, Tag-Cloud-Sort, Recent fehlt+Entfernen, Zoom-% (CLI + Qt)

---

## 0.8.0 — Bookmark-Export, Tag-Cloud Kontext, Status, Recent-Settings

Nach 0.7.9: Editor-Lesezeichen teilen, Tag-Cloud-Kontextmenü erweitern, Statusleiste und Recent-Liste verfeinern. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- Tag-Cloud **Rechtsklick**: **filtern**, **Farbe ändern** (alle Ann. mit Tag), umbenennen
- Statusleiste: **Seiten-/Zeileninfo** beim PDF↔Text-Wechsel robuster (`Zeile x/y` im Editor)

### Editor / Settings
- Editor-**Lesezeichen Export/Import** JSON (`ildbm-v1`) — Menü Bearbeiten
- **Zuletzt geöffnet**: **Max-Anzahl** (3–50) + **Liste leeren** in Einstellungen (Menü-Clear bleibt)

### Packaging / Docs
- Version **0.8.0** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Bookmark ildbm-v1, Tag-Cloud Kontext, Status PDF↔Text, Recent max/Clear (CLI + Qt)

---

## 0.7.9 — Such-Export, Ann.-Filter-Presets, Bracket-Auto-Close

Nach 0.7.8: Suchergebnisse exportieren, Annotations-Filter merken und Editor-Klammern verfeinern. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **Suchergebnis-Export**: Trefferliste als **CSV** / **JSON** (`ildsearch-v1`) — Sidebar-Buttons + Menü Bearbeiten
- Ann.-**Filter-Presets**: aktuelle Filter (Typ/Farbe/Tags/Seite/Suche/Regex) **speichern / laden / löschen**

### Editor / Settings
- **Bracket-Auto-Close** Toggle in Einstellungen (Standard an): `()[]{}` und Anführungszeichen beim Tippen

### Packaging / Docs
- Version **0.7.9** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Such-Export CSV/JSON, Ann.-Filter-Presets, Bracket-Auto-Close (CLI + Qt)

---

## 0.7.8 — Dry-Run-TXT, Ann.-Tooltip, Blink-Hinweis, Merge-Diff-Länge

Nach 0.7.7: Zip-Dry-Run, Ann.-Liste, Debounce-Hinweis und Merge-Diff verfeinern. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- Ann.-**Liste**: bei Ellipsis-Kürzung **Tooltip mit vollem Text**
- Ann.-**Merge-Diff**: **max. Zeichenlänge** je Seite in Einstellungen (12–64)

### Editor / Settings
- Vorlagen-Zip-Import Dry-Run: **Konfliktliste als TXT** exportieren
- Status-Blink **aus**: trotzdem **einmaliger Status-Hinweis** ohne Blink

### Packaging / Docs
- Version **0.7.8** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Dry-Run-TXT, Ann.-Tooltip, Blink-Hinweis, Merge-Diff-Länge (CLI + Qt)

---

## 0.7.7 — Status-Blink Settings, Merge-Tags/Farbe, Zip-Dry-Run, Ann.-Ellipsis

Nach 0.7.6: Dirty-UX, Merge-Diff, Zip-Import und Ann.-Liste verfeinern. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- Ann.-**Merge-Vorschau**: Diff-Kurztext zeigt zusätzlich **Tags** und **Farbe**
- Ann.-**Liste**: gekürzter Text nutzt **Snippet-Ellipsis-Style** («…» / …)

### Editor / Settings
- Pending Sidecar-Debounce: **Status-Blink** Dauer/Intensität in Einstellungen (**kurz** / **aus**)
- Vorlagen-Zip-Import: **Dry-Run-Liste** was überschrieben würde (im Konflikt-Dialog)

### Packaging / Docs
- Version **0.7.7** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Status-Blink Settings, Merge-Tags/Farbe, Zip-Dry-Run, Ann.-Ellipsis (CLI + Qt)

---

## 0.7.6 — Snippet-Ellipsis, Zip-Konflikt, Merge-Diff, Debounce-Blink

Nach 0.7.5: Suche, Vorlagen-Import, Merge-Vorschau und Dirty-UX verfeinern. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **Snippet-Ellipsis-Style** in Einstellungen: Match-Markierung `«…»` (Guillemets) oder `…` (Ellipsis)
- Ann.-**Merge-Vorschau**: Diff-Kurztext der beiden Annotationen (Ähnlichkeit + Textausschnitte)

### Editor / Settings
- Vorlagen-Zip-Import: **Konflikt-Dialog** (Überschreiben / Überspringen / Abbrechen)
- Pending Sidecar-Debounce: kurzer **Statusleisten-Blink** + Message „Speichern ausstehend…“

### Packaging / Docs
- Version **0.7.6** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Ellipsis-Style, Zip-Konflikt, Merge-Diff, Debounce-Blink (CLI + Qt)

---

## 0.7.5 — Snippet-Länge, Alle mergen/behalten, Vorlagen-Zip, Debounce-Tooltip

Nach 0.7.4: Suche, Merge-Vorschau, Vorlagen und Dirty-UX verfeinern. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **Treffer-Snippet-Länge** in Einstellungen (20–80 Zeichen Kontext um Match, Standard 40)
- Ann.-**Merge-Vorschau**: Buttons **Alle mergen** / **Alle behalten**

### Editor / Settings
- Nutzer-Vorlagen: **Export/Import Ordner als Zip** (`templates.json` + `*.ildtpl.md`)
- Pending Sidecar-Debounce: Tab-Tooltip **„Speichern ausstehend…“**

### Packaging / Docs
- Version **0.7.5** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Snippet-Länge-Settings, Alle mergen/behalten, Vorlagen-Zip, Debounce-Tooltip (CLI + Qt)

---

## 0.7.4 — Kontext-Snippets, Merge je Paar, Vorlagen-Drag, Dirty-Debounce

Nach 0.7.3: Trefferliste, Merge und Vorlagen/Dirty verfeinern. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **Trefferliste**: Kontext-Snippet mit Zeichen um den Match (`«…»`)
- Ann.-**Merge-Vorschau**: je Paar/Gruppe einzeln **mergen** oder **behalten**

### Editor / Settings
- Nutzer-Vorlagen: **Drag-Reihenfolge** speichern (Dialog + Menü)
- Dirty-Indikator am Tab/`*` auch bei **pending Sidecar-Debounce**

### Packaging / Docs
- Version **0.7.4** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Kontext-Snippet, Merge je Paar, Vorlagen-Reorder, Dirty-Debounce (CLI + Qt)

---

## 0.7.3 — Trefferliste, Vorlagen-Ordner, Merge-Vorschau, Ctrl+S-Flush

Nach 0.7.2: Schnellsuche und Merge/Save-UX verfeinern. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **Schnellsuche**: klickbare **Trefferliste** direkt unter der Suche (Index sync mit Weiter/Zurück)
- Ann.-**Merge-Vorschau**: Dialog mit Gruppenübersicht vor Apply (älteste behalten)

### Editor / Settings
- **Vorlagen-Ordner öffnen**: Spiegel unter `config/templates` im Explorer (Datei → Neu)
- Sidecar-Debounce: **Ctrl+S** flusht ausstehendes Speichern sofort

### Packaging / Docs
- Version **0.7.3** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Trefferliste-Klick, Vorlagen-Ordner, Merge-Vorschau-Dialog, Ctrl+S-Flush (CLI + Qt)

---

## 0.7.2 — Schnellsuche-Nav, Merge-Undo, Vorlagen-UI, Debounce-Settings

Nach 0.7.1: Navigation und Verwaltung verfeinern. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **Schnellsuche**: Trefferanzahl in der Sidebar; **Weiter/Zurück** navigiert über Doc-Treffer (Alle Docs / Alle PDFs) sowie Seite/Editor
- Ann.-**Merge-Undo**: Duplikate-Zusammenführen als benannter Undo-Stack-Eintrag („Duplikate zusammenführen“), Status/Hint

### Editor / Settings
- Nutzer-Vorlagen: **Umbenennen** / **Löschen** im Menü Datei → Neu → Meine Vorlagen
- Sidecar-Debounce-**Intervall** in Einstellungen (200–1000 ms, Default 400)

### Packaging / Docs
- Version **0.7.2** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: Treffer-Nav, Merge-Undo-Label, Vorlagen rename/delete, Debounce-Settings (CLI + Qt)

---

## 0.7.1 — PDF-Schnellsuche, Ann.-Duplikate, Vorlagen, Sidecar-Debounce

Nach Meilenstein 0.7.0: gezielte UX-/Performance-Härten. Stubs KI/Cloud/Stylus/3D bleiben Stubs.

### PDF / Suche / Annotationen
- **PDF-Schnellsuche** („Alle PDFs“): Volltext nur über geöffnete/gelistete PDFs; eine PDF-Öffnung pro Datei; Snippets um Treffer; Sprung + Highlight
- Volltext „Alle Docs“: casefold, bessere Snippets, bis 100 Treffer in der Liste
- Annotation-**Duplikate** (gleiche Seite+BBox±2px, gleicher Typ) finden und optional zusammenführen (Text/Tags mergen, älteste behalten)

### Editor / Performance
- **Als Vorlage speichern** aus aktuellem Dokument; Menü Datei → Neu → Meine Vorlagen
- Sidecar-Save **Debounce** (400 ms); Force-Save / Flush bei PDF-Wechsel, Close, Autosave

### Packaging / Docs
- Version **0.7.1** (App / `ild_pdf` / ISS / Smoke / Docs)
- Smoke: PDF-Suche, Duplikat-Merge, Nutzer-Vorlagen, Sidecar-Debounce (CLI + Qt wo sinnvoll)

---

## 0.7.0 — Release-Konsolidierung (0.6.0 → 0.7.0)

Meilenstein: alle 0.6.x-Inkremente gebündelt, Version einheitlich **0.7.0**, Smoke um ausgewählte 0.6.x-Pfade erweitert, kleine Review-Fixes. Stubs KI/Cloud/Stylus/3D bleiben Stubs (keine Fake-Features).

### PDF / Annotationen
- Selection→**Copy**/Notiz/Highlight+Notiz; Tag-**Autocomplete**/Multi-Select/**Cloud**/Rename (+ Undo, Confirm, Schwelle)
- Annotation-**Tag-Cloud** (Filter-Klick, Rechtsklick umbenennen); Sidecar-Tags unverändert

### Editor / Session / UX
- Session-**Tab-Order** Drag; **Andere Tabs schließen**; **Doc-Split** H/V (PDF+Editor, Panel-Session)
- **Sync-Scroll** optional + je Session; Dirty-Tabs Liste / Speichern / Alle speichern (Fortschritt, Abbrechen, **Fehlerliste**)
- Erste-Schritte-**Wizard** (0.6-Highlights, skip-once, dauerhaft, Reset); F1 Shortcuts + 0.6.8-Hinweise
- Sync: `-SkipStart`, Exit-Codes 0/1/2; Installer Desktopicon-Docs

### Packaging / Docs
- Inno Setup / Build / INFO / FEATURES / README auf **0.7.0**
- Sync: `scripts/sync-ild.ps1` (Repo) bzw. Store `docs/sync-ild.ps1`
- Smoke: open / annotate / export / license + ausgewählte 0.6.x-Pfade (CLI + offscreen Qt)

### Review-Fixes (0.7.0)
- Versionsstrings App / `ild_pdf` / ISS / Smoke / Docs vereinheitlicht
- CHANGELOG 0.6.1–0.6.9 zu Kurz-Tabelle verdichtet (wie zuvor 0.5.x)
- `ild_pdf/README.md` und `installer/build-installer.ps1` Versionshinweise auf aktuelle Release gebracht

---

## 0.6.0 — Release-Konsolidierung (0.5.0 → 0.6.0)

Meilenstein: alle 0.5.x-Inkremente gebündelt, Version einheitlich **0.6.0**, Smoke um ausgewählte 0.5.x-Pfade erweitert, kleine Review-Fixes. Stubs KI/Cloud/Stylus/3D bleiben Stubs (keine Fake-Features).

### PDF / Annotationen / OCR
- **Batch-OCR** gesamtes PDF; Annotation-**Tags**; **PDF bereinigen**; Selection→Highlight; Ann.-**Regex**
- Kommentar-**Bericht**; Farbe Palette-Zyklus; Seite löschen **Undo**; Annotation-**Gruppen**
- Seiten-**Historie**; Ann.-Export Tags/Gruppen; **Seiten-Favoriten** (Sidebar, Drag, JSON `ildfav-v1`)
- Ann.-Batch-**Farbe**/Opacity; Opacity Force-Save + **Toolbar-Slider**

### Editor / UX
- Projekt-**Workspace**; Dateien vergleichen; **Export-Profil**; Editor-**Minimap**; Soft-Hyphen/NBSP
- Startup-Deps-Check; Encoding **Auto**; Quiet Splash; Wortlisten-**Rechtschreibung**; Privacy-About
- Zeilenfavoriten (+ **Labels**); Crash-Report **ZIP** (+ optional Screenshot); **Erste-Schritte**-Wizard

### Packaging / Docs
- Inno Setup / Build / INFO / FEATURES / README auf **0.6.0**
- Sync: `scripts/sync-ild.ps1` (Repo) bzw. Store `docs/sync-ild.ps1`
- Smoke: open / annotate / export / license + ausgewählte 0.5.x-Pfade (CLI + offscreen Qt)

### Review-Fixes (0.6.0)
- Versionsstrings App / `ild_pdf` / ISS / Smoke / Docs vereinheitlicht
- CHANGELOG 0.5.1–0.5.9 zu Kurz-Tabelle verdichtet (wie zuvor 0.4.x)
- `ild_pdf/README.md` und `installer/build-installer.ps1` Versionshinweise auf aktuelle Release gebracht

### 0.6.x-Inkremente (Kurz)

| Ver. | Kern |
|------|------|
| **0.6.1** | Selection-Copy, Tag-Autocomplete, Session-Order, Installer-Docs |
| **0.6.2** | Selection→Notiz, Tag-Multi-Select, Close-Others, Sync-Exit |
| **0.6.3** | Highlight+Notiz, Tag-Cloud, Doc-Split, Unsaved-Count |
| **0.6.4** | Tag-Cloud-Filter, Sync-Scroll, Dirty-Tabs, Shortcuts |
| **0.6.5** | Tag-Rename, Vertikal-Split, Dirty-Save, Wizard-0.6 |
| **0.6.6** | Tag-Rename-Undo, Split-Settings, Alle-Speichern, Wizard-Skip |
| **0.6.7** | Tag-Undo-Label, Split-PDF+Editor, Save-Progress, Wizard-Dauerhaft |
| **0.6.8** | Split-Panel-Session, Save-Abbrechen, Wizard-Reset, Tag-Confirm |
| **0.6.9** | Sync-Scroll-Session, Tag-Schwelle, Save-Fehlerliste, F1-0.6.8 |

→ zusammengeführt in **0.7.0**.

---

## 0.5.0 — Release-Konsolidierung (0.4.0 → 0.5.0)

Meilenstein: alle 0.4.x-Inkremente gebündelt, Version einheitlich **0.5.0**, Smoke um ausgewählte 0.4.x-Pfade erweitert, kleine Review-Fixes. Stubs KI/Cloud/Stylus/3D bleiben Stubs (keine Fake-Features).

### PDF / Annotationen
- Native **Link-Annotationen**; **Stempel-Rotation** 90°; Outline-Goto gehärtet (objgen)
- Annotation **Copy/Paste**, **Lock**, CropBox-/**Druckermarken**-Overlay
- Sidecar **Schema v4** (`ildann-v4`) Export + Import-Validierung; **Notizfarbe** unabhängig
- Farben-Chips-Filter; Zeitstempel in Liste; Filter **nur aktuelle Seite**
- **Seitenlabels** (römisch/arabisch); Seitenbild→Editor; **Gehe zu Seite**
- Zwei-Seiten-Ansicht (**Spread**); **Continuous Scroll**

### Editor / UX
- Encoding UTF-8/Latin-1; Multi-Drop; Case gesamte Datei; Snippets; Templates
- Zeilen sortieren; Settings-Reset; Trim trailing/paste; Bracket-Match
- Zwischenablage-Verlauf; Tab duplizieren; Undo-Hint; Arbeitsverzeichnis öffnen
- Cheat-Sheet als PDF; About Feature-Kurzliste + FEATURES.md
- Flatten/Bake Progress; Batch Abbrechen

### Packaging / Docs
- Inno Setup / Build / INFO / FEATURES / README auf **0.5.0**
- Sync: `scripts/sync-ild.ps1` (Repo) bzw. Store `docs/sync-ild.ps1`
- Smoke: open / annotate / export / license + ausgewählte 0.4.x-Pfade (CLI + offscreen Qt)

### Review-Fixes (0.5.0)
- Versionsstrings App / `ild_pdf` / ISS / Smoke / Docs vereinheitlicht
- CHANGELOG 0.4.1–0.4.9 zu Kurz-Tabelle verdichtet (wie zuvor 0.3.x)
- Doppelte Leerzeile im Changelog-Abschnitt 0.4.7 entfernt (Kompaktierung)

### 0.5.x-Inkremente (Kurz)

| Ver. | Kern |
|------|------|
| **0.5.1** | Batch-OCR, Ann.-Tags, Projekt-Workspace, PDF bereinigen |
| **0.5.2** | Selection→Highlight, Ann.-Regex, Text-Diff, Export-Profil |
| **0.5.3** | Kommentar-Bericht, Farbe-Zyklus, Minimap, About-Keygen |
| **0.5.4** | Seiten-Löschen-Undo, Ann.-Gruppen, Soft-Hyphen/NBSP, Startup-Deps |
| **0.5.5** | Seiten-Historie-UI, Ann.-Export Tags/Gruppen, Encoding-Auto, Quiet Splash |
| **0.5.6** | Seiten-Favoriten, Ann.-Batch-Farbe, Wortlisten-Rechtschreibung, Privacy-About |
| **0.5.7** | Favoriten-Sidebar, Ann.-Opacity-Batch, Zeilenfavoriten, Crash-ZIP |
| **0.5.8** | Favoriten-Drag, Opacity-Force-Save, Zeilenfavoriten-Liste, Crash-Screenshot |
| **0.5.9** | Favoriten JSON, Opacity-Slider, Zeilenfavoriten-Labels, Erste-Schritte-Wizard |

→ zusammengeführt in **0.6.0**.

---

## 0.4.0 — Release-Konsolidierung (0.3.0 → 0.4.0)

Meilenstein: alle 0.3.x-Inkremente gebündelt, Version einheitlich **0.4.0**, Smoke um ausgewählte 0.3.x-Pfade erweitert, kleine Review-Fixes. Stubs KI/Cloud/Stylus/3D bleiben Stubs (keine Fake-Features).

### PDF / Seiten
- AcroForm-Felder lesen/schreiben; Stempel-Bibliothek GENEHMIGT/ENTWURF/VERTRAULICH
- Anhänge auflisten/extrahieren; Seiten als Einzel-PDFs; Text → Editor (Seite/gesamt)
- Raster-Export DPI 72/150/300; Thumbnail-Größe klein/normal/groß; Lazy-Load
- Fit-Width Ctrl+9 / **Fit-Height Ctrl+8**; Präsentationsmodus F5
- Seitengröße Statusleiste mm/inch; Fenster-Geometrie speichern

### Annotationen
- Layer ein-/ausblenden; Flatten/Bake → PDF; Duplizieren; Select-All Seite
- Sidebar: Typ-Filter, Textsuche, Gruppierung nach Seite, **Statistik je Typ**
- Farben-Favoriten (3 Presets); CSV-Export; Sidecar v3

### Editor / UX
- Soft-Wrap; Markdown-Vorschau; Sonderzeichen; Gehe zu Zeile; Zeile duplizieren/verschieben
- Block Tab/Shift+Tab; Kommentar Ctrl+/; Backup `.bak`; Overwrite-Schutz Export
- Session-Restore Toggle; Tray-Minimize + Tray-Tooltip mit Version
- Tab schließen (dirty); Lizenz Resttage/Ablauf klar; Zuletzt verwendete Ordner

### Packaging / Docs
- Inno Setup / Build / INFO / FEATURES / README auf **0.4.0**
- Sync: `scripts/sync-ild.ps1` (Repo) bzw. Store `docs/sync-ild.ps1`
- Smoke: open / annotate / export / license + ausgewählte 0.3.x-Pfade (CLI + offscreen Qt)

### Review-Fixes (0.4.0)
- `installer/installer-hinweis.txt` Version auf aktuelle Release gebracht (war 0.3.3)
- Versionsstrings App / `ild_pdf` / ISS / Smoke / Docs vereinheitlicht
- CHANGELOG 0.3.1–0.3.9 zu Kurz-Tabelle verdichtet (wie zuvor 0.2.x)

### 0.4.x-Inkremente (Kurz)

| Ver. | Kern |
|------|------|
| **0.4.1** | PDF-Links, Stempel-Rotation, Encoding, Multi-Drop |
| **0.4.2** | Outline-Goto, Ann.-Copy/Paste, Case-Datei, Progress |
| **0.4.3** | CropBox-Overlay, Ann.-Lock, Snippets, Templates |
| **0.4.4** | Druckermarken, Ann.-Schema v4, Zeilen sortieren, Settings-Reset |
| **0.4.5** | Seitenbild→Editor, Ann.-Import-Validierung, Trim, Toolbar |
| **0.4.6** | Goto Page, Ann.-Farben-Filter, Duplikat-Tab, Undo-Hint |
| **0.4.7** | Spread, Notizfarbe, Paste-Trim, Cheat-Sheet-PDF |
| **0.4.8** | Continuous Scroll, Ann.-Zeitstempel, Bracket-Match, Arbeitsverzeichnis |
| **0.4.9** | Seitenlabels, Ann.-Seitenfilter, Clipboard-Verlauf, About-Features |

→ zusammengeführt in **0.5.0**.

---

## 0.3.0 — Release-Meilenstein

Fokus: Konsolidierung 0.2.x → 0.3.0 (Versioning, Smoke, Docs, Review-Fixes Opacity/Ann-Suche/Toolbar/Indent/Sync). Inno gehärtet, Stubs ohne Fake-Features.

### 0.3.x-Inkremente (Kurz)

| Ver. | Kern |
|------|------|
| **0.3.1** | AcroForm, Stempel-Bibliothek, Tab schließen, Thumb Lazy-Load |
| **0.3.2** | Anhänge, Ann.-Layer, Markdown-Vorschau, recent_dirs |
| **0.3.3** | Einzel-PDFs, Ann.-Flatten, Soft-Wrap, Lizenz Resttage |
| **0.3.4** | PDF-Text→Editor, Ann.-Duplikat, Goto Line, Tray-Minimize |
| **0.3.5** | Seitengröße Status, Ann.-Gruppen, Zeile duplizieren, Backup .bak |
| **0.3.6** | Raster-DPI, Ann. Select-All, Kommentar Ctrl+/, Fenstergeometrie |
| **0.3.7** | Präsentation F5, Ann.-Favoriten, Block-Tab, Session-Toggle |
| **0.3.8** | Thumbnail-Größe, Ann.-CSV, Zeile verschieben, Overwrite-Schutz |
| **0.3.9** | Fit-Height, Ann.-Statistik, Sonderzeichen, Tray-Version |

→ zusammengeführt in **0.4.0**.

---

## 0.2.0 — Release-Meilenstein

Fokus: Release-Reife (Versioning, Installer, Smoke, Docs). Inno gehärtet, `open_document`-Fehler klar, Stubs ohne Fake-Features. README Quickstart + CHANGELOG eingeführt.

### 0.2.x-Inkremente (Kurz)

| Ver. | Kern |
|------|------|
| **0.2.1** | Sidecar/Fortschritt-UX, PDF-Open-Stabilität, Keygen-Pfad |
| **0.2.2** | Textsuche-Highlight, Farben-Picker, Export/Settings |
| **0.2.3** | Seiten→Bild, Ann. löschen, Statusleiste, Thumb-Reorder |
| **0.2.4** | Drehen, leere/duplizieren, Ann.-Liste, Suchhistorie |
| **0.2.5** | Outline edit, Ann.-JSON, Wortzählung, PDF-Kopie |
| **0.2.6** | Seitenbereich, Ann.-Filter, Find/Replace, Lizenz-Warnung |
| **0.2.7** | Spiegeln, Ann.-Edit, Zeilennummern, Alles speichern |
| **0.2.8** | Graustufen, Ann.-Opacity, Case-Toggle, Splash/Titel |
| **0.2.9** | Nachtmodus, Ann.-Suche, Einrückung, Logordner |

→ zusammengeführt in **0.3.0**.

---

## 0.1.x — Kurzüberblick (→ 0.2.0)

| Version | Kern |
|---------|------|
| **0.1.9** | Metadaten-Editor, Seitengröße/Crop, Export-Qualität, i18n DE/EN, Update-Check, Redaction-UX |
| **0.1.8** | Redaction, PDF-Passwort, Bildkompression, Thumbnails, F1-Hilfe, Logging |
| **0.1.7** | Wasserzeichen, Seitennummern, PDF-Vergleich, Clipboard-Paste, Session-Restore, Zoom-Cache |
| **0.1.6** | Batch, PDF merge/split, Outline, Volltext, Einstellungen |
| **0.1.5** | Signatur, Theme, OCR-Tabellen, Autosave, Drag-Drop |
| **0.1.4** | Undo/Redo, Zoom/Fit, Recent, Druck, Lizenz-Statusleiste |
| **0.1.3** | Overlay-Editor, Formen/Lineal, Export HTML/DOCX/PDF, Installer-Basis |
| **0.1.2** | Stempel/Callout, Rahmen-Kette, OCR-Modi, Formulare, build-windows |
| **0.1.1** | Icon-Auflösung, Inno + Sync, Annotation speichern, Seiten neu anordnen |
| **0.1.0** | MVP: UI, PDF/Annotationen, OCR-Bridge, Formulare, Lizenz Trial/Keys, Keygen |

Vollständige Feature-Liste: [FEATURES.md](FEATURES.md).
