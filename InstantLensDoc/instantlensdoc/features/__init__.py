"""Feature-Module 2.6.54: KI, Formerkennung, Variable Fonts, PAdES, Plugin-Erweiterungen."""

from .ki_assistant import KiRequest, KiResult, run_ki_action
from .shape_recognizer import ShapeResult, recognize_ink_as_shape, recognize_stroke

__all__ = [
    "KiRequest",
    "KiResult",
    "run_ki_action",
    "ShapeResult",
    "recognize_stroke",
    "recognize_ink_as_shape",
]
