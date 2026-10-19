"""PowerPoint 97–2003 (.ppt) ohne LibreOffice.

OLE-Container und Record-Header werden hier gelesen. Text kommt aus
RT_TextCharsAtom und RT_TextBytesAtom. Bilder nur bei PNG- oder JPEG-Signatur.
"""

from __future__ import annotations

import struct
import tempfile
from pathlib import Path

from officedisplay.model.presentation import Presentation, Slide, SlideObject, new_id


class PptReadError(ValueError):
    """Die .ppt-Datei lässt sich aus einem konkreten Grund nicht lesen."""


_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")
_ENDOFCHAIN = 0xFFFFFFFE
_FREESECT = 0xFFFFFFFF
_FATSECT = 0xFFFFFFFD
_DIFSECT = 0xFFFFFFFC
_NOSTREAM = 0xFFFFFFFF

_RT_SLIDE = 1006
_RT_PERSIST = 1011
_RT_TEXT_CHARS = 4000
_RT_TEXT_BYTES = 4008
_RT_SLIDE_LIST = 4080

_ENCRYPTED = "Die Datei ist verschlüsselt und lässt sich hier nicht öffnen."
_PNG = b"\x89PNG\r\n\x1a\n"
_JPEG = b"\xff\xd8\xff"


def import_ppt(path: str | Path) -> Presentation:
    source = Path(path)
    try:
        blob = source.read_bytes()
    except OSError as exc:
        raise PptReadError("Die Datei lässt sich nicht lesen.") from exc
    if not blob:
        raise PptReadError("Die Datei ist leer.")
    streams = _compound_streams(blob)
    names = {name.casefold(): data for name, data in streams.items()}
    if any(name.startswith("encrypt") for name in names):
        raise PptReadError(_ENCRYPTED)
    document = names.get("powerpoint document")
    if document is None:
        raise PptReadError("Die Datei enthält keinen PowerPoint-Dokumentstrom.")
    slides = _slides_from_document(document)
    pictures = _image_blobs(names.get("pictures", b""))
    _attach_loose_pictures(slides, pictures)
    if not slides:
        raise PptReadError("Die Datei enthält keine lesbaren Folien.")
    folder = Path(tempfile.mkdtemp(prefix="officedisplay-ppt-"))
    presentation = Presentation(title=source.stem or "PowerPoint")
    for index, item in enumerate(slides, start=1):
        presentation.slides.append(_make_slide(item, index, folder))
    return presentation


def _make_slide(item: dict, index: int, folder: Path) -> Slide:
    texts = [part for part in item["texts"] if part]
    title = ""
    for part in texts:
        title = part.split("\n", 1)[0].strip()
        if title:
            break
    slide = Slide(id=new_id(), name=(title[:48] or f"Folie {index}"))
    if texts:
        slide.objects.append(
            SlideObject(
                id=new_id(),
                kind="text",
                x=0.08,
                y=0.1,
                w=0.84,
                h=0.34 if item["images"] else 0.72,
                name="text",
                props={
                    "text": "\n".join(texts),
                    "font_size": 32,
                    "color": "#1B1F2A",
                    "font_family": "Segoe UI",
                    "align": "left",
                },
            )
        )
    for image_index, raw in enumerate(item["images"]):
        suffix = ".png" if raw.startswith(_PNG) else ".jpg"
        target = folder / f"folie{index}-{image_index}{suffix}"
        target.write_bytes(raw)
        slide.objects.append(
            SlideObject(
                id=new_id(),
                kind="image",
                x=0.08,
                y=0.48,
                w=0.84,
                h=0.42,
                name="bild",
                props={"path": str(target)},
            )
        )
    return slide


def _slides_from_document(blob: bytes) -> list[dict]:
    slides: list[dict] = []
    outline: list[list[str]] = []

    def take_slide(body: bytes) -> None:
        texts = _texts(body)
        images = _image_blobs(body)
        if texts or images:
            slides.append({"texts": texts, "images": images})

    def walk(data: bytes, in_outline: bool, bucket: list[str] | None) -> None:
        for ver, _inst, kind, payload in _records(data):
            if kind == _RT_SLIDE and ver == 0xF:
                take_slide(payload)
                continue
            if kind == _RT_SLIDE_LIST and ver == 0xF:
                walk(payload, True, None)
                continue
            if in_outline and kind == _RT_PERSIST:
                bucket = []
                outline.append(bucket)
                continue
            if kind == _RT_TEXT_CHARS:
                text = _clean(payload.decode("utf-16le", errors="ignore"))
                if text and bucket is not None:
                    bucket.append(text)
                continue
            if kind == _RT_TEXT_BYTES:
                text = _clean(payload.decode("cp1252", errors="replace"))
                if text and bucket is not None:
                    bucket.append(text)
                continue
            if ver == 0xF:
                walk(payload, in_outline, bucket)

    walk(blob, False, None)
    for index, group in enumerate(outline):
        if not group:
            continue
        if index < len(slides):
            if not slides[index]["texts"]:
                slides[index]["texts"] = group
        else:
            slides.append({"texts": group, "images": []})
    return slides


def _texts(data: bytes) -> list[str]:
    found: list[str] = []

    def walk(blob: bytes) -> None:
        for ver, _inst, kind, payload in _records(blob):
            if kind == _RT_TEXT_CHARS:
                text = _clean(payload.decode("utf-16le", errors="ignore"))
                if text:
                    found.append(text)
            elif kind == _RT_TEXT_BYTES:
                text = _clean(payload.decode("cp1252", errors="replace"))
                if text:
                    found.append(text)
            elif ver == 0xF and kind != _RT_SLIDE:
                walk(payload)

    walk(data)
    return found


def _records(blob: bytes):
    pos = 0
    end = len(blob)
    while pos + 8 <= end:
        ver_inst, kind, length = struct.unpack_from("<HHI", blob, pos)
        pos += 8
        if length < 0 or pos + length > end:
            break
        yield ver_inst & 0xF, ver_inst >> 4, kind, blob[pos : pos + length]
        pos += length


def _clean(text: str) -> str:
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def _image_blobs(blob: bytes) -> list[bytes]:
    found: list[bytes] = []
    seen: set[bytes] = set()
    for raw in _pngs(blob) + _jpegs(blob):
        if raw in seen:
            continue
        seen.add(raw)
        found.append(raw)
    return found


def _pngs(blob: bytes) -> list[bytes]:
    found = []
    start = 0
    while True:
        at = blob.find(_PNG, start)
        if at < 0:
            break
        end_mark = blob.find(b"IEND", at + 8)
        if end_mark < 0:
            break
        end = end_mark + 8
        if end <= len(blob):
            found.append(blob[at:end])
        start = at + 8
    return found


def _jpegs(blob: bytes) -> list[bytes]:
    found = []
    start = 0
    while True:
        at = blob.find(_JPEG, start)
        if at < 0:
            break
        end = blob.find(b"\xff\xd9", at + 3)
        if end < 0:
            break
        found.append(blob[at : end + 2])
        start = end + 2
    return found


def _attach_loose_pictures(slides: list[dict], pictures: list[bytes]) -> None:
    if not pictures:
        return
    owned = {raw for slide in slides for raw in slide["images"]}
    loose = [raw for raw in pictures if raw not in owned]
    if not loose:
        return
    if not slides:
        slides.append({"texts": [], "images": loose})
        return
    for index, raw in enumerate(loose):
        slides[min(index, len(slides) - 1)]["images"].append(raw)


def _compound_streams(blob: bytes) -> dict[str, bytes]:
    if len(blob) < 512 or blob[:8] != _SIGNATURE:
        raise PptReadError("Die Datei ist kein OLE-Dokument.")
    if struct.unpack_from("<H", blob, 0x1C)[0] != 0xFFFE:
        raise PptReadError("Die OLE-Datei ist unvollständig.")
    sector_shift = struct.unpack_from("<H", blob, 0x1E)[0]
    mini_shift = struct.unpack_from("<H", blob, 0x20)[0]
    if sector_shift not in {9, 12} or mini_shift < 6:
        raise PptReadError("Die OLE-Datei ist unvollständig.")
    sector_size = 1 << sector_shift
    mini_size = 1 << mini_shift
    if len(blob) < sector_size:
        raise PptReadError("Die OLE-Datei ist unvollständig.")
    fat_count = struct.unpack_from("<I", blob, 0x2C)[0]
    dir_start = struct.unpack_from("<I", blob, 0x30)[0]
    cutoff = struct.unpack_from("<I", blob, 0x38)[0]
    mini_fat_start = struct.unpack_from("<I", blob, 0x3C)[0]
    mini_fat_count = struct.unpack_from("<I", blob, 0x40)[0]
    difat_start = struct.unpack_from("<I", blob, 0x44)[0]
    difat_count = struct.unpack_from("<I", blob, 0x48)[0]
    difat: list[int] = []
    for index in range(109):
        value = struct.unpack_from("<I", blob, 0x4C + index * 4)[0]
        if value < _DIFSECT:
            difat.append(value)
    next_difat = difat_start
    for _ in range(difat_count):
        if next_difat >= _DIFSECT:
            break
        chunk = _sector(blob, next_difat, sector_size)
        entries = sector_size // 4
        for index in range(entries - 1):
            value = struct.unpack_from("<I", chunk, index * 4)[0]
            if value < _DIFSECT:
                difat.append(value)
        next_difat = struct.unpack_from("<I", chunk, (entries - 1) * 4)[0]
    if fat_count and len(difat) < fat_count:
        raise PptReadError("Die OLE-Datei ist unvollständig.")
    fat = bytearray()
    for sector in difat[:fat_count]:
        fat += _sector(blob, sector, sector_size)
    fat_table = list(struct.unpack("<" + "I" * (len(fat) // 4), fat)) if fat else []

    def read_chain(start: int, table: list[int], size: int) -> bytes:
        if start >= _DIFSECT:
            return b""
        out = bytearray()
        seen: set[int] = set()
        sector = start
        while sector < _DIFSECT:
            if sector in seen or sector >= len(table) and size == sector_size:
                break
            if size == sector_size and sector >= len(table):
                break
            seen.add(sector)
            if size == sector_size:
                out += _sector(blob, sector, sector_size)
                sector = table[sector] if sector < len(table) else _ENDOFCHAIN
            else:
                break
            if len(seen) > 100000:
                break
        return bytes(out)

    directory = read_chain(dir_start, fat_table, sector_size)
    entries = _directory(directory)
    root = next((entry for entry in entries if entry["type"] == 5), None)
    mini_stream = b""
    mini_table: list[int] = []
    if root is not None and mini_fat_count and mini_fat_start < _DIFSECT:
        mini_stream = read_chain(root["start"], fat_table, sector_size)[: root["size"]]
        mini_raw = read_chain(mini_fat_start, fat_table, sector_size)
        # The mini FAT may span the declared count of sectors.
        need = mini_fat_count * sector_size
        mini_table = list(struct.unpack("<" + "I" * (len(mini_raw[:need]) // 4), mini_raw[:need])) if mini_raw else []

    streams: dict[str, bytes] = {}
    for entry in entries:
        if entry["type"] != 2 or not entry["name"]:
            continue
        if entry["size"] < cutoff and mini_table:
            streams[entry["name"]] = _mini_read(mini_stream, mini_table, entry["start"], entry["size"], mini_size)
        else:
            streams[entry["name"]] = read_chain(entry["start"], fat_table, sector_size)[: entry["size"]]
    return streams


def _sector(blob: bytes, index: int, sector_size: int) -> bytes:
    offset = (index + 1) * sector_size
    chunk = blob[offset : offset + sector_size]
    if len(chunk) < sector_size:
        raise PptReadError("Die OLE-Datei ist unvollständig.")
    return chunk


def _directory(blob: bytes) -> list[dict]:
    entries = []
    for offset in range(0, len(blob) - 127, 128):
        name_raw = blob[offset : offset + 64]
        name_len = struct.unpack_from("<H", blob, offset + 64)[0]
        kind = blob[offset + 66]
        start = struct.unpack_from("<I", blob, offset + 116)[0]
        size = struct.unpack_from("<Q", blob, offset + 120)[0]
        if size > 0xFFFFFFFF:
            size &= 0xFFFFFFFF
        chars = max(0, min(32, name_len // 2 - 1))
        name = name_raw[: chars * 2].decode("utf-16le", errors="ignore")
        entries.append({"name": name, "type": kind, "start": start, "size": size})
    return entries


def _mini_read(stream: bytes, table: list[int], start: int, size: int, mini_size: int) -> bytes:
    if start >= _DIFSECT or size <= 0:
        return b""
    out = bytearray()
    seen: set[int] = set()
    sector = start
    while sector < _DIFSECT and len(out) < size:
        if sector in seen:
            break
        seen.add(sector)
        offset = sector * mini_size
        out += stream[offset : offset + mini_size]
        sector = table[sector] if sector < len(table) else _ENDOFCHAIN
        if len(seen) > 100000:
            break
    return bytes(out[:size])
