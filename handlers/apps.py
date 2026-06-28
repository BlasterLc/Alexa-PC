import subprocess

import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

from config import APPS

_OPEN_SYNONYMS = {"abrir", "abrí", "abre", "lanzar", "lanzá"}
_CLOSE_SYNONYMS = {"cerrar", "cerrá", "cierra", "matar", "matá"}


class AppHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("AppIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        slots = handler_input.request_envelope.request.intent.slots
        app_name = slots["appName"].value or ""
        app_action = (slots["appAction"].value or "").lower()

        exe = APPS.get(app_name)
        if not exe:
            return (
                handler_input.response_builder
                .speak("No conozco esa aplicación.")
                .set_should_end_session(False)
                .response
            )

        if app_action in _OPEN_SYNONYMS:
            subprocess.run(["powershell.exe", "Start-Process", exe], check=True)
            speech = f"Abriendo {app_name}."
        elif app_action in _CLOSE_SYNONYMS:
            process_name = exe.replace(".exe", "")
            subprocess.run(
                ["powershell.exe", "Stop-Process", "-Name", process_name, "-Force"],
                check=True,
            )
            speech = f"Cerrando {app_name}."
        else:
            speech = "No entendí si quieres abrir o cerrar."

        return (
            handler_input.response_builder
            .speak(speech)
            .set_should_end_session(False)
            .response
        )
