# InstantLens Doc — Kurzinfo

| | |
|---|---|
| Produkt | InstantLens Doc |
| Version | **2.5.20** |
| Hersteller | Andreas Meyer |
| Kontakt | ame@sellerbach.de |
| PDF | pypdfium2 / PDFium |
| Code | `/workspace/InstantLensDoc/` → Ziel `D:\AI_Temp\InstantLensDoc` |
| Branch | `cursor/instantlensdoc-2108` · [PR #3](https://github.com/kickmetox/hello-github/pull/3) |
| GUI | Python 3.12 + PySide6 |

## Lizenz

- Trial: **28 Tage** ab Erststart  
- Keys: **32 Tage (30+2)**, Format `ILD1.…`  
- Neu anfordern: **ame@sellerbach.de**  
- Statusleiste: bei **<7 Tagen** Restlaufzeit prominent hervorgehoben  
- Resttage Statusleiste + About **konsistent** („noch X Tage“ / „noch 1 Tag“)  
- Ablaufdatum **TT.MM.JJJJ** in About + Status (+ Lizenzdialog)  
- Warnung **≤3 Tage** vor Ablauf: Banner (nicht modal); **Klick → About/Aktivierung**  
- Banner: **Icon** + **Dismiss** + **Schließen-X**; Persistenz **`dismiss_date`** (bis morgen)  
- Banner: **Esc** schließt; **AccessibleName** für Screenreader  
- Banner: **Fokus-Ring** sichtbar; **Enter** öffnet Aktivierung  
- Banner-Text **i18n** (DE); Farbe **Warnung** (gelb) vs. **abgelaufen** (rot)  
- Lizenz-Dialog: Resttage + Ablaufdatum klar  
- About: Version, **Lizenzstatus**, Kontakt, Changelog-Kurzliste; bei Trial/ungültig **Lizenz aktivieren…**; **Privacy: lokal, keine Telemetrie**

## Sync (eine Zeile, copy-ready)

`powershell -ExecutionPolicy Bypass -File "D:\AI_Temp\sync-ild.ps1"`

Skript: [sync-ild.ps1](scripts/sync-ild.ps1) — Branch `cursor/instantlensdoc-2108` (oder `-LocalPack` / Pack-Zip) nach `D:\AI_Temp\InstantLensDoc`, pip, Start. **Nutzer-Icon in `assets` wird nicht überschrieben.**

**FEATURES.md lokal sync:** Nach Sync liegt `FEATURES.md` lokal im App-Ordner (`D:\AI_Temp\InstantLensDoc\FEATURES.md`); About/Stubs öffnen diese lokale Datei — Version **2.5.20**.

Ohne Start: `-NoStart` (Alias `-SkipStart`). Exit-Codes: **0** OK · **1** allgemein · **2** Git-Fehler.

Fallback bei Git-Fehler:
```powershell
powershell -ExecutionPolicy Bypass -File "D:\AI_Temp\sync-ild.ps1" -LocalPack D:\AI_Temp\InstantLensDoc-pack.zip -SkipStart
```

## Start (manuell)

```bat
cd D:\AI_Temp\InstantLensDoc
pip install -r requirements.txt
run.bat
```

`run.bat` prüft Python ≥3.10 und Kern-Deps (PySide6, pypdfium2, pikepdf, Pillow) mit klaren DE-Meldungen; bei fehlenden Paketen optional `python -m pip install -r requirements.txt` (J/N) oder non-interactive **`run.bat --yes`** / **`-y`**. Hilfe: **`run.bat --help`** / **`-h`**. Env-Override: **`set ILD_PYTHON=C:\Pfad\zu\python.exe`** (höchste Priorität); bei ungültigem/leerem Pfad Warnung, dann `.venv` falls vorhanden, sonst Fallback **`py -3` → `python` → `python3`**. Gewählte Binary: **`gefunden: …`** inkl. kurz **`--version`**. Hinweis wenn lokale **`.venv`** vorhanden aber unvollständig. Fehlt Python: kurzer Download-Hinweis **Microsoft Store** / **python.org**.

Exit-Codes `run.bat`: **0** OK / Hilfe · **1** Python/Deps/pip-Fehler bzw. Installation abgelehnt (App-Exitcode ≠0 wird durchgereicht).

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

Installer: `.\installer\build-installer.ps1` (optional `-NoKeygen`)  
Desktop-Verknüpfung: optionale Checkbox (`desktopicon`, Standard an / `checkedonce`)

## Neu in 2.5.20

Post-Release-Polish nach **2.5.19**:

- **OCR-Region:** Open Fail-Path A11y (Tab/Ordner/Datei ohne Pfad · Open-Exception)
- **Farben-Themes:** Swatch Ctrl+Shift+C alle Hex · Hex-All Fail-A11y
- **Dokument-Tags:** Tag−/Clear Fail-Path A11y · Pfad-Copy Fail-A11y
- **Export-Presets:** Summary-Copy Fail-A11y (Zwischenablage)
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.19

Post-Release-Polish nach **2.5.18**:

- **OCR-Region:** Text-Copy Clip-Fail A11y (fehlt/Zwischenablage)
- **Farben-Themes:** Swatch Shift+←/→ ±2 · Hex-Copy Fail-A11y
- **Dokument-Tags:** Tags-Copy/Paste Fail-Path A11y
- **Export-Presets:** Pfad-Copy / Apply-fehlt Fail-A11y
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.18

Post-Release-Polish nach **2.5.17**:

- **OCR-Region:** Pfad-Copy Fail-Path A11y (fehlt/leer)
- **Farben-Themes:** Swatch PageUp/PageDown · Ctrl+C Hex
- **Dokument-Tags:** Menü Öffnen\tEnter · Fail-A11y
- **Export-Presets:** JSON Imp/Exp A11y · Ordner-fehlt Fail-A11y
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.17

Post-Release-Polish nach **2.5.16**:

- **OCR-Region:** Text-Copy Fail-Path A11y (Ergebnis fehlt/leer)
- **Farben-Themes:** Swatch-Ziffern 1–6 → Fokus
- **Dokument-Tags:** F5 → Datei öffnen · Menü Entfernen\tEntf
- **Export-Presets:** Duplizieren/Umbenennen/Löschen A11y Announce
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.16

Post-Release-Polish nach **2.5.15**:

- **OCR-Region:** Fail-Path A11y wenn Ergebnisdatei fehlt
- **Farben-Themes:** Swatch Home/End · RMB Mid/Dbl-Hinweise
- **Dokument-Tags:** Tag± Status/A11y Announce
- **Export-Presets:** Reorder A11y · Menü Anwenden⏎Enter
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.15

Post-Release-Polish nach **2.5.14**:

- **OCR-Region:** F5 → Ergebnisdatei öffnen (Status aktiv · Menü-Hinweise)
- **Farben-Themes:** Swatch-Tastatur Space/H→HL · P→Stift · N→Notiz · C→Hex · ←/→ · AccessibleName
- **Dokument-Tags:** F4 → Ordner öffnen (Recent · Status/A11y)
- **Export-Presets:** F4 → Zielordner öffnen
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.14

Post-Release-Polish nach **2.5.13**:

- **OCR-Region:** F4 → Ergebnis-Ordner öffnen (Status aktiv)
- **Farben-Themes:** Shift+Doppelklick → Stift · Ctrl+Doppelklick → Notiz
- **Dokument-Tags:** Ctrl+Shift+C Pfad kopieren (Recent)
- **Export-Presets:** Ctrl+Home/End an Anfang/Ende verschieben
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.13

Post-Release-Polish nach **2.5.12**:

- **OCR-Region:** Ctrl+C → Text kopieren · Ctrl+Shift+C → Pfad (Status aktiv)
- **Farben-Themes:** Doppelklick Swatch → Highlight-Farbe setzen
- **Dokument-Tags:** F3 Tag entfernen (Recent)
- **Export-Presets:** Ctrl+↑/↓ Reihenfolge verschieben
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.12

Post-Release-Polish nach **2.5.11**:

- **OCR-Region:** Enter → Ergebnis-Tab fokussieren
- **Farben-Themes:** Shift+Mittelklick → Stift · Ctrl+Mittelklick → Notiz
- **Dokument-Tags:** F2 Tag hinzufügen (Recent)
- **Export-Presets:** Ctrl+Enter Anwenden ohne Schließen
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.11

Post-Release-Polish nach **2.5.10**:

- **OCR-Region:** Esc / Menü → Status schließen
- **Farben-Themes:** Swatch-Mittelklick → Highlight-Farbe setzen
- **Dokument-Tags:** Shift+Entf/Backspace → Alle Tags entfernen
- **Export-Presets:** Ctrl+D Duplizieren
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.10

Post-Release-Polish nach **2.5.9**:

- **OCR-Region:** Status-Rechtsklick → Kontextmenü (Tab · Ordner · Pfad · Text · Datei)
- **Farben-Themes:** Swatch-RMB → als Highlight-/Stift-/Notizfarbe setzen
- **Dokument-Tags:** Ctrl+X Tags ausschneiden · „Alle Tags entfernen“
- **Export-Presets:** F2 Umbenennen
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.9

Post-Release-Polish nach **2.5.8**:

- **OCR-Region:** Status-Alt+Klick öffnet Ergebnisdatei · Tooltip mit Textvorschau
- **Farben-Themes:** Swatch-Klick kopiert einzelne Hex-Farbe
- **Dokument-Tags:** Ctrl+C / Ctrl+V Tags kopieren/einfügen (Recent)
- **Export-Presets:** Pfad kopieren (RMB · Ctrl+Shift+C)
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.8

Post-Release-Polish nach **2.5.7**:

- **OCR-Region:** Status-Shift+Klick kopiert Ergebnistext (ohne Fehlerabschnitt)
- **Farben-Themes:** Button „Hex kopieren“ (6 Farben in Zwischenablage)
- **Dokument-Tags:** Kontextmenü „Tags einfügen“ aus Zwischenablage
- **Export-Presets:** Summary kopieren (RMB · Ctrl+C)
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.7

Post-Release-Polish nach **2.5.6**:

- **OCR-Region:** Status-Mittelklick/Ctrl+Klick kopiert Ergebnis-Pfad (Tooltip mit Pfad)
- **Farben-Themes:** Combo-Tooltip mit 6 Hex-Farben · Custom-Zähler N/20
- **Dokument-Tags:** Kontextmenü „Tags kopieren“
- **Export-Presets:** Rechtsklick → Zielordner öffnen · Entf löschen
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.6

Post-Release-Polish nach **2.5.5**:

- **OCR-Region:** Status-Rechtsklick öffnet Ergebnis-Ordner (Linksklick → Tab)
- **Farben-Themes:** Custom duplizieren (Builtins geschützt)
- **Dokument-Tags:** Quick-Tag Sort A–Z ↔ Häufigkeit (persistiert)
- **Export-Presets:** Listen-Tooltip Summary · Apply A11y Announcement
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.5

Post-Release-Polish nach **2.5.4**:

- **OCR-Region:** Status-Klick fokussiert Ergebnis-Tab
- **Farben-Themes:** Custom umbenennen (Builtins geschützt)
- **Dokument-Tags:** Quick-Tag A–Z mit Doc-Anzahl (N)
- **Export-Presets:** ★ aktiv in Liste · Duplizieren
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.4

Post-Release-Polish nach **2.5.3**:

- **OCR-Region:** Wörter/Zeichen im Status · A11y Announcement nach Erfolg
- **Farben-Themes:** Custom löschen (Builtins geschützt) · ★ Default in Combo
- **Dokument-Tags:** Tag-Vorschläge (Recent/Index) · Quick-Tag-Filter Combo
- **Export-Presets:** Umbenennen · Doppelklick/Enter Anwenden
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.3

Post-Release-Polish nach **2.5.2**:

- **OCR-Region:** Tab-Titel Ellipsis + Tooltip voll · Fehlerabschnitt wie Batch-OCR
- **Farben-Themes:** Merge Kollision skip/rename (`_2`) · Import-Log
- **Dokument-Tags-Filter:** Esc → Fokus Liste · Trefferanzahl A11y
- **Export-Presets:** Live-Pfad-Vorschau · ungültige JSON-Einträge überspringen + zählen
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.2

Post-Release-Polish nach **2.5.1**:

- **OCR-Region:** Fortschritt (Schritte) · Ergebnis-Tab Titel mit Seite/Region · Fehler anhängen Toggle
- **Farben-Themes:** Schema `ildcolors-theme-v1` · ungültig klar DE · Import Merge vs Ersetzen
- **Dokument-Tags-Filter:** Trefferanzahl · Esc leert Filter · fehlende getaggte Recent grau
- **Export-Presets:** Duplikat-Namen ablehnen · Export/Import aller Presets JSON (`ildexportpresets-v1`)
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.1

Post-Release-Polish nach **2.5.0**:

- **OCR-Region:** DPI/Sprache aus Defaults · Abbruch Esc/Progress · Hinweis bei leerem Ergebnis
- **Farben-Themes:** Vorschau-Swatches · Als Default speichern · Import/Export JSON
- **Dokument-Tags:** Tag hinzufügen/entfernen am Recent · Filter Clear · Persistenz
- **Export-Presets:** benannte Presets max. 10 · Anwenden/Löschen · Live-Zusammenfassung
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.5.0

Minor-Bump nach **2.4.5**:

- **PDF-OCR-Region:** Rechteck wählen → nur Region OCR → Text-Tab
- **Annotation-Farben-Themes:** vordefinierte Paletten Markieren/Corporate laden
- **Dokument-Tags global:** `ildtags-v1` über Docs hinweg filterbar in Willkommen/Recent
- **Export-Preset:** letzte Export-Einstellungen (DPI/Format/Pfad) als Preset „Zuletzt“
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.4.5

Post-Release-Polish nach **2.4.4**:

- **Thumb Auto-Prune:** Toast Dauer OCR-Toast-Settings · Klick kopiert Status erneut
- **Annotation-Vorlagen:** Esc → „Apply abgebrochen“ + Vorlagenname · A11y Announcement
- **Sync-Scroll:** AccessibleName live bei Toggle (an/aus im Namen)
- **F1 Cheat-Sheet TXT:** Reset Default über gemeinsamen Helper (`template_reset`)
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.4.4

Post-Release-Polish nach **2.4.3**:

- **Thumb Auto-Prune:** Status kopierbar (Klick → Zwischenablage) · Toast optional Settings
- **Annotation-Vorlagen:** Esc → Status „Apply abgebrochen“ · Fokus Toolbar
- **Sync-Scroll:** Announcement bei Toggle · AccessibleName Status-Widget
- **F1 Cheat-Sheet TXT:** Reset Default Bestätigung nur bei Abweichung · Fokus+Selektion
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.4.3

Post-Release-Polish nach **2.4.2**:

- **Thumb Auto-Prune:** Log/Status „N Dateien / X MB entfernt“ · Settings Intervall oder on-write
- **Annotation-Vorlagen:** Quick-Apply Rechtsklick wählen · Esc bricht Apply-Modus ab
- **Sync-Scroll:** Tooltip zeigt Zustand an/aus · A11y AccessibleName/Description
- **F1 Cheat-Sheet TXT:** Live-Vorschau Dateiname · Quick-Insert `{date}` · Reset Default
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.4.2

Post-Release-Polish nach **2.4.1**:

- **Thumb-Cache:** Bestätigung · freigegebene MB in Status · Auto-Prune bei Limit
- **Annotation-Vorlagen:** Toolbar Quick-Apply ★ · zuletzt verwendet merken
- **Sync-Scroll:** Status-Klick toggled · Tooltip mit Shortcut
- **F1 Cheat-Sheet TXT:** Zielordner merken · Template `{date}_shortcuts.txt`
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.4.1

Post-Release-Polish nach **2.4.0**:

- **Thumb-Cache:** max MB Settings · „Cache leeren“ · Hit/Miss Status optional Debug
- **Annotation-Vorlagen:** Umbenennen/Löschen · Vorschau · Standard ★
- **Sync-Scroll:** Statusleisten-Indikator an/aus · nur PDF↔PDF
- **F1 Cheat-Sheet:** Suche/Filter · Drucken · Export TXT
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.4.0

Minor-Bump nach **2.3.5**:

- **PDF-Seiten-Thumbnail Disk-Cache:** mtime-invalidiert · spürbar bei großen Docs
- **Annotation-Templates:** Stempel/Highlight-Styles speichern/laden (**ildtmpl-v1**)
- **Split-View Sync-Scroll:** Toggle für zwei PDF-Tabs nebeneinander (Scroll + Seiten-Sync)
- **Tastatur-Cheat-Sheet:** F1 / Hilfe Dialog mit Shortcut-Liste DE
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.3.5

Post-Release-Polish nach **2.3.4**:

- **PDF-Kompression:** Toggle AccessibleName/Description · Status Ersparnis-% announced
- **URL-Links TXT:** Reset Default Bestätigung nur bei Abweichung · Fokus+Selektion
- **Command Palette:** Pin-ersetzen-Bestätigung mit Namen des zu ersetzenden Pins
- **Telemetrie-Stub:** „Stubs öffnen“ → Fokus erste Stub-Zeile · Dialog schließt · weiter no-op
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.3.4

Post-Release-Polish nach **2.3.3**:

- **PDF-Kompression:** Label klar „Ergebnis nach Kompression öffnen“ · A11y (AccessibleName/Description)
- **URL-Links TXT:** Live-Vorschau Dateiname · Quick-Insert `{stem}`/`{date}` · Reset Default
- **Command Palette:** Overflow-Hinweis bei Pin-Limit · Option ältesten Pin ersetzen
- **Telemetrie-Stub:** Esc schließt Info-Dialog · Button „Stubs öffnen“ · weiter no-op
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.3.3

Post-Release-Polish nach **2.3.2**:

- **PDF-Kompression:** Öffnen-Toggle Settings merken · Status mit Ersparnis-% auch bei Fehler
- **URL-Links TXT:** Template `{stem}_links.txt` · Zielordner merken · UTF-8-BOM Option
- **Command Palette:** Pin-Persistenz · Unpin · max Pins Settings 3/5/10
- **Telemetrie-Stub:** kurz warum Stub · Verweis Tab Stubs · weiter no-op
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.3.2

Post-Release-Polish nach **2.3.1**:

- **PDF-Kompression:** optional neues File öffnen · Größenersparnis-% in Status
- **URL-Links Sidebar:** Suche/Filter · Doppelklick springt zur Seite · Export URL-Liste TXT
- **Command Palette:** Pin häufige Befehle · Recent-Anzahl Settings 5/10/20
- **Telemetrie-Stub:** Toggle disabled bleibt · Info-Dialog warum Stub
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.3.1

Post-Release-Polish nach **2.3.0**:

- **PDF-Kompression:** Vorher/Nachher-Größenanzeige · Abbruch · DPI/Qualität-Presets (Bildschirm/E-Book/Druck)
- **URL-Links:** Live-Validierung · Hover-Tooltip · Sidebar-Liste · Bearbeiten/Löschen
- **Command Palette:** Fuzzy-Filter · letzte Befehle · Esc schließt · Kategorien
- **Telemetrie-Stub:** Settings-Warntext „keine Datenübertragung“ · bleibt no-op
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.3.0

Minor-Bump nach **2.2.5**:

- **PDF-Kompression/Downsample:** Qualitäts-Dialog · optional Bilder-Downsample (pypdfium2-Raster + pikepdf) → neues File
- **Link-Annotationen:** Rechteck + URI in Sidecar · Klick öffnet Browser · optional Bake als PDF-Link
- **Schnellaktionen-Palette:** Ctrl+K Command Palette (öffnen, suchen, OCR, export…)
- **Telemetrie-Stub:** Settings opt-in „anonym Nutzung melden“ Default aus · immer no-op
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen/Telemetrie klar markiert (Ink ≠ Stylus)

## Neu in 2.2.5

Post-Release-Polish nach **2.2.4**:

- **Seitenbeschriftungen:** TXT **Live-Vorschau Dateiname** · Quick-Insert **`{stem}`/`{date}`** · **Reset Default**
- **Ink/Freihand:** Toast-**Klick fokussiert Ink-Tool** · Announcement **wie OCR**
- **Dokument-Historie:** **Redo** nach Undo Clear · **klarer DE-Hinweis** wenn kein Undo möglich
- **CONTRIBUTING:** Sync-Zeile **Windows** · optional **`-NoStart`**
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert (Ink ≠ Stylus)

## Neu in 2.2.4

Post-Release-Polish nach **2.2.3**:

- **Seitenbeschriftungen:** TXT-Template **`{stem}_labels.txt`** · Zielordner merken · UTF-8-BOM Option
- **Ink/Freihand:** Status **„Glättung angewandt“** Toast-Dauer Settings · A11y Announcement
- **Dokument-Historie:** Clear-Zähler **„N Einträge entfernt“** · Undo Clear (Session) bzw. Hinweis
- **CONTRIBUTING:** Sync-Befehl als **eine Zeile copy-ready**
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert (Ink ≠ Stylus)

## Neu in 2.2.3

Post-Release-Polish nach **2.2.2**:

- **Seitenbeschriftungen:** Vorschau Scroll-Liste erste 20 · Export Labels als TXT
- **Ink/Freihand:** Undo-Glätten mit **Redo ok** · Status **„Glättung angewandt“**
- **Dokument-Historie:** Clear optional nur aktuellen Filter · Export gefilterte Sicht
- **CONTRIBUTING:** Exitcode-Tabelle kurz · Link zu [`scripts/smoke_ild.py`](scripts/smoke_ild.py)
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert (Ink ≠ Stylus)

## Neu in 2.2.2

Post-Release-Polish nach **2.2.1**:

- **Seitenbeschriftungen:** Range-Überlappungs-Validierung (DE) · Vorschau erste Labels
- **Ink/Freihand:** Glättungsstärke leicht/mittel/stark · Undo nach Glätten eigener Stack-Eintrag
- **Dokument-Historie:** Doppelklick springt zur Seite (wenn page im Eintrag) · Clear mit Bestätigung
- **CONTRIBUTING:** Sync-Einzeiler = sync-ild.ps1-Pfad · Smoke-Beispielkommando
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert (Ink ≠ Stylus)

## Neu in 2.2.1

Post-Release-Polish nach **2.2.0**:

- **Seitenbeschriftungen:** Range-Editor · Import aus PDF · Reset arabisch 1…
- **Ink/Freihand:** Strichstärke/Farbe · Löschen letzter Strich · Glätten optional leicht
- **Dokument-Historie:** Panel letzte 50 · Filter Aktionstyp · Export JSON
- **CI:** Workflow-Stub klar **manual only**; CONTRIBUTING Sync-Einzeiler
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert (Ink ≠ Stylus)

## Neu in 2.2.0

Minor-Bump nach **2.1.5**:

- **PDF-Seitenbeschriftungen:** benutzerdefinierte Labels (i, ii, 1…) Sidecar + Anzeige; optional PDF PageLabels (pikepdf)
- **Ink/Freihand:** Maus-Polyline-Annotation · Sidecar · Undo (kein Stylus)
- **Dokument-Historie:** `*.ildhist.json` Schema **ildhist-v1** mit Zeitstempeln
- **CI:** `smoke_ild` in CONTRIBUTING/Docs; optional GitHub-Actions-Workflow-Stub (nur lokal dokumentiert)
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Nightly-Smoke

```bat
python scripts\smoke_ild.py
python scripts\smoke_ild.py --qt
python scripts\smoke_ild.py --json
```

Siehe auch **CONTRIBUTING.md**. Workflow-Stub: `.github/workflows/smoke-ild.yml` (**manual only**, keine Cloud-CI-Pflicht).

Exit **0**/OK (`ok=true`) · **1**/Fehler (`ok=false`) · **2**/ungültige Option. `--json` liefert `ok`, `checks`, `duration_ms`, `version`; bei Fail enthält `checks[]` ein Objekt mit `error` (max 200 Zeichen, Overflow `…`).

Beispiel Erfolg:

```json
{"ok": true, "version": "2.3.5", "duration_ms": 1234, "checks": ["version", "imports", "cli", "measure_diff_import", "changelog"]}
```

Beispiel Fail:

```json
{"ok": false, "version": "2.3.5", "duration_ms": 12, "checks": ["version", {"name": "imports", "error": "import x: …"}]}
```

Ende (ohne `--json`): `Laufzeit: N ms` · `smoke_ild: OK`.

## Neu in 2.1.5

Post-Release-Polish nach **2.1.4**:

- **PDF-Kommentar-Import:** Status-Copy-Toast **Dauer OCR-Settings** · **Klick fokussiert Statusleiste/Log** falls vorhanden
- **Messung / Diff:** Reset Default über **gemeinsamen Helper** · **Esc im Feld verwirft Edit** (nicht speichern)
- **Nightly-Smoke:** Fail-`error` **max 200 Zeichen truncated mit …** · Docs Fail-Beispiel
- **FEATURES.md lokal sync** Hinweis (siehe Sync)
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.1.4

Post-Release-Polish nach **2.1.3**:

- **PDF-Kommentar-Import:** Status kopieren → **Clipboard + Toast + A11y Announcement**
- **Messung:** CSV-Template **Reset Default** · Bestätigung nur bei Abweichung · **Fokus+Selektion**
- **PDF-Vergleich:** Diff-TXT **Quick-Insert-Buttons** · **Reset Default** (Bestätigung≠Default · Fokus+Selektion)
- **Nightly-Smoke:** `smoke_ild.py --json` bei Fail **`checks[].error` Text** · **Exitcode spiegelt `ok`**
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.1.3

Post-Release-Polish nach **2.1.2**:

- **PDF-Kommentar-Import:** Status **ersetzt / übersprungen / neu** · **kopierbarer Text** (Status kopieren)
- **Messung:** CSV Live-Template **`{stem}_measures.csv`** · Quick-Insert `{stem}`/`{date}` · ungültige rot
- **PDF-Vergleich:** Diff-TXT Template **`{stemA}_vs_{stemB}_{mode}.txt`** · Live-Vorschau · ungültige rot
- **Nightly-Smoke:** `smoke_ild.py --json` Felder **`ok`**, **`checks[]`**, **`duration_ms`**, **`version`** · Beispiel in Docs
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.1.2

Post-Release-Polish nach **2.1.1**:

- **PDF-Kommentar-Import:** Toggle **Nach Import Sidecar speichern** · Status **„N importiert, M übersprungen“**
- **Messung:** CSV-Spalten **Typ,Seite,Wert,Einheit** · Zielordner merken · UTF-8-BOM Option
- **PDF-Vergleich:** Textlayer **Unified/Side-by-Side Toggle** · Diff-TXT **Dateiname-Template**
- **Nightly-Smoke:** `smoke_ild.py` **`--json` Summary** · **Laufzeit ms** · in Docs erwähnt
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.1.1

Post-Release-Polish nach **2.1.0**:

- **PDF-Kommentar-Import:** Dry-Run-Zähler · Duplikat-Strategie keep/skip/replace · Fortschritt/Abbruch
- **Messung:** Snap-to-Annotation optional · Labels persistent · Messwerte-CSV
- **PDF-Vergleich:** Textlayer Ignore-Whitespace · Nur-Unterschiede · Export Unified Diff TXT
- **Nightly-Smoke:** `smoke_ild.py` Exit 0/1/2 · `--qt`/`--skip-qt` · DE-Hilfe
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.1.0

Minor-Bump nach **2.0.5**:

- **PDF-Kommentar-Import:** native Markup (pikepdf) grob → Sidecar
- **Messung:** Fläche (Rechteck) + Winkel (zwei Linien); Anzeige **mm/px Toggle**
- **PDF-Vergleich:** Textlayer-Diff (Unified) im Diff-Panel
- **Nightly-Smoke:** `scripts/smoke_ild.py` CLI+Import-Checks
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.0.5

Post-Release-Polish nach **2.0.4** (Basis **2.0.3** / **2.0.2** / **2.0.1** / **2.0.0** / **1.9.5**):

- **Multi-Dokument-Suche:** Reset Default **Bestätigung nur bei Abweichung** · **Fokus+Selektion**
- **PDF-Portfolios:** Footer-Klick filtert **übersprungene** (Toggle) · **leerer Footer bei 0**
- **Accessibility:** HC-Toast **gleiche Announcement-Pipeline wie OCR-Toast**
- **Installer:** `install-ild.ps1` **-Quiet -Uninstall**: **Exit 0 auch wenn nichts zu entfernen** · **Kurz-Summary stdout**
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.0.4

Post-Release-Polish nach **2.0.3** (Basis **2.0.2** / **2.0.1** / **2.0.0** / **1.9.5**):

- **Multi-Dokument-Suche:** CSV-Template **Quick-Insert `{date}`/`{query}`** · **ungültige Platzhalter rot** · **Reset Default**
- **PDF-Portfolios:** Footer **„extrahiert X, übersprungen Y“** · Button **Ordner öffnen**
- **Accessibility:** HC-Toast **Dauer aus OCR-Toast-Settings** · **A11y Announcement**
- **Installer:** `install-ild.ps1` **-Uninstall**: **Log-Datei-Pfad** ausgeben · **-Quiet** unterdrückt Prompts
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.0.3

Post-Release-Polish nach **2.0.2** (Basis **2.0.1** / **2.0.0** / **1.9.5**):

- **Multi-Dokument-Suche:** CSV **Zielordner merken** · Live-Dateiname-Template **`{date}_multisearch.csv`**
- **PDF-Portfolios:** Extrakt **Abbruch** · **Teilergebnis behalten** · **Statuszählung**
- **Accessibility:** HC-Toast **„High-Contrast an/aus“** · UI-Skala Reset **Bestätigung nur bei ≠100 %**
- **Installer:** `install-ild.ps1` **-Uninstall**: fehlende Shortcuts **kein Fehler** · Log-Zeile
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.0.2

Post-Release-Polish nach **2.0.1** (Basis **2.0.0** / **1.9.5**):

- **Multi-Dokument-Suche:** CSV-Spalten **Doc,Seite,Snippet,Match** · **UTF-8 BOM** Option · **Regex-Fehlerstatus**
- **PDF-Portfolios:** Extrakt **Zielordner merken** · **Namenskollision umbenennen** · **Fortschritt**
- **Accessibility:** UI-Skala Button **Reset 100 %** · High-Contrast Shortcut **Ctrl+Alt+H**
- **Installer:** `install-ild.ps1` **-Uninstall** entfernt Shortcuts · Exit-Codes **0/1** dokumentiert
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.0.1

Post-Release-Polish nach **2.0.0** (Basis **1.9.5** / **1.9.4** / **1.9.3** / **1.9.2** / **1.9.1** / **1.9.0**):

- **Multi-Dokument-Suche:** Case / Whole-word / Regex · Treffer-CSV · Fortschritt bei vielen Docs
- **PDF-Portfolios:** Inhaltsliste Sidebar · Auswahl extrahieren · Hinweis bei leerer Collection
- **Accessibility:** High-Contrast Persistenz live · UI-Schrift Skala 100/125/150 % Live-Vorschau (Settings)
- **Installer:** `install-ild.ps1` `-NoDesktop` · Idempotenz · DE-Meldungen · sync-ild.ps1-Hinweis
- Stubs KI/Cloud/Stylus/3D/Plugin-Hooks/Outline-Vorlesen unverändert klar markiert

## Neu in 2.0.0

Major-Release nach **1.9.5** (Basis **1.9.4** / **1.9.3** / **1.9.2** / **1.9.1** / **1.9.0**):

- **Multi-Dokument-Suche:** Volltext über alle offenen PDFs (Textlayer) · zentrale Trefferliste (Ctrl+Shift+F)
- **PDF-Portfolios:** mehrere Dateien → Container-PDF (pikepdf Attachments + `/Collection`) erstellen/öffnen/extrahieren
- **Accessibility:** Document Outline Vorlesen bleibt Stub; neu High-Contrast Theme Toggle + größere UI-Schrift (Settings)
- **Installer:** `scripts/install-ild.ps1` — Startmenü-Shortcut + optional Desktop-Link (User-Profil, ohne Admin)
- About zeigt Serie **„2.0“**; Stubs KI/Cloud/Stylus/3D/Plugin-Hooks unverändert klar markiert

## Neu in 1.9.5

Post-Release-Polish nach **1.9.4** (Basis **1.9.3** / **1.9.2** / **1.9.1** / **1.9.0**):

- **PDF-Anhänge:** Footer-Klick filtert Liste auf **umbenannt/übersprungen** (Toggle) · **leerer Footer wenn 0**
- **Quick-Stempel:** Esc → Fokus Toolbar · Shortcut **Ctrl+Shift+S** = Standard-Stempel ★
- **Tabellen-OCR → CSV:** Abbruch setzt **Trennzeichen-Combobox synchron** zurück · **A11y bei Speichern**
- **Settings-Seite „Stubs“:** Info-Dialog mit **Kurzbeschreibung** + Badge **„Geplant“** · **Esc schließt**
- Stubs klar als Stub / nicht produktiv markiert

## Neu in 1.9.4

Post-Release-Polish nach **1.9.3** (Basis **1.9.2** / **1.9.1** / **1.9.0**):

- **PDF-Anhänge:** Footer **„hinzugefügt X, umbenannt Y, übersprungen Z“** · **kopierbar**
- **Quick-Stempel:** Esc → **„Platzieren abgebrochen“** · **Zoom/Opacity** wie Signatur merken
- **Tabellen-OCR → CSV:** Live-Trennzeichen **Persistenz erst Speichern** · **Vorschau-Reset bei Abbruch**
- **Settings-Seite „Stubs“:** FEATURES fehlt → **Statushinweis** · **Doppelklick Stub = Info-Dialog**
- Stubs klar als Stub / nicht produktiv markiert

## Neu in 1.9.3

Post-Release-Polish nach **1.9.2** (Basis **1.9.1** / **1.9.0**):

- **PDF-Anhänge:** Duplikat-Dialog **„Für alle anwenden“** · Statuszählung am Ende
- **Quick-Stempel:** Rechtsklick Bibliothek wählen · **Esc** bricht Platzieren ab
- **Tabellen-OCR → CSV:** Zeilen/Spalten-Zähler · Trennzeichen live in Vorschau
- **Settings-Seite „Stubs“:** Link zu FEATURES.md · „keine Aktion“ klar · Sortierung A–Z
- Stubs klar als Stub / nicht produktiv markiert

## Neu in 1.9.2

Post-Release-Polish nach **1.9.1** (Basis **1.9.0**):

- **PDF-Anhänge:** Mehrfach-Drag&Drop · Duplikat-Namen Warnung + Umbenennen
- **Quick-Stempel:** Toolbar-Button · zuletzt verwendet merken (Fallback Standard ★)
- **Tabellen-OCR → CSV:** Vorschau erste 5 Zeilen vor Speichern · Abbruch möglich
- **Settings-Seite „Stubs“:** KI / Cloud / Stylus / 3D / Plugin-Hooks mit Status
- Stubs klar als Stub / nicht produktiv markiert

## Neu in 1.9.1

Post-Release-Polish nach **1.9.0** (Basis **1.8.5**):

- **PDF-Anhänge:** Spalten Größe/Typ · Doppelklick extrahieren · Drag&Drop hinzufügen
- **Stempel-Bildbibliothek:** Umbenennen/Löschen · Vorschau · Standard-Stempel ★
- **Tabellen-OCR → CSV:** Trennzeichen `;`/`,`/Tab · Zielordner merken · UTF-8-BOM Option
- **Plugin-Hooks Stub:** About „nicht produktiv“ · Event-Namen in Docs
- Stubs KI/Cloud/Stylus/3D + Plugin-Hooks klar als Stub / nicht produktiv

## Neu in 1.9.0

Minor-Release nach **1.8.5** (Basis **1.8.4** / **1.8.3** / **1.8.2**):

- **PDF-Anhänge:** listen / extrahieren / **hinzufügen** (pikepdf; Entfernen im Dialog)
- **Stempel-Bildbibliothek:** eigene Bilder unter `config/stamps/` · Sidecar-Stempel aus Bibliothek
- **Tabellen-OCR → CSV:** grobe Tabellenerkennung → CSV (UTF-8 BOM, `;`)
- **Plugin-Hooks Stub:** interner Event-Bus + no-op Loader (kein Plugin-System)
- Stubs KI/Cloud/Stylus/3D unverändert; Plugin-Hooks zusätzlich als Stub
