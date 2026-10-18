"""Modul 1: Umgebung und Anwendungen zwischen den Systemen übersetzen."""

from crossos.migrator.apps import plan_apps
from crossos.migrator.gestures import gesture_bridge
from crossos.migrator.packages import PackageBridge
from crossos.migrator.paths import translate_path
from crossos.migrator.semantic import translate_document
from crossos.migrator.shortcuts import translate_shortcut
from crossos.migrator.theme import theme_bridge

__all__ = [
    "PackageBridge",
    "gesture_bridge",
    "plan_apps",
    "theme_bridge",
    "translate_document",
    "translate_path",
    "translate_shortcut",
]
