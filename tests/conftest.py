from unittest.mock import MagicMock
from ask_sdk_model import IntentRequest


def make_handler_input(intent_name, slots: dict[str, str] | None = None):
    hi = MagicMock()
    intent = MagicMock()
    intent.name = intent_name
    intent.slots = {}
    if slots:
        for name, value in slots.items():
            slot = MagicMock()
            slot.value = value
            intent.slots[name] = slot
    request = MagicMock(spec=IntentRequest)
    request.intent = intent
    hi.request_envelope.request = request
    rb = MagicMock()
    rb.speak.return_value = rb
    rb.ask.return_value = rb
    rb.set_should_end_session.return_value = rb
    rb.response = MagicMock()
    hi.response_builder = rb
    return hi
