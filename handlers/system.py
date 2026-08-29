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
    "apaga": "apagar", "apagá": "apagar", "shutdown": "apagar",
    "reinicia": "reiniciar", "reiniciá": "reiniciar", "restart": "reiniciar",
    "bloquea": "bloquear", "bloqueá": "bloquear", "lock": "bloquear",
}


class SystemHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("SystemIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        slot = handler_input.request_envelope.request.intent.slots["action"]
        # Preferir el valor canónico que resuelve Alexa vía SYSTEM_ACTION_TYPE;
        # si no hay resolución, caer a lo hablado y mapear sinónimos a mano.
        action = ""
        try:
            resolutions = slot.resolutions.resolutions_per_authority
            if resolutions and resolutions[0].status.code.value == "ER_SUCCESS_MATCH":
                action = resolutions[0].values[0].value.name
        except (AttributeError, IndexError):
            pass
        if not action:
            raw = (slot.value or "").lower()
            action = _SYNONYMS.get(raw, raw)

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
            .ask("¿Algo más?")
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
