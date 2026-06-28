import subprocess

import ask_sdk_core.utils as ask_utils
from handlers.base import POWERSHELL_EXE
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

_DESTRUCTIVE = {"apagar", "reiniciar"}

_PS_COMMANDS: dict[str, list[str]] = {
    "apagar": [POWERSHELL_EXE, "Stop-Computer", "-Force"],
    "reiniciar": [POWERSHELL_EXE, "Restart-Computer", "-Force"],
    "bloquear": [POWERSHELL_EXE, "-Command", "rundll32.exe user32.dll,LockWorkStation"],
}

_SYNONYMS: dict[str, str] = {
    "apagá": "apagar", "shutdown": "apagar",
    "reiniciá": "reiniciar", "restart": "reiniciar",
    "bloqueá": "bloquear", "bloquea": "bloquear", "lock": "bloquear",
}


class SystemHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("SystemIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        raw = handler_input.request_envelope.request.intent.slots["action"].value or ""
        action = _SYNONYMS.get(raw.lower(), raw.lower())

        if action in _DESTRUCTIVE:
            handler_input.attributes_manager.session_attributes["pending_action"] = action
            return (
                handler_input.response_builder
                .speak(f"¿Seguro que quieres {action} la PC?")
                .ask("Di sí para confirmar o no para cancelar.")
                .response
            )

        if action == "bloquear":
            subprocess.run(_PS_COMMANDS["bloquear"], check=True)
            return (
                handler_input.response_builder
                .speak("Pantalla bloqueada.")
                .set_should_end_session(True)
                .response
            )

        return (
            handler_input.response_builder
            .speak("No entendí esa acción.")
            .set_should_end_session(False)
            .response
        )


class SystemConfirmHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        session = handler_input.attributes_manager.session_attributes
        return (
            ask_utils.is_intent_name("AMAZON.YesIntent")(handler_input)
            and "pending_action" in session
        ) or (
            ask_utils.is_intent_name("AMAZON.NoIntent")(handler_input)
            and "pending_action" in session
        )

    def handle(self, handler_input: HandlerInput) -> Response:
        session = handler_input.attributes_manager.session_attributes
        action = session.pop("pending_action", None)

        if ask_utils.is_intent_name("AMAZON.NoIntent")(handler_input) or not action:
            return (
                handler_input.response_builder
                .speak("Cancelado.")
                .set_should_end_session(True)
                .response
            )

        subprocess.run(_PS_COMMANDS[action], check=True)
        return (
            handler_input.response_builder
            .speak(f"Ejecutando {action}.")
            .set_should_end_session(True)
            .response
        )
