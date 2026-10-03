# InstantLens Doc — Kurzinfo

| | |
|---|---|
| Produkt | InstantLens Doc |
| Version | **2.0.3** |
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

## Sync (eine Zeile)

```powershell
powershell -ExecutionPolicy Bypass -File "D:\AI_Temp\sync-ild.ps1"
```

Skript: [sync-ild.ps1](scripts/sync-ild.ps1) — Branch `cursor/instantlensdoc-2108` (oder `-LocalPack` / Pack-Zip) nach `D:\AI_Temp\InstantLensDoc`, pip, Start. **Nutzer-Icon in `assets` wird nicht überschrieben.**

Ohne Start: `-SkipStart` (Alias `-NoStart`). Exit-Codes: **0** OK · **1** allgemein · **2** Git-Fehler.

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
