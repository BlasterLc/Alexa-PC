import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

from handlers.base import send_key, VK_CODES


class PlayPauseHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return (
            ask_utils.is_intent_name("AMAZON.PauseIntent")(handler_input) or
            ask_utils.is_intent_name("AMAZON.ResumeIntent")(handler_input)
        )

    def handle(self, handler_input: HandlerInput) -> Response:
        send_key(VK_CODES["play_pause"])
        return (
            handler_input.response_builder
            .speak("Listo.")
            .set_should_end_session(False)
            .response
        )


class NextHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("AMAZON.NextIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        send_key(VK_CODES["next"])
        return (
            handler_input.response_builder
            .speak("Siguiente.")
            .set_should_end_session(False)
            .response
        )


class PrevHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("AMAZON.PreviousIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        send_key(VK_CODES["prev"])
        return (
            handler_input.response_builder
            .speak("Anterior.")
            .set_should_end_session(False)
            .response
        )


class VolumeHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("VolumeIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        direction = handler_input.request_envelope.request.intent.slots["direction"].value
        vk = VK_CODES["vol_up"] if direction in ("subir", "arriba", "más", "sube") else VK_CODES["vol_down"]
        word = "Subiendo" if vk == VK_CODES["vol_up"] else "Bajando"
        send_key(vk)
        return (
            handler_input.response_builder
            .speak(f"{word} el volumen.")
            .set_should_end_session(False)
            .response
        )
