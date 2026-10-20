from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterator


AUTHOR = "Andreas Meyer"
EMAIL = "ame@sellerbach.de"


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def default_brand() -> dict[str, Any]:
    return {
        "locked": False,
        "heading_font": "Segoe UI",
        "body_font": "Segoe UI",
        "colors": ["#0B63E5", "#F28C28", "#3CB44B", "#E23B3B", "#1B1F2A", "#FFFFFF"],
        "logo": None,
    }


@dataclass
class SlideObject:
    id: str
    kind: str
    x: float
    y: float
    w: float
    h: float
    rotation: float = 0.0
    name: str = ""
    props: dict[str, Any] = field(default_factory=dict)
    children: list[SlideObject] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "rotation": self.rotation,
            "name": self.name,
            "props": copy.deepcopy(self.props),
            "children": [child.to_dict() for child in self.children],
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> SlideObject:
        return SlideObject(
            id=data.get("id") or new_id(),
            kind=data.get("kind") or "shape",
            x=float(data.get("x", 0)),
            y=float(data.get("y", 0)),
            w=float(data.get("w", 0.2)),
            h=float(data.get("h", 0.2)),
            rotation=float(data.get("rotation", 0)),
            name=data.get("name") or "",
            props=copy.deepcopy(data.get("props") or {}),
            children=[SlideObject.from_dict(child) for child in data.get("children") or []],
        )

    def clone(self) -> SlideObject:
        return SlideObject.from_dict(self.to_dict())


@dataclass
class Background:
    mode: str = "solid"
    color: str = "#FFFFFF"
    color2: str = "#E8EEF8"
    angle: float = 160.0
    image: str | None = None
    opacity: float = 1.0
    fit: str = "cover"
    offset_x: float = 0.0
    offset_y: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "color": self.color,
            "color2": self.color2,
            "angle": self.angle,
            "image": self.image,
            "opacity": self.opacity,
            "fit": self.fit,
            "offset_x": self.offset_x,
            "offset_y": self.offset_y,
        }

    @staticmethod
    def from_dict(data: dict[str, Any] | None) -> Background:
        data = data or {}
        return Background(
            mode=data.get("mode") or "solid",
            color=data.get("color") or "#FFFFFF",
            color2=data.get("color2") or "#E8EEF8",
            angle=float(data.get("angle", 160)),
            image=data.get("image"),
            opacity=float(data.get("opacity", 1)),
            fit=data.get("fit") or "cover",
            offset_x=float(data.get("offset_x", 0)),
            offset_y=float(data.get("offset_y", 0)),
        )


@dataclass
class Comment:
    id: str
    text: str
    author: str = AUTHOR

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "text": self.text, "author": self.author}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Comment:
        return Comment(
            id=data.get("id") or new_id(),
            text=data.get("text") or "",
            author=data.get("author") or AUTHOR,
        )


@dataclass
class Slide:
    id: str
    name: str
    objects: list[SlideObject] = field(default_factory=list)
    background: Background = field(default_factory=Background)
    notes: str = ""
    transition: str = "none"
    status: str = "entwurf"
    comments: list[Comment] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "objects": [obj.to_dict() for obj in self.objects],
            "background": self.background.to_dict(),
            "notes": self.notes,
            "transition": self.transition,
            "status": self.status,
            "comments": [comment.to_dict() for comment in self.comments],
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Slide:
        return Slide(
            id=data.get("id") or new_id(),
            name=data.get("name") or "Folie",
            objects=[SlideObject.from_dict(obj) for obj in data.get("objects") or []],
            background=Background.from_dict(data.get("background")),
            notes=data.get("notes") or "",
            transition=data.get("transition") or "none",
            status=data.get("status") or "entwurf",
            comments=[Comment.from_dict(item) for item in data.get("comments") or []],
        )

    def clone(self) -> Slide:
        return Slide.from_dict(self.to_dict())


@dataclass
class Presentation:
    title: str = "Unbenannt"
    width: int = 1920
    height: int = 1080
    slides: list[Slide] = field(default_factory=list)
    brand: dict[str, Any] = field(default_factory=default_brand)
    author: str = AUTHOR
    email: str = EMAIL
    theme: str = "hell"
    analytics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "officedisplay",
            "version": 1,
            "title": self.title,
            "width": self.width,
            "height": self.height,
            "author": self.author,
            "email": self.email,
            "theme": self.theme,
            "brand": copy.deepcopy(self.brand),
            "analytics": copy.deepcopy(self.analytics),
            "slides": [slide.to_dict() for slide in self.slides],
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Presentation:
        presentation = Presentation(
            title=data.get("title") or "Unbenannt",
            width=int(data.get("width") or 1920),
            height=int(data.get("height") or 1080),
            slides=[Slide.from_dict(slide) for slide in data.get("slides") or []],
            brand=copy.deepcopy(data.get("brand") or default_brand()),
            author=data.get("author") or AUTHOR,
            email=data.get("email") or EMAIL,
            theme=data.get("theme") or "hell",
            analytics=copy.deepcopy(data.get("analytics") or {}),
        )
        if not presentation.slides:
            presentation.slides.append(Slide(id=new_id(), name="Folie 1"))
        return presentation

    def clone(self) -> Presentation:
        return Presentation.from_dict(self.to_dict())


def blank_presentation() -> Presentation:
    presentation = Presentation()
    presentation.slides.append(
        Slide(
            id=new_id(),
            name="Folie 1",
            background=Background(mode="gradient", color="#0B63E5", color2="#08357A"),
        )
    )
    return presentation


def find_object(
    slide: Slide, object_id: str
) -> tuple[SlideObject | None, SlideObject | None, list[SlideObject] | None]:
    def walk(
        container: list[SlideObject], parent: SlideObject | None
    ) -> tuple[SlideObject | None, SlideObject | None, list[SlideObject] | None]:
        for obj in container:
            if obj.id == object_id:
                return obj, parent, container
            if obj.children:
                found = walk(obj.children, obj)
                if found[0] is not None:
                    return found
        return None, None, None

    return walk(slide.objects, None)


def object_path(slide: Slide, object_id: str) -> list[SlideObject]:
    path: list[SlideObject] = []

    def walk(container: list[SlideObject]) -> bool:
        for obj in container:
            path.append(obj)
            if obj.id == object_id:
                return True
            if obj.children and walk(obj.children):
                return True
            path.pop()
        return False

    if walk(slide.objects):
        return path
    return []


def absolute_geometry(path: list[SlideObject]) -> tuple[float, float, float, float]:
    x, y, w, h = 0.0, 0.0, 1.0, 1.0
    for obj in path:
        x = x + obj.x * w
        y = y + obj.y * h
        w = obj.w * w
        h = obj.h * h
    return x, y, w, h


def iter_objects(slide: Slide) -> Iterator[SlideObject]:
    def walk(objects: list[SlideObject]) -> Iterator[SlideObject]:
        for obj in objects:
            yield obj
            if obj.children:
                yield from walk(obj.children)

    yield from walk(slide.objects)


def flatten(slide: Slide) -> list[tuple[SlideObject, float, float, float, float]]:
    found: list[tuple[SlideObject, float, float, float, float]] = []

    def walk(objects: list[SlideObject], ox: float, oy: float, ow: float, oh: float) -> None:
        for obj in objects:
            ax = ox + obj.x * ow
            ay = oy + obj.y * oh
            aw = obj.w * ow
            ah = obj.h * oh
            if obj.kind == "group":
                walk(obj.children, ax, ay, aw, ah)
            else:
                found.append((obj, ax, ay, aw, ah))

    walk(slide.objects, 0, 0, 1, 1)
    return found


def remove_object(slide: Slide, object_id: str) -> SlideObject | None:
    obj, _parent, container = find_object(slide, object_id)
    if obj is None or container is None:
        return None
    container.remove(obj)
    return obj


def group_objects(slide: Slide, ids: list[str]) -> SlideObject | None:
    if len(ids) < 2:
        return None
    items: list[SlideObject] = []
    for object_id in ids:
        obj, parent, _container = find_object(slide, object_id)
        if obj is None or parent is not None:
            return None
        items.append(obj)
    min_x = min(obj.x for obj in items)
    min_y = min(obj.y for obj in items)
    max_x = max(obj.x + obj.w for obj in items)
    max_y = max(obj.y + obj.h for obj in items)
    width = max(max_x - min_x, 0.01)
    height = max(max_y - min_y, 0.01)
    for obj in items:
        slide.objects.remove(obj)
        obj.x = (obj.x - min_x) / width
        obj.y = (obj.y - min_y) / height
        obj.w = obj.w / width
        obj.h = obj.h / height
    group = SlideObject(
        id=new_id(),
        kind="group",
        x=min_x,
        y=min_y,
        w=width,
        h=height,
        name="Gruppe",
        children=items,
    )
    slide.objects.append(group)
    return group


def ungroup(slide: Slide, group_id: str) -> list[SlideObject]:
    obj, _parent, container = find_object(slide, group_id)
    if obj is None or obj.kind != "group" or container is None:
        return []
    container.remove(obj)
    released: list[SlideObject] = []
    for child in obj.children:
        child.x = obj.x + child.x * obj.w
        child.y = obj.y + child.y * obj.h
        child.w = child.w * obj.w
        child.h = child.h * obj.h
        container.append(child)
        released.append(child)
    return released


def move_object_to_slide(source: Slide, target: Slide, object_id: str) -> bool:
    if source is target:
        return False
    path = object_path(source, object_id)
    if not path:
        return False
    obj = path[-1]
    ax, ay, aw, ah = absolute_geometry(path)
    removed = remove_object(source, object_id)
    if removed is None:
        return False
    removed.x, removed.y, removed.w, removed.h = ax, ay, aw, ah
    target.objects.append(removed)
    return removed is obj


def duplicate_objects(slide: Slide, ids: list[str]) -> list[SlideObject]:
    copies: list[SlideObject] = []
    for object_id in ids:
        obj, parent, container = find_object(slide, object_id)
        if obj is None or container is None or parent is not None:
            continue
        clone = obj.clone()
        _rewrite_ids(clone)
        clone.x = min(0.95, clone.x + 0.03)
        clone.y = min(0.95, clone.y + 0.03)
        container.append(clone)
        copies.append(clone)
    return copies


def _rewrite_ids(obj: SlideObject) -> None:
    obj.id = new_id()
    for child in obj.children:
        _rewrite_ids(child)


def clamp_object(obj: SlideObject) -> None:
    obj.w = min(2.0, max(0.02, obj.w))
    obj.h = min(2.0, max(0.02, obj.h))
    obj.x = min(1.2, max(-0.3, obj.x))
    obj.y = min(1.2, max(-0.3, obj.y))
