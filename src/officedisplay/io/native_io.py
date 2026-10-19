from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from officedisplay.model.presentation import Presentation, iter_objects


MEDIA_KEYS = ("path", "image", "render_path")


def save_odisp(presentation: Presentation, path: str | Path) -> None:
    target = Path(path)
    media = []
    payload = presentation.to_dict()
    for slide in payload["slides"]:
        image = (slide.get("background") or {}).get("image")
        if image:
            media.append(image)
        _collect(slide.get("objects") or [], media)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("presentation.json", json.dumps(payload, ensure_ascii=False, indent=2))
        for index, source in enumerate(dict.fromkeys(media)):
            file_path = Path(source)
            if file_path.is_file():
                archive.write(file_path, f"media/{index}_{file_path.name}")


def _collect(objects, media: list[str]) -> None:
    for obj in objects:
        props = obj.get("props") or {}
        for key in ("path", "render_path"):
            if props.get(key):
                media.append(props[key])
        _collect(obj.get("children") or [], media)


def load_odisp(path: str | Path) -> Presentation:
    source = Path(path)
    folder = source.with_suffix("") 
    media_dir = Path(str(folder) + "_media")
    if media_dir.exists():
        shutil.rmtree(media_dir)
    media_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source, "r") as archive:
        payload = json.loads(archive.read("presentation.json").decode("utf-8"))
        for info in archive.infolist():
            if info.filename.startswith("media/") and not info.is_dir():
                archive.extract(info, media_dir)
    extracted = {path.name: path for path in media_dir.rglob("*") if path.is_file()}
    _rewrite(payload, extracted)
    return Presentation.from_dict(payload)


def _rewrite(node, extracted: dict[str, Path]) -> None:
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if key in MEDIA_KEYS and isinstance(value, str):
                name = Path(value).name
                for file_name, file_path in extracted.items():
                    if file_name.endswith(name) or name in file_name:
                        node[key] = str(file_path)
                        break
            else:
                _rewrite(value, extracted)
    elif isinstance(node, list):
        for item in node:
            _rewrite(item, extracted)


def referenced_files(presentation: Presentation) -> list[str]:
    files = []
    for slide in presentation.slides:
        if slide.background.image:
            files.append(slide.background.image)
        for obj in iter_objects(slide):
            for key in ("path", "render_path"):
                if obj.props.get(key):
                    files.append(obj.props[key])
    return files
