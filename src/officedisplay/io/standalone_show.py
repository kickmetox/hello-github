"""Programmordner: Browser-Slideshow, ohne Python und ohne den Editor."""

from __future__ import annotations

import html
import json
import shutil
import stat
from pathlib import Path

from officedisplay.io.slideshow_io import save_presentation_oshow, slideshow_from_presentation
from officedisplay.model.presentation import Presentation


LIESMICH = (
    "Doppelklick auf Slideshow.bat oder index.html.\n"
    "Kein Office Display, kein Python.\n"
    "mp4 und webm spielen, mkv, avi und mov im Browser oft nicht.\n"
)

SLIDESHOW_BAT = """@echo off\r
start "" "%~dp0index.html"\r
"""

SLIDESHOW_SH = """#!/bin/sh
cd "$(dirname "$0")" || exit 1
xdg-open "$PWD/index.html"
"""


def write_standalone_show(presentation: Presentation, folder: str | Path) -> Path:
    """Ordner zum Kopieren. Start ist index.html im Browser."""
    target = Path(folder)
    media = target / "media"
    media.mkdir(parents=True, exist_ok=True)
    show = slideshow_from_presentation(presentation, None)
    slides = [_slide_record(entry, media) for entry in show.entries]
    (target / "index.html").write_text(_page(show.title or "Slideshow", slides), encoding="utf-8", newline="\n")
    save_presentation_oshow(presentation, target / "show.oshow")
    (target / "Slideshow.bat").write_bytes(SLIDESHOW_BAT.encode("utf-8"))
    script = target / "Slideshow.sh"
    script.write_text(SLIDESHOW_SH, encoding="utf-8", newline="\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    (target / "liesmich.txt").write_text(LIESMICH, encoding="utf-8", newline="\n")
    leftover = target / "player.py"
    if leftover.is_file():
        leftover.unlink()
    return target


def _slide_record(entry, media: Path) -> dict:
    src = _copy_media(entry.path, media) if entry.path else ""
    return {
        "kind": entry.kind if entry.kind in {"image", "video", "text"} else "text",
        "title": entry.title or "",
        "text": entry.text or "",
        "src": src,
    }


def _copy_media(source: str, media: Path) -> str:
    path = Path(source)
    if not path.is_file():
        return ""
    name = path.name or "datei"
    dest = media / name
    stem, suffix = dest.stem, dest.suffix
    number = 2
    while dest.exists() and dest.stat().st_size != path.stat().st_size:
        dest = media / f"{stem}-{number}{suffix}"
        number += 1
    if not dest.exists():
        shutil.copyfile(path, dest)
    return f"media/{dest.name}"


def _page(title: str, slides: list[dict]) -> str:
    data = json.dumps(slides, ensure_ascii=False).replace("<", "\\u003c")
    safe_title = html.escape(title)
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{safe_title}</title>
<style>
html, body {{ margin: 0; height: 100%; background: #000; color: #fff; }}
#stage {{ height: 100%; display: flex; align-items: center; justify-content: center; }}
#stage img, #stage video {{ max-width: 100vw; max-height: 100vh; object-fit: contain; background: #000; }}
article {{ box-sizing: border-box; width: 100%; height: 100%; overflow: auto; padding: 48px; background: #F4F6FB; color: #1B1F2A; font: 32px "Segoe UI", sans-serif; white-space: pre-wrap; }}
article img {{ display: block; max-width: 100%; max-height: 40vh; margin-top: 24px; object-fit: contain; }}
#cover {{ position: fixed; inset: 0; display: none; }}
#cover.black {{ display: block; background: #000; }}
#cover.white {{ display: block; background: #fff; }}
</style>
</head>
<body>
<div id="stage"></div>
<div id="cover"></div>
<script>
var slides = {data};
var index = 0;
var blank = "";
var stage = document.getElementById("stage");
var cover = document.getElementById("cover");

function show() {{
  stage.textContent = "";
  if (!slides.length) return;
  if (index < 0) index = 0;
  if (index >= slides.length) index = slides.length - 1;
  var item = slides[index];
  if (item.kind === "text") {{
    var article = document.createElement("article");
    if (item.title) {{
      var heading = document.createElement("h1");
      heading.textContent = item.title;
      article.appendChild(heading);
    }}
    var body = document.createElement("p");
    body.textContent = item.text || item.title || "";
    article.appendChild(body);
    if (item.src) {{
      var extra = document.createElement("img");
      extra.src = item.src;
      extra.alt = item.title || "";
      article.appendChild(extra);
    }}
    stage.appendChild(article);
  }} else if (item.kind === "video") {{
    var video = document.createElement("video");
    video.controls = true;
    video.autoplay = true;
    video.src = item.src || "";
    stage.appendChild(video);
  }} else {{
    var image = document.createElement("img");
    image.src = item.src || "";
    image.alt = item.title || "";
    stage.appendChild(image);
  }}
  cover.className = blank;
}}

function enterFull() {{
  var root = document.documentElement;
  if (!document.fullscreenElement && root.requestFullscreen) root.requestFullscreen();
}}

document.addEventListener("keydown", function (event) {{
  var key = event.key;
  if (key === "Escape") {{
    if (document.fullscreenElement && document.exitFullscreen) document.exitFullscreen();
    return;
  }}
  enterFull();
  if (key === "b" || key === "B") {{
    blank = blank === "black" ? "" : "black";
    show();
    return;
  }}
  if (key === "w" || key === "W") {{
    blank = blank === "white" ? "" : "white";
    show();
    return;
  }}
  if (key === "Home") {{
    index = 0;
    blank = "";
    show();
    return;
  }}
  if (key === "End") {{
    index = slides.length ? slides.length - 1 : 0;
    blank = "";
    show();
    return;
  }}
  if (key === "ArrowRight" || key === "ArrowDown" || key === " ") {{
    if (index < slides.length - 1) index += 1;
    blank = "";
    show();
    event.preventDefault();
    return;
  }}
  if (key === "ArrowLeft" || key === "ArrowUp") {{
    if (index > 0) index -= 1;
    blank = "";
    show();
    return;
  }}
}});

show();
</script>
</body>
</html>
"""
