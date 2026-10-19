from __future__ import annotations

from pathlib import Path

from officedisplay.model.presentation import Presentation, Slide, SlideObject, new_id


class MacroError(Exception):
    pass


class MacroApi:
    def __init__(self, presentation: Presentation):
        self.presentation = presentation
        self.log: list[str] = []

    def slide_count(self) -> int:
        return len(self.presentation.slides)

    def add_text_slide(self, title: str, bullets: list[str] | None = None) -> None:
        slide = Slide(id=new_id(), name=title or "Makro")
        slide.objects.append(
            SlideObject(
                id=new_id(),
                kind="text",
                x=0.07,
                y=0.08,
                w=0.86,
                h=0.14,
                name="titel",
                props={"text": title, "font_size": 32, "bold": True, "color": "#0B63E5", "font_family": "Segoe UI"},
            )
        )
        if bullets:
            slide.objects.append(
                SlideObject(
                    id=new_id(),
                    kind="text",
                    x=0.08,
                    y=0.28,
                    w=0.84,
                    h=0.58,
                    name="inhalt",
                    props={
                        "text": "\n".join(f"• {item}" for item in bullets),
                        "font_size": 22,
                        "color": "#1B1F2A",
                        "font_family": "Segoe UI",
                    },
                )
            )
        self.presentation.slides.append(slide)
        self.log.append(f"Folie {title}")


def run_macro(path: str | Path, presentation: Presentation) -> str:
    source = Path(path).read_text(encoding="utf-8")
    api = MacroApi(presentation)
    safe_builtins = {
        "len": len,
        "range": range,
        "str": str,
        "int": int,
        "float": float,
        "list": list,
        "dict": dict,
        "enumerate": enumerate,
        "min": min,
        "max": max,
    }
    namespace = {"__builtins__": safe_builtins}
    try:
        exec(compile(source, str(path), "exec"), namespace, namespace)
    except Exception as exc:  # noqa: BLE001
        raise MacroError(f"Makro konnte nicht gelesen werden: {exc}") from exc
    runner = namespace.get("run")
    if not callable(runner):
        raise MacroError("Das Makro braucht eine Funktion run(api).")
    try:
        runner(api)
    except Exception as exc:  # noqa: BLE001
        raise MacroError(f"Makro abgebrochen: {exc}") from exc
    return "\n".join(api.log) or "Makro ausgeführt."
