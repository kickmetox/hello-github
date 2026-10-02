# InstantLens Doc

Moderne Textverarbeitung mit PDF-Annotator, OCR-Bridge und Formulargenerator.

**Version:** 0.2.2  
**Hersteller:** Andreas Meyer · ame@sellerbach.de

## Quickstart (Windows)

Eine Sync-Zeile (Branch → `D:\AI_Temp\InstantLensDoc`, pip, Start):

```powershell
powershell -ExecutionPolicy Bypass -File "D:\AI_Temp\sync-ild.ps1"
```

Oder lokal im App-Ordner:

```bat
cd /d D:\AI_Temp\InstantLensDoc && pip install -r requirements.txt && run.bat
```

Nur starten (nach Sync/pip): `run.bat`

## Neu in 0.2.2

- PDF-Textsuche: Treffer auf aktueller Seite highlighten; Weiter springt zum nächsten
- Annotation-Farben-Picker (Highlight / Stift); Export-Zielordner merken
- Einstellungen: Standard-Zoom, Autosave-Intervall

Siehe [CHANGELOG.md](CHANGELOG.md), [FEATURES.md](FEATURES.md) und [INFO.md](INFO.md).
