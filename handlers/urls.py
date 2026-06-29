import subprocess

import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

from config import URLS
from handlers.base import CMD_EXE


class UrlHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("OpenUrlIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        slots = handler_input.request_envelope.request.intent.slots
        slot = slots["siteName"]
        # Prefer Alexa's resolved canonical value over raw speech
        try:
            resolutions = slot.resolutions.resolutions_per_authority
            if resolutions and resolutions[0].status.code.value == "ER_SUCCESS_MATCH":
                site_name = resolutions[0].values[0].value.name
            else:
                site_name = slot.value or ""
        except Exception:
            site_name = slot.value or ""

        site_key = next((k for k in URLS if k.lower() == site_name.lower()), None)
        if not site_key:
            return (
                handler_input.response_builder
                .speak("No conozco ese sitio.")
                .set_should_end_session(False)
                .response
            )

        url = URLS[site_key]
        subprocess.run([CMD_EXE, "/c", "start", "", url], check=True)
        return (
            handler_input.response_builder
            .speak(f"Abriendo {site_key}.")
            .ask("¿Algo más?")
            .response
        )
