# ild_pdf — auskoppelbares PDF-Modul

Lizenzfreundliche PDF-Engine auf **pypdfium2 / PDFium** (kein Poppler/GPL).

## Installation

```bash
pip install pypdfium2 Pillow pikepdf
# Modul-Pfad zum Python-Path hinzufügen oder InstantLensDoc als Root nutzen
```

## Schnellstart

```python
from pathlib import Path
from ild_pdf import PdfDocument, render_page, Annotation, AnnotationStore, AnnotationType
from ild_pdf import rotate_page, delete_pages, reorder_pages
from ild_pdf import extract_page_image, insert_image_as_page

# Rendern
img = render_page("dokument.pdf", page_index=0, scale=2.0)
img.save("seite0.png")

# Annotationen (Sidecar JSON v2 neben dem PDF)
store = AnnotationStore("dokument.pdf")
store.add(Annotation(page=0, type=AnnotationType.HIGHLIGHT, x=40, y=100, width=200, text="Wichtig"))
store.add(Annotation(page=0, type=AnnotationType.STAMP, x=200, y=40, width=120, height=40, text="GEPRÜFT"))
store.add(Annotation(page=0, type=AnnotationType.CALLOUT, x=100, y=200, text="Hinweis", callout_x=60, callout_y=260))
store.save()

# Bild-Hooks
extract_page_image("dokument.pdf", 0, "seite0.png")
insert_image_as_page("dokument.pdf", "foto.jpg")

# Seitenoperationen
rotate_page("dokument.pdf", 0, 90)
# delete_pages("dokument.pdf", [2])
# reorder_pages("dokument.pdf", [1, 0, 2])
```

## API

| Symbol | Zweck |
|--------|--------|
| `PdfDocument` | Öffnen / Seitenzahl / Größe |
| `render_page` / `render_pages` | Seite(n) → PIL.Image |
| `convert_from_path` | pdf2image-ähnlicher Drop-in |
| `Annotation` / `AnnotationStore` | Highlight, Underline, Sticky, Text, Stempel, Callout |
| `extract_page_image` / `insert_image_as_page` | Seite↔Bild |
| `extract_embedded_images` / `insert_image_stamp_overlay` | Extraktion / Stempel-Hook |
| `rotate_page` / `delete_pages` / `reorder_pages` | pikepdf-Seitenops |

## Hinweis Poppler

Poppler wird **nicht** mitgeliefert. Für Legacy-Code: Aufrufe von `pdf2image.convert_from_path` auf `ild_pdf.render.convert_from_path` umstellen.
