"""Beispiel InstantLens Doc Plugin — on_open / on_save / on_scan + Menü.

Kopieren nach config/hooks/ oder Extras → Script-/Plugin-Hooks → Beispiel installieren.
"""

from instantlensdoc.features.plugins import register_menu_plugin


def on_open(**payload):
    return True


def on_save(**payload):
    return True


def on_scan(**payload):
    return True


def on_document_opened(**payload):
    on_open(**payload)


def register(api=None):
    def _ping():
        pass

    register_menu_plugin("Beispiel-Plugin: Ping", _ping, menu="Extras")
