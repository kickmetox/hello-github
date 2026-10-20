from __future__ import annotations

from officedisplay.model.presentation import Slide


def entrance_state(effect: str, t: float) -> dict:
    t = max(0.0, min(1.0, t))
    if effect == "fly":
        return {"opacity": min(1.0, t * 1.3), "dx": -0.22 * (1 - t), "scale": 1.0}
    if effect == "zoom":
        return {"opacity": t, "dx": 0.0, "scale": 0.72 + 0.28 * t}
    if effect == "fade":
        return {"opacity": t, "dx": 0.0, "scale": 1.0}
    return {"opacity": 1.0, "dx": 0.0, "scale": 1.0}


def apply_entrance(slide: Slide, t: float) -> Slide:
    cloned = slide.clone()
    for obj in cloned.objects:
        effect = (obj.props or {}).get("entrance")
        if not effect:
            continue
        state = entrance_state(str(effect), t)
        obj.props["opacity"] = state["opacity"]
        obj.x += state["dx"]
        scale = state["scale"]
        if scale != 1:
            cx = obj.x + obj.w / 2
            cy = obj.y + obj.h / 2
            obj.w *= scale
            obj.h *= scale
            obj.x = cx - obj.w / 2
            obj.y = cy - obj.h / 2
    return cloned


def morph_slide(source: Slide, target: Slide, t: float) -> Slide:
    """Objekte mit gleichem Namen wandern von der Quelle zum Ziel."""
    blended = target.clone()
    named = {obj.name: obj for obj in source.objects if obj.name}
    for obj in blended.objects:
        origin = named.get(obj.name)
        if origin is None:
            obj.props["opacity"] = t
            continue
        obj.x = origin.x + (obj.x - origin.x) * t
        obj.y = origin.y + (obj.y - origin.y) * t
        obj.w = origin.w + (obj.w - origin.w) * t
        obj.h = origin.h + (obj.h - origin.h) * t
        obj.props["opacity"] = 1
    return blended
