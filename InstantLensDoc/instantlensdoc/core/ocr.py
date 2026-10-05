"""OCR-Bridge über pytesseract / Tesseract — Presets + Ausgabe-Modi."""

from __future__ import annotations

import os
import platform
import shutil
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

from PIL import Image, ImageDraw, ImageFont


class OcrUnavailable(RuntimeError):
    """Tesseract oder pytesseract nicht verfügbar."""


class OcrOutputMode(str, Enum):
    """Ausgabe-Modus nach OCR."""

    EDITABLE_TEXT = "editable_text"  # reiner Text → Editor
    SEARCHABLE_IMAGE = "searchable_image"  # Bildseite + Textlayer-Sidecar
    TABLE_CSV = "table_csv"  # Tabellen-Heuristik → CSV — 1.9.0
    LAYOUT_PRESERVE = "layout_preserve"  # Text + Blöcke/Lesereihenfolge · hOCR/TSV — 2.6.3


# UI-Presets: Anzeigename → Tesseract-lang
LANG_PRESETS: Dict[str, str] = {
    "Deutsch + Englisch": "deu+eng",
    "Deutsch": "deu",
    "Englisch": "eng",
    "Französisch": "fra",
    "Spanisch": "spa",
    "Italienisch": "ita",
    "Niederländisch": "nld",
    "Polnisch": "pol",
    "Portugiesisch": "por",
    "Mehrsprachig (deu+eng+fra)": "deu+eng+fra",
}


TESSERACT_WIKI_URL = "https://github.com/UB-Mannheim/tesseract/wiki"

# ScanTuxio-Konvention (scantuxio/ocr.py + platform_utils.bundled_tool_dir):
# Frozen: <exe-dir>/tesseract/tesseract.exe + tessdata/ daneben
# Quelle: <projekt>/vendor/tesseract/tesseract.exe + tessdata/
# TESSDATA_PREFIX = dirname(exe)/tessdata  (conda-Build kennt den Prefix sonst nicht)
SCANTUXIO_WIN_ROOTS = (
    r"D:\AI_Temp\ScanTuxio Win",
    r"D:\AI_Temp\ScanTuxio-Win",
    r"D:\AI_Temp\ScanTuxioWin",
)

TESSERACT_COMMON_PATHS = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)

_TESS_EXE_NAMES = ("tesseract.exe", "tesseract")


def _ild_app_roots() -> List[Path]:
    """Install-/App-Root: Frozen-EXE, PyInstaller MEIPASS, Paket-Root, CWD."""
    roots: List[Path] = []

    def _add(raw: object) -> None:
        if not raw:
            return
        try:
            p = Path(str(raw)).expanduser().resolve()
        except OSError:
            p = Path(str(raw))
        if p not in roots:
            roots.append(p)

    if getattr(sys, "frozen", False):
        _add(Path(sys.executable).parent)
        mei = getattr(sys, "_MEIPASS", None)
        if mei:
            _add(mei)
    # instantlensdoc/core/ocr.py → App-Root InstantLensDoc/
    _add(Path(__file__).resolve().parents[2])
    _add(Path.cwd())
    for env_key in ("ILD_APP_ROOT", "INSTANTLENSDOC_ROOT"):
        _add(os.environ.get(env_key))
    return roots


def _join_win_or_posix(root: str, *parts: str) -> str:
    """Join ohne Path.resolve — Windows-Absolutfade (D:\\...) bleiben unter Linux literal."""
    if not parts:
        return root
    # Windows-Root (Laufwerkspfad) immer mit Backslash joinen
    if len(root) >= 2 and root[1] == ":" and ("\\" in root or root.endswith((":", "/", "\\"))):
        base = root.rstrip("\\/")
        return base + "\\" + "\\".join(parts)
    return str(Path(root).joinpath(*parts))


def _exe_paths_under_root(root: str) -> List[str]:
    """ScanTuxio-relative Layouts unter einem Root (als Strings)."""
    out: List[str] = []
    rels = (
        ("tesseract",),
        ("vendor", "tesseract"),
        ("bin",),
        ("Tesseract-OCR",),
        ("dist", "tesseract"),
        ("dist", "ScanTuxio", "tesseract"),
        (),
    )
    for rel in rels:
        tool = _join_win_or_posix(root, *rel) if rel else root
        for name in _TESS_EXE_NAMES:
            out.append(_join_win_or_posix(tool, name))
    return out


def tesseract_lookup_candidates() -> List[str]:
    """Kandidaten in Lookup-Reihenfolge (existieren nicht zwingend) — 2.6.42."""
    cands: List[str] = []

    def _push(p: object) -> None:
        s = str(p)
        if s and s not in cands:
            cands.append(s)

    for env_key in ("TESSERACT_CMD", "TESSERACT_PATH"):
        env = os.environ.get(env_key)
        if env:
            _push(env)
    for root in _ild_app_roots():
        for p in _exe_paths_under_root(str(root)):
            _push(p)
    for win_root in SCANTUXIO_WIN_ROOTS:
        for p in _exe_paths_under_root(win_root):
            _push(p)
        # Sibling neben ILD-Dest, z. B. InstantLensDoc-2642 → ..\ScanTuxio Win
        leaf = win_root.rstrip("\\/").split("\\")[-1].split("/")[-1]
        for app in _ild_app_roots():
            try:
                sib = str(app.parent / leaf)
            except OSError:
                continue
            if sib.replace("\\", "/").rstrip("/") == win_root.replace("\\", "/").rstrip("/"):
                continue
            # nur echte Sibling-Ordner auf dem gleichen Host (kein D:\-Literal unter /workspace)
            if len(sib) >= 2 and sib[1] == ":" and platform.system() != "Windows":
                continue
            if not Path(sib).is_dir() and platform.system() != "Windows":
                continue
            for p in _exe_paths_under_root(sib):
                _push(p)
    for p in TESSERACT_COMMON_PATHS:
        _push(p)
    return cands


def tessdata_dir_for(exe: str | os.PathLike[str]) -> Optional[str]:
    """TESSDATA_PREFIX wie ScanTuxio: tessdata neben tesseract.exe."""
    try:
        d = Path(exe).expanduser().resolve().parent
    except OSError:
        d = Path(exe).parent
    for cand in (
        d / "tessdata",
        d.parent / "tessdata",
        d / "tessdata" / "tessdata",
    ):
        try:
            if cand.is_dir():
                return str(cand)
        except OSError:
            continue
    return None


def apply_tessdata_prefix(exe: str | os.PathLike[str]) -> Optional[str]:
    """Setzt TESSDATA_PREFIX auf das mitgelieferte tessdata (ScanTuxio-Runtime)."""
    tessdata = tessdata_dir_for(exe)
    if tessdata:
        os.environ["TESSDATA_PREFIX"] = tessdata
        return tessdata
    return os.environ.get("TESSDATA_PREFIX") or None


def resolve_tesseract_executable() -> Optional[str]:
    """Bundled vendor → ScanTuxio Win → PATH → Program Files."""
    for cand in tesseract_lookup_candidates():
        p = Path(cand)
        try:
            if p.is_file():
                return str(p.resolve())
        except OSError:
            continue
    which = shutil.which("tesseract") or shutil.which("tesseract.exe")
    if which:
        return which
    if platform.system() == "Windows":
        for env_var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
            base = os.environ.get(env_var)
            if not base:
                continue
            tess_root = Path(base) / "Tesseract-OCR"
            if not tess_root.is_dir():
                continue
            for name in _TESS_EXE_NAMES:
                hit = tess_root / name
                if hit.is_file():
                    return str(hit)
    return None


_PATH_HINT_DE = (
    "Pfad-Hilfe (keine Extra-Installation noetig, wenn ScanTuxio-Runtime liegt):\n"
    "  {app}\\vendor\\tesseract\\tesseract.exe\n"
    "  {app}\\tesseract\\tesseract.exe   (neben InstantLensDoc.exe, ScanTuxio-Layout)\n"
    "  D:\\AI_Temp\\ScanTuxio Win\\tesseract\\tesseract.exe\n"
    "  D:\\AI_Temp\\ScanTuxio Win\\vendor\\tesseract\\tesseract.exe\n"
    "  D:\\AI_Temp\\ScanTuxio Win\\bin\\tesseract.exe\n"
    + "\n".join(f"  {p}" for p in TESSERACT_COMMON_PATHS)
    + "\n"
    "  tessdata: deu.traineddata + eng.traineddata neben der EXE (TESSDATA_PREFIX).\n"
    "  Copy-Hint: xcopy /E /I /Y \"D:\\AI_Temp\\ScanTuxio Win\\tesseract\" .\\vendor\\tesseract"
)

INSTALL_HINT_DE = (
    "OCR benötigt die Tesseract-Runtime (ScanTuxio-Bundle oder UB-Mannheim).\n\n"
    "Windows:\n"
    "  Bevorzugt: Runtime aus ScanTuxio Win (vendor/tesseract oder neben der EXE).\n"
    "  Fallback: winget install UB-Mannheim.TesseractOCR\n"
    f"  oder Installer: {TESSERACT_WIKI_URL}\n\n"
    f"{_PATH_HINT_DE}\n\n"
    "Danach Python-Paket (falls fehlen):\n"
    "  pip install pytesseract\n\n"
    "Sprachen: deu + eng empfohlen."
)

INSTALL_HINT_HTML = (
    "<p>OCR benötigt die Tesseract-Runtime (ScanTuxio-Bundle oder UB-Mannheim).</p>"
    "<p><b>Windows:</b> Runtime aus ScanTuxio Win "
    "(<code>vendor\\tesseract\\tesseract.exe</code>) oder "
    "<code>winget install UB-Mannheim.TesseractOCR</code><br>"
    f'oder <a href="{TESSERACT_WIKI_URL}">UB-Mannheim Tesseract (Wiki)</a></p>'
    "<p><b>Pfad-Hilfe</b>:<br>"
    "<code>{app}\\vendor\\tesseract\\tesseract.exe</code><br>"
    "<code>{app}\\tesseract\\tesseract.exe</code><br>"
    r"<code>D:\AI_Temp\ScanTuxio Win\tesseract\tesseract.exe</code><br>"
    + "<br>".join(f"<code>{p}</code>" for p in TESSERACT_COMMON_PATHS)
    + "<br><code>TESSDATA_PREFIX</code> = tessdata neben der EXE.</p>"
    "<p>Python: <code>pip install pytesseract</code></p>"
    "<p>Sprachen <code>deu</code> + <code>eng</code>.</p>"
)


@dataclass
class OcrLayoutBlock:
    """Ein Textblock aus Tesseract (Lesereihenfolge / BBox) — 2.6.3."""

    block_num: int
    reading_order: int
    left: int
    top: int
    width: int
    height: int
    lines: List[str] = field(default_factory=list)
    text: str = ""
    conf: float = -1.0


@dataclass
class OcrLayoutPage:
    """Layout-OCR einer Seite: Text + Blöcke + optional hOCR/TSV — 2.6.3."""

    text: str
    blocks: List[OcrLayoutBlock] = field(default_factory=list)
    hocr: str = ""
    tsv: str = ""
    lang: str = "deu+eng"
    width: int = 0
    height: int = 0


@dataclass
class OcrResult:
    text: str
    lang: str
    mode: OcrOutputMode
    source_label: str = ""
    searchable_pdf: Path | None = None
    sidecar: Path | None = None
    table_rows: List[List[str]] | None = None  # Rohzeilen Tabellen-CSV — 1.9.2
    blocks: List[OcrLayoutBlock] | None = None  # Layout-Blöcke — 2.6.3
    hocr_path: Path | None = None
    tsv_path: Path | None = None
    layout: OcrLayoutPage | None = None


def _configure_tesseract_cmd(pytesseract) -> None:
    """pytesseract.tesseract_cmd + TESSDATA_PREFIX (ScanTuxio-Bundle zuerst) — 2.6.42."""
    exe: Optional[str] = None
    try:
        current = getattr(pytesseract.pytesseract, "tesseract_cmd", None)
        if current and Path(str(current)).is_file():
            exe = str(Path(str(current)).resolve())
    except Exception:
        exe = None
    if not exe:
        exe = resolve_tesseract_executable()
    if not exe:
        return
    try:
        pytesseract.pytesseract.tesseract_cmd = exe
    except Exception:
        pass
    apply_tessdata_prefix(exe)


def tesseract_available() -> tuple[bool, str]:
    try:
        import pytesseract
    except ImportError:
        return False, "pytesseract nicht installiert (pip install pytesseract).\n\n" + INSTALL_HINT_DE
    try:
        _configure_tesseract_cmd(pytesseract)
        ver = pytesseract.get_tesseract_version()
        return True, f"Tesseract {ver}"
    except Exception as e:
        # Ein erneuter Pfad-Versuch nach Fehlschlag
        try:
            import pytesseract as _pt

            _configure_tesseract_cmd(_pt)
            ver = _pt.get_tesseract_version()
            return True, f"Tesseract {ver}"
        except Exception:
            pass
        return False, (
            "Tesseract-Runtime fehlt oder ist nicht im PATH.\n\n"
            + INSTALL_HINT_DE
            + f"\n\nTechnik-Detail: {e}"
        )


def list_installed_languages() -> List[str]:
    ok, _ = tesseract_available()
    if not ok:
        return []
    try:
        import pytesseract

        langs = pytesseract.get_languages(config="")
        return sorted(langs)
    except Exception:
        return []


def _load_image(source: Union[str, Path, Image.Image]) -> Image.Image:
    if isinstance(source, (str, Path)):
        return Image.open(source)
    return source


def format_text_as_table(lines: List[List[str]]) -> str:
    """Zeilen/Spalten als Markdown-Tabelle formatieren (einfach)."""
    if not lines:
        return ""
    col_count = max(len(r) for r in lines)
    if col_count < 2:
        return "\n".join(" ".join(r) for r in lines)
    widths = [0] * col_count
    padded: List[List[str]] = []
    for row in lines:
        cells = row + [""] * (col_count - len(row))
        padded.append(cells)
        for i, c in enumerate(cells):
            widths[i] = max(widths[i], len(c))
    header = padded[0]
    sep = "| " + " | ".join("-" * max(1, w) for w in widths) + " |"
    out = ["| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(header)) + " |", sep]
    for row in padded[1:]:
        out.append("| " + " | ".join(row[i].ljust(widths[i]) for i in range(col_count)) + " |")
    return "\n".join(out)


def format_rows_as_csv(
    rows: List[List[str]],
    *,
    delimiter: str = ";",
    dialect: str = "excel",
    utf8_bom: bool = True,
) -> str:
    """
    Zeilen/Spalten als CSV (Default `;` für DE-Excel) — 1.9.1.
    Optional UTF-8 BOM-Präfix im String (Excel-kompatibel).
    """
    import csv
    import io

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=delimiter, dialect=dialect, lineterminator="\n")
    for row in rows:
        writer.writerow([str(c) if c is not None else "" for c in row])
    body = buf.getvalue()
    return ("\ufeff" + body) if utf8_bom else body


def write_ocr_table_csv(
    path: str | Path,
    rows: List[List[str]],
    *,
    delimiter: str = ";",
    utf8_bom: bool = True,
) -> Path:
    """Schreibt Tabellen-OCR als CSV (UTF-8, optional BOM) — 1.9.1."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = format_rows_as_csv(rows, delimiter=delimiter, utf8_bom=utf8_bom)
    # BOM liegt ggf. schon im String; encoding utf-8 (nicht utf-8-sig) vermeidet Doppel-BOM
    path.write_text(text, encoding="utf-8")
    return path


def _rows_from_tesseract_data(
    data: dict,
    *,
    gap_threshold: int = 28,
    min_conf: int = 40,
) -> tuple[List[List[str]], bool]:
    """Grobe Tabellenerkennung aus image_to_data → (rows, table_like)."""
    n = len(data.get("text") or [])
    buckets: dict[tuple[int, int], list[tuple[int, str]]] = {}
    for i in range(n):
        word = (data["text"][i] or "").strip()
        if not word:
            continue
        conf_raw = data["conf"][i]
        conf = int(float(conf_raw)) if conf_raw not in ("-1", "") else -1
        if conf >= 0 and conf < min_conf:
            continue
        key = (int(data["block_num"][i]), int(data["line_num"][i]))
        left = int(data["left"][i])
        buckets.setdefault(key, []).append((left, word))

    if not buckets:
        return [], False

    line_rows: List[List[str]] = []
    table_like = False
    for _key in sorted(buckets.keys()):
        words = sorted(buckets[_key], key=lambda t: t[0])
        if len(words) >= 2:
            cols: List[str] = []
            col_words: List[str] = []
            prev_x = words[0][0]
            for left, w in words:
                if col_words and left - prev_x > gap_threshold:
                    cols.append(" ".join(col_words))
                    col_words = [w]
                else:
                    col_words.append(w)
                prev_x = left + len(w) * 8
            if col_words:
                cols.append(" ".join(col_words))
            if len(cols) >= 2:
                table_like = True
                line_rows.append(cols)
            else:
                line_rows.append([" ".join(w for _, w in words)])
        else:
            line_rows.append([words[0][1]])
    return line_rows, table_like


def ocr_image_table_rows(
    source: Union[str, Path, Image.Image],
    lang: str = "deu+eng",
) -> tuple[List[List[str]], bool]:
    """
    Tabellen-OCR → Roh-Zeilen (heuristisch) — 1.9.0.
    Rückgabe: (rows, table_like).
    """
    ok, msg = tesseract_available()
    if not ok:
        raise OcrUnavailable(msg)

    import pytesseract

    img = _load_image(source)
    try:
        data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
    except Exception:
        plain = pytesseract.image_to_string(img, lang="eng")
        lines = [ln.split() for ln in plain.splitlines() if ln.strip()]
        return lines, False

    rows, table_like = _rows_from_tesseract_data(data)
    if not rows:
        plain = pytesseract.image_to_string(img, lang=lang)
        lines = [ln.split() for ln in plain.splitlines() if ln.strip()]
        return lines, False
    return rows, table_like


def ocr_image_to_csv(
    source: Union[str, Path, Image.Image],
    lang: str = "deu+eng",
    *,
    delimiter: str = ";",
    utf8_bom: bool = True,
) -> tuple[str, bool]:
    """OCR → CSV-String (optional UTF-8 BOM) + table_like-Flag — 1.9.1."""
    rows, table_like = ocr_image_table_rows(source, lang=lang)
    if not rows:
        return ("\ufeff" if utf8_bom else ""), False
    return format_rows_as_csv(rows, delimiter=delimiter, utf8_bom=utf8_bom), table_like


def ocr_image_structured(
    source: Union[str, Path, Image.Image],
    lang: str = "deu+eng",
) -> tuple[str, bool]:
    """
    OCR mit Tabellen-Heuristik über Tesseract image_to_data.
    Liefert (Text, used_table_layout).
    """
    ok, msg = tesseract_available()
    if not ok:
        raise OcrUnavailable(msg)

    import pytesseract

    img = _load_image(source)
    try:
        data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
    except Exception:
        plain = pytesseract.image_to_string(img, lang="eng")
        return plain, False

    line_rows, table_like = _rows_from_tesseract_data(data)
    if not line_rows:
        plain = pytesseract.image_to_string(img, lang=lang)
        return plain, False

    if table_like and len(line_rows) >= 2:
        return format_text_as_table(line_rows), True
    plain_lines = [" ".join(r) for r in line_rows]
    return "\n".join(plain_lines), table_like


def _blocks_from_tesseract_data(
    data: dict,
    *,
    min_conf: int = 0,
) -> List[OcrLayoutBlock]:
    """
    Baut Textblöcke aus ``image_to_data`` in Lesereihenfolge (top→bottom, left→right).

    Level: 2=Block, 4=Zeile, 5=Wort. Blöcke werden nach Top/Left sortiert — 2.6.3.
    """
    n = len(data.get("text") or [])
    if n == 0:
        return []

    # Zeilen → Wörter sammeln
    line_words: dict[tuple[int, int, int], list[tuple[int, str, float]]] = {}
    line_bbox: dict[tuple[int, int, int], tuple[int, int, int, int]] = {}
    block_bbox: dict[int, list[tuple[int, int, int, int]]] = {}

    for i in range(n):
        try:
            level = int(data["level"][i])
        except Exception:
            continue
        try:
            block_num = int(data["block_num"][i])
        except Exception:
            continue
        left = int(data["left"][i])
        top = int(data["top"][i])
        width = int(data["width"][i])
        height = int(data["height"][i])

        if level == 2:  # Block
            block_bbox.setdefault(block_num, []).append((left, top, width, height))
            continue
        if level == 4:  # Zeile
            par = int(data.get("par_num", [0] * n)[i] or 0)
            line = int(data.get("line_num", [0] * n)[i] or 0)
            line_bbox[(block_num, par, line)] = (left, top, width, height)
            continue
        if level != 5:
            continue
        word = (data["text"][i] or "").strip()
        if not word:
            continue
        conf_raw = data["conf"][i]
        try:
            conf = float(conf_raw)
        except Exception:
            conf = -1.0
        if conf >= 0 and conf < min_conf:
            continue
        par = int(data.get("par_num", [0] * n)[i] or 0)
        line = int(data.get("line_num", [0] * n)[i] or 0)
        key = (block_num, par, line)
        line_words.setdefault(key, []).append((left, word, conf))

    if not line_words and not block_bbox:
        return []

    # Blöcke aus Zeilen-Keys ableiten
    block_ids = sorted(
        {k[0] for k in line_words.keys()} | set(block_bbox.keys()),
        key=lambda b: (
            min(
                (bb[1] for bb in block_bbox.get(b, [(0, 10**9, 0, 0)])),
                default=10**9,
            ),
            min(
                (bb[0] for bb in block_bbox.get(b, [(10**9, 0, 0, 0)])),
                default=10**9,
            ),
            b,
        ),
    )

    blocks: List[OcrLayoutBlock] = []
    for order, block_num in enumerate(block_ids):
        keys = sorted(
            [k for k in line_words if k[0] == block_num],
            key=lambda k: (
                line_bbox.get(k, (0, 10**9, 0, 0))[1],
                line_bbox.get(k, (10**9, 0, 0, 0))[0],
                k[1],
                k[2],
            ),
        )
        lines: List[str] = []
        confs: List[float] = []
        for key in keys:
            words = sorted(line_words[key], key=lambda t: t[0])
            line_txt = " ".join(w for _, w, _ in words).strip()
            if line_txt:
                lines.append(line_txt)
            for _, _, c in words:
                if c >= 0:
                    confs.append(c)
        if not lines:
            continue
        bbs = block_bbox.get(block_num) or []
        if bbs:
            left = min(b[0] for b in bbs)
            top = min(b[1] for b in bbs)
            right = max(b[0] + b[2] for b in bbs)
            bottom = max(b[1] + b[3] for b in bbs)
            width = max(0, right - left)
            height = max(0, bottom - top)
        else:
            # Fallback aus Zeilen-BBoxes
            lbs = [line_bbox[k] for k in keys if k in line_bbox]
            if lbs:
                left = min(b[0] for b in lbs)
                top = min(b[1] for b in lbs)
                right = max(b[0] + b[2] for b in lbs)
                bottom = max(b[1] + b[3] for b in lbs)
                width = max(0, right - left)
                height = max(0, bottom - top)
            else:
                left = top = width = height = 0
        avg_conf = sum(confs) / len(confs) if confs else -1.0
        text = "\n".join(lines)
        blocks.append(
            OcrLayoutBlock(
                block_num=block_num,
                reading_order=order,
                left=left,
                top=top,
                width=width,
                height=height,
                lines=lines,
                text=text,
                conf=avg_conf,
            )
        )
    # Lesereihenfolge nach Top/Left (praktisch für Spalten/Fotos)
    blocks.sort(key=lambda b: (b.top, b.left, b.block_num))
    for i, b in enumerate(blocks):
        b.reading_order = i
    return blocks


def format_layout_text(blocks: List[OcrLayoutBlock], *, block_gap: str = "\n\n") -> str:
    """Blöcke in Lesereihenfolge als editierbarer Text (Absätze) — 2.6.3."""
    parts = [b.text.strip() for b in blocks if b.text and b.text.strip()]
    return block_gap.join(parts).strip()


def write_layout_sidecars(
    out_dir: str | Path,
    stem: str,
    layout: OcrLayoutPage,
    *,
    lang: str = "deu+eng",
    write_hocr: bool = True,
    write_tsv: bool = True,
) -> tuple[Path, Path | None, Path | None]:
    """
    Schreibt Layout-Sidecars neben dem Dokument:

    - ``{stem}.ildocr.txt`` — editierbarer Text mit Layout-Absätzen + Block-Metadaten-Header
    - optional ``{stem}.ildocr.hocr`` / ``{stem}.ildocr.tsv``

    Rückgabe: (txt_path, hocr_path|None, tsv_path|None) — 2.6.3.
    """
    out_dir_p = Path(out_dir)
    out_dir_p.mkdir(parents=True, exist_ok=True)
    safe = Path(stem).stem or "ocr"
    txt_path = out_dir_p / f"{safe}.ildocr.txt"
    header_lines = [
        "# InstantLens Doc OCR (Layout)",
        f"# lang={lang}",
        "# mode=layout_preserve",
        f"# blocks={len(layout.blocks)}",
        f"# size={layout.width}x{layout.height}",
        "",
    ]
    # Kompakte Block-Übersicht für spätere Edit-/Suche
    if layout.blocks:
        header_lines.append("# --- Blöcke (Lesereihenfolge) ---")
        for b in layout.blocks:
            header_lines.append(
                f"# block#{b.reading_order} id={b.block_num} "
                f"bbox={b.left},{b.top},{b.width},{b.height} "
                f"conf={b.conf:.1f} lines={len(b.lines)}"
            )
        header_lines.append("")
    txt_path.write_text("\n".join(header_lines) + (layout.text or "") + "\n", encoding="utf-8")

    hocr_path: Path | None = None
    tsv_path: Path | None = None
    if write_hocr and layout.hocr:
        hocr_path = out_dir_p / f"{safe}.ildocr.hocr"
        hocr_path.write_text(layout.hocr, encoding="utf-8")
    if write_tsv and layout.tsv:
        tsv_path = out_dir_p / f"{safe}.ildocr.tsv"
        tsv_path.write_text(layout.tsv, encoding="utf-8")
    return txt_path, hocr_path, tsv_path


def ocr_image_layout(
    source: Union[str, Path, Image.Image],
    lang: str = "deu+eng",
    *,
    include_hocr: bool = True,
    include_tsv: bool = True,
) -> OcrLayoutPage:
    """
    Erweiterte OCR mit Layout-Erhalt: Blöcke, Lesereihenfolge, optional hOCR/TSV — 2.6.3.

    Nutzt Tesseract ``image_to_data`` (+ ``image_to_pdf_or_hocr`` / TSV).
    """
    ok, msg = tesseract_available()
    if not ok:
        raise OcrUnavailable(msg)

    import pytesseract

    img = _load_image(source)
    width, height = img.size
    blocks: List[OcrLayoutBlock] = []
    text = ""
    hocr = ""
    tsv = ""

    try:
        data = pytesseract.image_to_data(
            img, lang=lang, output_type=pytesseract.Output.DICT
        )
        blocks = _blocks_from_tesseract_data(data)
        text = format_layout_text(blocks)
    except Exception:
        blocks = []
        text = ""

    if not text.strip():
        try:
            text = pytesseract.image_to_string(img, lang=lang).strip()
        except Exception:
            text = pytesseract.image_to_string(img, lang="eng").strip()

    if include_hocr:
        try:
            raw = pytesseract.image_to_pdf_or_hocr(img, lang=lang, extension="hocr")
            if isinstance(raw, bytes):
                hocr = raw.decode("utf-8", errors="replace")
            else:
                hocr = str(raw)
        except Exception:
            hocr = ""

    if include_tsv:
        try:
            tsv = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.STRING)
        except Exception:
            tsv = ""

    return OcrLayoutPage(
        text=text,
        blocks=blocks,
        hocr=hocr,
        tsv=tsv or "",
        lang=lang,
        width=width,
        height=height,
    )


# Handschrift: Tesseract-PSM + Preprocess + Multi-PSM — kein separates ML-Modell
HANDWRITING_PSM_PRESETS: Dict[str, int] = {
    "block": 6,  # Uniform block of text
    "line": 7,  # Single text line
    "word": 8,  # Single word
    "sparse": 11,  # Sparse text
}
DEFAULT_HANDWRITING_PSM = 6
# PSM-Kandidaten für Auto-Auswahl (beste Confidence / Textlänge)
HANDWRITING_PSM_CANDIDATES: tuple[int, ...] = (6, 7, 8, 11, 4, 13)

HANDWRITING_UPGRADE_PATH = (
    "Upgrade-Pfad: externes Handschrift-ML (z. B. TrOCR / Kraken / lokale "
    "ONNX-Modelle) über Plugin-Hook oder ``ild.ocr_handwriting.engine=external``; "
    "derzeit verbessert über Preprocess + Multi-PSM, kein eingebettetes Netz."
)


def _handwriting_settings() -> dict:
    """Optionale Settings unter ``ild.ocr_handwriting`` / app_settings."""
    defaults = {
        "preprocess": True,
        "multi_psm": True,
        "psm": DEFAULT_HANDWRITING_PSM,
        "engine": "tesseract",
    }
    try:
        from instantlensdoc.core.app_settings import load_settings

        raw = load_settings().get("ocr_handwriting") or load_settings().get(
            "ild.ocr_handwriting"
        )
        if isinstance(raw, dict):
            out = dict(defaults)
            out.update(raw)
            return out
    except Exception:
        pass
    return dict(defaults)


def normalize_handwriting_psm(psm: int | str | None) -> int:
    """PSM 0–13 oder Preset-Name → gültiger PSM für Handschrift."""
    if isinstance(psm, str):
        key = psm.strip().lower()
        if key in HANDWRITING_PSM_PRESETS:
            return int(HANDWRITING_PSM_PRESETS[key])
        try:
            psm = int(key)
        except (TypeError, ValueError):
            return DEFAULT_HANDWRITING_PSM
    try:
        n = int(psm) if psm is not None else DEFAULT_HANDWRITING_PSM
    except (TypeError, ValueError):
        n = DEFAULT_HANDWRITING_PSM
    return max(0, min(13, n))


def _preprocess_handwriting(img: Image.Image) -> Image.Image:
    """Leichtes Preprocess: Graustufen, Kontrast, Schwellwert, Deskew (PIL)."""
    try:
        from PIL import ImageEnhance, ImageOps, ImageFilter
    except Exception:
        return img

    try:
        work = img.convert("L")
    except Exception:
        return img

    try:
        work = ImageOps.autocontrast(work, cutoff=2)
    except Exception:
        pass
    try:
        work = ImageEnhance.Contrast(work).enhance(1.6)
    except Exception:
        pass
    try:
        work = work.filter(ImageFilter.MedianFilter(size=3))
    except Exception:
        pass
    # Einfacher Schwellwert
    try:
        work = work.point(lambda p: 255 if p > 160 else 0)
    except Exception:
        pass
    # Leichtes Deskew über extrem grobe Schätzung (nur kleine Winkel)
    try:
        work = _deskew_light(work)
    except Exception:
        pass
    return work


def _deskew_light(img: Image.Image) -> Image.Image:
    """Sehr leichtes Deskew: nur ±3° testen, beste Projektions-Varianz."""
    try:
        import statistics
    except Exception:
        return img

    best = img
    best_score = -1.0
    for angle in (0, -2, 2, -3, 3):
        try:
            rotated = img.rotate(angle, expand=False, fillcolor=255) if angle else img
            # horizontale Projektion: Varianz der Zeilenmittel
            w, h = rotated.size
            if w < 8 or h < 8:
                return img
            pix = rotated.load()
            rows = []
            step = max(1, h // 64)
            for y in range(0, h, step):
                s = 0
                for x in range(0, w, max(1, w // 64)):
                    s += 1 if pix[x, y] < 128 else 0
                rows.append(s)
            if len(rows) < 3:
                continue
            score = float(statistics.pvariance(rows))
            if score > best_score:
                best_score = score
                best = rotated
        except Exception:
            continue
    return best


def _score_ocr_result(text: str, conf_avg: float | None) -> float:
    """Score aus Textlänge + optionaler mittlerer Confidence."""
    t = (text or "").strip()
    if not t:
        return -1.0
    # alnum-Anteil belohnen, reine Müllzeichen bestrafen
    alnum = sum(1 for c in t if c.isalnum())
    length_score = min(len(t), 500) + alnum * 0.5
    conf = float(conf_avg) if conf_avg is not None else 40.0
    return length_score * (0.5 + max(0.0, min(conf, 100.0)) / 200.0)


def _ocr_with_psm(
    img: Image.Image,
    lang: str,
    psm_n: int,
) -> tuple[str, float | None]:
    import pytesseract

    config = f"--psm {psm_n}"
    text = ""
    conf_avg: float | None = None
    try:
        text = str(pytesseract.image_to_string(img, lang=lang, config=config) or "")
    except Exception:
        try:
            text = str(pytesseract.image_to_string(img, lang="eng", config=config) or "")
        except Exception:
            text = ""
    try:
        data = pytesseract.image_to_data(
            img, lang=lang, config=config, output_type=pytesseract.Output.DICT
        )
        confs = []
        for c in data.get("conf") or []:
            try:
                v = float(c)
                if v >= 0:
                    confs.append(v)
            except (TypeError, ValueError):
                continue
        if confs:
            conf_avg = sum(confs) / len(confs)
    except Exception:
        conf_avg = None
    return text, conf_avg


def ocr_image_handwriting(
    source: Union[str, Path, Image.Image],
    lang: str = "deu+eng",
    *,
    psm: int | str | None = None,
    preprocess: bool | None = None,
    multi_psm: bool | None = None,
) -> str:
    """
    Handschriftenerkennung — verbessert gegenüber reinem PSM-Hook.

    Verbesserungen vs. reiner ``--psm``-Aufruf:
    - optionales PIL-Preprocess (Kontrast, Schwellwert, leichtes Deskew)
    - Multi-PSM: mehrere Modi (6/7/8/11/…) → beste Confidence/Textlänge
    - Settings ``ocr_handwriting`` / ``ild.ocr_handwriting`` (preprocess, multi_psm, psm)

    Kein eingebettetes Handschrift-ML-Netz; siehe ``HANDWRITING_UPGRADE_PATH``.
    """
    ok, msg = tesseract_available()
    if not ok:
        raise OcrUnavailable(msg)

    settings = _handwriting_settings()
    do_prep = settings.get("preprocess", True) if preprocess is None else bool(preprocess)
    do_multi = settings.get("multi_psm", True) if multi_psm is None else bool(multi_psm)
    if psm is None:
        psm = settings.get("psm", DEFAULT_HANDWRITING_PSM)

    img = _load_image(source)
    try:
        img = img.convert("RGB") if img.mode not in ("RGB", "L") else img
    except Exception:
        pass

    work = _preprocess_handwriting(img) if do_prep else img

    psm_n = normalize_handwriting_psm(psm)
    candidates: list[int] = [psm_n]
    if do_multi:
        for c in HANDWRITING_PSM_CANDIDATES:
            if c not in candidates:
                candidates.append(c)

    best_text = ""
    best_score = -1.0
    for cand in candidates:
        text, conf = _ocr_with_psm(work, lang, cand)
        score = _score_ocr_result(text, conf)
        if score > best_score:
            best_score = score
            best_text = text
        # Wenn Preprocess schwach: einmal Original versuchen (erster Kandidat)
        if cand == psm_n and do_prep and best_score < 5:
            text2, conf2 = _ocr_with_psm(img, lang, cand)
            score2 = _score_ocr_result(text2, conf2)
            if score2 > best_score:
                best_score = score2
                best_text = text2

    if best_text and str(best_text).strip():
        return str(best_text)

    # letzter Fallback wie zuvor
    import pytesseract

    config = f"--psm {psm_n}"
    try:
        return pytesseract.image_to_string(img, lang=lang, config=config)
    except Exception:
        try:
            return pytesseract.image_to_string(img, lang="eng", config=config)
        except Exception:
            return pytesseract.image_to_string(img, lang="eng")


def handwriting_recognize(
    image_path: Union[str, Path, Image.Image],
    lang: str = "deu+eng",
    *,
    psm: int | str | None = None,
) -> dict:
    """
    Handschrift erkennen — strukturierte API über ``ocr_image_handwriting``.

    Verbessert vs. reiner PSM-Hook: Preprocess + Multi-PSM-Auswahl.
    ``upgrade_path`` beschreibt den Weg zu externen ML-Modellen.
    """
    text = ocr_image_handwriting(image_path, lang=lang, psm=psm)
    settings = _handwriting_settings()
    return {
        "ok": True,
        "text": text,
        "lang": lang,
        "psm": normalize_handwriting_psm(
            psm if psm is not None else settings.get("psm")
        ),
        "preprocess": bool(settings.get("preprocess", True)),
        "multi_psm": bool(settings.get("multi_psm", True)),
        "engine": str(settings.get("engine") or "tesseract"),
        "improved_vs_pure_psm": True,
        "upgrade_path": HANDWRITING_UPGRADE_PATH,
        "note": (
            "Preprocess (Kontrast/Schwellwert/Deskew) + Multi-PSM Confidence-Pick; "
            "kein eingebettetes Handschrift-ML."
        ),
    }

def ocr_image(
    source: Union[str, Path, Image.Image],
    lang: str = "deu+eng",
    *,
    table_layout: bool = True,
    preserve_layout: bool = False,
    handwriting: bool = False,
    handwriting_psm: int | str = DEFAULT_HANDWRITING_PSM,
) -> str:
    ok, msg = tesseract_available()
    if not ok:
        raise OcrUnavailable(msg)

    import pytesseract

    img = _load_image(source)
    if handwriting:
        return ocr_image_handwriting(img, lang=lang, psm=handwriting_psm)
    if preserve_layout:
        try:
            layout = ocr_image_layout(img, lang=lang, include_hocr=False, include_tsv=False)
            if layout.text.strip():
                return layout.text
        except Exception:
            pass
    if table_layout:
        try:
            text, used = ocr_image_structured(img, lang=lang)
            if used or text.strip():
                return text
        except Exception:
            pass
    try:
        return pytesseract.image_to_string(img, lang=lang)
    except Exception:
        return pytesseract.image_to_string(img, lang="eng")


def ocr_pdf_page(pdf_path: str | Path, page_index: int = 0, lang: str = "deu+eng") -> str:
    from ild_pdf import render_page

    img = render_page(pdf_path, page_index=page_index, scale=2.0)
    return ocr_image(img, lang=lang)


# OCR-Render-DPI (Batch-Dialog): 150 / 300 — 1.1.2
OCR_DPI_CHOICES: tuple[int, ...] = (150, 300)
DEFAULT_OCR_DPI = 150


def dpi_to_scale(dpi: int) -> float:
    """DPI → pypdfium2-Render-Scale (72 DPI = 1.0)."""
    d = int(dpi) if dpi else DEFAULT_OCR_DPI
    if d not in OCR_DPI_CHOICES:
        d = min(OCR_DPI_CHOICES, key=lambda x: abs(x - d))
    return max(d / 72.0, 1.0)


def crop_page_image(
    img: Image.Image,
    rect: tuple[float, float, float, float],
    *,
    display_scale: float | None = None,
    render_scale: float | None = None,
) -> Image.Image:
    """
    Rechteck aus gerenderter Seite ausschneiden — 2.5.0.

    ``rect`` = (x, y, w, h) in Anzeige-Pixeln bei ``display_scale``.
    Wenn ``render_scale`` abweicht, werden die Koordinaten skaliert.
    """
    x, y, w, h = (float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3]))
    if (
        display_scale
        and render_scale
        and display_scale > 0
        and abs(float(display_scale) - float(render_scale)) > 1e-6
    ):
        f = float(render_scale) / float(display_scale)
        x, y, w, h = x * f, y * f, w * f, h * f
    left = max(0, int(round(min(x, x + w))))
    top = max(0, int(round(min(y, y + h))))
    right = min(img.width, int(round(max(x, x + w))))
    bottom = min(img.height, int(round(max(y, y + h))))
    if right - left < 2:
        right = min(img.width, left + 2)
    if bottom - top < 2:
        bottom = min(img.height, top + 2)
    if right <= left or bottom <= top:
        raise ValueError("OCR-Region ist leer oder außerhalb der Seite.")
    return img.crop((left, top, right, bottom))


def ocr_pdf_region(
    pdf_path: str | Path,
    page_index: int,
    rect: tuple[float, float, float, float],
    *,
    lang: str = "deu+eng",
    dpi: int | None = None,
    display_scale: float | None = None,
) -> OcrResult:
    """
    OCR nur auf einem Seiten-Rechteck → editierbarer Text — 2.5.0.

    ``rect`` = (x, y, width, height) in Anzeige-Pixeln (wie Annotationen).
    """
    from ild_pdf import render_page

    dpi_eff = int(dpi) if dpi else DEFAULT_OCR_DPI
    if dpi_eff not in OCR_DPI_CHOICES:
        dpi_eff = min(OCR_DPI_CHOICES, key=lambda x: abs(x - dpi_eff))
    scale = dpi_to_scale(dpi_eff)
    img = render_page(pdf_path, page_index=int(page_index), scale=scale)
    cropped = crop_page_image(
        img,
        rect,
        display_scale=display_scale if display_scale is not None else scale,
        render_scale=scale,
    )
    label = f"{Path(pdf_path).name} S.{int(page_index) + 1} Region"
    return run_ocr(
        cropped,
        lang=lang,
        mode=OcrOutputMode.EDITABLE_TEXT,
        source_label=label,
    )


@dataclass
class OcrDocumentResult:
    """Ergebnis einer Batch-OCR über PDF-Seiten (optional Bereich)."""

    text: str
    lang: str
    pages_done: int
    pages_total: int
    cancelled: bool = False
    page_texts: List[str] = field(default_factory=list)
    dpi: int = DEFAULT_OCR_DPI
    page_from: int = 1  # 1-basiert inkl.
    page_to: int = 0  # 1-basiert inkl.; 0 = Ende
    # (Seitennummer 1-basiert, Fehlermeldung) — 1.1.3
    page_errors: List[tuple[int, str]] = field(default_factory=list)


def _format_ocr_errors_section(page_errors: List[tuple[int, str]]) -> str:
    """Abschnitt „OCR-Fehler“ für Ergebnis-TXT — 1.1.3."""
    if not page_errors:
        return ""
    lines = ["--- OCR-Fehler ---"]
    for page_no, err in page_errors:
        msg = (err or "unbekannt").strip().replace("\n", " ")
        if len(msg) > 200:
            msg = msg[:197] + "…"
        lines.append(f"Seite {page_no}: {msg}")
    return "\n".join(lines) + "\n"


def ocr_pdf_document(
    pdf_path: str | Path,
    *,
    lang: str = "deu+eng",
    scale: float | None = None,
    dpi: int | None = None,
    page_from: int | None = None,
    page_to: int | None = None,
    attach_errors: bool = True,
    progress: Optional[Callable[[int, int, str], Optional[bool]]] = None,
) -> OcrDocumentResult:
    """
    OCR über PDF-Seiten (optional von–bis, 1-basiert inkl.).
    dpi 150/300 setzt scale=dpi/72; scale-Argument bleibt kompatibel.
    progress(page_1based, total_in_range, preview) → False zum Abbrechen.
    Seitenfehler werden gesammelt; mit attach_errors=True (Default) als Abschnitt
    angehängt (1.1.3/1.1.4). Abbruch behält Teilergebnis inkl. bisheriger Fehler.
    """
    from ild_pdf import render_page

    ok, msg = tesseract_available()
    if not ok:
        raise OcrUnavailable(msg)

    pdf_path = Path(pdf_path)
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        total = len(doc)
    finally:
        doc.close()

    use_dpi = int(dpi) if dpi is not None else DEFAULT_OCR_DPI
    if use_dpi not in OCR_DPI_CHOICES:
        use_dpi = min(OCR_DPI_CHOICES, key=lambda x: abs(x - use_dpi))
    if scale is None:
        scale = dpi_to_scale(use_dpi)
    else:
        scale = max(float(scale), 1.0)

    start = 1 if page_from is None else max(1, int(page_from))
    end = total if page_to is None else min(total, int(page_to))
    if start > total:
        start = total if total else 1
    if end < start:
        end = start
    if total <= 0:
        return OcrDocumentResult(
            text="",
            lang=lang,
            pages_done=0,
            pages_total=0,
            cancelled=False,
            page_texts=[],
            dpi=use_dpi,
            page_from=start,
            page_to=end,
            page_errors=[],
        )

    indices = list(range(start - 1, end))  # 0-basiert
    range_total = len(indices)
    page_texts: List[str] = []
    page_errors: List[tuple[int, str]] = []
    cancelled = False
    for i, page in enumerate(indices):
        if progress is not None:
            cont = progress(
                i + 1,
                range_total,
                f"Seite {page + 1}/{total} ({i + 1}/{range_total})",
            )
            if cont is False:
                cancelled = True
                break
        page_no = page + 1
        try:
            img = render_page(pdf_path, page_index=page, scale=scale)
            page_texts.append(ocr_image(img, lang=lang))
        except OcrUnavailable:
            raise
        except Exception as e:
            page_texts.append("")
            page_errors.append((page_no, f"{type(e).__name__}: {e}"))

    parts: List[str] = []
    for i, t in enumerate(page_texts):
        page_no = indices[i] + 1
        header = f"--- Seite {page_no}/{total} ---"
        body = (t or "").rstrip()
        if not body and any(pe[0] == page_no for pe in page_errors):
            body = (
                "[OCR-Fehler — siehe Abschnitt am Ende]"
                if attach_errors
                else "[OCR-Fehler]"
            )
        parts.append(f"{header}\n{body}" if body else header)
    combined = "\n\n".join(parts).strip()
    err_section = (
        _format_ocr_errors_section(page_errors) if attach_errors else ""
    )
    if err_section:
        combined = (combined + "\n\n" + err_section) if combined else err_section
    elif combined:
        combined += "\n"
    return OcrDocumentResult(
        text=combined,
        lang=lang,
        pages_done=len(page_texts),
        pages_total=range_total,
        cancelled=cancelled,
        page_texts=page_texts,
        dpi=use_dpi,
        page_from=start,
        page_to=end,
        page_errors=page_errors,
    )


def make_searchable_image_pdf(
    source: Union[str, Path, Image.Image],
    text: str,
    out_path: str | Path,
    *,
    lang: str = "deu+eng",
) -> Tuple[Path, Path]:
    """
    „Durchsuchbares Bild“: speichert Bild als PDF-Seite + Text-Sidecar
    (`*.ildocr.txt`) daneben. Kein vollständiges unsichtbares Textlayer-PDF
    (dafür bräuchte man reportlab/hocr) — aber real nutzbar für Suche/Archiv.
    """
    out_path = Path(out_path)
    if isinstance(source, (str, Path)):
        img = Image.open(source)
    else:
        img = source.copy()
    if img.mode == "RGBA":
        img = img.convert("RGB")

    # Titelzeile mit Hinweis auf Sidecar
    canvas = img
    try:
        draw = ImageDraw.Draw(canvas)
        # dezenter Hinweis unten
        note = "InstantLens Doc — durchsuchbares Bild (Text in Sidecar)"
        draw.rectangle([0, canvas.height - 18, canvas.width, canvas.height], fill=(240, 240, 240))
        draw.text((4, canvas.height - 16), note, fill=(80, 80, 80))
    except Exception:
        pass

    canvas.save(out_path, "PDF", resolution=150.0)
    sidecar = out_path.with_suffix(out_path.suffix + ".ildocr.txt")
    header = f"# InstantLens Doc OCR\n# lang={lang}\n# mode=searchable_image\n\n"
    sidecar.write_text(header + text, encoding="utf-8")
    return out_path, sidecar


def run_ocr(
    source: Union[str, Path, Image.Image],
    *,
    lang: str = "deu+eng",
    mode: OcrOutputMode = OcrOutputMode.EDITABLE_TEXT,
    out_dir: str | Path | None = None,
    source_label: str = "",
    csv_delimiter: str | None = None,
    csv_utf8_bom: bool | None = None,
    write_csv: bool = True,
    preserve_layout: bool = False,
    write_hocr: bool = True,
    write_tsv: bool = True,
    handwriting: bool = False,
    handwriting_psm: int | str = DEFAULT_HANDWRITING_PSM,
) -> OcrResult:
    """Einheitlicher OCR-Einstieg inkl. Layout-Erhalt / CSV / Handschrift — 1.9.2 / 2.6.3 / 2.6.19."""
    label = source_label or (
        str(source) if isinstance(source, (str, Path)) else "Bild"
    )
    if handwriting:
        text = ocr_image_handwriting(source, lang=lang, psm=handwriting_psm)
        return OcrResult(
            text=text,
            lang=lang,
            mode=OcrOutputMode.EDITABLE_TEXT,
            source_label=label + " [Handschrift]",
        )
    if mode == OcrOutputMode.TABLE_CSV:
        delim = csv_delimiter
        bom = csv_utf8_bom
        if delim is None or bom is None:
            try:
                from instantlensdoc.core.app_settings import (
                    get_ocr_table_csv_delimiter,
                    get_ocr_table_csv_utf8_bom,
                )

                if delim is None:
                    delim = get_ocr_table_csv_delimiter()
                if bom is None:
                    bom = get_ocr_table_csv_utf8_bom()
            except Exception:
                if delim is None:
                    delim = ";"
                if bom is None:
                    bom = True
        rows, _used = ocr_image_table_rows(source, lang=lang)
        csv_text = (
            format_rows_as_csv(rows, delimiter=str(delim), utf8_bom=bool(bom))
            if rows
            else ("\ufeff" if bom else "")
        )
        csv_path = None
        if write_csv:
            out_dir_p = Path(out_dir) if out_dir else Path.cwd()
            out_dir_p.mkdir(parents=True, exist_ok=True)
            stem = Path(label).stem if label else "ocr"
            csv_path = out_dir_p / f"{stem}_table.csv"
            csv_path.write_text(csv_text, encoding="utf-8")
        return OcrResult(
            text=csv_text,
            lang=lang,
            mode=mode,
            source_label=label,
            sidecar=csv_path,
            table_rows=rows or [],
        )

    # Layout-Erhalt-Modus oder preserve_layout-Flag — 2.6.3
    use_layout = mode == OcrOutputMode.LAYOUT_PRESERVE or preserve_layout
    layout: OcrLayoutPage | None = None
    if use_layout:
        layout = ocr_image_layout(
            source,
            lang=lang,
            include_hocr=write_hocr or mode == OcrOutputMode.LAYOUT_PRESERVE,
            include_tsv=write_tsv or mode == OcrOutputMode.LAYOUT_PRESERVE,
        )
        text = layout.text
    else:
        text = ocr_image(source, lang=lang)

    if mode == OcrOutputMode.EDITABLE_TEXT:
        return OcrResult(
            text=text,
            lang=lang,
            mode=mode,
            source_label=label,
            blocks=list(layout.blocks) if layout else None,
            layout=layout,
        )

    if mode == OcrOutputMode.LAYOUT_PRESERVE:
        out_dir_p = Path(out_dir) if out_dir else Path.cwd()
        stem = Path(label).stem if label else "ocr"
        assert layout is not None
        txt_path, hocr_path, tsv_path = write_layout_sidecars(
            out_dir_p,
            stem,
            layout,
            lang=lang,
            write_hocr=write_hocr,
            write_tsv=write_tsv,
        )
        return OcrResult(
            text=text,
            lang=lang,
            mode=mode,
            source_label=label,
            sidecar=txt_path,
            blocks=list(layout.blocks),
            hocr_path=hocr_path,
            tsv_path=tsv_path,
            layout=layout,
        )

    out_dir_p = Path(out_dir) if out_dir else Path.cwd()
    out_dir_p.mkdir(parents=True, exist_ok=True)
    stem = Path(label).stem if label else "ocr"
    out_pdf = out_dir_p / f"{stem}_searchable.pdf"
    pdf_path, sidecar = make_searchable_image_pdf(source, text, out_pdf, lang=lang)
    hocr_path = tsv_path = None
    if layout is not None and (write_hocr or write_tsv):
        _txt, hocr_path, tsv_path = write_layout_sidecars(
            out_dir_p,
            stem + "_searchable",
            layout,
            lang=lang,
            write_hocr=write_hocr,
            write_tsv=write_tsv,
        )
        # Primäres Sidecar bleibt das searchable ildocr.txt; Layout-TXT zusätzlich
        _ = _txt
    return OcrResult(
        text=text,
        lang=lang,
        mode=mode,
        source_label=label,
        searchable_pdf=pdf_path,
        sidecar=sidecar,
        blocks=list(layout.blocks) if layout else None,
        hocr_path=hocr_path,
        tsv_path=tsv_path,
        layout=layout,
    )


def status_message() -> str:
    ok, msg = tesseract_available()
    return msg if ok else f"OCR nicht verfügbar:\n{msg}"
