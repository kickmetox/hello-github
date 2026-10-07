"""Drucken unter Windows über Qt's QtPrintSupport/QPrinter statt der
rohen win32print-API - PySide6 ist ohnehin Abhängigkeit, QPrinter kennt
Kopienanzahl/Duplex/Druckerauswahl bereits nativ und kann das Rendering
selbst übernehmen. win32print.StartDocPrinter ist eine Roh-API (Bytes an
den Spooler) und könnte PDFs nicht ohne eigenes Rendering drucken.

Getestet: list_printers() und print_files() wurden komplett end-to-end
gegen ein echtes, in CUPS konfiguriertes Gerät verifiziert (mit expliziter
Zustimmung des Nutzers, da dabei tatsächlich eine Seite bedruckt wurde) -
Drucker-Liste, PDF laden/rendern, QPrinter-Auftrag, bestätigt am Papier-
ausgang. Das lief über Qts plattformunabhängige Druck-Abstraktion, die
unter Windows denselben Code gegen den nativen Windows-Druckertreiber
statt CUPS ausführt - Windows-spezifisches Treiberverhalten (insbesondere
Duplex, das hier nicht getestet wurde, da das Gerät einseitig bedruckte)
bleibt dennoch auf der echten Windows-Maschine zu verifizieren."""
from __future__ import annotations

from .printing import PrintError, PrinterInfo


def is_available() -> bool:
    try:
        from PySide6 import QtPrintSupport, QtPdf  # noqa: F401
    except ImportError:
        return False
    return True


def list_printers() -> list[PrinterInfo]:
    from PySide6.QtPrintSupport import QPrinterInfo

    default_name = QPrinterInfo.defaultPrinter().printerName()
    printers = []
    for info in QPrinterInfo.availablePrinters():
        printers.append(PrinterInfo(
            name=info.printerName(),
            state="bereit",
            is_default=(info.printerName() == default_name),
        ))
    return printers


def print_files(
    printer_name: str,
    file_paths: list[str],
    copies: int = 1,
    duplex: bool = False,
    timeout: int = 120,
) -> None:
    """Druckt PDF-Dateien, indem jede Seite über QPdfDocument gerendert
    und auf den QPrinter gemalt wird (kein zusätzliches PDF-Tool nötig -
    QtPdf ist seit PySide6 6.5 enthalten)."""
    if not file_paths:
        raise PrintError("Keine Datei zum Drucken übergeben.")

    from PySide6.QtCore import QSize, Qt
    from PySide6.QtGui import QPainter
    from PySide6.QtPrintSupport import QPrinter, QPrinterInfo

    try:
        from PySide6.QtPdf import QPdfDocument
    except ImportError as exc:
        raise PrintError(
            "PySide6-Modul 'QtPdf' fehlt - für Drucken unter Windows wird ein "
            "vollständiges PySide6 (>= 6.5) benötigt."
        ) from exc

    matching = [p for p in QPrinterInfo.availablePrinters() if p.printerName() == printer_name]
    if not matching:
        raise PrintError(f"Drucker '{printer_name}' nicht gefunden.")

    printer = QPrinter(matching[0], QPrinter.PrinterMode.HighResolution)
    printer.setCopyCount(max(1, copies))
    printer.setDuplex(QPrinter.DuplexMode.DuplexLongSide if duplex else QPrinter.DuplexMode.DuplexNone)

    painter = QPainter()
    started = False
    first_page = True
    try:
        for file_path in file_paths:
            doc = QPdfDocument()
            if doc.load(file_path) != QPdfDocument.Error.None_:
                raise PrintError(f"PDF konnte nicht geladen werden: {file_path}")
            for page_index in range(doc.pageCount()):
                if not started:
                    if not painter.begin(printer):
                        raise PrintError("Drucker konnte nicht geöffnet werden.")
                    started = True
                elif not first_page:
                    printer.newPage()
                first_page = False
                page_size = doc.pagePointSize(page_index).toSize()
                target = printer.pageRect(QPrinter.Unit.DevicePixel).size().toSize()
                render_size = page_size.scaled(target, Qt.AspectRatioMode.KeepAspectRatio)
                image = doc.render(page_index, render_size)
                painter.drawImage(painter.viewport(), image)
    finally:
        if started:
            painter.end()
