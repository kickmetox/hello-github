"""Office Display ruft keine Cloud-KI auf."""
from __future__ import annotations

class OnlineAIError(Exception):
    pass

class OnlineAISettings:
    def __init__(self, **_kwargs):
        self.enabled = False

def _offline(*_args, **_kwargs):
    raise OnlineAIError("Office Display arbeitet offline. Es gibt keine Cloud-KI und keinen Bilddienst.")

chat_completion = _offline
draft_deck = _offline
rewrite_text = _offline
generate_image = _offline
extract_json = _offline
validate_endpoint = _offline
