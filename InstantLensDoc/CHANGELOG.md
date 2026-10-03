# Changelog — InstantLens Doc

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
