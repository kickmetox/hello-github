# ild_pdf — auskoppelbares PDF-Modul

Lizenzfreundliche PDF-Engine auf **pypdfium2 / PDFium** (kein Poppler/GPL).  
Version **0.8.8**.


## Installation

```bash
pip install pypdfium2 Pillow pikepdf
# Modul-Pfad: InstantLensDoc-Root auf PYTHONPATH oder:
cd InstantLensDoc && python -c "import ild_pdf; print(ild_pdf.__version__)"
```

## Schnellstart

```python
from ild_pdf import (
    PdfDocument, render_page,
    Annotation, AnnotationStore, AnnotationType,
    rotate_page, flip_page, delete_pages, reorder_pages,
    extract_page_image, insert_image_as_page,
    extract_text_blocks, import_page_text_as_overlays, bake_text_overlays,
)

img = render_page("dokument.pdf", page_index=0, scale=2.0)
img.save("seite0.png")

store = AnnotationStore("dokument.pdf")
store.add(Annotation(0, AnnotationType.HIGHLIGHT, 40, 100, width=200, text="Wichtig"))
store.add(Annotation(0, AnnotationType.RECTANGLE, 50, 150, width=80, height=40, color="#27AE60"))
store.add(Annotation(0, AnnotationType.ARROW, 60, 200, callout_x=160, callout_y=120, color="#8E44AD"))
store.add(Annotation(0, AnnotationType.MEASURE, 20, 250, callout_x=200, callout_y=250, text="Messung"))
store.add(Annotation(0, AnnotationType.TEXT_OVERLAY, 40, 40, width=180, height=28, text="Editierbar", font_size=14))
store.save()  # → dokument.pdf.ildann.json (Sidecar v3)

# PDF-Text → Overlay (nicht natives Editieren — Overlay-Editor)
blocks = extract_text_blocks("dokument.pdf", 0)
import_page_text_as_overlays(store, "dokument.pdf", 0, scale=1.5)
bake_text_overlays("dokument.pdf", store, scale=1.5)  # Helvetica-Content ergänzen
```

## Beispielskript

```bash
python examples/ild_pdf_demo.py
python examples/ild_pdf_demo.py pfad/zu/datei.pdf
```

## API

| Symbol | Zweck |
|--------|--------|
| `PdfDocument` | Öffnen / Seitenzahl / Größe |
| `render_page` / `render_pages` | Seite(n) → PIL.Image |
| `convert_from_path` | pdf2image-ähnlicher Drop-in (`ild_pdf.render`) |
| `Annotation` / `AnnotationStore` | Sidecar `*.ildann.json` **v3**; `undo()` / `redo()` / `atomic()` |
| `AnnotationType` | + **redaction**, signature*, rectangle/line/arrow/measure, text_overlay |
| `DRAG_TYPES` | Typen für Drag-Zeichnung (UI) |
| `STAMP_PRESETS` / `STAMP_LIBRARY` / `stamp_with_date` | Stempel-Texte / Bibliothek + Datum |
| `list_form_fields` / `set_form_values` / `has_acroform` | AcroForm lesen/schreiben |
| `list_attachments` / `extract_attachment` / `has_attachments` | PDF-Anhänge auflisten/extrahieren |
| `extract_text_blocks` | Sichtbaren Text grob als Blöcke lesen |
| `extract_page_plain_text` / `extract_all_plain_text` | Plaintext Seite / gesamtes PDF → Editor |
| `import_page_text_as_overlays` | Blöcke → `TEXT_OVERLAY` im Store |
| `bake_text_overlays` | Overlays als PDF-Content (Helvetica) einbrennen |
| `extract_page_image` / `extract_pages_as_images` / `insert_image_as_page` | Seite(n)→PNG/JPEG / Bild→Seite |
| `extract_embedded_images` / `insert_image_stamp_overlay` | Extraktion / Stempel-Hook |
| `rotate_page` / `flip_page` / `delete_pages` / `reorder_pages` | pikepdf-Seitenops |
| `merge_pdfs` / `split_pdf` / `split_into_single_page_pdfs` / `extract_page_range` | Zusammenführen / Teilen / 1-Seite-PDFs / Seitenbereich |
| `flatten_annotations_to_pdf` / `bake_annotations` | Annotationen flatten/bake → neues PDF (alle Seiten) |
| `extract_outline` / `add_outline_item` / `delete_outline_item` | Lesezeichen lesen / hinzufügen / löschen |
| `apply_watermark` / `apply_page_numbers` | Wasserzeichen / Seitenzahlen |
| `inspect_pdf` / `clamp_render_scale` | Große-PDF-Diagnose / Zoom-Cap |
| `clear_render_cache` | Render-LRU leeren |
| `set_password` / `needs_password` | PDF verschlüsseln / prüfen |
| `bake_redactions` | Schwärzungen einbrennen |
| `compress_image_for_pdf` / `compress_pdf_as_images` | Bildkompression |
| `get_metadata` / `set_metadata` / `PdfMetadata` | Dokument-Metadaten |
| `PAGE_SIZE_PRESETS` / `get_page_boxes` / `set_page_size` / `set_crop_box` | Seitengröße / Crop |
| `format_size_pair` / `pt_to_mm` / `pt_to_inch` / `to_pt` | Seitengröße mm/inch formatieren |
| `PdfDocument.page_label` / `page_labels` / `format_page_status` | PDF-Seitenlabels (römisch/arabisch) |

### Sidecar-Schema v4 (`ildann-v4`) — PDF-Highlight-kompatibel

```json
{
  "version": 4,
  "schema": "ildann-v4",
  "pdf": "dokument.pdf",
  "meta": { "y_origin": "top", "coord_space": "render_pixels" },
  "annotations": [
    {
      "page": 0,
      "type": "highlight",
      "x": 40, "y": 80, "width": 120, "height": 14,
      "text": "markierter Text",
      "color": "#FFE066",
      "opacity": 0.5,
      "rects": [[40, 80, 120, 14]],
      "quadPoints": [40, 80, 160, 80, 40, 94, 160, 94],
      "colorRGB": [1.0, 0.8784, 0.4],
      "pdf_highlight": {
        "subtype": "Highlight",
        "rects": [[40, 80, 120, 14]],
        "quadPoints": [40, 80, 160, 80, 40, 94, 160, 94],
        "colorRGB": [1.0, 0.8784, 0.4],
        "opacity": 0.5,
        "contents": "markierter Text"
      }
    }
  ]
}
```

- **Export** (`export_json`): Schema v4 inkl. `rects` / `quadPoints` / `colorRGB` / `pdf_highlight` für Highlight & Underline.
- **Sidecar-Save**: Kernfelder + `version: 4` / `schema` (Interop-Felder beim Export).
- **Import** (`import_json`): Schema v4 wird validiert (`version`/`schema` + Annotation-Struktur); bei Fehler `AnnotationImportError`. Sidecar ohne version/schema bleibt importierbar.
- Koordinaten: Render-Pixel; `meta.y_origin=top` (UI). Linien: Start `(x,y)`, Ende `(callout_x, callout_y)`.

### Hinweis Textbearbeitung

Echtes natives PDF-Text-Rewrite ist mit pypdfium2/pikepdf nicht zuverlässig möglich.  
InstantLens Doc nutzt deshalb einen **Overlay-Editor** (Sidecar) und optional `bake_text_overlays`.

## Hinweis Poppler

Poppler wird **nicht** mitgeliefert. Für Legacy-Code: Aufrufe von `pdf2image.convert_from_path` auf `ild_pdf.render.convert_from_path` umstellen.
