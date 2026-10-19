"""Öffnen über die Endung. PPTX-Fallback bleibt in import_pptx."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from officedisplay.io.pptx_io import import_pptx
from officedisplay.model.presentation import Presentation


class FormatReadError(ValueError):
    """Die Datei hat eine bekannte Endung, lässt sich aber so nicht lesen."""


OOXML_EXT = {".pptx", ".potx", ".ppsx"}
PACKAGE_EXT = {".pdrx", ".prdx", ".prsx", ".prvx"}
TEXTISH_EXT = {".rtx"}
PPT_EXT = {".ppt"}
DECK_EXT = OOXML_EXT | PACKAGE_EXT | TEXTISH_EXT | PPT_EXT | {".odp", ".odisp"}

_PPT_MESSAGE = "Die Datei .ppt lässt sich nur öffnen, wenn LibreOffice (soffice) vorhanden ist."
_PACKAGE_MESSAGE = "Die Datei ist kein PowerPoint-Paket. Erwartet wird ein ZIP mit ppt/presentation.xml."
_RTX_MESSAGE = "Die Datei .rtx ist weder ein PowerPoint-Paket noch Text oder RTF."


def load_presentation(path: str | Path) -> Presentation:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix in OOXML_EXT:
        return import_pptx(source)
    if suffix in PACKAGE_EXT:
        if _has_presentation_xml(source):
            return import_pptx(source)
        raise FormatReadError(_PACKAGE_MESSAGE)
    if suffix in TEXTISH_EXT:
        if _has_presentation_xml(source):
            return import_pptx(source)
        text = _text_or_rtf(source)
        if text is None:
            raise FormatReadError(_RTX_MESSAGE)
        from officedisplay.ai.doc_transform import slides_from_text

        return slides_from_text(text, source.stem or "Dokument")
    if suffix in PPT_EXT:
        converted = _ppt_to_pptx(source)
        if converted is None:
            raise FormatReadError(_PPT_MESSAGE)
        return import_pptx(converted)
    if suffix == ".odp":
        from officedisplay.io.odp_io import import_odp

        return import_odp(source)
    if suffix == ".odisp":
        from officedisplay.io.native_io import load_odisp

        return load_odisp(source)
    raise FormatReadError("Diese Datei lässt sich nicht laden. Erwartet wird eine Präsentation oder ein bekanntes Bild- oder Videoformat.")


def _has_presentation_xml(source: Path) -> bool:
    if not zipfile.is_zipfile(source):
        return False
    try:
        with zipfile.ZipFile(source) as archive:
            names = {name.replace("\\", "/").lstrip("/") for name in archive.namelist()}
    except (OSError, zipfile.BadZipFile):
        return False
    return "ppt/presentation.xml" in names


def _text_or_rtf(source: Path) -> str | None:
    try:
        blob = source.read_bytes()
    except OSError:
        return None
    if not blob or b"\x00" in blob[:512]:
        return None
    if blob.startswith(b"{\\rtf") or blob.startswith(b"{\rtf"):
        return _rtf_to_text(blob.decode("latin-1", errors="replace"))
    try:
        return blob.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _rtf_to_text(raw: str) -> str:
    import re

    text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", raw)
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    text = text.replace("\\", " ")
    return re.sub(r"[ \t]+\n", "\n", text).strip()


def _ppt_to_pptx(source: Path) -> Path | None:
    soffice = shutil.which("soffice")
    if not soffice:
        return None
    folder = Path(tempfile.mkdtemp(prefix="officedisplay-ppt-"))
    try:
        subprocess.run(
            [soffice, "--headless", "--convert-to", "pptx", "--outdir", str(folder), str(source)],
            check=False,
            timeout=120,
            capture_output=True,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    converted = folder / f"{source.stem}.pptx"
    if converted.is_file():
        return converted
    found = list(folder.glob("*.pptx"))
    return found[0] if found else None
